# -*- coding: utf-8 -*-
"""
[2026-09-01 소유자 질문] 「OOS·WFA·DSR·PBO 같은 과적합 검증을 다 해본 거 맞나?」
                          -> 전수 확인했더니 **하나가 비어 있었다: 문턱 격자의 PBO.**

★ 무엇이 비어 있었나 (§-1 ② 「완료」를 쓰기 전에 파일에서 하나씩 확인 — 실제로 빈 칸이 나왔다)

  `research/audit_pbo.py` 의 후보 우주는 **혼합 x(19)·hex(4)·escape(12)·external(8)·
  gates(2)·B·T4 = 47개**다. **문턱 격자는 그 안에 없다.**
  v70 의 PBO 0.437 은 **T4 파라미터**에 잰 값이다.
  즉 **「−16 이라는 문턱을 153칸 중에서 고른 행위」에는 PBO 를 한 번도 안 걸었다.**
  04 §5-13 정정2 가 「PBO 가 답하지 않았다」고 적어 두었으나, **답하게 만들지는 않았다.**
  이 파일이 그 빈칸을 채운다.

★ 사전 등록 — 결과 보기 전에 못 박는다 (§-1 ⑤ 실패/통과가 각각 무엇을 뜻하는지 먼저)

  PBO = P(IS 1등이 OOS 에서 중앙값 아래로 떨어질 확률).
    · PBO ≥ 0.5  -> **IS 1등 고르기가 동전던지기 이하.** 「문턱을 성과로 고른다」는
                    절차 자체가 무의미하다는 뜻이고, −16 이 그 절차의 산물이라면
                    그 값에 특별한 근거가 없다는 증거가 된다.
    · PBO ≈ 0.3~0.5 -> 약한 신호. 고를 값어치가 크지 않다.
    · PBO ≤ 0.2  -> IS 에서 이긴 문턱이 OOS 에서도 대체로 이긴다. 선택에 실체가 있다.

  ⚠ **양쪽 어느 쪽이 나와도 「−16 이 최적이다」는 나오지 않는다.** PBO 가 평가하는 것은
    **「IS 1등을 고르는 절차」**이지 특정 값이 아니다. 이 구분을 못 하면 이건 관문이 아니다.
    (04 §5-13 정정2 가 낸 교훈의 재적용: **다른 대상에 잰 통계량을 이 대상의 근거로 쓰지 마라.**)

  ⚠ **후보들이 서로 매우 닮았다** — 문턱 변형끼리 상관 0.92~1.00(v43). 닮은 후보가 많으면
    OOS 상대순위가 촘촘해져 PBO 가 **중간값 쪽으로 끌린다.** 그래서 PBO 값 하나만 보지 말고
    **IS 1등 빈도의 분포**(어떤 문턱이 뽑히나)를 같이 본다.

방법: Bailey & López de Prado (2014) CSCV — `audit_pbo.py` 의 cscv() 와 **같은 구현**
  (S=8 연속 블록 · C(8,4)=70 분할 · Sharpe 주판정 · Calmar 보조).
  ⚠ 블록을 이어붙이면 MDD 가 왜곡되므로 Calmar 는 참고용이다(audit_pbo 와 같은 규약).

격자: `dsr_b.py` 와 **같은 153칸** (진입·복귀 −24%~−8%, 1%p, 복귀 ≥ 진입).
  복귀선이 진입선보다 깊은 조합은 상태기계상 −16/−16 과 **완전 등가**라 제외한다
  (v67 §C-2 — 등가 조합이 별개 후보로 집계되면 순위가 왜곡된다).

판정 아님 · 전략 무변경. 실행: python research/pbo_thresh.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
from itertools import combinations
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
PX = pd.Series(G.D['px'], index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
CUR = (-0.16, -0.16)
L = '=' * 96


def rets(a):
    return np.diff(a, prepend=1.0) / np.concatenate(([1.0], a[:-1]))


def metric(Rsub, kind):
    """audit_pbo.py 와 같은 구현."""
    if kind == 'sharpe':
        return Rsub.mean(axis=1) / Rsub.std(axis=1, ddof=1)
    a = np.cumprod(1 + Rsub, axis=1)
    peak = np.maximum.accumulate(a, axis=1)
    mdd = np.abs(np.min(a / peak - 1, axis=1))
    cagr = a[:, -1] ** (252.0 / Rsub.shape[1]) - 1
    return cagr / np.maximum(mdd, 1e-9)


def cscv(Rm, names, kind, label, cur_i):
    S = 8
    bnd = np.linspace(0, Rm.shape[1], S + 1, dtype=int)
    blocks = [np.arange(bnd[i], bnd[i + 1]) for i in range(S)]
    lam, below, picks = [], 0, {}
    cur_is, cur_oos = [], []
    for isb in combinations(range(S), S // 2):
        oob = [b for b in range(S) if b not in isb]
        i_idx = np.concatenate([blocks[b] for b in isb])
        o_idx = np.concatenate([blocks[b] for b in oob])
        mi, mo = metric(Rm[:, i_idx], kind), metric(Rm[:, o_idx], kind)
        best = int(np.argmax(mi))
        picks[names[best]] = picks.get(names[best], 0) + 1
        w = (np.sum(mo < mo[best]) + 0.5 * np.sum(mo == mo[best])) / len(mo)
        w = min(max(w, 1e-6), 1 - 1e-6)
        lam.append(np.log(w / (1 - w)))
        below += int(w < 0.5)
        # 현행이 그 분할에서 IS/OOS 로 몇 백분위였나 (참고)
        cur_is.append((np.sum(mi < mi[cur_i]) + 0.5 * np.sum(mi == mi[cur_i])) / len(mi))
        cur_oos.append((np.sum(mo < mo[cur_i]) + 0.5 * np.sum(mo == mo[cur_i])) / len(mo))
    lam = np.asarray(lam)
    pbo = below / len(lam)
    top = sorted(picks.items(), key=lambda t: -t[1])[:6]
    print('  %-22s PBO=**%.3f** · λ중앙 %+.2f · 분할 %d개' % (label, pbo, np.median(lam), len(lam)))
    print('  %-22s IS 1등으로 뽑힌 문턱: %s' % ('', ', '.join('%s(%d회)' % (k, v) for k, v in top)))
    print('  %-22s 현행 −16/−16 의 백분위 — IS 중앙 %.0f%% · **OOS 중앙 %.0f%%**'
          % ('', 100 * np.median(cur_is), 100 * np.median(cur_oos)))
    return pbo, picks


def build(cells):
    names, rows = [], []
    for en, ex in cells:
        w = EC.rule_dd(PX, en, ex)
        rows.append(rets(EC.sim2(w, QLDR, MIXR)))
        names.append('%.0f/%.0f' % (en * 100, ex * 100))
    return np.asarray(rows), names


def main():
    ths = [round(-0.24 + 0.01 * i, 2) for i in range(17)]
    full = [(en, ex) for en in ths for ex in ths if ex >= en]     # 153칸 (dsr_b 와 동일)
    diag = [(t, t) for t in ths]                                  # 대각선 17칸 (동결 규칙의 축)

    print(L)
    print('문턱 격자의 PBO — 「−16 을 153칸 중에서 고른 행위」가 과적합인가')
    print('   CSCV S=8 · C(8,4)=70 분할 · audit_pbo.py 와 같은 구현 · 격자는 dsr_b.py 와 동일')
    print(L)

    for cells, tag in ((full, '전체 격자 %d칸' % len(full)),
                       (diag, '대각선 %d칸 (진입=복귀)' % len(diag))):
        Rm, names = build(cells)
        ci = cells.index(CUR)
        print()
        print('[%s]' % tag)
        for kind, lab in (('sharpe', 'Sharpe (주판정)'), ('calmar', 'Calmar (참고)')):
            cscv(Rm, names, kind, lab, ci)

    # ── 대조군: 이 검사에 변별력이 있나 (§-1 ⑤ — 변별력 없는 검사는 관문이 아니다) ──
    print()
    print(L)
    print('대조군 — 이 검사에 변별력이 있는가 (통과만 보고 넘어가지 않기 위해)')
    print(L)
    print('  같은 CSCV 를 **정말로 과적합인 우주**에 걸어 본다: 문턱 격자에')
    print('  **무작위 신호 규칙 60개**를 섞는다(같은 회전수, 순수 잡음).')
    rng = np.random.default_rng(20260901)
    wcur = np.asarray(EC.rule_dd(PX, *CUR), float)
    turns = int(np.sum(np.abs(np.diff(wcur)) > 0.5))
    n = len(idx)
    noise_rows, noise_names = [], []
    for k in range(60):
        cuts = np.sort(rng.choice(np.arange(1, n), size=turns, replace=False))
        w = np.zeros(n); cur = 1.0; prev = 0
        for c in cuts:
            w[prev:c] = cur; cur = 1.0 - cur; prev = c
        w[prev:] = cur
        noise_rows.append(rets(EC.sim2(w, QLDR, MIXR)))
        noise_names.append('noise%02d' % k)
    Rm, names = build(full)
    Rm2 = np.vstack([Rm, np.asarray(noise_rows)])
    names2 = names + noise_names
    print()
    pbo_mix, picks = cscv(Rm2, names2, 'sharpe', 'Sharpe (문턱+잡음)', full.index(CUR))
    nwin = sum(v for k, v in picks.items() if k.startswith('noise'))
    print('  -> 잡음이 IS 1등으로 뽑힌 분할 %d/70. 잡음이 자주 뽑히면서도 PBO 가 낮으면'
          % nwin)
    print('     이 검사는 변별을 못 하는 것이다. 위 값과 비교해 읽어라.')

    # ── ⓐ 반증 — 「현행 OOS 90백분위」가 −16 의 성질인가, 격자 가운데면 다 그런가 ──
    print()
    print(L)
    print('ⓐ 반증 — 현행이 OOS 상위였다. 그러면 이웃도 다 그런가? (통과했으니 반드시 잰다)')
    print(L)
    Rm, names = build(diag)
    S = 8
    bnd = np.linspace(0, Rm.shape[1], S + 1, dtype=int)
    blocks = [np.arange(bnd[i], bnd[i + 1]) for i in range(S)]
    oosp = {nm: [] for nm in names}
    for isb in combinations(range(S), S // 2):
        oob = [b for b in range(S) if b not in isb]
        mo = metric(Rm[:, np.concatenate([blocks[b] for b in oob])], 'sharpe')
        for k, nm in enumerate(names):
            oosp[nm].append((np.sum(mo < mo[k]) + 0.5 * np.sum(mo == mo[k])) / len(mo))
    print()
    print('  대각선 17칸 각각의 **OOS 백분위 중앙값** (70분할, Sharpe)')
    print('  %-10s%14s%12s' % ('문턱', 'OOS 중앙 백분위', '최악 분할'))
    for nm in names:
        v = np.array(oosp[nm])
        mark = '  <- 현행' if nm == '-16/-16' else ''
        print('  %-10s%13.0f%%%11.0f%%%s' % (nm, 100 * np.median(v), 100 * np.min(v), mark))
    med = {nm: np.median(oosp[nm]) for nm in names}
    rank = sorted(names, key=lambda k: -med[k])
    print()
    print('  -> OOS 중앙 백분위 순위: %s' % ' > '.join(rank[:5]))
    print('     현행은 **%d위/%d**. 이웃(−15·−17)과의 차이가 작으면 「고원의 꼭대기」이고,'
          % (rank.index('-16/-16') + 1, len(names)))
    print('     크면 「−16 만 특별」이다 — 위 숫자로 직접 판단하라.')

    print()
    print(L)
    print('읽는 법')
    print(L)
    print('  · PBO 는 **「IS 1등을 고르는 절차」**를 평가한다. 낮게 나와도')
    print('    「−16 이 최적이다」가 참이 되지는 않는다 — 사전 등록한 대로다.')
    print('  · 문턱 후보들은 서로 상관 0.92~1.00(v43) 이라 OOS 순위가 촘촘하다.')
    print('    PBO 값 하나가 아니라 **IS 1등 빈도의 분포**를 같이 보라.')
    print()
    print('  ★ 가장 중요한 한정 — **CSCV 의 「OOS」는 진짜 OOS 가 아니다.**')
    print('    같은 54년을 블록으로 갈라 서로 검증할 뿐이고, **−16 은 그 54년을 다 본 뒤에**')
    print('    골라졌다. 그러므로 위의 「OOS 백분위 91%」에는 선택의 흔적이 남아 있다.')
    print('    v56 §0 이 적어 둔 그대로다 — 「나는 1972-2026 을 전부 봤다. 진짜 OOS 는')
    print('    만들 수 없다.」 **진짜 OOS 는 동결(2026-08-27) 이후 쌓이는 것뿐이다.**')
    print('    이 파일이 채운 것은 「PBO 를 문턱에 겨눈 적이 없다」는 **빈칸**이지,')
    print('    「−16 이 옳다」의 증명이 아니다.')
    print()
    print('  ※ 이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('    「04 §5-13 정정2 의 *정정 WFA*(훈련10y/걸음3y)는 결과만 문서에 있고')
    print('      재현 스크립트가 없다 — 재현 가능하게 만들어야 하지 않나?」')
    print('      -> 04 §7 대장에 미결로 올린다.')


if __name__ == '__main__':
    main()
