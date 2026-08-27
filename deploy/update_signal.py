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
SRC = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ"
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


def fetch():
    period1 = int(datetime.datetime(1999, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    period2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = f"{SRC}?period1={period1}&period2={period2}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.loads(r.read().decode("utf-8", "replace"))
    result = raw["chart"]["result"][0]
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    s = pd.Series(closes, index=idx, name="Close").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_cached():
    if not os.path.exists(CSV_PATH):
        return None
    df = pd.read_csv(CSV_PATH, parse_dates=["Date"]).set_index("Date")["Close"]
    return df.sort_index()


def drawdown(px: pd.Series):
    roll_max = px.rolling(LOOKBACK, min_periods=60).max()
    return (px / roll_max - 1), roll_max


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
    try:
        px = fetch()
        source = "yahoo"
    except Exception as e:
        print(f"[경고] 다운로드 실패({e}) — 캐시 사용", file=sys.stderr)
        px = load_cached()
        source = "cache"
        if px is None:
            raise

    cached = load_cached()
    if cached is not None:
        px = pd.concat([cached, px])
        px = px[~px.index.duplicated(keep="last")].sort_index()

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
