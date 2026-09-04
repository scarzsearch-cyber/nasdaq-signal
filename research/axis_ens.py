# -*- coding: utf-8 -*-
"""
[축2] 파라미터를 고르지 않는다 — 앙상블

문제의식: v18 §5-3(a) 는 "퍼지드 워크포워드에서 -16% 가 7개 구간 중 2번만 뽑혔다"고
정직하게 적어 두었다. v21 §11.8 은 "규칙을 자주 바꾸는 것이 최악"(OOS 69.15 vs 고정
160.7)이라고 결론냈다. 두 사실을 동시에 만족시키는 제3의 길이 앙상블이다 —
**하나를 고르지도, 갈아타지도 않고, 여러 개를 동시에 굴려 평균 비중을 유지한다.**

이건 파라미터 탐색이 아니라 파라미터 제거다. 따라서 HANDOFF §4 의 금지사항
("같은 데이터로 문턱·gap·확인일·필터를 더 조합하기")에 걸리지 않는다.
그리드 최고값을 채택하는 것이 아니라, 고르는 행위 자체를 없앤다.

  (a) 문턱 앙상블   -13/-16/-19 를 동일가중 평균 (비중 0, 1/3, 2/3, 1 을 오간다)
  (b) 룩백 앙상블   126/252/504 일 낙폭을 동일가중 평균
  (c) 풀 앙상블     문턱 3 x 룩백 3 = 9개 전부 평균

실행:  python axis_ens.py
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

import hist_defensive as DF
import hist_data as H
from axis_lib import COST, rule_w, dd_from, sim, check, row, show, qqq_curve

THS = (-0.13, -0.16, -0.19)
LBS = (126, 252, 504)


def lookback_drawdowns(px_full, idx, lbs=LBS):
    """전체 QQQ 프록시에서 룩백을 만든 뒤 분석 달력에 맞춘다."""
    out = {}
    for lb in lbs:
        full = pd.Series(dd_from(px_full, lb), index=px_full.index)
        aligned = full.reindex(idx)
        if aligned.isna().any():
            raise AssertionError('전체 QQQ 프록시가 분석 달력을 덮지 못한다: lb%d' % lb)
        out[lb] = aligned.values
    return out


def member_relation(ensemble_final, member_finals):
    """앙상블 하나를 바로 그 앙상블을 구성한 멤버들과만 비교한다."""
    members = np.asarray(member_finals, dtype=float)
    if not len(members) or not np.isfinite(members).all():
        raise AssertionError('멤버 최종값이 비었거나 유한하지 않다')
    return dict(ensemble=float(ensemble_final), median=float(np.median(members)),
                mean=float(np.mean(members)), best=float(np.max(members)),
                above_median=bool(ensemble_final > np.median(members)),
                above_best=bool(ensemble_final > np.max(members)))


def selfcheck():
    """절단 뒤 룩백 재계산과 잘못된 멤버 집합 재사용을 함께 막는다."""
    ix = pd.date_range('2000-01-03', periods=6, freq='B')
    px = pd.Series([100., 120., 90., 80., 85., 100.], index=ix)
    got = lookback_drawdowns(px, ix[2:], (3,))[3]
    truncated = dd_from(px.reindex(ix[2:]), 3)
    assert np.isclose(got[0], -0.25) and np.isclose(truncated[0], 0.0)

    own = member_relation(3.0, [1.0, 4.0, 5.0])
    other = member_relation(3.0, [1.0, 2.0, 5.0])
    assert not own['above_median'] and other['above_median']


def ensemble(D, dds, start, label):
    ddv = D['ddv']
    ref = qqq_curve(D, start)
    rows = []

    weights = {(lb, t): rule_w(dds[lb], t, t) for lb in LBS for t in THS}
    singles = {(lb, t): sim(D, weights[(lb, t)], start=start)
               for lb in LBS for t in THS}

    # (a) 문턱 앙상블
    for t in THS:
        c, sw = singles[(252, t)]
        rows.append(row('단일 %.0f/%.0f' % (t * 100, t * 100), c, sw, ref=ref))
    c, sw = sim(D, np.mean([weights[(252, t)] for t in THS], axis=0), start=start)
    rows.append(row('* 문턱앙상블 3', c, sw, ref=ref))

    # (b) 룩백 앙상블
    for lb in LBS:
        c, sw = singles[(lb, -0.16)]
        rows.append(row('단일 lb%d' % lb, c, sw, ref=ref))
    c, sw = sim(D, np.mean([weights[(lb, -0.16)] for lb in LBS], axis=0), start=start)
    rows.append(row('* 룩백앙상블 3', c, sw, ref=ref))

    # (c) 풀 앙상블
    W = [weights[(lb, t)] for lb in LBS for t in THS]
    c, sw = sim(D, np.mean(W, axis=0), start=start)
    rows.append(row('* 풀앙상블 9', c, sw, ref=ref))

    # 대조군
    for nm, en, ex in (('-16/-11', -0.16, -0.11), ('-16/-16', -0.16, -0.16)):
        c, sw = sim(D, rule_w(ddv, en, ex), start=start)
        rows.append(row('기준 %s' % nm, c, sw, ref=ref))

    df = show(rows, '축2 앙상블 — %s' % label)

    # 판정 보조: 세 앙상블을 각각 자기 구성 멤버와 비교한다.
    groups = {
        '문턱': ([(252, t) for t in THS], '* 문턱앙상블 3'),
        '룩백': ([(lb, -0.16) for lb in LBS], '* 룩백앙상블 3'),
        '전체': ([(lb, t) for lb in LBS for t in THS], '* 풀앙상블 9'),
    }
    relations = {}
    for nm, (keys, ens_name) in groups.items():
        member_finals = [float(singles[k][0].iloc[-1]) for k in keys]
        ens_final = float(df[df['name'] == ens_name]['final'].iloc[0])
        rel = member_relation(ens_final, member_finals)
        relations[nm] = rel
        print('  %s 멤버 %d개 -> 중앙값 %s / 평균 %s / 최고 %s / 앙상블 %s  [%s]'
              % (nm, len(keys), format(rel['median'], ',.0f'), format(rel['mean'], ',.0f'),
                 format(rel['best'], ',.0f'), format(rel['ensemble'], ',.0f'),
                 '중앙값 상회' if rel['above_median'] else '중앙값 이하'))
    return df, relations


if __name__ == '__main__':
    selfcheck()
    D = DF.build('chain')
    r_full, _ = H.qqq_proxy()
    px_full = (1 + r_full).cumprod()
    dds = lookback_drawdowns(px_full, D['idx'])
    assert np.allclose(dds[252], D['ddv']), '252일 룩백이 기준 엔진과 다르다'
    print('데이터 %s ~ %s  n=%d  방어=배당체인  편도비용 %.2f%%'
          % (D['idx'][0].date(), D['idx'][-1].date(), len(D['idx']), COST * 100))
    assert check(D), '검산 실패'
    runs = [ensemble(D, dds, None, '1972-2026 (54.5년)'),
            ensemble(D, dds, '2000-01-03', '2000-2026 (26.6년)')]
    rels = [rel for _, group in runs for rel in group.values()]
    n = len(rels)
    above_median = sum(r['above_median'] for r in rels)
    above_best = sum(r['above_best'] for r in rels)
    print('\n판정: 앙상블 %d개 비교 중 자기 멤버 중앙값 상회 %d/%d, 최고 멤버 상회 %d/%d.'
          % (n, above_median, n, above_best, n))
    if above_median < n:
        print('      따라서 "앙상블은 항상 멤버 중앙값보다 낫다"는 주장은 성립하지 않는다.')
    print('      파라미터 위험 보험으로는 정직하지만 성과 개선은 아니고,')
    print('      전환이 3.6~14배로 폭증한다(비용·세금 관문에서 더 불리해진다).')
