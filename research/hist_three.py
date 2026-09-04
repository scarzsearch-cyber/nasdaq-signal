# -*- coding: utf-8 -*-
"""-16/-16 vs -16/-15 vs -16/-11 3자 비교 (v21 조건: 실측 방어자산 / 한국 체결 / 원화)"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys

try:                       # [코드리뷰 2026-09-04] 이 파일은 콘솔에 표를 찍는다.
    _sys.stdout.reconfigure(encoding='utf-8')   # cp949 콘솔에서 em-dash 로 죽지 않게
except Exception:
    pass
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np, pandas as pd
from reentry_lib import run, met, rolling_stats
import hist_data as H, hist_defensive as DF, hist_korea as K, hist_krfinal as KF

S16 = dict(name='-16/-16', enter=-0.16, ladder=[(('dd', -0.16), 1.0, 0)])
S15 = dict(name='-16/-15', enter=-0.16, ladder=[(('dd', -0.15), 1.0, 0)])
S11 = dict(name='-16/-11', enter=-0.16, ladder=[(('dd', -0.11), 1.0, 0)])
ALL = [S11, S15, S16]


def sw(w):
    v = w.values
    return int(np.sum(v[1:] != v[:-1]))


def kelly(r, lab):
    r = np.asarray(r, dtype=float); r = r[~np.isnan(r)]
    mu, var = r.mean(), r.var()
    f = mu / var
    # 로그성장 최대화 레버리지를 격자로 직접 확인(로그수익 기반, 근사식 검증용)
    grid = np.arange(0.5, 5.01, 0.25)
    g = [np.mean(np.log1p(np.clip(x * r, -0.999, None))) * 252 for x in grid]
    best = grid[int(np.argmax(g))]
    print('%-28s  mu/var 근사 f* = %.2f   격자 최적 f* = %.2f   (연 %.2f%%, 변동성 %.2f%%)'
          % (lab, f, best, mu * 252 * 100, r.std() * np.sqrt(252) * 100))
    return best


def usd_table(kind, label, start=None, end=None, cost=0.001):
    D = DF.build(kind)
    print('\n----- %s -----' % label)
    print('%-9s %13s %7s %8s %7s %7s %6s %7s %7s' %
          ('전략', '최종배수', 'CAGR', 'MDD', 'Calmar', 'Sharpe', '전환', '5Y승률', '10Y승률'))
    idx = D['idx']
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = len(idx) if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    # [코드리뷰 2026-09-04] run() 은 r[0]=0 으로 눌러 곡선을 1.0 에서 시작시킨다.
    #   여기서 안 누르면 구간 첫날 수익이 벤치마크에만 한 번 더 곱해진다 —
    #   start=2000-01-03 에서 final 5.4322 vs 규약대로 5.0582 (첫날 qldr +7.39%).
    #   hyst_core 에서 2026-09-04 에 고친 것과 같은 결함이 여기 남아 있었다.
    br = np.asarray(D['qldr'][lo:hi], float).copy(); br[0] = 0.0
    qld = pd.Series(np.cumprod(1 + br), index=idx[lo:hi])
    out = {}
    for S in ALL:
        c, w, t = run(D, S['ladder'], enter=S['enter'], cost=cost, start=start, end=end)
        m = met(c); rs = rolling_stats(c, qld); out[S['name']] = m
        print('%-9s %13s %6.2f%% %7.2f%% %7.2f %7.2f %6d %6.1f%% %6.1f%%'
              % (S['name'], f"{m['final']:,.1f}", m['cagr'] * 100, m['mdd'] * 100,
                 m['calmar'], m['sharpe'], sw(w),
                 rs[5]['win'] if 5 in rs else np.nan, rs[10]['win'] if 10 in rs else np.nan))
    m = met(qld)
    print('%-9s %13s %6.2f%% %7.2f%% %7.2f %7.2f' % ('QLD보유', f"{m['final']:,.1f}",
          m['cagr'] * 100, m['mdd'] * 100, m['calmar'], m['sharpe']))
    return out


if __name__ == '__main__':
    print('===== 0. 사용자 전제 검증: QQQ 의 로그성장 최적 레버리지(f*) =====')
    D = DF.build('cash2')
    rq = np.nan_to_num(D['px'].pct_change().values)
    idx = D['idx']
    for lab, s, e in [('1972-2026 전구간', None, None), ('2000-2026', '2000-01-03', None),
                      ('1972-1999', None, '1999-12-31'), ('2010-2026', '2010-01-01', None)]:
        lo = 0 if s is None else idx.searchsorted(pd.Timestamp(s))
        hi = len(idx) if e is None else idx.searchsorted(pd.Timestamp(e), side='right')
        kelly(rq[lo:hi], 'QQQ ' + lab)
    print('  * f* > 2 면 「2배 레버리지는 아직 Kelly 미만」이라는 전제가 성립한다.')
    print('  * 단 f* 는 μ 추정에 극도로 민감하다. 아래 구간별 편차를 볼 것.')

    print('\n===== 1. 달러 기준 3자 비교 =====')
    usd_table('cash2', '방어=연2%현금 / 1972-2026 (v20 조건)')
    usd_table('chain', '방어=배당체인(실측) / 1972-2026')
    usd_table('chain', '방어=배당체인(실측) / 2000-2026', start='2000-01-03')
    usd_table('chain', '방어=배당체인(실측) / 2003-11~ 방어자산 100% 실물', start='2003-11-10')

    # ---------------------------------------------------------------- 2. 조건부 Kelly
    print('\n===== 2. 상태별 조건부 Kelly — 「도피 자체가 정당한가」 =====')
    ddv = D['ddv']
    for lab, mask in [('DD > -11%  (평상시)', ddv > -0.11),
                      ('-16% < DD <= -11% (회색지대)', (ddv <= -0.11) & (ddv > -0.16)),
                      ('DD <= -16% (도피 상태)', ddv <= -0.16)]:
        nxt = np.roll(rq, -1)                      # 신호 다음날 수익(체결 규약과 동일)
        r = nxt[:-1][mask[:-1]]
        kelly(r, '%-30s n=%5d' % (lab, len(r)))
    print('  * 도피 상태의 f* 가 2 미만이면 「그 구간에서 2배는 과레버리지」 = 도피가 정당하다.')

    # ---------------------------------------------------------------- 3. 한국 실전
    print('\n===== 3. 한국 실전 3자 비교 (원화·환노출2배·한국거래일·슬리피지0.1%) =====')
    krd = K.kr_caldays()
    Dk, idxk, lev2, lev1, dfk, fr = KF.build_krw('chain')
    lo = idxk.searchsorted(pd.Timestamp(KF.ST))
    _b = np.asarray(lev2[lo:], float).copy(); _b[0] = 0.0   # [코드리뷰] run() 규약과 동일
    bench = pd.Series(np.cumprod(1 + _b), index=idxk[lo:])
    print('%-9s %13s %7s %8s %7s %6s %7s %8s' %
          ('전략', '최종배수', 'CAGR', 'MDD', 'Calmar', '전환', '5Y승률', '10Y승률'))
    for S in ALL:
        c, w, t = KF.sim(Dk, idxk, lev2, dfk, S, krd)
        m = met(c); rs = rolling_stats(c, bench)
        print('%-9s %13s %6.2f%% %7.2f%% %7.2f %6d %6.1f%% %7.1f%%'
              % (S['name'], f"{m['final']:,.1f}", m['cagr'] * 100, m['mdd'] * 100,
                 m['calmar'], sw(w), rs[5]['win'], rs[10]['win']))
    m = met(bench)
    print('%-9s %13s %6.2f%% %7.2f%% %7.2f' % ('TIGER레버', f"{m['final']:,.1f}",
          m['cagr'] * 100, m['mdd'] * 100, m['calmar']))

    # ---------------------------------------------------------------- 4. 비용 민감도
    print('\n===== 4. 편도 총비용 민감도 (한국 실전 조건) =====')
    print('%-12s' % '편도비용' + ''.join('%14s' % S['name'] for S in ALL))
    for tot in (0.0005, 0.001, 0.002, 0.003, 0.005, 0.01):
        row = '%-12s' % ('%.2f%%' % (tot * 100))
        for S in ALL:
            c, w, t = KF.sim(Dk, idxk, lev2, dfk, S, krd, slip=0.0, cost=tot)
            row += '%14s' % f"{met(c)['final']:,.1f}"
        print(row)
    print('  * §4.4 실측 시초가 갭 표준편차 2.58% 를 감안하면 실효비용은 오른쪽 행에 가깝다.')

    # ---------------------------------------------------------------- 5. 회색지대 분해
    print('\n===== 5. 회색지대(-16%<DD<=-11%) 분해 — A와 B가 실제로 갈리는 유일한 구간 =====')
    n = len(ddv); armed = np.ones(n, dtype=bool); cur = True
    for i in range(n):
        if cur and ddv[i] <= -0.16: cur = False
        elif (not cur) and ddv[i] > -0.11: cur = True
        armed[i] = cur                                  # True = 아직 -16% 미돌파(하락 중)
    gray = (ddv <= -0.11) & (ddv > -0.16)
    nxt = np.roll(rq, -1)
    for lab, mask in [('하락 중 회색지대 (A·B 둘 다 QLD 보유)', gray & armed),
                      ('회복 중 회색지대 (A=SCHD, B=QLD) ★', gray & ~armed)]:
        r = nxt[:-1][mask[:-1]]
        kelly(r, '%-38s n=%5d' % (lab, len(r)))
    m = (gray & ~armed)[:-1]
    r = nxt[:-1][m]
    # [코드리뷰 2026-09-04] 방어자산도 **다음날**로 맞춘다. 종전에는 QQQ 만 np.roll 로
    #   한 칸 밀고 방어자산은 당일치를 썼다. 마스크가 561일에 걸쳐 70개의 비연속 블록이라
    #   하루 밀림이 상쇄되지 않고 140일이 통째로 바뀌었다 — 인쇄값 +48.5% vs 맞춘 값 +12.9%.
    nxt_s = np.roll(np.asarray(D['schdr'], float), -1)
    print('   ★ 구간 누적: QQQ %+.1f%%  /  2배환산 %+.1f%%  /  같은일수 방어자산 %+.1f%%'
          % ((np.prod(1 + r) - 1) * 100,
             (np.prod(1 + 2 * r - D['c_daily']) - 1) * 100,
             (np.prod(1 + nxt_s[:-1][m]) - 1) * 100))
    print('   => 이 구간이 B 의 초과수익 전부의 출처다. f* 와 누적수익이 이를 정당화하는지 보라.')

    # ---------------------------------------------------------------- 6. WFA / OOS
    print('\n===== 6. 고정 WFA / OOS 3자 (Train 5년 -> Test 1년, 연속상태) =====')
    for kind, lab in [('cash2', '방어=연2%현금'), ('chain', '방어=배당체인(실측)')]:
        Dw = DF.build(kind); iw = Dw['idx']
        for ss, se, plab in [(None, None, '1972-2026'), ('2000-01-03', None, '2000-2026')]:
            lo2 = 0 if ss is None else iw.searchsorted(pd.Timestamp(ss))
            yrs = sorted(set(iw[lo2:].year))
            picks, oos, wins = [], 1.0, []
            state = 1.0
            for y in yrs[5:]:
                tr0, tr1 = f'{y-5}-01-01', f'{y-1}-12-31'
                best, bv = None, -9e9
                for S in ALL:
                    c, w, t = run(Dw, S['ladder'], enter=S['enter'], start=tr0, end=tr1)
                    if c.iloc[-1] > bv: bv, best = c.iloc[-1], S
                c, w, t = run(Dw, best['ladder'], enter=best['enter'],
                              start=f'{y}-01-01', end=f'{y}-12-31', w0=state)
                if len(c) < 2: continue
                state = float(w.iloc[-1]); picks.append(best['name'])
                oos *= float(c.iloc[-1]); wins.append(c.iloc[-1] > 1)
            # [코드리뷰 2026-09-04] 고정 대조군은 **OOS 와 같은 창**에서 재야 한다.
            #   OOS 루프는 yrs[5:] 라 라벨이 '2000-2026' 이어도 실제로는 2005~ 를 덮는데,
            #   종전 대조군은 늘 start='2000-01-03' 이었다 — 적응형의 패배가 40~147% 부풀었다
            #   (2000-2026 행: OOS 71.04 vs 고정 165.35 로 2.3배 패배처럼 보였으나
            #    같은 창(2005~)의 고정은 89.29 라 실제 격차는 1.26배).
            ostart = f'{yrs[5]}-01-01'
            for S in ALL:
                c, w, t = run(Dw, S['ladder'], enter=S['enter'], start=ostart)
                print('  %-16s %-10s 고정(%s~) %12s'
                      % ('', S['name'], ostart[:4], f"{met(c)['final']:,.2f}"))
            print('  %-16s %-10s OOS 누적 %12s  승 %2d/%2d  선택분포 %s'
                  % (lab, '%s-%s' % (yrs[5], yrs[-1]), f'{oos:,.2f}', sum(wins), len(wins),
                     {p: picks.count(p) for p in sorted(set(picks))}))

    # ---------------------------------------------------------------- 7. 톱니 에피소드
    print('\n===== 7. 톱니 에피소드별 3자 (v20 hyst_episodes 정의: -16% 진입 ~ -11% 회복) =====')
    Dc = DF.build('chain'); ic = Dc['idx']; dc = Dc['ddv']
    eps, i, N = [], 0, len(dc)
    while i < N:
        if dc[i] <= -0.16:
            j = i
            while j < N and dc[j] <= -0.11: j += 1
            if j < N:
                seg = dc[i:j]; below = seg <= -0.16
                downs = int(np.sum(below[1:] & ~below[:-1])) + 1
                eps.append((ic[i], ic[min(j, N - 1)], j - i, downs - 1))
            i = j
        i += 1
    curves = {}
    for S in ALL:
        curves[S['name']] = run(Dc, S['ladder'], enter=S['enter'], cost=0.001)[0]
    saw = [e for e in eps if e[3] >= 1]
    print('  전체 에피소드 %d개 / 톱니(재하향 1회 이상) %d개' % (len(eps), len(saw)))
    print('%-12s %-12s %5s %5s' % ('시작', '종료', '일수', '재하향') +
          ''.join('%11s' % S['name'] for S in ALL))
    tot = {S['name']: [] for S in ALL}
    for s0, s1, nd, dn in saw:
        row = '%-12s %-12s %5d %5d' % (s0.date(), s1.date(), nd, dn)
        for S in ALL:
            c = curves[S['name']]
            v = (c.loc[:s1].iloc[-1] / c.loc[:s0].iloc[-1] - 1) * 100
            tot[S['name']].append(v); row += '%10.1f%%' % v
        print(row)
    print('%-36s' % '  톱니 평균' + ''.join('%10.1f%%' % np.mean(tot[S['name']]) for S in ALL))
    print('%-36s' % '  톱니 중앙값' + ''.join('%10.1f%%' % np.median(tot[S['name']]) for S in ALL))
    print('%-36s' % '  톱니 최악' + ''.join('%10.1f%%' % np.min(tot[S['name']]) for S in ALL))
    print('%-36s' % '  -16/-11 대비 승수' + ''.join('%10d' % sum(
        1 for k in range(len(saw)) if tot[S['name']][k] > tot['-16/-11'][k]) for S in ALL))

    # ---------------------------------------------------------------- 8. 위기별
    print('\n===== 8. 위기 구간별 3자 (방어=배당체인, 달러) =====')
    CR = [('1973-74', '1973-01-11', '1974-10-03'), ('1987', '1987-08-25', '1987-12-04'),
          ('2000-02 닷컴', '2000-03-10', '2002-10-09'), ('2007-09', '2007-10-31', '2009-03-09'),
          ('2020 코로나', '2020-02-19', '2020-03-23'), ('2022 인플레', '2021-11-19', '2022-12-28'),
          ('2025 관세', '2025-02-19', '2025-06-30')]
    qc = pd.Series(np.cumprod(1 + Dc['qldr']), index=ic)
    print('%-14s' % '위기' + ''.join('%11s' % S['name'] for S in ALL) + '%11s' % 'QLD보유')
    for nm, s0, s1 in CR:
        row = '%-14s' % nm
        for S in ALL:
            c = curves[S['name']]
            row += '%10.1f%%' % ((c.loc[:s1].iloc[-1] / c.loc[:s0].iloc[-1] - 1) * 100)
        row += '%10.1f%%' % ((qc.loc[:s1].iloc[-1] / qc.loc[:s0].iloc[-1] - 1) * 100)
        print(row)
