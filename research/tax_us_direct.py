# -*- coding: utf-8 -*-
"""
[사실 확인] QLD@ISA(국내) vs TQQQ@해외직투 — **세후로 비교하면 순위가 바뀌나** (2026-09-03, 소유자 질문)

소유자: 「미국직투계좌의 세금도 계산해야 해. 세전으로 하면 QLD ISA 가 너무 불리하니.」
→ 정확한 지적이다. §5-35·LEVERAGE_US.md 의 k 격자는 **전부 세전**이고, 그 표에서 3배가 2배를
  이기는 것은 **세금을 안 낸 3배**다. 실제로는 3배를 사려면 **해외계좌로 나가야 하고**(국내 3배 미상장),
  그 순간 ISA 의 과세이연을 잃는다.

⚠ **전략 무접촉 · 채택 아님 · 권고 아님.** LEVERAGE_US.md §4 결론(미국 진출 시에도 k=2)은 그대로다.
  이 파일은 그 문서 전체가 세전이라는 **빈칸 하나**만 채운다.

세제 규약
  · **ISA 중개형(국내 418660)**: 계좌 안 매매는 **무과세**(과세이연). 만기에 손익통산 후
    순이익에 **9.9%** 분리과세. ⚠ 서민형 비과세 400만원은 **넣지 않았다**(02 §7 이 이 규모에선
    기여 0% 로 이미 쟀다 — ISA 에 불리한 쪽 = 보수적). ⚠ 한도 연 2,000만·총 1억.
  · **일반계좌(국내상장 해외 ETF)**: 매매차익이 **배당소득 15.4%** · **손실 상계 불가** ·
    매도마다 과세. (tax_general_account.py 와 같은 규약)
  · **해외직투(미국 상장 QLD/TQQQ)**: **양도소득 22%** 분류과세 · **연내 손익통산** ·
    **이월 불가** · 기본공제 연 250만원(규모 의존이라 기본 제외).
    금융소득종합과세·건보료 **제외**(장점) — 이 표에 그 값어치는 안 들어간다.

★ 사전 등록 예측 (결과 보기 전 · 틀리면 그대로 적는다 §-1 ⑦)
    P1 세전 3배 우위(3,095,071 vs 199,448 = 15.5배)가 세후에는 **크게 줄지만 안 뒤집힌다**.
    P2 ISA 의 과세이연이 지평이 길수록 유리해져 **긴 창일수록 격차가 좁혀진다**.
    P3 해외직투는 매년 정산이라 **연내 손익통산의 값어치가 작다**(전환이 연 2~3회뿐).
    P4 「같은 배율(k=2)끼리」면 ISA 가 해외직투를 이긴다.

축퇴 검산(§5-38 교훈): 세율을 0 으로 두면 세전 공표 곡선이 그대로 나와야 한다.
  ★ 그 교훈이 나온 사고가 정확히 이 자리다 — 세금 루프를 새로 짜다 한 칸을 더 밀어
    세전이 반토막 났고, 검산을 넣고서야 잡혔다. 여기서는 assert 로 강제한다.

실행: python research/tax_us_direct.py [--emit]
      --emit 은 아티팩트용 JSON 을 stdout 끝에 찍는다(파일 쓰기 0).
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
_sys.path.insert(0, _os.path.join(_ROOT, 'deploy'))

import sys                                                 # noqa: E402
import json                                                # noqa: E402
import numpy as np                                         # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                    # noqa: E402
from axis_lib import lev_r                                 # noqa: E402

ISA_RATE, GEN_RATE, US_RATE = 0.099, 0.154, 0.22
L = '=' * 104
KS = tuple(round(2.0 + 0.1 * i, 1) for i in range(11))     # 2.0 ~ 3.0


def build():
    G, X = EC.selfcheck()
    idx = G.idx
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    wB = np.asarray(G.wB, float)                           # 이미 lag=1 집행값
    cur = {k: np.asarray(EC.sim2(wB, np.asarray(lev_r(G.D, k), float), MIXR), float)
           for k in KS}
    return idx, wB, cur


def switches(w):
    """전환이 일어난 인덱스 (비중이 바뀐 날)."""
    return np.where(np.abs(np.diff(w)) > 1e-9)[0] + 1


def after_isa(a, s, e, rate=ISA_RATE):
    """계좌 안 무과세 · 만기 1회 정산."""
    g = a[e] / a[s]
    return 1 + (g - 1) * (1 - rate) if g > 1 else g


def after_gen(a, sw, s, e, rate=GEN_RATE):
    """매도마다 과세 · 손실 상계 없음(배당소득)."""
    v, last = 1.0, a[s]
    for i in sw:
        if s < i < e:
            g = a[i] / last
            v *= (1 + (g - 1) * (1 - rate)) if g > 1 else g
            last = a[i]
    g = a[e] / last
    return v * ((1 + (g - 1) * (1 - rate)) if g > 1 else g)


def after_us(a, sw, yr, s, e, rate=US_RATE):
    """해외직투: 전환마다 실현 · **연내 손익통산** · 이월 불가 · 연말 정산."""
    v, last = 1.0, a[s]
    ybal, cy = 0.0, yr[s]
    for i in sw:
        if s < i < e:
            if yr[i] != cy:
                if ybal > 0:
                    v -= ybal * rate
                ybal = 0.0
                cy = yr[i]
            gain = v * (a[i] / last - 1.0)                 # 이번 전환의 실현 손익
            ybal += gain
            v *= a[i] / last
            last = a[i]
    if yr[e] != cy:
        if ybal > 0:
            v -= ybal * rate
        ybal = 0.0
    gain = v * (a[e] / last - 1.0)                         # 만기 청산도 실현으로 본다
    ybal += gain
    v *= a[e] / last
    if ybal > 0:
        v -= ybal * rate
    return v


ROWS = [
    ('QLD 2배 @ ISA 9.9%',      2.0, 'isa'),
    ('QLD 2배 @ 일반 15.4%',     2.0, 'gen'),
    ('QLD 2배 @ 해외직투 22%',    2.0, 'us'),
    ('2.5배 @ 해외직투 22%',      2.5, 'us'),
    ('TQQQ 3배 @ 해외직투 22%',  3.0, 'us'),
    ('TQQQ 3배 @ 세전(참고)',     3.0, 'pre'),
]
BASE = 'QLD 2배 @ ISA 9.9%'


def main():
    emit = '--emit' in sys.argv
    idx, wB, cur = build()
    n = len(idx)
    sw = switches(wB)
    yr = idx.year.values

    def val(k, mode, s, e):
        a = cur[k]
        if mode == 'pre':
            return a[e] / a[s]
        if mode == 'isa':
            return after_isa(a, s, e)
        if mode == 'gen':
            return after_gen(a, sw, s, e)
        return after_us(a, sw, yr, s, e)

    print(L)
    print('QLD@ISA vs TQQQ@해외직투 — 세후 비교 (전략 무접촉 · 채택 아님)')
    print(L)
    print('  창 {} ~ {} · 전환 {}회 · ISA {:.1f}%(만기1회) · 일반 {:.1f}%(매도마다) · 해외 {:.0f}%(연간정산)'
          .format(idx[0].date(), idx[-1].date(), len(sw),
                  ISA_RATE * 100, GEN_RATE * 100, US_RATE * 100))
    print('  ⚠ **달러 기준 엔진**이라 환 효과가 빠져 있다 — 418660 은 환노출 x2(원화환산지수의 2배),')
    print('     TQQQ 직투는 x1 이다. 이 구조 차이는 아래 표에 **안 들어간다**.')
    print('  ⚠ 합성 잣대(LEVERAGE_US §1): k>2 는 비용 과대 부과 = 3배에 보수적. k 사이 비교만 유효.')

    # ── 축퇴 검산 (§5-38 교훈 · assert 로 강제) ──────────────────────────────
    z = after_us(cur[2.0], sw, yr, 0, n - 1, rate=0.0)
    zi = after_isa(cur[3.0], 0, n - 1, rate=0.0)
    zg = after_gen(cur[2.0], sw, 0, n - 1, rate=0.0)
    print('  [검산] 세율 0 → 해외 {:,.3f} · ISA {:,.3f} · 일반 {:,.3f} vs 세전 {:,.3f} / {:,.3f}'
          .format(z, zi, zg, cur[2.0][-1], cur[3.0][-1]))
    assert abs(z / cur[2.0][-1] - 1) < 1e-9, '해외 축퇴 검산 실패'
    assert abs(zi / cur[3.0][-1] - 1) < 1e-9, 'ISA 축퇴 검산 실패'
    assert abs(zg / cur[2.0][-1] - 1) < 1e-9, '일반 축퇴 검산 실패'
    print()

    print('[54년 통짜 · 1 → 얼마]')
    print('  {:<26}{:>16}{:>13}'.format('', '세후 최종배수', 'vs QLD@ISA'))
    base = val(2.0, 'isa', 0, n - 1)
    out54 = {}
    for nm, k, mode in ROWS:
        v = val(k, mode, 0, n - 1)
        out54[nm] = v
        print('  {:<26}{:>15,.0f}배{:>12.2f}배'.format(nm, v, v / base))
    print()

    print('[지평별 창 전수 — 중앙 배수 (보폭 21일)]')
    HS = (5, 10, 20, 30)
    hdr = '  {:<26}'.format('') + ''.join('{:>12}'.format('%d년' % h) for h in HS)
    print(hdr)
    tbl = {}
    for nm, k, mode in ROWS:
        line = '  {:<26}'.format(nm)
        tbl[nm] = {}
        for h in HS:
            W = int(252 * h)
            vs = [val(k, mode, s, s + W) for s in range(0, n - W, 21)]
            m = float(np.median(vs))
            tbl[nm][h] = m
            line += '{:>11.1f}배'.format(m)
        print(line)
    print()

    print('[같은 창에서 QLD@ISA 대비 — 1.00 미만이면 ISA 쪽이 이긴다]')
    print(hdr)
    for nm, k, mode in ROWS:
        if nm == BASE:
            continue
        line = '  {:<26}'.format(nm)
        for h in HS:
            line += '{:>11.2f}배'.format(tbl[nm][h] / tbl[BASE][h])
        print(line)
    print()

    r = out54
    pre_gap = cur[3.0][-1] / cur[2.0][-1]
    post_gap = r['TQQQ 3배 @ 해외직투 22%'] / r[BASE]
    g5 = tbl['TQQQ 3배 @ 해외직투 22%'][5] / tbl[BASE][5]
    g30 = tbl['TQQQ 3배 @ 해외직투 22%'][30] / tbl[BASE][30]
    print('예측 대조:')
    print('  P1 세후에도 3배가 앞선다(안 뒤집힌다) → {}  (세전 {:.1f}배 → 세후 {:.2f}배)'
          .format('맞음' if post_gap > 1 else '**틀림**', pre_gap, post_gap))
    print('  P2 지평이 길수록 ISA 가 따라붙는다 → {}  (5년 {:.2f}배 → 30년 {:.2f}배)'
          .format('맞음' if g30 < g5 else '**틀림**', g5, g30))
    print('  P4 같은 k=2 면 ISA > 해외직투 → {}  ({:,.0f}배 vs {:,.0f}배)'
          .format('맞음' if r[BASE] > r['QLD 2배 @ 해외직투 22%'] else '**틀림**',
                  r[BASE], r['QLD 2배 @ 해외직투 22%']))
    print()
    # ── 세후 손익분기 배율 — 해외직투 k 가 몇이면 ISA 2배와 같아지나 ──────────
    print('[세후 손익분기 배율 — 해외직투 k 가 몇이어야 ISA 2배와 같아지나]')
    print('  {:<8}'.format('k') + ''.join('{:>12}'.format('%d년' % h) for h in HS)
          + '{:>12}'.format('54년'))
    grid = {}
    for k in KS:
        line = '  {:<6.1f}'.format(k)
        grid[k] = {}
        for h in HS:
            W = int(252 * h)
            m = float(np.median([val(k, 'us', s, s + W) for s in range(0, n - W, 21)]))
            grid[k][h] = m / tbl[BASE][h]
            line += '{:>11.2f}배'.format(grid[k][h])
        g54 = val(k, 'us', 0, n - 1) / base
        grid[k]['54'] = g54
        line += '{:>11.2f}배'.format(g54)
        print(line)
    print('  ※ 1.00 을 넘는 첫 k 가 손익분기다 — 그 아래면 ISA 에 그냥 두는 쪽이 낫다.')
    be = {}
    for h in list(HS) + ['54']:
        hit = [k for k in KS if grid[k][h] >= 1.0]
        be[str(h)] = hit[0] if hit else None
        print('    {:>4}년 손익분기 k = {}'.format(
            h, '{:.1f}'.format(hit[0]) if hit else '3.0 에서도 미달'))
    print()

    print('[이 측정이 낳은 질문]')
    print('  Q-a ISA 한도(연 2,000만·총 1억)를 넘는 돈은 ISA 밖이다 — 규모가 커지면')
    print('      비교가 「ISA vs 해외」가 아니라 「일반 15.4% vs 해외 22%」로 바뀐다.')
    print('      그 열이 위 표의 2·3행이다(해외가 세율은 높으나 손익통산·이월이 된다).')
    print('  Q-b 환 효과가 빠져 있다 — 418660 환노출 x2 vs TQQQ x1. 04 §5-37ⓕ 는 위기에')
    print('      원화 약세가 완충으로 작동한다고 실측했다(GFC +51.7%). 그 값어치는 미포함.')
    print('  Q-c 해외직투는 금소세·건보료 밖이다(LEVERAGE_US §7-③). 인출기에 유리할 수 있다.')

    if emit:
        # 아티팩트용 — k 격자의 위험·수익 지표 + 세제별 세후
        def fullmet(c):
            yrs = len(c) / 252.0
            d = c / np.maximum.accumulate(c) - 1
            r = np.diff(c) / c[:-1]
            cagr = c[-1] ** (1 / yrs) - 1
            W = 5040
            return dict(cagr=round(100 * cagr, 2),
                        vol=round(100 * float(np.std(r)) * np.sqrt(252), 1),
                        mdd=round(100 * float(d.min()), 1),
                        calmar=round(cagr / abs(float(d.min())), 3),
                        p05=round(float(np.quantile(c[W:] / c[:-W], 0.05)), 1),
                        w1d=round(100 * float(r.min()), 1),
                        pre=round(float(c[-1]), 0))
        ks = []
        for k in KS:
            m = fullmet(cur[k])
            m['k'] = k
            m['isa'] = round(val(k, 'isa', 0, n - 1), 0)
            m['us'] = round(val(k, 'us', 0, n - 1), 0)
            m['gen'] = round(val(k, 'gen', 0, n - 1), 0)
            m['hIsa'] = {}
            m['hUs'] = {}
            for h in HS:
                W = int(252 * h)
                ss = range(0, n - W, 21)
                m['hIsa'][str(h)] = round(float(np.median(
                    [val(k, 'isa', s, s + W) for s in ss])), 3)
                m['hUs'][str(h)] = round(float(np.median(
                    [val(k, 'us', s, s + W) for s in ss])), 3)
            ks.append(m)
        js = {'ks': ks,
              'full54': {k: round(v, 2) for k, v in out54.items()},
              'horizon': {k: {str(h): round(v, 3) for h, v in d.items()}
                          for k, d in tbl.items()},
              'grid': {str(k): {str(h): round(v, 4) for h, v in d.items()}
                       for k, d in grid.items()},
              'breakeven': be,
              'switches': int(len(sw)),
              'span': [str(idx[0].date()), str(idx[-1].date())]}
        print('\n===JSON===')
        print(json.dumps(js, ensure_ascii=False))


if __name__ == '__main__':
    main()
