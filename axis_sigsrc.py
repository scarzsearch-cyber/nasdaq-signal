# -*- coding: utf-8 -*-
"""
[v28 축6] 신호를 어느 종가로 잴 것인가 — 미국 원본 vs 국내 추종 ETF

사용자 질문 (2026-08-27):
  "한국 추종 ETF 종가로 잡는 게 맞을지 미국으로 보는 게 맞을지 모르겠어. QQQ, SCHD 두 종목.
   TIGER 미국채10년선물이나 ACE KRX금현물은 괴리가 있으니 그 ETF를 기준으로 잡잖아?
   두 개는 미국, 두 개는 한국으로 하는 게 맞는 걸까?"

[먼저 정리해야 할 것 — '두 개 vs 두 개'가 아니다]
  이 전략에 **신호원은 하나뿐이다**: QQQ 미국 종가의 252일 낙폭.
  · SCHD 는 신호가 아니다. deploy/update_signal.py 는 QQQ 만 받는다.
    코드 안의 'SCHD' 는 v18 때 방어자산이 SCHD 였던 시절의 **상태 이름**일 뿐이고,
    화면에는 '방어'로 표시된다(signal.html stateLabel).
  · 국채·금에도 신호가 없다. v27 에서 방어자산을 신호로 고르는 것을 기각했다.
    국내 ETF 는 **체결 자산**이지 **신호원**이 아니다.
  따라서 남는 진짜 질문은 하나다 — **QQQ 낙폭을 미국 종가로 잴까, 국내 ETF 종가로 잴까.**

[신호원 4종]
  A  미국 QQQ 종가            (현행)
  B  QQQ x 환율 (원화환산)     환율 오염만 분리
  C  국내 실물 133690 종가     환율 + 시차 + 추적오차 전부 (2010-10~)
  D  미국 QQQ 종가 1일 지연     시차만 분리

[체결은 4종 모두 동일] 원화 · 한국 거래일 · 슬리피지 0.1% · 방어 40/40/20.
  신호원만 갈아끼운다. 그래야 차이가 신호원 탓임을 말할 수 있다.

실행:  python axis_sigsrc.py
"""
import numpy as np
import pandas as pd

import hist_data as H
import hist_defasset as DA
import hist_defensive as DF
import hist_korea as K
import hist_krfinal as KF
from axis_lib import dd_from, rule_w
from reentry_lib import met

CRISES = [('닷컴 00-02', '2000-03-10'), ('GFC 07-09', '2007-10-31'),
          ('2011 유럽', '2011-07-07'), ('2015 차이나', '2015-08-10'),
          ('2018 4Q', '2018-10-01'), ('코로나 20', '2020-02-19'),
          ('2022 베어', '2022-01-03')]


def sources(D):
    """신호원 4종의 252일 낙폭 배열. 전부 D['idx'] 격자."""
    idx = D['idx']
    px = D['px']
    fxs = K.fx(idx)
    out = {}
    out['A 미국 QQQ 종가'] = dd_from(px, 252)
    out['B QQQ x 환율'] = dd_from(px * fxs, 252)
    kr = DA.kr('133690')                       # TIGER 미국나스닥100 (1배, 원화)
    kr = kr.reindex(idx.union(kr.index)).ffill().reindex(idx)
    krv = np.array(dd_from(kr, 252), dtype=float)
    krv[idx < kr.first_valid_index() + pd.Timedelta(days=400)] = np.nan
    out['C 국내 133690 종가'] = krv
    out['D 미국 종가 1일지연'] = dd_from(px.shift(1), 252)
    return out, kr.first_valid_index()


# ---------------------------------------------------------------- 1) 낙폭 자체
def s1_gap(D, S):
    idx = D['idx']
    a = S['A 미국 QQQ 종가']
    print('===== 1) 같은 날 낙폭이 얼마나 다른가 (A 대비, %p) =====')
    print('%-20s %8s %9s %9s %9s %9s'
          % ('신호원', 'n', '평균', '표준편차', 'QQQ최악5%일 평균', '최대'))
    worst = np.argsort(np.nan_to_num(D['px'].pct_change().values))[:int(len(idx) * 0.05)]
    for nm, v in S.items():
        if nm.startswith('A'):
            continue
        d = (v - a) * 100
        ok = ~np.isnan(d)
        w = worst[ok[worst]]
        print('%-20s %8d %8.2f %9.2f %17.2f %9.2f'
              % (nm, ok.sum(), np.nanmean(d), np.nanstd(d), np.nanmean(d[w]), np.nanmax(d)))
    print('  ※ 양수 = 그 신호원이 낙폭을 **얕게** 본다 = 도피가 늦어진다는 뜻이다.')
    print('    특히 "QQQ최악5%일" 열을 봐라 — 도피 판정이 실제로 걸리는 날들이다.')


# ---------------------------------------------------------------- 2) 상태 불일치
def s2_disagree(D, S, enter=-0.16, exit_=-0.16):
    idx = D['idx']
    print()
    print('===== 2) 상태 불일치 — 며칠이나 다른 판정을 하는가 (규칙 B -16/-16) =====')
    W = {nm: rule_w(np.nan_to_num(v, nan=0.0), enter, exit_) for nm, v in S.items()}
    valid = {nm: ~np.isnan(v) for nm, v in S.items()}
    base = W['A 미국 QQQ 종가']
    print('%-20s %8s %10s %10s %8s' % ('신호원', '유효일', '불일치일', '불일치비율', '전환횟수'))
    for nm, w in W.items():
        ok = valid[nm]
        dis = (w[ok] != base[ok]).sum()
        print('%-20s %8d %10d %9.2f%% %8d'
              % (nm, ok.sum(), dis, 100.0 * dis / ok.sum(),
                 int(np.abs(np.diff(w[ok])).sum())))
    return W, valid


# ---------------------------------------------------------------- 3) 위기별 시점
def s3_timing(D, S, W, valid):
    idx = D['idx']
    print()
    print('===== 3) 위기별 도피 시점 — 국내 종가로 재면 며칠 늦는가 =====')
    print('%-14s %-12s %-12s %-12s %-12s  %s'
          % ('위기', 'A 미국', 'B 원화환산', 'C 국내ETF', 'D 1일지연', '늦은 일수(B/C/D)'))
    for nm, dt in CRISES:
        t0 = idx.searchsorted(pd.Timestamp(dt))
        cells, firsts = [], {}
        for k in S:
            w = W[k]
            ok = valid[k]
            j = None
            for i in range(t0, min(t0 + 800, len(idx))):
                if ok[i] and w[i] == 0:
                    j = i
                    break
            firsts[k] = j
            cells.append('—' if j is None else str(idx[j].date()))
        ja = firsts['A 미국 QQQ 종가']
        lags = []
        for k in ('B QQQ x 환율', 'C 국내 133690 종가', 'D 미국 종가 1일지연'):
            jk = firsts[k]
            lags.append('—' if (jk is None or ja is None) else '%+d' % (jk - ja))
        print('%-14s %-12s %-12s %-12s %-12s  %s'
              % (nm, cells[0], cells[1], cells[2], cells[3], ' / '.join(lags)))
    print('  ※ 거래일 기준 차이다. 양수 = 그만큼 늦게 도피했다.')


# ---------------------------------------------------------------- 4) 성과
def s4_perf(D, S, krstart):
    """체결은 전부 동일(원화·한국 거래일·슬리피지 0.1%). 신호원만 바꾼다."""
    idx = D['idx']
    Dk, _, lev2, lev1, dfk, fr = KF.build_krw('chain')
    parts = {'div': dfk,
             'ust5': (1 + DA.ust_tr(idx, 5, 'TNX')) * (1 + fr) - 1,
             'gold': (1 + DA.gold_r(idx)) * (1 + fr) - 1}
    mix = DA.mix_monthly_parts(idx, DA.MIX_V23, parts)
    krd = K.kr_caldays()
    from hyst_core import A as RA, B as RB
    print()
    print('===== 4) 성과 — 체결 조건 동일, 신호원만 교체 =====')
    for st, lab in ((KF.ST, '원화 1997- (A/B/D 만, C 는 상장 전)'),
                    (str((krstart + pd.Timedelta(days=400)).date()), '원화 %s- (C 포함 공통창)'
                     % str((krstart + pd.Timedelta(days=400)).date()))):
        print()
        print('  [%s]' % lab)
        print('  %-20s %-11s %12s %8s %9s %8s %6s'
              % ('신호원', '규칙', '최종배수', 'CAGR', 'MDD', 'Calmar', '전환'))
        for nm, v in S.items():
            if nm.startswith('C') and lab.startswith('원화 1997'):
                continue
            Dx = dict(D)
            Dx['ddv'] = np.nan_to_num(v, nan=0.0)
            Dx['qldr'] = lev2
            Dx['schdr'] = mix
            for R in (RB, RA):
                c, w, t = K.run_kr(Dx, R, cost=0.001, slip=0.001, start=st, krdays=krd)
                m = met(c)
                print('  %-20s %-11s %12s %7.2f%% %8.2f%% %8.2f %6d'
                      % (nm if R is RB else '', R['name'], format(m['final'], ',.1f'),
                         m['cagr'] * 100, m['mdd'] * 100, m['calmar'],
                         int(np.abs(np.diff(w.values)).sum())))
    print('  ※ 공통창은 133690 상장 + 252일 룩백 확보 이후다. 짧아서 판정용이 아니라')
    print('    "국내 종가로 재면 실제로 어떻게 달라지는가"의 확인용이다.')


# ---------------------------------------------------------------- 5) 판정
def s5_verdict():
    print()
    print('===== 5) 판정 =====')
    print()
    print('  [질문 정리] "두 개는 미국, 두 개는 한국"이 아니다. **신호원은 하나뿐이다.**')
    print('   · SCHD 는 신호가 아니라 방어 상태의 옛 이름이다(update_signal.py 는 QQQ 만 받는다).')
    print('   · 국채·금에도 신호가 없다 — v27 에서 방어자산 선택을 기각했다. 그냥 사서 든다.')
    print('   · 국내 ETF 는 **체결 자산**이고, 미국 QQQ 는 **신호원**이다. 층이 다르다.')
    print()
    print('  [답] 신호는 **미국 QQQ 종가**로 잰다. 이유 넷.')
    print('   ① 환율 오염 — 국내 ETF 가격에는 환율이 섞여 있다. 위기에 원화가 약세면')
    print('      원화 기준 낙폭이 **얕게** 보여 도피가 늦어진다. 정확히 최악의 방향이다.')
    print('   ② 시차 — 한국장은 15:30 KST 마감이라 미국 시세를 하루 늦게 반영한다.')
    print('      국내 종가로 재면 판정이 하루 밀리고, 그 하루가 폭락일이다.')
    print('   ③ 이력 — 133690 은 2010-10 상장, 418660 은 2022-02 다. 252일 낙폭을 재려면')
    print('      최소 1년, 문턱을 검증하려면 수십 년이 필요하다. 국내 종가로는 불가능하다.')
    print('   ④ 괴리는 신호가 아니라 **체결가**의 문제다. 괴리가 있어도 판정은 안 흔들린다.')
    print()
    print('  [그럼 국채·금의 괴리는?] 그건 신호와 무관하다. 살 때 얼마에 사느냐의 문제고,')
    print('  v25 에서 실측했다(실측 NAV 대비 괴리는 이론가 잔차 상한보다 한 자릿수 작다).')
    print('  방어자산은 낙폭 판정을 받지 않으므로 기준가 자체가 필요 없다.')
    print()
    print('  [변경 없음] deploy/update_signal.py 는 QQQ 미국 종가만 받는다. 그대로 둔다.')


if __name__ == '__main__':
    D = DF.build('chain')
    S, krstart = sources(D)
    print('신호원 4종 · 격자 %s ~ %s (%d 거래일)'
          % (D['idx'][0].date(), D['idx'][-1].date(), len(D['idx'])))
    print('133690 상장 %s -> 252일 낙폭 유효 %s~'
          % (krstart.date(), (krstart + pd.Timedelta(days=400)).date()))
    print()
    s1_gap(D, S)
    W, valid = s2_disagree(D, S)
    s3_timing(D, S, W, valid)
    s4_perf(D, S, krstart)
    s5_verdict()
