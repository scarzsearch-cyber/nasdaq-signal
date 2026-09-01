# -*- coding: utf-8 -*-
"""
[공유용 변형 — 롤링 10년 모니터, 2026-09-01]
소유자 지적: 끝점이 전부 오늘인 트레일링 창 3개만 보여주면 "최근 10·20년에 SCHD를
사는 건 멍청한 짓"처럼 읽힌다. 그 셋은 독립 표본이 아니라 **같은 강세장을 세 길이로
자른 것**이다.

해법 = 이 저장소의 slice_scan.py 철학 그대로:
  「구간은 특정 날짜 하나가 아니라 **모든 시작일 분포**로 판정한다」(CLAUDE.md §-1 ⓑ·ⓓ)
전체 역사에서 **가능한 모든 10년 창**을 굴려서, 배합별 성적의 **분포**와
**QQQ 대비 승률**을 낸다. "최근 10년이 이랬다"가 아니라 "10년을 굴리면 이런 일이
몇 %쯤 일어난다"로 바꾸는 것.

★ 승률 옆에 **비중첩 창 수**를 반드시 병기한다(slice_scan.py 규약) — 겹치는 창은
독립 관측이 아니다.

실행: python research/share_variant_rolling.py
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
WIN_YEARS = 10

# ★ 시작 구간 선택의 근거: SCHD 대리(French 배당 포트폴리오)가 아니라 **실제 배당 ETF**가
#   존재하는 구간으로 제한한다. DVY 상장(2003-11)부터가 "실물로 살 수 있었던" 배당 ETF의
#   시작이고, 그 이전은 대리라 초보자에게 보여줄 근거로는 약하다.
#   다만 10년 창을 굴리려면 표본이 필요하므로 **1990년부터**(대리 포함)와
#   **2003-11부터**(실물만) 둘 다 낸다 — 표본 두께와 실물성의 맞교환을 드러낸다.
STARTS = {'1990~ (배당 대리 포함)': '1990-01-01',
          '2003-11~ (배당 ETF 실물만)': '2003-11-10'}


def metrics(curve, days):
    yrs = days / 252.0
    cagr = curve[-1] / curve[0]
    cagr = cagr ** (1 / yrs) - 1
    seg = curve / np.maximum.accumulate(curve)
    mdd = float(seg.min() - 1)
    return cagr * 100, mdd * 100


def build(start):
    D = dict(DF.build('chain', start=start))
    idx = D['idx']
    px = pd.Series(D['px'], index=idx)
    r_qqq1x = np.nan_to_num(px.pct_change().values)
    r_div = np.asarray(D['schdr'], float)
    curves = {}
    for s, q in [(10, 0)] + RATIOS + [(0, 10)]:
        r = r_div if q == 0 else (r_qqq1x if s == 0 else
                                  DA.mix_monthly_parts(idx, dict(div=s / 10, qqq=q / 10),
                                                       dict(div=r_div, qqq=r_qqq1x)))
        label = 'SCHD' if q == 0 else ('QQQ' if s == 0 else f'S{s}Q{q}')
        curves[label] = np.cumprod(1 + r)
    return idx, curves


def roll(idx, curves, win_years=WIN_YEARS, step_days=21):
    """모든 시작일(월 단위 스텝)에서 win_years 창을 굴린다."""
    W = int(win_years * 252)
    n = len(idx)
    starts = list(range(0, n - W, step_days))
    labels = list(curves.keys())
    out = {lb: {'cagr': [], 'mdd': [], 'calmar': []} for lb in labels}
    for s0 in starts:
        e0 = s0 + W
        for lb in labels:
            c = curves[lb][s0:e0 + 1]
            c = c / c[0]
            cagr, mdd = metrics(c, W)
            out[lb]['cagr'].append(cagr)
            out[lb]['mdd'].append(mdd)
            out[lb]['calmar'].append(cagr / abs(mdd) if mdd < 0 else np.nan)
    span_years = (idx[-1] - idx[0]).days / 365.25
    return out, len(starts), span_years / win_years


def q(a, p):
    return float(np.percentile(np.asarray(a, float), p))


def main():
    EC.selfcheck()
    report = {}
    for name, start in STARTS.items():
        idx, curves = build(start)
        dist, nwin, nonoverlap = roll(idx, curves)
        print(f'\n{"="*78}')
        print(f'[{name}]  {idx[0].date()} ~ {idx[-1].date()}')
        print(f'롤링 {WIN_YEARS}년 창 {nwin}개(월 단위 스텝) · ★ 비중첩 창 {nonoverlap:.1f}개뿐')
        print(f'{"="*78}')
        print(f"{'배합':<8}{'CAGR중앙':>9}{'CAGR최악':>9}{'CAGR최선':>9}"
              f"{'MDD중앙':>9}{'MDD최악':>9}{'QQQ이긴창%':>11}{'SCHD이긴창%':>12}")
        qc = np.asarray(dist['QQQ']['cagr'], float)
        sc = np.asarray(dist['SCHD']['cagr'], float)
        for lb in dist:
            d = dist[lb]
            c = np.asarray(d['cagr'], float)
            m = np.asarray(d['mdd'], float)
            win_q = float(np.mean(c > qc) * 100)
            win_s = float(np.mean(c > sc) * 100)
            print(f"{lb:<8}{q(c,50):>9.2f}{q(c,0):>9.2f}{q(c,100):>9.2f}"
                  f"{q(m,50):>9.1f}{q(m,0):>9.1f}{win_q:>11.1f}{win_s:>12.1f}")
        report[name] = dict(nwin=nwin, nonoverlap=round(nonoverlap, 1),
                            frm=str(idx[0].date()), to=str(idx[-1].date()))

        # ★ 핵심 질문: "SCHD를 섞은 게 QQQ 단독보다 나았던 10년 창이 실제로 있었나?"
        print(f'\n  [핵심] QQQ 단독보다 **수익까지** 앞선 10년 창의 비율:')
        for lb in ['SCHD', 'S8Q2', 'S6Q4', 'S4Q6']:
            c = np.asarray(dist[lb]['cagr'], float)
            print(f'    {lb:<6} {float(np.mean(c > qc) * 100):5.1f}%')
        # 낙폭까지 같이 본 승리(수익 높고 낙폭도 얕음)
        qm = np.asarray(dist['QQQ']['mdd'], float)
        print(f'  [핵심] QQQ 단독보다 **낙폭이 얕았던** 10년 창의 비율:')
        for lb in ['SCHD', 'S8Q2', 'S6Q4', 'S4Q6']:
            m = np.asarray(dist[lb]['mdd'], float)
            print(f'    {lb:<6} {float(np.mean(m > qm) * 100):5.1f}%')

    print('\n※ 승률은 창이 서로 겹치므로 「독립 시행 확률」이 아니다 — 비중첩 창 수를 함께 볼 것.')

    # ---- 화면용 JSON (1990~ 구간: 창이 가장 두껍다) ----
    idx, curves = build(STARTS['1990~ (배당 대리 포함)'])
    dist, nwin, nonoverlap = roll(idx, curves)
    qc = np.asarray(dist['QQQ']['cagr'], float)
    qm = np.asarray(dist['QQQ']['mdd'], float)
    rows = []
    for lb in dist:
        c = np.asarray(dist[lb]['cagr'], float)
        m = np.asarray(dist[lb]['mdd'], float)
        rows.append(dict(label=lb,
                         med=round(q(c, 50), 2), worst=round(q(c, 0), 2), best=round(q(c, 100), 2),
                         p10=round(q(c, 10), 2), p90=round(q(c, 90), 2),
                         mddMed=round(q(m, 50), 1), mddWorst=round(q(m, 0), 1),
                         winCagr=round(float(np.mean(c > qc) * 100), 1),
                         winMdd=round(float(np.mean(m > qm) * 100), 1),
                         lose=round(float(np.mean(c < 0) * 100), 1)))
    out = dict(rows=rows, nwin=nwin, nonoverlap=round(nonoverlap, 1),
               frm=str(idx[0].date()), to=str(idx[-1].date()), win_years=WIN_YEARS)
    with open('공유용_별도전략/_rolling_out.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'\n[저장] 공유용_별도전략/_rolling_out.json ({nwin}창 · 비중첩 {nonoverlap:.1f})')
    print('  손실로 끝난 10년 창 비율:', {r['label']: r['lose'] for r in rows})


if __name__ == '__main__':
    main()
