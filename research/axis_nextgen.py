# -*- coding: utf-8 -*-
"""
[v87] B+T4 차세대 구조 탐색 — 결합 구조와 의사결정 구조 (소유자 연구 요청서, 2026-08-30)

질문: "B의 단순성 + T4의 선제 감속 + 빠른 회복 포착을 동시에 얻는 **구조**가 있는가.
  더 좋은 지표가 아니라 더 좋은 의사결정 구조를 찾아라. 없으면 없다고 결론지어라."

[룰 준수 선언]
  · 채택안(−16/−16)·freeze.json·oos_log.csv·T4 파라미터(vt40·th2·창20·룩백4) 무변경.
  · 그림자 장부는 판단에 쓰지 않는다. 입력은 기존 연구와 같은 54.5년 체인뿐이다.
  · 이미 기각된 축은 재실행하지 않고 문서를 인용한다:
      히스테리시스·확인일·최소유지일(v82 K관문 9/9 전멸) · 무거래 밴드(v80 §4 기각)
      · RV비율/변화율(v54 G1, 4블록 2/4 탈락) · RV수준 상태변수(v53 G11 탈락)
      · 복귀 최적화 단독(v41 조기복귀 기각·v59 최적복귀일=저점 포착 0 이하)
      · ¼ 양자화(v81 §3 — 집행 단순화로 이미 유효 판정).
  · 부분비중 기각(v55)의 사유는 "노출 0 불가 → 재난 무방비"였다. 여기 후보들은
    전부 **B의 0% 도피를 보존**하므로 그 기각의 적용 범위 밖이다(v82 범위 원칙).
    단 변동성 조기방어(v32/40 기각) 혈통인 후보(BVOL·RMAP)는 그 사실을 명기한다.

[다중성 선언] 같은 54.5년 표본의 **18번째 채굴**이다. 시험 변형 수 23
  (혼합 6 + 구조 4 + 격자 12 + 무손잡이 1). 표본 안 성적은 등록 자격 심사일 뿐이며
  증거는 미래 그림자 OOS 만이 준다. 통과자가 나와도 **채택이 아니라
  "그림자 등록 논의 자격"**이다 — 등록 여부·규약은 소유자 결정 사항.

[후보 — 전부 기존 신호(wB, wT, votes, rv, dd)의 재배선. 새 지표 없음]
  MIX(x)      x·wB + (1−x)·wT, x ∈ {0,.1,.25,.5,.75,1}   (v81 §4 재확인 + 고원)
  AND         wB × wT           — T4 감속 + B 재난 확인 + 복귀도 T4 확인 (요청 C=P)
  MAX         max(wB, wT)       — B 진입 + 방어 중 T4 회복 신호로 조기 복귀 (요청 M)
  BVOL        wB × min(1, 40%/RV) — 투표 게이트 없이 변동성 감속만 + B 최종방어 (요청 N)
  BGATE(v*)   wB × (votes > v*), v* ∈ {0,1} — 평소 B, 추세 만장일치 붕괴 때만 선제 하선 (요청 O)
  RMAP(d1,v1) 2차원 낙폭×RV: wB=0→0 / (dd≤d1 ∧ RV≥v1)→½ / 그외→1.
              d1 ∈ {−8,−10,−12%}, v1 ∈ {35,40,45%} 격자 9 — 중심 (−10,40) (요청 I)
  HSPEED(s)   wB × (21일수익 > s), s ∈ {−15,−20,−25%} — 낙폭 속도축 (요청 H)
  CONFMIX     conf=|votes−2|/2 → conf·wT + (1−conf)·wB — 신호 확신도 혼합 (요청 §28)
  ※ 상태머신(요청 K)은 AND 와 동형이라 별도 구현하지 않는다: 정상(둘 다 ON)=T4크기,
    경계(RV↑)=T4크기↓, 재난(B=0)=0, 회복(B복귀+T4확인)=T4크기 — 정확히 wB×wT.

[★ 등록 관문 N1~N8 — 실행 전 고정. 기준: 54.5년 · T-bill 방어 · lag=1 · 편도 0.2%]
  N1 방어 개선   MDD ≥ B(0.2%) MDD + 3%p
  N2 보험료 한도 최종 ≥ 0.90 × B(0.2%)   (평상시 기회비용 ≤ 10% — 요청 Q의 보험료 관점)
  N3 사건 반복   독립 도피 22사건창 MDD 승률 vs B ≥ 60%
  N4 시대 불변   전반(1972–99)·후반(2000–26) 사건들 각각에서 사건승 ≥ 50%
  N5 회전 한도   연회전 ≤ 5.0 (B 2.6 의 약 2배 — "손 안 대는 시스템" 유지선)
  N6 고원        격자 후보는 모든 이웃 셀에서 N1∧N2 유지 (한 점 첨탑 무효)
  N7 반쪽 경제성 두 반쪽 각각 최종 ≥ 0.85 × 같은 반쪽 B
  N8 지연 강건   lag=2 에서 MDD ≥ B(lag=2) MDD + 2%p
  전부 충족 → 그림자 등록 논의 자격. 복수면 Calmar(0.2%) 최대 1개 (사전 타이브레이크).
  MIX25 보다 Calmar 낮은 통과자는 "혼합 하위호환"으로 표기한다.

[사전 예측 — 실행 전에 적는다 (v81 방식: 틀리면 틀렸다고 기록)]
  P-a AND 는 MDD 최량이나 노출 손실로 N2 탈락.
  P-b MAX 는 곰랠리를 얻어맞아 MDD 가 B 보다 못하다 (N1 탈락).
  P-c BVOL 이 가장 유망 — 게이트 왕복 없이 급락형만 깎는다. 단 1999형 고변동
      상승장 끌림으로 N2 가 아슬아슬할 것.
  P-d HSPEED 는 2020 V자 재진입 지연으로 이득 상쇄.
  P-e 혼합 고원(x=.1~.5)은 v81 대로 재확인될 것.

[진단 (관문 없음 — 측정만)]
  ① T4 분해: 추세게이트만 / 변동성타깃만 / 결합 (요청 V — 알파의 출처)
  ② 신호 괴리: B·T4 가 갈린 날의 앞 63일 수익 분포 (요청 R)
  ③ 최소 후회: 5년 창들에서 max(B,T4) 대비 최악 열세 (요청 §27)
  ④ 사건 채점: 사건승·M1 사전감속·회복 포착(저점 후 126일 평균 노출 − B) (요청 §33)
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

import hist_data as H
from axis_lib import sim
from research_kit import dist, fmt_dist, verdict
from axis_t4_shadow import build, met, VT, TH

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

KCOST = 0.002            # 관문 기준 (0.1% 는 참고 병기)
HALF = '2000-01-01'
V81 = dict(b1=170800, t1=163161, mix1=185582, b2=148455, t2=109451)   # 재현 검산 기준


# ==================================================================== 후보
def make_candidates(wB, wT, votes, rv, ddv, px):
    v = votes.fillna(4).values
    rvv = rv.values
    wv = np.clip(VT / rvv, None, 1.0)
    wv = np.where(np.isnan(wv), 1.0, wv)
    r21 = (px / px.shift(21) - 1).values

    C = {}
    for x in (0.0, 0.10, 0.25, 0.50, 0.75, 1.0):
        C['MIX(%.2f)' % x] = x * wB + (1 - x) * wT
    C['AND'] = wB * wT
    C['MAX'] = np.maximum(wB, wT)
    C['BVOL'] = wB * wv
    for vs in (0, 1):
        C['BGATE(>%d)' % vs] = wB * (v > vs).astype(float)
    for d1 in (-0.08, -0.10, -0.12):
        for v1 in (0.35, 0.40, 0.45):
            mid = (ddv <= d1) & (rvv >= v1)
            C['RMAP(%d,%d)' % (d1 * 100, v1 * 100)] = wB * np.where(mid, 0.5, 1.0)
    for s in (-0.15, -0.20, -0.25):
        ok = np.where(np.isnan(r21), True, r21 > s)
        C['HSPEED(%d)' % (s * 100)] = wB * ok.astype(float)
    conf = np.abs(v - TH) / 2.0
    C['CONFMIX'] = conf * wT + (1 - conf) * wB
    return C


# ==================================================================== 사건
def indep_events(D, wB):
    idx = D['idx']
    esc = np.where((wB[1:] == 0) & (wB[:-1] == 1))[0] + 1
    keep, last = [], None
    for e in esc:
        if last is None or (idx[e] - idx[last]).days > 252:
            keep.append(e)
        last = e
    return keep


def event_stats(D, w, curve, cB, wBv, keep, px):
    """사건승(창 MDD vs B) · 전/후반 사건승 · M1 사전감속 · 회복 포착."""
    idx = D['idx']
    n = len(idx)
    wins, m1, rec = [], [], []
    for e in keep:
        a = max(0, e - 63); b = min(n - 1, e + 252)
        sT = curve.iloc[a:b]; sB = cB.iloc[a:b]
        wins.append(float((sT / sT.cummax() - 1).min()) > float((sB / sB.cummax() - 1).min()))
        m1.append(w[max(0, e - 10):e].mean() < 0.7)
        t = a + int(np.argmin(px.values[a:b]))          # 사건창 저점
        c2 = min(n, t + 126)
        rec.append(w[t:c2].mean() - wBv[t:c2].mean())   # 저점 후 126일 평균 노출 − B
    wins = np.array(wins); yrs = np.array([idx[e].year for e in keep])
    early = yrs < 2000
    return dict(win=wins.mean(),
                win_a=wins[early].mean() if early.any() else np.nan,
                win_b=wins[~early].mean() if (~early).any() else np.nan,
                m1=np.mean(m1), rec=np.mean(rec))


# ==================================================================== main
def main():
    D, wT, wB, votes, rv = build('tbill')
    idx = D['idx']; n = len(idx); yrs = (idx[-1] - idx[0]).days / 365.25
    r_full, _ = H.qqq_proxy()
    px = (1 + r_full).cumprod().reindex(idx)
    ddv = D['ddv']
    keep = indep_events(D, wB)

    # --- 0. 재현 검산 (v81/v83 공표수치, ±1.5%) --------------------------------
    print('=' * 112)
    print('0. 재현 검산 — v81/v83 공표수치 (T-bill · lag=1)')
    print('=' * 112)
    cB1, _ = sim(D, wB, cost=0.001); cT1, _ = sim(D, wT, cost=0.001)
    cM1, _ = sim(D, 0.25 * wB + 0.75 * wT, cost=0.001)
    cB2, _ = sim(D, wB, cost=KCOST);  cT2, _ = sim(D, wT, cost=KCOST)
    pairs = [('B 0.1%', cB1, V81['b1']), ('T4 0.1%', cT1, V81['t1']),
             ('MIX25 0.1%', cM1, V81['mix1']), ('B 0.2%', cB2, V81['b2']),
             ('T4 0.2%', cT2, V81['t2'])]
    ok_rep = True
    for nm, c, ref in pairs:
        f = float(c.iloc[-1]); err = f / ref - 1
        ok_rep &= abs(err) <= 0.015
        print('  %-12s %10s  (v81/83 %s, 오차 %+.2f%%)' % (nm, format(f, ',.0f'), format(ref, ','), err * 100))
    if not ok_rep:
        raise SystemExit('재현 실패 — 엔진/데이터가 v81 과 다르다. 여기서 중단.')

    mB2 = met(cB2)
    cB2l, _ = sim(D, wB, cost=KCOST, lag=2); mB2l = met(cB2l)
    hB1 = float(sim(D, wB, cost=KCOST, end=HALF)[0].iloc[-1])
    hB2 = float(sim(D, wB, cost=KCOST, start=HALF)[0].iloc[-1])
    mM2 = met(sim(D, 0.25 * wB + 0.75 * wT, cost=KCOST)[0])

    # --- 1. 본 표 ---------------------------------------------------------------
    print()
    print('=' * 112)
    print('1. 후보 23종 — 편도 0.2%% (참고 0.1%%) · 사건 %d회 · 관문 N1~N8' % len(keep))
    print('=' * 112)
    print('%-14s %10s %7s %7s %6s %5s %6s %6s %7s %9s %10s %6s' %
          ('후보', '최종0.2%', 'MDD', 'Calmar', '회전yr', '사건승', '전/후', 'M1',
           '회복Δw', '최종0.1%', '반쪽72/00', 'N관문'))
    wBv = wB
    rows = {}
    for nm, w in make_candidates(wB, wT, votes, rv, ddv, px).items():
        c, _ = sim(D, w, cost=KCOST)
        m = met(c)
        turn = np.abs(np.diff(w, prepend=w[0])).sum() / yrs
        ev = event_stats(D, w, c, cB2, wBv, keep, px)
        c1, _ = sim(D, w, cost=0.001); f1 = float(c1.iloc[-1])
        cl, _ = sim(D, w, cost=KCOST, lag=2); ml = met(cl)
        h1 = float(sim(D, w, cost=KCOST, end=HALF)[0].iloc[-1])
        h2 = float(sim(D, w, cost=KCOST, start=HALF)[0].iloc[-1])
        ks = dict(
            N1=m['mdd'] >= mB2['mdd'] + 0.03,
            N2=m['final'] >= 0.90 * mB2['final'],
            N3=ev['win'] >= 0.60,
            N4=(np.isnan(ev['win_a']) or ev['win_a'] >= 0.50)
               and (np.isnan(ev['win_b']) or ev['win_b'] >= 0.50),
            N5=turn <= 5.0,
            N7=h1 >= 0.85 * hB1 and h2 >= 0.85 * hB2,
            N8=ml['mdd'] >= mB2l['mdd'] + 0.02)
        rows[nm] = dict(m=m, turn=turn, ev=ev, ks=ks, f1=f1, h=(h1, h2))
        print('%-14s %10s %6.1f%% %7.3f %6.1f %4.0f%% %3.0f/%.0f %5.0f%% %+6.2f %9s %5.2f/%4.2f %6s' %
              (nm, format(m['final'], ',.0f'), m['mdd'] * 100, m['calmar'], turn,
               ev['win'] * 100, ev['win_a'] * 100, ev['win_b'] * 100, ev['m1'] * 100,
               ev['rec'], format(f1, ',.0f'), h1 / hB1, h2 / hB2,
               ''.join('O' if ks[k] else 'X' for k in ('N1', 'N2', 'N3', 'N4', 'N5', 'N7', 'N8'))))

    # --- 2. N6 고원 + 종합 판정 -------------------------------------------------
    fam = {}
    grid = [(d1, v1) for d1 in (-8, -10, -12) for v1 in (35, 40, 45)]
    for d1, v1 in grid:
        nb = ['RMAP(%d,%d)' % (d2, v2) for d2, v2 in grid
              if (abs(d2 - d1) == 2) != (abs(v2 - v1) == 5)
              and abs(d2 - d1) <= 2 and abs(v2 - v1) <= 5]
        fam['RMAP(%d,%d)' % (d1, v1)] = nb
    fam['HSPEED(-15)'] = ['HSPEED(-20)']
    fam['HSPEED(-20)'] = ['HSPEED(-15)', 'HSPEED(-25)']
    fam['HSPEED(-25)'] = ['HSPEED(-20)']
    fam['BGATE(>0)'] = ['BGATE(>1)']
    fam['BGATE(>1)'] = ['BGATE(>0)']
    for x, nbs in (('0.10', ('0.00', '0.25')), ('0.25', ('0.10', '0.50')),
                   ('0.50', ('0.25', '0.75')), ('0.75', ('0.50', '1.00'))):
        fam['MIX(%s)' % x] = ['MIX(%s)' % q for q in nbs]

    passers = []
    for nm, r in rows.items():
        if nm in ('MIX(0.00)', 'MIX(1.00)'):
            continue
        if not all(r['ks'].values()):
            continue
        nbs = fam.get(nm, [])
        n6 = all(rows[q]['ks']['N1'] and rows[q]['ks']['N2'] for q in nbs) if nbs else True
        r['ks']['N6'] = n6
        if n6:
            passers.append(nm)
    print()
    print('=' * 112)
    if passers:
        best = max(passers, key=lambda q: rows[q]['m']['calmar'])
        sub = '혼합 하위호환' if rows[best]['m']['calmar'] < mM2['calmar'] else 'MIX25 도 넘음'
        checks = [(k, bool(v), '') for k, v in rows[best]['ks'].items()]
        print(verdict('N1~N8 통과 — 그림자 등록 논의 자격: %s (%s)' % (best, sub), checks)['text'])
        others = [p for p in passers if p != best]
        if others:
            print('   그 외 통과(타이브레이크 탈락): %s' % ', '.join(others))
    else:
        print('[판정] 전멸 — N1~N8 을 전부 충족한 신규 구조 없음')
    for nm, r in rows.items():
        if nm in ('MIX(0.00)', 'MIX(1.00)') or all(r['ks'].values()):
            continue
        print('   %-14s 미달: %s' % (nm, ','.join(k for k, v in r['ks'].items() if not v)))

    # --- 3. 진단 ① T4 분해 -------------------------------------------------------
    print()
    print('=' * 112)
    print('3. 진단 — T4 알파의 출처 (분해 · 0.2%/0.1%)')
    print('=' * 112)
    v = votes.fillna(4).values
    rvv = rv.values
    wv = np.where(np.isnan(np.clip(VT / rvv, None, 1.0)), 1.0, np.clip(VT / rvv, None, 1.0))
    for nm, w in (('추세게이트만', (v >= TH).astype(float)),
                  ('변동성타깃만', wv), ('T4(결합)', wT)):
        c2, _ = sim(D, w, cost=KCOST); c1, _ = sim(D, w, cost=0.001)
        m = met(c2)
        ev = event_stats(D, w, c2, cB2, wBv, keep, px)
        print('  %-8s 0.2%%: %10s  MDD %6.1f%%  Calmar %.3f · 사건승 %3.0f%% · 0.1%%: %s'
              % (nm, format(m['final'], ',.0f'), m['mdd'] * 100, m['calmar'],
                 ev['win'] * 100, format(float(c1.iloc[-1]), ',.0f')))

    # --- 4. 진단 ② 신호 괴리 -----------------------------------------------------
    print()
    print('4. 진단 — B·T4 가 갈린 날의 앞 63일 시장수익 (연장 체인)')
    fwd = (px.shift(-63) / px - 1).values
    conds = [('전체', np.ones(n, bool)),
             ('B=공격 & T4<0.3 (T4만 경고)', (wB == 1) & (wT < 0.3)),
             ('B=방어 & T4>0.7 (T4만 복귀)', (wB == 0) & (wT > 0.7)),
             ('일치 (둘 다 공격적)', (wB == 1) & (wT > 0.7))]
    for nm, msk in conds:
        s = fwd[msk & ~np.isnan(fwd)]
        if len(s) < 20:
            print('  %-28s n=%d (표본 부족)' % (nm, len(s)))
            continue
        print('  %-28s n=%5d  %s' % (nm, len(s), fmt_dist(dist(s, nm), pct=True)))

    # --- 5. 진단 ③ 최소 후회 (5년 창, max(B,T4) 대비) -----------------------------
    print()
    print('5. 진단 — 최소 후회: 5년 창에서 max(B,T4) 대비 열세 (0.2%)')
    L = 1260
    starts = np.arange(1, n - L, 21)
    def wfin(curve):
        lg = np.log(curve.values)
        return np.exp(lg[starts + L - 1] - lg[starts - 1])
    fB, fT = wfin(cB2), wfin(cT2)
    best = np.maximum(fB, fT)
    for nm in ('MIX(0.00)', 'MIX(0.25)', 'MIX(0.50)', 'MIX(1.00)', 'AND', 'MAX', 'BVOL', 'CONFMIX'):
        w = make_candidates(wB, wT, votes, rv, ddv, px)[nm]
        c, _ = sim(D, w, cost=KCOST)
        reg = wfin(c) / best - 1
        lab = {'MIX(0.00)': 'T4 단독', 'MIX(1.00)': 'B 단독'}.get(nm, nm)
        print('  %-10s 최악 %6.1f%% · P5 %6.1f%% · 중앙 %+5.1f%% (창 %d개)'
              % (lab, np.min(reg) * 100, np.percentile(reg, 5) * 100,
                 np.median(reg) * 100, len(reg)))


if __name__ == '__main__':
    main()
