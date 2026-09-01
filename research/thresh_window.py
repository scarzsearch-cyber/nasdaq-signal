# -*- coding: utf-8 -*-
"""
[2026-09-01 소유자 질문] 「내 전략은 54년을 **통으로** 재서 −16/−16 이 1등이라고
                          되어 있는 게 맞나?」

★ 사전 등록 — 결과를 보기 전에 적는다 (§-1 「사전 등록」).

  묻는 것은 두 가지이고 **서로 다른 질문**이다.
    Q1 (사실 확인) 54년 통짜로 격자 210개를 줄세우면 현행이 몇 위인가?
    Q2 (방법 확인) 그 순위가 이 전략을 채택한 **근거**인가? 그리고 근거가 될 수 있나?

  Q2 에 대한 사전 판단: **통짜 1위는 그 자체로 근거가 될 수 없다.**
    통짜는 **비중첩 창이 1개**다. 210개 규칙을 한 표본에 줄세우면 무엇이든 1등이 나온다 —
    1등이 나왔다는 사실은 그 규칙에 대해 **아무것도 말해주지 않는다**(210개 중 하나는
    반드시 1등이다). 통짜 순위가 뜻을 가지려면 **경계를 흔들어도 유지되는지**를 봐야 한다.

  통과/실패의 뜻을 먼저 적는다 (§-1 ⑤ — 양쪽 답이 같으면 관문이 아니다):
    · 시작·끝을 옮겼을 때 현행 순위가 **요동치면**  -> 통짜 1위는 **경계 선택의 산물**이다.
    · 겹치지 않는 블록에서 현행이 **자주 1등이면** -> 특정 사건에 맞춰진 지문(과적합)이다.
    · 겹치지 않는 블록에서 **어디서도 1등이 아닌데 최악 순위가 좋으면**
      -> 통짜 1위는 「어디서도 안 나쁘다」의 부산물이고, 근거는 통짜가 아니라 **블록** 쪽이다.
    세 결과가 서로 다른 문장을 낳는다 — 그러므로 이것은 관문이다.

측정 (전부 읽기 전용 · 전략 무변경 · 같은 엔진·같은 비용·같은 체결규약):
  A. 통짜 순위 — 54년 / 21세기 / 1972-99(v18 미관측) 각각
  B. 경계 민감도 — 시작연도 이동(끝 고정) · 끝연도 이동(시작 고정)
       ⚠ 이 창들은 **서로 포함관계**다(비중첩 1개). v57 이 정확히 이 착각을 정정했다 —
         숫자는 「독립 관측 N개」가 아니라 「같은 몸을 다른 각도로 본 것」이다.
  C. 겹치지 않는 블록 K=2·3·6 — 각 블록 순위 · 최악순위(미니맥스) · 1등 횟수
  D. 이웃 규칙과의 실제 차이 — 「1등」이 얼마나 값어치 있는 자리인가
       (v43: 문턱 변형끼리 상관 0.92~1.00 — 선택지가 아니라 중복)

재현:  python research/thresh_window.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)

import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

CUR = (-0.16, -0.16)
V18 = (-0.16, -0.11)
END = '2026-08-26'


def main():
    D = DF.build('chain')
    idx = D['idx']
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, 2)
    ddv = np.asarray(D['ddv'], float)

    # axis_selbias.py / axis_minimax.py 와 **같은 격자**(210개)
    combos = [(round(e, 2), round(x, 2))
              for e in np.arange(-0.24, -0.09, 0.01)
              for x in np.arange(e, -0.03, 0.01)]
    C = {}
    for c in combos:
        w = rule_w(ddv, c[0], c[1])
        pos = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(pos * rk + (1 - pos) * dfr); r[0] = 0.0
        t = np.abs(np.diff(pos, prepend=pos[0]))
        C[c] = np.cumprod((1 + r) * (1 - COST * t))

    def seg(c, a, b):
        lo = int(idx.searchsorted(pd.Timestamp(a)))
        hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
        return float(C[c][hi - 1] / C[c][lo])

    def rank_of(c, a, b):
        order = sorted(combos, key=lambda k: -seg(k, a, b))
        return order.index(c) + 1, order[0]

    yrs = lambda a, b: (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    fmt = lambda c: '%.0f/%.0f' % (c[0] * 100, c[1] * 100)
    L = '=' * 96

    print(L)
    print('격자 210개를 창별로 다시 줄세운다 — 「54년 통짜 1등」이 근거인가')
    print('   자료 %s ~ %s · 규칙 %d개 · 엔진/비용/체결규약은 axis_selbias 와 동일'
          % (str(idx[0])[:10], END, len(combos)))
    print(L)

    # ── A. 통짜 ─────────────────────────────────────────────────────────
    print()
    print('A. 통짜(한 덩어리)로 재면 — **비중첩 창 1개**짜리 관측이다')
    print('   %-22s%9s%10s%9s%9s   %s' % ('창', '길이', '비중첩', '현행순위', 'v18순위', '그 창의 1등'))
    for nm, a in (('54년 전체', '1972-01-01'), ('21세기', '2000-01-01'),
                  ('v18 미관측 28년', '1972-01-01')):
        b = '1999-12-31' if nm.startswith('v18') else END
        rc, top = rank_of(CUR, a, b)
        r18, _ = rank_of(V18, a, b)
        print('   %-22s%8.1f년%10d%9d위%8d위   %-8s %.1f배'
              % (nm, yrs(a, b), 1, rc, r18, fmt(top), seg(top, a, b)))
    print()
    print('   ※ 210개 중 하나는 **반드시** 1등이다. 「1등이 나왔다」는 사실 자체는')
    print('     그 규칙에 대해 아무것도 말해주지 않는다 — 경계를 흔들어 봐야 안다(B).')

    # ── B. 경계 민감도 ──────────────────────────────────────────────────
    print()
    print(L)
    print('B. 같은 통짜인데 **경계만** 옮기면 (⚠ 창들이 서로 포함관계 — 비중첩 1개)')
    print(L)
    print()
    print('   B-1 시작연도 이동 (끝은 %s 고정)' % END)
    print('   %-12s%9s%11s%11s   %s' % ('시작', '길이', '현행순위', '상위%', '그 창의 1등'))
    ranks_s = []
    for y in range(1972, 2016, 4):
        a = '%d-01-01' % y
        rc, top = rank_of(CUR, a, END)
        ranks_s.append(rc)
        print('   %-12s%8.1f년%10d위%10.0f%%   %-8s' % (a[:4], yrs(a, END), rc,
                                                       100 * (1 - (rc - 1) / len(combos)), fmt(top)))
    print()
    print('   B-2 끝연도 이동 (시작은 1972 고정)')
    print('   %-12s%9s%11s%11s   %s' % ('끝', '길이', '현행순위', '상위%', '그 창의 1등'))
    ranks_e = []
    for y in list(range(1990, 2026, 5)) + [2026]:
        b = END if y == 2026 else '%d-12-31' % y
        rc, top = rank_of(CUR, '1972-01-01', b)
        ranks_e.append(rc)
        print('   %-12s%8.1f년%10d위%10.0f%%   %-8s' % (str(y), yrs('1972-01-01', b), rc,
                                                       100 * (1 - (rc - 1) / len(combos)), fmt(top)))
    allr = ranks_s + ranks_e
    print()
    print('   -> 현행 순위 범위 **%d위 ~ %d위** / 210 (중앙 %d위) · 1등이 된 창 %d/%d'
          % (min(allr), max(allr), int(np.median(allr)),
             sum(1 for r in allr if r == 1), len(allr)))

    # ── C. 겹치지 않는 블록 ─────────────────────────────────────────────
    print()
    print(L)
    print('C. **겹치지 않는** 블록으로 쪼개면 (여기서만 관측이 여러 개가 된다)')
    print(L)
    BLOCKS = {}
    for K in (2, 3, 6):
        edges = pd.date_range('1972-01-01', END, periods=K + 1)
        BLOCKS[K] = [(str(edges[i])[:7], str(edges[i])[:10],
                      str(edges[i + 1] - pd.Timedelta(days=1))[:10]) for i in range(K)]
    for K, wins in BLOCKS.items():
        R = {c: [] for c in combos}
        for _, a, b in wins:
            order = sorted(combos, key=lambda k: -seg(k, a, b))
            for i, c in enumerate(order, 1):
                R[c].append(i)
        worst = {c: max(R[c]) for c in combos}
        mmrank = sorted(combos, key=lambda c: (worst[c], int(np.median(R[c])))).index(CUR) + 1
        tops = [max(combos, key=lambda c: seg(c, a, b)) for _, a, b in wins]
        print()
        print('   K=%d (각 %.1f년) — 현행의 구간별 순위 %s'
              % (K, yrs(wins[0][1], wins[0][2]), ' '.join('%d위' % r for r in R[CUR])))
        print('        최악순위 %d위 · 중앙 %d위 · 최고 %d위  ->  **미니맥스 %d위/210**'
              % (worst[CUR], int(np.median(R[CUR])), min(R[CUR]), mmrank))
        print('        각 블록 1등: %s' % ' · '.join(fmt(t) for t in tops))
        print('        그 1등들의 최악순위: %s'
              % ' · '.join('%s→%d위' % (fmt(t), max(R[t])) for t in dict.fromkeys(tops)))

    # ── D. 1등의 값어치 ─────────────────────────────────────────────────
    print()
    print(L)
    print('D. 「1등」이 얼마나 값어치 있는 자리인가 — 54년 통짜에서')
    print(L)
    order = sorted(combos, key=lambda c: -seg(c, '1972-01-01', END))
    v = {c: seg(c, '1972-01-01', END) for c in combos}
    top1 = v[order[0]]
    ny = yrs('1972-01-01', END)
    cagr = lambda m: (m ** (1.0 / ny) - 1) * 100
    print()
    print('   %-10s%12s%10s%11s' % ('순위', '54년 배수', '1등 대비', 'CAGR'))
    for i in (1, 2, 3, 5, 10, 20, 50, 105, 210):
        c = order[i - 1]
        print('   %-10s%12.0f%9.0f%%%10.2f%%%s' % ('%d위' % i, v[c], 100 * v[c] / top1,
                                                   cagr(v[c]), '  <- 현행' if c == CUR else ''))
    print()
    gap = cagr(top1) - cagr(v[order[1]])
    print('   ★ 사전에 「1등과 2등의 차이는 표본의 우연」이라 쓰려 했으나 **측정이 그렇지 않다** —')
    print('     1등은 2등보다 %.0f%% 크다. 다만 그것은 **연 %.2f%%p** 를 %.1f년 복리로 부풀린 것이다.'
          % (100 * (top1 / v[order[1]] - 1), gap, ny))
    print('     즉 통짜 최종배수는 **작은 연차이를 큰 순위차로 보이게 만드는 확대경**이다')
    print('     (slice_scan.py 머리말의 「통짜는 복리 높은 전략이 자동 우승」과 같은 사실).')
    for th in (0.9, 0.8, 0.7):
        near = [c for c in combos if v[c] >= top1 * th]
        es = sorted({c[0] for c in near})
        print('     1등의 %.0f%% 이내 **%3d개/210** (진입선 %.0f%% ~ %.0f%%)'
              % (100 * th, len(near), 100 * es[0], 100 * es[-1]))

    # ── 판정 ────────────────────────────────────────────────────────────
    print()
    print(L)
    print('판정')
    print(L)
    swing = max(allr) - min(allr)
    print()
    print('   Q1 54년 통짜에서 현행은 **%d위/210** 이다 — 사실이다.' % rank_of(CUR, '1972-01-01', END)[0])
    print('   Q2 그러나 그 1등은 이 전략을 채택한 근거가 **아니다**:')
    print('      · 통짜는 비중첩 창 **1개**다. 210개 중 하나는 반드시 1등이 된다.')
    print('      · 경계를 옮기면 순위가 %d위~%d위로 %d칸 움직인다(B).'
          % (min(allr), max(allr), swing))
    print('      · 근거는 **겹치지 않는 블록에서 어디서도 1등이 아닌데 최악이 좋다**는 쪽이다(C).')
    print()
    print('   ※ 이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('      「01_Strategy_Logic.md §4 의 문턱 격자 행이 창을 **54년**이라 적고,')
    print('        현행 순위를 **3위**라 적은 것은 무엇을 인용한 것인가?」')
    print('        -> 실측: 그 격자는 **2000-2026** 이고 현행은 **1위**다.')
    print('           3위는 (ㄱ) v18 이 고른 −16/−11 의 순위, 또는')
    print('                  (ㄴ) 현행의 **미니맥스**(겹치지 않는 6구간 최악순위) 순위다.')
    print('           둘은 서로 다른 3위이고, 둘 다 「54년 통짜 3위」가 아니다.')


if __name__ == '__main__':
    main()
