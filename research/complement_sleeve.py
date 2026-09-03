# -*- coding: utf-8 -*-
"""
[사실 확인] 「내 레버리지를 보완해 주는 주식 슬리브는 무엇인가」 — QQQ 집중도를 메우는 후보 비교 (2026-09-03, 소유자 질문)

소유자: 「QQQ 가 기술 63 · 통신 17 · 경기소비 16 이면, 내 레버리지를 보완해 주는 게 뭐가 있어?
        완전한 올웨더 헤지가 아니어도 **주식 + 주식**으로. QQQ+SCHD 로 섞는 사람들도 있더라고.」

⚠ **전략 무접촉 · 채택 아님.** §5-34 가 이미 「정적 배합은 선형이고 관문을 못 넘는다」를 확정했다 —
  이 파일은 **「그래도 섞는다면 무엇이 가장 덜 겹치나」**만 답한다. 규칙·비중을 바꾸자는 제안이 아니다.

★ **§5-34 가 정한 판정 삼각형을 그대로 쓴다** — 「낮은 상관」만으로는 부족하다:
  ① **섹터 겹침**(QQQ 와 min 합 · 수익률 기반 역추정) ② **상관**(전체 · QQQ 최악 5% 일) ③ **자체 수익**.
  국채가 상관 −0.19 로 가장 좋은데도 분산 보너스가 **음수**였던 이유가 ③ 이었다(자체 수익 1.31% < T-bill 4.57%).

후보 (전부 주식 · 공통 구간에서 비교): SCHD · VYM · DVY · SDY(고배당 계열) · IWN(소형가치) · IJR(소형) · RSP(S&P 동일가중) ·
  EFA(선진국) · EEM(신흥국) · EWY(한국) · EWJ(일본) · BRK-B(버크셔) · XLV/XLP/XLU/XLE(방어·경기둔감 섹터) · GDX(금광).

⚠ **한계 (반드시 병기)**: ① 공통 구간이 후보마다 다르다 — **가장 짧은 후보에 맞춘 공통창**과 **각자 최장 구간**을 둘 다 낸다.
  ② 섹터 역추정은 보유 공시가 아니다(§5-31 한계 그대로). ③ **평시의 낮은 상관이 위기에 지켜진다는 보장은 없다** —
  2008 에서 배당 ETF(−59.9%)·한국 금융주(−62.9%)가 QQQ(−53.0%)보다 더 빠졌다(§5-31 · §5-34 보강).

실행: python research/complement_sleeve.py   (약 20초 · 네트워크 0 — 캐시만 · 파일 쓰기 0)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

L = '=' * 116
SECT = {'XLK': '기술', 'XLC': '통신', 'XLY': '경기소비', 'XLF': '금융', 'XLV': '헬스케어',
        'XLP': '필수소비', 'XLI': '산업', 'XLE': '에너지', 'XLU': '유틸', 'XLB': '소재', 'XLRE': '부동산'}
CAND = [('SCHD', '배당다우존스'), ('VYM', '고배당'), ('DVY', '고배당가중'), ('SDY', '배당귀족'),
        ('IWN', '미국 소형가치'), ('IJR', '미국 소형'), ('RSP', 'S&P 동일가중'),
        ('EFA', '선진국(미국제외)'), ('EEM', '신흥국'), ('EWY', '한국'), ('EWJ', '일본'),
        ('BRK_B', '버크셔'), ('XLV', '헬스케어'), ('XLP', '필수소비'), ('XLU', '유틸리티'),
        ('XLE', '에너지'), ('GDX', '금광주')]
CRISES = [('GFC 2007~09', '2007-10-31', '2009-03-09'), ('코로나 2020', '2020-02-19', '2020-03-23'),
          ('금리 2022', '2021-11-19', '2022-10-14'), ('2025', '2025-02-19', '2025-04-08')]


def load(sym):
    d = pd.read_csv(f'data/hist/yahoo_{sym}.csv')
    k = 'Date' if 'Date' in d.columns else d.columns[0]
    d[k] = pd.to_datetime(d[k])
    return d.set_index(k)['Close'].astype(float).sort_index()


def nnls(X, y, iters=200):
    m, n = X.shape
    P = np.zeros(n, bool); w = np.zeros(n)
    XtX = X.T @ X; Xty = X.T @ y
    for _ in range(iters):
        g = Xty - XtX @ w; g[P] = -np.inf
        j = int(np.argmax(g))
        if g[j] <= 1e-12:
            break
        P[j] = True
        for _ in range(60):
            s = np.zeros(n); A = XtX[np.ix_(P, P)]
            s[P] = np.linalg.lstsq(A + 1e-12 * np.eye(A.shape[0]), Xty[P], rcond=None)[0]
            if s[P].min() > 0:
                w = s; break
            neg = P & (s <= 0)
            alpha = float(np.min(w[neg] / (w[neg] - s[neg] + 1e-300)))
            w = w + alpha * (s - w); P &= w > 1e-12
        else:
            break
    return w


def style(r, sec, s0, s1):
    w0 = r.dropna(); w0 = w0[(w0.index >= s0) & (w0.index <= s1)]
    cols = [c for c in sec.columns if sec[c].reindex(w0.index).notna().mean() > 0.98]
    if not cols:
        return None
    sub = sec[cols].reindex(w0.index); ix = sub.dropna().index
    if len(ix) < 120:
        return None
    X = sub.loc[ix].values; Y = w0.reindex(ix).values
    sc = float(np.sqrt(np.mean(X ** 2))) or 1.0
    lam = sc * np.sqrt(len(ix)) * 50
    w = nnls(np.vstack([X, np.full((1, len(cols)), lam)]), np.concatenate([Y, [lam]]))
    r2 = 1 - np.var(Y - X @ w) / np.var(Y)
    return dict(zip(cols, w)), float(r2)


def main():
    print(L); print('QQQ 를 보완하는 주식 슬리브 — 섹터 겹침 · 상관 · 자체 수익 (전략 무접촉 · 채택 아님)'); print(L)
    qqq = load('QQQ')
    sec = pd.DataFrame({s: load(s).pct_change() for s in SECT})
    S0, S1 = '2023-09-01', '2026-08-31'
    qs, qr2 = style(qqq.pct_change(), sec, S0, S1)
    g3 = ('XLK', 'XLC', 'XLY')
    print(f"  QQQ 내재 배합(최근 3년 · R²={qr2:.2f}): " + ' · '.join(f'{SECT[c]} {w*100:.0f}%' for c, w in
                                                                 sorted(qs.items(), key=lambda t: -t[1]) if w > 0.02))
    print(f'  → 기술·통신·경기소비 합 **{sum(qs.get(k, 0) for k in g3)*100:.0f}%**. 「보완」은 이 셋 밖의 비중을 얼마나 가져오는가다.')

    rq = qqq.pct_change()
    rows = []
    for sym, nm in CAND:
        try:
            s = load(sym)
        except Exception:
            continue
        r = s.pct_change()
        ix = rq.dropna().index.intersection(r.dropna().index)
        if len(ix) < 500:
            continue
        a, b = rq[ix], r[ix]
        q05 = a.quantile(0.05); m = a <= q05
        yrs = (ix[-1] - ix[0]).days / 365.25
        cg = (float((1 + b).prod()) ** (1 / yrs) - 1) * 100
        st = style(r, sec, S0, S1)
        ov = np.nan; out3 = np.nan; r2 = np.nan
        if st:
            w, r2 = st
            ov = sum(min(qs.get(k, 0), w.get(k, 0)) for k in SECT) * 100
            out3 = (1 - sum(w.get(k, 0) for k in g3)) * 100
        rows.append(dict(nm=nm, sym=sym, corr=float(np.corrcoef(a, b)[0, 1]),
                         cbad=float(np.corrcoef(a[m], b[m])[0, 1]), cagr=cg,
                         vol=float(b.std() * np.sqrt(252) * 100), ov=ov, out3=out3, r2=r2,
                         start=ix[0].date(), n=len(ix)))
    print('\n' + L); print('후보별 — 각자 최장 공통구간 (구간이 다르므로 수익은 직접 비교 금지 · 상관/겹침 위주로 볼 것)'); print(L)
    print(f"  {'슬리브':<16}{'상관':>8}{'폭락일 상관':>12}{'섹터 겹침':>10}{'QQQ 3섹터 밖':>13}"
          f"{'연수익':>9}{'연변동성':>9}{'시작':>12}")
    for d in sorted(rows, key=lambda x: x['corr']):
        print(f"  {d['nm']:<16}{d['corr']:>+8.3f}{d['cbad']:>+12.3f}"
              f"{(f'{d[chr(111)+chr(118)]:.0f}%' if not np.isnan(d['ov']) else '—'):>10}"
              f"{(f'{d[chr(111)+chr(117)+chr(116)+chr(51)]:.0f}%' if not np.isnan(d['out3']) else '—'):>13}"
              f"{d['cagr']:>8.2f}%{d['vol']:>8.1f}%{str(d['start']):>12}")
    print('  ※ 「섹터 겹침」은 QQQ 와의 min 합(작을수록 안 겹침) · 「QQQ 3섹터 밖」은 기술·통신·경기소비 이외의 비중(클수록 보완).')

    print('\n' + L); print('위기별 낙폭 — 평시의 낮은 상관이 위기에도 지켜지나 (창 안 단순 수익)'); print(L)
    hdr = f"  {'슬리브':<16}" + ''.join(f'{nm:>14}' for nm, _, _ in CRISES)
    print(hdr)
    print(f"  {'QQQ(기준)':<16}" + ''.join(
        f'{(lambda seg: f"{(seg.iloc[-1]/seg.iloc[0]-1)*100:>13.1f}%" if len(seg) > 2 else f"{chr(8212):>14}")(qqq[(qqq.index>=a)&(qqq.index<=b)]):>14}'
        for _, a, b in CRISES))
    for d in sorted(rows, key=lambda x: x['corr']):
        s = load(d['sym'])
        line = f"  {d['nm']:<16}"
        for _, a, b in CRISES:
            seg = s[(s.index >= a) & (s.index <= b)]
            line += f'{(seg.iloc[-1]/seg.iloc[0]-1)*100:>13.1f}%' if len(seg) > 2 else f'{"—":>14}'
        print(line)

    # 공통창 — 수익을 공정하게 비교하려면 같은 날짜여야 한다
    print('')
    print(L); print('공통창 2011-10-21 ~ (SCHD 상장 후 · 모든 후보가 존재) — 수익을 직접 비교할 수 있는 유일한 표'); print(L)
    C0 = pd.Timestamp('2011-10-21')
    print(f"  {'슬리브':<16}{'상관':>8}{'폭락일 상관':>12}{'연수익':>9}{'연변동성':>9}{'수익/변동성':>11}{'2020':>9}{'2022':>9}")
    out = []
    for sym, nm in [('QQQ', 'QQQ(기준)')] + CAND:
        try:
            ser = load(sym)
        except Exception:
            continue
        r = ser.pct_change()
        ix = rq.dropna().index.intersection(r.dropna().index)
        ix = ix[ix >= C0]
        if len(ix) < 500:
            continue
        a, b = rq[ix], r[ix]
        q05 = a.quantile(0.05); m = a <= q05
        yrs = (ix[-1] - ix[0]).days / 365.25
        cg = (float((1 + b).prod()) ** (1 / yrs) - 1) * 100
        vo = float(b.std() * np.sqrt(252) * 100)

        def win(x0, x1, sg=ser):
            z = sg[(sg.index >= x0) & (sg.index <= x1)]
            return (z.iloc[-1] / z.iloc[0] - 1) * 100 if len(z) > 2 else float('nan')
        out.append((nm, float(np.corrcoef(a, b)[0, 1]), float(np.corrcoef(a[m], b[m])[0, 1]),
                    cg, vo, cg / vo, win('2020-02-19', '2020-03-23'), win('2021-11-19', '2022-10-14')))
    for nm, c1, c2, cg, vo, rv, w20, w22 in sorted(out, key=lambda t: t[2]):
        print(f'  {nm:<16}{c1:>+8.3f}{c2:>+12.3f}{cg:>8.2f}%{vo:>8.1f}%{rv:>11.2f}{w20:>8.1f}%{w22:>8.1f}%')
    print('  ※ 「수익/변동성」은 무위험이자를 빼지 않은 거친 값이다 — 순위만 보라.')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 상관이 낮아도 §5-34 대로 「자체 수익」이 낮으면 분산 보너스가 음수가 된다 — 위 표의 연수익 열을 같이 볼 것.')
    print('  Q-b 이 표는 「섞는다면 무엇을」이지 「섞어야 하나」가 아니다. 후자는 §5-34 가 이미 답했다(관문 미달 · 선형).')


if __name__ == '__main__':
    main()
