# -*- coding: utf-8 -*-
"""
[v81] T4 심층 후속 — 가상 하락장 해부 + 시간 추세 + 운용 단순화 + B×T4 혼합

소유자 질문 (2026-08-29):
  Q1 닷컴·2008 의 B 승이 우연인가 → 가상의 하락장 다수 시뮬레이션으로 볼 수 있나?
  Q2 독립 도피 사건 방어를 보면 앞으로 T4 가 점점 강해지는 건가?
  Q3 T4 의 운용 단순성을 높일 수 없나?
  Q4 현행 B 와 T4 의 장점을 혼합할 수 없나?

[진단 전용 선언] 채택 후보 탐색이 아니다. T4 파라미터·채택안·그림자 기록 무변경.
합성 데이터는 v41 관문의 증거로 쓸 수 없다(관문은 실데이터 전용) — 기전 이해용이다.

[★ 사전 고정 예측·판정 기준 — 실행 전에 적었다]
  S1 합성 지도: T4 사건 MDD 승률은 ① 변동성 선행(lead)↑ 에 단조 증가,
     ② 하락 기간(Tc)↑ 에 단조 감소, ③ 곰랠리 진폭(A)↑ 에 단조 감소할 것.
     세 축 모두 예측 방향이면 "닷컴·2008 B 승 = 우연이 아니라 구조" 판정.
     (닷컴형 = 느림·랠리 큼 / 1987형 = 빠름·선행 큼 — 실측 국면과 대응 확인)
  S2 시간 추세: 실측 독립 사건 22회를 연대순 전반 11/후반 11 로 나눠
     승률 차가 이항 2σ(n=11, p̂=0.77 → ±25%p) 이내면 "강해지는 추세 근거 없음".
  S3 양자화(w 를 0/¼/½/¾/1 로 반올림): 최종 ±5% 이내 AND MDD 악화 ≤1%p 면
     "운용 단순화로 유효" (중간비중 일수·조정 횟수 감소량 병기).
  S4 혼합(자본 분할 x·B + (1−x)·T4): "장점 결합"의 인정 조건 =
     어떤 x 에서 Calmar > max(단독 둘) AND MDD > max(단독 둘) AND 최종 ≥ min(단독 둘).
     아니면 "평균화일 뿐" 판정. (신호 결합 계열은 재시험 금지 — dd-OR v68 기각,
     B 위 변동성 사이징 = 변동성 조기방어 v32/v40 기각, 앙상블 v55 기각.)

[합성 하락장 생성기] 상승 600일(12%/yr·σ18%) → 정점 전 lead 일 동안 σ 를 40% 로
  램프(가격은 횡보) → 하락 Tc 일에 로그 −45% 도달(σ40%), 곰랠리 2회(각 +A 로그) 삽입
  → 회복 500일(18%/yr, σ 는 126일에 걸쳐 18% 로 복귀). 시드 200개/설정.
  전략 규약은 실측과 동일: 2배 = 2r − c_daily(실측 역산), 방어 = 현금 2%/yr,
  lag=1, 편도 0.1%, B = −16/−16 · 252일, T4 = vt40/th2/창20/룩백 4종 (불변).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

from axis_lib import sim, COST
from research_kit import dist, fmt_dist, verdict
from axis_t4_shadow import build, met, LOOKS, TH, VT, WIN

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

S_SEEDS = 200
N_BULL, N_REC = 600, 500
SIG0, SIGC = 0.18, 0.40
DEPTH = np.log(0.55)                     # 기초지수 −45%


# ==================================================================== 생성기
def synth(Tc, lead, A, seed, depth=DEPTH, sigc=SIGC, S=S_SEEDS):
    """(일수, 시드) 로그수익 행렬. 국면 해부가 통제 변수다."""
    rng = np.random.default_rng(seed)
    mu, sg = [], []
    mu += [0.12 / 252] * (N_BULL - lead); sg += [SIG0] * (N_BULL - lead)
    for i in range(lead):                                   # 정점 전 σ 램프, 가격 횡보
        mu.append(0.0); sg.append(SIG0 + (sigc - SIG0) * (i + 1) / lead)
    downs = depth - 2 * A                                   # 랠리만큼 더 내려야 순 목표 깊이
    if A > 0:
        nd = max(1, int(Tc * 0.7 / 3)); nr = max(1, int(Tc * 0.3 / 2))
        segs = [(downs / 3, nd), (A, nr), (downs / 3, nd), (A, nr),
                (downs / 3, Tc - 3 * nd - 2 * nr if Tc - 3 * nd - 2 * nr > 0 else nd)]
    else:
        segs = [(downs, Tc)]
    for tot, ln in segs:
        mu += [tot / ln] * ln; sg += [sigc] * ln
    for i in range(N_REC):                                  # 회복, σ 복귀
        mu.append(0.18 / 252)
        sg.append(sigc + (SIG0 - sigc) * min(1.0, (i + 1) / 126))
    mu = np.array(mu)[:, None]; sg = np.array(sg)[:, None]
    z = rng.standard_normal((len(mu), S))
    return mu + sg / np.sqrt(252) * z


def strat_curves(lr, c_daily):
    """로그수익 행렬 -> (B 곡선, T4 곡선) 행렬. 실측과 같은 규약."""
    n, S = lr.shape
    px = np.exp(np.cumsum(lr, axis=0))
    r = np.expm1(lr)
    lev = 2 * r - c_daily
    cash = 0.02 / 252
    # dd (252 rolling max, min_periods 252)
    dd = np.full((n, S), 0.0)
    rm = pd.DataFrame(px).rolling(252, min_periods=252).max().values
    m = ~np.isnan(rm)
    dd[m] = px[m] / rm[m] - 1
    # B 상태기계 (벡터)
    wB = np.empty((n, S)); cur = np.ones(S)
    for i in range(n):
        cur = np.where(dd[i] <= -0.16, 0.0, np.where((cur < 1) & (dd[i] > -0.16), 1.0, cur))
        wB[i] = cur
    # T4
    votes = np.zeros((n, S))
    for k in LOOKS:
        v = np.zeros((n, S)); v[k:] = (px[k:] / px[:-k] > 1)
        v[:k] = 1                                           # 워밍업은 상승 국면
        votes += v
    rv = 2 * pd.DataFrame(r).rolling(WIN).std(ddof=1).values * np.sqrt(252)
    with np.errstate(divide='ignore', invalid='ignore'):
        wT = np.clip(VT / rv, 0, 1)
    wT[np.isnan(wT)] = 1.0
    wT[votes < TH] = 0.0
    out = []
    for w in (wB, wT):
        pos = np.vstack([w[:1], w[:-1]])                    # lag=1
        ret = pos * lev + (1 - pos) * cash
        turn = np.abs(np.diff(pos, axis=0, prepend=pos[:1]))
        out.append(np.cumprod((1 + ret) * (1 - COST * turn), axis=0))
    return out


def ep_mdd(c, lo):
    seg = c[lo:]
    return (seg / np.maximum.accumulate(seg, axis=0) - 1).min(axis=0)


def sec_synth(c_daily):
    print('=' * 100)
    print('S1. 합성 하락장 지도 — 어떤 해부에서 누가 이기나 (시드 %d/설정, 사건창 MDD 승률)' % S_SEEDS)
    print('=' * 100)
    Tcs = [10, 42, 126, 378, 756]
    leads = [0, 21, 63]
    As = [0.0, 0.15, 0.30]
    lo = N_BULL - 63
    grid = {}
    for lead in leads:
        print('\n  [변동성 선행 %d일]            곰랠리 0        +16%%        +35%%   | T4/B 최종 중앙' % lead)
        for Tc in Tcs:
            row = []; frm = []
            for A in As:
                lr = synth(Tc, lead, A, seed=hash((Tc, lead, A)) % 2 ** 31)
                cB, cT = strat_curves(lr, c_daily)
                mB = ep_mdd(cB, lo); mT = ep_mdd(cT, lo)
                row.append(float((mT > mB).mean()))
                frm.append(float(np.median(cT[-1] / cB[-1] - 1)))
                grid[(lead, Tc, A)] = row[-1]
            print('    하락 %4d일 (%s)   %6.0f%%      %6.0f%%      %6.0f%%   | %+5.0f%% ~ %+5.0f%%'
                  % (Tc, '1987형' if Tc <= 42 else ('닷컴형' if Tc >= 378 else '중간'),
                     row[0] * 100, row[1] * 100, row[2] * 100,
                     min(frm) * 100, max(frm) * 100))
    # 단조성 판정 (사전 예측 3축) — 위반 셀 수를 근거로 남긴다
    v_lead = sum(grid[(leads[i], t, a)] > grid[(leads[i + 1], t, a)] + 0.10
                 for i in range(len(leads) - 1) for t in Tcs for a in As)
    v_tc = sum(grid[(l, Tcs[i], a)] < grid[(l, Tcs[i + 1], a)] - 0.10
               for l in leads for i in range(len(Tcs) - 1) for a in As)
    v_a = sum(grid[(l, t, As[i])] < grid[(l, t, As[i + 1])] - 0.10
              for l in leads for t in Tcs for i in range(len(As) - 1))
    dot = grid[(0, 756, 0.30)]; s87 = grid[(63, 10, 0.0)]
    return [
        ('S1a 선행↑ → T4 승률↑ (±10%p 내 단조)', v_lead == 0, '위반 %d/30셀' % v_lead),
        ('S1b 기간↑ → T4 승률↓', v_tc == 0, '위반 %d/36셀' % v_tc),
        ('S1c 랠리↑ → T4 승률↓', v_a == 0, '위반 %d/30셀' % v_a),
        ('S1d 극단 대응: 닷컴형<50%<1987형', dot < 0.5 < s87,
         '닷컴형(느림·랠리·무선행) %.0f%% vs 1987형(급락·선행) %.0f%%' % (dot * 100, s87 * 100)),
    ]


def sec_synth_cal(c_daily):
    """[사후 추가 — 명기] 1차 지도(−45%·σ40 고정)가 사전 예측과 어긋났다(전역 T4 우세).
    원인 후보 둘을 가르기 위해 실측 위기의 해부(깊이·변동성·랠리)에 보정한 셀을 돌린다:
      (i) 생성기가 닷컴·2008 형을 재현 못 한 것인가 (보정 셀에서 B 과반승이면 재현)
      (ii) 실측의 B 승이 T4 우세 분포에서 나온 소수 추첨이었나 (보정 셀에서도 T4 과반승)
    보정값 출처: 실측 낙폭(닷컴 NDX −78%·2008 −54%)·실현변동성(45%/55%)·랠리 규모."""
    print()
    print('=' * 100)
    print('S1-보정. 실측 해부로 보정한 셀 (사후 추가 — 생성기 충실도 판별용, 시드 400)')
    print('=' * 100)
    cells = [
        ('닷컴 보정 (−78%·630일·랠리+42%·σ45·선행0)',
         dict(Tc=630, lead=0, A=0.35, depth=np.log(0.22), sigc=0.45)),
        ('2008 보정 (−54%·350일·랠리+20%·σ55·선행21)',
         dict(Tc=350, lead=21, A=0.18, depth=np.log(0.46), sigc=0.55)),
        ('1987 보정 (−35%·40일·무랠리·σ60·선행15)',
         dict(Tc=40, lead=15, A=0.0, depth=np.log(0.65), sigc=0.60)),
    ]
    out = {}
    lo = N_BULL - 63
    import zlib
    for nm, p in cells:
        # str hash 는 프로세스마다 솔트가 달라 재현이 안 된다 — crc32 로 고정
        lr = synth(p['Tc'], p['lead'], p['A'], seed=zlib.crc32(nm.encode('utf-8')),
                   depth=p['depth'], sigc=p['sigc'], S=400)
        cB, cT = strat_curves(lr, c_daily)
        mB = ep_mdd(cB, lo); mT = ep_mdd(cT, lo)
        win = float((mT > mB).mean())
        fr = cT[-1] / cB[-1] - 1
        out[nm[:2]] = win
        print('  %-42s T4 사건MDD 승률 %3.0f%% | T4/B 최종 중앙 %+.0f%% (P25 %+.0f%% · P75 %+.0f%%)'
              % (nm, win * 100, np.median(fr) * 100,
                 np.percentile(fr, 25) * 100, np.percentile(fr, 75) * 100))
    return [('S1e 보정 닷컴형에서 B 과반승 (생성기가 실측 재현)', out['닷컴'] < 0.5,
             '닷컴 보정 T4 승률 %.0f%% · 2008 보정 %.0f%% · 1987 보정 %.0f%%'
             % (out['닷컴'] * 100, out['20'] * 100, out['19'] * 100))]


def sec_trend(D, wT, wB, cT, cB):
    print()
    print('=' * 100)
    print('S2. 실측 22개 사건 — T4 방어 우위에 시간 추세가 있나')
    print('=' * 100)
    idx = D['idx']
    esc = np.where((wB[1:] == 0) & (wB[:-1] == 1))[0] + 1
    keep, last = [], None
    for e in esc:
        if last is None or (idx[e] - idx[last]).days > 252:
            keep.append(e)
        last = e
    wins = []
    for e in keep:
        a = max(0, e - 63); b = min(len(idx) - 1, e + 252)
        sT = cT.iloc[a:b]; sB = cB.iloc[a:b]
        wins.append(float((sT / sT.cummax() - 1).min()) > float((sB / sB.cummax() - 1).min()))
    h = len(keep) // 2
    w1, w2 = np.mean(wins[:h]), np.mean(wins[h:])
    per1 = '%s~%s' % (idx[keep[0]].year, idx[keep[h - 1]].year)
    per2 = '%s~%s' % (idx[keep[h]].year, idx[keep[-1]].year)
    print('  전반 %s: %d/%d (%.0f%%) | 후반 %s: %d/%d (%.0f%%)'
          % (per1, sum(wins[:h]), h, w1 * 100, per2, sum(wins[h:]), len(wins) - h, w2 * 100))
    sig2 = 2 * np.sqrt(0.77 * 0.23 / h)
    return [('S2 시간 추세 없음 (차이 ≤ 2σ=%.0f%%p)' % (sig2 * 100),
             abs(w2 - w1) <= sig2, '전반 %.0f%% vs 후반 %.0f%%' % (w1 * 100, w2 * 100))]


def sec_quant(D, wT):
    print()
    print('=' * 100)
    print('S3. 운용 단순화 — w 를 0/¼/½/¾/1 로 양자화하면 성과가 유지되나')
    print('=' * 100)
    rows = []
    for nm, w in (('연속(현행 정의)', wT), ('¼ 양자화', np.round(wT * 4) / 4)):
        for cost in (0.001, 0.002):
            c, sw = sim(D, w, cost=cost)
            m = met(c)
            yrs = (D['idx'][-1] - D['idx'][0]).days / 365.25
            turn = np.abs(np.diff(np.r_[w[0], w[:-1]], prepend=w[0])).sum() / yrs
            mid = float(((w > 0) & (w < 1)).mean())
            adj = int((np.abs(np.diff(w)) > 1e-9).sum())
            rows.append((nm, cost, m, turn, mid, adj / yrs))
            print('  {:<14s} 편도 {:.1f}%: 최종 {:,.0f}  MDD {:.1f}%  Calmar {:.3f}  연회전 {:.1f}  중간비중 {:.0f}%  조정 {:.0f}회/yr'
                  .format(nm, cost * 100, m['final'], m['mdd'] * 100, m['calmar'],
                          turn, mid * 100, adj / yrs))
    b1, q1 = rows[0], rows[2]
    ok = (abs(q1[2]['final'] / b1[2]['final'] - 1) <= 0.05
          and q1[2]['mdd'] >= b1[2]['mdd'] - 0.01)
    return [('S3 ¼ 양자화 유효 (최종 ±5%·MDD ≤1%p)', ok,
             '최종 %+.1f%% · MDD %+.2f%%p · 조정 %.0f→%.0f회/yr'
             % ((q1[2]['final'] / b1[2]['final'] - 1) * 100,
                (q1[2]['mdd'] - b1[2]['mdd']) * 100, b1[5], q1[5]))]


def sec_blend(D, wT, wB):
    print()
    print('=' * 100)
    print('S4. 자본 분할 혼합 x·B + (1−x)·T4 — 장점 결합인가 평균화인가 (편도 0.1%)')
    print('=' * 100)
    rB, _ = sim(D, wB); rT, _ = sim(D, wT)
    dr = np.corrcoef(rB.pct_change().dropna(), rT.pct_change().dropna())[0, 1]
    print('  두 전략 일간수익 상관: %.3f' % dr)
    best = {}
    solo = {}
    for x in np.round(np.arange(0, 1.01, 0.125), 3):
        w = x * wB + (1 - x) * wT
        c, _ = sim(D, w)
        m = met(c)
        if x in (0.0, 1.0):
            solo[x] = m
        best[x] = m
        print('  x={:.3f}  최종 {:,.0f}  MDD {:.1f}%  Calmar {:.3f}'
              .format(x, m['final'], m['mdd'] * 100, m['calmar']))
    mx_cal = max(solo[0.0]['calmar'], solo[1.0]['calmar'])
    mx_mdd = max(solo[0.0]['mdd'], solo[1.0]['mdd'])
    mn_fin = min(solo[0.0]['final'], solo[1.0]['final'])
    hit = [x for x, m in best.items() if 0 < x < 1 and m['calmar'] > mx_cal
           and m['mdd'] > mx_mdd and m['final'] >= mn_fin]
    for cost in (0.002,):                                  # 한국 실효비용 참조
        line = []
        for x in (0.0, 0.25, 1.0):
            c, _ = sim(D, x * wB + (1 - x) * wT, cost=cost)
            m = met(c)
            line.append('x={:.2f} {:,.0f}/MDD {:.1f}%'.format(x, m['final'], m['mdd'] * 100))
        print('  참조 편도 %.1f%%: %s' % (cost * 100, ' | '.join(line)))
    ev = ('x=' + '·'.join('%.3f' % x for x in hit) if hit else '없음 — 평균화')
    return [('S4 장점 결합 존재 (Calmar·MDD 둘 다 단독 초과)', bool(hit), ev)]


def main():
    D, wT, wB, _, _ = build('tbill')
    cT, _ = sim(D, wT); cB, _ = sim(D, wB)
    ck = sec_synth(D['c_daily'])
    ck += sec_synth_cal(D['c_daily'])
    ck += sec_trend(D, wT, wB, cT, cB)
    ck += sec_quant(D, wT)
    ck += sec_blend(D, wT, wB)
    print()
    print('=' * 100)
    print(verdict('T4 후속 4문 (진단 전용 — 채택 무관)', ck)['text'])


if __name__ == '__main__':
    main()
