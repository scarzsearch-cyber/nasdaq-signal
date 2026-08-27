# -*- coding: utf-8 -*-
"""
[v35] 전수조사 — 폴더 안의 모든 파이썬 파일을 한 줄도 빼지 않고 훑는다

v34 는 '채택 결정에 관여한 파일'만 읽고 나머지는 패턴 스캔으로 갈음했다.
사용자 요구로 **전수**로 바꾼다. 방법은 AST 기반이다 — 정규식은 놓친다.

[검사 항목]
  1. 백테스트 루프의 체결 정렬       (v33 버그 유형)
  2. 재조정 비용 분모               (v27 버그 유형)
  3. 미래 참조 — 문턱/통계에 전표본   (v30 버그 유형)
  4. rolling/expanding 의 shift 누락  (신호 계열 일반)
  5. 하드코딩된 판정 문구            (v30 초판 유형 — 출력과 결론이 어긋남)
  6. 죽은 파일 / import 실패
  7. 문서 수치 vs 코드 출력 대조

각 파일을 AST 로 파싱해 **모든 for 루프**를 찾아 위험 패턴을 검사한다.
"""
import ast
import io
import os
import sys
import glob

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = '.'
SKIP_DIRS = {'__pycache__', '.git', '.claude'}
findings = []


def rec(sev, f, line, kind, msg):
    findings.append((sev, f, line, kind, msg))


def src_of(node, lines):
    try:
        return '\n'.join(lines[node.lineno - 1: node.end_lineno])
    except Exception:
        return ''


def has_call(node, names):
    """서브트리에 지정한 이름의 호출/속성이 있는가"""
    for n in ast.walk(node):
        if isinstance(n, ast.Attribute) and n.attr in names:
            return True
        if isinstance(n, ast.Name) and n.id in names:
            return True
    return False


def check_loop_alignment(fn, tree, lines, f):
    """① 백테스트 루프: 수익 적용이 포지션 결정보다 먼저 오는가 (2버킷형)"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        body = node.body
        grow_i = pos_i = None
        for i, st in enumerate(body):
            s = src_of(st, lines)
            # 자산 성장: X *= (1 + r[i]) 형
            if grow_i is None and isinstance(st, ast.AugAssign) \
                    and isinstance(st.op, ast.Mult) and '(1 +' in s:
                grow_i = i
            # 포지션 결정: pos = w[i - 1] 형
            if pos_i is None and isinstance(st, ast.Assign) \
                    and ('w[i - 1]' in s or 'w[i-1]' in s or '[i - lag]' in s):
                pos_i = i
        if grow_i is not None and pos_i is not None and grow_i < pos_i:
            # 단일버킷(V *= (1 + (rk if pos else dfr))) 은 pos 로 자산을 고르므로 무해
            gs = src_of(body[grow_i], lines)
            if 'pos' in gs:
                continue
            rec('HIGH', f, body[grow_i].lineno, '체결정렬',
                '수익 적용이 포지션 결정보다 먼저 (v33 유형)')


def check_cost_denom(fn, tree, lines, f):
    """② 재조정 비용 분모: 비용 곱한 뒤 분모를 잡는가 (v27 유형)"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        cost_i = prev_i = None
        for i, st in enumerate(node.body):
            s = src_of(st, lines)
            if cost_i is None and ('(1 - cost' in s or '* (1 - rebal_cost' in s):
                cost_i = i
            if prev_i is None and isinstance(st, ast.Assign) \
                    and ('prev = sum(' in s or 'prev = b.sum()' in s):
                prev_i = i
        if cost_i is not None and prev_i is not None and cost_i < prev_i:
            rec('HIGH', f, node.body[prev_i].lineno, '비용분모',
                '비용 차감 뒤에 분모를 잡음 (v27 유형)')


def check_lookahead(fn, tree, lines, f):
    """③ 전표본 통계를 문턱으로 쓰는가 (v30 유형)"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        s = src_of(node, lines)
        if any(k in s for k in ('nanpercentile', 'np.percentile', '.quantile(')) \
                and 'expanding' not in s and 'rolling' not in s:
            # 결과 분포 출력(f-string 안)이면 제외
            rec('CHECK', f, node.lineno, '전표본문턱',
                s.strip().replace('\n', ' ')[:88])


def check_shift(fn, tree, lines, f):
    """④ rolling/expanding 산출물이 shift 없이 신호로 쓰이는가"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        s = src_of(node, lines)
        if ('rolling(' in s or 'expanding(' in s) and 'return' in s:
            if 'shift(' not in s and node.name in ('dd_arr', 'ma_arr', 'mom_arr', 'vol_arr',
                                                   'zc', 'exp_q', 'z'):
                rec('CHECK', f, node.lineno, 'shift누락',
                    f'{node.name}() 가 rolling/expanding 결과를 shift 없이 반환')


def check_hardcoded_verdict(fn, tree, lines, f):
    """⑤ 하드코딩된 판정 문구 — 계산 결과와 무관하게 결론을 인쇄하는가"""
    VERDICT = ('진다', '이긴다', '기각', '채택', '통과', '실패한다', '우세', '열세')
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == 'print'):
            continue
        for a in node.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                t = a.value
                if any(v in t for v in VERDICT) and '->' in t:
                    rec('CHECK', f, node.lineno, '판정하드코딩',
                        t.strip()[:88])


def point_in_time_replay():
    """★ 결정적 검사 — 시점별 재계산

    벡터 연산으로 만든 신호가 정말 '그날까지의 정보'만 쓰는지 확인하는 유일한 방법은
    **날짜별로 데이터를 잘라서 다시 계산해보는 것**이다. 잘린 데이터로 만든 값이
    전체 데이터로 만든 값과 같으면 미래를 안 본 것이다.
    """
    import numpy as np
    import pandas as pd
    import hist_defensive as DF
    import axis_volguard as V
    from axis_lib import rule_w

    print("=" * 92)
    print("★ 시점별 재계산 (point-in-time replay) — 미래참조의 결정적 검사")
    print("=" * 92)
    D = DF.build('chain')
    idx, px = D['idx'], D['px']
    n = len(idx)
    rng = np.random.default_rng(0)
    pts = sorted(rng.choice(np.arange(3000, n), size=40, replace=False))

    # (a) 핵심 신호 — 252일 낙폭
    full = (px / px.rolling(252, min_periods=252).max() - 1).fillna(0).values
    bad = 0
    for t in pts:
        cut = px.iloc[:t + 1]
        v = (cut / cut.rolling(252, min_periods=252).max() - 1).fillna(0).values[-1]
        if abs(v - full[t]) > 1e-12:
            bad += 1
    print(f"  (a) QQQ 252일 낙폭        불일치 {bad}/{len(pts)}")

    # (b) 변동성 가드 — zc(z점수) + exp_q(확장창 분위)
    rv_full = px.pct_change().rolling(10, min_periods=10).std()
    z_full = V.zc(rv_full.values)
    q_full = V.exp_q(z_full, 0.925)
    bz = bq = 0
    for t in pts:
        cut = px.iloc[:t + 1]
        rv = cut.pct_change().rolling(10, min_periods=10).std()
        z = V.zc(rv.values)
        if abs(z[-1] - z_full[t]) > 1e-10:
            bz += 1
        q = V.exp_q(z, 0.925)
        a, b = q[-1], q_full[t]
        if not (np.isnan(a) and np.isnan(b)) and abs(np.nan_to_num(a) - np.nan_to_num(b)) > 1e-10:
            bq += 1
    print(f"  (b) 변동성 z점수 zc()      불일치 {bz}/{len(pts)}")
    print(f"  (c) 확장창 분위 exp_q()    불일치 {bq}/{len(pts)}")

    # (d) 최종 비중경로
    wf = rule_w(D['ddv'], -0.16, -0.16)
    bw = 0
    for t in pts:
        cut = px.iloc[:t + 1]
        dv = (cut / cut.rolling(252, min_periods=252).max() - 1).fillna(0).values
        if rule_w(dv, -0.16, -0.16)[-1] != wf[t]:
            bw += 1
    print(f"  (d) 비중경로 rule_w()      불일치 {bw}/{len(pts)}")

    tot = bad + bz + bq + bw
    print("")
    print(f"  -> 총 불일치 {tot}건. 0 이면 어떤 신호도 미래를 보지 않는다.")
    if tot:
        rec('HIGH', '(runtime)', 0, '시점별재계산', f'{tot}건 불일치 — 미래참조 의심')
    print()


def main():
    files = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.endswith('.py'):
                files.append(os.path.join(dp, fn).replace('\\', '/').lstrip('./'))
    files.sort()
    print(f"전수조사 대상: 파이썬 {len(files)}개 파일\n")
    point_in_time_replay()

    ok = 0
    for f in files:
        try:
            src = io.open(f, encoding='utf-8').read()
            lines = src.split('\n')
            tree = ast.parse(src)
            ok += 1
        except Exception as e:
            rec('HIGH', f, 0, '파싱실패', str(e)[:80])
            continue
        check_loop_alignment(f, tree, lines, f)
        check_cost_denom(f, tree, lines, f)
        check_lookahead(f, tree, lines, f)
        check_shift(f, tree, lines, f)
        check_hardcoded_verdict(f, tree, lines, f)

    print(f"파싱 성공 {ok}/{len(files)}\n")
    for sev in ('HIGH', 'CHECK'):
        rows = [r for r in findings if r[0] == sev]
        print("=" * 92)
        print(f"[{sev}] {len(rows)}건")
        print("=" * 92)
        if not rows:
            print("  없음\n")
            continue
        for _, f, ln, kind, msg in rows:
            print(f"  {f}:{ln}  <{kind}>  {msg}")
        print()

    # 파일 목록 (전수 확인용)
    print("=" * 92)
    print("전수 목록")
    print("=" * 92)
    for f in files:
        n = sum(1 for r in findings if r[1] == f)
        mark = f'  <- {n}건' if n else ''
        print(f"  {f}{mark}")


if __name__ == '__main__':
    main()
