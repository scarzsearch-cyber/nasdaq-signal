# -*- coding: utf-8 -*-
"""
[사실 확인] 전략 B ISA(국내) vs 3배 B 직투 — **세후로 비교하면 순위가 바뀌나** (2026-09-03, 소유자 질문)

소유자: 「미국직투계좌의 세금도 계산해야 해. 세전으로 하면 QLD ISA 가 너무 불리하니.」
→ 정확한 지적이다. §5-35·LEVERAGE_US.md 의 k 격자는 **전부 세전**이고, 그 표에서 3배가 2배를
  이기는 것은 **세금을 안 낸 3배**다. 실제로는 3배를 사려면 **해외계좌로 나가야 하고**(국내 3배 미상장),
  그 순간 ISA 의 과세이연을 잃는다.

⚠ **전략 무접촉 · 채택 아님 · 권고 아님.** LEVERAGE_US.md §1~§9 의 세전 비교에
  계좌 제약·세금·환노출 차이를 넣어 재판정한다. 결론은 출력값에서 따로 읽는다.

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
    P1 세전 3배 우위가 세후에는 **크게 줄지만 안 뒤집힌다**.
    P2 ISA 의 과세이연이 지평이 길수록 유리해져 **긴 창일수록 격차가 좁혀진다**.
    P3 해외직투는 매년 정산이라 **연내 손익통산의 값어치가 작다**(전환이 연 2~3회뿐).
    P4 「같은 배율(k=2)끼리」면 ISA 가 해외직투를 이긴다.

축퇴 검산(§5-38 교훈): 세율을 0 으로 두면 세전 공표 곡선이 그대로 나와야 한다.
  ★ 그 교훈이 나온 사고가 정확히 이 자리다 — 세금 루프를 새로 짜다 한 칸을 더 밀어
    세전이 반토막 났고, 검산을 넣고서야 잡혔다. 여기서는 assert 로 강제한다.

실행: python research/tax_us_direct.py [--emit] [--c21] [--accum] [--windows]
      --c21 은 21세기(2000~) 격자만 찍는다 — **화면에 싣는 기준은 이쪽이다**(v131).
      --emit 은 아티팩트용 JSON 을 stdout 끝에 찍는다(파일 쓰기 0).
      --accum 은 월 100만원 적립·ISA 한도 및 요인별 비교를 재현한다.
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

ISA_RATE, GEN_RATE, US_RATE = 0.099, 0.154, 0.22
COST = 0.001
L = '=' * 104
KS = tuple(round(2.0 + 0.1 * i, 1) for i in range(11))     # 2.0 ~ 3.0


def build():
    """공표 비교에 쓰는 보정 엔진.

    국내는 원화환산 지수의 배율(환노출 x2), 직투는 달러 ETF 뒤 환산(환노출 x1)이며
    3배 비용은 실물 TQQQ 역산값을 쓴다. 구현은 파일 아래 build2 한 곳에만 둔다.
    """
    return build2(krw=True, real3x=True)


def switches(w):
    """전환이 일어난 인덱스 (비중이 바뀐 날)."""
    return np.where(np.abs(np.diff(w)) > 1e-9)[0] + 1


def strip_switch_cost(a, sw, cost=COST):
    """sim2 곡선에서 전환일 비용만 벗겨 세금 엔진이 매도 전에 직접 적용하게 한다."""
    a = np.asarray(a, float)
    g = np.ones(len(a), float)
    g[1:] = a[1:] / a[:-1]
    use = np.asarray([int(i) for i in sw if 0 < i < len(a)], int)
    if len(use):
        g[use] /= (1 - cost)
    return np.cumprod(g)


def after_isa(a, s, e, rate=ISA_RATE):
    """계좌 안 무과세 · 만기 1회 정산."""
    g = a[e] / a[s]
    return 1 + (g - 1) * (1 - rate) if g > 1 else g


def after_gen(a, sw, s, e, rate=GEN_RATE, cost=COST):
    """매도마다 과세 · 손실 상계 없음(배당소득).

    sw 는 **집행 비중**이 바뀌는 날이다. 전환은 그날 수익 전에 일어나므로 i일
    매도의 평가액은 a[i]가 아니라 전일 종가 a[i-1]이다.
    """
    v, basis, last = 1.0, 1.0, s
    for i in sw:
        if s < i <= e:
            v *= a[i - 1] / a[last]
            v *= 1 - cost
            gain = max(v - basis, 0.0)
            v -= gain * rate
            basis = v
            last = i - 1
    v *= a[e] / a[last]
    v -= max(v - basis, 0.0) * rate                    # 지평 끝 청산
    return v


def after_us(a, sw, yr, s, e, rate=US_RATE, deduct=0.0, cost=COST):
    """해외직투: 전환 실현 · 연내 손익통산 · 이월 불가 · 매년 정산.

    세금은 계좌에서 꺼내는 것으로 모델링하므로 납부 뒤 남은 취득원가도 같은 비율로
    줄인다. 연중 전환이 없어도 전년도 세금을 제때 내도록 모든 연말을 이벤트로 넣는다.
    """
    v, basis, last, ybal = 1.0, 1.0, s, 0.0

    def settle(vv, bb, bal):
        tax = max(bal - deduct, 0.0) * rate
        if tax <= 0:
            return vv, bb, 0.0
        if tax >= vv:
            raise ValueError('세금이 계좌 평가액 이상이다')
        basis_sold = bb * (tax / vv)
        carry = tax - basis_sold
        return vv - tax, bb - basis_sold, carry

    # 이벤트 좌표는 모두 장 마감 인덱스다. 같은 전일 종가에서 연말 정산과 다음해
    # 첫날 전환이 겹치면 연말을 먼저 닫고, 전환 손익은 새해 몫으로 잡는다.
    events = []
    for j in np.where(np.asarray(yr[:-1]) != np.asarray(yr[1:]))[0]:
        if s <= j < e:
            events.append((int(j), 0, 'year'))
    for i in sw:
        if s < i <= e:
            events.append((int(i - 1), 1, 'switch'))

    for t, _, kind in sorted(events):
        v *= a[t] / a[last]
        last = t
        if kind == 'year':
            v, basis, carry = settle(v, basis, ybal)
            ybal = carry                                  # 세금 마련용 매도의 새해 손익
        else:
            v *= 1 - cost
            ybal += v - basis
            basis = v

    v *= a[e] / a[last]
    ybal += v - basis                                  # 지평 끝 청산
    tax = max(ybal - deduct, 0.0) * rate
    if tax >= v and tax > 0:
        raise ValueError('세금이 계좌 평가액 이상이다')
    v -= tax
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
    if '--windows' in sys.argv:
        disjoint_report()
        return
    if '--accum' in sys.argv:
        accumulation_report()
        return
    if '--c21' in sys.argv:
        c21()
        return
    emit = '--emit' in sys.argv
    idx, wB, dom, us, S = build()
    n = len(idx)
    exec_pos = np.r_[wB[0], wB[:-1]]
    sw = switches(exec_pos)
    yr = idx.year.values
    dom_tax = {k: strip_switch_cost(dom[k], sw) for k in KS}
    us_tax = {k: strip_switch_cost(us[k], sw) for k in KS}

    def val(k, mode, s, e):
        a = us[k] if mode in ('us', 'pre') else dom[k]
        if mode == 'pre':
            return a[e] / a[s]
        if mode == 'isa':
            return after_isa(a, s, e)
        if mode == 'gen':
            return after_gen(dom_tax[k], sw, s, e)
        return after_us(us_tax[k], sw, yr, s, e)

    print(L)
    print('전략 B ISA vs 3배 B 직투 — 세후 비교 (전략 무접촉 · 채택 아님)')
    print(L)
    print('  창 {} ~ {} · 전환 {}회 · ISA {:.1f}%(만기1회) · 일반 {:.1f}%(매도마다) · 해외 {:.0f}%(연간정산)'
          .format(idx[S].date(), idx[-1].date(), len(sw[(sw > S)]),
                  ISA_RATE * 100, GEN_RATE * 100, US_RATE * 100))
    print('  원화 기준: 국내 418660 계열은 환노출 x2 · 미국 직투는 환노출 x1.')
    print('  3배 비용은 2010년 이후 실물 TQQQ 역산값을 사용(그 이전은 합성).')

    # ── 축퇴 검산 (§5-38 교훈 · assert 로 강제) ──────────────────────────────
    z = after_us(us_tax[2.0], sw, yr, S, n - 1, rate=0.0)
    zi = after_isa(dom[3.0], S, n - 1, rate=0.0)
    zg = after_gen(dom_tax[2.0], sw, S, n - 1, rate=0.0)
    pre2 = us[2.0][-1] / us[2.0][S]
    pre3dom = dom[3.0][-1] / dom[3.0][S]
    pre2dom = dom[2.0][-1] / dom[2.0][S]
    print('  [검산] 세율 0 → 해외 {:,.3f} · ISA {:,.3f} · 일반 {:,.3f} vs 세전 {:,.3f} / {:,.3f}'
          .format(z, zi, zg, pre2, pre3dom))
    assert abs(z / pre2 - 1) < 1e-9, '해외 축퇴 검산 실패'
    assert abs(zi / pre3dom - 1) < 1e-9, 'ISA 축퇴 검산 실패'
    assert abs(zg / pre2dom - 1) < 1e-9, '일반 축퇴 검산 실패'
    print()

    print('[원화자료 전체 창 · 1 → 얼마]  ※ 이름 규약: 전략 B 규칙을 쓰면 이름 뒤에 B (CLAUDE §3)')
    print('  {:<26}{:>16}{:>13}'.format('', '세후 최종배수', 'vs 전략 B ISA'))
    base = val(2.0, 'isa', S, n - 1)
    out54 = {}
    for nm, k, mode in ROWS:
        v = val(k, mode, S, n - 1)
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
            vs = [val(k, mode, s, s + W) for s in range(S, n - W, 21)]
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
    pre_gap = (us[3.0][-1] / us[3.0][S]) / (dom[2.0][-1] / dom[2.0][S])
    post_gap = r['3배 B 직투 22%'] / r[BASE]
    g_by_h = [tbl['3배 B 직투 22%'][h] / tbl[BASE][h] for h in HS]
    p2_ok = all(b < a for a, b in zip(g_by_h, g_by_h[1:]))
    print('예측 대조:')
    print('  P1 세후에도 3배가 앞선다(안 뒤집힌다) → {}  (세전 {:.1f}배 → 세후 {:.2f}배)'
          .format('맞음' if post_gap > 1 else '**틀림**', pre_gap, post_gap))
    print('  P2 지평이 길수록 ISA 가 따라붙는다 → {}  (5/10/20/30년 {})'
          .format('맞음' if p2_ok else '**틀림**',
                  ' → '.join('{:.2f}배'.format(v) for v in g_by_h)))
    print('  P4 같은 k=2 면 ISA > 해외직투 → {}  ({:,.0f}배 vs {:,.0f}배)'
          .format('맞음' if r[BASE] > r['전략 B 직투 22%'] else '**틀림**',
                  r[BASE], r['전략 B 직투 22%']))
    print()
    # ── 세후 손익분기 배율 — 해외직투 k 가 몇이면 ISA 2배와 같아지나 ──────────
    full_years = (idx[-1] - idx[S]).days / 365.25
    full_label = '전체 {:.1f}년'.format(full_years)
    print('[세후 손익분기 배율 — 직투 배율이 몇이어야 전략 B ISA 와 같아지나]')
    print('  {:<8}'.format('k') + ''.join('{:>12}'.format('%d년' % h) for h in HS)
          + '{:>12}'.format(full_label))
    grid = {}
    for k in KS:
        line = '  {:<6.1f}'.format(k)
        grid[k] = {}
        for h in HS:
            W = int(252 * h)
            m = float(np.median([val(k, 'us', s, s + W) for s in range(S, n - W, 21)]))
            grid[k][h] = m / tbl[BASE][h]
            line += '{:>11.2f}배'.format(grid[k][h])
        gfull = val(k, 'us', S, n - 1) / base
        grid[k]['full'] = gfull
        line += '{:>11.2f}배'.format(gfull)
        print(line)
    print('  ※ 1.00 을 넘는 첫 k 가 손익분기다 — 그 아래면 ISA 에 그냥 두는 쪽이 낫다.')
    be = {}
    for h in list(HS) + ['full']:
        hit = [k for k in KS if grid[k][h] >= 1.0]
        be[str(h)] = hit[0] if hit else None
        lab = full_label if h == 'full' else '{}년'.format(h)
        print('    {:>9} 손익분기 k = {}'.format(
            lab, '{:.1f}'.format(hit[0]) if hit else '3.0 에서도 미달'))
    print()

    print('[이 측정이 낳은 질문]')
    print('  Q-a ISA 한도(연 2,000만·총 1억)를 넘는 돈은 ISA 밖이다 — 규모가 커지면')
    print('      비교가 「ISA vs 해외」가 아니라 「일반 15.4% vs 해외 22%」로 바뀐다.')
    print('      그 열이 위 표의 2·3행이다(해외는 연내 손익통산이 되지만 손실 이월은 안 된다).')
    print('  Q-b 환노출 차이(국내 x2 · 직투 x1)는 원화로 반영했다. 환 효과의 방향은')
    print('      창에 따라 바뀌므로 「환 때문」이라고 쓸 땐 같은 창의 환 유무 열을 대조해야 한다.')
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
            cmet = us[k][S:] / us[k][S]
            m = fullmet(cmet)
            m['k'] = k
            m['isa'] = round(val(k, 'isa', S, n - 1), 0)
            m['us'] = round(val(k, 'us', S, n - 1), 0)
            m['gen'] = round(val(k, 'gen', S, n - 1), 0)
            m['hIsa'] = {}
            m['hUs'] = {}
            m['hGen'] = {}
            m['hPre'] = {}
            for h in HS:
                W = int(252 * h)
                ss = range(S, n - W, 21)
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
              'full_period': {k: round(v, 2) for k, v in out54.items()},
              'full_period_years': round(full_years, 3),
              'horizon': {k: {str(h): round(v, 3) for h, v in d.items()}
                          for k, d in tbl.items()},
              'grid': {str(k): {str(h): round(v, 4) for h, v in d.items()}
                       for k, d in grid.items()},
              'breakeven': be,
              'switches': int(np.sum(sw > S)),
              'span': [str(idx[S].date()), str(idx[-1].date())]}
        print('\n===JSON===')
        print(json.dumps(js, ensure_ascii=False))




# =============================================================================
# [철회] 2026-09-03 옛 계산 이력 — 아래 수치·인과·동률은 현재 근거로 사용 금지.
# =============================================================================
# [철회] 옛 설명: 한 방이 아니라 두 방이라는 주장 (10년 단위 B 세전).
# [철회] 옛 값: 1972~81 4.07배 · 1982~91 8.73배 · 1992~2001 30.13배.
# [철회] 옛 값: 2002~11 3.11배 · 2012~21 26.59배 · 2022~26 2.10배.
# [철회] 옛 값: 최고 10년 하나 제외 199,448 → 6,167배(3.3%), 둘 제외 232배.
# [철회] 이 옛 선택 구간만으로 현재 모형의 성과 원인을 단정하지 않는다.
#
# [철회] 「세금 격차 자체는 버블 의존이 아니다」라는 옛 인과 주장은 현재 근거가 아니다.
# [철회] ISA÷해외 1.22 / 1.38 / 1.39 / 1.16 / 1.49 / 1.18 및 최대/최소 1.28은 옛 값.
# [철회] 「연 4.09%p는 구조적 · 6.28배는 고른 격차의 누적」이라는 일반화도 사용 금지.
#
# [철회] 21세기(2000~)에 대한 아래 옛 수치와 판정은 수정된 계산으로 대체됐다.
# [철회] QLD 2배 ISA 146.1배 vs TQQQ 3배 해외 146.6배 = 1.00배 동률 — 현재는 아님.
# [철회] 옛 MDD −49.6% → −62.5%, 「이득 0·낙폭만 12.9%p 악화」도 사용 금지.
# [철회] 옛 21세기 손익분기 k=3.0(54년 2.7) — 현재 --c21 격자로 확인할 것.
#
# ⚠ **v131 규약 위반이었다**: 「성과·배수 주장은 21세기 기준 · 54년은 폭락 검증용에만」이
#   이미 소유자 규정으로 있었는데 내가 54년 통짜를 표 머리에 올렸다. 소유자가 잡았다.
#   「데이터엔 넣되 표엔 넣지 마라」는 유지한다. 외부 아티팩트의 당시 편집 기록은
#   현재 화면이 교정 엔진을 반영했다는 증거가 아니다. v205에서 원본 미확인·재발행 보류.
#
# [정정] 현재 재현: 기본 실행은 원화자료 전체 약45.4년, --c21은 2000년 이후 한 구간.


# ★★★ 2026-09-04 코드리뷰: 연말 세금 정산 누락·세금 납부 후 취득원가·전환일
#   순서를 바로잡았다. 현재 값은 21세기 **283.9 / 161.5 = 1.76배**, 전체 45.4년
# [정정] 전체는 **253,390 / 145,135 = 1.75배**다. 위 1.00배·146.6은 철회된 옛 기록이다.
#   현재 재현: python research/tax_us_direct.py (원화자료 전체) · --c21 (21세기).
# [정정] 5년 9구간 중 B 6승(--windows)은 1981-04-14 시작이다. 2000년 이후를 나눈 결과가 아니다.
# [정정] 각 창은 한 번에 투자한 거치식이다. 기간별 결과를 모든 미래 시작일의 승률로 쓰지 않는다.


def c21():
    """21세기(2000~) 기준 k 격자 — v131 규정. 표에 싣는 것은 이쪽이다."""
    idx, wB, dom, us, s0 = build()
    sw = switches(np.r_[wB[0], wB[:-1]])
    us_tax = {k: strip_switch_cost(us[k], sw) for k in KS}
    yr = idx.year.values
    m = np.where((yr >= 2000) & (np.arange(len(idx)) >= s0))[0]
    S, E = m[0], m[-1]
    base = after_isa(dom[2.0], S, E)
    base_seg = dom[2.0][S:E + 1] / dom[2.0][S]
    base_dd = base_seg / np.maximum.accumulate(base_seg) - 1
    base_mdd = 100 * float(base_dd.min())
    print('21세기 {} ~ {} ({:.1f}년) · 전략 B ISA {:.1f}배 · MDD {:.1f}%'
          .format(idx[S].date(), idx[E].date(), len(m) / 252.0, base, base_mdd))
    print('  {:<6}{:>10}{:>10}{:>10}{:>10}{:>9}'
          .format('k', '세전', 'ISA', '해외', 'vs ISA2', '직투MDD'))
    for k in KS:
        a_dom, a_us = dom[k], us[k]
        seg = a_us[S:E + 1] / a_us[S]
        d = seg / np.maximum.accumulate(seg) - 1
        u = after_us(us_tax[k], sw, yr, S, E)
        print('  {:<6.1f}{:>9.1f}배{:>9.1f}배{:>9.1f}배{:>9.2f}배{:>8.1f}%'
              .format(k, a_us[E] / a_us[S], after_isa(a_dom, S, E), u, u / base, 100 * d.min()))
    k3 = KS[-1]
    k3_seg = us[k3][S:E + 1] / us[k3][S]
    k3_dd = 100 * float((k3_seg / np.maximum.accumulate(k3_seg) - 1).min())
    k3_post = after_us(us_tax[k3], sw, yr, S, E)
    print('  실제 선택지: 전략 B ISA {:.1f}배 / {:.1f}% vs 3배 B 직투 {:.1f}배 / {:.1f}%'
          .format(base, base_mdd, k3_post, k3_dd))
    print('  ※ 이 표가 화면(아티팩트 배율 탭)에 실리는 기준이다. 원화자료 전체 창은 위 main() 에만.')


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


def accum_B(a, sw, yr, s, e, pm, isa_free=ISA_FREE, r_isa=ISA_RATE, r_gen=GEN_RATE,
            year_cap=ISA_YEAR_CAP, total_cap=ISA_TOTAL_CAP, cost=COST):
    """전략 B — ISA 버킷 + 한도 초과분 일반 버킷. 반환 (세후 평가액, 총 납입, ISA 소진 시점 년)"""
    iv = ib = gv = gb = 0.0
    isa_paid = 0.0
    ypaid, cy = 0.0, yr[s]
    paid = 0.0
    full_at = None
    swi = set(int(t) for t in sw if s < t <= e)
    for t in range(s + 1, e + 1):
        if yr[t] != cy:
            ypaid, cy = 0.0, yr[t]
        g = a[t] / a[t - 1]
        if t in swi:                                  # 장 시작 전환: 전일 종가에서 실현
            # 입력 sim2 곡선의 비용을 분리해 매도대금에서 먼저 차감한다.
            # 비용 차감 후 실현손익을 과세해야 after_gen과 순서가 같다.
            iv *= 1 - cost
            gv *= 1 - cost
            g /= 1 - cost
            gain = gv - gb
            if gain > 0:
                gv -= gain * r_gen
            gb = gv

        iv *= g
        gv *= g
        if (t - s) % 21 == 0:
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
    iv -= max(iv - ib - isa_free, 0.0) * r_isa        # ISA 만기 1회 정산(서민형 비과세 차감)
    gv -= max(gv - gb, 0.0) * r_gen                   # 일반 만기 청산
    return iv + gv, paid, full_at


def accum_US(a, sw, yr, s, e, pm, rate=US_RATE, deduct=US_DEDUCT, cost=COST):
    """TQQQ B 직투 — 한도 없음 · 전환마다 실현 · 연내 통산 · 연 250만 공제 · 이월 불가."""
    v = b = 0.0
    ybal, cy = 0.0, yr[s]
    paid = 0.0

    def settle(vv, bb, bal):
        tax = max(bal - deduct, 0.0) * rate
        if tax <= 0 or vv <= 0:
            return vv, bb, 0.0
        if tax >= vv:
            raise ValueError('세금이 계좌 평가액 이상이다')
        basis_sold = bb * tax / vv
        return vv - tax, bb - basis_sold, tax - basis_sold

    swi = set(int(t) for t in sw if s < t <= e)
    for t in range(s + 1, e + 1):
        if yr[t] != cy:
            v, b, carry = settle(v, b, ybal)
            ybal, cy = carry, yr[t]                  # 세금 마련용 매도 손익은 새해에 포함
        g = a[t] / a[t - 1]
        if t in swi:                                  # 장 시작 전환: 전일 종가에서 실현
            v *= 1 - cost
            g /= 1 - cost
            ybal += v - b
            b = v

        v *= g
        if (t - s) % 21 == 0:
            v += pm
            b += pm
            paid += pm
    ybal += v - b
    v, _, _ = settle(v, b, ybal)
    return v, paid


def accumulation_report():
    """같은 원화 곡선·시작창에서 적립과 계좌 한도의 효과를 한 단계씩 잰다."""
    idx, w, dom, us, start = build()
    sw = switches(np.r_[w[0], w[:-1]])
    yr = idx.year.values
    print('적립 재검산: {}~{} · 21거래일마다 100만원 · 시작일 보폭 21일'.format(
        idx[start].date(), idx[-1].date()))
    print('금액 단위 만원 · 중앙값은 같은 시작창 집합에서 각각 계산 · 실제 달력 월납입의 근사')
    for h in (5, 10, 20, 30):
        width = 252 * h
        starts = list(range(start, len(idx) - width, 21))
        b = np.array([accum_B(dom[2.0], sw, yr, s, s + width, 100)[0] for s in starts])
        u = np.array([accum_US(us[3.0], sw, yr, s, s + width, 100)[0] for s in starts])
        print('{}년 n={} · B 중앙 {:.1f} / p05 {:.1f} · 3배 B 직투 중앙 {:.1f} / p05 {:.1f} · 비 {:.4f}'.format(
            h, len(starts), np.median(b), np.quantile(b, .05), np.median(u),
            np.quantile(u, .05), np.median(u) / np.median(b)))
        if h == 30:
            u2 = [accum_US(us[2.0], sw, yr, s, s + width, 100)[0] for s in starts]
            bi = [accum_B(dom[2.0], sw, yr, s, s + width, 100,
                           isa_free=0, year_cap=np.inf, total_cap=np.inf)[0] for s in starts]
            print('30년 단위 대조(ISA 한도 무한): ISA {:.1f}만원 / 직투2배 {:.1f}만원 · 납입 36000만원'.format(
                np.median(bi), np.median(u2)))
        if h != 20:
            continue
        # 거치→적립→ISA 한도→해외 공제→ISA 공제 순서. 다른 축은 고정한다.
        u_tax = strip_switch_cost(us[3.0], sw)
        lump_b = np.array([after_isa(dom[2.0], s, s + width) for s in starts])
        lump_u = np.array([after_us(u_tax, sw, yr, s, s + width) for s in starts])
        inf_b = np.array([accum_B(dom[2.0], sw, yr, s, s + width, 100,
                                  isa_free=0, year_cap=np.inf, total_cap=np.inf)[0] for s in starts])
        cap_b = np.array([accum_B(dom[2.0], sw, yr, s, s + width, 100,
                                  isa_free=0)[0] for s in starts])
        nod_u = np.array([accum_US(us[3.0], sw, yr, s, s + width, 100,
                                  deduct=0)[0] for s in starts])
        stages = [np.median(lump_u) / np.median(lump_b),
                  np.median(nod_u) / np.median(inf_b),
                  np.median(nod_u) / np.median(cap_b),
                  np.median(u) / np.median(cap_b), np.median(u) / np.median(b)]
        print('20년 요인 분해: ' + ' -> '.join('{:.5f}'.format(v) for v in stages))
        print('직전 단계 대비: ' + ' / '.join('{:+.2%}'.format(y / x - 1) for x, y in zip(stages, stages[1:])))
    print('다음 질문: 해외 방어자산 구성·배당 원천징수·금융소득종합과세는 이 단순화 모형 밖이다.')


def disjoint_report():
    """원화자료 시작부터 겹치지 않게 자른 모든 완전한 창. 거치식 비교."""
    idx, w, dom, us, start = build()
    sw = switches(np.r_[w[0], w[:-1]])
    yr = idx.year.values
    a = strip_switch_cost(us[3.0], sw)
    for h in (5, 10, 20, 25, 30):
        width = 252 * h
        rows = [(s, after_us(a, sw, yr, s, s + width) / after_isa(dom[2.0], s, s + width))
                for s in range(start, len(idx) - width, width)]
        print('{}년 · 완전한 창 {}개 · B승 {} · {}'.format(
            h, len(rows), sum(v < 1 for _, v in rows),
            ' / '.join('{}~{} {:.4f}'.format(idx[s].date(), idx[s + width].date(), v) for s, v in rows)))
    print('시작점을 원화자료 첫날에 고정한 서술용 표다. 시작점 선택에 따른 차이를 일반화하지 않는다.')


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
#    ⚠ **방향이 창에 따라 다르다**(§-1 ⑧): 세금 엔진 수정 후 같은 창에서
#      1981~ 은 3배에 불리(3.25→1.75), 21세기는 3배에 유리(1.57→1.76)다.
#      **환 주장에는 반드시 창을 붙여라.**
#    ⚠ 원화 배수는 **원화 가치 하락을 포함**한다(1981 680원 → 2026 1,385원).
#      달러 기준과 **수준**을 비교하지 마라 — 의미 있는 것은 **같은 통화 안의 비(比)**다.
#
# 순효과 (21세기 26.6년 · TQQQ B 직투 ÷ 전략 B ISA, 수정 세금 엔진):
#   ① 달러·합성 1.23배 → ② 실물보정 1.57 → ③ 환만 1.38 → **④ 둘 다 1.76배**
#   (전략 B MDD −53.2% · TQQQ B −61.3%)
#
# ⛔ **못 고치는 것** — 방법이 아니라 자료·미래의 한계다:
#   · 현재 원화 표본은 약45.4년. 시작점 고정으로 완전히 자른 30년 창은 1개뿐이다.
#   · ISA 제도가 30년 유지될지 — 미래의 정책이다.
#   · 옛 재표집 구간은 경로·전환일 불일치로 사용 중지. 유효한 대체 구간을 만들었다고 하지 않는다.
#   · 금소세·건보료 이점 — 소유자 소득 구조에 달렸다(가정 없이는 못 잰다).

C3_REAL = 0.00021170          # 실물 TQQQ 역산 (연 5.33%p) — 위 ① 참조
FX_CSV = 'data/hist/fred_DEXKOUS.csv'


def cost_k(k, c2):
    """배율별 합성비용. 차입분은 (k-1) 비례, 보수는 비비례 — 2배·3배 **실측 두 점을 선형 보간**.

    ⚠ **정의역은 k ∈ [2, 3] 뿐이다.** 두 점 보간이라 밖으로 나가면 뜻이 없다 —
      k=1 에 넣으면 연 +1.26%p 가 나오는데 **1배 상품의 비용은 0 이어야 한다**
      (2026-09-03 자체 점검에서 적발 · 실사용은 KS=2.0~3.0 이라 안 걸렸다).
      밖에서 부르면 예외를 던진다. 1배가 필요하면 lev_r 규약((k−1)·c_daily)을 쓰라.
    """
    if not (2.0 - 1e-9 <= k <= 3.0 + 1e-9):
        raise ValueError(
            'cost_k 의 정의역은 k∈[2,3] 이다 (2배·3배 실측 두 점 보간). k=%r 은 밖이다.' % k)
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


if __name__ == '__main__':
    main()
