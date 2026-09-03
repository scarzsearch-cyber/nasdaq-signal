#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
매일 QQQ 종가를 받아 신호를 계산하고 data/signal.json 을 갱신한다.
GitHub Actions에서 매일 자동 실행된다. 로컬에서 수동 실행도 가능:  python3 deploy/update_signal.py

두 전략을 함께 판정한다 (진입선은 -16%로 동일, 복귀선만 다름).
  B  -16 / -16 : 낙폭이 -16%를 회복하면 곧바로 QLD.   전략_v21 §11 권고안.
  A  -16 / -11 : 낙폭이 -11%보다 얕아져야 QLD.        기존 채택안.
어느 쪽을 쓸지는 화면에서 고른다. 성과지표는 deploy/build_stats.py 가 미리 굳혀둔
data/strategy_stats.json 을 그대로 실어 나른다.
"""
import json, os, sys
import datetime
# 윈도우 콘솔(cp949)에서 '−'(U+2212) 때문에 마지막 print 가 죽는다.
# 파일은 이미 쓰인 뒤라 결과는 맞지만, 수동 실행이 실패로 보인다.
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')   # 예비 사슬 경고문도 한글이다
except Exception:
    pass
import urllib.request
import pandas as pd
import numpy as np

LOOKBACK = 252
# 진입선은 공통 -16%. 복귀선만 전략별로 다르다.
ENTER = -0.16
STRATS = [
    ("B", "−16 / −16", -0.16, -0.16),
    ("A", "−16 / −11", -0.16, -0.11),
]
DEFAULT = "B"

# 도피 상태에서 보유할 방어자산 (전략_v23 §7). 전부 국내 상장·ISA 편입 가능·환노출.
DEFENSIVE = {
    "version": "v23",
    "label": "배당 40 / 미국채 40 / 금 20",
    "rebalance": "도피 구간 안에서 월 1회 (5%p 이상 벌어졌을 때만 해도 됨)",
    "note": "국채는 배당이 실패한 위기(GFC·코로나·87)에서 유일하게 벌어준다. "
            "국내 미국채10년선물 ETF 는 표기와 달리 환노출이고 실효만기는 약 5년이다"
            "(axis_krspec.py 실측). 전략_v23.md §5 참고.",
    # 다리마다 종목은 **딱 하나**만 둔다. 전략은 단순해야 지켜진다.
    "legs": [
        {"code": "458730", "name": "TIGER 미국배당다우존스", "weight": 40, "fx": "환노출"},
        {"code": "305080", "name": "TIGER 미국채10년선물", "weight": 40, "fx": "환노출"},
        {"code": "411060", "name": "ACE KRX금현물", "weight": 20, "fx": "환노출"},
    ],
}
RISK = {"code": "418660", "name": "TIGER 미국나스닥100레버리지(합성)"}

# stooq.com이 자동화 요청을 JS 챌린지로 차단해 Yahoo Finance chart API로 대체.
# [v66] Yahoo 가 죽는 날을 위한 예비 사슬: query1 → query2 미러 → 네이버 증권 → 캐시.
SRC = "https://{host}.finance.yahoo.com/v8/finance/chart/QQQ"
NAVER_SRC = "https://api.stock.naver.com/stock/QQQ.O/basic"
OUT_DIR = "data"
CSV_PATH = os.path.join(OUT_DIR, "qqq.csv")
JSON_PATH = os.path.join(OUT_DIR, "signal.json")
STATS_PATH = os.path.join(OUT_DIR, "strategy_stats.json")

# 과거 4대 위기 (궤적 비교용) — 고점일 기준
CRISES = [
    ("닷컴 2000",  "2000-03-27"),
    ("GFC 2007",   "2007-10-31"),
    ("코로나 2020", "2020-02-19"),
    ("2022 베어",   "2021-11-19"),
]


def fetch(host="query1"):
    period1 = int(datetime.datetime(1999, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    period2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = f"{SRC.format(host=host)}?period1={period1}&period2={period2}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.loads(r.read().decode("utf-8", "replace"))
    result = raw["chart"]["result"][0]
    ts = result["timestamp"]
    # [v71/B-1] 수정 종가(배당 조정)를 쓴다 — 백테스트(qqq_us_d.csv)와 같은 기준.
    # 비수정 종가는 배당락만큼 낙폭이 더 깊어 27년 중 11일 신호가 갈렸다(v67 감사).
    # 수정 종가로는 백테스트와 신호 불일치 0일(6,908일 검증). adjclose 가 없으면
    # 비수정으로 폴백하되 경고를 남긴다.
    ind = result["indicators"]
    closes = (ind.get("adjclose") or [{}])[0].get("adjclose")
    if not closes:
        print("[경고] adjclose 없음 — 비수정 종가로 폴백", file=sys.stderr)
        closes = ind["quote"][0]["close"]
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    s = pd.Series(closes, index=idx, name="Close").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    # [v66] 장중 가드: 미국 정규장 진행 중에 받으면 마지막 봉은 확정 종가가
    # 아니라 실시간 가격이다. 예약 실행이 몇 시간 밀려 개장(13:30 UTC) 뒤에
    # 돌 때 장중가가 종가로 둔갑하는 것을 막는다.
    # 판별은 서버가 주는 값만 쓴다 — 규칙은 in_session() 에 한 곳으로 모았다
    # (wait_close.closed() 도 같은 함수를 쓴다. 두 벌이면 갈린다).
    # (v8 chart meta 에 marketState 는 없다.)
    meta = result.get("meta", {})
    qt = meta.get("regularMarketTime")
    if in_session(meta) and len(s) > 0:
        live_day = pd.to_datetime(qt, unit="s", utc=True).tz_convert(None).normalize()
        if s.index[-1] == live_day:
            print(f"장중 실행 감지 — 진행 중인 {live_day.date()} 봉 제외")
            s = s.iloc[:-1]
    return s


def in_session(meta):
    """[2026-09-04 코드리뷰] 이 응답이 **진행 중인 정규장** 안에서 찍힌 것인가.

    종전 판별은 `regularMarketTime < currentTradingPeriod.regular.end` 하나였다. 그 식은
    **currentTradingPeriod 가 다음 세션으로 넘어간 뒤**에도 참이 된다 — qt 는 오늘 마감에
    굳어 있는데 end 가 내일 마감이 되기 때문이다. 그러면 이미 확정된 마지막 봉을
    「진행 중」으로 오인해 **버린다**(= 그날 전환 신호를 통째로 놓친다).

    실측 2026-09-03: 장 마감 뒤의 ^KS11 은 qt=09-03 09:05Z 인데 start=09-04 00:00Z ·
    end=09-04 06:00Z 였다(418660.KS 도 같다) — 즉 롤오버는 실제로 일어난다.
    QQQ 에서 이 오판이 난 흔적은 아직 없다(08-29 09:22 KST 슬롯이 정상 as_of 08-28).
    그래도 고치는 이유는 **한쪽으로만 틀리기 때문**이다: start 를 넣는 것은 엄격한 조임이라
    「마감」을 「장중」으로 바꾸는 일이 없다(라이브 4종 + 합성 5경우 전수 확인 — 풀림 0건).
    프리마켓도 같은 모양이라 같이 막힌다(전일 종가를 오늘 장중가로 오인하던 경우).

    start 가 없으면 종전 식으로 물러선다 — 판정을 막는 방향으로는 엄격해지지 않는다
    (v137 fail open: 인프라가 부실할 때 신호를 멈추는 것이 가장 나쁘다).
    """
    qt = meta.get("regularMarketTime")
    reg = meta.get("currentTradingPeriod", {}).get("regular", {})
    start, end = reg.get("start"), reg.get("end")
    if not (qt and end):
        return False
    if start is None:
        return qt < end
    return start <= qt < end

def fetch_naver():
    """[v66] Yahoo 가 양쪽 다 죽었을 때의 예비 소스 — 네이버 증권 해외종목 API.
    이력은 캐시(data/qqq.csv)가 들고 있으므로 **최신 확정 종가 한 줄**만 가져와 붙인다.
    규칙(QQQ 미국장 종가)은 그대로다 — 같은 값을 다른 창구에서 읽을 뿐이다.
    안전장치 둘:
      ① marketStatus 가 CLOSE 일 때만 쓴다 (장중가 오염 방지 — Yahoo 쪽 가드와 같은 목적).
      ② 캐시 마지막 날짜보다 새 날짜일 때만 붙인다 (예비 소스가 과거를 덮어쓰지 않게).
    [v71] 네이버는 비수정 종가지만 최신 봉은 수정 종가와 항상 같으므로(조정은 과거에만
    적용) 수정 종가 캐시에 붙여도 일관된다. 예외적으로 Yahoo 가 며칠 죽은 사이 배당락이
    지나면 그 며칠만 최대 배당 1회분(~0.15%p) 오차가 났다가, Yahoo 복구 시 전체 이력을
    다시 받으며 자동 정정된다.
    """
    req = urllib.request.Request(NAVER_SRC, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode("utf-8", "replace"))
    if d.get("marketStatus") != "CLOSE":
        raise RuntimeError(f"네이버 marketStatus={d.get('marketStatus')} — 확정 종가 아님")
    close = float(d["closePriceRaw"])
    # localTradedAt 예: '2026-08-28T16:00:02-04:00' — 앞 10자리가 미국 동부 날짜
    day = pd.Timestamp(str(d["localTradedAt"])[:10])
    cached = load_cached()
    if cached is None:
        raise RuntimeError("캐시가 없어 네이버 한 줄로는 이력을 만들 수 없음")
    if day <= cached.index[-1]:
        raise RuntimeError(f"네이버 종가({day.date()})가 캐시({cached.index[-1].date()})보다 새롭지 않음")
    return pd.Series([close], index=[day], name="Close")


def load_cached():
    if not os.path.exists(CSV_PATH):
        return None
    df = pd.read_csv(CSV_PATH, parse_dates=["Date"]).set_index("Date")["Close"]
    return df.sort_index()


# [v137] 종가 이상치 가드 — 04 §5-8 이 실측한 공백을 메운다.
#   실측: ±10% 종가 오류 200회 중 49회가 신호를 바꿨고 최악 −19.1%. 가드가 없었다.
#   임계값은 실측에서 나온다(임의 임계 금지 — SURVIVAL_MONITOR §11):
#   QQQ 1999~2026 일간 |수익| 최대 16.84%(2001-01-03) · 99.9분위 10.73% · 20% 초과 0일.
BIG_MOVE = 0.10        # 이 이상 움직이면 「대조가 필요한 큰 움직임」
XSRC_TOL = 0.005       # 두 소스가 같은 날 종가에 이 이상 어긋나면 데이터 오류


def sanity_check(px, source):
    """입력 검증 전용 — 전략 파라미터·판정 로직에 일절 관여하지 않는다.

    크기만으로는 「진짜 폭락」과 「데이터 오류」를 구별할 수 없다(둘 다 −10%대가 가능).
    그래서 큰 움직임일 때만 **다른 소스로 대조**한다.

    ★ 실패 방향 규약 (이 함수의 핵심):
      · 인프라 문제(대조 소스 불통·형식 변경)에는 **통과**시킨다 — fail open.
        진짜 폭락일에 대조 소스가 죽었다고 신호를 막으면 04 §5-8 이 실측한
        「닷컴 방어 진입을 놓치면 −96.5%」가 현실이 된다.
      · 막는 것은 **두 소스가 실제로 어긋났을 때**와 **값 자체가 불가능할 때**뿐.
    """
    if px is None or len(px) == 0:
        raise RuntimeError("[가드] 시세가 비었다")
    last = float(px.iloc[-1])
    if not np.isfinite(last) or last <= 0:
        raise RuntimeError(f"[가드] 종가가 불가능한 값이다: {last}")
    if len(px) < 2:
        return
    move = last / float(px.iloc[-2]) - 1
    if abs(move) <= BIG_MOVE:
        return

    day = px.index[-1]
    print(f"[가드] 큰 움직임 감지 {move:+.2%} ({day.date()}) — 다른 소스로 대조한다",
          file=sys.stderr)
    try:
        if source == "naver":
            other = fetch()                      # 야후로 대조
            ref = float(other.loc[day])
            oname = "yahoo"
        else:
            other = fetch_naver()                # 네이버로 대조 (최신 한 줄)
            if other.index[-1] != day:
                print(f"[가드] 대조 소스의 최신일({other.index[-1].date()})이 다르다 "
                      f"— 대조 불가, 통과시킨다", file=sys.stderr)
                return
            ref = float(other.iloc[-1])
            oname = "naver"
    except Exception as e:
        print(f"[가드] 대조 소스 사용 불가({e}) — **통과시킨다**(fail open). "
              f"진짜 폭락일을 막지 않기 위한 규약이다.", file=sys.stderr)
        return

    diff = abs(last / ref - 1)
    if diff > XSRC_TOL:
        raise RuntimeError(
            f"[가드] 두 소스가 어긋난다 — 데이터 오류로 판단해 중단한다. "
            f"{source}={last:.2f} vs {oname}={ref:.2f} (차이 {diff:.2%} > {XSRC_TOL:.1%}). "
            f"수동 확인 후 재실행하라.")
    print(f"[가드] 대조 일치({oname}={ref:.2f}, 차이 {diff:.3%}) — 진짜 움직임이다. 진행",
          file=sys.stderr)


def drawdown(px: pd.Series):
    roll_max = px.rolling(LOOKBACK, min_periods=60).max()
    return (px / roll_max - 1), roll_max


HIST_SHIFT_TOL = 0.05          # %p — 아래 실측에서 정상 0.0002 · 방법론 변경 1.06 이라 그 사이


def history_shift(old_px, new_px):
    """[2026-09-04 코드리뷰] **과거 봉이 소리 없이 다시 쓰이는 것**을 감지한다(막지는 않는다).

    캐시 병합은 `keep="last"` 라 새로 받은 값이 **과거 날짜까지 덮어쓴다.** 그런데
    sanity_check 는 **마지막 봉만** 본다 — 즉 야후가 이력 전체를 이상하게 주면 252일 고점이
    바뀌고 **낙폭이 바뀌고 판정이 바뀌는데** 아무 검사도 걸리지 않는다.

    「과거 값이 바뀌었나」로 재면 못 쓴다 — 실측(qqq.csv 13판본쌍) 매 실행마다 과거
    5,600여 행이 배당 재조정 반올림으로 0.0001% 씩 움직인다. 그래서 **판정이 실제로 쓰는
    낙폭**으로 잰다. 비례 재조정은 종가와 252일 고점을 같은 비율로 밀어 낙폭을 거의 안 바꾼다:
      · 정상 12판본쌍 — 과거 낙폭 최대 변화 **0.000191%p**
      · 방법론 변경 1건(89a6cf6, 종가→수정종가) — **1.056%p**
    5,500배 차이라 문턱 0.05%p 는 평시에 조용하고 의미 있는 변화는 전부 잡는다.

    ★ 막지 않는 이유: v137 fail open. 이력이 이상하다고 신호 갱신을 멈추면 04 §5-8 의
      최악 −96.5%(전환을 놓친 경우)가 현실이 된다. 여기서는 **로그에 크게 남기는 것**까지 한다.
    """
    try:
        common = old_px.index.intersection(new_px.index)[:-1]      # 마지막 봉 제외 = 과거만
        if len(common) < 300:
            return 0.0
        d0 = drawdown(old_px)[0].reindex(common) * 100
        d1 = drawdown(new_px)[0].reindex(common) * 100
        shift = float((d1 - d0).abs().max())
    except Exception as e:                                          # 감시가 갱신을 막지 않는다
        print(f"[경고] 이력 변화 점검 실패({e}) — 갱신은 계속한다", file=sys.stderr)
        return 0.0
    if shift > HIST_SHIFT_TOL:
        worst = (drawdown(new_px)[0].reindex(common) - drawdown(old_px)[0].reindex(common)).abs().idxmax()
        print("=" * 70, file=sys.stderr)
        print(f"[경고] 과거 낙폭이 다시 쓰였다 — 최대 {shift:.3f}%p (문턱 {HIST_SHIFT_TOL}%p, "
              f"가장 큰 날 {worst.date()})", file=sys.stderr)
        print("  평시 값은 0.0002%p 다. 이 크기는 ① 출처의 수정주가 방법론 변경이거나",
              file=sys.stderr)
        print("  ② 이력이 손상된 것이다. 신호는 그대로 갱신했다(v137 fail open) —",
              file=sys.stderr)
        print("  data/qqq.csv 의 이전 커밋과 비교해 확인할 것.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
    return shift

def states(dd: pd.Series, enter: float, exit_: float):
    """전량 전환 상태기계. 낙폭 <= enter -> SCHD, 낙폭 > exit -> QLD."""
    out, cur = [], "QLD"
    for d in dd.values:
        if pd.isna(d):
            out.append(cur); continue
        if cur == "QLD" and d <= enter:
            cur = "SCHD"
        elif cur == "SCHD" and d > exit_:
            cur = "QLD"
        out.append(cur)
    return pd.Series(out, index=dd.index)


def trajectories(px: pd.Series, dd: pd.Series, days=400):
    """각 위기의 고점 이후 낙폭 궤적 + 현재 진행중인 낙폭 궤적"""
    out = {}
    for name, peak in CRISES:
        seg = dd.loc[peak:].iloc[:days]
        if len(seg) > 20:
            out[name] = [round(float(v) * 100, 2) for v in seg.values]
    # 현재 궤적: 최근 252일 고점 이후
    cur_dd = dd.iloc[-1]
    if cur_dd < -0.03:
        rm = px.rolling(LOOKBACK, min_periods=60).max().iloc[-1]
        recent = px.iloc[-LOOKBACK:]
        hits = recent[recent >= rm * 0.9999]
        if len(hits):
            seg = dd.loc[hits.index[-1]:]
            if len(seg) > 3:
                out["현재"] = [round(float(v) * 100, 2) for v in seg.values[:days]]
    return out


def load_stats():
    if not os.path.exists(STATS_PATH):
        print(f"[경고] {STATS_PATH} 없음 — 성과지표 없이 진행", file=sys.stderr)
        return None
    with open(STATS_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # [v66] 예비 사슬: Yahoo query1 → query2 미러 → 네이버 증권 → 캐시.
    # 캐시로 떨어지면 그날 종가는 못 싣는다 — 그 전에 세 번 시도한다.
    px, source = None, None
    for name, fn in [("yahoo",  fetch),
                     ("yahoo2", lambda: fetch(host="query2")),
                     ("naver",  fetch_naver)]:
        try:
            px, source = fn(), name
            break
        except Exception as e:
            print(f"[경고] {name} 실패({e}) — 다음 소스 시도", file=sys.stderr)
    if px is None:
        print("[경고] 모든 소스 실패 — 캐시 사용", file=sys.stderr)
        px = load_cached()
        source = "cache"
        if px is None:
            raise RuntimeError("소스 전부 실패 + 캐시도 없음")

    cached = load_cached()
    if cached is not None:
        px = pd.concat([cached, px])
        px = px[~px.index.duplicated(keep="last")].sort_index()
        history_shift(cached, px)

    # [v137] 이상치 가드 — 반드시 CSV 쓰기 **전**에. 네이버 대조가 옛 캐시를 기준으로
    # 「더 새로운 날인가」를 판정하므로, 캐시를 덮어쓴 뒤엔 대조가 불가능해진다.
    sanity_check(px, source)

    px.rename("Close").to_frame().to_csv(CSV_PATH, index_label="Date")

    now_utc = pd.Timestamp.now("UTC")
    now_kst = now_utc.tz_convert("Asia/Seoul")

    dd, roll_max = drawdown(px)
    d = float(dd.iloc[-1])

    st = {k: states(dd, en, ex) for k, _, en, ex in STRATS}

    strategies = {}
    for k, name, en, ex in STRATS:
        s = st[k]
        last, prev = s.iloc[-1], (s.iloc[-2] if len(s) > 1 else s.iloc[-1])
        line = en if last == "QLD" else ex
        strategies[k] = {
            "key": k,
            "name": name,
            "enter": round(en * 100, 0),
            "exit": round(ex * 100, 0),
            "state": last,
            "prev_state": prev,
            "changed_today": bool(last != prev),
            "next_line": round(line * 100, 0),
            "gap_pp": round(abs(d - line) * 100, 1),
        }

    lo = max(0, len(px) - 12)
    recent = [
        {"d": px.index[i].strftime("%Y-%m-%d"),
         "c": round(float(px.iloc[i]), 2),
         "dd": round(float(dd.iloc[i]) * 100, 2),
         **{k: st[k].iloc[i] for k, _, _, _ in STRATS},
         "s": st["A"].iloc[i]}                       # 구버전 화면 호환
        for i in range(lo, len(px))
    ][::-1]

    dflt = strategies[DEFAULT]
    payload = {
        "as_of": px.index[-1].strftime("%Y-%m-%d"),
        # 화면은 updated_at_iso 를 받아 브라우저에서 한국시간으로 찍는다.
        # updated_at 은 그게 없을 때의 대비(그리고 로그 가독성)용 KST 문자열.
        "updated_at": now_kst.strftime("%Y-%m-%d %H:%M KST"),
        "updated_at_iso": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "close": round(float(px.iloc[-1]), 2),
        "high_252": round(float(roll_max.iloc[-1]), 2),
        "dd": round(d * 100, 2),
        "default": DEFAULT,
        "defensive": DEFENSIVE,
        "risk": RISK,
        "strategies": strategies,
        "recent": recent,
        "stats": load_stats(),
        "trajectories": trajectories(px, dd),
        # --- 구버전 signal.html 호환용 미러 (A 기준) ---
        "state": strategies["A"]["state"],
        "prev_state": strategies["A"]["prev_state"],
        "changed_today": strategies["A"]["changed_today"],
        "next_line": strategies["A"]["next_line"],
        "gap_pp": strategies["A"]["gap_pp"],
        "enter": -16.0,
        "exit": -11.0,
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    line = f"{payload['as_of']}  종가 {payload['close']}  낙폭 {payload['dd']}%"
    for k, name, _, _ in STRATS:
        s = strategies[k]
        line += f"   |  {name} → {s['state']}"
        if s["changed_today"]:
            line += " *** 전환 ***"
    print(line)


if __name__ == "__main__":
    main()
