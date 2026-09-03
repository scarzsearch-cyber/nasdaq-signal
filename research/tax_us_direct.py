# -*- coding: utf-8 -*-
"""
[사실 확인] 전략 B ISA(국내) vs 3배 B 직투 — **세후로 비교하면 순위가 바뀌나** (2026-09-03, 소유자 질문)

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

실행: python research/tax_us_direct.py [--emit] [--c21]
      --c21 은 21세기(2000~) 격자만 찍는다 — **화면에 싣는 기준은 이쪽이다**(v131).
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
    ('전략 B ISA 9.9%',        2.0, 'isa'),
    ('전략 B 일반 15.4%',       2.0, 'gen'),
    ('전략 B 직투 22%',         2.0, 'us'),
    ('2.5배 B 직투 22%',        2.5, 'us'),
    ('3배 B 직투 22%',          3.0, 'us'),
    ('3배 B 세전(참고)',         3.0, 'pre'),
]
BASE = '전략 B ISA 9.9%'


def main():
    if '--c21' in sys.argv:
        c21()
        return
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
    print('전략 B ISA vs 3배 B 직투 — 세후 비교 (전략 무접촉 · 채택 아님)')
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

    print('[54년 통짜 · 1 → 얼마]  ※ 이름 규약: 전략 B 규칙을 쓰면 이름 뒤에 B (CLAUDE §3)')
    print('  {:<26}{:>16}{:>13}'.format('', '세후 최종배수', 'vs 전략 B ISA'))
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

    print('[같은 창에서 전략 B ISA 대비 — 1.00 미만이면 전략 B ISA 가 이긴다]')
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
    print('[세후 손익분기 배율 — 직투 배율이 몇이어야 전략 B ISA 와 같아지나]')
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
            m['hGen'] = {}
            m['hPre'] = {}
            for h in HS:
                W = int(252 * h)
                ss = range(0, n - W, 21)
                m['hIsa'][str(h)] = round(float(np.median(
                    [val(k, 'isa', s, s + W) for s in ss])), 3)
                m['hUs'][str(h)] = round(float(np.median(
                    [val(k, 'us', s, s + W) for s in ss])), 3)
                m['hGen'][str(h)] = round(float(np.median(
                    [val(k, 'gen', s, s + W) for s in ss])), 3)
                m['hPre'][str(h)] = round(float(np.median(
                    [val(k, 'pre', s, s + W) for s in ss])), 3)
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




# =============================================================================
# [보강 2026-09-03, 소유자 지적 「54년짜리는 버블 한 방 아니냐 · 표에서 빼라」]
# =============================================================================
# ★ 소유자 지적이 맞다 — 다만 **한 방이 아니라 두 방**이다 (10년 단위 B 세전):
#     1972~81  4.07배 · 1982~91  8.73배 · **1992~2001 30.13배** ·
#     2002~11  3.11배 · **2012~21 26.59배** · 2022~26 2.10배
#   **최고 10년 하나만 빼면 199,448 → 6,167배(3.3%)**, 둘 빼면 232배.
#   → 54년 통짜 배수는 두 국면이 만든다. **표에 실으면 현실감을 왜곡한다.**
#
# ★ 그러나 **세금 격차 자체는 버블 의존이 아니다** — ISA÷해외가 10년 단위로
#   1.22 / 1.38 / 1.39 / 1.16 / 1.49 / 1.18 로 **고르다**(최대/최소 1.28).
#   즉 「연 4.09%p」는 구조적이고, 6.28배는 그 고른 격차가 5.5개 10년 곱해진 것이다.
#
# ★★ **21세기(2000~, 26.6년 · v131 소유자 규정 기준)로 재면 결론이 바뀐다**:
#     QLD 2배 @ISA **146.1배** vs TQQQ 3배 @해외 **146.6배 = 1.00배 (동률)**
#     MDD 는 −49.6% → −62.5%. **세후로 사는 것이 0인데 낙폭만 12.9%p 깊어진다.**
#     21세기 세후 손익분기 k = **3.0** (54년의 2.7보다 높다 — 3배까지 올려야 본전).
#
# ⚠ **v131 규약 위반이었다**: 「성과·배수 주장은 21세기 기준 · 54년은 폭락 검증용에만」이
#   이미 소유자 규정으로 있었는데 내가 54년 통짜를 표 머리에 올렸다. 소유자가 잡았다.
#   → 아티팩트 표에서 54년 통짜를 전부 뺐고(21세기·지평별만), 이 파일은 계속 다 출력한다
#     (「데이터엔 넣되 표엔 넣지 마라」 — 소유자 지시 그대로).
#
# 재현: python research/tax_us_direct.py  (54년) · 아래 c21() (21세기)


def c21():
    """21세기(2000~) 기준 k 격자 — v131 규정. 표에 싣는 것은 이쪽이다."""
    idx, wB, cur = build()
    sw = switches(wB)
    yr = idx.year.values
    m = np.where(yr >= 2000)[0]
    S, E = m[0], m[-1]
    base = after_isa(cur[2.0], S, E)
    print('21세기 {} ~ {} ({:.1f}년) · ISA 2배 기준 {:.1f}배'
          .format(idx[S].date(), idx[E].date(), len(m) / 252.0, base))
    print('  {:<6}{:>10}{:>10}{:>10}{:>10}{:>9}'
          .format('k', '세전', 'ISA', '해외', 'vs ISA2', 'MDD'))
    for k in KS:
        a = cur[k]
        seg = a[S:E + 1]
        d = seg / np.maximum.accumulate(seg) - 1
        u = after_us(a, sw, yr, S, E)
        print('  {:<6.1f}{:>9.1f}배{:>9.1f}배{:>9.1f}배{:>9.2f}배{:>8.1f}%'
              .format(k, a[E] / a[S], after_isa(a, S, E), u, u / base, 100 * d.min()))
    print('  ※ 이 표가 화면(아티팩트 배율 탭)에 실리는 기준이다. 54년 통짜는 위 main() 에만.')


if __name__ == '__main__':
    main()


# =============================================================================
# [보강 2026-09-03, 소유자 지적] 적립식 + ISA 한도 — 「어느 순간 거치식이 된다」
# =============================================================================
# 소유자: 「2배는 ISA 1억까지밖에 추가납입이 안 돼서 어느 순간 거치식이 되고,
#          3배는 적립식으로 계속 납입도 가능한데 이런 차이도 계산되니?」
# → **안 됐다.** 위 표는 전부 「1원이 얼마가 되나」(거치식 배수)다.
#   ISA 한도(연 2,000만·총 1억)를 넣으면 월 100만 기준 **8.3년에 한도가 차고**
#   그 뒤 납입은 **일반계좌 15.4%** 몫이 된다. 직투는 한도가 없다.
#
# 모형: 월 PM 만원 납입 · 이벤트 구동(적립일·전환일만 계산)
#   전략 B  = ISA 버킷(계좌 안 무과세 · 만기 9.9% · 서민형 비과세 400만) +
#             한도 초과분이 가는 일반 버킷(전환마다 15.4% · 손실 상계 불가)
#   TQQQ B 직투 = 단일 버킷 · 전환마다 실현 · **연내 손익통산** · **연 250만 공제** ·
#             이월 불가 · 22%. (실제 납부는 다음해 5월이나 여기서는 연말에 뗀다 = 보수적)
# 축퇴 검산: 모든 세율 0 + ISA 한도 무한 → 두 경로가 **순수 적립 곡선과 일치**해야 한다.

ISA_YEAR_CAP = 2000.0        # 만원 · 연간
ISA_TOTAL_CAP = 10000.0      # 만원 · 총 1억
ISA_FREE = 400.0             # 만원 · 서민형 비과세(소유자 해당)
US_DEDUCT = 250.0            # 만원 · 해외 양도소득 기본공제(연간)


def _events(s, e, sw, step=21):
    """적립일(step 거래일마다) + 전환일 을 시간순으로."""
    con = [(t, 'c') for t in range(s + step, e + 1, step)]
    swi = [(int(t), 's') for t in sw if s < t <= e]
    return sorted(con + swi, key=lambda x: (x[0], x[1] == 'c'))


def accum_B(a, sw, yr, s, e, pm, isa_free=ISA_FREE, r_isa=ISA_RATE, r_gen=GEN_RATE,
            year_cap=ISA_YEAR_CAP, total_cap=ISA_TOTAL_CAP):
    """전략 B — ISA 버킷 + 한도 초과분 일반 버킷. 반환 (세후 평가액, 총 납입, ISA 소진 시점 년)"""
    iv = ib = gv = gb = 0.0
    isa_paid = 0.0
    ypaid, cy = 0.0, yr[s]
    paid = 0.0
    last = s
    full_at = None
    for t, kind in _events(s, e, sw):
        g = a[t] / a[last]
        iv *= g
        gv *= g
        last = t
        if kind == 'c':
            if yr[t] != cy:
                ypaid, cy = 0.0, yr[t]
            room = min(year_cap - ypaid, total_cap - isa_paid)
            to_isa = max(0.0, min(pm, room))
            iv += to_isa
            ib += to_isa
            isa_paid += to_isa
            ypaid += to_isa
            rest = pm - to_isa
            gv += rest
            gb += rest
            paid += pm
            if full_at is None and isa_paid >= total_cap - 1e-9:
                full_at = (t - s) / 252.0
        else:                                        # 전환 — ISA 는 무과세, 일반만 과세
            gain = gv - gb
            if gain > 0:
                gv -= gain * r_gen
            gb = gv
    g = a[e] / a[last]
    iv *= g
    gv *= g
    iv -= max(iv - ib - isa_free, 0.0) * r_isa        # ISA 만기 1회 정산(서민형 비과세 차감)
    gv -= max(gv - gb, 0.0) * r_gen                   # 일반 만기 청산
    return iv + gv, paid, full_at


def accum_US(a, sw, yr, s, e, pm, rate=US_RATE, deduct=US_DEDUCT):
    """TQQQ B 직투 — 한도 없음 · 전환마다 실현 · 연내 통산 · 연 250만 공제 · 이월 불가."""
    v = b = 0.0
    ybal, cy = 0.0, yr[s]
    paid = 0.0
    last = s

    def settle(vv, bal):
        return vv - max(bal - deduct, 0.0) * rate if bal > 0 else vv

    for t, kind in _events(s, e, sw):
        v *= a[t] / a[last]
        last = t
        if yr[t] != cy:
            v = settle(v, ybal)                       # 세금은 평가액에서만 빠진다(원가 불변)
            ybal, cy = 0.0, yr[t]
        if kind == 'c':
            v += pm
            b += pm
            paid += pm
        else:
            gain = v - b
            ybal += gain
            b = v
    v *= a[e] / a[last]
    if yr[e] != cy:
        v = settle(v, ybal)
        ybal = 0.0
    ybal += v - b
    v = settle(v, ybal)
    return v, paid


# =============================================================================
# [결함 개선 2026-09-03, 소유자 「방법론적 결함등은 다 개선할순없어?」]
# =============================================================================
# 고칠 수 있어서 고친 것 둘 — **결론이 바뀐다**.
#
# ① **합성 3배가 실물 TQQQ 보다 연 1.26%p 낮게 잡혀 있었다.**
#    현행 `lev_r(D,k) = k*r - (k-1)*c_daily` 는 2배 실물에서 역산한 c_daily 를
#    **(k-1) 에 비례**시킨다. 차입분은 그게 맞지만 **운용보수는 k 에 비례하지 않는다**
#    (lev_r 의 docstring 이 이미 그렇게 적어 놓고 크기를 안 쟀다).
#    실물 TQQQ(2010-02~, `data/hist/yahoo_TQQQ.csv`)로 **build_ext 와 같은 방법**
#    (c_k = mean(k*r_idx − r_real))으로 역산:
#        현행 가정 c(3) = 2*c_daily = 연 6.59%p
#        실물 역산 c(3)            = 연 **5.33%p**   ← C3_REAL
#    검증: 같은 방법으로 k=2 를 역산하면 0.012774%/일 로 규약 c_daily 0.013076% 와
#    3.0e-06 차 — **방법 재현 확인**. 크기의 정체도 맞는다(QLD 보수 0.95%×2 − TQQQ 0.84% ≈ 1.06%p).
#    ⚠ 한계: 실물 TQQQ 는 **2010-02 이후뿐**이고 그 구간은 저금리기다. 차입비용은 단기금리를
#      따라가므로 고금리 시대(1970~80년대)에는 **양쪽 다** 과소평가된다. 다만 **상대 편향**
#      (3배 vs 2배)은 대부분 보수 항목이라 금리와 무관 — 그래서 이 보정은 수준보다 견고하다.
#
# ② **환 효과가 빠져 있었다.** 418660 은 **원화환산 지수의 2배**라 환노출 ×2 이고
#    TQQQ 직투는 ×1 이다. 방어 3다리도 전부 환노출이다.
#        전략 B(원화)   = 2*[(1+r)(1+rfx)−1] − c2
#        TQQQ B(원화)   = (1 + 3r − c3)(1+rfx) − 1
#    ⚠ 환율(FRED DEXKOUS)은 **1981-04 부터** — 원화 기준 창은 45.5년으로 짧아진다.
#    ⚠ **방향이 창에 따라 다르다**(§-1 ⑧): 1981~ 에서는 3배에 불리(2.46→1.22),
#      21세기에서는 3배에 유리(1.27→1.39). 1981~2000 의 급격한 원화 약세를 ×2 로 먹은 탓.
#      **환 주장에는 반드시 창을 붙여라.**
#    ⚠ 원화 배수는 **원화 가치 하락을 포함**한다(1981 680원 → 2026 1,385원).
#      달러 기준과 **수준**을 비교하지 마라 — 의미 있는 것은 **같은 통화 안의 비(比)**다.
#
# 순효과 (21세기 26.6년 · TQQQ B 직투 ÷ 전략 B ISA):
#   ① 현행 1.00배 → ② 실물보정 1.27 → ③ 환만 1.10 → **④ 둘 다 1.39배**
#   (전략 B MDD −49.6% → −53.2% · TQQQ B −62.5% → −61.3%)
#
# ⛔ **못 고치는 것** — 방법이 아니라 자료·미래의 한계다:
#   · 30년 창이 1.8개 — 표본이 55년뿐이다. 더 긴 나스닥 데이터가 없다.
#   · ISA 제도가 30년 유지될지 — 미래의 정책이다.
#   · 블록 부트스트랩이 다년 약세장을 자르는 편향 — 완화만 되고 제거는 안 된다.
#   · 금소세·건보료 이점 — 소유자 소득 구조에 달렸다(가정 없이는 못 잰다).

C3_REAL = 0.00021170          # 실물 TQQQ 역산 (연 5.33%p) — 위 ① 참조
FX_CSV = 'data/hist/fred_DEXKOUS.csv'


def cost_k(k, c2):
    """배율별 합성비용. 차입분은 (k-1) 비례, 보수는 비비례 — 2배·3배 실측 두 점을 선형 보간."""
    return c2 + (k - 2.0) * (C3_REAL - c2)


def build2(krw=False, real3x=True):
    """보정 곡선 두 벌을 만든다.
       dom = 국내(418660 계열) — 원화 기준이면 **환노출 x2**(원화환산 지수의 2배)
       us  = 미국 직투        — 원화 기준이면 **환노출 x1**(달러 자산 x 환율)
    반환 (idx, wB, dom, us, s0). 달러 기준(krw=False)이면 dom == us 이고 s0=0."""
    import pandas as pd
    import hist_data as H
    G, X = EC.selfcheck()
    idx = G.idx
    D = G.D
    px = pd.Series(D['px'], index=idx)
    r = np.nan_to_num(px.pct_change().values)
    wB = np.asarray(G.wB, float)
    MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    c2 = D['c_daily']
    ck = (lambda k: cost_k(k, c2)) if real3x else (lambda k: (k - 1) * c2)

    if not krw:
        cur = {k: np.asarray(EC.sim2(wB, k * r - ck(k), MIX), float) for k in KS}
        return idx, wB, cur, cur, 0

    f = H._fred(FX_CSV, 'DEXKOUS')
    fxs = f.reindex(idx.union(f.index)).ffill().reindex(idx)
    rfx = np.nan_to_num(fxs.pct_change().values)
    s0 = int(np.searchsorted(idx, fxs.first_valid_index())) + 1
    dfs = (1 + MIX) * (1 + rfx) - 1                 # 방어 3다리 전부 환노출 x1
    rk = (1 + r) * (1 + rfx) - 1                    # 원화환산 지수
    dom = {k: np.asarray(EC.sim2(wB, k * rk - ck(k), dfs), float) for k in KS}
    us = {k: np.asarray(EC.sim2(wB, (1 + (k * r - ck(k))) * (1 + rfx) - 1, dfs), float)
          for k in KS}
    return idx, wB, dom, us, s0
