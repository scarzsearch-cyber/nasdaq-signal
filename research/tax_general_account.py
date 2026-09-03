# -*- coding: utf-8 -*-
"""
[사실 확인] 일반계좌(ISA 아님)에서 「배당 다리를 안 팔면」 세금이 얼마나 절약되나 (2026-09-03, 소유자 질문)

소유자: 「배당 다리를 안 팔아도 되니까 ISA 가 아닌 상황에선 세금 감면 도움을 크게 받는 거 아냐?」

⚠ **전략 무접촉 · 채택 아님.** 「헤지6/4 를 채택하라」가 아니라 **「일반계좌라면 그 이점이 얼마인가」**만 잰다.
  소유자 계좌는 **ISA 중개형**이라 계좌 안 매매는 만기 손익통산이고 전환해도 과세가 없다(설명서 §④) — 이 표는 **일반계좌 몫이 생겼을 때**의 이야기다.

세제 규약 (국내상장 해외 ETF · 일반계좌):
  · 매매차익은 **배당소득 15.4%** 원천징수. **손실 상계 불가**(배당소득은 손익통산이 안 된다) → 매도마다 `max(이익, 0)` 에만 과세.
  · 보유 중에는 과세 없음(미실현). 팔 때만 낸다 → **안 팔면 이연**된다. 그것이 소유자가 지적한 이점이다.
  · 금융소득종합과세(연 2,000만원 초과)는 넣지 않았다 — 인출 설계에 따라 달라져 여기서는 15.4% 단일세율로만.

비교 (54년 · 엔진 · 편도 0.1% 거래비용은 별도로 이미 반영된 곡선 위에서 세금만 추가):
  ① **현행 B** — 전환마다 보유 전량을 팔고 산다. 매도 100% → 실현 100%.
  ② **헤지6/4** — 공격 = QLD 60 + 배당 40 · 방어 = 배당 40 + 국채 40 + 금 20.
     **배당 40% 는 양쪽에 다 있으므로 전환 때 팔지 않는다.** 대신 **공격 다리를 월 1회 재조정**하며 이긴 쪽을 판다 → 그때마다 과세.
  ③ **헤지6/4 (재조정 없음)** — 비율이 흘러가게 두는 변형. 세금은 가장 적지만 비중이 표류한다(참고용).

예측 (결과 전 등록 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 세전 격차(B 217,110배 vs 헤지6/4 31,804배 = 6.8배)는 세후에 **줄어들지만 뒤집히지는 않는다**.
  P2 헤지6/4 의 월 재조정이 만드는 과세가 전환 절감을 상당 부분 상쇄한다 — 재조정 없는 변형(③)이 ②보다 뚜렷이 낫다.
  P3 세후에도 B 가 3배 이상 앞선다.

실행: python research/tax_general_account.py   (약 20초 · 네트워크 0 · 파일 쓰기 0)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
_sys.path.insert(0, _os.path.join(_ROOT, 'deploy'))

import sys
import io
import contextlib
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                   # noqa: E402
import hist_defensive as DF                               # noqa: E402
import hist_defasset as DA                                # noqa: E402
import reentry_lib as RL                                  # noqa: E402
from build_stats import STRATS, defensive_r               # noqa: E402

TAX = 0.154
L = '=' * 112


def sell(val, basis, frac):
    """보유 일부를 판다 → (매도대금(세후), 남은 평가액, 남은 원가, 낸 세금)"""
    proceeds = val * frac
    cost = basis * frac
    gain = max(proceeds - cost, 0.0)
    tax = gain * TAX
    return proceeds - tax, val - proceeds, basis - cost, tax


def main():
    print(L); print('일반계좌 세후 — 「배당 다리를 안 팔면」 얼마나 절약되나 (전략 무접촉)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        D = dict(DF.build('chain'))
    idx = pd.DatetimeIndex(D['idx'])
    qldr = np.nan_to_num(np.asarray(D['qldr'], float))
    divr = np.nan_to_num(np.asarray(D['schdr'], float))
    basket = np.nan_to_num(np.asarray(defensive_r(idx, divr, 'mix'), float))
    px = pd.Series(D['px'], index=idx).astype(float)
    w = np.asarray(EC.rule_dd(px, -0.16, -0.16), float)          # 1=공격 0=방어
    pos = np.empty(len(w)); pos[0] = w[0]; pos[1:] = w[:-1]      # lag 1 집행
    月末 = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).transform('last').values

    # ── ① 현행 B : 전환마다 전량 매도 ────────────────────────────────────────
    v, b, taxes, n_sell = 1.0, 1.0, 0.0, 0
    # ⚠ pos 는 이미 lag=1 집행값이다. pos[i] 를 그대로 쓴다 — pos[i-1] 로 또 밀면 2칸 지연(실측 세전 96,562배로 반토막).
    for i in range(1, len(idx)):
        v *= (1 + (qldr[i] if pos[i] > 0.5 else basket[i]))
        if pos[i] != pos[i - 1]:                                  # 전환일 — 전량 교체
            cash, _, _, t = sell(v, b, 1.0)
            taxes += t; n_sell += 1
            v, b = cash, cash
    B_after, B_tax, B_sell = v, taxes, n_sell

    # ── ②③ 헤지6/4 : 배당 다리는 안 판다 ────────────────────────────────────
    def hedge(rebal_monthly):
        # 슬리브 3개: L(레버리지) · Dv(배당) · Df(국채+금 = 방어 중 60% 부분)
        vL, bL = 0.6, 0.6
        vD, bD = 0.4, 0.4          # 배당 — 절대 안 판다
        vF, bF = 0.0, 0.0          # 국채+금
        # 방어 바스켓 중 배당을 뺀 나머지(국채40+금20)의 수익률
        ust = np.nan_to_num(np.asarray(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE), float))
        gold = np.nan_to_num(np.asarray(DA.gold_r(idx), float))
        rF = (0.40 * ust + 0.20 * gold) / 0.60
        taxes = 0.0; n = 0
        for i in range(1, len(idx)):
            vL *= (1 + qldr[i]); vD *= (1 + divr[i]); vF *= (1 + rF[i])
            if pos[i] != pos[i - 1]:
                if pos[i] > 0.5:                                  # 방어 → 공격: 국채·금 팔고 QLD 산다
                    cash, vF, bF, t = sell(vF, bF, 1.0)
                    taxes += t; n += 1
                    vL, bL = cash, cash
                else:                                             # 공격 → 방어: QLD 팔고 국채·금 산다
                    cash, vL, bL, t = sell(vL, bL, 1.0)
                    taxes += t; n += 1
                    vF, bF = cash, cash
            elif rebal_monthly and pos[i] > 0.5 and idx[i] == 月末[i]:
                tot = vL + vD
                tgtL, tgtD = 0.6 * tot, 0.4 * tot
                if vL > tgtL:                                     # 레버리지가 이겼다 → 판다
                    f = (vL - tgtL) / vL
                    cash, vL, bL, t = sell(vL, bL, f)
                    taxes += t; n += 1
                    vD += cash; bD += cash
                elif vD > tgtD:                                   # 배당이 이겼다 → 판다(배당도 이때는 판다)
                    f = (vD - tgtD) / vD
                    cash, vD, bD, t = sell(vD, bD, f)
                    taxes += t; n += 1
                    vL += cash; bL += cash
        return vL + vD + vF, taxes, n

    H_after, H_tax, H_sell = hedge(True)
    H2_after, H2_tax, H2_sell = hedge(False)
    # ★ ③ 의 세전도 실제로 계산한다 — 표의 숫자 칸에 「—」를 넣지 않는다(소유자 지시 2026-09-03)
    def hedge_pretax(rebal_monthly):
        vL, vD, vF = 0.6, 0.4, 0.0
        ust_ = np.nan_to_num(np.asarray(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE), float))
        gold_ = np.nan_to_num(np.asarray(DA.gold_r(idx), float))
        rF_ = (0.40 * ust_ + 0.20 * gold_) / 0.60
        for i in range(1, len(idx)):
            vL *= (1 + qldr[i]); vD *= (1 + divr[i]); vF *= (1 + rF_[i])
            if pos[i] != pos[i - 1]:
                if pos[i] > 0.5:
                    vL += vF; vF = 0.0
                else:
                    vF += vL; vL = 0.0
            elif rebal_monthly and pos[i] > 0.5:
                if idx[i] == 月末[i]:
                    tot = vL + vD; vL, vD = 0.6 * tot, 0.4 * tot
        return vL + vD + vF
    preH2 = hedge_pretax(False)

    # ── 세전 기준 ───────────────────────────────────────────────────────────
    def pre(att):
        Dx = dict(D); Dx['qldr'] = np.asarray(att, float); Dx['schdr'] = basket
        with contextlib.redirect_stdout(io.StringIO()):
            c, _, _ = RL.run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
        return float(np.asarray(c, float)[-1])
    preB = pre(qldr)
    preH = pre(DA.mix_monthly_parts(idx, {'a': 0.6, 'b': 0.4}, {'a': qldr, 'b': divr}))

    # 검산: 세금 0 으로 돌린 수동 루프가 공표 곡선과 같은 자리인가 (비용 0 이라 조금 커야 정상)
    chk = 1.0
    for i in range(1, len(idx)):
        chk *= (1 + (qldr[i] if pos[i] > 0.5 else basket[i]))
    print(f'  [검산] 세금·비용 0 수동 루프 {chk:,.0f}배 vs 공표 B(비용 0.1%) 217,110배 — 비용만큼 커야 정상')
    print(f'  창 {idx[0].date()} ~ {idx[-1].date()} · 세율 {TAX*100:.1f}% · 손실 상계 없음(배당소득)')
    print(f"\n  {'':<26}{'세전 최종':>13}{'세후 최종':>13}{'낸 세금':>11}{'과세 매도':>10}{'세후/세전':>10}")
    for nm, pr, af, tx, ns in (('① 현행 B', preB, B_after, B_tax, B_sell),
                               ('② 헤지6/4 (월 재조정)', preH, H_after, H_tax, H_sell),
                               ('③ 헤지6/4 (재조정 없음)', preH2, H2_after, H2_tax, H2_sell)):
        print(f'  {nm:<26}{pr:>12,.0f}배{af:>12,.0f}배{tx:>10,.0f}{ns:>10}{af/pr:>10.3f}')
    print(f'\n  세전 격차 B ÷ 헤지6/4 = {preB/preH:>6.2f}배')
    print(f'  세후 격차 B ÷ 헤지6/4 = {B_after/H_after:>6.2f}배  (재조정 없는 변형 대비 {B_after/H2_after:.2f}배)')
    print(f'\n  ★ 「배당을 안 판다」의 이점: 헤지6/4 의 과세 매도가 전환 {B_sell}회 → {H_sell}건으로 바뀐다.')
    print(f'    단 ② 는 월 재조정이 과세를 새로 만든다 — ③(재조정 없음)과 비교하면 그 크기가 보인다.')
    print('\n예측 대조:')
    print(f'  P1 세후에 격차가 줄지만 안 뒤집힌다 → {"맞음" if B_after > H_after else "**틀림**"} '
          f'(세전 {preB/preH:.2f}배 → 세후 {B_after/H_after:.2f}배)')
    print(f'  P2 재조정 없는 ③ 이 ② 보다 낫다 → {"맞음" if H2_after > H_after else "**틀림**"} ({H2_after:,.0f} vs {H_after:,.0f})')
    print(f'  P3 세후에도 B 가 3배 이상 → {"맞음" if B_after/H_after >= 3 else "**틀림**"}')
    # ── 소유자 질문: ISA vs 일반계좌 두 갈래 · 지평 창으로 ──────────────────
    print('')
    print(L); print('[소유자 질문] ISA vs 일반계좌 — 같은 B 를 두 계좌에서 굴리면'); print(L)
    print('  ISA 중개형 = 계좌 안 매매 무과세 · 만기 손익통산 후 순이익에 9.9% 분리과세')
    print('  일반계좌   = 국내상장 해외 ETF 매매차익이 배당소득 15.4% · 손실 상계 불가 · 매도마다 과세')
    print('  ⚠ ISA 의 200만원 비과세는 원금 규모에 따라 달라 넣지 않았다(ISA 에 불리한 쪽 = 보수적).')
    ISA = 0.099
    Dx = dict(D); Dx['qldr'] = qldr; Dx['schdr'] = basket
    with contextlib.redirect_stdout(io.StringIO()):
        aB2, wv, _ = RL.run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
    aB2 = np.asarray(aB2, float)
    SWi = np.where(np.abs(np.diff(np.asarray(wv, float))) > 0)[0] + 1

    def after_gen(a, s, e):
        v, last = 1.0, a[s]
        for i in SWi:
            if s < i < e:
                g = a[i] / last
                v *= (1 + (g - 1) * (1 - TAX)) if g > 1 else g
                last = a[i]
        g = a[e] / last
        return v * ((1 + (g - 1) * (1 - TAX)) if g > 1 else g)

    def after_isa(a, s, e):
        g = a[e] / a[s]
        return 1 + (g - 1) * (1 - ISA) if g > 1 else g

    print('')
    print(f"  {'지평':<10}{'창 수':>7}{'세전 중앙':>12}{'ISA 세후':>12}{'일반 세후':>12}{'일반의 손실':>12}")
    for yy, lab in ((10, '10년'), (20, '20년'), (30, '30년'), (None, '54년 전체')):
        if yy is None:
            s0, e0 = 0, len(aB2) - 1
            pm, im, gm = aB2[-1] / aB2[0], after_isa(aB2, s0, e0), after_gen(aB2, s0, e0)
            print(f'  {lab:<10}{1:>7}{pm:>11,.0f}배{im:>11,.0f}배{gm:>11,.0f}배{(gm/im-1)*100:>11.1f}%')
            continue
        W = int(yy * 252)
        pl, il, gl = [], [], []
        for s0 in range(0, len(aB2) - W, 63):
            e0 = s0 + W
            pl.append(aB2[e0] / aB2[s0]); il.append(after_isa(aB2, s0, e0)); gl.append(after_gen(aB2, s0, e0))
        pm, im, gm = np.median(pl), np.median(il), np.median(gl)
        print(f'  {lab:<10}{len(pl):>7}{pm:>11,.1f}배{im:>11,.1f}배{gm:>11,.1f}배{(gm/im-1)*100:>11.1f}%')
    print('')
    print('  ※ 「일반의 손실」 = 같은 창에서 일반계좌가 ISA 대비 몇 % 적게 남는가(중앙).')
    print('  ⚠ ISA 는 연 2,000만원 · 총 1억 납입 한도가 있다 — 그 이상은 일반계좌 몫이다(§5-8 이 그 몫을 잰 이유).')
    print('')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 이 표는 15.4% 단일세율이다 — 금융소득종합과세(연 2,000만 초과)에 걸리면 세율이 오르고 고회전 쪽이 더 불리해진다.')
    print('  Q-b 소유자 계좌는 ISA 라 이 표는 「일반계좌 몫이 생겼을 때」에만 쓰인다(설명서 §④).')


if __name__ == '__main__':
    main()
