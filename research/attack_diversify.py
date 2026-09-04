# -*- coding: utf-8 -*-
"""
[실험 · 소유자 요청] 공격 다리에 무엇을 섞어야 변동성이 **비선형**으로 줄어드나 — 분산효과의 상한 (2026-09-03)

소유자: 「SCHD 를 섞어도 변동성을 확 줄이진 못한다는 거잖아. 선형이 아닌 분산효과로 수익은 높아지는데 변동성이 더 줄거나,
        수익 대비 변동성을 줄일 보험이 더 없는지 분석해 보고 싶어.」

⚠ **전략 무접촉.** 후보를 채택하지 않는다. 관문 ①②③ 은 결과 전에 박는다.

★ **왜 SCHD 는 선형이었나 — 수학이 먼저다.** 두 자산 배합의 분산은 σ² = w²σ₁² + (1−w)²σ₂² + 2w(1−w)ρσ₁σ₂ 다.
  **분산효과(볼록성)는 오직 ρ 가 낮을 때 생긴다.** QQQ↔SCHD 의 ρ 는 **+0.71**(§5-31 실측)이라 거의 직선이 된다.
  ρ 가 낮은 자산은 이 저장소에 이미 측정돼 있다 — §5-16 A: **국채 −0.16 · 금 −0.03 · T-bill −0.01**(방어 중 상관).
  그래서 이 파일의 진짜 질문은 **「배당 대신 국채·금을 공격 다리에 섞으면 볼록성이 생기나」**이고, 그 답은 **비용을 얼마에 사는가**로 귀결된다.

★ **이미 무덤에 있는 것 (재탐색 아님 · 대조용)**: 현금 20~30% 상시 **71개 창 승률 0%**(§1 v47) · 다자산 리스크패리티×추세 **② 참패**(5.9 vs 62배) ·
  변동성 타깃팅 **MDD −80.0~−87.1%**(충격형 −96.2~−97.7%) · OTM 풋 테일헤지 **문헌 기각**(분산위험프리미엄 음) · 방어 인버스 슬리브 **0.997배**(§5-24) ·
  트랜치 **관문① +5.0% 미달**. **이 파일은 그것들을 다시 돌리지 않는다** — 「공격 다리 정적 배합」이라는 한 형태만, 자산만 바꿔 가며 잰다.

무엇을 재나 (배합 상대만 바꾼다 · 규칙 −16/−16 과 방어 40/40/20 은 고정 · 월 1회 재조정):
  X ∈ {배당(SCHD 체인) · 국채 ust5 · 금 · 방어바스켓 40/40/20 · T-bill}  ·  w(QLD) = 100~50%
  ① 상관 실측(전체·QQQ 최악 5% 일) ② 변동성·MDD·수익 ③ **볼록성 지표** — 「같은 변동성을 QLD 비중만 줄여 얻었을 때의 수익」과 비교해
     **분산 보너스**가 실제로 있는가(있으면 곡선이 직선 위로 부푼다) ④ 관문 ①②③.

사전 등록 예측 (결과 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 국채·금·T-bill 은 SCHD 보다 **변동성을 더 많이** 줄인다(상관이 낮으므로). 10%p 당 −8% 이상.
  P2 그러나 **분산 보너스는 작다** — 2배 자산의 변동성이 워낙 커서 σ₁ 이 지배한다. 볼록성 지표는 어느 조합에서도 「수익이 오르면서 변동성이 준다」를 못 만든다.
  P3 **금이 가장 볼록**하다(ρ≈0 · 자체 수익 > 0). 그러나 관문 ① 은 못 넘는다.
  P4 T-bill 은 사실상 「현금 상시 보유」와 같아 §1 v47 의 재현이 된다 — 수익만 깎인다.
  P5 어떤 X 도 ①②③ 동시 통과 0.

실행: python research/attack_diversify.py   (약 30초 · 네트워크 0 · 파일 쓰기 0)
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
import hist_defasset as DA                                # noqa: E402
import hist_defensive as DF                               # noqa: E402
import reentry_lib as RL                                  # noqa: E402
from build_stats import STRATS, defensive_r               # noqa: E402

L = '=' * 122
WS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]


def met(c, idx):
    c = np.asarray(c, float)
    m = EC.fullmet(c, idx=idx)
    r = pd.Series(c, index=idx).pct_change()
    m['vol'] = float(r.std(ddof=1) * np.sqrt(252) * 100)
    m['p05_20'] = EC.p05_20y(c)
    s = pd.Series(c, index=idx)
    q = (s / s.shift(2520)).dropna()
    m['med10'] = float(q.median()) if len(q) else np.nan
    m['p05_10'] = float(q.quantile(0.05)) if len(q) else np.nan
    return m


def blocks(c, idx, nb=4):
    c = np.asarray(c, float)
    e = np.linspace(0, len(c), nb + 1).astype(int)
    return [EC.fullmet(c[a:b] / c[a], idx=idx[a:b])['calmar'] for a, b in zip(e[:-1], e[1:])]


def main():
    print(L); print('공격 다리 분산 — 무엇을 섞어야 변동성이 비선형으로 줄어드나 (전략 무접촉 · 채택 아님)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        D = dict(DF.build('chain'))
    idx = pd.DatetimeIndex(D['idx'])
    qldr = np.asarray(D['qldr'], float)
    divr = np.asarray(D['schdr'], float)
    px = pd.Series(D['px'], index=idx).astype(float)
    # 방어 부품 (엔진의 방어 바스켓과 같은 부품)
    ust = np.asarray(DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE), float)
    gold = np.asarray(DA.gold_r(idx), float)
    tb = np.asarray(DA._short_rate(idx), float) / 252.0
    basket = np.asarray(defensive_r(idx, divr, 'mix'), float)
    cand = {'배당(SCHD 체인)': divr, '국채 ust5(선물형)': ust, '금': gold,
            '방어바스켓 40/40/20': basket, 'T-bill(현금)': tb}
    rq = px.pct_change()
    q05 = rq.quantile(0.05)
    print(f'  엔진 {idx[0].date()} ~ {idx[-1].date()} · 규칙 −16/−16 · 방어 40/40/20 고정 · 공격 다리만 배합(월 1회 재조정)')
    print(f'\n  [상관] QQQ 일간수익 대비 — 분산효과의 원천은 이것 하나다')
    print(f"    {'자산':<22}{'전체 ρ':>10}{'QQQ 최악5%일 ρ':>16}{'연변동성':>10}{'연수익':>9}")
    for nm, r in cand.items():
        s = pd.Series(np.nan_to_num(r), index=idx)
        c_all = float(np.corrcoef(rq.fillna(0), s)[0, 1])
        m = rq <= q05
        c_bad = float(np.corrcoef(rq[m].fillna(0), s[m])[0, 1])
        cc = np.cumprod(1 + np.nan_to_num(r))
        yrs = (idx[-1] - idx[0]).days / 365.25
        print(f'    {nm:<22}{c_all:>+10.3f}{c_bad:>+16.3f}{s.std()*np.sqrt(252)*100:>9.1f}%{(cc[-1]**(1/yrs)-1)*100:>8.2f}%')

    ALL = {}
    for nm, r in cand.items():
        print('\n' + L); print(f'[{nm}] 을 공격 다리에 섞을 때'); print(L)
        # [2026-09-04 코드리뷰] 「분산보너스」 열을 뺐다. 이 열은 무수익 직선을
        # 기준으로 잡아 전부 「초과」로 찍히는 잘못된 값이었고, 아래 요약 A 가
        # 이미 그 사실을 적으면서 T-bill 기준으로 다시 낸다. 틀린 값을 40줄 위에
        # 먼저 보여주고 나중에 정정하는 배치라 읽는 사람이 틀린 쪽을 먼저 가져간다
        # (§-1 ③: 철회한 주장을 남겨두지 마라). 값은 요약 A 에만 있다.
        print(f"  {'QLD':>5}{'최종배수':>13}{'CAGR':>8}{'변동성':>8}{'vs100':>8}{'MDD':>8}{'Calmar':>8}"
              f"{'ΔCal':>8}{'20y p05':>9}{'Δp05':>8}{'10년중앙':>9}{'블록':>5}  관문")
        rows = {}
        for w in WS:
            att = np.asarray(DA.mix_monthly_parts(idx, {'a': w, 'b': 1 - w},
                                                  {'a': qldr, 'b': np.nan_to_num(r)}), float)
            Dx = dict(D); Dx['qldr'] = att; Dx['schdr'] = basket
            with contextlib.redirect_stdout(io.StringIO()):
                c, _, _ = RL.run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
            rows[w] = dict(m=met(c, idx), bl=blocks(c, idx), curve=np.asarray(c, float))
        ALL[nm] = rows
        b = rows[1.0]
        for w in WS:
            m = rows[w]['m']
            wins = sum(1 for x, y in zip(rows[w]['bl'], b['bl']) if x > y)
            d1 = m['calmar'] / b['m']['calmar'] - 1
            dp = m['p05_20'] / b['m']['p05_20'] - 1
            g = (d1 > 0.102, dp >= 0, wins >= 3)
            tag = '★①②③' if all(g) else ('①' if g[0] else '-') + ('②' if g[1] else '-') + ('③' if g[2] else '-')
            print(f"  {w*100:>4.0f}%{m['final']:>13,.0f}{m['cagr']:>7.2f}%{m['vol']:>7.1f}%"
                  f"{(m['vol']/b['m']['vol']-1)*100:>+7.1f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}{d1:>+7.1%}"
                  f"{m['p05_20']:>8.1f}배{dp:>+7.1%}{m['med10']:>8.1f}배{wins:>4}/4  {tag}")

    # ── 분산 보너스: 같은 변동성을 「현금(T-bill)」으로 만들었을 때와 비교 ────────
    print('\n' + L); print('요약 A — 분산 보너스: **같은 변동성**을 현금으로 만들었을 때 대비 수익 차이'); print(L)
    print('  ※ 분산 보너스는 이 표에만 있다. 초판은 위 표에도 열이 하나 있었는데 무수익 직선 기준이라 전부')
    print('  「초과」로 찍히는 잘못된 값이었고, 2026-09-04 코드리뷰에서 그 열을 삭제했다.')
    print('  기준선은 **T-bill 배합 곡선**이다. 같은 연변동성이 되도록 T-bill 비중을 보간해 그때의 CAGR 과 비교한다.')
    tbv = [(ALL['T-bill(현금)'][w]['m']['vol'], ALL['T-bill(현금)'][w]['m']['cagr']) for w in WS]
    tbv = sorted(tbv)
    xs = [v for v, _ in tbv]; ys = [c for _, c in tbv]
    print(f"\n  {'배합 상대':<22}{'QLD':>6}{'변동성':>9}{'CAGR':>9}{'현금으로 같은 변동성':>20}{'분산 보너스':>12}")
    for nm in cand:
        for w in WS[1:]:
            m = ALL[nm][w]['m']
            cash_cagr = float(np.interp(m['vol'], xs, ys))
            print(f"  {nm:<22}{w*100:>5.0f}%{m['vol']:>8.1f}%{m['cagr']:>8.2f}%{cash_cagr:>19.2f}%{m['cagr']-cash_cagr:>+11.2f}%p")

    # ── 금이 ①③ 을 통과했다 → §-1 ⓐ 무조건 반증 ─────────────────────────────
    print('\n' + L); print('요약 B — [반증 · §-1 ⓐ] 금이 관문 ①③ 을 통과했다. 시대를 쪼개 본다'); print(L)
    print('  ★ 이 저장소는 금에 대해 이미 경고를 갖고 있다 — §5-16 A: 「금의 73-74 +139.5% 는 1971 금 자유화 국면 ·')
    print('    HANDOFF §2 방법론의 일반화 금지 대상」. 즉 **금의 이득이 1970년대에 몰려 있는지**가 첫 질문이다.')
    ERAS = [('1972~1980 (금 자유화)', '1972-01-01', '1980-12-31'), ('1981~1999', '1981-01-01', '1999-12-31'),
            ('2000~2012', '2000-01-01', '2012-12-31'), ('2013~2026', '2013-01-01', '2026-12-31')]
    print(f"\n  {'구간':<22}{'B(QLD100%)':>13}{'QLD70+금30':>13}{'배수비':>9}{'B MDD':>9}{'배합 MDD':>10}{'금 자체 CAGR':>13}")
    g70 = ALL['금'][0.7]['curve']; b100 = ALL['금'][1.0]['curve']
    gs = pd.Series(np.cumprod(1 + np.nan_to_num(gold)), index=idx)
    for nm2, a2, b2 in ERAS:
        m2 = (idx >= pd.Timestamp(a2)) & (idx <= pd.Timestamp(b2))
        if m2.sum() < 252:
            continue
        x1 = b100[m2]; x2 = g70[m2]; gg = gs[m2]
        yrs = (idx[m2][-1] - idx[m2][0]).days / 365.25
        r1 = x1[-1] / x1[0]; r2 = x2[-1] / x2[0]
        d1 = EC.fullmet(x1 / x1[0], idx=idx[m2])['mdd']; d2 = EC.fullmet(x2 / x2[0], idx=idx[m2])['mdd']
        print(f'  {nm2:<22}{r1:>12.2f}배{r2:>12.2f}배{r2/r1:>9.2f}{d1:>8.1f}%{d2:>9.1f}%'
              f'{(gg.iloc[-1]/gg.iloc[0])**(1/yrs)*100-100:>12.2f}%')
    print('\n  → 금 배합이 이기는 구간이 **1970년대 하나**면 그것은 규칙이 아니라 그 시대의 금값 이야기다.')
    print('    네 블록 전부에서 이긴다면 반대로 「시대 산물」 설명은 약해진다 — 아래 숫자로 직접 판단한다.')

    # ── 요약 C: 이미 갖고 있는 비선형 보험 ───────────────────────────────────
    # [2026-09-04 코드리뷰] 여기 「이 측정이 낳은 다음 질문」 머리글이 내용 없이
    # 한 번 더 찍히고 있었다(진짜 블록은 이 함수 끝에 있다). §-1 ⑥ 이 요구하는
    # 필수 출력이라, 빈 머리글을 먼저 본 사람은 그 절이 비었다고 읽는다.
    print('\n' + L); print('요약 C — 「수익은 오르는데 변동성은 준다」를 실제로 만든 것은 무엇인가'); print(L)
    static = np.cumprod(1 + np.nan_to_num(qldr))
    ms = met(static, idx); mb = ALL['금'][1.0]['m']
    print(f"  {'':<26}{'CAGR':>9}{'연변동성':>10}{'MDD':>9}{'최종배수':>14}")
    print(f"  {'2배 계속보유 (신호 없음)':<26}{ms['cagr']:>8.2f}%{ms['vol']:>9.1f}%{ms['mdd']:>8.1f}%{ms['final']:>14,.0f}")
    print(f"  {'B — 같은 자산 + 전환뿐':<26}{mb['cagr']:>8.2f}%{mb['vol']:>9.1f}%{mb['mdd']:>8.1f}%{mb['final']:>14,.0f}")
    print(f"  차이: CAGR {mb['cagr']-ms['cagr']:+.2f}%p · 변동성 {mb['vol']-ms['vol']:+.1f}%p · MDD {mb['mdd']-ms['mdd']:+.1f}%p")
    print('  ★ **같은 자산인데 수익이 오르면서 변동성과 낙폭이 동시에 준다.** 소유자가 찾는 「비선형」은 여기 있고, 이미 갖고 있다.')
    print('  정적 배합은 두 자산을 **항상 같은 비율**로 섞으므로 직선 위를 움직인다. 전환은 **상태에 따라 노출을 0/100 으로 바꾸므로**')
    print('  같은 자산으로도 곡선 밖으로 나간다 — 정적 분산이 살 수 없는 것을 사는 유일한 축이 이것이다.')
    best = max(((nm, w, ALL[nm][w]['m']) for nm in cand for w in WS[1:]),
               key=lambda t: t[2]['cagr'] - float(np.interp(t[2]['vol'], xs, ys)))
    # [2026-09-04 코드리뷰] 「1/7」이 박혀 있었다 — 두 항은 실행마다 계산되는데
    # 비율만 상수라, 자료가 갱신되거나 best 가 바뀌면 같은 문장 안에서 숫자와
    # 비율이 어긋난다. 비율도 계산한다.
    bonus_best = best[2]['cagr'] - float(np.interp(best[2]['vol'], xs, ys))
    switch_gain = mb['cagr'] - ms['cagr']
    ratio = switch_gain / bonus_best if bonus_best > 0 else float('nan')
    print(f"\n  참고 — 정적 분산의 최대 보너스는 {best[0]} {best[1]*100:.0f}% 의 "
          f"**{bonus_best:+.2f}%p** 였다. 전환이 만든 {switch_gain:+.2f}%p 의 "
          + (f'1/{ratio:.0f} 이다.' if np.isfinite(ratio) else '반대 방향이다.'))

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 분산 보너스가 있어도 관문 ①을 못 넘으면 그것은 「보너스가 작다」는 뜻이다 — 크기를 보고 말할 것.')
    print('  Q-b 공격 다리에 방어자산을 상시로 섞는 것은 §1 v47(현금 20~30% 상시 · 71개 창 승률 0%)의 변형이다.')
    print('      결과가 그와 다르면 이유를 적고, 같으면 그 항목을 재확인한 것으로 끝낸다.')


if __name__ == '__main__':
    main()
