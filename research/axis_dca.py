# -*- coding: utf-8 -*-
"""
[v47] 적립식에서 다른 전략들이 현행을 능가하는가

사용자 지적: "이전엔 거치식을 전제로 테스트한 경우가 많아서."
맞다. 적립식으로 판정한 축은 변동성가드(v32)·낙폭매수(v40) 둘뿐이다.
RSI 와 이동평균선은 **한 번도 안 해봤다.**

[시험 대상]
  C0  현행 -16/-16                        (기준선)
  C1  규칙 없이 레버리지 정액적립          "그냥 DCA"
  C2  평단가 이하 매수                     평단가보다 쌀 때만 레버리지에 납입
  C3  RSI 과열 익절 / 과매도 매수          RSI(14) >= hi 면 방어, <= lo 면 공격
  C4  20일 이동평균 돌파
  C5  60일 이동평균 돌파
  C6  현금 20~30% 상시 보유 + 급락 추매
  C7  거치식 vs 적립식                     "거치식 금지"가 맞는가

[규약 — 어기면 결과가 거짓이 된다]
  · 모든 지표는 **전일까지의 데이터**로 계산해 당일 체결한다(pos = w.shift(1)).
    RSI·이평선은 shift(1) 을 명시적으로 건다. 안 걸면 미래참조다.
  · 비용 편도 0.1%, 회전율 |Δpos| 비례.
  · 적립: 월초 1단위 x 60개월(ISA 5년) 납입 후 창 끝까지 보유.
  · 판정: 20년 창 분포의 **중앙 · 5분위 · 최악**을 함께 본다(research_kit.dist).

[검산]
  일반 시뮬레이터가 axis_lib.accumulate() 와 **오차 0** 인지 먼저 확인한다.
  엔진을 새로 짜다 체결규약을 어긴 전례가 있다(v30).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
import axis_lib as AX
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import dist, verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PAY_MONTHS = 60          # ISA 5년 납입
K = 2                    # 레버리지 배수


# ================================================================= 지표
def rsi(px, n=14):
    """Wilder RSI. **shift(1) 은 호출부에서 건다** — 여기서는 당일까지의 값."""
    d = pd.Series(px).diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).values


def sma_cross(px, n):
    """종가가 n일 이동평균 위면 1, 아래면 0. 당일까지의 값."""
    s = pd.Series(px)
    m = s.rolling(n, min_periods=n).mean()
    return (s > m).astype(float).fillna(1.0).values


# ================================================================= 시뮬레이터
def dca(D, rk, dfr, wpath, lo, hi, pay=PAY_MONTHS, cost=COST,
        route=None, months=None):
    """월초 1단위 적립. wpath[i] = **그날 들고 있어야 할 위험자산 비중**(이미 지연 반영).

    route(i, R, C, avg) -> True 면 그달 납입금을 위험자산으로, False 면 대기.
                           None 이면 wpath 를 따른다(현행 규약).
    반환 (납입, 평가액 시계열, 위험자산 평단가 시계열)
    """
    R = C = paid = 0.0
    prev = wpath[lo]
    vals, avg_hist = [], []
    cost_basis = 0.0            # 위험자산 취득원가 누계 (평단가용)
    units = 0.0                 # 위험자산 '구좌수' — 가격지수로 환산
    px = np.cumprod(1 + np.nan_to_num(rk))      # 위험자산 가격지수
    for i in range(lo, hi):
        pos = wpath[i]
        if pos != prev:                                  # 비중 변경
            if pos > prev:                               # 방어 -> 공격
                mv = C * (pos - prev) / max(1 - prev, 1e-12)
                C -= mv; R += mv * (1 - cost)
                units += mv * (1 - cost) / px[i]; cost_basis += mv * (1 - cost)
            else:                                        # 공격 -> 방어
                mv = R * (prev - pos) / max(prev, 1e-12)
                R -= mv; C += mv * (1 - cost)
                if units > 0:
                    f = mv / max(R + mv, 1e-12)
                    units *= (1 - f); cost_basis *= (1 - f)
            prev = pos

        R *= (1 + rk[i]); C *= (1 + dfr[i])

        if i > lo and months[i] != months[i - 1] and paid < pay:
            paid += 1.0
            avg = cost_basis / units if units > 1e-12 else 0.0
            if route is None:
                to_risk = (pos >= 1)
            else:
                to_risk = route(i, R, C, avg, px)
            if to_risk:
                R += 1.0; units += 1.0 / px[i]; cost_basis += 1.0
            else:
                C += 1.0
        vals.append(R + C)
        avg_hist.append(cost_basis / units if units > 1e-12 else np.nan)
    return paid, np.array(vals), np.array(avg_hist)


def lag(w):
    """체결규약: 그날 들고 있는 비중은 전일 신호다."""
    return np.r_[w[0], w[:-1]]


# ================================================================= 검산
def selfcheck(D, rk, dfr, months):
    """일반 시뮬레이터가 axis_lib.accumulate() 와 같은가 — 오차 0 이어야 한다."""
    w = rule_w(D['ddv'], -0.16, -0.16)
    n = len(D['idx'])
    lo, hi = 0, n
    paid0, fin0, _ = AX.accumulate(D, K, w, lo, hi)
    # accumulate() 는 납입 제한이 없다 -> pay 를 무한대로 맞춘다
    paid1, v1, _ = dca(D, rk, dfr, lag(w), lo, hi, pay=10 ** 9, months=months)
    err = abs(v1[-1] / fin0 - 1)
    print("  [검산] 일반 시뮬 vs axis_lib.accumulate()")
    print("         납입 %.0f vs %.0f   최종 %,.3f vs %,.3f   상대오차 %.2e"
          .replace('%,', '%') % (paid1, paid0, v1[-1], fin0, err))
    if err > 1e-9 or paid1 != paid0:
        raise SystemExit('  검산 실패 — 엔진이 다르다. 결과를 믿을 수 없다.')
    print("         오차 0 — 같은 엔진이다.\n")


# ================================================================= 후보
def build_candidates(D, rk, dfr):
    px = np.asarray(D['px'], dtype=float)
    ddv = D['ddv']
    n = len(ddv)
    base = rule_w(ddv, -0.16, -0.16)
    r = rsi(px)
    cands = {}

    cands['C0 현행 -16/-16'] = dict(w=lag(base), route=None)
    cands['C1 그냥 레버리지 DCA'] = dict(w=np.ones(n), route=None)

    # C2 평단가 이하 매수 — 규칙은 현행 그대로 쓰되 **납입 배치만** 바꾼다
    def route_avg(i, R, C, avg, px_):
        if avg <= 0:
            return True
        return px_[i] < avg           # 평단가보다 쌀 때만 위험자산에
    cands['C2 평단가 이하 매수'] = dict(w=lag(base), route=route_avg)

    # C3 RSI — 전일까지의 RSI 로 당일 비중 결정
    for hi_, lo_ in ((75, 35), (70, 30), (80, 40)):
        w = np.ones(n); cur = 1.0
        for i in range(n):
            if r[i] >= hi_:
                cur = 0.0
            elif r[i] <= lo_:
                cur = 1.0
            w[i] = cur
        cands['C3 RSI %d/%d' % (hi_, lo_)] = dict(w=lag(w), route=None)

    # C4/C5 이동평균 돌파
    for nn in (20, 60, 200):
        cands['C%s 이평 %d일 돌파' % ('4' if nn == 20 else '5', nn)] = dict(
            w=lag(sma_cross(px, nn)), route=None)

    # C6 현금(방어) 상시 20~30% + 급락 시 추매
    for keep in (0.20, 0.30):
        w = base.copy()
        w = np.where(w >= 1.0, 1.0 - keep, 0.0)          # 공격 때도 keep 만큼 남긴다
        w = np.where((base >= 1.0) & (ddv <= -0.10), 1.0, w)   # 급락 -> 마른자금 투입
        cands['C6 현금 %d%% 상시' % (keep * 100)] = dict(w=lag(w), route=None)

    # 원문은 '**일부** 익절 / 비중 **확대**' 다. 전량 0/1 은 원문보다 가혹하니
    # 부분비중 판도 같이 잰다.
    for hi_, lo_, keep in ((75, 35, 0.5), (70, 30, 0.5)):
        w = np.ones(n); cur = 1.0
        for i in range(n):
            if r[i] >= hi_:
                cur = keep
            elif r[i] <= lo_:
                cur = 1.0
            w[i] = cur
        cands['C3p RSI %d/%d 부분익절' % (hi_, lo_)] = dict(w=lag(w), route=None)

    # RSI/이평을 현행과 **겹쳐서** 쓰는 안 (단독이 아니라 보조)
    w = base.copy()
    w[(base >= 1.0) & (np.r_[r[0], r[:-1]] >= 75)] = 0.0
    cands['C3b 현행 + RSI75 익절'] = dict(w=lag(w), route=None)
    w = base.copy()
    m20 = sma_cross(px, 20)
    w[(base >= 1.0) & (m20 < 0.5)] = 0.0
    cands['C4b 현행 + 20일선 이탈'] = dict(w=lag(w), route=None)
    return cands


# ================================================================= 본체
def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    D = dict(D); D['schdr'] = dfr
    months = pd.Series(idx).dt.to_period('M').values

    print("=" * 92)
    print("적립식 시험 — 월 1단위 x %d개월 납입 후 보유. 구간 %s ~ %s"
          % (PAY_MONTHS, idx[0].date(), idx[-1].date()))
    print("=" * 92)
    selfcheck(D, rk, dfr, months)

    cands = build_candidates(D, rk, dfr)
    L = 20 * 252
    st = list(range(0, N - L, 126))
    print("  20년 창 %d개 · 후보 %d개\n" % (len(st), len(cands)))

    res = {}
    for nm, c in cands.items():
        mult = []
        for s in st:
            paid, v, _ = dca(D, rk, dfr, c['w'], s, s + L,
                             route=c['route'], months=months)
            mult.append(v[-1] / paid)
        res[nm] = np.array(mult)

    b = res['C0 현행 -16/-16']
    db = dist(b, 'C0')
    print("  %-26s%9s%9s%9s%8s%9s%9s%8s"
          % ('후보', '중앙', '5분위', '최악', '승률', '중앙대비', '보유일', '전환'))
    for nm, m in res.items():
        d = dist(m, nm)
        w = cands[nm]['w']
        inmkt = float(np.mean(w)) * 100                 # 위험자산 평균 비중
        sw = int((np.abs(np.diff(w)) > 1e-9).sum())
        wr = '' if nm.startswith('C0') else '%6.0f%%' % ((m > b).mean() * 100)
        rel = '' if nm.startswith('C0') else '%8.0f%%' % ((d['median'] / db['median'] - 1) * 100)
        print("  %-26s%9.1f%9.1f%9.1f%8s%9s%8.0f%%%8d"
              % (nm, d['median'], d['p5'], d['worst'], wr, rel, inmkt, sw))
    print()
    print("  보유일 = 54년 평균 레버리지 비중 · 전환 = 비중이 바뀐 횟수(54년)")

    print()
    print("=" * 92)
    print("판정 — 현행을 이기려면 중앙·좌측꼬리·승률을 **모두** 넘어야 한다")
    print("=" * 92)
    passed = []
    for nm, m in res.items():
        if nm.startswith('C0'):
            continue
        d = dist(m, nm)
        v = verdict(nm, [
            ('20년창 중앙이 현행 이상', d['median'] >= db['median'],
             '%.1f vs %.1f' % (d['median'], db['median'])),
            ('20년창 5분위가 현행 이상', d['p5'] >= db['p5'],
             '%.1f vs %.1f' % (d['p5'], db['p5'])),
            ('승률 > 55%', (m > b).mean() > 0.55, '%.0f%%' % ((m > b).mean() * 100)),
        ])
        if v['adopt']:
            passed.append(nm)
        print(v['text'])
        print()
    print("통과한 후보: %s" % (', '.join(passed) if passed else '없음'))
    return res, b, st, D, rk, dfr, months


def s_lump_vs_dca(D, rk, dfr, months, st, L):
    """'거치식 금지'가 맞는가 — 같은 총액을 한 번에 vs 나눠서."""
    print()
    print("=" * 92)
    print("보론. '거치식 금지'가 맞는가 — 같은 총액 %d단위" % PAY_MONTHS)
    print("=" * 92)
    base = lag(rule_w(D['ddv'], -0.16, -0.16))
    lump, dcav = [], []
    for s in st:
        _, v, _ = dca(D, rk, dfr, base, s, s + L, pay=PAY_MONTHS, months=months)
        dcav.append(v[-1] / PAY_MONTHS)
        # 거치식: 첫 달에 60단위를 한 번에
        R = C = 0.0; prev = base[s]
        first = True
        vals = []
        for i in range(s, s + L):
            pos = base[i]
            if pos != prev:
                if pos >= 1:
                    R += C * (1 - COST); C = 0.0
                else:
                    C += R * (1 - COST); R = 0.0
                prev = pos
            R *= (1 + rk[i]); C *= (1 + dfr[i])
            if first:
                if pos >= 1:
                    R += PAY_MONTHS
                else:
                    C += PAY_MONTHS
                first = False
            vals.append(R + C)
        lump.append(vals[-1] / PAY_MONTHS)
    lump, dcav = np.array(lump), np.array(dcav)
    dl, dd_ = dist(lump, '거치식'), dist(dcav, '적립식')
    print("  %-14s%10s%10s%10s" % ('', '중앙', '5분위', '최악'))
    print("  %-14s%10.1f%10.1f%10.1f" % ('거치식', dl['median'], dl['p5'], dl['worst']))
    print("  %-14s%10.1f%10.1f%10.1f" % ('적립식', dd_['median'], dd_['p5'], dd_['worst']))
    print("\n  거치식이 이긴 창 %.0f%%" % ((lump > dcav).mean() * 100))
    print(verdict('거치식을 피해야 하는가', [
        ('적립식 중앙이 거치식 이상', dd_['median'] >= dl['median'],
         '%.1f vs %.1f' % (dd_['median'], dl['median'])),
        ('적립식 좌측꼬리가 거치식 이상', dd_['p5'] >= dl['p5'],
         '%.1f vs %.1f' % (dd_['p5'], dl['p5'])),
    ])['text'])


if __name__ == '__main__':
    res, b, st, D, rk, dfr, months = main()
    s_lump_vs_dca(D, rk, dfr, months, st, 20 * 252)
