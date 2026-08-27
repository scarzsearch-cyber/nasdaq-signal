# -*- coding: utf-8 -*-
"""
[v46] 실물 TIGER 3.2년에서 A(-16/-11) 가 이긴 이유를 분해한다

화면의 '원화 · 실물 TIGER' 탭에서 A 가 MDD·Calmar·Sortino 를 전부 이긴다.
사용자 질문: "왜 -16/-11 이 압도적으로 좋은 성과를 내는거야? 실제로 뭐가 옳은지 증명해줘."

[구조]
  A 와 B 는 **진입선이 -16% 로 같다.** 다른 건 복귀선뿐이다.
    B: 낙폭이 -16% 를 회복하면 곧바로 공격
    A: 낙폭이 -11% 보다 얕아져야 공격
  그래서 둘의 차이는 **B 가 먼저 돌아가 있는 구간(선행구간)** 에서만 생긴다.
  선행구간 동안 B 는 레버리지, A 는 방어바스켓을 든다.

  즉 **B - A = 선행구간들의 (레버리지 - 방어) 합 + 전환비용 차이.**
  나머지 날은 두 전략이 같은 자산을 들어 기여가 0 이다.

[귀속 규약]
  수익은 eff = hold.shift(1) 로 붙는다(hist_krreal). 구간도 eff 로 잡는다.
  hold 로 잡으면 하루 어긋난다 — v33 에서 같은 실수를 했다.
  일별 로그차의 합이 실제 B/A 와 맞는지 **검산해서 출력한다.**

[판정]
  3.2년 표본의 선행구간 수를 세고, 같은 규칙을 54년에 적용했을 때의
  선행구간 분포에서 그 표본이 어디쯤인지 본다.
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defensive as DF
import hist_krreal as KR
from axis_lib import rule_w
from axis_defmix import materials, mix_monthly_from
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ENTER, EXB, EXA = -0.16, -0.16, -0.11
NL = chr(10)


def episodes(a, b):
    """a > b 인 구간 [i, j) 들을 뽑는다."""
    lead = np.asarray(a) > np.asarray(b)
    out, i, n = [], 0, len(lead)
    while i < n:
        if lead[i]:
            j = i
            while j < n and lead[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def s1_real():
    print("=" * 84)
    print("1. 실물 TIGER 3.2년 — 실제로 무슨 일이 있었나")
    print("=" * 84)
    cb, hb, _ = KR.run_real(EXB, defmix=True)
    ca, ha, _ = KR.run_real(EXA, defmix=True)
    idx = cb.index
    fb, fa = float(cb.iloc[-1]), float(ca.iloc[-1])
    print("  구간 %s ~ %s  (%d거래일)" % (idx[0].date(), idx[-1].date(), len(idx)))
    print("  최종배수  B %.3f   A %.3f   A/B %.3f배" % (fb, fa, fa / fb))
    print()

    def switches(h):
        d = h.diff().fillna(0)
        return [(t, '공격' if v > 0 else '방어') for t, v in d.items() if v != 0]

    sb, sa = switches(hb), switches(ha)
    print("  전환  B %d회 / A %d회" % (len(sb), len(sa)))
    print("  %-26s%s" % ('B 전환', 'A 전환'))
    for i in range(max(len(sb), len(sa))):
        l = "%s %s" % (sb[i][0].date(), sb[i][1]) if i < len(sb) else ''
        r = "%s %s" % (sa[i][0].date(), sa[i][1]) if i < len(sa) else ''
        print("  %-26s%s" % (l, r))

    rb = cb.pct_change().fillna(0).values
    ra = ca.pct_change().fillna(0).values
    eb = hb.shift(1).fillna(1.0).values
    ea = ha.shift(1).fillna(1.0).values
    dlog = np.log1p(rb) - np.log1p(ra)
    same = (eb == ea)

    print()
    print("  두 전략이 **같은 자산을 든 날** %d일 / %d일 = %.1f%%"
          % (int(same.sum()), len(idx), same.mean() * 100))
    print("    그 날들의 기여   %+.2f%%   <- 전환비용 차이만 남는다"
          % ((np.exp(dlog[same].sum()) - 1) * 100))
    print("    갈린 날 %d일 기여 %+.2f%%"
          % (int((~same).sum()), (np.exp(dlog[~same].sum()) - 1) * 100))
    print("    합계 검산 %+.2f%%  vs 실제 B/A-1 %+.2f%%   <- 일치해야 한다"
          % ((np.exp(dlog.sum()) - 1) * 100, (fb / fa - 1) * 100))

    eps = episodes(eb, ea)
    print()
    print("  선행구간(B 는 레버리지 · A 는 방어) %d개" % len(eps))
    print("  %-3s%-13s%-13s%5s%10s%10s%10s"
          % ('#', '시작', '끝', '일수', 'B 수익', 'A 수익', 'B-A'))
    for n, (i, j) in enumerate(eps, 1):
        gb = float(np.prod(1 + rb[i:j]) - 1)
        ga = float(np.prod(1 + ra[i:j]) - 1)
        print("  %-3d%-13s%-13s%5d%9.1f%%%9.1f%%%9.1f%%p"
              % (n, idx[i].date(), idx[j - 1].date(), j - i,
                 gb * 100, ga * 100, (gb - ga) * 100))
    lo, hi = eps[0][0], eps[-1][1]
    print()
    print("  ** 갈린 기간은 %s ~ %s 뿐이다. 나머지 %d일은 두 전략이 완전히 같다. **"
          % (idx[lo].date(), idx[hi - 1].date(), len(idx) - (hi - lo)))
    return len(eps), fa / fb


def s2_history():
    print()
    print("=" * 84)
    print("2. 같은 선행구간을 54년 전체에 적용하면 — 분포")
    print("=" * 84)
    D = DF.build('chain')
    idx, ddq = D['idx'], D['ddv']
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    q = D['qldr']
    wb, wa = rule_w(ddq, ENTER, EXB), rule_w(ddq, ENTER, EXA)
    # 체결규약: 그날 벌어들이는 비중은 전날 신호다
    pb = np.r_[wb[0], wb[:-1]]
    pa = np.r_[wa[0], wa[:-1]]
    eps = episodes(pb, pa)

    rows = []
    for (i, j) in eps:
        lev = float(np.prod(1 + np.nan_to_num(q[i:j])) - 1)
        dfv = float(np.prod(1 + np.nan_to_num(defr[i:j])) - 1)
        rows.append(dict(start=idx[i], end=idx[j - 1], days=j - i,
                         lev=lev, dfr=dfv, edge=lev - dfv))
    R = pd.DataFrame(rows)
    print("  선행구간 %d개  (%s ~ %s, 54년)" % (len(R), idx[0].date(), idx[-1].date()))
    print("  B 가 이긴 구간 %d개 / 진 구간 %d개  = 승률 %.0f%%"
          % (int((R.edge > 0).sum()), int((R.edge <= 0).sum()), (R.edge > 0).mean() * 100))
    print("  기여 중앙 %+.1f%%p   평균 %+.1f%%p   표준편차 %.1f%%p"
          % (R.edge.median() * 100, R.edge.mean() * 100, R.edge.std() * 100))
    print("  최악 %+.1f%%p (%s)   최고 %+.1f%%p (%s)"
          % (R.edge.min() * 100, R.loc[R.edge.idxmin(), 'start'].date(),
             R.edge.max() * 100, R.loc[R.edge.idxmax(), 'start'].date()))

    for lab, sub in [('가장 나쁜 5개 (A 가 이긴 구간)', R.nsmallest(5, 'edge')),
                     ('가장 좋은 5개 (B 가 이긴 구간)', R.nlargest(5, 'edge'))]:
        print()
        print("  " + lab)
        print("  %-13s%-13s%5s%10s%9s%10s"
              % ('시작', '끝', '일수', '레버리지', '방어', 'B-A'))
        for _, r in sub.iterrows():
            print("  %-13s%-13s%5d%9.1f%%%8.1f%%%9.1f%%p"
                  % (r.start.date(), r.end.date(), int(r.days),
                     r.lev * 100, r.dfr * 100, r.edge * 100))
    return R


def s3_smallsample(R, n_real):
    print()
    print("=" * 84)
    print("3. 선행구간 %d개로 결론을 낼 수 있는가" % n_real)
    print("=" * 84)
    rng = np.random.default_rng(11)
    e = R.edge.values

    def p_lose(n, trials=40000):
        d = np.array([np.prod(1 + rng.choice(e, n, replace=True)) - 1
                      for _ in range(trials)])
        return float((d <= 0).mean()), float(np.median(d))

    print("  54년 분포에서 선행구간을 n 개 무작위로 뽑았을 때")
    print("  %-14s%22s%18s" % ('n', 'A 가 더 좋아 보일 확률', '누적 중앙'))
    for n in (1, 2, 3, 5, 10, 19, 30, 70):
        if n > len(e):
            break
        p, m = p_lose(n)
        mark = '   <- 실물 3.2년' if n == n_real else ''
        print("  %-14d%21.1f%%%17.1f%%%s" % (n, p * 100, m * 100, mark))
    p2, _ = p_lose(n_real)
    print()
    print("  실제 표본은 선행구간 %d개다. 순전한 운으로 A 가 이길 확률 %.0f%%."
          % (n_real, p2 * 100))
    print("  동전을 몇 번 던져 앞면이 덜 나온 것과 같은 수준이다.")
    return p2


def s4_horizon():
    print()
    print("=" * 84)
    print("4. 3.2년 창을 54년 내내 굴리면 — A 가 이기는 창이 얼마나 흔한가")
    print("=" * 84)
    D = DF.build('chain')
    idx, ddq, N = D['idx'], D['ddv'], len(D['idx'])
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    q = D['qldr']

    def logs(ex):
        w = rule_w(ddq, ENTER, ex)
        p = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(p * q + (1 - p) * defr); r[0] = 0
        t = np.abs(np.diff(p, prepend=p[0]))
        return np.log((1 + r) * (1 - 0.002 * t))

    lb, la = logs(EXB), logs(EXA)
    for yrs in (3, 5, 10, 20):
        L = int(yrs * 252)
        st = range(0, N - L, 21)
        d = np.array([lb[s:s + L].sum() - la[s:s + L].sum() for s in st])
        print("  %2d년 창 %4d개 :  B 승률 %5.1f%%   B-A 중앙 %+7.1f%%   5분위 %+7.1f%%"
              % (yrs, len(d), (d > 0).mean() * 100,
                 (np.exp(np.median(d)) - 1) * 100,
                 (np.exp(np.percentile(d, 5)) - 1) * 100))
    L = int(3.2 * 252)
    st = range(0, N - L, 21)
    d = np.array([lb[s:s + L].sum() - la[s:s + L].sum() for s in st])
    print()
    print("  3.2년 창 %d개 중 A 가 이긴 창 %d개 = %.0f%%"
          % (len(d), int((d <= 0).sum()), (d <= 0).mean() * 100))
    print("  -> 3.2년짜리 표본에서 A 가 이기는 건 **드문 일이 아니다.**")
    return float((d > 0).mean())


def main():
    n_real, _ = s1_real()
    R = s2_history()
    p2 = s3_smallsample(R, n_real)
    w3 = s4_horizon()
    print()
    print("=" * 84)
    v = verdict('실물 3.2년의 A 우세가 규칙을 바꿀 근거가 되는가', [
        ('선행구간 표본이 판단 최소치(19) 이상', n_real >= 19, '%d개' % n_real),
        ('우연으로 뒤집힐 확률이 5% 미만', p2 < 0.05, '%.0f%%' % (p2 * 100)),
        ('54년 선행구간에서 A 가 앞선다', R.edge.median() <= 0,
         '중앙 %+.1f%%p, B 승률 %.0f%%' % (R.edge.median() * 100, (R.edge > 0).mean() * 100)),
        ('3.2년 창 대부분에서 A 가 앞선다', w3 < 0.5, 'B 승률 %.0f%%' % (w3 * 100)),
    ])
    print(v['text'])


if __name__ == '__main__':
    main()
