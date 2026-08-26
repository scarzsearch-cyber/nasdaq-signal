# -*- coding: utf-8 -*-
"""
§5 핵심: '-16% 아래로 → 위로 잠시 회복 → 다시 아래로' 가 실제 역사에서
몇 번 일어났고, 그때 A(-16/-11)와 B(-16/-16)의 거래수/손익이 얼마나 갈렸나.

에피소드 정의 (전략과 무관하게 낙폭 경로만으로 정의):
  시작 = dd 가 -16% 이하로 처음 내려간 날 (직전에 dd > -11% 이던 상태에서)
  종료 = 그 뒤 dd 가 -11% 위로 처음 올라온 날
  -> 시작 직전 두 전략 모두 QLD 100%, 종료일 두 전략 모두 QLD 100% 로 수렴하므로
     구간 수익률 비교가 정확히 사과 대 사과가 된다.
"""
import numpy as np, pandas as pd
from reentry_lib import run, met
import hist_data as H
from hyst_core import A, B, switches

ENTER, EXITA = -0.16, -0.11


def episodes(dd):
    d = dd.values; idx = dd.index
    eps = []; i = 0; n = len(d)
    armed = True                      # dd > -11% 상태(=QLD)에서 출발
    while i < n:
        if armed and d[i] <= ENTER:
            s = i
            j = i
            while j < n and d[j] <= EXITA:
                j += 1
            e = min(j, n - 1)
            seg = d[s:e + 1]
            # -16% 하향 돌파 횟수 (에피소드 내부)
            below = seg <= ENTER
            downs = int(np.sum(below[1:] & ~below[:-1])) + 1     # 첫 진입 포함
            ups = int(np.sum(~below[1:] & below[:-1]))
            eps.append(dict(start=idx[s], end=idx[e], days=e - s + 1,
                            mindd=float(seg.min()) * 100,
                            downs=downs, sawtooth=downs - 1, ups=ups))
            i = e + 1
            armed = True
        else:
            i += 1
    return pd.DataFrame(eps)


def main():
    D = H.build_ext()
    dd = D['dd']
    ep = episodes(dd)

    cA, wA, _ = run(D, A['ladder'], enter=A['enter'])
    cB, wB, _ = run(D, B['ladder'], enter=B['enter'])
    qld = pd.Series(np.cumprod(1 + D['qldr']), index=D['idx'])

    def segret(c, s, e):
        z = c.loc[s:e]
        return (z.iloc[-1] / z.iloc[0] - 1) * 100 if len(z) > 1 else np.nan

    def nsw(w, s, e):
        return len(switches(w.loc[s:e]))

    rows = []
    for _, r in ep.iterrows():
        s, e = r['start'], r['end']
        s0 = D['idx'][max(0, D['idx'].searchsorted(s) - 1)]
        e1 = D['idx'][min(len(D['idx']) - 1, D['idx'].searchsorted(e) + 1)]
        ra, rb, rq = segret(cA, s0, e1), segret(cB, s0, e1), segret(qld, s0, e1)
        rows.append(dict(시작=str(s.date()), 종료=str(e.date()), 거래일=int(r['days']),
                         최저낙폭=r['mindd'], 톱니=int(r['sawtooth']),
                         A전환=nsw(wA, s0, e1), B전환=nsw(wB, s0, e1),
                         A수익=ra, B수익=rb, QLD수익=rq, BminusA=rb - ra))
    t = pd.DataFrame(rows)
    pd.set_option('display.width', 250)
    print('===== 전체 하락 에피소드 (dd<=-16% 진입 ~ dd>-11% 복귀) =====')
    print(t.to_string(index=False, float_format=lambda x: f'{x:,.2f}'))

    print('\n===== 요약 =====')
    print('에피소드 수            : %d' % len(t))
    print('톱니(재하향)가 있던 것 : %d 개  (톱니 총 횟수 %d)' % ((t['톱니'] > 0).sum(), t['톱니'].sum()))
    print('A 총전환 %d / B 총전환 %d  (에피소드 내부)' % (t['A전환'].sum(), t['B전환'].sum()))
    saw = t[t['톱니'] > 0]; nos = t[t['톱니'] == 0]
    for nm, g in [('톱니 있음', saw), ('톱니 없음', nos)]:
        if len(g) == 0: continue
        print('%s (n=%d): A평균 %+6.2f%%  B평균 %+6.2f%%  B-A평균 %+6.2f%%p | B가 이긴 횟수 %d/%d'
              % (nm, len(g), g['A수익'].mean(), g['B수익'].mean(), g['BminusA'].mean(),
                 (g['BminusA'] > 0).sum(), len(g)))
    print('\n톱니 구간에서 B-A 최악 5개:')
    print(saw.nsmallest(5, 'BminusA')[['시작', '종료', '최저낙폭', '톱니', 'B전환', 'A수익', 'B수익', 'BminusA']]
          .to_string(index=False, float_format=lambda x: f'{x:,.2f}'))
    t.to_csv('hyst_episodes.csv', index=False, encoding='utf-8-sig')


if __name__ == '__main__':
    main()
