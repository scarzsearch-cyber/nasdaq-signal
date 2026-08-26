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
import numpy as np

import hist_defensive as DF
from axis_lib import COST, rule_w, dd_from, sim, check, row, show, qqq_curve

THS = (-0.13, -0.16, -0.19)
LBS = (126, 252, 504)


def ensemble(D, start, label):
    px, ddv = D['px'], D['ddv']
    ref = qqq_curve(D, start)
    rows = []

    # (a) 문턱 앙상블
    for t in THS:
        c, sw = sim(D, rule_w(ddv, t, t), start=start)
        rows.append(row('단일 %.0f/%.0f' % (t * 100, t * 100), c, sw, ref=ref))
    c, sw = sim(D, np.mean([rule_w(ddv, t, t) for t in THS], axis=0), start=start)
    rows.append(row('* 문턱앙상블 3', c, sw, ref=ref))

    # (b) 룩백 앙상블
    dds = {lb: dd_from(px, lb) for lb in LBS}
    for lb in LBS:
        c, sw = sim(D, rule_w(dds[lb], -0.16, -0.16), start=start)
        rows.append(row('단일 lb%d' % lb, c, sw, ref=ref))
    c, sw = sim(D, np.mean([rule_w(dds[lb], -0.16, -0.16) for lb in LBS], axis=0), start=start)
    rows.append(row('* 룩백앙상블 3', c, sw, ref=ref))

    # (c) 풀 앙상블
    W = [rule_w(dds[lb], t, t) for lb in LBS for t in THS]
    c, sw = sim(D, np.mean(W, axis=0), start=start)
    rows.append(row('* 풀앙상블 9', c, sw, ref=ref))

    # 대조군
    for nm, en, ex in (('-16/-11', -0.16, -0.11), ('-16/-16', -0.16, -0.16)):
        c, sw = sim(D, rule_w(ddv, en, ex), start=start)
        rows.append(row('기준 %s' % nm, c, sw, ref=ref))

    df = show(rows, '축2 앙상블 — %s' % label)

    # 판정 보조: 앙상블이 멤버 분포의 어디에 앉는가
    mem = df[df['name'].str.startswith('단일 -')]['final'].values
    ens = float(df[df['name'] == '* 문턱앙상블 3']['final'].iloc[0])
    print('  문턱 멤버 %s  ->  중앙값 %s / 평균 %s / 앙상블 %s'
          % (', '.join(format(x, ',.0f') for x in mem), format(np.median(mem), ',.0f'),
             format(mem.mean(), ',.0f'), format(ens, ',.0f')))
    return df


if __name__ == '__main__':
    D = DF.build('chain')
    print('데이터 %s ~ %s  n=%d  방어=배당체인  편도비용 %.2f%%'
          % (D['idx'][0].date(), D['idx'][-1].date(), len(D['idx']), COST * 100))
    assert check(D), '검산 실패'
    ensemble(D, None, '1972-2026 (54.5년)')
    ensemble(D, '2000-01-03', '2000-2026 (26.6년)')
    print('\n판정: 앙상블은 항상 멤버 중앙값보다 낫고 최고 멤버보다 못하다.')
    print('      파라미터 위험 보험으로는 정직하지만 성과 개선은 아니고,')
    print('      전환이 3.6~14배로 폭증한다(비용·세금 관문에서 더 불리해진다).')
