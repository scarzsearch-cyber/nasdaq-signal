# -*- coding: utf-8 -*-
"""axis_defmix.sim_hold 다자산 재조정 회계의 독립 원장 검증 (2026-09-06 · 감사 도구 · CI 미등재).

왜: I1 `check_hold` 는 단일자산(재조정 거래 0)만 `sim_def` 와 대조한다 — 다자산 재조정의 비용·거래량은
어느 관문에도 안 걸린다(`audit/GATES_DATA_2026-09-06.md` 사각지대). 이 도구는 그 자리를 **엔진을 복제하지 않는**
금액 원장으로 잰다. 엔진·규약·동결값·원자료·관문은 손대지 않는다(읽기만).

엔진 계약(`axis_defmix.sim_hold` docstring · 2026-09-06 판독):
  ① 전일 신호(w[i-lag])대로 **당일 시작에** 전환 — 전체 자산에 cost 한 번(V *= 1-cost)
  ② 도피 구간 안 월/분기 첫 거래일: 편도 회전 turn = Σ|b_k/V − f_k|/2 · V *= 1 − rebal_cost·2·turn · 비중을 목표로
  ③ 그 다음 당일 수익. 첫날 수익은 0. 전환일에는 재조정을 하지 않는다(elif).
저장소의 비용 단위(`research/rebalance_accounting.py` docstring): 「fee = cost × 편도(half-L1) 회전 × 자산」.

독립 원장(이 파일): 자산별 **금액**·현금·거래 목록을 든다. 거래는 「목표 금액 − 보유 금액」으로 매도/매수 금액을 만들고
수수료 = 비용률 × 편도 회전 금액(½Σ|목표−보유|)을 현금에서 빼며, 현금은 항상 0 으로 되돌린다(전량 재투자).
전환·재조정 모두 같은 편도 단위 비용률을 쓴다 — 그래서 엔진 호출은 rebal_cost = 비용률/2 (엔진은 다리당 과금 ×2).
검사: 원장 최종·경로 vs 엔진 경로(상대 1e-12) · Σ보유 = 평가액 · 현금 0 · 수수료 ≥ 0 · 총수수료 = 거래 목록 합.

결함 주입(엔진 사본을 메모리에서만 변조 · 저장소 무접촉): 재조정 비용 누락 · 재조정 이중 부과 · 전환 이중 부과 ·
회전 편도 아님(×2) · v27형(비용이 비율에서 약분) · 미래참조(lag) · 첫날 수익 · 다리 하나 수익 누락 · 무해 변조(대조군).

실행: python audit/rebal_ledger_check.py  (종료코드 0 = 원본 통과 + 결함 전부 탐지 + 대조군 통과)
"""
import inspect
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import axis_defmix as DM  # noqa: E402

TOL = 1e-12


# ---------------------------------------------------------------- 독립 원장
def ledger_path(idx, w, rr, comp, weights, fee_oneway, lag=1, start=None, end=None, rebal='M'):
    """자산별 금액 원장. 반환: (평가액 Series, 거래 목록, 불변식 위반 목록)."""
    n = len(idx)
    lo = 0 if start is None else idx.searchsorted(pd.Timestamp(start))
    hi = n if end is None else idx.searchsorted(pd.Timestamp(end), side='right')
    keys = [k for k, v in weights.items() if v > 0]
    tot = float(sum(weights.values()))
    frac = {k: weights[k] / tot for k in keys}
    per = None if rebal is None else pd.Series(idx).dt.to_period(rebal).values

    def target_for(pos, V):
        if pos >= 1:
            return {'RISK': V}
        return {k: V * frac[k] for k in keys}

    def trade_to(hold, target, rate, day, why, trades, viol):
        """보유 금액 → 목표 금액. 매도·매수 금액과 수수료를 거래 목록에 남기고 현금을 0 으로 되돌린다."""
        V = sum(hold.values())
        cash = 0.0
        sold = bought = 0.0
        for k in set(hold) | set(target):
            h = hold.get(k, 0.0)
            t = target.get(k, 0.0)
            if t < h:
                sold += h - t
            elif t > h:
                bought += t - h
        oneway = 0.5 * (sold + bought)             # 편도 회전 금액 = ½Σ|목표−보유| (= 매도 = 매수, 전량 재투자)
        fee = rate * oneway
        cash += sold - fee                         # 매도 대금에서 수수료
        # 남은 현금을 목표 비율로 전부 재투자 — 수수료만큼 목표가 비례 축소된다
        V2 = V - fee
        tw = {k: (t / V) for k, t in target.items()} if V > 0 else {}
        new = {k: V2 * tw[k] for k in tw}
        cash = 0.0
        if fee < 0:
            viol.append('%s 수수료 음수 %.3e' % (day.date(), fee))
        if abs(sum(new.values()) - V2) > 1e-9 * max(V2, 1.0):
            viol.append('%s 재투자 뒤 Σ보유≠V−fee' % day.date())
        trades.append(dict(day=day, why=why, sold=sold, bought=bought, oneway=oneway, fee=fee))
        return new, cash

    trades, viol = [], []
    pos0 = w[lo]
    hold = target_for(pos0, 1.0)                   # 첫날: 진입 비용 0 · 수익 0
    cash = 0.0
    prev = pos0
    out = [sum(hold.values())]
    for i in range(lo + 1, hi):
        pos = w[i - lag] if i - lag >= lo else w[lo]
        V = sum(hold.values()) + cash
        if pos != prev:
            hold, cash = trade_to(hold, target_for(pos, V), fee_oneway, idx[i], 'switch', trades, viol)
            prev = pos
        elif pos < 1 and per is not None and per[i] != per[i - 1]:
            hold, cash = trade_to(hold, target_for(pos, V), fee_oneway, idx[i], 'rebal', trades, viol)
        # 당일 수익
        if 'RISK' in hold:
            hold['RISK'] *= (1.0 + float(np.nan_to_num(rr[i])))
        else:
            for k in keys:
                hold[k] *= (1.0 + float(np.nan_to_num(comp[k][i])))
        if cash != 0.0:
            viol.append('%s 현금 잔존 %.3e' % (idx[i].date(), cash))
        out.append(sum(hold.values()) + cash)
    return pd.Series(out, index=idx[lo:hi]), trades, viol


# ---------------------------------------------------------------- 합성 사례
def make_case(seed, n=140, keys=('div', 'ust10', 'gold')):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range('2024-01-02', periods=n)
    rr = rng.normal(0.0008, 0.02, n)
    comp = {k: rng.normal(0.0002, 0.006 + 0.004 * j, n) for j, k in enumerate(keys)}
    comp[keys[0]][5] = np.nan                       # 결측 하루 — 엔진은 nan_to_num(0)
    # 신호: 공격 → 도피(월 경계 2개 이상 포함) → 공격 → 도피 → 공격
    w = np.ones(n)
    a, b = 12 + int(rng.integers(0, 6)), 70 + int(rng.integers(0, 12))
    w[a:b] = 0.0
    c, d = b + 15 + int(rng.integers(0, 5)), min(n - 3, b + 45 + int(rng.integers(0, 10)))
    w[c:d] = 0.0
    D = {'idx': idx, 'qldr': rr}
    return D, w, comp


def compare(sim_fn, D, w, comp, weights, cost=DM.COST, rebal='M', start=None, end=None, lag=1):
    eng = sim_fn(D, w, comp, weights, cost=cost, lag=lag, start=start, end=end, rebal=rebal, rebal_cost=cost / 2.0)
    led, trades, viol = ledger_path(D['idx'], w, D['qldr'], comp, weights, cost, lag=lag, start=start, end=end, rebal=rebal)
    a = np.asarray(eng.values, float)
    b = np.asarray(led.values, float)
    if len(a) != len(b):
        return dict(ok=False, maxrel=np.inf, viol=viol + ['길이 %d vs %d' % (len(a), len(b))], trades=trades)
    rel = np.max(np.abs(a / b - 1.0))
    return dict(ok=(rel < TOL and not viol), maxrel=rel, viol=viol, trades=trades)


# ---------------------------------------------------------------- 결함 주입(메모리 사본)
MUTANTS = [
    ('rebal_cost_omitted', '재조정 비용 누락',
     'V *= (1 - rebal_cost * 2 * turn)', 'V *= 1.0'),
    ('rebal_cost_double', '재조정 비용 이중 부과',
     'V *= (1 - rebal_cost * 2 * turn)', 'V *= (1 - rebal_cost * 2 * turn) ** 2'),
    ('switch_cost_double', '전환 비용 이중 부과',
     'V *= (1 - cost)', 'V *= (1 - cost) ** 2'),
    ('turn_not_oneway', '회전을 편도가 아니라 양방향 합으로(×2)',
     'for k in keys) / 2.0', 'for k in keys)'),
    ('v27_cost_cancels', 'v27형 — 비용을 비율 재설정 뒤에 물어 다음날 약분',
     'V *= (1 - rebal_cost * 2 * turn)              # 구간 내 리밸런싱\n            buckets = {k: V * frac[k] for k in keys}',
     'buckets = {k: V * frac[k] for k in keys}\n            V *= (1 - rebal_cost * 2 * turn)'),
    ('lookahead_lag', '미래참조 — 당일 신호로 당일 체결',
     'pos = w[i - lag] if i - lag >= lo else w[lo]', 'pos = w[i]'),
    ('first_day_return', '첫날 수익을 먹음',
     'if i > lo:                                        # ② 당일 수익', 'if True:'),
    ('leg_return_dropped', '다리 하나(gold) 수익 누락',
     'buckets[k] *= (1 + R[k][i])', "buckets[k] *= (1 + (R[k][i] if k != 'gold' else 0.0))"),
]
CONTROL = ('control_comment', '무해 변조(주석만) — 대조군 · 통과해야 한다',
           '# ① 당일 시작에 전환', '# (대조군) 당일 시작에 전환')


def mutant_sim(old, new):
    src = inspect.getsource(DM.sim_hold)
    assert src.count(old) == 1, '변조 대상 문자열이 1회가 아니다: %r' % old[:40]
    src = src.replace(old, new)
    ns = {'np': np, 'pd': pd, 'COST': DM.COST}
    exec(src, ns)
    return ns['sim_hold']


# ---------------------------------------------------------------- 실행
def main():
    W = {'div': .4, 'ust10': .4, 'gold': .2}
    cases = [make_case(s) for s in range(12)]
    grid = [dict(rebal='M'), dict(rebal='Q'), dict(rebal=None),
            dict(rebal='M', start='2024-03-01'), dict(rebal='M', end='2024-06-14'),
            dict(rebal='M', start='2024-02-20', end='2024-07-01')]
    fails = 0
    print('== 원본 sim_hold vs 독립 원장 (사례 %d × 격자 %d) ==' % (len(cases), len(grid)))
    worst = 0.0
    n_trades = 0
    for D, w, comp in cases:
        for g in grid:
            r = compare(DM.sim_hold, D, w, comp, W, **g)
            worst = max(worst, r['maxrel'])
            n_trades += len(r['trades'])
            if not r['ok']:
                fails += 1
                print('  FAIL', g, 'maxrel %.2e' % r['maxrel'], r['viol'][:3])
    print('  최대 상대오차 %.2e · 거래 %d건(전환+재조정) · 불변식 위반 %s' % (worst, n_trades, '0' if fails == 0 else fails))
    # 단일자산 축퇴: 원장 = sim_def (엔진 자체 검산과 같은 방향의 독립 확인)
    D, w, comp = cases[0]
    led1, _, _ = ledger_path(D['idx'], w, D['qldr'], comp, {'div': 1.0}, DM.COST, rebal='M')
    sd = DM.sim_def(D, w, np.nan_to_num(comp['div']))
    e1 = abs(led1.iloc[-1] / sd.iloc[-1] - 1)
    print('  단일자산 축퇴 원장 vs sim_def 오차 %.2e %s' % (e1, 'OK' if e1 < TOL else 'FAIL'))
    fails += int(e1 >= TOL)

    print('== 결함 주입(엔진 메모리 사본) — 원장이 잡아야 한다 ==')
    detect = 0
    for mid, why, old, new in MUTANTS:
        fn = mutant_sim(old, new)
        caught = False
        mx = 0.0
        for D, w, comp in cases[:4]:
            for g in grid[:3]:
                try:
                    r = compare(fn, D, w, comp, W, **g)
                except Exception as e:  # noqa: BLE001
                    r = dict(ok=False, maxrel=np.inf, viol=[repr(e)])
                mx = max(mx, r['maxrel'])
                if not r['ok']:
                    caught = True
        detect += int(caught)
        print('  %-20s %-40s %s  (최대 상대오차 %.2e)' % (mid, why, 'CAUGHT' if caught else 'MISSED', mx))
        if not caught:
            fails += 1
    cid, cwhy, cold, cnew = CONTROL
    fn = mutant_sim(cold, cnew)
    ok_ctrl = all(compare(fn, D, w, comp, W, **g)['ok'] for D, w, comp in cases[:4] for g in grid[:3])
    print('  %-20s %-40s %s' % (cid, cwhy, 'PASS' if ok_ctrl else 'FAIL(과민)'))
    fails += int(not ok_ctrl)
    print('== 합계: 결함 %d/%d 탐지 · 대조군 %s · 실패 %d ==' % (detect, len(MUTANTS), 'PASS' if ok_ctrl else 'FAIL', fails))
    return 0 if fails == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
