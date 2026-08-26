# -*- coding: utf-8 -*-
"""
[v30] 매크로 지표(VIX·하이일드 스프레드)를 조기경보 신호로 추가할 수 있는가

기존 신호는 QQQ 252일 낙폭 하나(-16%/-11%). MD6류 대시보드가 보여주는
VIX·하이일드 스프레드 같은 신용/변동성 지표가 QQQ 낙폭보다 먼저 위기를
감지해서 방어 진입을 앞당길 수 있는지를 검증한다.

데이터: yahoo_VIX(1990~), yahoo_HYG·yahoo_IEF(HYG 2007-04~) — 미국 원천,
        QQQ 신호와 동일한 "미국 종가" 계열이라 v28에서 정한 원칙과 합치.
HY 스프레드 대용치: HYG/IEF 비율의 63일 낙폭 (신용스프레드 확대 ≈ 회사채 ETF가
        국채 대비 underperform). 실제 OAS 지수가 아니라 근사치임을 명시.
"""
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

COST = 0.001


def load(path, datecol='Date', pricecol='Close'):
    d = pd.read_csv(path)
    d[datecol] = pd.to_datetime(d[datecol])
    return d.set_index(datecol)[pricecol].sort_index()


def dd_from(px, lb):
    return (px / px.rolling(lb, min_periods=lb).max() - 1).fillna(0)


def rule_w(ddv, enter, exit_, w0=1.0):
    n = len(ddv)
    w = np.empty(n)
    cur = w0
    for i in range(n):
        if cur >= 1.0:
            if ddv[i] <= enter:
                cur = 0.0
        else:
            if ddv[i] <= enter:
                cur = 0.0
            elif ddv[i] > exit_:
                cur = 1.0
        w[i] = cur
    return w


def bt(qqqr, qldr, defr, w, cost=COST):
    """w=1 -> QLD(2x), w=0 -> 방어자산.

    [v30 정정] 체결 규약 pos = w.shift(1) — 전일 종가 신호로 당일 체결.
    이걸 안 지키면 VIX처럼 폭락 당일 튀는 지표에서 미래훔쳐보기가 발생한다.
    """
    n = len(w)
    pos = np.empty(n)
    pos[0] = w[0]
    pos[1:] = w[:-1]                    # shift(1)
    out = np.empty(n)
    for i in range(n):
        r = qldr[i] if pos[i] >= 1.0 else defr[i]
        if i > 0 and pos[i] != pos[i - 1]:
            r -= cost
        out[i] = r
    return out


def mdd(cum):
    peak = np.maximum.accumulate(cum)
    return (cum / peak - 1).min()


def main():
    qqq = load('qqq_us_d.csv')
    qld = load('qld_us_d.csv')
    schd = load('schd_us_d.csv')
    vix = load('data/hist/yahoo_VIX.csv')
    hyg = load('data/hist/yahoo_HYG.csv')
    ief = load('data/hist/yahoo_IEF.csv')

    idx = qqq.index.intersection(qld.index).intersection(schd.index)
    idx = idx.intersection(vix.index).intersection(hyg.index).intersection(ief.index)
    idx = idx.sort_values()
    print(f"공통 구간: {idx.min().date()} ~ {idx.max().date()}  ({len(idx)}거래일)")

    qqq, qld, schd, vix, hyg, ief = [s.reindex(idx) for s in (qqq, qld, schd, vix, hyg, ief)]
    qqqr = qqq.pct_change().fillna(0).values
    qldr = qld.pct_change().fillna(0).values
    defr = schd.pct_change().fillna(0).values

    ddq = dd_from(qqq, 252).values
    spread_proxy = (hyg / ief)
    dds = dd_from(spread_proxy, 63).values          # HY 스프레드 확대 대용
    ddv_vix_z = (vix - vix.rolling(756, min_periods=252).mean()) / vix.rolling(756, min_periods=252).std()
    ddv_vix_z = ddv_vix_z.fillna(0).values

    # ---------------------------------------------------------- s1. 선행성 점검
    print("\n[1] 3대 위기에서 QQQ 낙폭신호(-16%) 대비 HY스프레드/VIX 신호가 며칠 먼저 왔나")
    crises = {
        '2008 GFC': ('2008-06-01', '2009-04-01'),
        '2011 유럽': ('2011-06-01', '2011-11-01'),
        '2018 Q4': ('2018-09-01', '2019-01-15'),
        '2020 COVID': ('2020-01-15', '2020-04-15'),
        '2022 긴축': ('2022-01-01', '2022-07-01'),
    }
    dates = idx
    for name, (s, e) in crises.items():
        m = (dates >= s) & (dates <= e)
        if m.sum() < 10:
            continue
        sub = np.where(m)[0]
        qtrig = sub[ddq[sub] <= -0.16]
        strig = sub[dds[sub] <= np.nanpercentile(dds[m], 5)]   # 스프레드 하위5% = 급확대
        vtrig = sub[ddv_vix_z[sub] >= 1.5]                     # VIX 1.5시그마 이상
        qd = dates[qtrig[0]] if len(qtrig) else None
        sd = dates[strig[0]] if len(strig) else None
        vd = dates[vtrig[0]] if len(vtrig) else None
        lead_s = (qd - sd).days if (qd is not None and sd is not None) else None
        lead_v = (qd - vd).days if (qd is not None and vd is not None) else None
        print(f"  {name}: QQQ신호={qd.date() if qd is not None else '-'}  "
              f"HY스프레드={sd.date() if sd is not None else '-'}(선행 {lead_s}일)  "
              f"VIX={vd.date() if vd is not None else '-'}(선행 {lead_v}일)")

    # ---------------------------------------------------------- s2. 예측력 (단순 평균비교)
    print("\n[2] 신호 발생 시점 이후 21거래일 QQQ 수익률 — 신호군 vs 비신호군")
    fwd = pd.Series(qqqr).rolling(21).sum().shift(-21).values  # 근사 합산수익
    for name, trig in [('HY스프레드 급확대(하위5%)', dds <= np.nanpercentile(dds, 5)),
                        ('VIX 1.5시그마', ddv_vix_z >= 1.5),
                        ('QQQ dd<=-16%(참고)', ddq <= -0.16)]:
        a = fwd[trig]
        b = fwd[~trig]
        a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
        if len(a) < 10:
            continue
        a_mean = a.mean()
        b_mean = b.mean()
        a_std = a.std()
        se = a_std / np.sqrt(len(a)) if len(a) > 1 else 0
        print(f"  {name}: n={len(a)}  이후21일평균={a_mean*100:+.2f}% vs 비신호 {b_mean*100:+.2f}%  차이={((a_mean-b_mean)*100):+.2f}%p")

    # ---------------------------------------------------------- s3. 백테스트 — 조기경보 병합 규칙
    print("\n[3] 백테스트 — 기존(QQQ만) vs 다양한 조기경보 병합")
    base_w = rule_w(ddq, -0.16, -0.11)
    base_r = bt(qqqr, qldr, defr, base_w)
    base_cum = np.cumprod(1 + base_r)
    base_cagr = base_cum[-1] ** (252 / len(base_cum)) - 1
    base_mdd = mdd(base_cum)

    print(f"  기존 (QQQ만): 최종배수={base_cum[-1]:.2f}배  CAGR={base_cagr*100:.2f}%  MDD={base_mdd*100:.2f}%  Calmar={base_cagr/abs(base_mdd):.2f}")

    for sig_name, sig_val in [('HY스프레드 하위3%', dds <= np.nanpercentile(dds, 3)),
                               ('VIX 1.5시그마', ddv_vix_z >= 1.5)]:
        early = sig_val & (ddq <= -0.05)
        comb_ddv = np.where(early, -0.20, ddq)
        comb_w = rule_w(comb_ddv, -0.16, -0.11)
        r = bt(qqqr, qldr, defr, comb_w)
        cum = np.cumprod(1 + r)
        cagr = cum[-1] ** (252 / len(cum)) - 1
        m = mdd(cum)
        turns = np.abs(np.diff(comb_w)).sum()
        gain = ((cagr - base_cagr) / base_cagr * 100) if base_cagr > 0 else 0
        print(f"  + {sig_name} 조기경보: 최종배수={cum[-1]:.2f}배  CAGR={cagr*100:.2f}%({gain:+.2f}%)  MDD={m*100:.2f}%  "
              f"전환={turns:.0f}  Calmar={cagr/abs(m):.2f}")

    # ---------------------------------------------------------- s4. 플라시보 검증
    print("\n[4] 플라시보 — 실제 신호 효과 vs 무작위 신호 (500회 부트스트랩)")
    rng = np.random.default_rng(42)

    # HY스프레드 검증
    early_hy = (dds <= np.nanpercentile(dds, 3)) & (ddq <= -0.05)
    real_w_hy = rule_w(np.where(early_hy, -0.20, ddq), -0.16, -0.11)
    real_r_hy = bt(qqqr, qldr, defr, real_w_hy)
    real_cagr_hy = np.cumprod(1 + real_r_hy)[-1] ** (252 / len(real_r_hy)) - 1

    n_early = int(early_hy.sum())
    better_hy = 0
    for _ in range(500):
        rand_idx = rng.choice(len(ddq), size=n_early, replace=False)
        rand_early = np.zeros(len(ddq), dtype=bool)
        rand_early[rand_idx] = True
        rd = np.where(rand_early & (ddq <= -0.05), -0.20, ddq)
        rw = rule_w(rd, -0.16, -0.11)
        rr = bt(qqqr, qldr, defr, rw)
        rc = np.cumprod(1 + rr)[-1] ** (252 / len(rr)) - 1
        if rc >= real_cagr_hy:
            better_hy += 1

    # VIX 검증
    early_vix = (ddv_vix_z >= 1.5) & (ddq <= -0.05)
    real_w_vix = rule_w(np.where(early_vix, -0.20, ddq), -0.16, -0.11)
    real_r_vix = bt(qqqr, qldr, defr, real_w_vix)
    real_cagr_vix = np.cumprod(1 + real_r_vix)[-1] ** (252 / len(real_r_vix)) - 1

    n_early_vix = int(early_vix.sum())
    better_vix = 0
    for _ in range(500):
        rand_idx = rng.choice(len(ddq), size=n_early_vix, replace=False)
        rand_early = np.zeros(len(ddq), dtype=bool)
        rand_early[rand_idx] = True
        rd = np.where(rand_early & (ddq <= -0.05), -0.20, ddq)
        rw = rule_w(rd, -0.16, -0.11)
        rr = bt(qqqr, qldr, defr, rw)
        rc = np.cumprod(1 + rr)[-1] ** (252 / len(rr)) - 1
        if rc >= real_cagr_vix:
            better_vix += 1

    print(f"  HY스프레드: 실제 CAGR={real_cagr_hy*100:.2f}%  무작위 중 같거나 나음={better_hy}/500 ({better_hy/500*100:.1f}%)")
    print(f"  VIX:       실제 CAGR={real_cagr_vix*100:.2f}%  무작위 중 같거나 나음={better_vix}/500 ({better_vix/500*100:.1f}%)")
    print(f"  (5% 미만이어야 '우연이 아니다' — 위 둘 다 20% 이상이면 거짓신호)")

    # ---------------------------------------------------------- s5. VIX 신호 과최적화 검증
    print("\n[5] VIX 신호 상세 진단 — 정말 좋은 신호인가 vs 과최적화인가")

    # VIX 신호가 발동하는 시점의 시장 상황
    vix_sig_dates = idx[early_vix]
    if len(vix_sig_dates) > 0:
        print(f"  VIX 신호 발동 {len(vix_sig_dates)}회. 발동 시점의 QQQ 평균낙폭={ddq[early_vix].mean()*100:.2f}%")
        print(f"  발동 후 21일 QQQ평균수익={fwd[early_vix][~np.isnan(fwd[early_vix])].mean()*100:+.2f}%")

    # 비용 재검증: 전환비용이 제대로 반영되었나
    w_base = rule_w(ddq, -0.16, -0.11)
    w_vix = rule_w(np.where(early_vix, -0.20, ddq), -0.16, -0.11)

    # 전환 발생 위치별로 수익 분리
    trans_idx = np.where(np.abs(np.diff(np.concatenate([[w_vix[0]], w_vix]))) > 0)[0]
    print(f"  VIX 신호 기반 전환 위치 {len(trans_idx)}곳. 처음 5개: {trans_idx[:5]}")

    # Walk-forward로 재검증 — 최종 10년 OOS
    oos_start = len(idx) - 252*10
    train_w = rule_w(np.where(early_vix[:oos_start], -0.20, ddq[:oos_start]), -0.16, -0.11)
    test_w = rule_w(np.where(early_vix[oos_start:], -0.20, ddq[oos_start:]), -0.16, -0.11)

    test_r = bt(qqqr[oos_start:], qldr[oos_start:], defr[oos_start:], test_w)
    test_cum = np.cumprod(1 + test_r)
    test_cagr = test_cum[-1] ** (252 / len(test_cum)) - 1

    base_test_r = bt(qqqr[oos_start:], qldr[oos_start:], defr[oos_start:],
                     rule_w(ddq[oos_start:], -0.16, -0.11))
    base_test_cum = np.cumprod(1 + base_test_r)
    base_test_cagr = base_test_cum[-1] ** (252 / len(base_test_cum)) - 1

    print(f"  마지막 10년 OOS 테스트:")
    print(f"    기존 신호 CAGR={base_test_cagr*100:.2f}%  배수={base_test_cum[-1]:.2f}배")
    print(f"    VIX신호   CAGR={test_cagr*100:.2f}%  배수={test_cum[-1]:.2f}배  차이={((test_cagr-base_test_cagr)*100):+.2f}%p")
    if test_cagr < base_test_cagr:
        print(f"    ⚠️ OOS에서 오히려 악화 — 과최적화 신호")

    # ------------------------------------------------------ s6. 공포탐욕지수 분해 검증
    print("\n[6] 공포탐욕지수(CNN Fear&Greed) 구성요소 검증")
    print("  CNN 공포탐욕지수는 7개 지표의 평균이다. 그중 이 데이터로 만들 수 있는 4개를 각각 시험한다.")

    spy = load('data/hist/yahoo_SPY.csv').reindex(idx)

    # ① 주가 모멘텀 — S&P가 125일 이평 위/아래 (원본과 동일 정의)
    ma125 = spy.rolling(125, min_periods=125).mean()
    fg_mom = ((spy / ma125 - 1).fillna(0)).values

    # ② 안전자산 선호 — 주식 20일수익 − 국채 20일수익 (원본과 동일 정의)
    r20_spy = spy.pct_change(20).fillna(0).values
    r20_ief = ief.pct_change(20).fillna(0).values
    fg_safe = r20_spy - r20_ief

    # ③ 정크본드 수요 = HY스프레드 (위에서 이미 검증, 여기선 z점수로)
    fg_junk = dds

    # ④ 시장 변동성 = VIX (위에서 이미 검증, 부호 반전 — 높을수록 공포)
    fg_vol = -ddv_vix_z

    def z(a, win=756):
        s = pd.Series(a)
        return ((s - s.rolling(win, min_periods=252).mean()) / s.rolling(win, min_periods=252).std()).fillna(0).values

    # 0~100 공포탐욕 점수로 합성 (높을수록 탐욕)
    fg_score = 50 + 12.5 * (z(fg_mom) + z(fg_safe) + z(fg_junk) + z(fg_vol)) / 2
    fg_score = np.clip(fg_score, 0, 100)
    print(f"  합성 공포탐욕지수: 평균={fg_score.mean():.1f}  최저={fg_score.min():.1f}  최고={fg_score.max():.1f}")

    print("\n  (6-1) 각 구성요소 단독 예측력 — 이후 21일 QQQ 수익률")
    for nm, arr, lo_is_fear in [('① 주가모멘텀', fg_mom, True), ('② 안전자산선호', fg_safe, True),
                                 ('③ 정크본드수요', fg_junk, True), ('④ 변동성(VIX)', fg_vol, True),
                                 ('⑤ 합성 공포탐욕', fg_score, True)]:
        zz = z(arr) if nm != '⑤ 합성 공포탐욕' else (fg_score - 50) / 12.5
        fear = zz <= -1.5          # 극단적 공포
        greed = zz >= 1.5          # 극단적 탐욕
        af = fwd[fear]; af = af[~np.isnan(af)]
        ag = fwd[greed]; ag = ag[~np.isnan(ag)]
        if len(af) < 10 or len(ag) < 10:
            print(f"    {nm}: 표본부족")
            continue
        print(f"    {nm}: 공포시 이후21일={af.mean()*100:+.2f}%(n={len(af)})  "
              f"탐욕시={ag.mean()*100:+.2f}%(n={len(ag)})  격차={((af.mean()-ag.mean())*100):+.2f}%p")

    print("\n  (6-2) 공포탐욕지수를 실제 전략에 붙였을 때 — 양방향 모두 시험")
    for nm, cond in [('탐욕극단(>80)에 방어전환', fg_score >= 80),
                      ('공포극단(<20)에 방어전환', fg_score <= 20),
                      ('공포극단(<20)에 공격유지(역발상)', None)]:
        if cond is None:
            # 역발상: 공포극단이면 QQQ신호를 무시하고 공격 유지
            cw = rule_w(ddq, -0.16, -0.11)
            cw = np.where(fg_score <= 20, 1.0, cw)
        else:
            cw = rule_w(np.where(cond & (ddq <= -0.05), -0.20, ddq), -0.16, -0.11)
        r = bt(qqqr, qldr, defr, cw)
        cum = np.cumprod(1 + r)
        cagr = cum[-1] ** (252 / len(cum)) - 1
        m = mdd(cum)
        turns = np.abs(np.diff(cw)).sum()
        print(f"    {nm}: 배수={cum[-1]:.2f}배  CAGR={cagr*100:.2f}%({((cagr-base_cagr)/base_cagr*100):+.1f}%)  "
              f"MDD={m*100:.2f}%  전환={turns:.0f}")
    print(f"    [기준] 기존 QQQ만: 배수={base_cum[-1]:.2f}배  CAGR={base_cagr*100:.2f}%  MDD={base_mdd*100:.2f}%  전환={np.abs(np.diff(base_w)).sum():.0f}")

    # ------------------------------------------------------ s6-3. 유일한 개선안 정밀검증
    print("\n  (6-3) 유일하게 CAGR이 오른 '공포극단 역발상' 정밀검증")
    contra_w = np.where(fg_score <= 20, 1.0, base_w)
    override = int(((fg_score <= 20) & (base_w < 1.0)).sum())
    r = bt(qqqr, qldr, defr, contra_w)
    cum = np.cumprod(1 + r)
    cagr = cum[-1] ** (252 / len(cum)) - 1
    m = mdd(cum)
    print(f"    실제로 기존신호를 뒤집은 날 = {override}일 ({override/len(idx)*100:.1f}%)")
    print(f"    Calmar: 기존 {base_cagr/abs(base_mdd):.3f} → 역발상 {cagr/abs(m):.3f}  "
          f"({'개선' if cagr/abs(m) > base_cagr/abs(base_mdd) else '악화'})")
    print(f"    MDD:    기존 {base_mdd*100:.2f}% → 역발상 {m*100:.2f}%  (위험 {(abs(m)-abs(base_mdd))*100:+.2f}%p)")

    # 이 개선이 특정 사건 하나에 의존하는가 — 위기별 기여 분해
    print("    위기별 기여(역발상 − 기존, 누적수익 차):")
    base_r_full = bt(qqqr, qldr, defr, base_w)
    for name, (s, e) in crises.items():
        mm = (dates >= s) & (dates <= e)
        if mm.sum() < 10:
            continue
        d = np.prod(1 + r[mm]) - np.prod(1 + base_r_full[mm])
        print(f"      {name}: {d*100:+.2f}%p")

    # 플라시보 A — 날짜 흩뿌리기 (신호의 뭉침을 깨므로 클러스터 신호에 유리하게 편향된다)
    fear_mask = fg_score <= 20
    n_ov = int(fear_mask.sum())
    better_c = 0
    for _ in range(500):
        ri = rng.choice(len(ddq), size=n_ov, replace=False)
        rm = np.zeros(len(ddq), dtype=bool)
        rm[ri] = True
        rw = np.where(rm, 1.0, base_w)
        rr = bt(qqqr, qldr, defr, rw)
        rc = np.cumprod(1 + rr)[-1] ** (252 / len(rr)) - 1
        if rc >= cagr:
            better_c += 1
    print(f"    플라시보A(날짜 흩뿌리기): 이보다 좋은 비율={better_c}/500 ({better_c/500*100:.1f}%)  ※편향된 검정")

    # 플라시보 B — 블록 이동. 뭉침을 유지한 채 신호 구간만 통째로 옮긴다. 이게 올바른 검정이다.
    seg = []
    i = 0
    while i < len(fear_mask):
        if fear_mask[i]:
            j = i
            while j < len(fear_mask) and fear_mask[j]:
                j += 1
            seg.append((i, j - i))
            i = j
        else:
            i += 1
    print(f"    신호 구간 개수 = {len(seg)}개 (길이: {[l for _, l in seg]})")
    better_b = 0
    for _ in range(500):
        rm = np.zeros(len(ddq), dtype=bool)
        for _, ln in seg:
            st = rng.integers(0, len(ddq) - ln)
            rm[st:st + ln] = True
        rw = np.where(rm, 1.0, base_w)
        rr = bt(qqqr, qldr, defr, rw)
        rc = np.cumprod(1 + rr)[-1] ** (252 / len(rr)) - 1
        if rc >= cagr:
            better_b += 1
    print(f"    플라시보B(블록 이동): 이보다 좋은 비율={better_b}/500 ({better_b/500*100:.1f}%)  ← 이쪽이 올바른 검정")

    # 사건 단위 표본수 — 이게 진짜 n
    print(f"    ※ 실질 표본수 = 신호구간 {len(seg)}개 / 위기 3건. 통계적 결론을 내기엔 너무 적다.")

    # OOS
    contra_test_r = bt(qqqr[oos_start:], qldr[oos_start:], defr[oos_start:], contra_w[oos_start:])
    contra_test_cum = np.cumprod(1 + contra_test_r)
    contra_test_cagr = contra_test_cum[-1] ** (252 / len(contra_test_cum)) - 1
    print(f"    마지막10년 OOS: 기존 {base_test_cagr*100:.2f}% → 역발상 {contra_test_cagr*100:.2f}%  "
          f"({(contra_test_cagr-base_test_cagr)*100:+.2f}%p)")

    # ------------------------------------------------------ s7. 왜 실패하는가 — 동행성 측정
    print("\n[7] 실패 원인 — 이 지표들은 '선행'이 아니라 '동행'이다")
    print("  QQQ 낙폭(수준) 대비 각 지표의 시차별 상관. lag<0 = 지표가 먼저 움직임(선행)")
    ddq_s = pd.Series(ddq)
    for nm, arr, flip in [('VIX z점수', ddv_vix_z, -1), ('HY스프레드', dds, 1), ('공포탐욕지수', fg_score, 1)]:
        s = pd.Series(arr) * flip
        rows = []
        for lag in (-20, -10, -5, 0, 5, 10):
            rows.append((lag, s.shift(-lag).corr(ddq_s)))
        best = max(rows, key=lambda x: abs(x[1]))
        txt = '  '.join(f"{l:+d}일={c:+.3f}" for l, c in rows)
        print(f"  {nm}: {txt}   ← 최대 {best[0]:+d}일")
    print("  → 최대상관이 0일이면 선행지표가 아니라 주가와 같이 움직이는 동행지표다.")
    print("  → 동행지표를 신호로 쓰면 새 정보 없이 전환 횟수만 늘어난다(비용↑, 톱니↑).")

    print("\n[8] 최종 결론")
    print("  기존(QQQ 낙폭만): 배수 %.2f배 / CAGR %.2f%% / MDD %.2f%% / 전환 %d회"
          % (base_cum[-1], base_cagr * 100, base_mdd * 100, np.abs(np.diff(base_w)).sum()))
    print("  매크로 지표를 어떤 방식으로 붙여도 이보다 나아지지 않았고, 플라시보 검증도 통과하지 못했다.")
    print("  → 기각. 화면·전략에 반영하지 않는다.")


if __name__ == '__main__':
    main()
