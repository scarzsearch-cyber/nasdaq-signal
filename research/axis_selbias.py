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
    print("T3. 워크포워드 **모델선택** — 그 시점 자료로만 최적을 뽑고 이후에서 평가")
    print("=" * 104)
    print("  '내 선택 절차'를 그대로 흉내낸다: 과거 전체로 최종배수 1등을 고른다.")
    print()
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
    print(verdict('현행이 선택편향의 산물인가', [
        ('v18 이 자기 표본에서 1등을 골랐다 (편향의 증거)', i18 == 1,
         '실제 %d위/%d' % (i18, len(combos))),
        ('v18 이 못 본 28년에서 상위 25% 안에 든다', pct18 >= 75,
         '상위 %.0f%%' % pct18),
        ('워크포워드 선택이 고정 -16/-16 을 이긴다 (선택이 값어치 있다)',
         win > len(rows) / 2, '%d/%d 시점' % (win, len(rows))),
        ('뽑히는 규칙이 시점마다 안정적이다', len(uniq) <= 2,
         '서로 다른 %d개' % len(uniq)),
    ], adopt_if=['v18 이 자기 표본에서 1등을 골랐다 (편향의 증거)'])['text'])


if __name__ == '__main__':
    main()
