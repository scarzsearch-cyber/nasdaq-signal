# -*- coding: utf-8 -*-
"""
[생존성 연구 ①, 소유자 지시 2026-08-31] 현행 B 의 생존 조건 지도.

  1. 드리프트 임계 — 지수 rolling CAGR 이 얼마 밑이면 B 우위(절대·상대)가 죽는가
  2. 드리프트×변동성 2D 지도 — 어떤 환경에서 강하고 약한가 (+SPX·KOSPI 참조점)
  3. 볼드래그 국면 — 지수 횡보인데 2배가 크게 뒤처진 구간의 빈도·정체
  4. 지평표 — 3/5/10/15/20년: 손실확률·맨몸 상대승률·중앙·최악
  5. 2026 현재 상태 — 각 지표의 역사 분포 백분위

정의: CAGR 은 (끝/시작)^(252/w)−1 · 변동성은 일수익 std×√252 · 드래그는
2×지수CAGR − 2배CAGR (비용+볼드래그 합산, 연율) · 상대성과는 log(B배수/맨몸배수).
전략 무변경·판정 아님. 실행: python research/surv_map.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
r1 = np.nan_to_num(pd.Series(G.D['px']).pct_change().values)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
aB = EC.sim2(np.asarray(G.wB, float), QLDR, MIXR)
a2 = np.cumprod(1 + QLDR)
a1 = np.cumprod(1 + r1)
wB = np.asarray(G.wB, float)

L1 = np.concatenate(([0], np.cumsum(np.log1p(r1))))
L2 = np.concatenate(([0], np.cumsum(np.log1p(np.diff(a2, prepend=1.0) / np.concatenate(([1.0], a2[:-1]))))))
LB = np.concatenate(([0], np.cumsum(np.log1p(np.diff(aB, prepend=1.0) / np.concatenate(([1.0], aB[:-1]))))))
S1 = np.concatenate(([0], np.cumsum(r1)))
Q1 = np.concatenate(([0], np.cumsum(r1 ** 2)))
DEF = np.concatenate(([0], np.cumsum(1 - wB)))


def cagr(L, i, w):
    return np.expm1((L[i + 1] - L[i + 1 - w]) * 252.0 / w)


def vol(i, w):
    m = (S1[i + 1] - S1[i + 1 - w]) / w
    v = (Q1[i + 1] - Q1[i + 1 - w]) / w - m * m
    return np.sqrt(max(v, 0)) * np.sqrt(252)


def wmdd(a, i, w):
    seg = a[i + 1 - w:i + 1]
    peak = np.maximum.accumulate(seg)
    return abs(float(np.min(seg / peak - 1)))


def windows(w, stride=5, need_mdd=False):
    rows = []
    for i in range(w - 1, n, stride):
        c1 = cagr(L1, i, w)
        c2 = cagr(L2, i, w)
        cb = cagr(LB, i, w)
        ex = (LB[i + 1] - LB[i + 1 - w]) - (L2[i + 1] - L2[i + 1 - w])
        row = dict(i=i, c1=c1, c2=c2, cb=cb, v=vol(i, w),
                   drag=2 * c1 - c2, ex=ex * 252.0 / w)
        if need_mdd:
            m = wmdd(aB, i, w)
            row['cal'] = cb / max(m, 1e-9)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    # ---- 1. 드리프트 임계 ----
    print('\n[1] 지수 rolling CAGR 구간별 — B 는 어디서 죽는가')
    for w, lab in ((2520, '10년'), (5040, '20년')):
        df = windows(w, 5)
        print(f'  ({lab} 창 {len(df)}개 · 5일 보폭)')
        print(f"  {'지수CAGR':>10} {'창수':>5} {'B CAGR중앙':>9} {'맨몸2x중앙':>9} "
              f"{'P(B>맨몸)':>9} {'P(B<0)':>7}")
        edges = [(-1, 0), (0, 0.05), (0.05, 0.10), (0.10, 0.15), (0.15, 9)]
        for lo, hi in edges:
            m = (df.c1 >= lo) & (df.c1 < hi)
            if m.sum() == 0:
                print(f'  {lo*100:>4.0f}~{hi*100:>3.0f}% {0:>5}')
                continue
            d = df[m]
            print(f'  {lo*100:>4.0f}~{hi*100:>3.0f}% {len(d):>5} {d.cb.median()*100:>8.1f}% '
                  f'{d.c2.median()*100:>8.1f}% {np.mean(d.ex > 0):>9.1%} {np.mean(d.cb < 0):>7.1%}')

    # ---- 2. 드리프트 × 변동성 지도 (10년 창) ----
    print('\n[2] 드리프트×변동성 지도 — 10년 창 B CAGR 중앙 / P(B>맨몸) (행=지수CAGR, 열=변동성)')
    df = windows(2520, 10, need_mdd=True)
    cq = [-9, 0.05, 0.10, 0.15, 9]
    vq = list(np.quantile(df.v, [0, 1 / 3, 2 / 3, 1.0]))
    print(f'  변동성 3분위 경계: {vq[1]*100:.1f}% · {vq[2]*100:.1f}% (전 창 범위 {vq[0]*100:.0f}~{vq[3]*100:.0f}%)')
    hdr = '  지수CAGR\\변동성 ' + ''.join(f"{['저','중','고'][k]+'변동':>16}" for k in range(3))
    print(hdr)
    for a_, b_ in zip(cq[:-1], cq[1:]):
        cells = []
        for k in range(3):
            m = (df.c1 >= a_) & (df.c1 < b_) & (df.v >= vq[k]) & (df.v <= vq[k + 1] + 1e-12)
            d = df[m]
            cells.append('      —        ' if len(d) < 10 else
                         f'{d.cb.median()*100:>5.1f}%/{np.mean(d.ex>0):>4.0%} n={len(d):<4}')
        print(f'  {a_*100:>4.0f}~{b_*100:>3.0f}%     ' + ' '.join(cells))
    print('  (참조점: SPX 54년 지수 CAGR 8.6%·변동성 17% → 중단 행 · KOSPI 29년 4.7%·22% → 최하단 행 —'
          '\n   엔진 연구의 전멸이 이 지도의 왼쪽/아래 칸과 일치)')

    # ---- 3. 볼드래그 국면 ----
    print('\n[3] 볼드래그 국면 — 3년 지수 CAGR |±3%| 횡보인데 2배가 뒤처진 창')
    df3 = windows(756, 5)
    flat = df3[np.abs(df3.c1) < 0.03]
    lag_ = flat[flat.c2 < flat.c1 - 0.03]
    yrs = sorted(set(pd.Series(idx)[flat.i].dt.year))
    print(f'  횡보 3년 창 {len(flat)}/{len(df3)} ({len(flat)/len(df3):.0%}) · '
          f'그중 2배가 지수보다 연 3%p+ 뒤처진 창 {len(lag_)}/{len(flat)} ({0 if len(flat)==0 else len(lag_)/len(flat):.0%})')
    print(f'  횡보 창 종료 연도: {yrs}')
    print(f'  횡보 창 드래그 중앙 {flat.drag.median()*100:.1f}%/yr vs 전체 {df3.drag.median()*100:.1f}%/yr — '
          f'B 는 그 창들에서 CAGR 중앙 {flat.cb.median()*100:+.1f}% (도피가 드래그 일부를 상쇄)')

    # ---- 4. 지평표 ----
    print('\n[4] 투자기간별 (전 창 · 보폭 1일)')
    print(f"  {'기간':>5} {'창수':>6} {'손실확률':>8} {'P(B>맨몸2x)':>10} {'중앙':>7} {'p05':>6} {'최악':>6}")
    for w, lab in ((756, '3년'), (1260, '5년'), (2520, '10년'), (3780, '15년'), (5040, '20년')):
        mb = aB[w:] / aB[:-w]
        mh = a2[w:] / a2[:-w]
        print(f'  {lab:>5} {len(mb):>6} {np.mean(mb < 1):>8.1%} {np.mean(mb > mh):>10.1%} '
              f'{np.median(mb):>6.2f}배 {np.quantile(mb, 0.05):>5.2f}배 {mb.min():>5.2f}배')

    # ---- 5. 2026 현재 상태 ----
    print('\n[5] 2026-08 현재 — 후행 지표의 역사 백분위 (높음=역사적 강세 상태)')

    def pct_rank(series, val, hi_good=True):
        p = float(np.mean(np.asarray(series) <= val))
        return p

    rows = []
    for w, lab in ((756, '3년'), (1260, '5년'), (2520, '10년'), (5040, '20년')):
        df_ = windows(w, 5)
        cur_c = cagr(L1, n - 1, w)
        cur_v = vol(n - 1, w)
        rows.append((f'지수 {lab} CAGR', f'{cur_c*100:+.1f}%', pct_rank(df_.c1, cur_c)))
        if w <= 2520:
            rows.append((f'지수 {lab} 변동성', f'{cur_v*100:.1f}%', pct_rank(df_.v, cur_v)))
    df3_ = windows(756, 5)
    cur_drag = 2 * cagr(L1, n - 1, 756) - cagr(L2, n - 1, 756)
    rows.append(('2배 드래그 3년', f'{cur_drag*100:.1f}%/yr', pct_rank(df3_.drag, cur_drag)))
    df5_ = windows(1260, 5, need_mdd=True)
    cur_cb = cagr(LB, n - 1, 1260)
    cur_cal = cur_cb / max(wmdd(aB, n - 1, 1260), 1e-9)
    rows.append(('B 5년 CAGR', f'{cur_cb*100:+.1f}%', pct_rank(df5_.cb, cur_cb)))
    rows.append(('B 5년 Calmar', f'{cur_cal:.2f}', pct_rank(df5_.cal, cur_cal)))
    defsh = (DEF[n] - DEF[n - 1260]) / 1260
    hist_def = [(DEF[i + 1] - DEF[i + 1 - 1260]) / 1260 for i in range(1259, n, 5)]
    rows.append(('방어 일수 비중 5년', f'{defsh:.1%}', pct_rank(hist_def, defsh)))
    sw = np.abs(np.diff(wB))
    last_re = np.where((np.diff(wB) > 0))[0]
    if len(last_re):
        li = int(last_re[-1]) + 1
        rows.append(('마지막 복귀 후 B', f'{aB[-1]/aB[li]:.2f}배 ({str(idx[li].date())}~)', float('nan')))
    rows.append(('전환 횟수 최근 5년', f'{int(sw[-1260:].sum())}회', float('nan')))
    for nm, v, p in rows:
        pr = '' if np.isnan(p) else f' · 역사 백분위 {p:.0%}'
        print(f'  {nm:<18} {v:<24}{pr}')
    print('  ⚠ 백분위가 높다 = 지금까지 좋았다는 뜻일 뿐, 미래 보증이 아니다 (금지 6·7).')

    # ---- [6] 상품 생존 트립와이어 (2026-08-31 측정 감사) --------------------
    #   FINAL_AUDIT 은 「상품 이벤트는 대체 교체로 흡수 가능」이라 단언했으나 **트리거가
    #   없었다.** nav_collect.py 가 이미 시총을 적립하므로 밴드만 얹는다. 전략 무관 —
    #   전환 신호일에 상품이 정지돼 있으면 그날 하루가 아니라 전환 자체를 놓친다.
    print('\n[6] 상품 생존 — 4다리 AUM 트립와이어 (data/nav_history.csv)')
    WATCH4 = {'418660': '공격 레버리지', '458730': '방어 배당',
              '305080': '방어 국채', '411060': '방어 금'}
    BAND_WARN, BAND_ALERT = 300, 100          # 억원 — 관리종목/상폐 요건(50억)에 여유를 둔 선
    try:
        nav = pd.read_csv('data/nav_history.csv', encoding='utf-8', dtype=str)
        last = {}
        for _, r in nav.iterrows():
            if r['code'] in WATCH4:
                last[r['code']] = r
        if not last:
            raise ValueError('감시 4종목 수집분 없음')
        for code, lab in WATCH4.items():
            r = last.get(code)
            if r is None:
                print(f'  {code} {lab:<12} 수집분 없음 — nav_collect.py 확인')
                continue
            eok = float(r['mktcap_eok'] or 0)
            st = ('★경보' if eok < BAND_ALERT else
                  '주의' if eok < BAND_WARN else '정상')
            print(f'  {code} {lab:<12} 시총 {eok:>8,.0f}억  [{st}]  ({r["as_of"]} 기준)')
        print(f'  밴드: 정상 ≥{BAND_WARN}억 · 주의 <{BAND_WARN}억 · 경보 <{BAND_ALERT}억')
        print('  경보 시 할 일: 대체 상품(KODEX 미국나스닥100레버리지 등) 사전 확인 —')
        print('  국내 상폐는 NAV 정산이라 원금 소실형이 아니나 과세 이벤트+재진입 마찰이 비용.')
    except Exception as e:                     # 수집분이 없어도 [1]~[5] 는 살아야 한다
        print(f'  (건너뜀: {e})')


if __name__ == '__main__':
    main()
