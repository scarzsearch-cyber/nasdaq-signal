# -*- coding: utf-8 -*-
"""
[v56] 선택편향 감사 — -16/-16 자체가 이 데이터에 맞춰 골라진 것인가

지적(정당하다): v18~v55 는 **같은 자료로 모델 선택과 검증을 반복**했다.
관문(4블록·P5·G11)도 결과를 본 뒤에 만들었다. 연구자 자유도가 계속 늘었다.
따라서 "현행이 robust 하다"를 지금 결과만으로 단정할 수 없다.

**새 전략을 하나 더 찾는 것보다 이걸 먼저 한다.**

[정직하게 먼저 인정할 것]
  나는 1972-2026 을 **전부 봤다.** 그래서 **진짜 out-of-sample 은 만들 수 없다.**
  대신 답할 수 있는 것은 이것이다:

    "**그 시점의 자료만으로 내 선택 절차를 돌렸다면 무엇을 골랐고,
      그 뒤에 어떻게 됐는가?**"

  이건 연구자 자유도의 비용을 **직접 측정**한다.

[검사]
  T1 v18 의 선택 재현 — 2000-2026 만으로 격자를 훑으면 -16 이 1등인가?
       1등이면 '표본 내 최적화로 골랐다'는 증거다.
       1등이 아니면 그 가설은 약해진다.
  T2 v18 이 못 본 구간(1972-1999)에서의 성적 — 사실상 뒤로 향한 hold-out
  T3 **워크포워드 모델선택** — 결정시점 T 마다 T 이전 자료로만 최적을 뽑고
       T 이후에서만 평가한다. 고정 -16/-16 과 비교한다.
       고정이 이기면 **선택 절차 자체가 값어치가 없다**는 뜻이고,
       현행의 생존이 선택편향의 산물이라는 주장이 약해진다.
  T4 선택된 규칙이 시점마다 얼마나 흔들리는가 (안정성)

[규약] 모든 평가는 같은 엔진·같은 비용·같은 체결규약. 미래참조 없음.
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
from axis_lib import rule_w, lev_r, COST
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

K = 2
CUR = (-0.16, -0.16)
V18 = (-0.16, -0.11)          # v18 이 실제로 고른 것
L = 20 * 252
DISJOINT = [('1986-01-01', '1995-12-31', 1985),
            ('1996-01-01', '2005-12-31', 1995),
            ('2006-01-01', '2015-12-31', 2005),
            ('2016-01-01', '2026-08-26', 2015)]


def main():
    D = DF.build('chain')
    idx, N = D['idx'], len(D['idx'])
    comp = materials(D)
    dfr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                           {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    rk = lev_r(D, K)
    ddv = np.asarray(D['ddv'], float)
    months = pd.Series(idx).dt.to_period('M').values
    mstart = np.where(np.r_[False, months[1:] != months[:-1]])[0]

    combos = []
    for e in np.arange(-0.24, -0.09, 0.01):
        for x in np.arange(e, -0.03, 0.01):
            combos.append((round(e, 2), round(x, 2)))

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
        return float(C[c][hi - 1] / C[c][lo]), lo, hi

    def dca(c, lo, hi, pay=60):
        m = mstart[(mstart > lo) & (mstart < hi)][:pay]
        return float(np.mean(C[c][hi - 1] / C[c][m])) if len(m) else np.nan

    print("=" * 104)
    print("v56 선택편향 감사 — 나는 1972-2026 을 전부 봤다. 진짜 OOS 는 만들 수 없다.")
    print("      대신 '그 시점 자료만으로 골랐다면?' 을 잰다.")
    print("=" * 104)
    print()

    # ---------------------------------------------------------------- T1
    print("=" * 104)
    print("T1. v18 의 선택 재현 — v18 은 **2000-01~2026-08 자료만** 썼다 (문서 §2)")
    print("=" * 104)
    a, b = '2000-01-01', '2026-08-26'
    rank = sorted(combos, key=lambda c: -seg(c, a, b)[0])
    i18 = rank.index(V18) + 1
    icur = rank.index(CUR) + 1
    print("  격자 %d개를 2000-2026 최종배수로 줄세우면" % len(combos))
    print("  %-12s%12s%8s" % ('규칙', '최종배수', '순위'))
    for c in rank[:5]:
        mk = '  <- v18 채택' if c == V18 else ('  <- 현행' if c == CUR else '')
        print("  %-12s%12.1f%8d%s" % ('%.0f/%.0f' % (c[0] * 100, c[1] * 100),
                                      seg(c, a, b)[0], rank.index(c) + 1, mk))
    print("  ...")
    print("  %-12s%12.1f%8d  <- **v18 이 고른 것**"
          % ('-16/-11', seg(V18, a, b)[0], i18))
    print("  %-12s%12.1f%8d  <- 현행" % ('-16/-16', seg(CUR, a, b)[0], icur))
    print()
    print("  -> v18 이 표본 내 최적을 골랐다면 1위였어야 한다. **%d위다.**" % i18)
    print()

    # ---------------------------------------------------------------- T2
    print("=" * 104)
    print("T2. v18 이 **못 본 구간** 1972-1999 성적 — 뒤로 향한 hold-out")
    print("=" * 104)
    a2, b2 = '1972-01-01', '1999-12-31'
    rank2 = sorted(combos, key=lambda c: -seg(c, a2, b2)[0])
    print("  %-12s%14s%8s" % ('규칙', '1972-99 배수', '순위'))
    for c in rank2[:3]:
        print("  %-12s%14.1f%8d" % ('%.0f/%.0f' % (c[0] * 100, c[1] * 100),
                                    seg(c, a2, b2)[0], rank2.index(c) + 1))
    print("  ...")
    for c in (V18, CUR):
        mk = '  <- v18 채택' if c == V18 else '  <- 현행'
        print("  %-12s%14.1f%8d%s" % ('%.0f/%.0f' % (c[0] * 100, c[1] * 100),
                                      seg(c, a2, b2)[0], rank2.index(c) + 1, mk))
    print()
    pct18 = 100.0 * (1 - (rank2.index(V18)) / len(combos))
    pctcur = 100.0 * (1 - (rank2.index(CUR)) / len(combos))
    print("  -> v18 이 **한 번도 안 본 28년**에서 -16/-11 은 상위 %.0f%%, -16/-16 은 상위 %.0f%%."
          % (pct18, pctcur))
    print()

    # ---------------------------------------------------------------- T3
    print("=" * 104)
    print("T3a. 워크포워드 모델선택 — 2026 끝점이 겹친 창(역사 참고, 독립 횟수 아님)")
    print("=" * 104)
    print("  '내 선택 절차'를 그대로 흉내낸다: 과거 전체로 최종배수 1등을 고른다.")
    print()

    # v57 정정: 위 7개는 전부 2026에서 끝나는 포함관계다. 판정에는 아래
    # 서로 겹치지 않는 네 평가창만 쓴다.
    print("  T3b. 겹치지 않는 네 평가창 — 선택은 각 창 시작 전 자료만")
    print("  %-10s%-12s%12s%12s%10s" % ('선택시점', '뽑힌 규칙', '이후 선택', '이후 고정', '차이'))
    disjoint_rows = []
    for a3, b3, T in DISJOINT:
        best = max(combos, key=lambda c: seg(c, '1972-01-01', '%d-12-31' % T)[0])
        vs, vf = seg(best, a3, b3)[0], seg(CUR, a3, b3)[0]
        disjoint_rows.append((T, best, vs, vf))
        print("  %-10d%-12s%12.2f%12.2f%9.0f%%"
              % (T, '%.0f/%.0f' % (best[0] * 100, best[1] * 100),
                 vs, vf, (vs / vf - 1) * 100))
    disjoint_win = sum(vs > vf for _, _, vs, vf in disjoint_rows)
    print("  선택 절차가 고정을 이긴 겹치지 않는 창: %d/%d\n"
          % (disjoint_win, len(disjoint_rows)))
    print("  %-8s%-12s%12s%12s%11s%11s"
          % ('결정시점', '그때 뽑힌 규칙', '이후 선택', '이후 고정', '차이', '이후기간'))
    picks = []
    rows = []
    for T in (1985, 1990, 1995, 2000, 2005, 2010, 2015):
        cut = '%d-12-31' % T
        nxt = '%d-01-01' % (T + 1)
        best = max(combos, key=lambda c: seg(c, '1972-01-01', cut)[0])
        picks.append((T, best))
        v_sel = seg(best, nxt, '2026-08-26')[0]
        v_fix = seg(CUR, nxt, '2026-08-26')[0]
        rows.append((T, best, v_sel, v_fix))
        print("  %-8d%-12s%12.1f%12.1f%10.0f%%   %s~"
              % (T, '%.0f/%.0f' % (best[0] * 100, best[1] * 100),
                 v_sel, v_fix, (v_sel / v_fix - 1) * 100, nxt[:7]))
    win = sum(1 for _, _, s, f in rows if s > f)
    print()
    print("  **선택 절차가 고정 -16/-16 을 이긴 시점: %d/%d**" % (win, len(rows)))
    print()

    # 적립식으로도 같은 것
    print("  같은 것을 적립식(ISA형 20년창 중앙)으로")
    print("  %-8s%-12s%12s%12s%11s" % ('결정시점', '뽑힌 규칙', '이후 선택', '이후 고정', '차이'))
    win2 = 0
    for T in (1985, 1990, 1995, 2000, 2005):
        cut = '%d-12-31' % T
        nxt = '%d-01-01' % (T + 1)
        best = max(combos, key=lambda c: seg(c, '1972-01-01', cut)[0])
        lo = int(idx.searchsorted(pd.Timestamp(nxt)))
        st = [s for s in range(lo, N - L, 63)]
        if len(st) < 5:
            continue
        f = lambda c: float(np.median([dca(c, s, s + L) for s in st]))
        vs, vf = f(best), f(CUR)
        win2 += (vs > vf)
        print("  %-8d%-12s%12.1f%12.1f%10.0f%%"
              % (T, '%.0f/%.0f' % (best[0] * 100, best[1] * 100), vs, vf,
                 (vs / vf - 1) * 100))
    print()

    # ---------------------------------------------------------------- T4
    print("=" * 104)
    print("T4. 선택된 규칙이 시점마다 얼마나 흔들리는가")
    print("=" * 104)
    uniq = sorted(set(p for _, p in picks))
    print("  뽑힌 규칙: %s" % ' · '.join('%.0f/%.0f' % (c[0] * 100, c[1] * 100)
                                       for _, c in picks))
    print("  서로 다른 규칙 %d개 / 결정시점 %d개" % (len(uniq), len(picks)))
    ee = [c[0] for _, c in picks]; xx = [c[1] for _, c in picks]
    print("  진입선 범위 %.0f%% ~ %.0f%%   복귀선 범위 %.0f%% ~ %.0f%%"
          % (min(ee) * 100, max(ee) * 100, min(xx) * 100, max(xx) * 100))
    print()

    print("=" * 104)
    red_flag = icur == 1
    back_holdout = pctcur >= 75
    selection_value = disjoint_win > len(disjoint_rows) / 2
    stable = len(uniq) <= 2
    print('[현행 B가 선택편향의 산물인가] 판정: **순수 OOS까지 판단 보류**')
    print('  %s 표본 내 1위 붉은 깃발                 현행 %d위/%d'
          % ('O' if red_flag else 'X', icur, len(combos)))
    print('  %s 2000년 이전 역방향 hold-out 생존       상위 %.0f%%'
          % ('O' if back_holdout else 'X', pctcur))
    print('  %s 과거만 보고 고른 절차가 고정 B를 이김      %d/%d 겹치지 않는 창'
          % ('O' if selection_value else 'X', disjoint_win, len(disjoint_rows)))
    print('  %s 선택 규칙이 시점마다 안정적              서로 다른 %d개'
          % ('O' if stable else 'X', len(uniq)))
    print('  -> 내부 자료에는 붉은 깃발이 있지만 다른 시대의 붕괴 증거도 없다. '
          '같은 자료를 이미 봤으므로 어느 쪽도 확정하지 않고 동결 이후 OOS만 판단한다.')


if __name__ == '__main__':
    main()
