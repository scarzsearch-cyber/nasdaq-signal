# -*- coding: utf-8 -*-
"""저장소 검사 현황표 생성기 (2026-09-06) — 검사를 **실행하지 않는다.** 추적 파일 목록 × 기존 감사 장부·회귀 모듈·관문 목록을 대조해
파일마다 「검사 근거 · 검사 수준 · 검사 후 변경 여부 · 담당」을 적는다. 결과는 audit/COVERAGE_MAP_2026-09-06.md 의 부록 표.

    python audit/coverage_map.py > /tmp/map.md        # 표만 출력(장부의 서술은 손으로)

검사 수준(섞지 않는다 — 높은 것이 낮은 것을 포함하지 않는다는 뜻이 아니라 「가장 강한 근거」만 적는다):
  L0 미검증 · L1 열람/결과 대조 · L2 전문 판독(+실행·수정) · L3 함수 검토/회귀 검사·상시 관문 · L4 연결 검사/실측 · L5 변조(관문 변별력)
담당: 「돈전략(확인)」= 소유자 지시(2026-09-05/06)로 확인된 범위 — F계열 research · 전략 계산 엔진 · 동결값 · 실측 장부 · 원자료.
      그 밖의 research 는 「담당 확인 필요」. 운영·화면·문서·검사 도구는 이번 감사 범위.
"""
import io
import os
import re
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def git(*a):
    return subprocess.run(['git', '-c', 'core.quotepath=false', *a], cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout


LEVEL_NAME = {0: 'L0 미검증', 1: 'L1 열람·대조', 2: 'L2 전문 판독', 3: 'L3 함수 검토·회귀·관문', 4: 'L4 연결·실측', 5: 'L5 변조'}

# 장부 → (수준, 표시명). 장부 본문에 파일 이름이 나오면 그 파일의 근거로 센다.
LEDGERS = {
    'audit/HANDOFF_CROSSCHECK_2026-09-05.md': (1, '인계 교차검증'),
    'audit/HANDOFF_TO_CODEX_2026-09-05.md': (1, '인계문'),
    'audit/AUDIT_LEDGER_2026-09-05.md': (2, 'v206 전체 감사'),
    'audit/CODE_REVIEW_SWEEP_2026-09-05.md': (2, '순회 B01~B15'),
    'research/CODE_REVIEW_2026-09-05.md': (2, 'research 리뷰 v204~v209'),
    'audit/DEEP_REVIEW_OPS_UI_2026-09-05.md': (3, 'v220 심층'),
    'audit/OPS_UI_CROSSCHECK_2026-09-05.md': (3, 'v221 교차'),
    'audit/OPS_RECOVERY_2026-09-05.md': (4, 'v222 연결'),
    'audit/WATCHDOG_CHAIN_2026-09-05.md': (4, '파수꾼 연결'),
    'audit/PAGES_CONCURRENCY_2026-09-06.md': (4, 'pages 실측'),
    'audit/SCREEN_STATES_2026-09-05.md': (4, 'v223 화면 실측'),
    'audit/SCREEN_MATRIX2_2026-09-06.md': (4, 'v224 화면 실측'),
    'audit/MOBILE_OPS_2026-09-06.md': (4, 'v225 모바일 실측'),
}
# 변조 검사는 verify_all 에만 해당한다(다른 파일은 변조 「대상」이지 검사받은 것이 아니다).
GATE_MUTATION = ('audit/GATE_MUTATION_2026-09-05.md', 5, '관문 변별력')

# 회귀 모듈 → (수준, 다루는 파일). 모듈 본문의 파일/모듈 이름을 그대로 근거로 쓴다.
TESTS = {
    'audit/test_ops_recovery3.py': 4, 'audit/test_watchdog_chain4.py': 4, 'audit/test_pages_concurrency.py': 4,
    'audit/test_ops_review2.py': 3, 'audit/test_fold_anchor.py': 3,
    'audit/test_research_review.py': 3, 'audit/test_account_ledger.py': 3, 'audit/test_f1_placebo.py': 3,
    'audit/test_f2_mix.py': 3, 'audit/test_execution_bands.py': 3, 'audit/test_execution_policy.py': 3,
    'audit/test_f3_design.py': 3, 'audit/test_basket_accounting.py': 3, 'audit/test_f4_design.py': 3,
    'audit/test_f4_products.py': 3,
}
# verify_all 상시 관문이 직접 재계산·대조하는 파일(문자열 검사만인 것은 L1 로 낮춰 적는다).
VERIFY_L3 = {'hist_defensive.py', 'hist_data.py', 'axis_lib.py', 'axis_defmix.py', 'axis_volguard.py', 'reentry_lib.py',
             'hist_defasset.py', 'hist_krfinal.py', 'deploy/update_signal.py', 'data/signal.json', 'data/qqq.csv',
             'data/strategy_stats.json', 'data/freeze.json', 'data/oos_log.csv', 'data/oos_protocol_b.json',
             'data/retired_numbers.json', 'data/kr_holidays.json'}
VERIFY_L1 = {'signal.html', 'guide.html', 'notes.html', 'FILES.md', '04_Rejected_Research.md', '01_Strategy_Logic.md',
             '02_Risk_Management.md', 'deploy/watchdog.py', 'deploy/kr_holidays.py', 'deploy/nav_collect.py',
             'deploy/price_now.py', 'deploy/refresh_hist.py', 'deploy/wait_close.py', 'deploy/kr_sources.py',
             '.github/workflows/pages.yml', '.github/workflows/daily-signal.yml', '.github/workflows/monthly-stats.yml',
             '.github/workflows/watchdog.yml', '.github/workflows/price.yml', 'AGENTS.md', 'CLAUDE.md',
             'research/tax_us_direct.py', 'manifest.json', 'icon-192.png', 'icon-512.png', 'data/dd_percentile.json'}
SELFTEST_L3 = {'deploy/watchdog.py', 'deploy/wait_close.py', 'deploy/update_signal.py', 'deploy/build_stats.py',
               'deploy/data_check.py', 'deploy/price_poll.py', 'deploy/refresh_hist.py', 'deploy/notify.py',
               'deploy/signal_alert.py', 'deploy/oos_log.py', 'deploy/nav_collect.py', 'deploy/kakao_setup.py',
               'deploy/kakao_keepalive.py', 'deploy/kr_holidays.py', 'deploy/stamp_rev.py', 'research/axis_finalverify.py'}

F_SERIES = re.compile(r'^research/strategy_f[1-4]_')
ENGINES = {'hist_data.py', 'hist_defasset.py', 'hist_defensive.py', 'hist_divetf.py', 'hist_korea.py', 'hist_krfinal.py',
           'hist_krreal.py', 'hist_tiger.py', 'hyst_core.py', 'reentry_lib.py', 'axis_lib.py', 'axis_defmix.py', 'axis_volguard.py'}
LEDGER_FILES = {'data/oos_log.csv', 'data/nav_history.csv', 'data/freeze.json', 'data/oos_protocol_b.json'}
GENERATED = {'data/strategy_stats.json', 'data/signal.json', 'data/dd_percentile.json', 'data/isa_stats.json',
             'data/crisis_paths.json', 'data/ops_check.json', 'data/kr_holidays.json', 'data/signal_alert_state.json',
             'data/qqq.csv'}
CONTRACTS = {'data/retired_numbers.json'}


def classify(p):
    """(묶음, 종류, 담당)"""
    if p.startswith('archive/') or p.startswith('docs/history/') or p.startswith('docs/raw/'):
        return ('보관본', '보관본', '검사 대상 아님(§2 읽기 전용 · 보관)')
    if p.startswith('data/hist/') or p in ('qqq_us_d.csv', 'qld_us_d.csv', 'schd_us_d.csv', 'fixed_wfa_hist.csv', 'hyst_wfa.csv'):
        return ('원자료', '원자료', '돈전략(확인 · 원자료)')
    if p in LEDGER_FILES:
        return ('실측 장부·동결값', '장부', '돈전략(확인 · 동결값·실측 장부)')
    if p in GENERATED:
        return ('생성물(파이프라인 산출)', '생성물', '운영(이번 범위 · 생성자 코드로 검사)')
    if p in CONTRACTS:
        return ('계약 파일', '계약', '운영(이번 범위)')
    if p.startswith('공유용_별도전략/'):
        return ('공유용_별도전략(격리)', '실행 코드', '검사 대상 아님(격리 · g_isolation 관문만)')
    if p.startswith('내가_보는_것/'):
        return ('소유자 안내·점검', '실행 코드' if p.endswith('.py') else '문서', '운영(이번 범위)')
    if p.startswith('.github/'):
        return ('워크플로', '실행 코드', '운영(이번 범위)')
    if p.startswith('deploy/'):
        return ('운영 스크립트', '실행 코드' if p.endswith('.py') else '문서', '운영(이번 범위)')
    if p.startswith('audit/'):
        return ('검사 도구·회귀·장부', '실행 코드' if p.endswith('.py') else '문서', '운영(이번 범위)')
    if p in ('signal.html', 'guide.html', 'notes.html', 'manifest.json', 'icon-192.png', 'icon-512.png'):
        return ('화면', '화면', '운영·화면(이번 범위)')
    if p in ('verify_all.py', 'research_kit.py'):
        return ('검사 진입점', '실행 코드', '운영(이번 범위)')
    if p in ENGINES:
        return ('전략 계산 엔진(루트)', '실행 코드', '돈전략(확인 · 전략 계산)')
    if F_SERIES.match(p):
        return ('research F계열', '실행 코드', '돈전략(확인 · F계열)')
    if p.startswith('research/') and p.endswith('.py'):
        return ('research 연구 스크립트', '실행 코드', '담당 확인 필요')
    if p.startswith('research/') and p.endswith('.md'):
        return ('research 문서', '문서', '담당 확인 필요')
    if p.endswith('.md'):
        return ('문서(루트·docs)', '문서', '운영(이번 범위)')
    return ('기타', '기타', '담당 확인 필요')


def main():
    tracked = [t for t in git('ls-files').splitlines() if t.strip()]
    texts = {}
    for lp in list(LEDGERS) + [GATE_MUTATION[0]] + list(TESTS):
        fp = os.path.join(ROOT, lp)
        texts[lp] = io.open(fp, encoding='utf-8').read() if os.path.exists(fp) else ''
    ctime = {}
    def last_commit(p):
        if p not in ctime:
            ctime[p] = int(git('log', '-1', '--format=%ct', '--', p).strip() or 0)
        return ctime[p]

    rows = []
    for p in tracked:
        grp, kind, owner = classify(p)
        base = os.path.basename(p)
        stem = os.path.splitext(base)[0]
        pat = re.compile(r'(?<![\w-])' + re.escape(base) + r'(?!\w)')            # 경로 구분자(/ .) 앞은 허용
        stem_pat = re.compile(r'(?<![\w-])' + re.escape(stem) + r'(?![\w])') if len(stem) >= 6 else None
        ev = []          # (level, label, ledger_path)
        if grp in ('보관본',) or grp.startswith('공유용'):
            pass
        else:
            for lp, (lv, name) in LEDGERS.items():
                if pat.search(texts[lp]) or (p in texts[lp]) or (stem_pat and stem_pat.search(texts[lp])):   # 순회 장부는 stem 만 적는다
                    ev.append((lv, name, lp))
            if p == 'verify_all.py':
                ev.append((GATE_MUTATION[1], GATE_MUTATION[2], GATE_MUTATION[0]))
            for tp, lv in TESTS.items():
                t = texts[tp]
                if p == tp:
                    continue
                if pat.search(t) or (stem_pat and stem_pat.search(t)):
                    ev.append((lv, '회귀 ' + os.path.basename(tp), tp))
            if p in VERIFY_L3:
                ev.append((3, '관문 verify_all(재계산·지문)', 'verify_all.py'))
            elif p in VERIFY_L1:
                ev.append((1, '관문 verify_all(문자열·목록)', 'verify_all.py'))
            if p in SELFTEST_L3:
                ev.append((3, '셀프테스트(I14)', 'verify_all.py'))
        # research 는 운영 연결·실측 장부에 이름만 나온 것을 「연결 검사」로 세지 않는다(언급 = L1)
        if grp.startswith('research'):
            ev = [(1 if (lv >= 3 and lp not in ('research/CODE_REVIEW_2026-09-05.md',) and not lp.startswith('audit/test_')) else lv, name if lv < 3 or lp.startswith('audit/test_') else name + '(언급)', lp) for lv, name, lp in ev]
        level = max([e[0] for e in ev], default=0)
        strongest = [e for e in ev if e[0] == level]
        # 검사 후 변경: 파일의 마지막 커밋이 가장 최근 근거(장부·회귀 모듈)의 마지막 커밋보다 뒤인가
        changed = ''
        if ev:
            newest_ev = max(last_commit(e[2]) for e in ev)
            if last_commit(p) > newest_ev:
                changed = '검사 후 변경'
        labels = '·'.join(sorted({e[1] for e in strongest}))
        na = None
        if grp == '보관본': na = 'n/a 보관본'
        elif grp.startswith('공유용'): na = 'n/a 격리(g_isolation 만)'
        elif grp == '원자료': na = 'n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님)'
        elif grp.startswith('생성물'): na = 'n/a 생성물(생성자 코드 기준)'
        elif grp == '실측 장부·동결값': na = 'n/a 장부(관문 I11·I13 지문·행수 감시 · 내용은 §2 불변)'
        elif grp == '검사 도구·회귀·장부' and (kind == '문서' or base.startswith('test_')): na = 'n/a 근거 문서/회귀 모듈(도구)'
        elif grp == '검사 도구·회귀·장부' and not ev: na = 'n/a 검사 도구 자신(대상 아님)'
        level_name = na or LEVEL_NAME[level]
        others = '·'.join(sorted({e[1] for e in ev if e[0] < level}))
        rows.append((grp, p, kind, owner, level_name, labels, others, changed))

    # 요약
    by = defaultdict(list)
    for r in rows:
        by[r[0]].append(r)
    print('## 요약 (묶음별)\n')
    print('| 묶음 | 파일 수 | L0 | L1 | L2 | L3 | L4 | L5 | n/a | 검사 후 변경 | 담당 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for grp, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        cnt = [sum(1 for r in rs if r[4].startswith('L%d' % i)) for i in range(6)]
        na = sum(1 for r in rs if r[4].startswith('n/a'))
        ch = sum(1 for r in rs if r[7])
        owners = '·'.join(sorted({r[3] for r in rs}))
        print('| %s | %d | %s | %d | %d | %s |' % (grp, len(rs), ' | '.join(str(c) for c in cnt), na, ch, owners))
    print('\n## 부록 — 파일별\n')
    print('| 묶음 | 파일 | 종류 | 담당 | 수준 | 근거(최강) | 그 외 근거 | 변경 |')
    print('|---|---|---|---|---|---|---|---|')
    for r in sorted(rows, key=lambda r: (r[0], r[1])):
        print('| %s | `%s` | %s | %s | %s | %s | %s | %s |' % r)


if __name__ == '__main__':
    main()
