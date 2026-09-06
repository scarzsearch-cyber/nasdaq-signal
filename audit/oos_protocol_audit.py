# -*- coding: utf-8 -*-
"""B 판정 규약 평가기(research/oos_protocol_b.py --oos) 독립 규약 검증 도구 (2026-09-06 · 검사 권한만 · CI 미등재).

무엇을 하나
  evaluate_oos(D) 에 **합성 D**(idx·w·B·H)를 넣어, 등록 규약(data/oos_protocol_b.json · 02 §5-1)이 말하는 대로
  판정하는지 본다. 기대값은 규약 문구와 JSON 수치에서 손으로 계산했고 평가기의 식을 복사하지 않았다.
  평가기·규약·등록값·실측 장부·CI 를 바꾸지 않는다. 지문 불일치 검사만 임시 사본 파일로 PROTO 를 잠시 돌린 뒤 되돌린다.
  결과 장부: audit/OOS_PROTOCOL_2026-09-06.md.

합성 D 의 규약 (손계산이 되게)
  idx  영업일. JSON 의 oos_start(동결일)가 idx 안에 있고 그 위치가 i0.
  B·H  **수준(level)** 배열 — 사건창 밖은 1.0. 사건 i 의 창(lo=i−63 … hi=i+252)은 (lo..i) 1.0 → (i+1..hi−1) 바닥 → (hi) 끝값.
       창 시작 B[lo]=H[lo]=1.0 이라 정규화가 정확하고, 끝값을 1.0 으로 두면 「사건창 B/H−1」= B 끝값 − 1 이다.
       MDD = 바닥 − 1 (끝값 ≥ 바닥일 때).
  w    기본 1 · 사건 i 부터 dur 일 동안 0 (그 다음 날 1 로 복귀).
  역사 독립 사건 20건(간격 400일 > 252) — 재난(H MDD ≤ −50%) 8건 전부 B 가 얕음 → A 8/8 · 보험료 최저 2건 −0.293 → P05 −0.293
  (np.percentile 선형 보간: 20건의 5% 위치는 0.95 로 최저 두 값 사이) → 평가기의 기저율 자기검산이 등록값과 일치.

실행  python audit/oos_protocol_audit.py [--root <repo>] [--engine]
  --engine  실제 엔진 D(load) 로 ① 기준 출력 ② 등록값 독립 재계산 ③ 등록 전후(창 미충족 역사 사건) 노출
            ④ 장부↔엔진 도피일 대조 ⑤ 실제 역사 + 합성 OOS 구간 검사. 엔진 검산에 수십 초.
종료코드  0 = 기대와 전부 일치 · 1 = 불일치 있음. 「규약 모호」 표시는 코드 동작을 기대값으로 두고 장부에 분류만 남긴다.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.dirname(HERE)
GAP_HIST = 400          # 역사 사건 간격(> 252 → 전부 독립)
N_HIST = 20
I_FREEZE = 63 + N_HIST * GAP_HIST + 300   # 동결일 위치 (마지막 역사 창이 끝나고 여유 300일)


def load_module(root):
    p = os.path.join(root, 'research', 'oos_protocol_b.py')
    spec = importlib.util.spec_from_file_location('oos_protocol_b_under_audit', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)            # 모듈은 import 시 자기 저장소 루트로 chdir 한다
    return m


def run_eval(m, D):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = m.evaluate_oos(D)
    return rc, buf.getvalue()


def verdict_line(out):
    mm = re.search(r'판정: (.*)', out)
    return mm.group(1).strip() if mm else None


def event_lines(out):
    return [ln.strip() for ln in out.splitlines() if ln.strip().startswith('· ')]


# ---------------------------------------------------------------- 합성 D
class Synth:
    """역사 20건 + OOS 사건/R 일정으로 D 를 만든다. 사건은 (offset, mdd_h, mdd_b, prem, dur) — offset 은 i0 기준 거래일."""

    def __init__(self, m, freeze, n_post, hist_events=None, oos_events=(), pre_events=(), b_schedule=(),
                 drop_freeze_day=False, w0_defense=0, levels=(), w_zero=()):
        self.m = m
        pre = pd.bdate_range(end=freeze - pd.Timedelta(days=1), periods=I_FREEZE)
        post = pd.bdate_range(start=freeze, periods=n_post + (1 if drop_freeze_day else 0))
        if drop_freeze_day:
            post = post[1:]
        self.idx = pre.append(post)
        self.n = len(self.idx)
        self.i0 = int(np.searchsorted(self.idx.values, np.datetime64(freeze)))
        self.B = np.ones(self.n)
        self.H = np.ones(self.n)
        self.w = np.ones(self.n)
        if w0_defense:
            self.w[:w0_defense] = 0.0
        self.events = []
        hist = hist_events if hist_events is not None else self.default_history()
        for (i, mh, mb, pr, dur) in hist:
            self.put(i, mh, mb, pr, dur)
        for (off, mh, mb, pr, dur) in pre_events:
            self.put(self.i0 + off, mh, mb, pr, dur)
        for (off, mh, mb, pr, dur) in oos_events:
            self.put(self.i0 + off, mh, mb, pr, dur)
        for (off_a, off_b, level) in b_schedule:            # B 수준을 [i0+off_a, i0+off_b) 에 덮어쓴다 (H 는 1)
            self.B[self.i0 + off_a:self.i0 + off_b] = level
        for (off_a, off_b, lvB, lvH) in levels:              # 겹치는 창(종속 사건)은 수준을 직접 그린다
            self.B[self.i0 + off_a:self.i0 + off_b] = lvB
            self.H[self.i0 + off_a:self.i0 + off_b] = lvH
        for (off_a, off_b) in w_zero:
            self.w[self.i0 + off_a:self.i0 + off_b] = 0.0

    @staticmethod
    def default_history():
        ev = []
        for k in range(N_HIST):
            i = 63 + k * GAP_HIST
            if k < 8:                       # 재난 8건 — A 통과 (B 가 얕다)
                ev.append((i, -0.55, -0.40, -0.10, 100))
            elif k < 10:                    # 보험료 최저 2건 = −0.293 → P05 −0.293
                ev.append((i, -0.30, -0.20, -0.293, 100))
            else:
                ev.append((i, -0.30, -0.20, -0.05 + 0.01 * (k - 10), 100))
        return ev

    def put(self, i, mdd_h, mdd_b, prem, dur, h_end=1.0):
        PRE, POST = self.m.PRE, self.m.POST
        n = self.n
        hi = i + POST
        assert 0 <= i - PRE and i < n, ('사건 위치', i, n)
        self.H[i + 1:min(hi, n)] = 1.0 + mdd_h
        self.B[i + 1:min(hi, n)] = 1.0 + mdd_b
        if hi < n:
            self.H[hi] = h_end
            self.B[hi] = (1.0 + prem) * h_end
        self.w[i:min(i + dur, n)] = 0.0
        self.events.append(dict(i=i, date=self.idx[i].date()))

    def D(self):
        return dict(idx=self.idx, w=self.w.copy(), B=self.B.copy(), H=self.H.copy())


# ---------------------------------------------------------------- 검사 항목
class Report:
    def __init__(self):
        self.rows = []

    def add(self, case, desc, ok, actual='', note=''):
        self.rows.append((case, desc, bool(ok), actual, note))
        print(('  OK   ' if ok else '  DIFF ') + f'[{case}] {desc}' + (f' — {actual}' if actual else '') + (f'  ※ {note}' if note else ''))

    def summary(self):
        bad = [r for r in self.rows if not r[2]]
        print(f'\n합계 {len(self.rows)} 검사 · 불일치 {len(bad)}')
        return 0 if not bad else 1


def synthetic_cases(m, R, freeze, P):
    gB, gR = P['gates']['B_premium'], P['gates']['R_rolling_3y']
    warnB, outB = gB['warn_below'], gB['outside_history_below']
    warnR, outR = gR['warn_below'], gR['outside_history_below']
    Y3 = 3 * m.Y

    def go(**kw):
        S = Synth(m, freeze, **kw)
        rc, out = run_eval(m, S.D())
        return S, rc, out

    # C00 기준 — 사건 0 · R 불가
    S, rc, out = go(n_post=300)
    R.add('C00', '사건 0 · 자기검산 통과 · rc 0', rc == 0 and '동결 이후 도피 사건 0건' in out and '판정 중단' not in out, f'rc={rc}')
    R.add('C00', '「판정 불가 — 정상」 + 「재검토 사유 없음 (판정 사건 0건)」', '판정 불가 — 정상' in out and verdict_line(out) == '재검토 사유 없음 (판정 사건 0건)', verdict_line(out))
    R.add('C00', 'R 계산 불가 — 동결 뒤 299거래일 (n−1−i0)', 'R 계산 불가 — 동결 뒤 299거래일' in out)
    R.add('C00', '파수꾼 파서 호환(사건 수 정규식 · ok 조건 문구)', re.search(r'동결 이후 도피 사건 (\d+)건', out) is not None and '판정: 재검토 사유 없음' in out)

    # C01~C04 A 재난 지급 경계
    S, rc, out = go(n_post=400, oos_events=[(70, -0.50, -0.40, -0.10, 100)])
    ln = event_lines(out)
    R.add('C01', 'H 창 MDD = −50.0% 정확히 → A 적용(≤) · 통과 · [독립]', len(ln) == 1 and 'A 재난 지급 통과' in ln[0] and '[독립]' in ln[0] and rc == 0, ln[0] if ln else out[-200:])
    R.add('C01', '판정 「재검토 사유 없음」(사건 0건 꼬리 없음)', verdict_line(out) == '재검토 사유 없음', verdict_line(out))
    S, rc, out = go(n_post=400, oos_events=[(70, -0.50 + 1e-6, -0.40, -0.10, 100)])
    ln = event_lines(out)
    R.add('C02', 'H 창 MDD = −50%+1e-6 → A 해당 없음', len(ln) == 1 and 'A 해당 없음' in ln[0], ln[0] if ln else '')
    S, rc, out = go(n_post=400, oos_events=[(70, -0.55, -0.55, -0.10, 100)])
    ln = event_lines(out)
    R.add('C03', 'B MDD == H MDD(동률) → A 실패(엄격 >) · ★역사 밖 · rc 1', len(ln) == 1 and '★역사 밖' in ln[0] and rc == 1, ln[0] if ln else '')
    R.add('C03', '판정 「역사 밖 — 재검토 연구 개시 (<날짜> A)」', (verdict_line(out) or '').startswith('**역사 밖 — 재검토 연구 개시** (') and ' A)' in (verdict_line(out) or ''), verdict_line(out))
    S, rc, out = go(n_post=400, oos_events=[(70, -0.55, -0.55 + 1e-6, -0.10, 100)])
    ln = event_lines(out)
    R.add('C04', 'B 가 1e-6 얕음 → A 통과', len(ln) == 1 and 'A 재난 지급 통과' in ln[0] and rc == 0, ln[0] if ln else '')

    # C05 종속 사건의 A 실패 — 창이 겹치므로 수준을 직접 그린다(전부 이진 정확값)
    #   H 1.0 → 0.375(i1+1) → 0.1875(i2+1) · B 1.0 → 0.5 → 0.25. 창1(lo1 기준): H MDD −0.8125 · B −0.75 → A 통과.
    #   창2(lo2=i2−63 · H 0.375 · B 0.5 기준): 둘 다 비율 0.5 → MDD −0.5 == −0.5 → A 적용(≤) · 동률 → 실패.
    S, rc, out = go(n_post=500, levels=[(71, 171, 0.5, 0.375), (171, 500, 0.25, 0.1875)], w_zero=[(70, 100), (170, 200)])
    ln = event_lines(out)
    dep_line = ln[1] if len(ln) == 2 else ''
    R.add('C05', '종속 사건(간격 100) 의 A 실패: 첫째 [독립] 통과 · 둘째 [종속] 줄에는 ★역사 밖 · 판정에는 미반영 · rc 0',
          len(ln) == 2 and 'A 재난 지급 통과' in ln[0] and '[종속]' in dep_line and 'A 재난 지급 ★역사 밖' in dep_line and rc == 0 and verdict_line(out) == '재검토 사유 없음',
          f'{dep_line} | 판정 {verdict_line(out)}',
          note='규약 모호 — A 는 독립 사건 기준(8/8)이라 종속 사건을 판정에서 빼는 것은 규약과 맞지만, 줄 문구가 「★역사 밖」이라 파수꾼 라인·사람 읽기가 어긋난다')

    # C06~C09 B 보험료 경계
    for tag, pr, want, want_rc in (('C06', warnB + 1e-6, '정상', 0), ('C07', warnB - 1e-6, '주의', 0),
                                   ('C08', outB + 1e-6, '주의', 0), ('C09', outB - 1e-6, '★역사 밖', 1)):
        S, rc, out = go(n_post=400, oos_events=[(70, -0.30, -0.25, pr, 100)])
        ln = event_lines(out)
        okv = (verdict_line(out) or '')
        if want == '정상':
            okvv = okv == '재검토 사유 없음'
        elif want == '주의':
            okvv = okv.startswith('주의 (') and ' B)' in okv and '기록·알림만' in okv
        else:
            okvv = okv.startswith('**역사 밖') and ' B)' in okv
        R.add(tag, f'보험료 {pr:+.7f} → B {want} · rc {want_rc}', len(ln) == 1 and f'B 보험료 {want}' in ln[0] and rc == want_rc and okvv, f'{ln[0] if ln else ""} | 판정 {okv}')
    # 정확히 경계값 — 정보용(부동소수점에 달렸다)
    for tag, pr in (('C06x', warnB), ('C08x', outB)):
        S, rc, out = go(n_post=400, oos_events=[(70, -0.30, -0.25, pr, 100)])
        ln = event_lines(out)
        side = re.search(r'B 보험료 (\S+)', ln[0]).group(1) if ln else '?'
        R.add(tag, f'보험료 = {pr} 정확히(정보용 · 규약은 「<」) → 관측 {side}', True, ln[0] if ln else '', note='동률 판정은 부동소수점에 달렸다 — 규약 경계는 ±1e-6 케이스로 확정')

    # C11~C12 창 미충족 경계
    S, rc, out = go(n_post=70 + 252, oos_events=[(70, -0.55, -0.55, -0.60, 100)])        # hi == n → 미충족
    ln = event_lines(out)
    R.add('C11', 'i+252 == n → 창 미충족 · 판정 보류 · 역사 밖 자료 무시 · rc 0', len(ln) == 1 and '창 미충족' in ln[0] and rc == 0 and verdict_line(out) == '재검토 사유 없음' and '동결 이후 도피 사건 1건' in out, f'{ln[0] if ln else ""} | 판정 {verdict_line(out)}',
          note='표시 — 파수꾼은 「사건 1건 — 재검토 사유 없음」(ok) 으로 읽는다: 보류 사건도 「사건 N건」에 든다')
    S, rc, out = go(n_post=70 + 253, oos_events=[(70, -0.55, -0.55, -0.60, 100)])        # hi == n−1 → 충족
    ln = event_lines(out)
    R.add('C12', 'i+252 == n−1 → 판정 · A 실패 → rc 1', len(ln) == 1 and '창 미충족' not in ln[0] and '★역사 밖' in ln[0] and rc == 1, ln[0] if ln else '')

    # C13~C14 독립 간격
    S, rc, out = go(n_post=700, oos_events=[(70, -0.30, -0.25, -0.05, 30), (70 + 252, -0.30, -0.25, -0.05, 30)])
    ln = event_lines(out)
    R.add('C13', '간격 = 252 → 둘째 [종속] (초과만 독립)', len(ln) == 2 and '[독립]' in ln[0] and '[종속]' in ln[1], ' / '.join(x[:24] for x in ln))
    S, rc, out = go(n_post=700, oos_events=[(70, -0.30, -0.25, -0.05, 30), (70 + 253, -0.30, -0.25, -0.05, 30)])
    ln = event_lines(out)
    R.add('C13', '간격 = 253 → 둘째 [독립]', len(ln) == 2 and '[독립]' in ln[1], ' / '.join(x[:24] for x in ln))
    S, rc, out = go(n_post=900, oos_events=[(70, -0.30, -0.25, -0.05, 30), (270, -0.30, -0.25, -0.05, 30), (470, -0.30, -0.25, -0.05, 30)])
    ln = event_lines(out)
    R.add('C14', '연쇄 0·200·400 → 셋째 [종속] (직전 도피 기준 · 첫째와는 400)', len(ln) == 3 and '[종속]' in ln[1] and '[종속]' in ln[2], ' / '.join(x[:24] for x in ln))

    # C15~C16 등록 전후 — 동결 직전 사건
    S, rc, out = go(n_post=300, pre_events=[(-100, -0.55, -0.55, -0.10, 30)])
    R.add('C15', '동결 100일 전 재난 A 실패 사건 — 등록 때는 창 미충족(미포함) · 자료가 자라 창이 차면 역사에 편입 → 자기검산 「판정 중단」 rc 2',
          rc == 2 and '판정 중단' in out and 'A 독립 8/9' in out, re.search(r'기저율 자기검산: [^\n]*', out).group(0) if '자기검산' in out else out[-200:],
          note='규약 모호 — 등록 시점에 창이 안 찬 동결 이전 사건은 등록값(8/8 · 69건)에 없는데, 평가기의 「역사」는 날짜 < 동결 전부라 나중에 편입된다. 실제 자료 노출은 --engine E2')
    S, rc, out = go(n_post=100, pre_events=[(-100, -0.55, -0.55, -0.10, 30)])
    R.add('C15', '같은 사건 · 자료가 아직 창을 못 채움(n_post 100) → 자기검산 통과 · OOS 0건', rc == 0 and '동결 이후 도피 사건 0건' in out and '판정 중단' not in out, f'rc={rc}')
    S, rc, out = go(n_post=400, oos_events=[(0, -0.30, -0.25, -0.05, 30)])
    R.add('C16', '동결일 당일 도피 → OOS 사건(≥)', '동결 이후 도피 사건 1건' in out and rc == 0)
    S, rc, out = go(n_post=400, pre_events=[(-1, -0.30, -0.25, -0.05, 30)])
    R.add('C16', '동결 전날 도피 → OOS 0건 · 창이 차면 역사 편입(보험료 정상이라 자기검산 P05 불변)', '동결 이후 도피 사건 0건' in out and rc == 0 and '판정 중단' not in out, f'rc={rc}')

    # C17 R 경계
    for tag, r, want, want_rc in (('C17', warnR + 1e-6, '정상', 0), ('C17', warnR - 1e-6, '주의', 0),
                                  ('C17', outR + 1e-6, '주의', 0), ('C17', outR - 1e-6, '★역사 밖', 1)):
        S, rc, out = go(n_post=Y3 + 1, b_schedule=[(Y3, Y3 + 1, 1.0 + r)])
        mm = re.search(r'R 3년 롤링 B/H − 1: 현재 ([^ ]+) → (정상|주의|★역사 밖)', out)
        okv = verdict_line(out) or ''
        okvv = okv.startswith('재검토 사유 없음') if want == '정상' else ((okv.startswith('주의 (') and 'R)' in okv) if want == '주의' else (okv.startswith('**역사 밖') and 'R)' in okv))
        R.add(tag, f'동결 뒤 정확히 756일 · 롤링 {r:+.7f} → R {want} · rc {want_rc}', mm is not None and mm.group(2) == want and rc == want_rc and okvv, (mm.group(0) if mm else out[-160:]) + f' | 판정 {okv}')
    S, rc, out = go(n_post=Y3)
    R.add('C17', '동결 뒤 755일 → R 계산 불가', 'R 계산 불가 — 동결 뒤 755거래일' in out)

    # C18 R 과거 최저 vs 현재
    S, rc, out = go(n_post=Y3 + 11, b_schedule=[(Y3, Y3 + 10, 0.4), (Y3 + 10, Y3 + 11, 1.0)])
    mm = re.search(r'R 3년 롤링 B/H − 1: 현재 ([^ ]+) → (정상|주의|★역사 밖) · 동결 이후 최저 ([^\n]+)', out)
    R.add('C18', '동결 이후 창 최저 −60%(역사 밖) 였으나 현재 0% → 판정 정상(현재 창만 판정)', mm is not None and mm.group(2) == '정상' and mm.group(3).startswith('-60.0%') and rc == 0, mm.group(0) if mm else out[-160:],
          note='규약 모호 — JSON judgment.combination 「어느 관문이든 역사 밖 1건 → 재검토」· R 「상시」인데 평가기는 상태(현재 창)만 보고 과거 창의 역사 밖을 기억하지 않는다(주간 실행 사이의 창은 판정에 안 남는다)')

    # C19 지문 불일치 — 임시 사본으로 PROTO 를 잠시 돌린다
    with tempfile.TemporaryDirectory() as td:
        bad = json.loads(json.dumps(P))
        bad['gates']['B_premium']['warn_below'] = -0.5
        tp = os.path.join(td, 'proto_bad.json')
        with io.open(tp, 'w', encoding='utf-8') as f:
            json.dump(bad, f, ensure_ascii=False, indent=1)
        keep = m.PROTO
        try:
            m.PROTO = tp
            S, rc, out = go(n_post=400, oos_events=[(70, -0.55, -0.55, -0.60, 100)])
        finally:
            m.PROTO = keep
    R.add('C19', '규약 사본의 값 변경(지문 불일치) → rc 2 · 「판정을 내지 않는다」 · 판정 줄 없음', rc == 2 and '지문 불일치' in out and verdict_line(out) is None, f'rc={rc}')

    # C21 동결일이 거래일이 아닐 때
    S, rc, out = go(n_post=400, drop_freeze_day=True, oos_events=[(0, -0.30, -0.25, -0.05, 30)])
    R.add('C21', 'idx 에 동결일이 없으면 다음 거래일부터 OOS(그날 사건 = OOS 1건)', '동결 이후 도피 사건 1건' in out and rc == 0 and str(S.idx[S.i0].date()) == '2026-08-31', str(S.idx[S.i0].date()))

    # C22 방어 상태로 시작
    S, rc, out = go(n_post=300, w0_defense=50)
    R.add('C22', 'w 가 0 으로 시작(첫날 방어) → 사건 아님 · 역사 20건 그대로(자기검산 통과)', rc == 0 and '판정 중단' not in out, f'rc={rc}')

    # C23 장부 미참조 — 정적
    src = io.open(os.path.join(os.path.dirname(m.__file__), 'oos_protocol_b.py'), encoding='utf-8').read()
    R.add('C23', '평가기는 oos_log.csv 를 읽지 않는다(정적) — 장부의 누락·중복·순서는 판정에 영향 0', 'oos_log' not in src.replace('장부 oos_log.csv 의 state', ''),
          note='규약 모호 — JSON event.definition 「장부 state QLD→SCHD 에 대응」은 코드 어디서도 대조하지 않는다(--engine E4 가 읽기 전용으로 대조)')


def registration_consistency(m, R, P):
    ev = P['event']
    R.add('C20', 'JSON 사건창 [−63, 252] · 독립 간격 252 = 모듈 상수 PRE/POST/INDEP', list(ev['window_trading_days']) == [-m.PRE, m.POST] and ev['independent_gap_trading_days'] == m.INDEP, f'{ev["window_trading_days"]} / {ev["independent_gap_trading_days"]} vs {m.PRE}/{m.POST}/{m.INDEP}')
    gB, gR = P['gates']['B_premium'], P['gates']['R_rolling_3y']
    R.add('C20', 'B warn_below == history.p05 · outside == history.worst', gB['warn_below'] == gB['history']['p05'] and gB['outside_history_below'] == gB['history']['worst'])
    R.add('C20', 'R warn_below == history.p05 · outside == history.worst', gR['warn_below'] == gR['history']['p05'] and gR['outside_history_below'] == gR['history']['worst'])
    R.add('C20', '지문 재계산 == 기록 지문', m.fingerprint(P) == P['fingerprint'], P['fingerprint'])
    R.add('C20', 'oos_start 가 영업일', pd.Timestamp(P['applies_to']['oos_start']).weekday() < 5, P['applies_to']['oos_start'])


# ---------------------------------------------------------------- 엔진 모드
def own_mdd(x):
    x = np.asarray(x, float)
    peak = -np.inf
    worst = 0.0
    for v in x:                                   # 누적 최대를 손으로 — np.maximum.accumulate 를 안 쓴다
        peak = v if v > peak else peak
        d = v / peak - 1.0
        worst = d if d < worst else worst
    return float(worst)


def independent_recompute(D, P, PRE=63, POST=252, GAP=252):
    """등록값(history)을 평가기 함수 없이 다시 센다 — 정의만 같고 코드는 다르다."""
    idx, w, B, H = D['idx'], np.asarray(D['w']), np.asarray(D['B'], float), np.asarray(D['H'], float)
    n = len(idx)
    start = pd.Timestamp(P['applies_to']['oos_start'])
    esc = [i for i in range(1, n) if w[i] == 0.0 and w[i - 1] == 1.0]
    rows = []
    prev = None
    for i in esc:
        indep = prev is None or (i - prev) > GAP
        prev = i
        lo, hi = max(0, i - PRE), i + POST
        full = hi < n
        if not full:
            rows.append(dict(i=i, date=idx[i], full=False, indep=indep))
            continue
        b = B[lo:hi + 1] / B[lo]
        h = H[lo:hi + 1] / H[lo]
        rows.append(dict(i=i, date=idx[i], full=True, indep=indep, mdd_b=own_mdd(b), mdd_h=own_mdd(h), prem=b[-1] / h[-1] - 1.0))
    E = pd.DataFrame(rows)
    pre = E[(E.date < start) & E.full]
    dis = pre[(pre.mdd_h <= -0.5) & pre.indep]
    a = (int((dis.mdd_b > dis.mdd_h).sum()), len(dis))
    prem = np.sort(pre.prem.values)
    k = 756
    roll = np.array([B[j + k] / B[j] / (H[j + k] / H[j]) - 1.0 for j in range(0, n - k)])
    yrs = (idx[-1] - idx[0]).days / 365.25
    return dict(E=E, a=a, n_pre=len(pre), prem=prem, p05=float(np.percentile(prem, 5)), p10=float(np.percentile(prem, 10)),
                med=float(np.median(prem)), worst=float(prem.min()),
                r_p05=float(np.percentile(roll, 5)), r_p10=float(np.percentile(roll, 10)), r_med=float(np.median(roll)),
                r_worst=float(roll.min()), r_neg=float(np.mean(roll < 0)), r_nonov=len(roll) / k, years=yrs, esc=esc)


def ledger_escapes(root):
    p = os.path.join(root, 'data', 'oos_log.csv')
    L = pd.read_csv(p)
    L = L.sort_values('as_of')
    out = []
    prev = None
    for r in L.itertuples():
        if prev == 'QLD' and r.state != 'QLD':
            out.append(str(r.as_of))
        prev = r.state
    return out, str(L.as_of.iloc[-1]), len(L)


def engine_cases(m, R, root, P):
    D = m.load()
    idx = D['idx']
    n = len(idx)
    start = pd.Timestamp(P['applies_to']['oos_start'])
    # E0 기준 출력
    rc, out = run_eval(m, D)
    R.add('E0', '실제 엔진 D → rc 0 · 자기검산 통과 · 사건 0건 · 「판정 사건 0건」', rc == 0 and '판정 중단' not in out and '동결 이후 도피 사건 0건' in out and verdict_line(out) == '재검토 사유 없음 (판정 사건 0건)', re.search(r'기저율 자기검산: [^\n]*', out).group(0))
    # E1 등록값 독립 재계산
    X = independent_recompute(D, P)
    gA, gB, gR = P['gates']['A_disaster_payout'], P['gates']['B_premium'], P['gates']['R_rolling_3y']
    R.add('E1', f'A 재난 지급 독립 재계산 {X["a"][0]}/{X["a"][1]} == 등록 {gA["history"]["pass"]}/{gA["history"]["n"]}', X['a'] == (gA['history']['pass'], gA['history']['n']))
    R.add('E1', f'B 사건 수 {X["n_pre"]} == 등록 n {gB["history"]["n"]}', X['n_pre'] == gB['history']['n'])
    for key, val in (('p05', X['p05']), ('p10', X['p10']), ('median', X['med']), ('worst', X['worst'])):
        R.add('E1', f'B history.{key} 등록 {gB["history"][key]:+.3f} vs 재계산 {val:+.4f} (|Δ| ≤ 0.0005)', abs(val - gB['history'][key]) <= 0.0005 + 1e-12)
    for key, val in (('p05', X['r_p05']), ('p10', X['r_p10']), ('median', X['r_med']), ('worst', X['r_worst']), ('share_negative', X['r_neg'])):
        tol = 0.005 if key == 'share_negative' else 0.0005
        R.add('E1', f'R history.{key} 등록 {gR["history"][key]:+.3f} vs 재계산 {val:+.4f} (|Δ| ≤ {tol})', abs(val - gR['history'][key]) <= tol + 1e-12)
    R.add('E1', f'R nonoverlap_windows 등록 {gR["history"]["nonoverlap_windows"]} vs 재계산 {X["r_nonov"]:.1f}', abs(X['r_nonov'] - gR['history']['nonoverlap_windows']) <= 0.05 + 1e-12)
    # E2 등록 전후 노출 — 동결 이전인데 창이 안 찬 사건이 있는가
    E = X['E']
    pend = E[(E.date < start) & (~E.full)]
    last = E.iloc[-1]
    R.add('E2', f'동결 이전 사건 중 창 미충족(나중에 역사 편입) {len(pend)}건 — 마지막 도피 {last.date.date()} (i+252 {"충족" if last.full else "미충족"} · 자료 끝 {idx[-1].date()})', len(pend) == 0, '' if len(pend) == 0 else str(list(pend.date.dt.date)),
          note='0건이면 등록 시점(자료 끝 2026-08-28)에 역사 집합이 닫혀 있었다 — C15 의 표류 경로가 실제 등록에는 해당 없음')
    # E3 장부↔엔진 도피일 대조 (읽기 전용)
    led, led_last, led_n = ledger_escapes(root)
    eng = [str(idx[i].date()) for i in X['esc'] if idx[i] >= start]
    R.add('E3', f'장부(oos_log.csv {led_n}행 · 마지막 {led_last}) QLD→방어 전환일 {led} vs 엔진 동결 이후 도피일 {eng} (엔진 자료 끝 {idx[-1].date()})', led == eng,
          note='둘 다 0건이라 대조가 사소하다. 엔진 자료(월간 연장)가 장부(일간)보다 뒤처지므로 사건 직후 몇 주는 평가기가 그 사건을 모른다')
    # E4 실제 역사 + 합성 OOS 구간
    def extend(n_post, events=(), b_sched=()):
        post = pd.bdate_range(start=idx[-1] + pd.Timedelta(days=1), periods=n_post)
        idx2 = idx.append(post)
        B2 = np.concatenate([D['B'], np.full(n_post, D['B'][-1])])
        H2 = np.concatenate([D['H'], np.full(n_post, D['H'][-1])])
        w2 = np.concatenate([D['w'], np.ones(n_post)])
        i0 = n - 1 + 1                                    # 첫 합성 날
        for (off, mh, mb, pr, dur) in events:
            i = i0 + off
            hi = i + m.POST
            H2[i + 1:min(hi, len(idx2))] = H2[i0] * (1 + mh)
            B2[i + 1:min(hi, len(idx2))] = B2[i0] * (1 + mb)
            if hi < len(idx2):
                H2[hi] = H2[i0]
                B2[hi] = B2[i0] * (1 + pr)
            w2[i:min(i + dur, len(idx2))] = 0.0
        for (a, b, lv) in b_sched:
            B2[i0 + a:i0 + b] = B2[i0] * lv
        return dict(idx=idx2, w=w2, B=B2, H=H2)
    R.add('E4', '(전제) 엔진 자료 마지막 날 == 동결일 — 합성 구간의 창(lo=i−63)이 실제 자료를 안 건드리게 off ≥ 64', idx[-1] == start, str(idx[-1].date()))
    rc, out = run_eval(m, extend(400, events=[(70, -0.55, -0.55, -0.10, 100)]))
    ln = event_lines(out)
    R.add('E4', '실제 역사 + 합성 재난 A 실패 → ★역사 밖 · rc 1 · 자기검산 그대로', rc == 1 and len(ln) == 1 and '★역사 밖' in ln[0] and '판정 중단' not in out, ln[0] if ln else out[-200:])
    rc, out = run_eval(m, extend(400, events=[(70, -0.30, -0.25, gB['warn_below'] - 1e-6, 100)]))
    ln = event_lines(out)
    R.add('E4', '실제 역사 + 합성 보험료 P05 아래 → 주의 · rc 0', rc == 0 and len(ln) == 1 and 'B 보험료 주의' in ln[0] and (verdict_line(out) or '').startswith('주의 ('), ln[0] if ln else out[-200:])
    rc, out = run_eval(m, extend(757, b_sched=[(756, 757, 1 + gR['outside_history_below'] - 1e-6)]))
    R.add('E4', '실제 역사 + 합성 R 최악 아래(동결 뒤 756일) → ★역사 밖 · rc 1', rc == 1 and '→ ★역사 밖' in out and (verdict_line(out) or '').endswith('(R)'), (re.search(r'R 3년 롤링[^\n]*', out) or [''])[0] if re.search(r'R 3년 롤링[^\n]*', out) else out[-200:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=DEFAULT_ROOT)
    ap.add_argument('--engine', action='store_true')
    a = ap.parse_args()
    root = os.path.abspath(a.root)
    m = load_module(root)
    P = json.load(io.open(os.path.join(root, 'data', 'oos_protocol_b.json'), encoding='utf-8'))
    freeze = pd.Timestamp(P['applies_to']['oos_start'])
    print(f'저장소 {root} · 규약 지문 {P["fingerprint"]} · 동결일 {freeze.date()} · 모듈 PRE/POST/INDEP {m.PRE}/{m.POST}/{m.INDEP}')
    R = Report()
    print('\n[등록 내부 정합]')
    registration_consistency(m, R, P)
    print('\n[합성 D — 경계값·표본 부족·간격·등록 전후·R·지문]')
    synthetic_cases(m, R, freeze, P)
    if a.engine:
        print('\n[엔진 모드 — 실제 D]')
        engine_cases(m, R, root, P)
    sys.exit(R.summary())


if __name__ == '__main__':
    main()
