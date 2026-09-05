# -*- coding: utf-8 -*-
"""verify_all.py 관문 변별력 검사 — 「실패해야 할 때 실제로 실패하는가」 (2026-09-05 · 5차)

이 저장소에서 가장 큰 사각지대는 「통과만 하는 검사」다(CLAUDE §-1 ⑤ · v148 · v186).
v148·v186·2026-09-04 코드리뷰가 관문 몇 개를 일부러 깨뜨려 봤지만 전수는 없었다.
여기서는 verify_all 의 관문 하나하나에 **그 관문이 막으려는 결함을 실제로 주입**하고
(임시 클론 · 실제 저장소·장부 무접촉) 그 관문이 FAIL(설계상 WARN 이면 WARN)을 내는지 본다.

    python audit/gate_mutation.py            # 전수 (약 3~5분 · 임시 클론)
    python audit/gate_mutation.py --only i6  # 접두어로 고른다
    python audit/gate_mutation.py --list

판정: 기대한 검사명이 FAIL/WARN 목록에 있으면 「잡힘」. 하나라도 못 잡으면 종료코드 1.
※ 전략·실측 장부·원자료는 클론 안에서만 바뀐다. 실제 작업 트리는 읽기만 한다.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


# ------------------------------------------------------------------ 편집 도우미
def _p(root, rel):
    return os.path.join(root, rel.replace('/', os.sep))


def read(root, rel):
    return io.open(_p(root, rel), encoding='utf-8').read()


def write(root, rel, text):
    d = os.path.dirname(_p(root, rel))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(_p(root, rel), 'w', encoding='utf-8', newline='\n').write(text)


def sub(root, rel, old, new, count=1):
    """old 가 반드시 있어야 한다 — 없으면 변조 자체가 헛돈 것이라 예외로 멈춘다."""
    t = read(root, rel)
    if old not in t:
        raise AssertionError('변조 대상 문자열 없음: %s ← %r' % (rel, old[:60]))
    write(root, rel, t.replace(old, new, count) if count else t.replace(old, new))


def append(root, rel, text):
    write(root, rel, read(root, rel) + text)


def remove(root, rel):
    os.remove(_p(root, rel))


def edit_json(root, rel, fn):
    j = json.load(io.open(_p(root, rel), encoding='utf-8'))
    fn(j)
    write(root, rel, json.dumps(j, ensure_ascii=False, indent=1))


def edit_csv_row(root, rel, row_idx, col, value):
    lines = read(root, rel).splitlines()
    hdr = lines[0].split(',')
    cells = lines[row_idx].split(',')
    cells[hdr.index(col)] = value
    lines[row_idx] = ','.join(cells)
    write(root, rel, '\n'.join(lines) + '\n')


def git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', check=True)


# ------------------------------------------------------------------ 변조 목록
# (id, 관문 함수, D 필요 여부, 기대 [(검사명 부분문자열, 'F'|'W')], 변조 함수, 설명)
M = []


def mut(id_, gate, need_d, expect, why='', blind=False):
    """blind=True: 그 관문의 **검사 대상이 아닌** 결함 — 못 잡는 것이 정상이며 BLIND 로 표시한다(사각지대 문서화)."""
    def deco(fn):
        M.append((id_, gate, need_d, expect, fn, why, blind))
        return fn
    return deco


def _scen(j, key):
    return [x for x in j['scenarios'] if x['key'] == key][0]


def _emb(j, key):
    return [x for x in j['stats']['scenarios'] if x['key'] == key][0]


# ---- I1~I4 엔진 ----
@mut('i3_lag0', 'i3_lag', True, [('미래훔쳐보기가 규약보다 유리', 'F')],
     '체결 지연 규약이 0 이 되면(당일 신호 당일 체결) 미래훔쳐보기와 같아진다')
def _(r):
    sub(r, 'axis_lib.py', 'def sim(D, w, riskon_r=None, cost=COST, lag=1,',
        'def sim(D, w, riskon_r=None, cost=COST, lag=0,')


@mut('i2_ddv_future', 'i2_pit', True, [('QQQ 낙폭 시점별 일치', 'F')],
     '엔진의 낙폭 벡터가 하루 앞 값을 쓰면(미래참조) 시점별 재계산과 갈린다')
def _(r):
    sub(r, 'hist_data.py', 'ddv=dd.values.astype(float)',
        'ddv=dd.shift(-1).fillna(0).values.astype(float)')


@mut('i4_ust_fee', 'i4_real', True, [('국채 305080 드리프트', 'F')],
     '국채 모형 보수를 연 3%p 올리면 실물과 ±1.5%p 를 넘는다')
def _(r):
    sub(r, 'hist_defasset.py', 'UST_FEE = 0.0029', 'UST_FEE = 0.0329')


# ---- I11 동결 ----
@mut('i11_freeze_enter', 'i11_freeze', False, [('진입선 -0.16', 'F')])
def _(r):
    edit_json(r, 'data/freeze.json', lambda j: j['rule'].__setitem__('enter', -0.15))


@mut('i11_freeze_lookback', 'i11_freeze', False,
     [('룩백 252일', 'F'), ('화면 룩백이 동결값과 같다', 'F'), ('신호 생성기 룩백이 동결값과 같다', 'F')])
def _(r):
    edit_json(r, 'data/freeze.json', lambda j: j['rule'].__setitem__('lookback', 200))


@mut('i11_upd_strat', 'i11_freeze', False, [('신호 생성기가 동결 규칙과 같다', 'F')])
def _(r):
    sub(r, 'deploy/update_signal.py', '("B", "−16 / −16", -0.16, -0.16)', '("B", "−16 / −16", -0.16, -0.15)')


@mut('i11_upd_adjclose', 'i11_freeze', False, [('신호원이 수정 종가(adjclose)다', 'F')],
     '값을 뽑는 줄만 비수정 종가로 — 주석·경고문의 adjclose 는 그대로 남긴다')
def _(r):
    sub(r, 'deploy/update_signal.py', 'ind.get("adjclose")', 'ind.get("close")')


@mut('i11_upd_lookback', 'i11_freeze', False, [('신호 생성기 룩백이 동결값과 같다', 'F')])
def _(r):
    sub(r, 'deploy/update_signal.py', '\nLOOKBACK = 252', '\nLOOKBACK = 200')


@mut('i11_html_rule', 'i11_freeze', False, [('화면이 동결 규칙과 같다', 'F')])
def _(r):
    sub(r, 'signal.html', 'enter:-0.16, exit:-0.16', 'enter:-0.16, exit:-0.15')


@mut('i11_html_lookback', 'i11_freeze', False, [('화면 룩백이 동결값과 같다', 'F')])
def _(r):
    sub(r, 'signal.html', 'const LOOKBACK = 252;', 'const LOOKBACK = 200;')


@mut('i11_oos_fp', 'i11_freeze', False, [('OOS 장부 지문이 전부 현행 동결본과 같다', 'F')])
def _(r):
    edit_csv_row(r, 'data/oos_log.csv', 1, 'fingerprint', 'deadbeefdeadbeef')


@mut('i11_oos_truncated', 'i11_freeze', False, [('OOS 장부가 줄지 않았다', 'F')],
     '작업본이 HEAD 보다 한 행 짧다 — 장부가 잘린 것')
def _(r):
    lines = read(r, 'data/oos_log.csv').splitlines()
    write(r, 'data/oos_log.csv', '\n'.join(lines[:-1]) + '\n')


@mut('i11_oos_empty', 'i11_freeze', False, [('OOS 장부가 쌓이고 있다', 'W'), ('OOS 장부가 줄지 않았다', 'F')],
     '장부가 머리글만 남으면 「안 쌓임」은 WARN(설계) 이고 「줄었다」가 FAIL 로 잡아야 한다')
def _(r):
    write(r, 'data/oos_log.csv', read(r, 'data/oos_log.csv').splitlines()[0] + '\n')


# ---- g_freeze_seal ----
@mut('seal_weights', 'g_freeze_seal', False, [('동결 파일 내용이 봉인과 같다', 'F'), ('방어 비중 40/40/20', 'F')])
def _(r):
    def f(j):
        for x in j['defensive']:
            x['weight'] = {'458730': 0.5, '305080': 0.3, '411060': 0.2}[x['code']]
    edit_json(r, 'data/freeze.json', f)


@mut('seal_cost', 'g_freeze_seal', False, [('동결 파일 내용이 봉인과 같다', 'F'), ('비용 규약 편도', 'F')])
def _(r):
    edit_json(r, 'data/freeze.json', lambda j: j['cost'].__setitem__('one_way', 0.002))


@mut('seal_exec', 'g_freeze_seal', False, [('동결 파일 내용이 봉인과 같다', 'F'), ('체결 규약이 한 칸 지연이다', 'F')])
def _(r):
    edit_json(r, 'data/freeze.json', lambda j: j.__setitem__('execution', '당일 종가 신호 -> 당일 체결'))


@mut('seal_riskon', 'g_freeze_seal', False, [('동결 파일 내용이 봉인과 같다', 'F'), ('공격 자산이 418660 이다', 'F')])
def _(r):
    edit_json(r, 'data/freeze.json', lambda j: j['risk_on'].__setitem__('code', '409820'))


@mut('seal_only_label', 'g_freeze_seal', False, [('동결 파일 내용이 봉인과 같다', 'F')],
     'rule 밖 항목(principle) 한 글자 — 숫자 검사는 못 보지만 내용 봉인이 잡아야 한다')
def _(r):
    edit_json(r, 'data/freeze.json', lambda j: j.__setitem__('principle', str(j.get('principle', '')) + ' x'))


# ---- I12 그림자 ----
@mut('i12_missing_field', 'i12_shadow', False, [('그림자 세 필드가 모든 OOS 행에 있다', 'F')])
def _(r):
    edit_csv_row(r, 'data/oos_log.csv', 2, 't4_votes', '')


@mut('i12_inconsistent', 'i12_shadow', False, [('그림자 기록이 정의와 모순 없음', 'F')],
     'votes 3 · rv 34.9 인데 w 0.5 — 정의(w=min(1,40/rv)) 위반')
def _(r):
    edit_csv_row(r, 'data/oos_log.csv', 2, 't4_w', '0.5')


@mut('i12_all_blank', 'i12_shadow', False, [('그림자 기록이 실제로 쌓여 있다', 'F')],
     '전 행의 t4 세 열이 비면 「0행 검사 PASS」가 아니라 파이프라인 사망으로 잡아야 한다')
def _(r):
    lines = read(r, 'data/oos_log.csv').splitlines()
    hdr = lines[0].split(',')
    out = [lines[0]]
    for ln in lines[1:]:
        c = ln.split(',')
        for k in ('t4_votes', 't4_rv', 't4_w'):
            c[hdr.index(k)] = ''
        out.append(','.join(c))
    write(r, 'data/oos_log.csv', '\n'.join(out) + '\n')


@mut('i12_doc_stale', 'i12_shadow', False, [('01 문서 AUTO-STATS 블록 동기화', 'F')],
     '01 문서의 AUTO-STATS 블록이 옛 끝 날짜를 들고 있다')
def _(r):
    S = json.load(io.open(_p(r, 'data/strategy_stats.json'), encoding='utf-8'))
    endd = S['scenarios'][0]['strategies']['B']['end']
    t = read(r, '01_Strategy_Logic.md')
    i0, j0 = t.find('<!-- AUTO-STATS:START'), t.find('<!-- AUTO-STATS:END -->')
    blk = t[i0:j0].replace(endd, '2020-01-01')
    assert endd in t[i0:j0]
    write(r, '01_Strategy_Logic.md', t[:i0] + blk + t[j0:])


# ---- I13 규약 ----
@mut('i13_body', 'i13_protocol', False, [('규약 지문 일치', 'F')])
def _(r):
    edit_json(r, 'data/oos_protocol_b.json', lambda j: j.__setitem__('judgment', str(j.get('judgment')) + ' x'))


@mut('i13_freeze_link', 'i13_protocol', False, [('규약 지문 일치', 'F'), ('규약이 가리키는 동결 지문', 'F')])
def _(r):
    edit_json(r, 'data/oos_protocol_b.json', lambda j: j['applies_to'].__setitem__('freeze_fingerprint', '0000000000000000'))


@mut('i13_doc', 'i13_protocol', False, [('02 §5-1 이 같은 지문을 적고 있다', 'F')])
def _(r):
    j = json.load(io.open(_p(r, 'data/oos_protocol_b.json'), encoding='utf-8'))
    sub(r, '02_Risk_Management.md', j['fingerprint'], 'xxxx', count=0)


@mut('i13_evaluator_gone', 'i13_protocol', False, [('평가기 존재', 'F')])
def _(r):
    remove(r, 'research/oos_protocol_b.py')


# ---- I6 라이브 ----
def _sig(fn):
    return lambda r: edit_json(r, 'data/signal.json', fn)


@mut('i6_asof', 'i6_live', False, [('as_of 가 데이터 마지막 날과 일치', 'F')])
def _(r):
    _sig(lambda j: j.__setitem__('as_of', '2026-09-03'))(r)


@mut('i6_dd', 'i6_live', False, [('낙폭 재계산 일치', 'F')],
     'gap_pp 는 CSV 에서 재계산하므로 json dd 만 바꿔서는 gap 검사가 안 울리는 것이 맞다')
def _(r):
    _sig(lambda j: j.__setitem__('dd', j['dd'] + 0.5))(r)


@mut('i6_stats_gen', 'i6_live', False, [('signal.json 내장 stats 가 strategy_stats.json 과 같은', 'F')])
def _(r):
    _sig(lambda j: j['stats'].__setitem__('generated_at', '2000-01-01 00:00 UTC'))(r)


@mut('i6_final', 'i6_live', False, [('내장 us_2000 B 최종배수 일치', 'F')])
def _(r):
    _sig(lambda j: _emb(j, 'us_2000')['strategies']['B'].__setitem__('final', _emb(j, 'us_2000')['strategies']['B']['final'] * 1.01))(r)


@mut('i6_ulcer', 'i6_live', False, [('내장 us_2000 A ulcer 일치', 'F')])
def _(r):
    _sig(lambda j: _emb(j, 'us_2000')['strategies']['A'].__setitem__('ulcer', _emb(j, 'us_2000')['strategies']['A']['ulcer'] + 1))(r)


@mut('i6_horizons', 'i6_live', False, [('내장 us_1972 B horizons 일치', 'F')])
def _(r):
    _sig(lambda j: _emb(j, 'us_1972')['strategies']['B']['horizons'].__setitem__('20', 1.0))(r)


@mut('i6_horizons_missing', 'i6_live', False, [('내장 us_1972 B horizons 일치', 'F')],
     '20년 표본인데 사본에서 horizons 가 통째로 빠짐 — 옛 None==None 탈출구 재발 검사')
def _(r):
    _sig(lambda j: _emb(j, 'us_1972')['strategies']['B'].pop('horizons'))(r)


@mut('i6_bench', 'i6_live', False, [('내장 us_2000 벤치 lev 있음', 'F')])
def _(r):
    _sig(lambda j: _emb(j, 'us_2000')['benchmarks']['lev'].pop('ulcer'))(r)


@mut('i6_close', 'i6_live', False, [('close 재계산 일치', 'F')])
def _(r):
    _sig(lambda j: j.__setitem__('close', j['close'] + 1))(r)


@mut('i6_high', 'i6_live', False, [('high_252 재계산 일치', 'F')])
def _(r):
    _sig(lambda j: j.__setitem__('high_252', j['high_252'] + 1))(r)


@mut('i6_state', 'i6_live', False, [('상태 재계산 일치 (B)', 'F')])
def _(r):
    _sig(lambda j: j['strategies']['B'].__setitem__('state', 'SCHD'))(r)


@mut('i6_changed', 'i6_live', False, [('changed_today 재계산 일치 (B)', 'F')])
def _(r):
    _sig(lambda j: j['strategies']['B'].__setitem__('changed_today', True))(r)


@mut('i6_prev', 'i6_live', False, [('prev_state 재계산 일치 (B)', 'F')])
def _(r):
    _sig(lambda j: j['strategies']['B'].__setitem__('prev_state', 'SCHD'))(r)


@mut('i6_nextline', 'i6_live', False, [('next_line 재계산 일치 (B)', 'F')])
def _(r):
    _sig(lambda j: j['strategies']['B'].__setitem__('next_line', -11.0))(r)


@mut('i6_gap', 'i6_live', False, [('gap_pp 재계산 일치 (B)', 'F')])
def _(r):
    _sig(lambda j: j['strategies']['B'].__setitem__('gap_pp', j['strategies']['B']['gap_pp'] + 1))(r)


@mut('i6_enter', 'i6_live', False, [('진입·복귀선이 동결값 그대로 (B)', 'F')])
def _(r):
    _sig(lambda j: j['strategies']['B'].__setitem__('enter', -30.0))(r)


# ---- I7 공표 ----
@mut('i7_final', 'i7_stats', True, [('us_1972 B 가 현재 코드와 일치', 'F')])
def _(r):
    edit_json(r, 'data/strategy_stats.json',
              lambda j: _scen(j, 'us_1972')['strategies']['B'].__setitem__('final', _scen(j, 'us_1972')['strategies']['B']['final'] * 1.05))


@mut('i7_bench_years', 'i7_stats', True, [('us_2000 벤치가 전략과 같은 기간', 'F')])
def _(r):
    edit_json(r, 'data/strategy_stats.json',
              lambda j: _scen(j, 'us_2000')['benchmarks']['lev'].__setitem__('years', _scen(j, 'us_2000')['benchmarks']['lev']['years'] + 1))


@mut('i7_bench_mdd', 'i7_stats', True, [('us_2000 벤치 lev 가 전략보다 깊게 빠진다', 'F')])
def _(r):
    edit_json(r, 'data/strategy_stats.json',
              lambda j: _scen(j, 'us_2000')['benchmarks']['lev'].__setitem__('mdd', -10.0))


# ---- I8 봉인 ----
@mut('i8_rule_w_edit', 'i8_deps', False, [('공용 모형 8종이 봉인과 같다', 'F')],
     'rule_w 본문에 실행문 하나 — 주석만 바꿔도 잡히는 것이 봉인의 뜻')
def _(r):
    t = read(r, 'axis_lib.py')
    m = re.search(r'^def rule_w\(.*?\):\n', t, re.M | re.S)
    assert m
    write(r, 'axis_lib.py', t[:m.end()] + '    _probe = 1\n' + t[m.end():])


@mut('i8_rule_w_gone', 'i8_deps', False, [('공용 모형 8종이 봉인과 같다', 'F')])
def _(r):
    sub(r, 'axis_lib.py', 'def rule_w(', 'def rule_w_renamed(')


# ---- I9 폐기 수치 ----
@mut('i9_current_doc', 'i9_retired', False, [('현행 문서에 폐기 수치 없음', 'F')])
def _(r):
    append(r, 'README.md', '\n최종배수 263,062 (시험).\n')


@mut('i9_ledger_loose', 'i9_retired', False, [('정정 대장에 맨몸으로 남은 폐기 수치 없음', 'F')],
     'CLAUDE.md 에 폐기값을 근처(±3줄) 정정 표시 없이 인용')
def _(r):
    append(r, 'CLAUDE.md', '\n\n\n\n\n시험 인용 263,062 배.\n\n\n\n\n')


@mut('i9_target_gone', 'i9_retired', False, [('폐기 수치 검사 대상이 전부 있다', 'W')],
     '검사 대상 문서가 사라지면 조용히 통과가 아니라 WARN(설계)')
def _(r):
    remove(r, 'HANDOFF.md')


# ---- I14 셀프테스트 ----
@mut('i14_exit1', 'i14_selftests', False, [('한국 휴장일 셀프테스트', 'F')])
def _(r):
    write(r, 'deploy/kr_holidays.py', 'import sys\nsys.exit(1)\n')


@mut('i14_gone', 'i14_selftests', False, [('화면 개정 도장 셀프테스트', 'F')])
def _(r):
    remove(r, 'deploy/stamp_rev.py')


# ---- I5 화면 검사 ----
def _h(old, new):
    return lambda r: sub(r, 'signal.html', old, new)


for _id, _name, _old, _new in (
        ('i5_order', '화면: A(-16/-11) 가 없다', "const ORDER = ['B'];", "const ORDER = ['A', 'B'];"),
        ('i5_sel', '화면: 기본 규칙이 B 다', "let sel  = 'B';", "let sel  = 'A';"),
        ('i5_skey', '화면: 저장된 옛 선택값을 지운다', 'localStorage.removeItem(SKEY)', 'void 0'),
        ('i5_rec', '화면: 비교표 전략 4줄 + 추천은 파랑만', 'tr.rec td.strat', 'tr.rec td.name'),
        ('i5_guide_tab', '화면: 설명서 탭 연결', 'href="guide.html"', 'href="guide2.html"'),
        ('i5_notes_tab', '화면: 업데이트 노트 탭 연결', 'href="notes.html"', 'href="notes2.html"'),
        ('i5_prox', '화면: 임계점 거리 게이지', 'function paintProx', 'function _paintProx'),
        ('i5_action', '화면: 오늘의 행동', 'function portCompute', 'function _portCompute'),
        ('i5_pending', '화면: 전환 미체결 경고', 'function drawPending', 'function _drawPending'),
        ('i5_fold', '화면: 성과표 각주·타임머신은 접힘', '망설여진다면', '망설이면'),
        ('i5_extbar', '화면: 바깥 링크 스트립', 'id="extbar"', 'id="extbar2"'),
        ('i5_sticky', '화면: 모바일 고정열(Sticky)', 'td.strat{position:sticky', 'td.strat{position:static'),
        ('i5_t4', '화면: T4 그림자 패널', 'function drawT4', 'function _drawT4'),
        ('i5_horiz', '화면: 같은 기간 비교표가 있다', 'function drawHoriz', 'function _drawHoriz'),
        ('i5_per', '화면: 기준마다 실제 구간을 적는다', 'class="per"', 'class="per2"'),
        ('i5_mdd_col', '화면: MDD 를 보여준다', '>MDD</th>', '>낙폭</th>'),
        ('i5_ulcer_def', '화면: Ulcer 설명이 정의문이 아니다', 'id="asof"', 'id="asof" data-x="낙폭의 제곱평균"'),
        ('i5_grade', '화면: 등급표 3종', 'const gUlc', 'const _gUlc'),
        ('i5_time', '화면: 체결 시각이 하나로 통일돼 있다', 'id="asof"', 'id="asof" data-x="09:30~15:00"'),
        ('i5_concentration', '화면: 기여 집중(닷컴)', '급락은 거의 못 피합니다', '급락도 피합니다'),
        ('i5_retired_mix', "화면: 폐기 조합 '배당50/금50' 없음", 'id="asof"', 'id="asof" data-x="배당50/금50"'),
        ('i5_cagr', '화면: 최종배수 옆에 CAGR', '>CAGR</th>', '>연수익</th>'),
        ('i5_rev_mark', '화면: 개정 시점 주입 자리가 있다', "const HTML_REV = '__HTML' + '_REV__';", "const HTML_REV = 'x';"),
        ('i5_rev_div', '화면: 개정 표시가 종가일과 분리돼 있다', 'class="rev" id="htmlRev"', 'class="rev" id="htmlRev2"'),
        ('i5_font', '화면: IBM Plex Mono 참조 없음', 'id="asof"', 'id="asof" data-x="IBM Plex Mono"'),
):
    mut(_id, 'i5_decisions', True, [(_name, 'F')])(_h(_old, _new))


@mut('i5_price', 'i5_decisions', True, [('시세: 화면이 시세를 표시 경로로만 쓴다', 'F')],
     'loadPrice 를 정의·호출 전부 다른 이름으로 — 표시 경로가 통째로 사라진 상태')
def _(r):
    sub(r, 'signal.html', 'loadPrice', 'loadPrize', count=0)


@mut('i5_gcal', 'i5_decisions', True, [('화면: 전략별 심사 줄', 'F')])
def _(r):
    sub(r, 'signal.html', '통상 눈금', '보통 눈금', count=0)


@mut('i5_guide_must', 'i5_decisions', True, [('설명서: 필수 절 존재', 'F')])
def _(r):
    sub(r, 'guide.html', 'id="must"', 'id="must2"')


@mut('i5_guide_count', 'i5_decisions', True, [('설명서: 자동 검증 개수의 낡은 고정 숫자가', 'F')])
def _(r):
    sub(r, 'guide.html', '자동 검증이 잡아내고', '자동 검증 12종이 잡아내고')


@mut('i5_lead_count', 'i5_decisions', True, [('화면: 비교표 각주가 문단으로 끊겨 있다', 'F')],
     '각주 4문단 중 2개를 합친다(lead 2개만 남김)')
def _(r):
    t = read(r, 'signal.html')
    assert t.count('<p><span class="lead">') == 4
    write(r, 'signal.html', t.replace('<p><span class="lead">', '<p><span class="lead2">', 2))


# ---- g_review_context ----
@mut('rc_agents', 'g_review_context', False, [('지침: AGENTS는 최신 CLAUDE 전문을', 'F')])
def _(r):
    sub(r, 'AGENTS.md', '전문', '일부')


@mut('rc_guide_guarantee', 'g_review_context', False, [('설명서: 배율 비교 바로 옆에 기간', 'F')])
def _(r):
    sub(r, 'guide.html', '앞으로도 더 유리하다는 보장은 없습니다.', '앞으로도 더 유리합니다.')


@mut('rc_guide_15x', 'g_review_context', False, [('설명서: 54년 약 15배 성과 문구를', 'F')])
def _(r):
    sub(r, 'guide.html', '</body>', '<p>54년이면 약 15배가 됩니다.</p></body>')


@mut('rc_icon', 'g_review_context', False, [('화면: 세 탭이 배포된 아이콘을 명시한다', 'F')])
def _(r):
    sub(r, 'notes.html', '<link rel="icon" type="image/png" href="icon-192.png">', '')


@mut('rc_isa_label', 'g_review_context', False, [('화면: ISA 수치가 5년 납입형임을 명시한다', 'F')])
def _(r):
    sub(r, 'signal.html', '5년 납입 · 20년 결과', '20년 결과')


@mut('rc_tax_retract', 'g_review_context', False, [('연구 주석: 옛 동률·버블 주장은 같은 줄에', 'F')])
def _(r):
    sub(r, 'research/tax_us_direct.py', '# [철회] QLD 2배 ISA 146.1배', '# QLD 2배 ISA 146.1배')


# ---- g_repo_map ----
@mut('map_new_file', 'g_repo_map', False, [('파일 지도가 실제 파일을 따라잡았다', 'F')])
def _(r):
    write(r, 'deploy/zz_probe_gate.py', '# probe\n')
    git(r, 'add', 'deploy/zz_probe_gate.py')


@mut('map_basename_shadow', 'g_repo_map', False, [('파일 지도가 실제 파일을 따라잡았다', 'F')],
     '★ 기존 파일과 basename 이 같은 새 파일(research/watchdog.py) — FILES.md 산문의 맨 basename 에 무임승차하는가')
def _(r):
    write(r, 'research/watchdog.py', '# probe\n')
    git(r, 'add', 'research/watchdog.py')


@mut('map_stale_toc_04', 'g_toc', False, [('04 목차가 본문 절을 전부 담고 있다', 'F')])
def _(r):
    append(r, '04_Rejected_Research.md', '\n## §9-99. 관문 변별력 시험용 절\n본문.\n')


# ---- g_isolation ----
@mut('iso_write_out', 'g_isolation', False, [('공유용_별도전략 이 본 전략을 오염시키지 않는다', 'F')])
def _(r):
    write(r, '공유용_별도전략/zz_probe.py', "open('data/nav_history.csv', 'w').write('x')\n")


@mut('iso_dotdot', 'g_isolation', False, [('공유용_별도전략 이 본 전략을 오염시키지 않는다', 'F')])
def _(r):
    write(r, '공유용_별도전략/zz_probe.py', "import pandas as pd\npd.DataFrame().to_csv('공유용_별도전략/../data/oos_log.csv')\n")


@mut('iso_deploy_import', 'g_isolation', False, [('공유용_별도전략 이 본 전략을 오염시키지 않는다', 'F')])
def _(r):
    write(r, '공유용_별도전략/zz_probe.py', "from deploy import notify\n")


@mut('iso_dynamic', 'g_isolation', False, [('공유용: 경로가 실행 중 정해지는 쓰기', 'W')])
def _(r):
    write(r, '공유용_별도전략/zz_probe.py', "import sys\nopen(sys.argv[1], 'w').write('x')\n")


# ---- g_notes_lag ----
@mut('notes_claude_ahead', 'g_notes_lag', False, [('업데이트 노트가 최신 버전까지 담고 있다', 'F')])
def _(r):
    sub(r, 'CLAUDE.md', '## 4. 기구현 요약 (중복 제작 금지 — 상세는 signal.html 직접 확인)\n',
        '## 4. 기구현 요약 (중복 제작 금지 — 상세는 signal.html 직접 확인)\n\n- **v999 (시험)**: 노트에 없는 버전.\n')


@mut('notes_claude_ahead_dash', 'g_notes_lag', False, [('업데이트 노트가 최신 버전까지 담고 있다', 'F')],
     '§4 의 다수파 형식 `- v999:` 도 읽는가')
def _(r):
    sub(r, 'CLAUDE.md', '## 4. 기구현 요약 (중복 제작 금지 — 상세는 signal.html 직접 확인)\n',
        '## 4. 기구현 요약 (중복 제작 금지 — 상세는 signal.html 직접 확인)\n\n- v999: 노트에 없는 버전.\n')


@mut('notes_freeze_claim', 'g_notes_lag', False, [('업데이트 노트: 규칙 무변경 선언', 'F')])
def _(r):
    sub(r, 'notes.html', '<b>변경 0회</b>', '<b>변경 1회</b>')


# ---- g_deploy ----
@mut('dep_guide_copy', 'g_deploy', False, [('배포: guide.html 이 Pages 복사 목록에 있다', 'F')],
     '복사 줄을 주석으로만 남긴다 — 주석의 이름으로 통과하면 안 된다')
def _(r):
    sub(r, '.github/workflows/pages.yml', '          cp guide.html _site/guide.html', '          # cp guide.html _site/guide.html')


@mut('dep_ddp_missing', 'g_deploy', False, [('배포: dd_percentile.json 이 만들어지고 복사된다', 'F')])
def _(r):
    remove(r, 'data/dd_percentile.json')


@mut('dep_pwa', 'g_deploy', False, [('배포: PWA 파일이 Pages 복사 목록에 있다', 'F')])
def _(r):
    remove(r, 'icon-512.png')


@mut('dep_monthly_order', 'g_deploy', False, [('배포: 낙폭 백분위가 월간 워크플로에서 갱신된다', 'F')])
def _(r):
    sub(r, '.github/workflows/monthly-stats.yml', 'python3 research/emit_dd_distribution.py', 'python3 research/emit_dd.py')


@mut('dep_monthly_add_dir', 'g_deploy', False, [('배포: 월간 잡은 허용 산출물만 명시적으로 스테이징한다', 'F')])
def _(r):
    sub(r, '.github/workflows/monthly-stats.yml', '          git add -- "${OUTPUTS[@]}"', '          git add data/\n          git add -- "${OUTPUTS[@]}"')


@mut('dep_monthly_rebase', 'g_deploy', False, [('배포: 월간 산출물은 non-fast-forward에 재사용되지 않는다', 'F')])
def _(r):
    sub(r, '.github/workflows/monthly-stats.yml', '          git add -- "${OUTPUTS[@]}"', '          git pull --rebase\n          git add -- "${OUTPUTS[@]}"')


@mut('dep_sigalert_id', 'g_deploy', False, [('배포: 전환 알림 실패가 OOS 기록과 무관하게', 'F')],
     '★ 부분문자열 계열: id 만 sigalertx 로 바뀌고 steps.sigalert 참조가 남으면 이슈가 영원히 안 뜬다 — 5차 전엔 통과')
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', 'id: sigalert\n', 'id: sigalertx\n')


@mut('dep_navlog_id', 'g_deploy', False, [('배포: NAV·OOS 장부 실패가 다음 슬롯 재시도와', 'F')])
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', 'id: navlog\n', 'id: navlogx\n')


@mut('dep_issue_blocking', 'g_deploy', False, [('배포: 실패 이슈 API 장애가 NAV/OOS·신호 커밋을 막지 않는다', 'F')])
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', 'continue-on-error: true   # 이슈 API 장애가', 'continue-on-error: false   # 이슈 API 장애가')


@mut('dep_finalizer', 'g_deploy', False, [('배포: 비차단 보고·토큰 실패가 커밋 뒤 다시', 'F')])
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', 'id: keepalive\n', 'id: keepalivex\n')


@mut('dep_daily_add_dir', 'g_deploy', False, [('배포: 일일 잡도 허용 장부만 스테이징한다', 'F')])
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', '          git add -- data/qqq.csv', '          git add data/\n          git add -- data/qqq.csv')


@mut('dep_daily_rebase', 'g_deploy', False, [('배포: 일일·파수꾼 잡은 경합 때 옛 산출물을', 'F')])
def _(r):
    sub(r, '.github/workflows/watchdog.yml', '          git push', '          git pull --rebase\n          git push')


@mut('dep_reset_gone', 'g_deploy', False, [('배포: 일일 잡은 체크아웃 뒤 최신 main', 'F')])
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', '          git reset --hard origin/main', '          git status')


@mut('dep_dup_exit', 'g_deploy', False, [('배포: 일일 잡은 push 직전 원격이 이미', 'F')])
def _(r):
    sub(r, '.github/workflows/daily-signal.yml', '                exit 0\n', '                true\n')


@mut('dep_token_twice', 'g_deploy', False, [('배포: 회전한 카카오 토큰이 후속 스텝에 유지된다', 'F')],
     '잡 env 밖에서 스텝마다 secret 을 다시 넣으면 회전값이 덮인다')
def _(r):
    sub(r, '.github/workflows/watchdog.yml', '          GH_PAT: ${{ secrets.GH_PAT }}\n',
        '          GH_PAT: ${{ secrets.GH_PAT }}\n          KAKAO_REFRESH_TOKEN: ${{ secrets.KAKAO_REFRESH_TOKEN }}\n')


@mut('dep_pat_missing', 'g_deploy', False, [('배포: 토큰을 회전할 수 있는 모든 호출에 GH_PAT가 전달된다', 'F')])
def _(r):
    t = read(r, '.github/workflows/watchdog.yml')
    i = t.rfind('          GH_PAT: ${{ secrets.GH_PAT }}\n')
    assert i > 0
    write(r, '.github/workflows/watchdog.yml', t[:i] + t[i + len('          GH_PAT: ${{ secrets.GH_PAT }}\n'):])


@mut('dep_price_cron', 'g_deploy', False, [('배포: 개장 전 시세 폴러가 KST 월~금', 'F')])
def _(r):
    sub(r, '.github/workflows/price.yml', "cron: '30,40,50 23 * * 0-4'", "cron: '30,40,50 23 * * 1-5'")


@mut('dep_fred_url', 'g_deploy', False, [('배포: DEXKOUS 주 공급원은 실제 FRED CSV', 'F')])
def _(r):
    sub(r, 'deploy/refresh_hist.py', 'fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS', 'fred.stlouisfed.org/graphs/fredgraph.csv?id=DEXKOUS')


@mut('dep_pages_conclusion', 'g_deploy', False, [('배포: 일일 잡이 커밋 뒤 실패해도 최신', 'F')])
def _(r):
    sub(r, '.github/workflows/pages.yml', '  workflow_run:', "  workflow_run:\n    # if: github.event.workflow_run.conclusion == 'success'")


# ---- g_signal_coupling ----
@mut('cpl_price_in_signal', 'g_signal_coupling', False, [('시세: 신호 생성이 price.json 을 읽지 않는다', 'F')])
def _(r):
    append(r, 'deploy/update_signal.py', "\n_PRICE = 'data/price.json'\n")


@mut('cpl_kr_sources_in_judge', 'g_signal_coupling', False, [('시세: 가격 표시·KOSPI 원자료만 예비 체인을 쓰고', 'F')])
def _(r):
    append(r, 'deploy/wait_close.py', "\nimport kr_sources\n")


@mut('cpl_nav_core', 'g_signal_coupling', False, [('NAV: 핵심 4종 완전 수집', 'F')])
def _(r):
    sub(r, 'deploy/nav_collect.py', 'CORE_CODES', 'CORE_CODE', count=0)


@mut('cpl_nav_open', 'g_signal_coupling', False, [('NAV: 한국장 개장 중에는 적립하지 않는다', 'F')])
def _(r):
    sub(r, 'deploy/nav_collect.py', 'def kr_market_open', 'def kr_market_is_open')


# ---- g_watchdog ----
@mut('wd_mode_missing', 'g_watchdog', False, [('파수꾼: 전환 실행일 재알림·근접 진입 알림이 모드와 스텝 양쪽에', 'F')])
def _(r):
    sub(r, 'deploy/watchdog.py', "'near': mode_near", "'near2': mode_near")


@mut('wd_step_missing', 'g_watchdog', False, [('파수꾼: 전환 실행일 재알림·근접 진입 알림이 모드와 스텝 양쪽에', 'F')],
     '★ 부분문자열 계열: `watchdog.py near2` 가 `watchdog.py near` 를 포함한다 — 5차 전엔 통과')
def _(r):
    sub(r, '.github/workflows/watchdog.yml', 'watchdog.py near', 'watchdog.py near2')


@mut('wd_hol_commit', 'g_watchdog', False, [('파수꾼: 휴장일 표가 매주 자동 연장된다', 'F')])
def _(r):
    sub(r, '.github/workflows/watchdog.yml', 'git add data/ops_check.json data/kr_holidays.json', 'git add data/ops_check.json')


@mut('wd_hol_minday', 'g_watchdog', False, [('파수꾼: 휴장일 표가 매주 자동 연장된다', 'F')])
def _(r):
    sub(r, 'deploy/kr_holidays.py', 'MIN_DAYS_PER_YEAR', 'MIN_DAYS_YEAR', count=0)



# ---- [2026-09-06 · 6차] 자료 의존 관문 I1·I5·I10 — 격리 클론의 원자료를 합성 계열로 바꿔 「실패해야 할 때 실패하는가」 ----
#   계약(관문이 재는 것): I1 = 엔진 동치(run==sim · 세율0 축퇴 · 회계 장난감 · 적립 항등식 · 단일자산 sim_hold==sim_def)
#                        I5 = 채택 결정이 지금 자료로도 같은가(B>A · 원화 20년창 좌측꼬리 40/40/20>배당100 · 미국 종가>원화환산)
#                        I10 = 전제(2배 보유 MDD ≤ −90% · 최근 20년 CAGR > 3% · 전략 > 2배 보유)
#   ⚠ 실제 원자료·동결값·장부는 건드리지 않는다 — 클론 안의 사본만 바꾼다. 새 규칙을 관문에 넣지 않는다.
def _synth_prices(root, ret_fn):
    """세 가격 원자료(FRED 종합 1971~ · 야후 NDX 1985~ · QQQ 1999~)의 **날짜는 그대로** 두고 종가만 합성한다.
    엔진(hist_data.qqq_proxy)은 세 파일을 일간수익률로 접합하므로 파일마다 같은 ret_fn 을 자기 날짜에 적용하면 된다."""
    import pandas as pd, numpy as np
    for rel, dcol, vcol in (('data/hist/fred_NASDAQCOM.csv', 'observation_date', 'NASDAQCOM'),
                            ('data/hist/yahoo_NDX.csv', 'Date', 'Close'),
                            ('qqq_us_d.csv', 'Date', 'Close')):
        d = pd.read_csv(_p(root, rel))
        dates = pd.to_datetime(d[dcol])
        n = len(d); px = np.empty(n); px[0] = 100.0
        for i in range(1, n):
            px[i] = px[i - 1] * (1.0 + ret_fn(i, n, dates.iloc[i]))
        d[vcol] = np.round(px, 6)
        if rel == 'qqq_us_d.csv':
            for c in ('Open', 'High', 'Low'):
                d[c] = d[vcol]
        d.to_csv(_p(root, rel), index=False)


def _growth(i, n, dt):                       # 폭락 없는 완만한 상승(연 ≈ 16% · σ 6%) — 2배 보유가 안 무너지고 전환도 안 생긴다
    import numpy as np
    rng = _growth.rng
    return 0.0006 + rng.normal(0.0, 0.004)


def _flat20(i, n, dt):                       # 2006-08 까지 상승, 그 뒤 20년은 평균 0(횡보)
    import numpy as np
    return _growth(i, n, dt) if dt < __import__('pandas').Timestamp('2006-08-01') else _flat20.rng.normal(0.0, 0.004)


def _sawtooth(i, n, dt):                     # 20일 +1.0% / 40일 −0.6% — 첫 −16 뒤 B 는 −13 에서 재진입해 다시 맞고, A(−11 복귀)는 밖에 머문다
    return 0.010 if (i % 60) < 20 else -0.006


@mut('data_growth_i10', 'i10_premise', True,
     [('P1 2배 보유 MDD', 'F'), ('P3 전략이 2배 그냥 보유를 이긴다', 'F')],
     '폭락 없는 합성 계열: 2배 보유 MDD 가 얕고(P1) 전환이 없어 전략=보유(P3) — 나스닥 고유 성질이 사라진 세계')
def _(r):
    import numpy as np
    _growth.rng = np.random.default_rng(1)
    _synth_prices(r, _growth)


@mut('data_flat20_i10', 'i10_premise', True, [('P2 기초지수 최근 20년 연평균 상승', 'F')],
     '최근 20년 횡보 합성 계열 — 지킬 상승이 없다(P2)')
def _(r):
    import numpy as np
    _growth.rng = np.random.default_rng(2); _flat20.rng = np.random.default_rng(3)
    _synth_prices(r, _flat20)


@mut('data_growth_i5', 'i5_decisions', True, [('B(-16/-16) > A(-16/-11)', 'F')],
     '전환이 한 번도 없으면 B 와 A 가 같아 「B>A」가 성립하지 않는다 — 채택 결정의 근거가 자료에서 사라진 경우')
def _(r):
    import numpy as np
    _growth.rng = np.random.default_rng(1)
    _synth_prices(r, _growth)


@mut('data_sawtooth_i5', 'i5_decisions', True, [('B(-16/-16) > A(-16/-11)', 'F')],
     '톱니 합성 계열: B 는 −16 을 넘나들며 왕복 손실, A 는 −11 복귀선 밖에 머문다 → A>B')
def _(r):
    _synth_prices(r, _sawtooth)


@mut('data_fx_flat_i5', 'i5_decisions', True, [('신호원: 미국 종가 > 원화환산', 'F')],
     '환율을 상수로 — 원화환산 신호와 미국 종가 신호가 같아져 「미국 종가 > 원화환산 ×2」가 성립하지 않는다')
def _(r):
    import pandas as pd
    d = pd.read_csv(_p(r, 'data/hist/fred_DEXKOUS.csv'))
    d['DEXKOUS'] = 1000.0
    d.to_csv(_p(r, 'data/hist/fred_DEXKOUS.csv'), index=False)


@mut('data_gold_collapse_i5', 'i5_decisions', True, [('[원화] 20년창 좌측꼬리 40/40/20 > 배당100', 'F')],
     '금 다리를 1981 부터 연 −25% 로 무너뜨리면 40/40/20 의 최악 20년창이 배당100 아래로 내려간다. '
     '(첫 시도 — SCHD 2011~ 를 연 50% 로 부풀린 변조는 못 뒤집었다: 5분위를 정하는 최악 창들이 2011 이전에 끝나 부풀림이 닿지 않는다. '
     '관문 결함이 아니라 변조가 5분위 창을 안 건드린 것 — 그대로 적는다)')
def _(r):
    import pandas as pd, numpy as np
    d = pd.read_csv(_p(r, 'data/hist/lbma_gold_pm.csv'))
    dt = pd.to_datetime(d['Date'])
    k = np.clip((dt - pd.Timestamp('1981-01-01')).dt.days.values / 365.25, 0, None)
    d['Close'] = d['Close'].values * (0.75 ** k)
    d.to_csv(_p(r, 'data/hist/lbma_gold_pm.csv'), index=False)


# ---- I1 엔진 동치 — 관문이 재는 회계·동치 결함 ----
@mut('i1_sim_cost_double', 'i1_engine', False, [('axis_lib.check', 'F')],
     'sim 의 전환 비용을 2배로 — run(reentry_lib) 과 갈린다')
def _(r):
    sub(r, 'axis_lib.py', 'curve = pd.Series(np.cumprod((1 + r) * (1 - cost * turn)), index=idx[sl])',
        'curve = pd.Series(np.cumprod((1 + r) * (1 - 2 * cost * turn)), index=idx[sl])')


@mut('i1_withdraw_basis', 'i1_engine', False, [('axis_lib.check', 'F')],
     '세금 마련 매도에서 원가를 안 빼면(2차 실현손익 소실) 회계 장난감이 어긋난다')
def _(r):
    sub(r, 'axis_lib.py', '    basis_sold = B * (tax / V)\n', '    basis_sold = 0.0\n')


@mut('i1_accum_buycost', 'i1_engine', False, [('axis_lib.check', 'F')],
     '적립 매수비용 기본값 0 → 0.1%: accumulate 가 Σ 납입일별 거치식 배수 항등식에서 벗어난다')
def _(r):
    sub(r, 'axis_lib.py', 'rk=None, buy_cost=0.0, return_paths=False):', 'rk=None, buy_cost=0.001, return_paths=False):')


@mut('i1_hold_rebal_blind', 'i1_engine', False, [('axis_defmix.check_hold', 'F')],
     '★ 사각지대: sim_hold 의 **다자산 재조정 비용**을 2배로 — check_hold 는 단일자산(재조정 0)만 sim_def 와 대조하므로 못 본다',
     blind=True)
def _(r):
    sub(r, 'axis_defmix.py', 'V *= (1 - rebal_cost * 2 * turn)', 'V *= (1 - rebal_cost * 4 * turn)')


# ------------------------------------------------------------------ 실행기
TAKES_D = {'i2_pit', 'i3_lag', 'i4_real', 'i5_decisions', 'i7_stats', 'i10_premise'}

RUN_SNIPPET = r'''
import sys, json, io
try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import verify_all as V
gate, need_d = sys.argv[1], sys.argv[2] == "1"
D = None
if need_d or gate == "i1_engine":
    D = V.i1_engine()
if gate != "i1_engine":
    V.FAIL.clear(); V.WARN.clear()
    fn = getattr(V, gate)
    fn(D) if gate in %r else fn()
print("@@RESULT@@" + json.dumps({"F": V.FAIL, "W": V.WARN}, ensure_ascii=False))
''' % (sorted(TAKES_D),)


def run_gate(root, gate, need_d):
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    r = subprocess.run([PY, '-c', RUN_SNIPPET, gate, '1' if need_d else '0'], cwd=root,
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       timeout=600, env=env)
    for ln in r.stdout.splitlines():
        if ln.startswith('@@RESULT@@'):
            return json.loads(ln[len('@@RESULT@@'):]), r
    return None, r


def make_clone(dst):
    subprocess.run(['git', 'clone', '-q', '--local', '--no-hardlinks', ROOT, dst],
                   check=True, capture_output=True)
    git(dst, 'config', 'user.email', 'gate@probe')
    git(dst, 'config', 'user.name', 'gate-probe')


def restore(root):
    git(root, 'reset', '-q', '--hard')
    git(root, 'clean', '-fdq')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='변조 id 접두어(쉼표로 여러 개)')
    ap.add_argument('--verify', default='', help='클론에 넣을 다른 verify_all.py (옛 사본 대조용)')
    ap.add_argument('--no-runner', action='store_true', help='실행기 검사(종료코드·크래시 격리) 생략')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--keep', action='store_true', help='임시 클론을 남긴다')
    a = ap.parse_args()
    pre = [x for x in a.only.split(',') if x]
    sel = [m for m in M if not pre or any(m[0].startswith(x) for x in pre)]
    if a.list:
        for m in sel:
            print('%-26s %-18s %s%s' % (m[0], m[1], '; '.join(n for n, _ in m[3]), ' [blind]' if m[6] else ''))
        return 0
    tmp = tempfile.mkdtemp(prefix='gate_mut_')
    root = os.path.join(tmp, 'clone')
    t0 = time.time()
    make_clone(root)
    # ★ git clone 은 **커밋된 HEAD** 를 준다 — 작업본에서 고친(미커밋) 파일은 따로 옮겨야 한다.
    #   첫 실행에서 이것을 빠뜨려 고친 verify_all 대신 옛 것을 재고 있었다(5차 실측).
    import shutil as _sh
    changed = [ln[3:].strip().strip('"') for ln in
               git(ROOT, 'status', '--porcelain', '--untracked-files=no').stdout.splitlines()
               if ln[:2].strip() and not ln.startswith('D ') and not ln.startswith(' D')]
    for rel in changed:
        _sh.copy(os.path.join(ROOT, rel), _p(root, rel))
    if a.verify:
        _sh.copy(a.verify, os.path.join(root, 'verify_all.py'))
    git(root, 'add', '-A', '.')
    git(root, 'commit', '-q', '--allow-empty', '-m', 'probe: working copy')
    print('클론 %s (%.1f초 · 작업본 반영 %d파일%s)' % (root, time.time() - t0, len(changed),
                                                ' · verify_all 대체' if a.verify else ''))
    # 기준선 — 변조 없이 관문마다 통과해야 변조 결과를 읽을 수 있다
    gates = sorted({(m[1], m[2]) for m in sel})
    base_bad = []
    for g, nd in gates:
        res, r = run_gate(root, g, nd)
        if res is None:
            base_bad.append('%s: 결과 없음 %s' % (g, r.stderr[-300:]))
        elif res['F']:
            base_bad.append('%s: 기준선 FAIL %s' % (g, res['F']))
    if base_bad:
        print('기준선이 깨끗하지 않다 — 변조 판정 불가:\n  ' + '\n  '.join(base_bad))
        return 2
    print('기준선 관문 %d개 전부 PASS (%.0f초)' % (len(gates), time.time() - t0))
    rows = []
    for id_, gate, need_d, expect, fn, why, blind in sel:
        t1 = time.time()
        try:
            fn(root)
        except Exception as e:
            rows.append((id_, gate, 'HARNESS', '변조 실패 %s: %s' % (type(e).__name__, e)))
            restore(root)
            continue
        res, r = run_gate(root, gate, need_d)
        restore(root)
        if res is None:
            rows.append((id_, gate, 'CRASH', (r.stderr.strip().splitlines() or ['?'])[-1][:160]))
            continue
        missed = []
        for name, kind in expect:
            pool = res['F'] if kind == 'F' else res['W']
            if not any(name in x for x in pool):
                missed.append('%s(%s)' % (name, kind))
        extra = [x for x in res['F'] if not any(n in x for n, _ in expect)]
        verdict = 'CAUGHT' if not missed else ('BLIND' if blind else 'MISSED')
        rows.append((id_, gate, verdict,
                     ('못 잡음: ' + '; '.join(missed)) if missed
                     else ('연쇄 FAIL %d' % len(extra) if extra else '') , round(time.time() - t1, 1)))
    # ---- 실행기 자체: ① 실패 1건이면 종료코드 1 ② 한 관문이 예외로 죽어도 뒤 관문이 돈다
    if not a.no_runner:
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        sub(root, 'signal.html', 'const LOOKBACK = 252;', 'const LOOKBACK = 200;')
        r1 = subprocess.run([PY, 'verify_all.py', '--fast'], cwd=root, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=900, env=env)
        restore(root)
        ok1 = r1.returncode == 1 and '실패 1건' in r1.stdout and '화면 룩백이 동결값과 같다' in r1.stdout
        rows.append(('runner_exit_code', 'main', 'CAUGHT' if ok1 else 'MISSED',
                     'rc=%d' % r1.returncode + ('' if ok1 else ' — 실패 1건·종료코드 1 이어야 한다')))
        write(root, 'data/strategy_stats.json', 'not json')
        r2 = subprocess.run([PY, 'verify_all.py', '--fast'], cwd=root, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=900, env=env)
        restore(root)
        ok2 = (r2.returncode == 1 and '예외로 중단됐다' in r2.stdout
               and '[PASS] 공용 모형 8종이 봉인과 같다' in r2.stdout
               and '파일 지도가 실제 파일을 따라잡았다' in r2.stdout)
        rows.append(('runner_crash_isolation', 'main', 'CAUGHT' if ok2 else 'MISSED',
                     'rc=%d' % r2.returncode + ('' if ok2 else ' — 예외 관문은 FAIL 로, 뒤 관문(I8·g_*)은 계속 돌아야 한다')))
    print('\n%-26s %-18s %-7s %s' % ('변조', '관문', '판정', '비고'))
    for row in rows:
        print('%-26s %-18s %-7s %s' % (row[0], row[1], row[2], row[3]))
    n_c = sum(1 for x in rows if x[2] == 'CAUGHT')
    n_b = sum(1 for x in rows if x[2] == 'BLIND')
    n_m = [x for x in rows if x[2] not in ('CAUGHT', 'BLIND')]
    print('\n변조 %d개 · 잡힘 %d · 사각지대(문서화) %d · 못 잡음/오류 %d · %.0f초' % (len(rows), n_c, n_b, len(n_m), time.time() - t0))
    for x in n_m:
        print('  ✗ %s (%s) — %s' % (x[0], x[1], x[3]))
    if not a.keep:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return 1 if n_m else 0


if __name__ == '__main__':
    sys.exit(main())
