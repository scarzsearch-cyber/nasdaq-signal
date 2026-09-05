# -*- coding: utf-8 -*-
"""
[v80] T4 그림자 추적 심층 고찰 — 전략 해부 + **판정 규약 자체의 품질 검사**

질문 (소유자, 2026-08-29): "그림자 추적 중인 T4 를 더 깊이 고찰·분석하고,
룰을 지키는 한에서 개선 여지를 파악하라."

[룰 준수 선언 — 이 스크립트가 하지 않는 것]
  · 채택안(−16/−16)·freeze.json·oos_log.csv 를 건드리지 않는다.
  · T4 의 사전 고정 파라미터(vt40·th2·창20·룩백 4종)를 **바꾸지 않는다** —
    바꾸면 그림자 기록이 무효다(v69). 파라미터 재탐색(16번째 채굴)도 하지 않는다.
  · 그림자 장부(1행, 2026-08-28~)를 **판단에 쓰지 않는다** — 이 분석의 입력은
    전부 동결 이전(1972~2026-08) 데이터다.

[무엇을 재나 — 4개 축]
  A. 재현·검산   v68 공표수치(T-bill 규약)가 이 엔진에서 재현되는가.
                 장부 구현(deploy/oos_log.py t4_shadow)과 pandas 독립 계산의 동치.
                 종가 원천 이원화(data/qqq.csv vs qqq_us_d.csv)가 신호를 얼마나 가르나.
  B. 기전 해부   노출 분포·회전 분해(게이트 vs 변동성조정)·경계 체류·위기별·
                 연도별 상대기여·lag/비용 민감도.
  C. 판정 규약 전력(power) 분석 — **핵심 신규.** v69 판정 규약(3년+사건≥1회,
                 MDD·Calmar 우위 AND 최종열세 ≤ 교환비)을 1972~2026 의 모든
                 3년 창에 소급 적용하면 판정이 얼마나 자주, 어느 방향으로 나는가.
                 규약의 모호점 2개를 계산으로 잰다:
                   ① 교환비 한도가 −8%(비용 0.1%)인지 −29%(0.2%)인지 미고정
                   ② T4 재구성 시 (1−w) 보완자산이 미고정 (T-bill? SCHD? 바스켓?)
  D. 집행층 개선  신호·기록 열은 불변으로 두고, **판정 재구성 규약**에만 속하는
                 무거래 밴드(목표비중과 보유비중의 차가 밴드 이하면 매매 생략)가
                 한국 실효비용(0.2%)에서 T4 의 알려진 약점(회전 ×3.3)을 줄이는가.

[★ 사전 고정 판정 기준 — 실행 전에 적었다]
  A-1 v68 재현: v68 입력 종료일(2026-08-26)까지 잘라 MDD 오차 ≤ 0.3%p,
                 최종배수 오차 ≤ 5% (당시 실행 코드는 보관되지 않아 잔차 허용)
  A-2 장부 구현 동치: 최근 250 세션에서 t4_shadow() vs pandas 오차 0 (반올림 단위)
  A-3 원천 이원화: 게이트 상태(votes≥2) 불일치 < 2% 일수, |Δw| 중앙 < 0.02
  C-1 한도 해석(−8% vs −29%)에 3년 창 판정 뒤집힘 < 10% 면 "둔감"(모호성 무해)
  C-2 보완자산(T-bill vs SCHD/현금2%)에 판정 뒤집힘 < 10% 면 "둔감"
  C-3 3년 창 승률이 |p−0.5| > 0.15 면 "판별력 있음", 이내면 "동전던지기"
      (하나라도 실패 → 판정 규약 보강 필요 — 단 보강은 소유자 결정 사항으로 보고만)
  D-1 밴드 채택 후보의 조건 (비용 0.2% 기준, band=0 대비):
      최종 ≥ 100% AND Calmar ≥ 100% AND MDD 악화 ≤ 1%p AND 연회전 ≤ 60%
      AND 이웃 밴드에서도 최종·Calmar 조건 성립(고원). 격자 경계 최적은 무효.

[한계 — 미리 적는다]
  · C 는 달러·대용 체인 기준이다. 실제 판정은 원화 실측이지만, 규약의 *구조적*
    성질(한도 해석·보완자산·판별력)은 통화와 무관하게 드러난다.
  · 3년 창들은 서로 겹친다(월 시작 롤링) — 독립 표본이 아니라 **경향**만 말한다.
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_data as H
from axis_lib import rule_w, sim, COST
from research_kit import dist, fmt_dist, sweep, verdict, DesignError

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

LOOKS = (21, 63, 126, 252)     # v68 사전 고정 — 바꾸지 않는다
TH = 2
VT = 0.40
WIN = 20
V68 = dict(t4_final=155279, t4_mdd=-0.534, b_final=168413, b_mdd=-0.631)   # v68 공표 (v210 거래일 정정 전 · 역사 기록)
V68_END = pd.Timestamp('2026-08-26')
# [순회 B09 · 2026-09-05] v210(FRED 빈 가격 행 114개 제거) 뒤 **같은 코드**로 같은 종료일까지 재면
#   T4 254,088(+63.6%) · MDD -50.9% / B 181,018(+7.5%) · MDD -63.1%(동일) — 원인은 자료 하나뿐이다
#   (B08 에서 v203·v209·v210 작업트리로 대조). A-1 은 현행 자료 기준 V210 으로 재현하고 v68 값은 병기한다.
#   자료가 또 바뀌면 이 자리를 의도적으로 갱신하고 이유를 남긴다 — 허용 폭을 조용히 넓히지 마라.
V210 = dict(t4_final=254088, t4_mdd=-0.509, b_final=181018, b_mdd=-0.631)
REF = V210


# ==================================================================== 신호
def t4_weight(px):
    """v68/oos_log.py 와 같은 정의. px 는 전체 체인(클리핑 전) 종가."""
    r = px.pct_change()
    votes = sum((px / px.shift(k) > 1).astype(int) for k in LOOKS)
    rv = 2.0 * r.rolling(WIN).std(ddof=1) * np.sqrt(252)
    w = (VT / rv).clip(upper=1.0).where(votes >= TH, 0.0)
    return w, votes, rv


def build(cash):
    D = H.build_ext(cash=cash)
    r_full, _ = H.qqq_proxy()
    px_full = (1 + r_full).cumprod()
    w, votes, rv = t4_weight(px_full)
    wT = w.reindex(D['idx']).fillna(1.0).values      # 잔여 NaN 없음(체인이 1971 시작)
    wB = rule_w(D['ddv'], -0.16, -0.16)
    return D, wT, wB, votes.reindex(D['idx']), rv.reindex(D['idx'])


def independent_escapes(w, gap=252):
    """1→0 도피 중 직전 *원시 도피*와 gap 거래행 초과인 사건만 남긴다.

    oos_protocol_b.independent()/lookback200.independent()의 동형이다. `last`는
    보관 여부와 무관하게 매 원시 사건에서 갱신해야 한 위기의 연쇄를 중간 사건
    하나 때문에 둘로 쪼개지 않는다.
    """
    esc = np.flatnonzero((np.asarray(w[1:]) == 0) & (np.asarray(w[:-1]) == 1)) + 1
    keep, last = [], None
    for e in esc:
        if last is None or e - last > gap:
            keep.append(int(e))
        last = int(e)
    return keep


def event_bounds(n, event, pre=63, post=252):
    """iloc용 [start, stop): 사건일-pre부터 사건일+post까지 양끝 포함."""
    return max(0, event - pre), min(n, event + post + 1)


def selfcheck_events():
    """kept-only·달력일·끝점 누락이 되살아나지 않는 최소 반례."""
    w = np.ones(656)
    for e in (1, 201, 401, 654):
        w[e] = 0.0
    assert independent_escapes(w) == [1, 654]
    a, b = event_bounds(1000, 100)
    assert (a, b, b - a) == (37, 353, 316)


def met(curve):
    yrs = (curve.index[-1] - curve.index[0]).days / 365.25
    fin = float(curve.iloc[-1] / curve.iloc[0])
    cagr = fin ** (1 / yrs) - 1
    m = float((curve / curve.cummax() - 1).min())
    return dict(final=fin, cagr=cagr, mdd=m, calmar=cagr / abs(m) if m < 0 else np.nan)


# ==================================================================== A
def sec_a(D, wT, wB):
    print('=' * 100)
    print('A. 재현·검산')
    print('=' * 100)
    cT, _ = sim(D, wT)
    cB, _ = sim(D, wB)
    if V68_END not in cT.index or V68_END not in cB.index:
        raise DesignError('v68 기준일 %s 이 재구성 곡선에 없다' % V68_END.date())
    # [코드리뷰 2026-09-04] v68의 고정 숫자와 현재 데이터 끝을 비교하면 자료가
    # 연장될수록 오차가 커져 언젠가 반드시 실패한다. 같은 종료일끼리만 재현한다.
    mT_ref, mB_ref = met(cT.loc[:V68_END]), met(cB.loc[:V68_END])
    ok_mdd = (abs(mT_ref['mdd'] - REF['t4_mdd']) <= 0.003
              and abs(mB_ref['mdd'] - REF['b_mdd']) <= 0.003)
    ok_fin = (abs(mT_ref['final'] / REF['t4_final'] - 1) <= 0.05
              and abs(mB_ref['final'] / REF['b_final'] - 1) <= 0.05)
    print('  v68 기준일 %s까지 같은 창으로 재현 (앵커: v210 자료 기준 · v68 공표값 병기)' % V68_END.date())
    print('  T4  최종 {:,.0f} (v210 기준 {:,d} · v68 {:,d})  MDD {:.1f}% (v210 {:.1f}% · v68 {:.1f}%)  Calmar {:.3f}'.format(
        mT_ref['final'], REF['t4_final'], V68['t4_final'], mT_ref['mdd'] * 100, REF['t4_mdd'] * 100,
        V68['t4_mdd'] * 100, mT_ref['calmar']))
    print('  B   최종 {:,.0f} (v210 기준 {:,d} · v68 {:,d})  MDD {:.1f}% (v210 {:.1f}% · v68 {:.1f}%)  Calmar {:.3f}'.format(
        mB_ref['final'], REF['b_final'], V68['b_final'], mB_ref['mdd'] * 100, REF['b_mdd'] * 100,
        V68['b_mdd'] * 100, mB_ref['calmar']))

    # 장부 구현 vs pandas — 같은 원시 파일(data/qqq.csv)
    _sys.path.insert(0, _os.path.join(_ROOT, 'deploy'))
    from oos_log import t4_shadow
    q = pd.read_csv('data/qqq.csv', parse_dates=['Date']).set_index('Date')['Close']
    wq, vq, rq = t4_weight(q)
    dates = q.index[-250:]
    n_bad = 0
    for d in dates:
        got = t4_shadow(str(d.date()))
        exp = (int(vq.loc[d]), round(float(rq.loc[d]) * 100, 1), round(float(wq.loc[d]), 3))
        if got is None or (got[0], got[1], got[2]) != exp:
            n_bad += 1
    print('  장부 t4_shadow() vs pandas 독립검산: 최근 250세션 불일치 %d건' % n_bad)

    led = pd.read_csv('data/oos_log.csv')
    row = led.iloc[-1]
    lg = t4_shadow(str(row['as_of']))
    print('  장부 최신행 %s: 기록 (%s, %s, %s) vs 재계산 %s'
          % (row['as_of'], row['t4_votes'], row['t4_rv'], row['t4_w'], lg))

    # 원천 이원화 — data/qqq.csv vs 연구용 qqq_us_d.csv (겹침 2000-03~)
    s = H._stooq('qqq_us_d.csv')
    ws, vs2, _ = t4_weight(s)
    ix = wq.dropna().index.intersection(ws.dropna().index)
    gate_q, gate_s = (vq.reindex(ix) >= TH), (vs2.reindex(ix) >= TH)
    dis = float((gate_q != gate_s).mean())
    dw = (wq.reindex(ix) - ws.reindex(ix)).abs()
    d_dw = dist(dw.values, '|Δw| 원천 간')
    print('  원천 이원화: 게이트 불일치 %.2f%% 일수, |Δw| 중앙 %.4f · 최악 %.3f (n=%d)'
          % (dis * 100, d_dw['median'], -d_dw['worst'] if d_dw['worst'] < 0 else d_dw['best'], d_dw['n']))
    # MDD와 최종배수는 따로 보고해 어느 쪽이 깨졌는지 숨기지 않는다.
    checks = [
        ('A-1a MDD 재현 (v210 기준 앵커 · ≤0.3%p)', ok_mdd,
         'MDD 오차 T4 %+.2f%%p · B %+.2f%%p'
         % ((mT_ref['mdd'] - REF['t4_mdd']) * 100,
            (mB_ref['mdd'] - REF['b_mdd']) * 100)),
        ('A-1b 최종배수 재현 (v210 기준 앵커 · 같은 종료일·≤5%)', ok_fin,
         '최종 오차 T4 %+.1f%% · B %+.1f%% (기준일 %s)'
         % ((mT_ref['final'] / REF['t4_final'] - 1) * 100,
            (mB_ref['final'] / REF['b_final'] - 1) * 100, V68_END.date())),
        ('A-2 장부 구현 동치 (불일치 0)', n_bad == 0, '250세션 중 %d건' % n_bad),
        ('A-3 원천 이원화 미미', dis < 0.02 and d_dw['median'] < 0.02,
         '게이트 %.2f%% · |Δw| 중앙 %.4f' % (dis * 100, d_dw['median'])),
    ]
    return checks, cT, cB


# ==================================================================== B
def sec_b(D, wT, wB, votes, rv, cT, cB):
    print()
    print('=' * 100)
    print('B. 기전 해부')
    print('=' * 100)
    idx = D['idx']
    yrs = (idx[-1] - idx[0]).days / 365.25
    v = votes.values
    w = wT
    print('  노출 분포: w=0 %.1f%% · 0<w<1 %.1f%% · w=1 %.1f%% 일수 / 평균 노출 %.2f (B 평균 %.2f)'
          % ((w == 0).mean() * 100, ((w > 0) & (w < 1)).mean() * 100,
             (w == 1).mean() * 100, w.mean(), wB.mean()))
    gate = (w > 0)
    flips = int((gate[1:] != gate[:-1]).sum())
    dwv = np.abs(np.diff(w, prepend=w[0]))
    gate_days = np.r_[False, gate[1:] != gate[:-1]]
    print('  회전: 연 %.1f (B %.1f) — 게이트 전환 기인 %.0f%% · 변동성 조정 기인 %.0f%%'
          % (dwv.sum() / yrs, np.abs(np.diff(wB, prepend=wB[0])).sum() / yrs,
             dwv[gate_days].sum() / dwv.sum() * 100, dwv[~gate_days].sum() / dwv.sum() * 100))
    print('  게이트 전환 %d회 (연 %.1f) · votes==2 경계 체류 %.1f%% 일수'
          % (flips, flips / yrs, (v == TH).mean() * 100))

    crises = [('1987 폭락', '1987-08-01', '1988-12-31'),
              ('닷컴', '2000-03-01', '2003-10-01'),
              ('2008 금융위기', '2007-10-01', '2009-12-31'),
              ('코로나', '2020-02-01', '2020-12-31'),
              ('2022 긴축', '2021-11-01', '2023-06-30')]
    print('  위기별 구간 내 MDD (T4 vs B):')
    for nm, a, b in crises:
        sT, sB = cT.loc[a:b], cB.loc[a:b]
        mT = (sT / sT.cummax() - 1).min()
        mB = (sB / sB.cummax() - 1).min()
        tag = 'T4 우위' if mT > mB else 'B 우위'
        print('    %-12s T4 %6.1f%%  vs  B %6.1f%%   [%s]' % (nm, mT * 100, mB * 100, tag))

    rel = np.log(cT.values) - np.log(cB.values)
    yearly = pd.Series(rel, index=idx).groupby(idx.year).last().diff()
    yearly.iloc[0] = pd.Series(rel, index=idx).groupby(idx.year).last().iloc[0]
    top = yearly.sort_values()
    print('  연도별 로그 상대기여(T4−B): 최악 %s / 최선 %s'
          % (' · '.join('%d %.2f' % (y, x) for y, x in top.head(3).items()),
             ' · '.join('%d %+.2f' % (y, x) for y, x in top.tail(3).items())))

    # --- 기전 직접 측정: B 가 도피하는 날, T4 는 이미 줄여 놓았나 ---------------
    # 공표 부속서와 OOS 관문의 계약: 직전 원시 도피와 252 **거래행** 초과.
    # 2026-09-04 교차검증에서 calendar-day 사본과 kept-only 사본을 모두 제거했다.
    keep = independent_escapes(wB)
    at_esc = np.array([w[e] for e in keep])
    pre10 = np.array([w[max(0, e - 10):e].mean() for e in keep])
    d_at = dist(at_esc, 'B도피일 T4 노출')
    print('  기전 직접 측정 — 독립 도피 사건 %d회: B 도피일의 T4 노출 %s'
          % (len(keep), fmt_dist(d_at)))
    print('    직전 10일 평균 노출 중앙 %.2f · 도피일 노출<0.7 인 사건 %d/%d (%.0f%%)'
          % (float(np.median(pre10)), int((at_esc < 0.7).sum()), len(keep),
             (at_esc < 0.7).mean() * 100))
    ev_rows = []
    for e in keep:
        a, b = event_bounds(len(idx), e)
        sT = cT.iloc[a:b]; sB = cB.iloc[a:b]
        mT_ = float((sT / sT.cummax() - 1).min()); mB_ = float((sB / sB.cummax() - 1).min())
        ev_rows.append(mT_ > mB_)
    print('    사건창(도피−63d~+252d) MDD 에서 T4 우위: %d/%d (%.0f%%)'
          % (sum(ev_rows), len(ev_rows), np.mean(ev_rows) * 100))
    # 부속서(M1·M2) 기저율 — 문턱 민감도까지 함께 (사전 등록용 수치)
    m2 = np.array(ev_rows)
    for th, label in ((0.7, '공식'), (0.5, '민감도')):
        m1 = pre10 < th
        print('    [부속서 %s] M1(직전10일 평균<%.1f) %d/%d (%.0f%%) · M1∧M2 %d/%d (%.0f%%)'
              % (label, th, int(m1.sum()), len(keep), m1.mean() * 100,
                  int((m1 & m2).sum()), len(keep), (m1 & m2).mean() * 100))
    print('    [부속서] M1·M2 둘 다 실패: %d/%d (%.0f%%)'
          % (int(((pre10 >= 0.7) & ~m2).sum()), len(keep), ((pre10 >= 0.7) & ~m2).mean() * 100))

    for lag in (1, 2, 3):
        a, _ = sim(D, wT, lag=lag)
        b, _ = sim(D, wB, lag=lag)
        ma, mb = met(a), met(b)
        print('  lag={}: T4 {:,.0f} (MDD {:.1f}%) vs B {:,.0f} (MDD {:.1f}%)'.format(
            lag, ma['final'], ma['mdd'] * 100, mb['final'], mb['mdd'] * 100))
    for c in (0.001, 0.002, 0.003):
        a, _ = sim(D, wT, cost=c)
        b, _ = sim(D, wB, cost=c)
        print('  편도 {:.1f}%: T4 {:,.0f} vs B {:,.0f} (격차 {:+.0f}%)'.format(
            c * 100, a.iloc[-1], b.iloc[-1], (a.iloc[-1] / b.iloc[-1] - 1) * 100))


# ==================================================================== C
def window_stats(curve_net_log, curve, starts, L):
    """롤링 창의 (최종수익, MDD, Calmar). curve_net_log = log누적, curve = pd.Series."""
    out = []
    cv = curve.values
    for a in starts:
        b = a + L
        fin = float(np.exp(curve_net_log[b - 1] - (curve_net_log[a - 1] if a else 0.0)))
        seg = cv[a:b]
        m = float((seg / np.maximum.accumulate(seg) - 1).min())
        yrs = L / 252.0
        cagr = fin ** (1 / yrs) - 1
        out.append((fin, m, cagr / abs(m) if m < 0 else np.nan))
    return np.array(out)


def sec_c(D, wT, wB):
    print()
    print('=' * 100)
    print('C. 판정 규약 전력 분석 — v69 규약을 과거 3년 창에 소급 적용하면?')
    print('=' * 100)
    idx = D['idx']
    n = len(idx)
    res = {}
    for cash, label in (('tbill', 'T-bill 보완'), ('fixed2', 'SCHD/현금2% 보완')):
        Dc = D if cash == 'tbill' else H.build_ext(cash='fixed2')
        cT, _ = sim(Dc, wT)
        cB, _ = sim(Dc, wB)
        lgT, lgB = np.log(cT.values), np.log(cB.values)
        res[cash] = (cT, cB, lgT, lgB)

    ddv = D['ddv']
    for L, lab in ((756, '3년'), (1260, '5년')):
        starts = np.arange(1, n - L, 21)
        has_ev = np.array([bool((ddv[a:a + L] <= -0.16).any()) for a in starts])
        st = starts[has_ev]
        print('\n  [%s 창] 전체 %d개 중 사건(dd≤−16%%) 포함 %d개 (%.0f%%)'
              % (lab, len(starts), len(st), has_ev.mean() * 100))
        verd = {}
        for cash, clab in (('tbill', 'T-bill 보완'), ('fixed2', 'SCHD/현금2% 보완')):
            cT, cB, lgT, lgB = res[cash]
            sT = window_stats(lgT, cT, st, L)
            sB = window_stats(lgB, cB, st, L)
            risk_ok = (sT[:, 1] > sB[:, 1]) & (sT[:, 2] > sB[:, 2])
            fr = sT[:, 0] / sB[:, 0] - 1
            win_soft = risk_ok & (fr >= -0.29)
            win_hard = risk_ok & (fr >= -0.08)
            verd[cash] = (win_soft, win_hard, fr, risk_ok)
            d_fr = dist(fr, '최종수익 상대')
            print('    %-16s 위험우위(MDD·Calmar 둘다) %.0f%% | 승(−29%% 한도) %.0f%% | 승(−8%%) %.0f%%'
                  % (clab, risk_ok.mean() * 100, win_soft.mean() * 100, win_hard.mean() * 100))
            print('      수익격차 분포: %s' % fmt_dist(d_fr, pct=True))
        allowed = (1 - 0.29) ** (L / 252 / 54.55) - 1      # 교환비 연율화 시의 한도
        ws0, wh0, fr0, rk0 = verd['tbill']
        print('    참조 — 한도를 연율화(−0.63%%/yr → %s 누적 %.1f%%)하면 승 %.0f%%'
              % (lab, allowed * 100, (rk0 & (fr0 >= allowed)).mean() * 100))
        deep = np.array([bool((ddv[a:a + L] <= -0.30).any()) for a in st])
        if deep.any():
            ws0, wh0, fr0, rk0 = verd['tbill']
            print('    대형 위기(dd≤−30%%) 창 %d개 한정: 위험우위 %.0f%% | 승(−29%%) %.0f%%'
                  % (int(deep.sum()), rk0[deep].mean() * 100, ws0[deep].mean() * 100))
        flip_bound = float((verd['tbill'][0] != verd['tbill'][1]).mean())
        flip_asset = float((verd['tbill'][0] != verd['fixed2'][0]).mean())
        if L == 756:
            ws, wh, fr, rk = verd['tbill']
            c3 = dict(flip_bound=flip_bound, flip_asset=flip_asset,
                      win=float(ws.mean()), win_hard=float(wh.mean()),
                      risk=float(rk.mean()), n=len(st))
        print('    한도 해석(−8 vs −29)에 판정 뒤집힘: %.0f%% | 보완자산에 뒤집힘: %.0f%%'
              % (flip_bound * 100, flip_asset * 100))

    checks = [
        ('C-1 한도 해석에 둔감 (<10%)', c3['flip_bound'] < 0.10,
         '뒤집힘 %.0f%% (n=%d)' % (c3['flip_bound'] * 100, c3['n'])),
        ('C-2 보완자산에 둔감 (<10%)', c3['flip_asset'] < 0.10,
         '뒤집힘 %.0f%%' % (c3['flip_asset'] * 100)),
        ('C-3 3년 판정 판별력 (|p−.5|>.15)', abs(c3['win'] - 0.5) > 0.15,
         '승률 %.0f%% (−29%% 한도) / %.0f%% (−8%%)' % (c3['win'] * 100, c3['win_hard'] * 100)),
    ]
    return checks


# ==================================================================== D
def band_curve(D, wT, band, cost, every=1):
    """무거래 밴드 집행: |목표−보유| > band 일 때만(그리고 every일마다 검사) 보유를 목표로."""
    idx = D['idx']
    rk, dfr = D['qldr'], D['schdr']
    n = len(idx)
    pos = np.empty(n)
    h = wT[0]
    for i in range(n):
        t = wT[i - 1] if i else wT[0]           # lag=1
        if i % every == 0 and abs(t - h) > band:
            h = t
        pos[i] = h
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr)
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    curve = pd.Series(np.cumprod((1 + r) * (1 - cost * turn)), index=idx)
    yrs = (idx[-1] - idx[0]).days / 365.25
    return curve, float(turn.sum() / yrs)


def sec_d(D, wT):
    print()
    print('=' * 100)
    print('D. 집행층 개선 — 무거래 밴드 (신호·기록 열 불변, 판정 재구성 규약만)')
    print('=' * 100)
    bands = [0.0, 0.025, 0.05, 0.10, 0.15, 0.20]
    tabs = {}
    for cost in (0.001, 0.002):
        def f(band, _cost=cost):
            c, tw = band_curve(D, wT, band, _cost)
            m = met(c)
            m['turn'] = tw
            return m
        r = sweep(f, {'band': bands}, metric='calmar', edge='warn')
        tabs[cost] = r['table']
        print('\n  편도 %.1f%% (경계축: %s · 고원 %s):' % (cost * 100, r['edge_axes'], r['plateau']))
        t = r['table']
        base = t[t['band'] == 0.0].iloc[0]
        for _, x in t.iterrows():
            print('    band {:5.1f}%  최종 {:>9,.0f} ({:+5.1f}%)  MDD {:6.1f}%  Calmar {:.3f}  연회전 {:4.1f}'.format(
                x['band'] * 100, x['final'], (x['final'] / base['final'] - 1) * 100,
                x['mdd'] * 100, x['calmar'], x['turn']))
    # 주간 검사 참조
    c5, t5 = band_curve(D, wT, 0.0, 0.002, every=5)
    m5 = met(c5)
    print('  참조: 주1회 재조정(밴드0, 0.2%)  최종 {:,.0f}  MDD {:.1f}%  연회전 {:.1f}'.format(
        m5['final'], m5['mdd'] * 100, t5))

    # ★ 사전 기준 D-1 적용 (비용 0.2%)
    t = tabs[0.002]
    base = t[t['band'] == 0.0].iloc[0]
    ok_bands = []
    for i, x in t.iterrows():
        if x['band'] == 0.0:
            continue
        if (x['final'] >= base['final'] and x['calmar'] >= base['calmar']
                and x['mdd'] >= base['mdd'] - 0.01 and x['turn'] <= base['turn'] * 0.6):
            ok_bands.append(x['band'])
    # [코드리뷰 2026-09-04] 세 가지를 바로잡는다.
    #  ① `0 < k` 가 인덱스 0 을 제외해 가장 낮은 후보 밴드는 **위쪽 이웃만** 검사됐다.
    #     docstring 41행의 사전등록은 「이웃 밴드에서도」이므로 양쪽을 본다(0 <= k).
    #  ② 이웃 집합이 비면 `all([]) == True` 라 **아무것도 검사하지 않고** 고원이 됐다.
    #     이웃이 없으면 고원을 주장할 수 없다 — False 로 둔다.
    #  ③ 비교가 `base * 0.97` 이었는데 사전등록은 「최종·Calmar 조건 성립」(= >= base)이다.
    #     등록 뒤에 들어간 3% 완화라 되돌린다.
    plateau_ok = False
    pick = None
    for b in ok_bands:
        j = bands.index(b)
        nb = [bands[k] for k in (j - 1, j + 1) if 0 <= k < len(bands)]
        good = bool(nb) and all(
            float(t[t['band'] == q]['final'].iloc[0]) >= base['final']
            and float(t[t['band'] == q]['calmar'].iloc[0]) >= base['calmar']
            for q in nb)
        if good:
            plateau_ok, pick = True, b
            break
    # [코드리뷰 2026-09-04] ★ D-1 은 자료가 정한 기각이 아니다. 회전 조건이
    #   `turn <= base*0.6` 인데, 같은 실행의 sec_b 가 인쇄하듯 T4 회전의 **81%가 0<->1
    #   게이트 전환**(크기 1.0)이라 어떤 밴드로도 억제되지 않는다. 사전등록 격자 끝
    #   (band=0.20)에서도 회전이 base 의 86% 이고, 0.005~1.000 을 199칸 전수 스캔해도
    #   네 조건 동시 충족은 0개다(회전 조건만 처음 만족하는 0.930 에서 Calmar 가 미달).
    #   즉 통과할 입력이 존재하지 않는 관문이다(CLAUDE.md §-1 ⑤). 그 사실을 인쇄한다.
    tmin = float(t['turn'].min())
    print('  [진단] 회전 하한 %.2f (요구 %.2f = base %.2f x0.6) — 밴드로 억제 못 하는 '
          '게이트 전환이 회전의 대부분이라 이 관문은 통과할 입력이 없다.'
          % (tmin, base['turn'] * 0.6, base['turn']))
    checks = [('D-1 밴드 개선 존재 (0.2% 비용·고원)', bool(ok_bands) and plateau_ok,
               '조건 충족 밴드 %s · 대표 %s'
               % (['%.1f%%' % (b * 100) for b in ok_bands], ('%.1f%%' % (pick * 100)) if pick else '-'))]
    return checks


# ==================================================================== main
def main():
    selfcheck_events()
    D, wT, wB, votes, rv = build('tbill')
    ck_a, cT, cB = sec_a(D, wT, wB)
    sec_b(D, wT, wB, votes, rv, cT, cB)
    ck_c = sec_c(D, wT, wB)
    ck_d = sec_d(D, wT)

    print()
    print('=' * 100)
    v1 = verdict('T4 그림자 — 구현·기록 건전성', ck_a)
    print(v1['text'])
    print()
    v2 = verdict('v69 판정 규약 — 이대로 충분한가', ck_c)
    print(v2['text'])
    print()
    v3 = verdict('집행층 개선(무거래 밴드) — 후보가 있는가', ck_d)
    print(v3['text'])


if __name__ == '__main__':
    main()
