# -*- coding: utf-8 -*-
"""
[v83] B 를 같은 잣대로 검사 — 룰 감사(v82)에서 고친 두 조항을 채택안에도 적용

소유자 질문 (2026-08-29): "애매한 조항을 고친 걸로 B 도 검사가 가능한가?
B 와 T4 둘 다 검사하고 결론지어라."

적용하는 조항:
  조항① (기각의 적용 범위) — B 의 채택을 떠받치는 기각들이 **실전 맥락(원화·적립식·
    한국비용·정정 후)에서 시험됐는지** 감사한다 (§4, 문서 감사 — v83 문서에 표).
  조항② (비용 가정의 실측 검증) — 비용을 가정이 아니라 **변수**로 놓고 B 의 우위가
    몇 %까지 견디는지 잰다. T4 에 했던 사건 단위 기전 검사도 B 에 대칭으로 한다.

[★ 사전 고정 검사 기준 — 실행 전에 적었다. T-bill 규약 · lag=1 · 54.5년]
  P1 비용 내성   편도 0.1~0.3% 전부에서 B 최종 > 2배 그냥 보유 (0.4% 는 참고)
  P2 규칙 우위   편도 0.1~0.3% 전부에서 B 최종 ≥ A(−16/−11) (v43 재확인)
  P3 기전 실증   독립 도피 22사건창 MDD 에서 B > 2배 보유 승률 ≥ 70%
                (T4 의 M2 검사와 같은 잣대 — T4 vs B 는 77%였다)
  P4 사각지대   dd 가 (−16%, −8%) 에 연속 체류한 최장 구간 ≤ 252일
                (v81 발견 — 완만·얕은 하락은 B 무력. 1년 넘는 배회가 역사에
                 실재했다면 사각지대는 가설이 아니라 실적이다)
  전부 계산에서 판정문 생성 (research_kit.verdict).
"""
# --- 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
# ---------------------------------------------------------------------------
import numpy as np
import pandas as pd

from axis_lib import rule_w, sim
from research_kit import verdict
from axis_t4_shadow import build, met

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def events(D, wB):
    idx = D['idx']
    esc = np.where((wB[1:] == 0) & (wB[:-1] == 1))[0] + 1
    keep, last = [], None
    for e in esc:
        if last is None or (idx[e] - idx[last]).days > 252:
            keep.append(e)
        last = e
    return keep


def ev_mdd_wins(D, ca, cb, keep):
    wins = []
    for e in keep:
        a = max(0, e - 63); b = min(len(D['idx']) - 1, e + 252)
        sA, sB = ca.iloc[a:b], cb.iloc[a:b]
        wins.append(float((sA / sA.cummax() - 1).min()) > float((sB / sB.cummax() - 1).min()))
    return np.mean(wins), len(keep)


def main():
    D, wT, wB, votes, rv = build('tbill')
    idx = D['idx']
    wA = rule_w(D['ddv'], -0.16, -0.11)
    wH = np.ones(len(idx))
    keep = events(D, wB)

    print('=' * 100)
    print('P1·P2. 비용을 변수로 — 편도비용별 54년 최종배수 (T-bill 규약)')
    print('=' * 100)
    print('%-8s %12s %12s %12s %12s' % ('편도', '2배 보유', 'A(-16/-11)', 'B(-16/-16)', 'T4'))
    tbl = {}
    for c in (0.001, 0.002, 0.003, 0.004):
        row = {}
        for nm, w in (('hold', wH), ('A', wA), ('B', wB), ('T4', wT)):
            cv, _ = sim(D, w, cost=c)
            row[nm] = met(cv)
        tbl[c] = row
        print('%.1f%%    %12s %12s %12s %12s' %
              (c * 100, *[format(row[k]['final'], ',.0f') for k in ('hold', 'A', 'B', 'T4')]))
    print('MDD      %11.1f%% %11.1f%% %11.1f%% %11.1f%%' %
          tuple(tbl[0.001][k]['mdd'] * 100 for k in ('hold', 'A', 'B', 'T4')))
    p1 = all(tbl[c]['B']['final'] > tbl[c]['hold']['final'] for c in (0.001, 0.002, 0.003))
    p2 = all(tbl[c]['B']['final'] >= tbl[c]['A']['final'] for c in (0.001, 0.002, 0.003))

    print()
    print('=' * 100)
    print('P3. 기전 실증 — 독립 도피 22사건창 MDD 승률 (T4 검사와 같은 잣대)')
    print('=' * 100)
    cB, _ = sim(D, wB, cost=0.002)
    cH, _ = sim(D, wH, cost=0.002)
    cT, _ = sim(D, wT, cost=0.002)
    wbh, n = ev_mdd_wins(D, cB, cH, keep)
    wth, _ = ev_mdd_wins(D, cT, cH, keep)
    wtb, _ = ev_mdd_wins(D, cT, cB, keep)
    print('  B  vs 2배보유: %2.0f%% (%d사건)  |  T4 vs 2배보유: %2.0f%%  |  T4 vs B: %2.0f%%'
          % (wbh * 100, n, wth * 100, wtb * 100))
    # B 도피 왕복 구조 (T4 게이트 구조와 대칭 진단)
    off = []
    g = (wB > 0).astype(int)
    ch = np.flatnonzero(np.diff(g)) + 1
    for s in np.split(np.arange(len(g)), ch):
        if g[s[0]] == 0:
            off.append(len(s))
    print('  B 도피 구간 %d개: 중앙 %d일 · 21일 이하 %.0f%% (T4 게이트: 중앙 4~5일 · 55%%가 5일 이하)'
          % (len(off), np.median(off), np.mean([x <= 21 for x in off]) * 100))

    print()
    print('=' * 100)
    print('P4. 사각지대 실재성 — dd 가 (−16%, −8%) 에 연속 체류한 구간 (v81 발견의 실측)')
    print('=' * 100)
    zone = (D['ddv'] > -0.16) & (D['ddv'] <= -0.08)
    runs = []
    ch = np.flatnonzero(np.diff(zone.astype(int))) + 1
    for s in np.split(np.arange(len(zone)), ch):
        if zone[s[0]]:
            runs.append((len(s), s[0], s[-1]))
    runs.sort(reverse=True)
    print('  체류 총 %.0f%% 일수 · 구간 %d개 · 최장 3개:' % (zone.mean() * 100, len(runs)))
    rB = np.log(cB.values); rT = np.log(cT.values); rH = np.log(cH.values)
    for L, a, b in runs[:3]:
        per = '%s~%s' % (idx[a].date(), idx[b].date())
        gB = (rB[b] - rB[a]) * 100; gT = (rT[b] - rT[a]) * 100; gH = (rH[b] - rH[a]) * 100
        print('    %3d일  %s   구간 로그수익: B %+5.0f%% · T4 %+5.0f%% · 보유 %+5.0f%%'
              % (L, per, gB, gT, gH))
    p4_max = runs[0][0] if runs else 0

    print()
    checks = [
        ('P1 비용 내성 (B>보유, ≤0.3% 전부)', p1,
         '0.3%%에서 B {:,.0f} vs 보유 {:,.0f}'.format(tbl[0.003]['B']['final'],
                                                    tbl[0.003]['hold']['final'])),
        ('P2 규칙 우위 (B≥A, ≤0.3% 전부)', p2,
         '0.2%%에서 B {:,.0f} vs A {:,.0f}'.format(tbl[0.002]['B']['final'],
                                                  tbl[0.002]['A']['final'])),
        ('P3 기전 실증 (사건승 ≥70%)', wbh >= 0.70, 'B vs 보유 %.0f%%' % (wbh * 100)),
        ('P4 사각지대 희귀 (최장 ≤252일)', p4_max <= 252, '최장 %d일' % p4_max),
    ]
    print(verdict('B 동일 잣대 검사 (조항①·② 적용)', checks)['text'])


if __name__ == '__main__':
    main()
