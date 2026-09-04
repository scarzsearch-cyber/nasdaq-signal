# -*- coding: utf-8 -*-
"""
[v52] VIX 를 '매일 게이트'가 아니라 '도피 시작 시 한 번 읽는 상태변수'로

v51 이 밝힌 것: VIX 는 데드캣을 **실제로 구별한다**(2000 닷컴 -41.1%p -> +0.6%p).
못 쓴 이유는 신호가 틀려서가 아니라 **매일 게이트로 쓰니 떨려서다**(전환 80 -> 218회).

그래서 마지막 변형: **상태를 한 번만 분류하고, 그 도피 구간 내내 유지한다.**
신호가 매일 뒤집히지 않으므로 떨림이 구조적으로 불가능하다.

[후보]
  S1  진입 시 VIX 극단(패닉) -> 조기복귀 허용 / 평온 -> 현행 유지
        가설: 패닉성 급락은 V자로 튄다. 조용한 하락은 구조적이라 천천히 간다.
  S2  S1 의 반대 (패닉 -> 늦게, 평온 -> 현행)
        가설의 반증용. 방향을 모르면 둘 다 재야 한다.
  S3  진입 시 VIX 극단 -> 복귀선 -11% 로 완화 / 아니면 -16%
  S4  도피 중 VIX 가 **진입시점 대비 X% 하락**하면 그때 한 번 복귀 (래치)
        하루 등락이 아니라 '정점 통과'를 한 번만 판정한다.

[규약]
  · 진입은 현행 -16% 그대로. 복귀만 바꾼다.
  · VIX 는 1990-01 부터. 기준선도 **같은 구간으로 잘라** 비교한다.
  · 4블록은 3/4 만 가능 -> **'4블록 검증 불가'로 표기**한다(v51 §11).
  · 상태는 도피 진입일에 확정하고 그 도피가 끝날 때까지 바꾸지 않는다.
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

K = 2
ENTER = -0.16
Y0 = 1990


def load(path, idx):
    d = pd.read_csv(path)
    c = [x for x in d.columns if x.lower() in ('date', 'observation_date')][0]
    v = [x for x in d.columns if x.lower() in ('close', 'adj close', 'value')][0]
    s = pd.Series(pd.to_numeric(d[v], errors='coerce').values,
                  index=pd.to_datetime(d[c])).sort_index().dropna()
    s = s[~s.index.duplicated(keep='last')]
    o = s.reindex(idx, method='ffill')          # ffill 만. bfill 은 미래참조
    o[idx < s.index[0]] = np.nan
    return o.values


def curve(rk, dfr, w, cost=COST):
    pos = np.r_[w[0], w[:-1]]
    r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    return np.cumprod((1 + r) * (1 - cost * t)), pos


def state_rule(ddv, vix, vz, mode, dd20=None, drop=0.30, panic_z=1.5):
    """도피 진입일에 VIX 상태를 **한 번** 읽고, 그 도피 내내 유지한다.

    [v52 정정] 초판은 'ddv > ENTER 면 무조건 복귀'를 먼저 처리해서
    **복귀를 늦추는 변형(S2/S3)이 발동조차 못 했다.** 기준선과 수치가
    완전히 같게 나와서 발각됐다. 여기서는 복귀 조건을 상태가 **전부** 정한다.
    """
    n = len(ddv)
    w = np.empty(n)
    cur = 1.0
    panic = False           # 이번 도피의 상태 (진입 시 확정, 안 바뀐다)
    v_at = np.nan
    for i in range(n):
        just_entered = False
        if ddv[i] <= ENTER and cur >= 1.0:
            # **새 도피 시작 — 여기서만 읽는다**
            panic = bool(np.nan_to_num(vz[i], nan=0.0) > panic_z)
            v_at = vix[i]
            cur = 0.0
            just_entered = True
        if cur < 1.0:
            back = False
            if mode == 'S1':
                # 패닉이면 조기복귀 허용, 평온이면 현행
                back = ((ddv[i] > ENTER) or
                        (not just_entered and panic and dd20 is not None and dd20[i] > 0.03))
            elif mode == 'S2':
                # 반증용 — 패닉이면 **늦게**(-11%), 평온이면 현행(-16%)
                back = (ddv[i] > -0.11) if panic else (ddv[i] > ENTER)
            elif mode == 'S3':
                # 평온(=조용한 구조적 하락)이면 늦게, 패닉이면 현행
                back = (ddv[i] > ENTER) if panic else (ddv[i] > -0.11)
            elif mode == 'S4':
                # VIX 정점 통과를 **한 번만** 판정 (래치)
                back = (ddv[i] > ENTER) and (
                    (not panic) or (np.isfinite(v_at) and vix[i] < v_at * (1 - drop)))
            if back:
                cur = 1.0
        w[i] = cur
    return w


def selfcheck_state_rule():
    """S1 조기복귀가 −16% 아래에서도 실제 발동하고, 평온형은 발동하지 않는다."""
    d = np.array([-0.10, -0.17, -0.18, -0.15])
    v = np.array([20., 40., 30., 25.])
    rec = np.array([0., 0., 0.04, 0.04])
    panic = state_rule(d, v, np.array([0., 2., 2., 2.]), 'S1', rec)
    calm = state_rule(d, v, np.zeros(4), 'S1', rec)
    assert panic[1] == 0 and panic[2] == 1 and calm[2] == 0


def main():
    selfcheck_state_rule()
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    ddv = np.asarray(D['ddv'], float)
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]
    L = 20 * 252

    vix = load('data/hist/yahoo_VIX.csv', idx)
    vz = ((vix - pd.Series(vix).rolling(756, min_periods=252).mean().values)
          / pd.Series(vix).rolling(756, min_periods=252).std().values)
    dd20 = np.full(N, np.nan); dd20[20:] = ddv[20:] - ddv[:-20]

    base = rule_w(ddv, ENTER, ENTER)
    G = np.where((ddv <= ENTER) & (dd20 > 0.03), 1.0, np.where(ddv > ENTER, 1.0, 0.0))
    v5 = np.full(N, np.nan); v5[5:] = vix[5:] - vix[:-5]
    A3 = np.where((ddv <= ENTER) & (dd20 > 0.03) & (np.nan_to_num(v5, nan=1.) < 0),
                  1.0, np.where(ddv > ENTER, 1.0, 0.0))

    cd = {'현행 -16/-16': base, 'G (매일 게이트 아님)': G, 'A3 VIX 매일 게이트(v51)': A3}
    for m in ('S1', 'S2', 'S3'):
        cd['%s VIX상태 1회판정' % m] = state_rule(ddv, vix, vz, m, dd20)
    for dp in (0.25, 0.35, 0.50):
        cd['S4 VIX 진입대비 -%d%% 래치' % (dp * 100)] = state_rule(
            ddv, vix, vz, 'S4', dd20, dp)

    lo0 = int(idx.searchsorted(pd.Timestamp('%d-01-01' % Y0)))
    st = list(range(lo0, N - L, 63))
    print("=" * 104)
    print("v52 — VIX 를 도피 시작 시 **한 번만** 읽는다.  구간 %d~ · 20년 창 %d개"
          % (Y0, len(st)))
    print("     4블록 중 1972-85 는 VIX 가 없다 -> **4블록 검증 불가**(3/4)")
    print("=" * 104)

    def ev(w):
        c, pos = curve(rk, dfr, w)
        isa = np.array([np.mean(c[s + L - 1] / c[mstart[(mstart > s) & (mstart < s + L)][:60]])
                        for s in st])
        per = np.array([np.mean(c[s + L - 1] / c[mstart[(mstart > s) & (mstart < s + L)]])
                        for s in st])
        seg = c[lo0:]
        return dict(isa=isa, per=per, mdd=float((seg / np.maximum.accumulate(seg) - 1).min()),
                    sw=int((np.abs(np.diff(pos[lo0:])) > 1e-9).sum()), c=c)

    R = {nm: ev(w) for nm, w in cd.items()}
    b = R['현행 -16/-16']
    print("  %-28s%9s%8s%8s%10s%8s%9s%7s"
          % ('전략', 'ISA중앙', 'P20', 'P5', '영구중앙', '영구P5', 'MDD', '전환'))
    for nm in cd:
        r = R[nm]
        same = (nm != '현행 -16/-16'
                and np.allclose(r['isa'], b['isa']) and r['sw'] == b['sw'])
        tag = '  <- 기준' if nm.startswith('현행') else ('  <- **무발동**' if same else '')
        print("  %-28s%9.1f%8.1f%8.1f%10.1f%8.1f%8.1f%%%7d%s"
              % (nm, np.median(r['isa']), np.percentile(r['isa'], 20),
                 np.percentile(r['isa'], 5), np.median(r['per']),
                 np.percentile(r['per'], 5), r['mdd'] * 100, r['sw'], tag))
    print()
    print("  '무발동' = 조건이 한 번도 발동하지 않아 현행과 동일. 후보로 세지 않는다.")
    print()
    print("  현행 대비 (%)")
    print("  %-28s%9s%8s%8s%10s%8s" % ('전략', 'ISA중앙', 'P20', 'P5', '영구중앙', '영구P5'))
    for nm in cd:
        if nm.startswith('현행'):
            continue
        r = R[nm]
        g = lambda k, p: ((np.percentile(r[k], p) / np.percentile(b[k], p) - 1) * 100
                          if p else (np.median(r[k]) / np.median(b[k]) - 1) * 100)
        print("  %-28s%8.0f%%%7.0f%%%7.0f%%%9.0f%%%7.0f%%"
              % (nm, g('isa', 0), g('isa', 20), g('isa', 5), g('per', 0), g('per', 5)))

    # 닷컴 사례
    print()
    print("=" * 104)
    print("2000 닷컴 (2000-03 ~ 2003-12) — 데드캣을 걸렀는가")
    print("=" * 104)
    lo = int(idx.searchsorted(pd.Timestamp('2000-03-01')))
    hi = int(idx.searchsorted(pd.Timestamp('2003-12-31'), side='right'))
    v0 = b['c'][hi - 1] / b['c'][lo] - 1
    for nm in cd:
        c = R[nm]['c']
        v = c[hi - 1] / c[lo] - 1
        print("  %-28s%10.1f%%%11.1f%%p" % (nm, v * 100, (v - v0) * 100))

    print()
    print("=" * 104)
    win = []
    for nm in cd:
        if nm.startswith('현행'):
            continue
        r = R[nm]
        if (np.median(r['isa']) > np.median(b['isa'])
                and np.percentile(r['isa'], 20) > np.percentile(b['isa'], 20)
                and np.percentile(r['isa'], 5) > np.percentile(b['isa'], 5)
                and np.median(r['per']) > np.median(b['per'])
                and r['mdd'] >= b['mdd']):
            win.append(nm)
    print(verdict('VIX 상태변수를 전략 후보로 승격할 수 있는가', [
        ('중앙·P20·P5·영구중앙·MDD 를 모두 이긴 후보가 있다', len(win) > 0,
         ', '.join(win) if win else '없음'),
        ('4블록 검증이 가능하다', False, 'VIX 가 1990~ 이라 1972-85 블록 없음'),
    ])['text'])


if __name__ == '__main__':
    main()
