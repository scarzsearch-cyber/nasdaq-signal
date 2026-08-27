# -*- coding: utf-8 -*-
"""
[v38] 연구 도구 — 틀린 방법을 **어렵게** 만든다

2026-08-27 에 검증 설계 오류 5건이 났다. README §5 는 그걸 "사람이 봐야 함"으로
분류했는데, 다시 보니 **4.5건은 API 를 바꾸면 막힌다.**
린터로 사후 탐지하는 게 아니라, **올바른 것만 쉽게** 만드는 방식이다.

| 실제로 났던 오류 | 여기서 어떻게 막는가 |
|---|---|
| 격자 단면만 보고 '첨탑' 오판 (v31) | `sweep()` 이 전 차원을 강제하고 **경계 최적점을 거부**한다 |
| 수익 기준 워크포워드로 잡음 선택 (v31) | `walkforward()` 가 지표를 필수 인자로 받고 **고정 대조군을 병기**한다 |
| 적립 MDD 를 초기 잔고까지 세서 -70% (v32) | `mdd()` 가 적립 경로면 `since=` 없이는 **거부**한다 |
| 분포에서 한 숫자만 뽑아 인용 (v32) | `dist()` 가 중앙·5분위·최악을 **항상 함께** 준다 |
| 계산과 무관한 판정문 인쇄 (v27/v30) | `verdict()` 가 계산값에서만 문장을 만든다 |

사용법은 각 함수 독스트링에. 새 분석은 이걸 쓰고, 직접 짜지 마라.
`python research_kit.py` 로 자기검사를 돌린다(CI 가 부른다).
"""
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


class DesignError(Exception):
    """분석 설계가 틀렸을 때. 결과를 내기 전에 멈춘다."""


# ==================================================================== 분포
def dist(vals, name=''):
    """분포를 **통째로** 반환한다. 한 숫자만 뽑아 쓰는 걸 막는다.

    v32 에서 중앙값 대신 최악 창 값을 인용해 -69~75% 라고 보고했다.
    실제 중앙값은 -51.6% 였다. 그래서 여기서는 셋을 항상 같이 준다.

    >>> d = dist([1, 2, 3, 10, 20]); d['median'], d['p5'], d['worst']
    """
    a = np.asarray([v for v in np.asarray(vals, dtype=float).ravel() if np.isfinite(v)])
    if len(a) < 3:
        raise DesignError(f'{name}: 표본 {len(a)}개로는 분포를 말할 수 없다')
    return dict(name=name, n=len(a), median=float(np.median(a)),
                p5=float(np.percentile(a, 5)), p10=float(np.percentile(a, 10)),
                worst=float(a.min()), best=float(a.max()), mean=float(a.mean()))


def fmt_dist(d, pct=False, w=9):
    u = '%' if pct else ''
    m = 100 if pct else 1
    return (f"n={d['n']:<4} 중앙 {d['median']*m:{w}.2f}{u}  "
            f"5분위 {d['p5']*m:{w}.2f}{u}  최악 {d['worst']*m:{w}.2f}{u}")


# ==================================================================== MDD
def mdd(curve, since=None, kind='lump'):
    """최대낙폭. **적립 경로면 `since` 를 강제**한다.

    kind='lump'  거치식 — 첫 값이 이미 전액이다. 그대로 잰다.
    kind='accum' 적립식 — 잔고가 0 에서 시작한다. 초기의 1단위 등락이
                 낙폭으로 잡혀 -23% 가 -70% 로 부풀었다(v32 의 실제 오류).
                 `since` (납입 종료 인덱스 등)를 반드시 줘야 한다.

    적립식에서 무엇을 재고 싶은지 먼저 정해라:
      · 목돈을 지켜보는 낙폭      -> since=납입종료 인덱스
      · 원금 대비 최악            -> mdd_vs_paid(curve, paid)
    """
    a = np.asarray(curve, dtype=float)
    if kind == 'accum':
        if since is None:
            raise DesignError(
                'kind="accum" 이면 since= 가 필요하다. 적립 초기에는 잔고가 1단위라 '
                '그 등락이 낙폭으로 잡힌다(v32 에서 -23%가 -70%로 부풀었다). '
                '납입 종료 인덱스를 주거나, 원금 대비를 원하면 mdd_vs_paid() 를 써라.')
        a = a[since:]
    elif kind != 'lump':
        raise DesignError(f'kind 는 "lump" 또는 "accum" — 받은 값: {kind}')
    a = a[a > 0]
    if len(a) < 2:
        raise DesignError('유효 구간이 2일 미만이다')
    return float((a / np.maximum.accumulate(a) - 1).min())


def mdd_vs_paid(curve, paid):
    """평가액이 '그때까지 낸 돈' 밑으로 얼마나 내려갔나. 적립식에서 가장 체감되는 수치."""
    v = np.asarray(curve, dtype=float)
    p = np.asarray(paid, dtype=float)
    m = p > 0
    if m.sum() < 2:
        raise DesignError('납입 기록이 없다')
    return float((v[m] / p[m] - 1).min())


# ==================================================================== 격자
def sweep(fn, grid, metric='calmar', edge='raise'):
    """파라미터 격자를 **전부** 훑고, 최적점이 경계면 거부한다.

    v31 이 룩백 21일 줄 하나만 보고 "첨탑이므로 잡음"이라 오판했다.
    실제로는 워크포워드가 고르는 영역(룩백 5~14일)이 넓은 평지였다.

    fn(**params) -> dict(final=, cagr=, mdd=, calmar=) 를 돌려줘야 한다.
    grid: {'lb': [5,7,10,14,21], 'q': [...], 'gate': [...]}  — 각 축의 후보

    반환: dict(best=, table=DataFrame, plateau=bool, edge_axes=[...])
      plateau  최적점 주변 ±1 칸이 최적의 70% 이상이면 True (고원)
      edge_axes 최적점이 격자 끝에 붙은 축 목록 — 있으면 격자를 넓혀야 한다
    """
    import itertools
    keys = list(grid)
    rows = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        p = dict(zip(keys, combo))
        r = fn(**p)
        if metric not in r:
            raise DesignError(f'fn 이 {metric} 를 안 돌려줬다. 키: {list(r)}')
        rows.append({**p, **r})
    df = pd.DataFrame(rows)
    bi = int(df[metric].idxmax())
    best = df.loc[bi].to_dict()

    edges = [k for k in keys if best[k] in (grid[k][0], grid[k][-1]) and len(grid[k]) > 1]
    if edges and edge == 'raise':
        raise DesignError(
            f'최적점이 격자 경계에 있다: {edges}. 진짜 최적이 격자 밖일 수 있으니 '
            f'그 축을 넓혀서 다시 돌려라. (v31 이 이걸 안 해서 "첨탑"으로 오판했다) '
            f'경계를 알고도 진행하려면 edge="warn".')

    # 고원 판정 — 최적점 주변 ±1 칸
    nb = []
    for k in keys:
        i = grid[k].index(best[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(grid[k]):
                q = {kk: best[kk] for kk in keys}
                q[k] = grid[k][j]
                m = df
                for kk, vv in q.items():
                    m = m[m[kk] == vv]
                if len(m):
                    nb.append(float(m[metric].iloc[0]))
    bv = float(best[metric])
    plateau = bool(nb) and min(nb) >= bv * 0.70 if bv > 0 else False
    return dict(best=best, table=df, plateau=plateau, edge_axes=edges,
                neighbors=nb, n_cells=len(df))


# ==================================================================== 워크포워드
def walkforward(fit, test, splits, metric='calmar', fixed=None):
    """워크포워드. **지표를 명시**해야 하고, 고정 대조군을 강제로 병기한다.

    v31 이 IS **수익 최대**로 골라 잡음을 골랐고 OOS 에서 졌다.
    Calmar 로 고르니 선택이 수렴했고, **아예 안 고르고 못박는 게 더 나았다**
    (v32: 고정 8/9 vs 선택 5/9).

    fit(lo, hi) -> params      학습 구간에서 고른 파라미터
    test(params, lo, hi) -> dict(...)   그 파라미터의 OOS 성적
    splits: [(fit_lo, fit_hi, test_lo, test_hi), ...]
    fixed:  미리 못박은 파라미터. **반드시 줘라** — 이게 진짜 대조군이다.
    """
    if fixed is None:
        raise DesignError(
            'fixed= 가 필요하다. 선택한 파라미터를 "고정 대조군"과 비교하지 않으면 '
            '선택이 도움이 됐는지 알 수 없다. v32 에서 고정이 선택을 이겼다(8/9 vs 5/9).')
    sel, fix = [], []
    for fl, fh, tl, th in splits:
        p = fit(fl, fh)
        sel.append({**test(p, tl, th), 'params': p})
        fix.append(test(fixed, tl, th))
    ds = dist([r[metric] for r in sel], '선택')
    dfx = dist([r[metric] for r in fix], '고정')
    return dict(selected=sel, fixed=fix, d_sel=ds, d_fix=dfx,
                selection_helps=ds['median'] > dfx['median'],
                sel_params=[r['params'] for r in sel])


# ==================================================================== 판정
def verdict(name, checks, adopt_if=None):
    """판정문을 **계산값에서** 만든다. 문장을 하드코딩하지 못하게 한다.

    v27 이 옛 숫자(도피구간 9.32%)를 판정문에 박아둬서, 모형을 고친 뒤에도
    틀린 문장이 계속 인쇄됐다. v35 의 AST 스캐너도 서술형이라 못 잡았다.

    checks: [(관문이름, 통과여부, 근거문자열), ...]
    adopt_if: 통과해야 하는 관문 이름들. None 이면 전부.
    """
    need = set(adopt_if) if adopt_if else {c[0] for c in checks}
    passed = {c[0] for c in checks if c[1]}
    okay = need <= passed
    lines = [f"[{name}] 판정: {'채택' if okay else '기각'}"]
    for nm, p, ev in checks:
        mark = 'O' if p else 'X'
        star = ' *' if nm in need else '  '
        lines.append(f"  {mark}{star} {nm:<28} {ev}")
    if not okay:
        lines.append(f"  -> 미통과: {', '.join(sorted(need - passed))}")
    lines.append("  (* = 채택 필수 관문. 이 문장은 계산 결과에서 생성됐다)")
    return dict(adopt=okay, text='\n'.join(lines),
                failed=sorted(need - passed))


# ==================================================================== 자기검사
def _selftest():
    print("=" * 70)
    print("research_kit 자기검사 — 실제로 났던 오류를 재현해 막히는지 본다")
    print("=" * 70)
    n = 0

    def case(desc, fn):
        nonlocal n
        try:
            fn()
            print(f"  [FAIL] {desc} — 막지 못했다")
        except DesignError as e:
            n += 1
            print(f"  [OK]   {desc}")
            print(f"         └ {str(e)[:74]}")

    # #3 적립 MDD 초기허수
    acc = np.r_[0, 1, 0.7, 1.9, 3.0, 12.0]
    case('적립 경로에 since 없이 mdd()', lambda: mdd(acc, kind='accum'))
    got = mdd(acc, since=3, kind='accum')
    print(f"  [OK]   since 를 주면 계산된다 — {got:.1%}")

    # #1 격자 경계
    def f(lb, q):
        return dict(final=lb * q, cagr=.2, mdd=-.5, calmar=lb * q / 100)
    case('최적점이 격자 경계에 있는 sweep()',
         lambda: sweep(f, {'lb': [5, 10, 21], 'q': [.9, .95]}))
    r = sweep(f, {'lb': [5, 10, 21], 'q': [.9, .95]}, edge='warn')
    print(f"  [OK]   edge='warn' 이면 진행하되 경계를 알려준다 — {r['edge_axes']}")

    # #2 고정 대조군 누락
    case('fixed 없이 walkforward()',
         lambda: walkforward(lambda a, b: 1, lambda p, a, b: dict(calmar=.4),
                             [(0, 1, 1, 2)]))

    # #4 표본 부족
    case('표본 2개로 dist()', lambda: dist([1, 2]))

    # #5 판정문 생성
    v = verdict('테스트축', [('플라시보', True, 'p=0.02'),
                            ('워크포워드', False, 'OOS -7.3%')])
    print(f"  [OK]   판정문이 계산값에서 생성된다 (adopt={v['adopt']})")
    print('\n' + '\n'.join('         ' + x for x in v['text'].split('\n')))

    print("\n" + "=" * 70)
    print(f"설계 오류 {n}종을 API 단계에서 차단했다.")
    print("=" * 70)
    return n >= 4


if __name__ == '__main__':
    sys.exit(0 if _selftest() else 1)
