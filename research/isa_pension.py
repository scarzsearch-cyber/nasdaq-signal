# -*- coding: utf-8 -*-
"""
[ISA 만기 → 연금계좌 이체, 2026-08-31 소유자 승인] 세 번째 선택지를 계량한다.

배경: 화면 taxPanel 은 「연장 vs 3년마다 해지·재가입」만 비교한다
  (v203 회계 교정: 20년 중앙 135.24배 vs 114.38배).
  조세특례제한법 제91조의18 ④ 가 주는 세 번째 선택지 — 만기 60일 이내 연금계좌
  (IRP·연금저축) 납입 시 **납입액의 10%, 최대 300만원 추가 세액공제** — 가 분석에 없다.

핵심 제약 (이 계산의 전부):
  **레버리지 ETF 는 퇴직연금(IRP/DC)에서 매매 불가** — 근로자퇴직급여 보장법.
  IRP 는 위험자산 70% 한도도 있다. 즉 연금으로 옮긴 돈으로는 **전략 B 를 못 굴린다.**
  따라서 이 결정은 「일회성 세액공제 10%」 vs 「B(2배 규칙) − 1배 보유 의 복리 격차」다.
  격차가 지평에 대해 지수적으로 벌어지므로 손익분기 지평만 찾으면 답이 난다.

판정 아님 · 전략 무변경. 실행: python research/isa_pension.py
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

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                 # noqa: E402

G, X = EC.selfcheck()
idx = G.idx
n = len(idx)
PX = pd.Series(G.D['px'], index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))

CREDIT = 0.10          # 이체액의 10% 세액공제 (상한 300만원 → 이체 3,000만원에서 포화)
CAP = 3_000_000
HS = [(756, '3년'), (1260, '5년'), (1764, '7년'), (2520, '10년'),
      (3780, '15년'), (5040, '20년')]


def main():
    wB = EC.rule_dd(PX, -0.16, -0.16)
    aB = EC.sim2(wB, QLDR, MIXR)                 # ISA: 전략 B (2배 + 규칙)
    r1 = np.nan_to_num(PX.pct_change().values)   # 연금: 1배 지수 보유 (레버리지 불가)
    a1 = np.cumprod(1 + r1)

    print('\n[1] 같은 돈을 3년 뒤부터 굴렸을 때 — B(ISA) vs 1배 보유(연금)')
    print(f"{'남은 지평':>8} {'B 중앙':>9} {'1배 중앙':>9} {'배수비 B/1배':>13} "
          f"{'세액공제로 메우려면':>18}")
    for w, lab in HS:
        mb = np.median(aB[w:] / aB[:-w])
        m1 = np.median(a1[w:] / a1[:-w])
        ratio = mb / m1
        print(f'{lab:>8} {mb:>8.2f}배 {m1:>8.2f}배 {ratio:>12.2f}배 '
              f'{(ratio - 1) * 100:>17.0f}%')

    print('\n[2] 세액공제가 주는 것 — 일회성 10% (상한 300만원)')
    for amt in (10_000_000, 30_000_000, 50_000_000, 100_000_000):
        cr = min(amt * CREDIT, CAP)
        print(f'  이체 {amt/1e8:>4.2f}억원 → 세액공제 {cr:>10,.0f}원 '
              f'= 이체액의 {cr/amt:>5.2%}')
    print(f'  ※ 3,000만원 초과분엔 공제가 안 붙는다 — 클수록 효과가 희석된다.')

    print('\n[3] 손익분기 — 세액공제 10%(최대)가 복리 격차를 언제까지 이기나')
    hit = None
    for w, lab in HS:
        mb = np.median(aB[w:] / aB[:-w])
        m1 = np.median(a1[w:] / a1[:-w])
        gap = mb / m1 - 1
        win = '연금 우세' if gap < CREDIT else 'B(ISA) 우세'
        if hit is None and gap >= CREDIT:
            hit = lab
        print(f'  {lab:>4}: 복리 격차 {gap:>7.1%} vs 세액공제 {CREDIT:.0%}  → {win}')
    print(f'\n  손익분기: {hit} 이후로는 세액공제가 복리 격차를 못 따라간다.')
    print('  (연금 과세이연·연금소득세 3.3~5.5% 는 미반영 — 넣어도 부호는 안 바뀐다:')
    print('   ISA 도 과세이연이고, 위 격차는 세전 배수비라 양쪽에 같은 방향으로 작용)')

    print('\n[4] 이 계산이 다루지 않는 것 (판단에 필요)')
    print('  · 55세 이전 인출 시 기타소득세 16.5% — 유동성이 완전히 묶인다')
    print('  · 연금저축은 IRP 와 규정이 달라 별도 확인 필요 (레버리지 취급·위험자산 한도)')
    print('  · 소득이 없어 납부세액이 적으면 세액공제를 다 못 받는다 (환급 한도)')
    print('  · 위 배수비는 중앙값 — 꼬리에서는 1배 보유가 B 보다 나은 창도 있다')


if __name__ == '__main__':
    main()
