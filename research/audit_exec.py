# -*- coding: utf-8 -*-
"""
[통합 연구 Part 1 후속, 2026-08-31] 혼합의 실전 집행 근사 — 고원이 사는가.

혼합 x·B+(1−x)·T4 의 목표 공격비중 w*(t)=x·wB+(1−x)·wT4 는 매일 움직인다.
수동 체결자의 매매 부담을 진단한다. 옛 주1회/밴드 결과는 거래를 안 한 날에도
비중을 고정하는 오류가 있어 2026-09-05 R06에서 교정했다. 옛 숫자를 인용하지 않는다.

집행 모드 (lag=1, 비용은 전체 자산 실제 회전 half-L1의 비례 차감):
  daily   — 기준 (연구 원형)
  weekly  — 5거래일마다만 목표로 재조정 (그 사이 보유 수량 고정)
  band5/10— 목표 공격비중과 실제 공격비중이 5/10%p 이상 벌어질 때만 전 자산 재조정
  q25     — T4 쪽 w 를 ¼ 단위 양자화 (v81 §3 등록된 집행 후보) + 매일
비용 0.1%·0.2% 모두. x∈{0.30,0.40,0.55}. 한국 달력·실거래 수수료·세금·납입은
없으므로 원화 ISA 집행 가능성의 인증이 아니다. 전량 방어 예외도 새로 넣지 않는다.

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
import pandas as pd
from research.band_accounting import banded_path

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


def exec_path(target, mode, cost=.001):
    """N x 3 종가 목표 → 실제 보유 장부. 옛 scalar 목표 고정 API는 폐기.

    weekly는 원래 종가행 0,5,10,...에서 읽고 실행행 1,6,11,...에 거래한다.
    band는 원래 공격비중 기준을 유지한다. 거래하지 않으면 방어 두 다리도
    보유 수량을 유지하고, 거래할 때만 그날의 전체 목표로 맞춘다.
    """
    target = np.asarray(target, float)
    if target.shape != (n, 3):
        raise ValueError('N x 3 close-day targets required')
    if mode not in ('daily', 'weekly', 'band5', 'band10'):
        raise ValueError('unknown execution mode')
    positions = np.vstack([target[0], target[:-1]])
    eligible = np.ones(n, bool)
    if mode == 'weekly':
        eligible[:] = False
        eligible[1::5] = True
    band = float(mode[4:])/100 if mode.startswith('band') else 0.
    result = banded_path(positions, np.column_stack([X.QLDR, X.MIXR, X.tb]),
                         eligible, cost, band,
                         trigger_asset=0 if mode.startswith('band') else None,
                         inclusive=True)
    return pd.Series(result['wealth'], index=G.idx), result


def mix_targets(x, quantize=False):
    """Net close-day targets for the existing B/basket + T4/T-bill mix."""
    if not np.isfinite(x) or not 0 <= x <= 1:
        raise ValueError('B fraction must be in [0, 1]')
    w4 = np.round(wT4*4)/4 if quantize else wT4
    tq = x*wB + (1-x)*w4
    wm = x*(1-wB)
    wt = np.clip(1-tq-wm, 0, 1)
    return np.column_stack([tq, 1-tq-wt, wt])


def mix_q25(x, cost):
    """기존 ¼ 양자화 목표의 일별 재조정. 목표가 같아도 표류 매매가 생긴다."""
    return exec_path(mix_targets(x, quantize=True), 'daily', cost)


def stats_of(result):
    """Actual half-L1 turnover and trade days; legacy N/252 annualization."""
    return (float(result['turnover'].sum())/(n/252),
            float(result['trade_days'].sum())/(n/252))


def main():
    for cost in (0.001, 0.002):
        b = X.three_way(wB, 1 - wB, np.zeros(n), cost=cost)
        rb = G.report('', b)
        g1, g2 = rb['calmar'] * 1.102, p05(b)
        print(f'\n=== 비례비용 {cost*100:.1f}% — 기준 B: Calmar {rb["calmar"]:.3f} '
              f'p05 {p05(b):.1f} → 관문① >{g1:.3f} · ② ≥{g2:.1f} ===')
        print(f"{'x':>5} {'모드':<8} {'최종배수':>10} {'Calmar':>7} {'p05':>6} "
              f"{'회전/yr':>7} {'매매일/yr':>8} {'①②':>4}")
        for x in (0.30, 0.40, 0.55):
            target = mix_targets(x)
            rows = []
            for nm in ('daily', 'weekly', 'band5', 'band10'):
                curve, detail = exec_path(target, nm, cost)
                rows.append((nm, curve, detail))
            cq, tq_q = mix_q25(x, cost)
            rows.append(('q25', cq, tq_q))
            for nm, c, detail in rows:
                r = G.report('', c)
                pp = p05(c)
                ok = ('★' if (r['calmar'] > g1 and pp >= g2) else '·')
                tv, td = stats_of(detail)
                print(f"{x:>5.2f} {nm:<8} {r['final']:>10.1f} {r['calmar']:>7.3f} "
                      f"{pp:>6.1f} {tv:>7.2f} {td:>8.1f} {ok:>4}")
    print('다음 질문: 회전액과 실제 거래일수 감소가 한국장·원화·납입 계좌에도 '
          '유지되는가? §15 후속이며 이 달러 진단으로 채택하지 않는다.')


if __name__ == '__main__':
    main()
