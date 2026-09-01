# -*- coding: utf-8 -*-
"""
[공유용 변형 1차 실측 — 배당다우존스50 + 나스닥100비레버리지50 공격, 2026-09-01]
소유자 요청: 본인 전략(B, 동결)을 공유하지 않고 지인에게 줄 별도(비레버리지) 전략의
"이미 있는 도구로 쉽게 구할 수 있나"에 대한 1차 실측. 판정 아님·전략 B 무변경
(§2 무접촉) — 새 파일 하나만 추가, 기존 파일은 전부 읽기만 한다.

구성 (전부 소유자 지시):
  공격 = 배당다우존스(div) 50% + 나스닥100 비레버리지(qqq 1x) 50%, 월초 재조정.
         (실물 대응: 458730 TIGER 미국배당다우존스 / 133690 TIGER 미국나스닥100)
  방어 = 미국채(ust5) + 금(gold) — **배당은 방어에서 뺀다.**
         이유: research/def_bond.py 실측 「배당은 방어 중 QQQ 상관 +0.775 ·
         최악5%일 평균 −1.77%」로 헤지력이 약한데, 이번 구성은 배당을 공격에
         이미 절반 넣었으므로 방어에도 또 넣으면 같은 약점 자산을 양쪽에
         중복 배치하는 셈이다.
  신호 = 기존 QQQ 252일 고점낙폭 rule_dd 그대로 1차 재사용 — 문턱만 별도 스캔.
         (공격 자산이 레버리지 0·배당 절반 섞여 원래보다 훨씬 잔잔해졌으므로
         −16%가 이 조합에도 맞는 문턱이라는 보장은 없다 — 그래서 [2]에서 스캔한다.)

엔진: eng_common.rule_dd / sim2 / fullmet, hist_defasset.mix_monthly_parts —
전부 기존 검증 함수를 그대로 호출한다(새 계산 로직 0). 데이터는
hist_defensive.build('chain') 54년 체인 — 전략 B 백테스트와 동일 재료.

★ 이 파일의 산출물은 1차 스크리닝이다 — CLAUDE.md §-1 규약대로 아직 다음이 없다:
  ⓑ 방어 비중을 손으로 몇 개만 골랐다 → 무작위 조합 분포로 재검증 안 함
  PBO/DSR · 20년창 p05 · 전 시작일 분포(slice_scan 방식) 안 함
채택·기각 어느 쪽도 아니다. "구하기 쉬운가"에 대한 1차 답만 낸다.

실행: python research/share_variant_divqqq.py
"""
# --- [v39 규약과 동일] 경로보정 ---------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defensive as DF                              # noqa: E402
import hist_defasset as DA                                # noqa: E402
import eng_common as EC                                   # noqa: E402

D = dict(DF.build('chain'))
idx = D['idx']
px = pd.Series(D['px'], index=idx)
n = len(idx)

r_qqq1x = np.nan_to_num(px.pct_change().values)            # 나스닥100 1배 (133690 대응)
r_div = np.asarray(D['schdr'], float)                       # 배당다우존스 체인 (458730 대응)
r_ust5 = np.nan_to_num(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE))
r_gold = np.nan_to_num(DA.gold_r(idx))

# 공격 다리: 배당 50 / 나스닥100(1x) 50, 월초 재조정
r_attack = DA.mix_monthly_parts(idx, dict(div=0.5, qqq=0.5),
                                 dict(div=r_div, qqq=r_qqq1x))

DEF_CANDS = {
    '국채70/금30': dict(ust5=0.70, gold=0.30),
    '국채60/금40': dict(ust5=0.60, gold=0.40),
    '국채50/금50': dict(ust5=0.50, gold=0.50),
    '국채100':     dict(ust5=1.00),
}

TH_GRID = [-10, -12, -14, -16, -18, -20, -22, -25]


def curve_for(defw, in_th, out_th=None):
    out_th = in_th if out_th is None else out_th
    r_def = DA.mix_monthly_parts(idx, defw, dict(ust5=r_ust5, gold=r_gold))
    w = EC.rule_dd(px, in_th / 100, out_th / 100)
    c = EC.sim2(w, r_attack, r_def)
    return c, w


def main():
    EC.selfcheck()   # 공용 엔진(rule_dd/sim2/fullmet) 자체가 살아있는지 먼저 확인
    print(f'\n데이터 구간: {idx[0].date()} ~ {idx[-1].date()}  ({n}행, 전략 B와 동일 체인)\n')

    print('[1] 기존 신호(-16/-16) 재사용 · 방어 후보 비교')
    print(f"{'방어 조합':<14}{'최종배수':>12}{'CAGR%':>8}{'MDD%':>8}{'Calmar':>8}{'전환수':>7}")
    for name, w0 in DEF_CANDS.items():
        c, w = curve_for(w0, -16)
        m = EC.fullmet(c, idx=idx)
        turns = int(np.sum(np.abs(np.diff(w))))
        print(f"{name:<14}{m['final']:>12.2f}{m['cagr']:>8.2f}{m['mdd']:>8.2f}{m['calmar']:>8.3f}{turns:>7}")

    bench_atk = np.cumprod(1 + r_attack)
    mb = EC.fullmet(bench_atk, idx=idx)
    print(f"{'(참고)공격만 보유':<14}{mb['final']:>12.2f}{mb['cagr']:>8.2f}{mb['mdd']:>8.2f}{mb['calmar']:>8.3f}{'-':>7}")

    print('\n[2] 방어 = 국채60/금40 고정 · 진입 문턱 스캔 (복귀문턱=진입문턱, 대칭)')
    print(f"{'문턱%':>7}{'최종배수':>12}{'CAGR%':>8}{'MDD%':>8}{'Calmar':>8}{'전환수':>7}")
    for th in TH_GRID:
        c, w = curve_for(DEF_CANDS['국채60/금40'], th)
        m = EC.fullmet(c, idx=idx)
        turns = int(np.sum(np.abs(np.diff(w))))
        print(f"{th:>7}{m['final']:>12.2f}{m['cagr']:>8.2f}{m['mdd']:>8.2f}{m['calmar']:>8.3f}{turns:>7}")


if __name__ == '__main__':
    main()
