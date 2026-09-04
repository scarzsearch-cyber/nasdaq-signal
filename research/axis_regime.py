# -*- coding: utf-8 -*-
"""
[v42] 국면 적응 — 평시엔 공격적 규칙, 옛날식 폭락 조짐이면 -16/-16 으로 후퇴

사용자 제안: "매 순간 최적값(-23%/-11%)을 찾는 건 미래 예측이라 불가능하지만,
**-16/-16 으로 넘어가는 것**은 가능하지 않나?"

맞는 지적이다. 최적값 예측은 불가능해도 **국면 판정**은 관측만으로 된다.
겹치는 10년 창에서 최적 진입선이 -10% -> -23% -> -16% -> -23% 로 계속 움직였고
(v41/v42 §1), 어느 시대 최적값도 다음 시대엔 100위권으로 밀렸다.
그렇다면 **국면을 읽어 규칙을 바꾸는** 메타규칙이 있을 수 있다.

[핵심 제약 — 미래참조 금지]
  국면 판정은 **그날까지 관측된 것**만 쓴다. 확장창·후행 통계만 허용.
  research_kit 의 mdd/dist/verdict 로 판정하고, 시점별 재계산으로 검산한다.

[시험할 메타규칙]
  M0  현행          항상 -16/-16
  M1  후행성과 선택   최근 K년에 가장 좋았던 규칙을 다음 해에 쓴다
  M2  도피기간 감지   공격적 규칙으로 시작. 이번 도피가 D일 넘으면 -16/-16 으로 후퇴
  M3  변동성 국면     후행 변동성이 확장창 상위면 보수, 아니면 공격
  M4  회복속도 기억   최근 위기들의 회복이 느렸으면 보수

[이미 아는 것 — 반복하지 말 것]
  v32: 파라미터를 '고르면' 못박은 것보다 나빴다(고정 8/9 vs 선택 5/9).
       M1 이 그 함정에 정확히 해당한다. 그래도 이번엔 '규칙 선택'이라 다시 잰다.
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import dist, verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CONS = (-0.16, -0.16)                 # 보수 — 후퇴 지점
AGGR = (-0.23, -0.21)                 # 공격 — 현대 구간 최적 근방
POOL = [(-0.11, -0.11), (-0.16, -0.16), (-0.23, -0.21)]


def build():
    D = DF.build('chain')
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, D['idx'])
    return D, defr


def curve(D, defr, w):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * D['qldr'] + (1 - pos) * defr)
    r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - COST * t))


def state_machine(ddq, pick):
    """pick[i] = 그날 적용할 (enter, exit). 상태는 이어서 간다(전량 전환 규약)."""
    n = len(ddq)
    w = np.empty(n)
    cur = 1.0
    for i in range(n):
        e, x = pick[i]
        if cur >= 1.0:
            if ddq[i] <= e:
                cur = 0.0
        else:
            if ddq[i] <= e:
                cur = 0.0
            elif ddq[i] > x:
                cur = 1.0
        w[i] = cur
    return w


# ------------------------------------------------------------------ M1
def m1_trailing(D, defr, ddq, idx, look_yrs=10):
    """최근 look_yrs 성적이 가장 좋았던 규칙을 다음 1년간 쓴다. 미래참조 없음."""
    n = len(idx)
    logs = {}
    for c in POOL:
        w = rule_w(ddq, c[0], c[1])
        pos = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(pos * D['qldr'] + (1 - pos) * defr)
        r[0] = 0.0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        logs[c] = np.log((1 + r) * (1 - COST * t))
    L = look_yrs * 252
    pick = [CONS] * n
    yr = pd.Series(idx).dt.year.values
    cur = CONS
    for i in range(n):
        if i >= L and (i == L or yr[i] != yr[i - 1]):        # 매년 초 재선택
            cur = max(POOL, key=lambda c: logs[c][i - L:i].sum())
        pick[i] = cur
    return state_machine(ddq, pick), pick


# ------------------------------------------------------------------ M2
def m2_duration(ddq, days=63, stay_yrs=0):
    """공격으로 시작. **이번 도피가 days 를 넘으면** 그때부터 보수로 후퇴.
    stay_yrs > 0 이면 후퇴 후 그만큼 보수를 유지한다."""
    n = len(ddq)
    w = np.empty(n)
    cur = 1.0
    since = 0
    cons_until = -1
    for i in range(n):
        conservative = (i <= cons_until)
        if cur < 1.0:
            since += 1
            if since > days and not conservative:
                conservative = True
                cons_until = i + int(stay_yrs * 252)
        e, x = CONS if conservative else AGGR
        if cur >= 1.0:
            if ddq[i] <= e:
                cur = 0.0; since = 0
        else:
            if ddq[i] <= e:
                cur = 0.0
            elif ddq[i] > x:
                cur = 1.0; since = 0
        w[i] = cur
    return w


# ------------------------------------------------------------------ M3
def m3_vol(D, ddq, idx, q=0.70, win=756):
    """후행 변동성이 **확장창 상위 q** 면 보수, 아니면 공격."""
    px = D['px']
    rv = px.pct_change().rolling(252, min_periods=252).std()
    s = pd.Series(rv.values).reset_index(drop=True)
    thr = s.expanding(min_periods=win).quantile(q).shift(1).values
    hi = np.nan_to_num(s.values, nan=0) >= np.nan_to_num(thr, nan=1e9)
    pick = [CONS if h else AGGR for h in hi]
    return state_machine(ddq, pick), hi


# ------------------------------------------------------------------ M4
def m4_memory(ddq, idx, k=3, slow=126):
    """최근 k 번의 도피 중 **평균 지속일이 slow 이상**이면 보수."""
    n = len(ddq)
    w = np.empty(n)
    cur = 1.0
    since = 0
    hist = []
    pick = []
    for i in range(n):
        recent = hist[-k:]
        conservative = (len(recent) >= k and np.mean(recent) >= slow)
        e, x = CONS if conservative else AGGR
        pick.append(conservative)
        if cur >= 1.0:
            if ddq[i] <= e:
                cur = 0.0; since = 1
        else:
            since += 1
            if ddq[i] <= e:
                pass
            elif ddq[i] > x:
                cur = 1.0; hist.append(since); since = 0
        w[i] = cur
    return w, np.array(pick)


def main():
    D, defr = build()
    idx, ddq, N = D['idx'], D['ddv'], len(D['idx'])
    # win 인자가 실제 워밍업을 바꾸는지 확인한다. 종전에는 756 하드코딩이라
    # win=1과 win=N+1이 완전히 같은 경로를 냈다.
    _, h_short = m3_vol(D, ddq, idx, win=1)
    _, h_long = m3_vol(D, ddq, idx, win=N + 1)
    assert not np.array_equal(h_short, h_long) and not h_long.any()
    print(f"구간 {idx[0].date()} ~ {idx[-1].date()}")
    print(f"보수 {CONS[0]*100:.0f}/{CONS[1]*100:.0f}  ·  공격 {AGGR[0]*100:.0f}/{AGGR[1]*100:.0f}\n")

    cases = {}
    cases['M0 현행 -16/-16'] = rule_w(ddq, *CONS)
    cases['(참고) 공격 -23/-21'] = rule_w(ddq, *AGGR)
    w1, pick1 = m1_trailing(D, defr, ddq, idx)
    cases['M1 후행성과 선택'] = w1
    for d in (42, 63, 126):
        cases[f'M2 도피>{d}일 후퇴'] = m2_duration(ddq, d)
    cases['M2 도피>63일 +3년유지'] = m2_duration(ddq, 63, 3)
    w3, hi = m3_vol(D, ddq, idx)
    cases['M3 변동성 국면'] = w3
    w4, p4 = m4_memory(ddq, idx)
    cases['M4 회복속도 기억'] = w4

    L = 20 * 252
    st = list(range(0, N - L, 63))
    base = curve(D, defr, cases['M0 현행 -16/-16'])
    rb = np.array([base[s + L] / base[s] for s in st])
    db = dist(rb, 'M0')
    print(f"  {'메타규칙':<22}{'최종배수':>12}{'20년중앙':>10}{'20년5분위':>11}{'MDD':>9}{'승률':>8}")
    out = {}
    for nm, w in cases.items():
        c = curve(D, defr, w)
        rr = np.array([c[s + L] / c[s] for s in st])
        m = (c / np.maximum.accumulate(c) - 1).min()
        d = dist(rr, nm)
        wins = (rr > rb).mean() if nm != 'M0 현행 -16/-16' else np.nan
        out[nm] = (c, rr, d, m)
        ws = f"{wins*100:7.0f}%" if not np.isnan(wins) else f"{'-':>8}"
        print(f"  {nm:<22}{c[-1]:>12,.0f}{d['median']:>10.1f}{d['p5']:>11.1f}{m*100:>8.1f}%{ws}")

    print("\n" + "=" * 78)
    print("판정 — 현행을 이기려면 좌측꼬리를 지켜야 한다")
    print("=" * 78)
    for nm in cases:
        if nm.startswith('M0') or nm.startswith('(참고)'):
            continue
        c, rr, d, m = out[nm]
        wins = float((rr > rb).mean())
        v = verdict(nm, [
            ('20년 5분위가 현행 이상', d['p5'] >= db['p5'], f"{d['p5']:.1f} vs {db['p5']:.1f}"),
            ('20년 중앙이 현행 이상', d['median'] >= db['median'], f"{d['median']:.1f} vs {db['median']:.1f}"),
            ('20년창 승률 > 55%', wins > 0.55, f"{wins*100:.0f}%"),
            ('MDD 비악화', m >= out['M0 현행 -16/-16'][3],
             f"{m*100:.1f}% vs {out['M0 현행 -16/-16'][3]*100:.1f}%"),
        ])
        print(v['text']); print()


if __name__ == '__main__':
    main()
