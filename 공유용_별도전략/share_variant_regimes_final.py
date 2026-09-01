# -*- coding: utf-8 -*-
"""
[공유용 변형 — 트레일링 창 폐기 + 양쪽 국면 사례, 2026-09-02]

소유자 결정: 「최근 10/20/30년」 토글을 없앤다. 셋 다 끝점이 오늘이라
**같은 기술주 강세장을 세 길이로 자른 것**이었고, 그래서 SCHD 가 무조건
후진 자산처럼 보였다. 대신 **QQQ 가 강했던 국면 / SCHD 가 강했던 국면을
대칭으로** 보여준다.

★ 체리피킹이 아닌 이유 (규약):
  - 양쪽을 **같은 수·같은 형식**으로 싣는다. 한쪽만 고르지 않는다.
  - 구간은 **이름 있는 국면**으로 잡는다(닷컴·GFC·AI 랠리 등). 성과가 최대가 되게
    날짜를 미세조정하지 않는다.
  - 편향 없는 기준선인 **롤링 320창 분포**는 화면에 그대로 남는다 — 사례는 그
    분포의 «예시»일 뿐이라는 것을 화면이 말한다.

내는 것:
  [1] 전 구간(1990~) 정적 배합 지표 — 차트의 단일 기준이 된다
  [2] 전 구간 월초 스냅샷 곡선 — 적립 계산기용
  [3] 양쪽 국면 사례

실행: python 공유용_별도전략/share_variant_regimes_final.py
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

START = '1990-01-01'
RATIOS = [(8, 2), (7, 3), (6, 4), (5, 5), (4, 6)]

# ★ 이름 있는 국면 — 양쪽 4개씩 대칭
QQQ_ERAS = [
    ('AI 랠리',        '2023-01-03', '2024-12-31', '챗GPT 이후 2년'),
    ('코로나 회복장',   '2020-03-23', '2021-12-31', '폭락 직후 반등'),
    ('기술주 대세상승', '2009-03-09', '2020-01-31', 'GFC 저점 이후 11년'),
    ('금융위기',       '2007-10-31', '2009-03-09', '고배당에 금융주가 많던 때'),
]
SCHD_ERAS = [
    ('닷컴 붕괴',      '2000-03-10', '2002-10-09', '기술주가 무너진 2년 반'),
    ('잃어버린 7년',   '2000-03-10', '2007-10-31', '닷컴 고점에서 GFC 직전까지'),
    ('2022 인플레',    '2022-01-03', '2022-10-12', '금리 급등의 해'),
    ('올해(2026)',     '2026-01-02', '2026-08-28', '지금 진행 중'),
]

D = dict(DF.build('chain', start=START))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
n = len(idx)
r_qqq = np.nan_to_num(px.pct_change().values)
r_div = np.asarray(D['schdr'], float)


def blend_r(s, q):
    if q == 0:
        return r_div
    if s == 0:
        return r_qqq
    return DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10), dict(div=r_div, qqq=r_qqq))


LABELS, CURVES = [], {}
for s, q in [(10, 0)] + RATIOS + [(0, 10)]:
    lb = 'SCHD' if q == 0 else ('QQQ' if s == 0 else f'S{s}Q{q}')
    LABELS.append(lb)
    CURVES[lb] = np.cumprod(1 + blend_r(s, q))


def seg(cur, a, b):
    ser = pd.Series(cur, index=idx).loc[a:b]
    return float(ser.iloc[-1] / ser.iloc[0] - 1) * 100 if len(ser) > 1 else np.nan


def month_snap(cur):
    s = pd.Series(np.arange(n), index=idx)
    fp = s.groupby(idx.to_period('M')).first()
    return [str(p) for p in fp.index], cur[fp.values]


def main():
    EC.selfcheck()
    print(f'\n데이터 {idx[0].date()} ~ {idx[-1].date()} ({n}거래일 · '
          f'{(idx[-1]-idx[0]).days/365.25:.1f}년)\n')

    print('[1] 전 구간 정적 배합 (차트 단일 기준)')
    print(f"{'라벨':<8}{'CAGR%':>8}{'변동성%':>9}{'MDD%':>8}{'최종배수':>10}{'Calmar':>8}")
    stat, monthly, dates_ref = [], {}, None
    for lb in LABELS:
        c = CURVES[lb]
        m = EC.fullmet(c, idx=idx)
        r = np.diff(c, prepend=1.0) / np.concatenate(([1.0], c[:-1]))
        v = float(np.std(r[1:]) * np.sqrt(252) * 100)
        print(f"{lb:<8}{m['cagr']:>8.2f}{v:>9.2f}{m['mdd']:>8.2f}{m['final']:>10.1f}{m['calmar']:>8.3f}")
        s_, q_ = (10, 0) if lb == 'SCHD' else ((0, 10) if lb == 'QQQ' else (int(lb[1]), int(lb[3])))
        stat.append(dict(label=lb, s=s_, q=q_, cagr=round(m['cagr'], 2), vol=round(v, 2),
                         mdd=round(m['mdd'], 2), final=round(m['final'], 2),
                         calmar=round(m['calmar'], 4)))
        if lb not in ('SCHD', 'QQQ'):
            dts, ms = month_snap(c)
            dates_ref = dates_ref or dts
            monthly[lb] = [round(float(x), 5) for x in ms]

    def era_block(title, eras):
        print(f'\n{title}')
        print(f"{'국면':<16}{'기간':<24}" + ''.join(f'{k:>9}' for k in LABELS))
        rows = []
        for name, a, b, note in eras:
            vals = {lb: seg(CURVES[lb], a, b) for lb in LABELS}
            print(f"{name:<16}{a[:7]+'~'+b[:7]:<24}" + ''.join(f'{vals[k]:>9.1f}' for k in LABELS))
            rows.append(dict(name=name, frm=a[:7].replace('-', '.'), to=b[:7].replace('-', '.'),
                             note=note, v={k: round(vals[k], 1) for k in vals}))
        return rows

    q_rows = era_block('[3a] QQQ 가 강했던 국면 — 누적 수익률(%)', QQQ_ERAS)
    s_rows = era_block('[3b] SCHD 가 강했던 국면 — 누적 수익률(%)', SCHD_ERAS)

    out = dict(static=stat, monthly=dict(dates=dates_ref, ratios=monthly),
               frm=str(idx[0].date()), to=str(idx[-1].date()), months=len(dates_ref),
               years=round((idx[-1] - idx[0]).days / 365.25, 1),
               qqq_eras=q_rows, schd_eras=s_rows)
    with open('공유용_별도전략/_regimes_final.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print('\n[저장] 공유용_별도전략/_regimes_final.json')
    print('\n※ 사례는 예시일 뿐 — 편향 없는 기준선은 롤링 320창 분포다(화면에 유지).')


if __name__ == '__main__':
    main()
