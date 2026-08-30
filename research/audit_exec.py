# -*- coding: utf-8 -*-
"""
[통합 연구 Part 1 후속, 2026-08-31] 혼합의 실전 집행 근사 — 고원이 사는가.

혼합 x·B+(1−x)·T4 의 목표 공격비중 w*(t)=x·wB+(1−x)·wT4 는 매일 움직인다.
수동 체결자는 매일 못 따라간다. v80 은 T4 단독을 주1회로 늦추면 최종 −68%
(게이트 지연 = lag3 효과)임을 보였다 — 혼합도 같은 함정에 빠지는가?

집행 모드 (전부 three_way 규약: lag=1, 비용은 공격 회전만):
  daily   — 기준 (연구 원형)
  weekly  — 5거래일마다만 목표로 재조정 (그 사이 비중 고정)
  band5/10— 목표와 5/10%p 이상 벌어질 때만 재조정
  q25     — T4 쪽 w 를 ¼ 단위 양자화 (v81 §3 등록된 집행 후보) + 매일
비용 0.1%(연구)·0.2%(한국 실효, v68) 모두. x∈{0.30,0.40,0.55}.

판정 아님(v80) — 04 §5-3 혼합 고원 기록의 집행 민감도 주석용.
실행: python research/audit_exec.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hypo_gates as G                                  # noqa: E402
import hypo_hex as X                                    # noqa: E402
import hypo_t4_real as R                                # noqa: E402

n = len(G.idx)
wT4 = R.t4_w(G.r_eq1)
wB = X.wB


def p05(curve, w=5040):
    a = curve.values
    return float(np.quantile(a[w:] / a[:-w], 0.05))


def exec_path(target, mode):
    """목표 비중 경로 → 집행 비중 경로 (모드별)."""
    if mode == 'daily':
        return target
    w = np.empty(n)
    cur = target[0]
    for i in range(n):
        if mode == 'weekly':
            if i % 5 == 0:
                cur = target[i]
        elif mode.startswith('band'):
            th = float(mode[4:]) / 100
            if abs(target[i] - cur) >= th:
                cur = target[i]
        w[i] = cur
    return w


def mix_exec(x, mode, cost):
    """혼합의 3다리 목표를 공격비중 기준으로 집행 근사.
    mix/T-bill 다리는 공격 잔여를 B·T4 규약 비율로 배분(wB 는 0/1 이라
    mix 다리 = x·(1−wB) 는 이벤트성 — 그대로 두고 공격측만 근사한다)."""
    tq = x * wB + (1 - x) * wT4
    wq = exec_path(tq, mode)
    wm = x * (1 - wB)
    wt = np.clip(1 - wq - wm, 0, 1)
    wm = 1 - wq - wt
    return X.three_way(wq, wm, wt, cost=cost)


def mix_q25(x, cost):
    """T4 쪽 w 를 ¼ 단위 양자화 (v81 §3 등록 집행 후보). 양자화 스텝(25%p)이
    어떤 밴드보다 크므로 별도 밴드 모드는 의미 없음 — q25 단독만 둔다."""
    w4 = np.round(wT4 * 4) / 4
    tq = x * wB + (1 - x) * w4
    wm = x * (1 - wB)
    wt = np.clip(1 - tq - wm, 0, 1)
    wm = 1 - tq - wt
    return X.three_way(tq, wm, wt, cost=cost), tq


def stats_of(wq):
    d = np.abs(np.diff(wq))
    return (float(np.sum(d)) / (n / 252),          # 회전(|Δw| 합)/yr
            float(np.sum(d > 1e-9)) / (n / 252))   # 매매 발생일수/yr


def main():
    for cost in (0.001, 0.002):
        b = X.three_way(wB, 1 - wB, np.zeros(n), cost=cost)
        rb = G.report('', b)
        g1, g2 = rb['calmar'] * 1.102, p05(b)
        print(f'\n=== 비용 편도 {cost*100:.1f}% — 기준 B: Calmar {rb["calmar"]:.3f} '
              f'p05 {p05(b):.1f} → 관문① >{g1:.3f} · ② ≥{g2:.1f} ===')
        print(f"{'x':>5} {'모드':<8} {'최종배수':>10} {'Calmar':>7} {'p05':>6} "
              f"{'회전/yr':>7} {'매매일/yr':>8} {'①②':>4}")
        for x in (0.30, 0.40, 0.55):
            tq_full = x * wB + (1 - x) * wT4
            rows = []
            for nm in ('daily', 'weekly', 'band5', 'band10'):
                wq = exec_path(tq_full, nm)
                wm = x * (1 - wB)
                wt = np.clip(1 - wq - wm, 0, 1)
                rows.append((nm, X.three_way(wq, 1 - wq - wt, wt, cost=cost), wq))
            cq, tq_q = mix_q25(x, cost)
            rows.append(('q25', cq, tq_q))
            for nm, c, wq in rows:
                r = G.report('', c)
                pp = p05(c)
                ok = ('★' if (r['calmar'] > g1 and pp >= g2) else '·')
                tv, td = stats_of(wq)
                print(f"{x:>5.2f} {nm:<8} {r['final']:>10.1f} {r['calmar']:>7.3f} "
                      f"{pp:>6.1f} {tv:>7.2f} {td:>8.1f} {ok:>4}")


if __name__ == '__main__':
    main()
