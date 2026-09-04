# -*- coding: utf-8 -*-
"""
[v43] B(-16/-16) 확정 + 보조전략 탐색 — v21 이 A 를 권한 근거를 다시 잰다

v21 은 -16/-11(A) 을 권했다. 근거 두 개가 **틀렸다**:

  오류① 상대 변화율을 절대 순위로 착각
        v21 자기 표에서 마찰을 다 물린 뒤에도 B 1,241.8 > A 1,078.3 이었는데,
        "B 가 2~3배 더 깎인다"를 "A 가 낫다"로 읽었다.
  오류② 표준편차를 평균비용과 직접 비교
        "갭 표준편차 2.58% 는 비용 0.1% 의 26배" — 단위가 다르다.
        방향 없는 분산의 실제 비용은 sigma^2/2 = 0.033%/회. 0.1% 의 1/3 이다.

여기서 프로젝트 자체 엔진(hist_korea.run_kr, 한국 거래일 + 슬리피지)으로 다시 잰다.
재구현하지 않는다 — v30 에서 엔진을 새로 짜다 체결규약을 어긴 전례가 있다.

[검사]
  1  슬리피지 스윕 — A 가 이기려면 얼마나 커야 하나
  2  갭 분산 몬테카를로 — v21 이 실측한 2.58% 를 전환마다 물린다
  3  보조전략 후보 — B 와 얼마나 다른가(상태일치·상관), B 부진창을 메우나
  4  -11/-11 시대별 분해 — B 부진창에서 좋아 보인 후보가 시대 전용인지
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_defasset as DA
import hist_defensive as DF
import hist_korea as K
import hist_krfinal as KF
from hyst_core import A as SA, B as SB
from axis_lib import rule_w, COST
from axis_defmix import materials, mix_monthly_from, UST_FEE
from research_kit import verdict

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

GAP_SD = 0.0258        # v21 §4.4 실측: 레버리지 시초가 갭 표준편차


def krw_setup():
    D, ki, lev2, _, dfk, fr = KF.build_krw('chain')
    kc = {'div': np.asarray(dfk, dtype=float),
          'ust5': (1 + DA.ust_tr(ki, 5, 'TNX', futures=True, fee=UST_FEE)) * (1 + fr) - 1,
          'gold': (1 + DA.gold_r(ki)) * (1 + fr) - 1}
    sr = mix_monthly_from(kc, {'div': .4, 'ust5': .4, 'gold': .2}, ki)
    Dx = dict(D); Dx['qldr'] = lev2; Dx['schdr'] = sr
    return Dx, ki, K.kr_caldays()


def run_kr(Dx, krd, S, slip):
    c, w, t = K.run_kr(Dx, S, cost=0.001, slip=slip, start=KF.ST, krdays=krd)
    # 신호 변화가 아니라 한국 거래일 매핑 뒤 실제 체결을 센다. 휴장 사이에
    # 신호가 왕복하면 한 번도 체결되지 않을 수 있다.
    n = int(np.count_nonzero(np.asarray(t, dtype=float)))
    return float(c.iloc[-1]), n, c


def flip_text(flip, tested_max=0.03):
    return ('편도 %.1f%%' % (flip * 100) if flip is not None
            else '편도 %.1f%%까지 역전 없음' % (tested_max * 100))


def flip_is_implausible(flip):
    return flip is None or flip >= 0.005


def s1_slip(Dx, krd):
    print("=" * 78)
    print("1. 슬리피지 스윕 — A 가 이기려면 얼마나 커야 하나")
    print("=" * 78)
    print(f"  {'편도 슬리피지':<16}{'B -16/-16':>13}{'A -16/-11':>13}{'B/A':>9}")
    flip = None
    for s in (0.000, 0.001, 0.002, 0.003, 0.005, 0.010, 0.015, 0.020, 0.030):
        vb, tb, _ = run_kr(Dx, krd, SB, s)
        va, ta, _ = run_kr(Dx, krd, SA, s)
        mk = ''
        if va > vb:
            mk = ' <- A 우세'
            if flip is None:
                flip = s
        print(f"  {s*100:>9.1f}%{'':<6}{vb:>13,.1f}{va:>13,.1f}{vb/va:>9.2f}{mk}")
    vb, tb, _ = run_kr(Dx, krd, SB, 0.001)
    va, ta, _ = run_kr(Dx, krd, SA, 0.001)
    print(f"\n  전환 B {tb}회 / A {ta}회")
    print(f"  실제 가정(0.1%)에서 B/A = {vb/va:.2f}")
    extra = (' (실제 가정의 %.0f배)' % (flip / 0.001)) if flip is not None else ''
    print(f"  역전 지점 = {flip_text(flip)}{extra}")
    return vb, va, tb, ta, flip


def s2_gap(cb, ca, tb, ta, n=2000):
    print("\n" + "=" * 78)
    print("2. 갭 분산 몬테카를로 — v21 이 실측한 2.58% 를 전환마다 물린다")
    print("=" * 78)
    print("  v21: '표준편차 2.58% 는 비용 0.1% 의 26배' -> 단위가 다르다.")
    print("       방향 없는 분산의 실제 비용은 sigma^2/2 다.")
    rng = np.random.default_rng(7)
    rb = np.array([cb * np.prod(1 + rng.normal(0, GAP_SD, tb)) for _ in range(n)])
    ra = np.array([ca * np.prod(1 + rng.normal(0, GAP_SD, ta)) for _ in range(n)])
    print(f"\n  {'':<6}{'중앙':>11}{'5분위':>11}{'95분위':>11}")
    print(f"  {'B':<6}{np.median(rb):>11,.0f}{np.percentile(rb,5):>11,.0f}{np.percentile(rb,95):>11,.0f}")
    print(f"  {'A':<6}{np.median(ra):>11,.0f}{np.percentile(ra,5):>11,.0f}{np.percentile(ra,95):>11,.0f}")
    print(f"\n  B 가 A 를 이긴 비율 {(rb>ra).mean()*100:.1f}%")
    print(f"  갭 전 B/A {cb/ca:.2f}  ->  갭 후 중앙 B/A {np.median(rb)/np.median(ra):.2f}")
    db = 1 - np.median(rb) / cb; da = 1 - np.median(ra) / ca
    print(f"  변동성 손실  B {db*100:.1f}%  A {da*100:.1f}%  차이 {(db-da)*100:.1f}%p")
    print(f"  이론값 sigma^2/2 x 전환수: B {GAP_SD**2/2*tb*100:.1f}%  A {GAP_SD**2/2*ta*100:.1f}%")
    return float((rb > ra).mean()), float(np.median(rb) / np.median(ra))


def s3_secondary():
    print("\n" + "=" * 78)
    print("3. 보조전략 후보 — B 와 얼마나 다른가")
    print("=" * 78)
    D = DF.build('chain'); idx = D['idx']; ddq = D['ddv']; N = len(idx)
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    q = D['qldr']

    def mk(e, x):
        w = rule_w(ddq, e, x); pos = np.r_[w[0], w[:-1]]
        r = np.nan_to_num(pos * q + (1 - pos) * defr); r[0] = 0
        return w, np.log((1 + r) * (1 - COST * np.abs(np.diff(pos, prepend=pos[0]))))

    Bw, Bl = mk(-0.16, -0.16)
    L = 20 * 252; st = list(range(0, N - L, 63))
    rB = np.array([np.exp(Bl[s:s + L].sum()) for s in st])
    bad = np.argsort(rB)[:len(st) // 4]
    CAND = {'A -16/-11 (참조)': (-0.16, -0.11), '-19/-18': (-0.19, -0.18),
            '-16/-15': (-0.16, -0.15), '-23/-7': (-0.23, -0.07),
            '-11/-11': (-0.11, -0.11), '-12/-6': (-0.12, -0.06)}
    print(f"  {'후보':<22}{'상태일치':>9}{'수익상관':>9}{'B부진창서':>11}{'전체승률':>9}")
    rec = [i for i in range(len(st)) if idx[st[i]].year >= 2000]
    stats = {}
    for nm, (e, x) in CAND.items():
        w, l = mk(e, x)
        r = np.array([np.exp(l[s:s + L].sum()) for s in st])
        # 같은 날짜의 일간 로그수익 상관. 겹치는 20년 말기배수의 차분은
        # 동시점 수익이 아니며 0.9 관문을 위로 왜곡했다.
        cor = float(np.corrcoef(Bl, l)[0, 1])
        recent_win = float((r[rec] > rB[rec]).mean())
        stats[nm] = dict(corr=cor, recent_win=recent_win)
        print(f"  {nm:<22}{(w==Bw).mean()*100:>8.0f}%{cor:>9.2f}"
              f"{np.median(r[bad]/rB[bad]-1)*100:>10.0f}%{(r>rB).mean()*100:>8.0f}%")
    low = [(nm, d) for nm, d in stats.items() if d['corr'] < 0.9]
    print("\n  -> 일간 수익상관 0.90 미만 후보: %s"
          % (', '.join('%s %.3f' % (nm, d['corr']) for nm, d in low) if low else '없음'))
    print("     -16/-15 는 상태일치 99%, 상관 1.00 — 사실상 같은 전략이다.")

    print("\n" + "=" * 78)
    print("4. -11/-11 시대별 분해 — B 부진창의 우위가 시대 전용인가")
    print("=" * 78)
    _, Cl = mk(-0.11, -0.11)
    print(f"  {'구간':<12}{'-11/-11':>12}{'B':>12}{'차이':>10}")
    for nm, a, b in [('1972-85', '1972-01-01', '1985-12-31'),
                     ('1986-99', '1986-01-01', '1999-12-31'),
                     ('2000-13', '2000-01-01', '2013-12-31'),
                     ('2014-26', '2014-01-01', '2026-12-31')]:
        lo = int(idx.searchsorted(pd.Timestamp(a))); hi = int(idx.searchsorted(pd.Timestamp(b), side='right'))
        v1 = np.exp(Cl[lo:hi].sum()); v0 = np.exp(Bl[lo:hi].sum())
        print(f"  {nm:<12}{v1:>12,.1f}{v0:>12,.1f}{(v1/v0-1)*100:>9.0f}%")
    rC = np.array([np.exp(Cl[s:s + L].sum()) for s in st])
    yrs = np.array([idx[st[i]].year for i in bad])
    print(f"\n  'B 부진창' {len(bad)}개 중 1970년대 시작 {(yrs<1980).sum()}개")
    print(f"  2000년 이후 시작 창 {len(rec)}개에서 -11/-11 승리 {(rC[rec]>rB[rec]).sum()}개"
          f"  (중앙 {np.median(rC[rec]/rB[rec]-1)*100:+.0f}%)")
    return stats


def main():
    Dx, ki, krd = krw_setup()
    vb, va, tb, ta, flip = s1_slip(Dx, krd)
    winrate, ratio = s2_gap(vb, va, tb, ta)
    stats = s3_secondary()
    low = [(nm, d) for nm, d in stats.items() if d['corr'] < 0.9]
    viable = [(nm, d) for nm, d in low if d['recent_win'] > 0.3]
    print("\n" + "=" * 78)
    v = verdict('메인 규칙 B(-16/-16)', [
        ('마찰 반영 후에도 A 를 앞선다', vb > va, f'{vb:,.0f} vs {va:,.0f} ({vb/va:.2f}배)'),
        ('갭 분산 반영 후에도 앞선다', ratio > 1.0, f'{ratio:.2f}배, 승률 {winrate*100:.0f}%'),
        ('역전에 필요한 슬리피지가 비현실적', flip_is_implausible(flip), flip_text(flip)),
    ])
    print(v['text'])
    print()
    v2 = verdict('보조전략 채택', [
        ('B 와 상관 0.9 미만인 후보가 있다', bool(low),
         ', '.join('%s %.3f' % (nm, d['corr']) for nm, d in low) if low else '없음'),
        ('그 저상관 후보가 최근 구간에서도 쓸 만하다', bool(viable),
         ', '.join('%s 승률 %.0f%%' % (nm, d['recent_win'] * 100) for nm, d in low)
         if low else '대상 없음'),
    ])
    print(v2['text'])


if __name__ == '__main__':
    assert flip_text(None).endswith('역전 없음')
    assert flip_text(0.0).startswith('편도 0.0%') and not flip_is_implausible(0.0)
    main()
