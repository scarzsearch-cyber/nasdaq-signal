# -*- coding: utf-8 -*-
"""
[공유용 변형 — 위기 구간 실측, 2026-09-02] share_variant_regime_probe.py 후속.

소유자 지적: 트레일링 10/20/30년만 보여주니 SCHD 가 무조건 후진 자산처럼 보인다.

★ 구간 선정 규약 — 여기가 핵심이다.
  "SCHD 가 이긴 구간을 골라 넣는다" = 결과를 보고 고르는 것 = 체리피킹(§-1 ⓑ 금지).
  대신 **결과와 무관하게 미리 정해진 이름 있는 사건**만 쓴다:
    닷컴 붕괴 · 금융위기 · 코로나 · 2022 인플레 — 누구나 아는 4개.
  이 4개는 「주식이 크게 빠진 때」로 정의되지 「SCHD 가 이긴 때」로 정의되지 않는다.
  (실제로 코로나 구간은 SCHD 가 더 많이 빠진다 — 불리한 결과도 그대로 싣는다.)

  + 최근 성적(1년·연초 이후)도 같이 낸다. 이것도 결과와 무관한 「그냥 최근」이다.

실행: python 공유용_별도전략/share_variant_crisis.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import sys
import json
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defensive as DF                                # noqa: E402
import hist_defasset as DA                                 # noqa: E402
import eng_common as EC                                     # noqa: E402

RATIOS = [(8, 2), (7, 3), (6, 4), (5, 5), (4, 6)]

# ★ 결과를 보기 전에 고정한 구간 (이름 있는 사건 + 그냥 최근)
EVENTS = [
    ('닷컴 붕괴',   '2000-03-10', '2002-10-09', '기술주가 무너진 2년 반'),
    ('금융위기',    '2007-10-31', '2009-03-09', '2008년 전후'),
    ('코로나 급락', '2020-02-19', '2020-03-23', '한 달 만의 폭락'),
    ('2022 인플레', '2022-01-03', '2022-10-12', '금리 급등의 해'),
]

D = dict(DF.build('chain', start='1996-01-01'))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
r_qqq = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)


def series(s, q):
    r = r_div if q == 0 else (r_qqq if s == 0 else
                              DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10),
                                                   dict(div=r_div, qqq=r_qqq)))
    return pd.Series(np.cumprod(1 + r), index=idx)


SERIES = {}
for s, q in [(10, 0)] + RATIOS + [(0, 10)]:
    SERIES['SCHD' if q == 0 else ('QQQ' if s == 0 else f'S{s}Q{q}')] = series(s, q)


def seg_ret(cur, a, b):
    z = cur.loc[a:b]
    return float(z.iloc[-1] / z.iloc[0] - 1) * 100 if len(z) > 1 else np.nan


def main():
    EC.selfcheck()
    end = idx[-1]
    out = {'events': [], 'recent': []}

    print(f'\n데이터 {idx[0].date()} ~ {end.date()}\n')
    print('[1] 이름 있는 위기 4개 — 그 구간의 누적 수익률(%)')
    hdr = f"{'구간':<14}" + ''.join(f'{k:>9}' for k in SERIES)
    print(hdr)
    for name, a, b, note in EVENTS:
        vals = {k: seg_ret(v, a, b) for k, v in SERIES.items()}
        print(f"{name:<14}" + ''.join(f'{vals[k]:>9.1f}' for k in SERIES))
        out['events'].append(dict(name=name, frm=a, to=b, note=note,
                                  vals={k: round(vals[k], 1) for k in vals}))

    print('\n[2] 최근 성적 — 누적 수익률(%)')
    recents = [('최근 1년', end - pd.DateOffset(years=1), end),
               ('최근 2년', end - pd.DateOffset(years=2), end),
               ('2026년 연초 이후', pd.Timestamp('2026-01-01'), end)]
    print(hdr)
    for name, a, b in recents:
        vals = {k: seg_ret(v, a, b) for k, v in SERIES.items()}
        print(f"{name:<14}" + ''.join(f'{vals[k]:>9.1f}' for k in SERIES))
        out['recent'].append(dict(name=name, frm=str(pd.Timestamp(a).date()), to=str(b.date()),
                                  vals={k: round(vals[k], 1) for k in vals}))

    with open('공유용_별도전략/_crisis_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('\n[저장] 공유용_별도전략/_crisis_out.json')
    print('\n※ 코로나 구간처럼 SCHD 가 더 나빴던 사건도 그대로 싣는다 — 유리한 것만 고르지 않는다.')


if __name__ == '__main__':
    main()
