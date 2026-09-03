# -*- coding: utf-8 -*-
"""
[v37] 단일 검증 진입점 — 이것 하나만 통과하면 된다

사용자는 파이썬을 직접 돌리지 않는다. 그래서 **검증이 자동으로 돌아야** 한다.
`.github/workflows/verify.yml` 이 매 push 마다 `--fast` 와 전체를 **둘 다** 부른다.
**이 파일은 루트에 있어야 한다** — 사용자와 CI 의 진입점이다.

⚠ [2026-09-04 정정] **「배포 게이트」가 아니다.** verify.yml 과 pages.yml 은 둘 다 push
  트리거로 **독립 실행**된다 — 검증이 실패해도 배포는 나가고, 실패는 **이슈(메일)**로만
  알린다. 그게 맞다: 문서 검사가 신호 화면을 얼릴 수 있으면 v137 fail-open 원칙
  (인프라 문제로 진짜 폭락일 신호를 막지 마라)과 정면으로 어긋난다.
  ※ 이 줄은 종전에 「실패하면 CI 가 막아야 한다」였다. CLAUDE.md §0 이 2026-09-01 에
    철회한 주장인데, 그 정정 커밋이 **같은 파일의 아래쪽만 고치고 이 머리말은 놓쳤다**
    (§-1 ③ 「정정한 뒤 같은 파일의 나머지도 다시 읽어라」의 실사례).

    python verify_all.py            # 전체 (실측 5.3초)
    python verify_all.py --fast     # 전략 불변식 일부만 (실측 1.8초)

⚠ [2026-09-04 정정] 종전 표기는 「전체 5~15분 · fast 1~2분」이었다 — 실측의 **56~167배**다.
  그 숫자가 「전체는 무거우니 fast 만 돌리자」의 근거가 됐고, v168 이 정확히 그래서
  화면 검사 7건을 깨뜨린 채 지나갔다(v172 가 기록). 두 모드 차이는 3.5초뿐이다.
  **화면·문서를 건드렸으면 전체로 돌려라.**

[왜 이게 필요한가 — 2026-08-27 에 12건의 오류를 찾고 나서]

  ① 검산 함수가 없던 곳에서만 틀렸다 (2건, 프로젝트 코드)
     run/sim/sim_hold/after_tax 는 check() 가 지켰다 -> 0건
     accumulate/mix_monthly 는 검산이 없었다 -> 2건 다 여기서
  ② 엔진을 안 쓰고 새로 짜서 틀렸다 (2건)
  ③ 모형이 실제 상품과 달랐다 (1건 — 「선물」을 현물로)
  ④ 검증 설계 자체가 틀렸다 (5건)
  ⑤ 공용 모형을 바꾸고 사용처를 안 돌렸다 (1건)
  ⑥ 플랫폼 (1건 — GitHub 예약 실행 누락)

  -> ①②⑤ 는 이 파일이 막는다. ③④ 는 사람이 봐야 한다(README 의 체크리스트).

[불변식 — 하나라도 깨지면 실패]
  I1  엔진 동치      run == sim == sim_hold == after_tax(0%) == 적립(1회납입)
  I2  미래 미참조     시점별 재계산이 전체계산과 일치
  I3  체결 규약      미래를 당기면 좋아진다 (안 좋아지면 이미 보고 있다)
  I4  모형 vs 실물   국내 ETF 3종 연드리프트 ±1.5%p
  I5  채택 결정      B>A, 40/40/20 좌측꼬리(원화), 미국종가 신호
  I6  라이브 정합    signal.json 이 update_signal.py 재계산과 일치
  I7  공표 수치      strategy_stats.json 이 현재 코드 출력과 일치
  I8  의존성         공용 모형 7종이 봉인과 같은가 (바뀌면 사용처를 다시 돌려야 한다)
  I9  폐기 수치      옛 공표값이 현행 문서·화면에 남아 있지 않은가
  I10 전제 감시      나스닥 고유 성질(극단 MDD·장기 상승)이 유지되는가
  I11 규칙 동결      코드·화면이 data/freeze.json 과 같은가 (+ 룩백 3곳 대조)
  I12 T4 그림자      평가 전용 기록의 정의상 불변식 (+ 기록이 실제로 쌓이는가)
  I13 B 판정 규약    data/oos_protocol_b.json 지문 — 사후 수정 방지 (02 §5-1)
  I14 셀프테스트     파수꾼 34경우 · 종가 대기 루프 9경로

[저장소 위생 관문 — 전략 불변식이 아니다 · §2 경계 밖]
  g_repo_map        FILES.md 파일 지도       g_toc          04 절 목차
  g_isolation       공유용_별도전략 격리(AST) g_notes_lag    업데이트 노트 지연
  g_deploy          Pages 복사 목록          g_watchdog     파수꾼 모드·스텝
  g_signal_coupling 판정 경로가 표시 자료를 안 읽는가
  g_freeze_seal     freeze.json 내용 봉인 (FREEZE_SEAL)

⚠ [2026-09-04] §2 는 「verify_all 의 전략 검사(I1~I12)는 읽기만」이라고 정한다.
  위생 관문(g_*)은 그 경계 **밖**이다 — 종전에는 전부 i5_decisions 안에 있어서
  경계가 지켜질 수 없었다(최근 비-시세 커밋 13건이 전부 i5_decisions 를 고쳤다).
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

FAIL, WARN = [], []
T0 = time.time()

# [2026-09-04 코드리뷰] data/freeze.json 의 **내용 봉인**. 그 파일 자체의 fingerprint 필드는
# 저장소 어디에서도 재계산되지 않아(조리법 480가지 전수 탐색, 일치 0건) 검증 불가능하다.
# freeze.json 은 §2 라 못 고치므로, 여기에 독립적인 봉인을 걸어 둔다 — g_freeze_seal 참조.
# 의도적으로 바꿀 때만 이 값을 갱신하고 02 §5-1 에 날짜·이유를 남긴다.
FREEZE_SEAL = '65df0ed8b72a3632'


def ok(name, cond, detail='', warn=False):
    tag = 'PASS' if cond else ('WARN' if warn else 'FAIL')
    print(f"  [{tag}] {name}" + (f"   {detail}" if detail else ''))
    if not cond:
        (WARN if warn else FAIL).append(name)
    return cond


def _differs(a, b, tol=1e-12):
    """두 값이 다른가 — **NaN 은 「다름」으로 센다.**

    [2026-09-04 코드리뷰] 종전 I2 는 `abs(a - b) > tol` 로 비교했는데 한쪽이 NaN 이면
    그 식이 **항상 False** 라 NaN 이 「일치」로 집계됐다. zc·exp_q 가 통째로 NaN 이 돼도
    「불일치 0/25 · PASS」가 뜨고 정상 런과 문구까지 같았다 — 미래 미참조 불변식이다.
    """
    import math
    na, nb = (a is None or (isinstance(a, float) and math.isnan(a))), \
             (b is None or (isinstance(b, float) and math.isnan(b)))
    if na or nb:
        return not (na and nb)          # 둘 다 NaN 이면 같은 것으로 본다(워밍업 구간)
    return abs(float(a) - float(b)) > tol

def head(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


# ------------------------------------------------------------------ I1
def i1_engine():
    head("I1. 엔진 동치 — 모든 시뮬레이터가 같은 답을 내는가")
    import hist_defensive as DF
    import axis_lib as L
    from axis_defmix import materials, check_hold
    D = DF.build('chain')
    ok('axis_lib.check (run/sim/after_tax/적립)', L.check(D))
    ok('axis_defmix.check_hold (바스켓)', check_hold(D, materials(D)))
    return D


# ------------------------------------------------------------------ I2
def i2_pit(D):
    head("I2. 미래 미참조 — 시점별 재계산")
    print("  그날까지의 데이터만으로 다시 계산해 전체계산과 대조한다.")
    import axis_volguard as V
    from axis_lib import rule_w
    px, n = D['px'], len(D['idx'])
    rng = np.random.default_rng(0)
    pts = sorted(rng.choice(np.arange(3000, n), size=25, replace=False))
    full = (px / px.rolling(252, min_periods=252).max() - 1).fillna(0).values
    wf = rule_w(D['ddv'], -0.16, -0.16)
    rvf = V.zc(px.pct_change().rolling(10, min_periods=10).std().values)
    qf = V.exp_q(rvf, 0.925)
    b = [0, 0, 0, 0]
    for t in pts:
        c = px.iloc[:t + 1]
        dv = (c / c.rolling(252, min_periods=252).max() - 1).fillna(0).values
        # [2026-09-04 코드리뷰] ★ 종전 첫 검사는 full 을 여기서 다시 만들어 **자기 표현식을
        #   자기 자신과 비교**했다(적대적 2,000점에서 편차 0.00e+00 — 실패할 수 없었다).
        #   판정이 실제로 쓰는 것은 엔진이 만든 D['ddv'] 다 → 그쪽과 대조한다.
        if _differs(dv[-1], D['ddv'][t]):
            b[0] += 1
        if rule_w(dv, -0.16, -0.16)[-1] != wf[t]:
            b[1] += 1
        z = V.zc(c.pct_change().rolling(10, min_periods=10).std().values)
        if _differs(z[-1], rvf[t], 1e-10):
            b[2] += 1
        q = V.exp_q(z, 0.925)
        if _differs(q[-1], qf[t], 1e-10):
            b[3] += 1
    for nm, v in zip(('QQQ 낙폭', '비중경로', '변동성 z', '확장창 분위'), b):
        ok(f'{nm} 시점별 일치', v == 0, f'불일치 {v}/{len(pts)}')


# ------------------------------------------------------------------ I3
def i3_lag(D):
    head("I3. 체결 규약 — 미래를 당기면 좋아지는가")
    from axis_lib import rule_w, sim, COST
    w = rule_w(D['ddv'], -0.16, -0.16)
    pos = w.copy()
    r = np.nan_to_num(pos * D['qldr'] + (1 - pos) * D['schdr'])
    r[0] = 0.0
    t = np.abs(np.diff(pos, prepend=pos[0]))
    peek = float(np.cumprod((1 + r) * (1 - COST * t))[-1])
    base = float(sim(D, w)[0].iloc[-1])
    ok('미래훔쳐보기가 규약보다 유리', peek > base * 1.10,
       f'{peek:,.0f} vs {base:,.0f} ({peek/base-1:+.0%})')


# ------------------------------------------------------------------ I4
def i4_real(D):
    head("I4. 모형 vs 실물 — 국내 ETF 연드리프트")
    import hist_defasset as DA
    import hist_krfinal as KF
    from axis_defmix import mix_monthly_from
    _, ki, _, _, dfk, fr = KF.build_krw('chain')
    syn = {'div': pd.Series(np.asarray(dfk, dtype=float), index=ki),
           'ust5': pd.Series((1 + DA.ust_tr(ki, 5, 'TNX', futures=True, fee=DA.UST_FEE)) * (1 + fr) - 1, index=ki),
           'gold': pd.Series((1 + DA.gold_r(ki)) * (1 + fr) - 1, index=ki)}
    for code, k, nm in [('458730', 'div', '배당'), ('305080', 'ust5', '국채'), ('411060', 'gold', '금')]:
        kr = DA.kr(code)
        # pct_change 는 반드시 교집합 **후에** (v34 교훈)
        a = kr.reindex(kr.index.intersection(ki)).pct_change().dropna()
        # [2026-09-04 코드리뷰] ★ 종전엔 분자와 분모가 **서로 다른 날짜 집합**을 복리했다.
        #   실물 a 는 교집합의 연속 관측 사이 수익이라 공백을 통째로 먹는데(실측 다일 수익
        #   98/1868건, 최장 6일), 합성은 `reindex(a.index)` 라 그 사이 날을 그냥 버렸다.
        #   실측 오차 — 국채 −0.032%/년 → **−0.928%**(문턱 ±1.5%p 의 62%) · 금은 **부호가
        #   뒤집힌다**(−0.243% → +0.385%). 진짜 모형-실물 괴리 1%p 가 정렬 아티팩트로 상쇄된다.
        #   게다가 fillna(0) 이라 원자료가 몇 주 뒤지면 결측이 0% 날로 변해 그대로 통과했다.
        #   → 같은 구간의 합성 **전체**와 비교하고, 연수도 그 구간 길이로 잰다.
        full = syn[k].loc[a.index[0]:a.index[-1]]
        if full.isna().any():
            ok(f'{nm} {code} 합성 계열에 결측 없음', False,
               '%d일 결측 — 0%%로 메우면 드리프트가 가짜로 좋아진다' % int(full.isna().sum()))
            full = full.dropna()
        y = len(full) / 252.0
        d = ((1 + full).prod() / (1 + a).prod()) ** (1 / y) - 1
        ok(f'{nm} {code} 드리프트 ±1.5%p', abs(d) < 0.015,
           f'{d:+.2%}/년 ({y:.1f}년 · 실물 관측 {len(a)}일 / 구간 {len(full)}일)')


# ==================================================================== 저장소 위생 관문
# [2026-09-04 코드리뷰] ★ 아래 관문들은 **전략 불변식이 아니다** — 저장소가 스스로를
#   기록·격리·배포하는 것을 지킨다. 종전에는 전부 i5_decisions() 안, 그것도
#   `if os.path.exists('signal.html'):` 블록 **안쪽**에 있었다. 그래서
#   ⓐ signal.html 이름만 바뀌어도 이 관문들이 통째로 조용히 사라졌고(실측 51개 검사 → 0개),
#   ⓑ §2 가 「verify_all 의 전략 검사(I1~I12)는 읽기만」이라고 정한 경계 안에 새 관문이
#     계속 들어가, 최근 비-시세 커밋 13건이 전부 i5_decisions 를 고쳤다(§2 위반 유발).
#   → 최상위 함수로 꺼냈다. **전략 검사(I1~I14)와 위생 관문은 이제 파일에서 갈린다.**


def _read(p):
    """파일을 통째로 읽는다. 없으면 None (호출부가 warn 을 내게)."""
    try:
        return io.open(p, encoding='utf-8').read()
    except Exception:
        return None


def _need(name, p):
    """관문의 대상 파일이 있는가. 없으면 WARN 을 내고 False — **조용히 사라지지 않는다.**"""
    if os.path.exists(p):
        return True
    ok(name, False, '%s 없음 — 이 관문이 이번 실행에서 돌지 않았다' % p, warn=True)
    return False


def g_repo_map():
    """[v172] 파일 지도 관문 — 추적 파일이 FILES.md 에 없으면 실패.

    [2026-09-04 코드리뷰] 구멍 둘을 막았다.
      ⓐ git 이 실패하면 tk=[] 가 되어 **아무것도 검사하지 않고 통과**했다
        (실측: 정상 「검사 대상 201개」 vs git 실패 「검사 대상 0개 전부 등재」 — 둘 다 PASS).
        subprocess.run 에 check=True 가 없어 종료코드 128 은 예외조차 안 났다.
        → check=True + 실패는 WARN 으로 드러낸다. timeout 도 60 → 20초.
      ⓑ 등재 검사가 **basename 부분문자열**이라 남의 행에 무임승차했다. 실측: 미등재 새 파일
        research/hist.py · deploy/protocol_b.py · .github/workflows/stats.yml · deploy/lib.py ·
        data/log.csv 가 전부 PASS(refresh_hist.py · oos_protocol_b.py · monthly-stats.yml 등의
        부분문자열). 추적 파일 중에도 3쌍이 이미 서로 가려 준다.
        → **전체 경로**로 본다. FILES.md 표는 이미 저장소 상대 경로를 적고 있고,
          디렉터리 없이 basename 만 적힌 옛 행(audit/*.py 등)은 basename 도 허용한다.
    """
    if not _need('파일 지도 관문', 'FILES.md'):
        return
    fmap = _read('FILES.md') or ''
    try:
        tk = subprocess.run(['git', '-c', 'core.quotepath=false', 'ls-files'],
                            capture_output=True, text=True, encoding='utf-8',
                            check=True, timeout=20).stdout.splitlines()
    except Exception as e:
        ok('파일 지도가 실제 파일을 따라잡았다', False,
           'git ls-files 실패(%s) — 검사하지 못했다(통과가 아니다)' % type(e).__name__,
           warn=True)
        return
    tk = [t.strip().replace(chr(92), '/') for t in tk if t.strip()]

    def watched(p):
        if p.startswith('archive/') or p.startswith('docs/'):
            return False                      # 옛 기록 — 지도의 대상이 아니다
        if p.startswith(('deploy/', 'research/', 'audit/')) and p.endswith(('.py', '.md')):
            return True
        if p.startswith('내가_보는_것/'):
            return True
        if p.startswith('.github/workflows/'):
            return True
        if '/' not in p and p.endswith(('.py', '.html')):
            return True
        return bool(re.match(r'data/[^/]+\.(json|csv)$', p))

    def listed(p):
        if p in fmap:
            return True
        # FILES.md 는 표 칸(`경로`)과 산문 둘 다로 등재한다(예: 49행의 research/*.md 나열).
        # 전체 경로만 인정하면 오탐 10건이 나고, v172 가 「오탐이 나면 관문이 무시당한다」고
        # 적어 둔 그대로가 된다. 그래서 basename 을 쓰되 **단어 경계**를 요구한다 —
        # 이러면 hist.py 가 refresh_hist.py 에, verify.py 가 axis_finalverify.py 에,
        # withdraw.py 가 plan30_withdraw.py 에 무임승차하던 것이 전부 막힌다.
        b = os.path.basename(p)
        return re.search(r'(?<![\w/.-])' + re.escape(b) + r'(?!\w)', fmap) is not None

    watch = [p for p in tk if watched(p)]
    miss = [p for p in watch if not listed(p)]
    ok('파일 지도가 실제 파일을 따라잡았다', not miss,
       ('FILES.md 미등재 %d건: %s (v172)' % (len(miss), ', '.join(miss[:5]))) if miss
       else '검사 대상 %d개 전부 등재 (전체 경로 기준)' % len(watch))


def g_toc():
    """[2026-09-03] 04 절 목차가 본문을 따라가는가 — 지도가 조용히 틀려지는 것을 막는다.

    [2026-09-04 코드리뷰] 제목에 「목차」가 들어간 절이 검사에서 통째로 빠졌다
    (`'## ' and '목차' not in l` 이 헤더 판별과 제외를 한 줄에 섞었다). 실측:
    `## §5-42. 새 후보 — 목차 정리 겸용` 을 넣으면 본문 절로 세지 않아 PASS 였다.
    → 목차 표 자체는 **줄 번호가 아니라 위치**(첫 절 앞)로 가리고, 절 제목의 「목차」는 안 본다.
    """
    if not _need('04 목차 관문', '04_Rejected_Research.md'):
        return
    r4 = (_read('04_Rejected_Research.md') or '').split(chr(10))
    hd = [i for i, l in enumerate(r4) if l.startswith('## ')]
    if not hd:
        ok('04 목차가 본문 절을 전부 담고 있다', False, '절을 하나도 못 찾았다')
        return
    # ★ 목차 자신이 **첫 번째 '## ' 절**이다(04 9행). 종전처럼 제목에 '목차' 가 들었는지로
    #   가르면 본문 절 제목에 그 낱말이 들어가는 순간 그 절이 검사에서 빠진다(실측 확인).
    #   위치로 가른다 — 첫 절은 목차, 그 뒤가 전부 본문이다.
    body_idx = hd[1:]
    body = [r4[i][3:].split('.')[0].strip() for i in body_idx]
    toc_head = chr(10).join(r4[:hd[1]] if len(hd) > 1 else r4)
    listed = set(x.strip() for x in re.findall(r'^\| \*\*([^*]+)\*\*', toc_head, re.M))
    gone = [s for s in body if s not in listed]
    ok('04 목차가 본문 절을 전부 담고 있다', bool(body) and not gone,
       ('목차 누락 %d개: %s — 절을 추가했으면 04 맨 앞 목차에도 한 줄 (2026-09-03)'
        % (len(gone), ', '.join(gone[:5]))) if gone else '절 %d개 전부 색인' % len(body))


SHARE = '공유용_별도전략'
# 폴더 밖으로 나가는 쓰기·삭제로 쓰이는 호출들. (모듈, 함수) 또는 (None, 메서드).
# ★ 이름만으로는 못 가른다 — replace·copy·move 는 str/DataFrame 메서드로도 흔하다
#   (실측 오탐: a[:7].replace('-','.') 가 「'-' 에 쓰기」로 잡혔다).
#   그래서 **모듈이 붙은 것**과 **모호하지 않은 메서드**를 갈라 둔다.
_WRITE_MODULE = {                      # os.remove(...) 처럼 모듈이 앞에 붙어야 인정
    'os': ('replace', 'rename', 'remove', 'unlink'),
    'shutil': ('copy', 'copy2', 'copyfile', 'move', 'rmtree'),
    'np': ('save', 'savez', 'savez_compressed', 'savetxt'),
    'numpy': ('save', 'savez', 'savez_compressed', 'savetxt'),
    'plt': ('savefig',), 'pyplot': ('savefig',),
    'Path': ('write_text', 'write_bytes'),
}
_WRITE_METHOD = ('write_text', 'write_bytes', 'to_csv', 'to_json', 'to_pickle',
                 'to_excel', 'to_parquet', 'to_hdf', 'to_feather', 'savefig',
                 'savetxt', 'to_stata')
# json.dump(obj, f) · f.write(text) 는 **경로가 아니라 내용**을 받는다 — 위험은 그 f 를
# 만든 open() 에 있고 그건 위에서 이미 잡힌다. 여기서 세면 오탐만 는다.


def _lit_path(node, consts):
    """AST 노드에서 **경로 문자열**을 뽑는다. 못 뽑으면 None(→ 경고 대상)."""
    import ast
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return consts.get(node.id)
    if isinstance(node, ast.JoinedStr):        # f'data/{x}.json' → 리터럴 조각만 이어 붙인다
        s = ''.join(v.value for v in node.values
                    if isinstance(v, ast.Constant) and isinstance(v.value, str))
        return s or None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = _lit_path(node.left, consts), _lit_path(node.right, consts)
        return (a or '') + (b or '') if (a or b) else None
    if isinstance(node, ast.Call):             # os.path.join('data','x.json')
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == 'join':
            parts = [_lit_path(a, consts) for a in node.args]
            if all(p is not None for p in parts):
                return '/'.join(parts)
    return None


def _scan_share_file(path, rel, bad, unk):
    """한 파일의 AST 를 훑어 폴더 밖 쓰기·deploy 호출을 찾는다."""
    import ast
    try:
        tree = ast.parse(io.open(path, encoding='utf-8').read(), filename=path)
    except Exception as e:
        bad.append('%s -> 파싱 실패(%s)' % (rel, type(e).__name__))
        return 0
    consts = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            v = _lit_path(n.value, consts)
            if v:
                consts[n.targets[0].id] = v
    wr = 0
    for n in ast.walk(tree):
        # ① deploy 파이프라인 호출 — import / importlib / sys.path / subprocess argv
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == 'deploy' or a.name.startswith('deploy.'):
                    bad.append('%s -> deploy 임포트' % rel)
        if isinstance(n, ast.ImportFrom) and (n.module or '').split('.')[0] == 'deploy':
            bad.append('%s -> deploy 임포트' % rel)
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value.replace(chr(92), '/')
            if v == 'deploy' or v.startswith('deploy.') or v.startswith('deploy/'):
                bad.append('%s -> deploy 경로 문자열 %r' % (rel, n.value))
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else '')
        if name != 'open':
            mod = ''
            if isinstance(f, ast.Attribute):
                v = f.value
                while isinstance(v, ast.Attribute):
                    v = v.value
                if isinstance(v, ast.Name):
                    mod = v.id
                elif isinstance(v, ast.Call) and isinstance(v.func, ast.Name):
                    mod = v.func.id            # Path('x').write_text(...)
            if not (name in _WRITE_METHOD or name in _WRITE_MODULE.get(mod, ())):
                continue
        # ② open 은 모드가 읽기면 통과 (기본값 'r')
        if name == 'open':
            mode = None
            if len(n.args) > 1:
                mode = _lit_path(n.args[1], consts)
            for kw in n.keywords:
                if kw.arg == 'mode':
                    mode = _lit_path(kw.value, consts)
            if mode is None:
                mode = 'r'
            if not any(c in mode for c in 'wax+'):
                continue
        # ③ 대상 경로: 첫 인자, 또는 메서드면 수신자(Path('x').write_text())
        tgt = None
        if n.args:
            tgt = _lit_path(n.args[0], consts)
        for kw in n.keywords:
            if kw.arg in ('path', 'path_or_buf', 'filename', 'fname', 'file'):
                tgt = _lit_path(kw.value, consts) or tgt
        if tgt is None and isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call):
            if f.value.args:
                tgt = _lit_path(f.value.args[0], consts)
        wr += 1
        if tgt is None:
            unk.append('%s(%s)' % (rel, name))
            continue
        # ④ ★ 정규화해서 본다 — '공유용_별도전략/../data/x' 는 폴더 안이 아니다
        norm = os.path.normpath(tgt.replace(chr(92), '/')).replace(chr(92), '/')
        if os.path.isabs(norm) or not (norm == SHARE or norm.startswith(SHARE + '/')):
            bad.append('%s -> %s' % (rel, tgt))
    return wr


def g_isolation():
    """[2026-09-02] 공유용_별도전략/ 격리 — 읽기(빌려쓰기)는 자유, **쓰기(오염)는 차단**.

    소유자 규정: 「저 스크립트는 우리 전략을 빌려 써도 된다. 우리 게 이상한 걸 흡수해서
    손상되지 않기만 하면 된다.」 그 폴더는 FILES.md 관문 밖이라(의도) **이 검사가 유일한 감시**다.

    [2026-09-04 코드리뷰] 종전 구현은 정규식 두 개(`open('lit','w')` · `.to_csv('lit')`)뿐이라
    실측 **9/9 우회가 전부 통과**했다 — f-문자열 open · Path.write_text · mode='w' 키워드 ·
    os.path.join · df.to_json · shutil.copy · os.remove · importlib.import_module('deploy…') ·
    하위 폴더(listdir 비재귀). 그리고 경로 검사가 원문 문자열 startswith 라
    **'공유용_별도전략/../data/nav_history.csv'** 가 「폴더 안」으로 통과했다(§2 장부다).
    → **AST 로 다시 짰다**: 쓰기·삭제 호출 20여 종 · 하위 폴더 재귀 · 경로 normpath ·
      deploy 임포트/동적 임포트/경로 문자열. 경로가 실행 중 정해지면 종전대로 **경고**로 둔다
      (그 폴더는 다른 세션이 계속 파일을 늘리는 자리라 딱딱하게 실패시키면 관문이 무시당한다).
    """
    if not os.path.isdir(SHARE):
        return                                 # 폴더 자체가 없으면 지킬 것도 없다
    bad, unk, wr = [], [], 0
    n_files = 0
    for root, _dirs, files in os.walk(SHARE):
        for fn in sorted(files):
            if not fn.endswith('.py'):
                continue
            n_files += 1
            p = os.path.join(root, fn)
            wr += _scan_share_file(p, os.path.relpath(p, SHARE).replace(chr(92), '/'), bad, unk)
    ok('공유용_별도전략 이 본 전략을 오염시키지 않는다', not bad,
       ('★ 폴더 밖 쓰기/파이프라인 호출 %d건: %s' % (len(bad), '; '.join(bad[:3]))) if bad
       else '.py %d개 · 쓰기 %d곳 전부 %s/ 안 · deploy 호출 0 (읽기는 자유)' % (n_files, wr, SHARE))
    if unk:
        ok('공유용: 경로가 실행 중 정해지는 쓰기', False,
           '%d건 — 눈으로 확인 필요: %s' % (len(unk), ', '.join(unk[:3])), warn=True)


def g_notes_lag():
    """[v148] 업데이트 노트가 CLAUDE.md §4 최신 vNN 을 따라가는가.

    [2026-09-04 코드리뷰] 종전 정규식 `^- \\*\\*.*$` 은 §4 의 **다수파 형식인 `- v90:` 계열
    31개를 못 봤고**, 동시에 파일 전체를 훑어 §4 밖의 굵은 글머리까지 읽었다. 실측:
    저장소 자신의 형식으로 `- v203: …` 을 추가하고 노트를 안 고쳐도 **PASS**,
    반대로 §0 에 `- **주의**: v210 …` 한 줄만 있어도 거짓 FAIL 이 났다.
    → **§4 절 안으로 앵커**를 옮기고 두 형식을 모두 읽는다.
    """
    if not (_need('노트 지연 관문', 'notes.html') and _need('노트 지연 관문', 'CLAUDE.md')):
        return
    n = _read('notes.html') or ''
    cm = _read('CLAUDE.md') or ''
    # [v142] 노트의 핵심 메시지는 「규칙은 안 바뀌었다」 — 이게 사라지면 이 화면은 그냥
    # 변경 목록이 되고 동결의 의미가 화면에서 사라진다.
    ok('업데이트 노트: 규칙 무변경 선언 + 돌아가기 탭',
       '매매 규칙은 한 번도 바뀌지 않았습니다' in n and '변경 0회' in n
       and 'href="./"' in n and 'href="guide.html"' in n,
       '동결 사실이 화면에 남아 있어야 한다 (v142)')
    # §4 절만 자른다 (제목이 바뀌면 잘라내기가 실패하므로 그때는 경고)
    m = re.search(r'^##\s*4\..*$', cm, re.M)
    if not m:
        ok('업데이트 노트가 최신 버전까지 담고 있다', False,
           'CLAUDE.md 에서 §4 절 제목을 못 찾았다 — 앵커를 고쳐야 한다', warn=True)
        return
    nxt = re.search(r'^##\s', cm[m.end():], re.M)
    sec = cm[m.end(): m.end() + (nxt.start() if nxt else len(cm))]
    # 두 형식 모두: '- **vNN ...' 과 '- vNN: ...' · 범위 표기(v154~v160)도 전부 읽는다
    cv = [int(x) for ln in re.findall(r'^-\s+.*$', sec, re.M)
          for x in re.findall(r'v(\d+)', ln)]
    nvs = [int(x) for x in re.findall(r'class="v">v(\d+)', n)]
    ok('업데이트 노트가 최신 버전까지 담고 있다',
       bool(cv) and bool(nvs) and max(nvs) >= max(cv),
       '노트 최신 v%s vs CLAUDE §4 최신 v%s — 뒤처지면 실패 (v148)'
       % (max(nvs) if nvs else '?', max(cv) if cv else '?'))


def g_deploy():
    """배포 복사 목록 — 빠지면 로컬에선 보이고 **라이브에서만 404** 가 난다(v78 실사고).

    [2026-09-04 코드리뷰] dd_percentile 검사가 `in pg or not os.path.exists(...)` 라
    **산출이 멈추는 순간(=라이브 404 가 나는 바로 그 상황) 공허하게 통과**했다.
    PWA 검사처럼 「목록에 있다 AND 로컬에 있다」를 둘 다 요구하도록 갈았다.
    """
    if not _need('배포 복사 목록 관문', '.github/workflows/pages.yml'):
        return
    pg = _read('.github/workflows/pages.yml') or ''
    for f, why in (('guide.html', '설명서 탭 (v78 실사고)'),
                   ('notes.html', '업데이트 노트 탭 (v142)'),
                   ('price.json', '시세 배지 (v145)')):
        # ★ 주석에 이름이 남아 있어도 통과하던 것 — 실제 복사 명령줄에서 찾는다.
        lines = [l for l in pg.split(chr(10)) if not l.strip().startswith('#')]
        ok('배포: %s 이 Pages 복사 목록에 있다' % f, any(f in l for l in lines), why)
    ok('배포: dd_percentile.json 이 만들어지고 복사된다',
       'dd_percentile.json' in pg and os.path.exists('data/dd_percentile.json'),
       '산출이 멈춰도 통과하던 것을 막았다 — 목록 AND 로컬 존재 (v164)')
    ok('배포: PWA 파일이 Pages 복사 목록에 있다',
       'manifest.json' in pg and 'icon-192.png' in pg and 'icon-512.png' in pg
       and os.path.exists('manifest.json') and os.path.exists('icon-192.png')
       and os.path.exists('icon-512.png'),
       '홈 화면 추가 (v104) — 누락 시 라이브 404')
    # [v197] 낙폭 백분위는 원자료 연장(월간)과 같은 워크플로에서, 그 **뒤에** 돌아야 한다.
    if os.path.exists('.github/workflows/monthly-stats.yml'):
        ms = _read('.github/workflows/monthly-stats.yml') or ''
        both = 'emit_dd_distribution.py' in ms and 'refresh_hist.py' in ms
        ok('배포: 낙폭 백분위가 월간 워크플로에서 갱신된다',
           both and ms.index('refresh_hist.py') < ms.index('emit_dd_distribution.py'),
           '원자료 연장 뒤에 돌아야 한다 (v197)')


def g_signal_coupling():
    """[v145] **판정 경로가 표시용 자료를 읽지 않는다** — 동결 규칙(QQQ 미국 종가만)의 결합 차단.

    시세 스냅샷은 표시 전용이다. 신호 생성이 price.json 을 읽는 순간 동결이 깨진다.
    2026-09-03 예비 출처 체인도 같은 규약 — 표시·기록·원자료 셋에만 붙고 판정 경로엔 없다.
    """
    if not _need('판정 경로 결합 관문', 'deploy/update_signal.py'):
        return
    up = _read('deploy/update_signal.py') or ''
    ok('시세: 신호 생성이 price.json 을 읽지 않는다',
       'price.json' not in up and 'price_now' not in up,
       '판정은 QQQ 종가만 — 시세는 화면 표시 전용 (v145)')
    if os.path.exists('deploy/kr_sources.py'):
        pn, nc = _read('deploy/price_now.py') or '', _read('deploy/nav_collect.py') or ''
        rh, wc = _read('deploy/refresh_hist.py') or '', _read('deploy/wait_close.py') or ''
        ok('시세: 예비 출처 체인이 표시·기록·원자료 경로에 붙고 판정 경로엔 없다',
           'kr_sources' in pn and 'kr_sources' in nc and 'kr_sources' in rh
           and 'kr_sources' not in up and 'kr_sources' not in wc,
           '네이버 → 다음 → 토스 → 야후 → 구글 (2026-09-03) · 판정은 QQQ 종가 3중 체인')


def g_watchdog():
    """[v192] 실행 규율 알림 2종이 파수꾼 **모드와 워크플로 스텝 양쪽**에 있는가.

    한쪽만 있으면 조용히 안 돈다. 근접 판정이 B(strategies.B · recent[].B)를 읽는지도 본다 —
    signal.json 최상위 키는 A 미러(exit −11)라 읽으면 복귀선이 틀린다.
    """
    if not (_need('파수꾼 관문', 'deploy/watchdog.py')
            and _need('파수꾼 관문', '.github/workflows/watchdog.yml')):
        return
    wd = _read('deploy/watchdog.py') or ''
    wy = _read('.github/workflows/watchdog.yml') or ''
    ok('파수꾼: 전환 실행일 재알림·근접 진입 알림이 모드와 스텝 양쪽에',
       "'switchday': mode_switchday" in wd and "'near': mode_near" in wd
       and 'watchdog.py switchday' in wy and 'watchdog.py near' in wy
       and "row.get('B'" in wd,
       '모드만 있고 스텝이 없으면 조용히 안 돈다 · 근접 판정은 B 열 (v192)')
    kh = _read('deploy/kr_holidays.py') or ''
    ok('파수꾼: 휴장일 표가 매주 자동 연장된다 (같으면 안 씀)',
       'kr_holidays.py --emit' in wy
       and 'git add data/ops_check.json data/kr_holidays.json' in wy
       and "old.get('holidays') == out" in kh,
       '2032 에 조용히 끝나는 파일 — 재생성은 주간, 커밋은 해가 바뀔 때만 (v195)')


def g_freeze_seal():
    """[2026-09-04 코드리뷰] freeze.json 의 **내용 봉인** — 새로 만든 관문.

    ★ 왜 필요한가: I13 은 oos_protocol_b.json 의 지문은 **재계산해서** 대조하는데,
      freeze.json 은 `j['applies_to']['freeze_fingerprint'] == F['fingerprint']` 로
      **저장된 문자열 둘을 비교**할 뿐이다. 그리고 F['fingerprint'] 를 만드는 코드가
      저장소 어디에도 없다 — 조리법 480가지(본문 범위 4 × sort_keys × ensure_ascii ×
      구분자 × sha256/sha1/md5 × 길이 5)를 전부 돌려도 **일치 0건**이었다.
      즉 rule 밖 항목(defensive 비중 · cost · execution)을 고쳐도 지문은 그대로고,
      I11 은 enter/exit/lookback 세 개만 숫자로 보며, oos_log.csv 는 낡은 지문을 계속 찍는다.
      **OOS 순수성 주장이 기대는 봉인이 검증 불가능한 상태다.**

    ⛔ freeze.json 은 §2 절대 수정 금지라 **건드리지 않는다.** 기존 fingerprint 필드는
      장부 라벨로 그대로 두고, 여기서는 **독립적인 내용 봉인**을 새로 건다:
      본문(fingerprint 제외)을 정규화 직렬화해 sha256 하고, 그 값을 아래에 박아 둔다.
      freeze.json 이 한 글자라도 바뀌면 이 관문이 실패한다. 바꾸려면 의도적으로
      이 상수를 갱신하고 02 §5-1 에 날짜·이유를 남겨야 한다 — 실수로는 못 바꾼다.
    """
    if not _need('동결 내용 봉인', 'data/freeze.json'):
        return
    import hashlib
    F = json.load(io.open('data/freeze.json', encoding='utf-8'))
    body = {k: v for k, v in F.items() if k != 'fingerprint'}
    seal = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()[:16]
    ok('동결 파일 내용이 봉인과 같다', seal == FREEZE_SEAL,
       '재계산 %s vs 등록 %s — 다르면 freeze.json 이 바뀐 것이다' % (seal, FREEZE_SEAL))
    # 그리고 rule 밖 항목도 숫자로 못 박는다 — 봉인 상수를 누가 갱신해도 이건 남는다.
    # (I11 은 enter/exit/lookback 셋만 본다. 방어 비중·비용은 아무도 안 보고 있었다.)
    d = {x['code']: x['weight'] for x in F.get('defensive', [])}
    ok('방어 비중 40/40/20', d.get('458730') == 0.4 and d.get('305080') == 0.4
       and d.get('411060') == 0.2 and abs(sum(d.values()) - 1.0) < 1e-9, str(d))
    ok('공격 자산이 418660 이다', F.get('risk_on', {}).get('code') == '418660',
       F.get('risk_on', {}).get('name', '?'))
    c = F.get('cost', {})
    ok('비용 규약 편도 0.1% · 슬리피지 0.1%',
       c.get('one_way') == 0.001 and c.get('slippage') == 0.001, str(c))
    ok('체결 규약이 한 칸 지연이다', 'shift(1)' in str(F.get('execution', '')),
       F.get('execution', '?'))


# ------------------------------------------------------------------ I5
def i5_decisions(D):
    head("I5. 채택 결정 — 지금 계산해도 같은 답인가")
    import hist_defasset as DA
    import hist_krfinal as KF
    from axis_lib import rule_w
    from axis_defmix import materials, mix_monthly_from, sim_def
    comp = materials(D)
    idx = D['idx']
    WA = rule_w(D['ddv'], -0.16, -0.11)
    WB = rule_w(D['ddv'], -0.16, -0.16)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    a = float(sim_def(D, WA, defr).iloc[-1])
    b = float(sim_def(D, WB, defr).iloc[-1])
    ok('B(-16/-16) > A(-16/-11)', b > a, f'{b:,.0f} vs {a:,.0f}')

    # 원화 좌측꼬리 (v23 의 실제 판정 기준)
    _, ki, lev2, _, dfk, fr = KF.build_krw('chain')
    kc = {'div': np.asarray(dfk, dtype=float),
          'ust5': (1 + DA.ust_tr(ki, 5, 'TNX', futures=True, fee=DA.UST_FEE)) * (1 + fr) - 1,
          'gold': (1 + DA.gold_r(ki)) * (1 + fr) - 1}
    fx = int(ki.searchsorted(pd.Timestamp('1981-04-13')))

    def ks(dr):
        wv = WB[fx:]
        p = np.empty_like(wv); p[0] = wv[0]; p[1:] = wv[:-1]
        rr = np.nan_to_num(p * lev2[fx:] + (1 - p) * dr[fx:]); rr[0] = 0
        return np.cumprod((1 + rr) * (1 - 0.001 * np.abs(np.diff(p, prepend=p[0]))))

    k1 = ks(mix_monthly_from({k: kc[k] for k in ('div', 'ust5', 'gold')},
                             {'div': .4, 'ust5': .4, 'gold': .2}, ki))
    k2 = ks(mix_monthly_from({'div': kc['div']}, {'div': 1.0}, ki))
    L20 = 20 * 252
    q1 = np.array([k1[i + L20] / k1[i] for i in range(0, len(k1) - L20, 63)])
    q2 = np.array([k2[i + L20] / k2[i] for i in range(0, len(k2) - L20, 63)])
    ok('[원화] 20년창 좌측꼬리 40/40/20 > 배당100',
       np.percentile(q1, 5) > np.percentile(q2, 5) and q1.min() > q2.min(),
       f'5분위 {np.percentile(q1,5):.1f} vs {np.percentile(q2,5):.1f}')

    # 신호원
    pxk = D['px'].reindex(ki).ffill() * (1 + pd.Series(fr, index=ki)).cumprod()
    ddk = (pxk / pxk.rolling(252, min_periods=252).max() - 1).fillna(0).values
    kd = mix_monthly_from({k: kc[k] for k in ('div', 'ust5', 'gold')},
                          {'div': .4, 'ust5': .4, 'gold': .2}, ki)
    us = ks(kd)[-1]

    def ks2(w_, dr):
        wv = w_[fx:]
        p = np.empty_like(wv); p[0] = wv[0]; p[1:] = wv[:-1]
        rr = np.nan_to_num(p * lev2[fx:] + (1 - p) * dr[fx:]); rr[0] = 0
        return np.cumprod((1 + rr) * (1 - 0.001 * np.abs(np.diff(p, prepend=p[0]))))[-1]

    krw = ks2(rule_w(ddk, -0.16, -0.16), kd)
    ok('신호원: 미국 종가 > 원화환산', us > krw * 2, f'{us:,.0f} vs {krw:,.0f}')

    # [v45] 화면이 채택 결정을 따르는가.
    # v43 §4 는 'A 는 선택지가 아니라 참조'로 결정했는데 signal.html 은 계속
    # 고를 수 있게 두고 있었다. 문서와 화면이 어긋나는 걸 아무도 안 보고 있었다.
    # [2026-09-04 코드리뷰] 종전엔 else 가 없어, signal.html 이름만 바뀌어도 아래 화면 검사가
    # 통째로 조용히 사라졌다(무관한 관문 6개는 이 블록 밖으로 꺼냈다 — 위 '저장소 위생 관문').
    if not _need('화면 검사(i5_decisions)', 'signal.html'):
        return
    if True:
        h = io.open('signal.html', encoding='utf-8').read()
        # [v61] A 를 화면에서 완전히 뺐다. 판정 근거는 위 B>A 재계산이 계속 지킨다.
        ok("화면: A(-16/-11) 가 없다",
           "'−16 / −11'" not in h and "const ORDER = ['B'];" in h,
           'signal.html STRAT · ORDER')
        ok("화면: 기본 규칙이 B 다", "let sel  = 'B';" in h, 'signal.html sel')
        ok("화면: 저장된 옛 선택값을 지운다",
           "localStorage.removeItem(SKEY)" in h, 'localStorage 마이그레이션')
        # [v61] 지표에 눈금이 붙는가 — 숫자만으로는 체감이 안 된다
        # [v72] 카드 눈금은 소유자 요청으로 제거 — 비교는 성과 비교표 한 곳에서만.
        #       벤치마크와 전략 3줄(채택안/배당100/헤지 60/40)이 표에 있는지 본다.
        # [v73] 비교표는 전략 4줄 (벤치 줄은 소유자 요청으로 제거, 데이터는 JSON 유지).
        #       헤지 방어 추천(mix)이 파랑으로 표시되는지도 본다.
        # [v78] 소유자 명명 규약: −16 기본 / −16 배당 / 헤지6/4 기본 / 헤지6/4 배당
        # [v85] 추천 표기는 파란 전략명(tr.rec)뿐 — ★추천 텍스트는 소유자 지시로 금지.
        ok("화면: 비교표 전략 4줄 + 추천은 파랑만",
           "strategies_hedge_div" in h and h.count("헤지6/4") >= 3
           and "★추천" not in h and "tr.rec td.strat" in h,
           '−16 기본·배당 / 헤지6/4 기본·배당, 추천=파란 전략명 (v85)')
        ok("화면: 설명서 탭 연결", 'href="guide.html"' in h and os.path.exists('guide.html'),
           '별도 화면 설명서 (v78)')
        ok("화면: 업데이트 노트 탭 연결",
           'href="notes.html"' in h and os.path.exists('notes.html'),
           '세 번째 탭 (v142)')
        if os.path.exists('guide.html'):
            g = io.open('guide.html', encoding='utf-8').read()
            # [2026-09-04 코드리뷰] 「반드시 이해」는 리드문(138행)·목차 링크(169행)에도 있어
            #   <section id="must"> 를 통째로 지워도 통과했다(실측). 섹션 id 로 본다.
            ok("설명서: 필수 절 존재",
               'id="t4"' in g and 'id="must"' in g and 'href="./"' in g,
               'T4 상세 + 이해 필수 6가지(section id=must) + 돌아가기 탭')
        # [v145] 화면이 시세를 **표시 경로로만** 쓰는가 (판정 결합 차단은 g_signal_coupling)
        ok('시세: 화면이 시세를 표시 경로로만 쓴다',
           'loadPrice' in h and 'chgBadge' in h,
           'price.json 은 배지·현재가 기본값에만 (v145)')
        ok("화면: 임계점 거리 게이지 + 궤적 경고",
           "function paintProx" in h and 'id="proxBox"' in h and "방어 트리거" in h,
           '여유/접근/근접 + 트리거 발생 (v73)')
        # [v185] 포지션 계산기 삭제 — 검사를 없애지 않고 **책임을 물려받은 쪽**으로 옮긴다.
        #   「이 돈으로 몇 주 사면 되나」는 이제 포트폴리오의 「오늘의 행동」이 한다
        #   (현금을 넣으면 매수 주수·소요금액·잔여현금까지 나온다 — v185 실측).
        ok("화면: 오늘의 행동(주수·금액 지시)",
           "function portCompute" in h and 'id="portAction"' in h
           and "오늘의 행동" in h and "주문 메모 복사" in h,
           '보유+현금 → 목표비중 차이 → 매수/매도 주수 (v89·v185)')
        # [v191] 전환 **다음 날부터** 상단이 「오늘 할 일 없음」이 되던 구멍 — 보유가 판정
        #   반대편에 남아 있으면 미체결 경고가 상단에 남아야 한다(04 §5-8 의 −96.5% 는
        #   「안 판 채로 다음 신호까지」다). 평시 한 줄 자체는 그대로 있어야 한다.
        ok("화면: 전환 미체결 경고(전환 다음 날 이후)",
           "function drawPending" in h and "function wrongSideWeight" in h
           and "<b>전환 미체결</b>" in h and "오늘 할 일 없음" in h,
           '보유가 판정 반대편이면 상단 경고 유지 · 체결 기록으로 해제 (v191)')
        # [v196] 접은 것은 접혔을 뿐 내용은 남아야 한다 — 각주 3문단·타임머신·체크리스트 한 줄.
        ok("화면: 성과표 각주·타임머신은 접힘(details) + 전환일 한 줄",
           'id="perfNoteFold"' in h and 'id="tmFold"' in h and "fold.hidden = false" in h
           # [2026-09-04 코드리뷰] 종전 두 조건('75번(54%)' · '−96.5%')은 v165 FACTS 배열과
           #   주석이 대신 만족시켜, 체크리스트 한 줄을 지워도 통과했다 — CLAUDE v196 이
           #   「소유자가 이상하다면 이 한 줄만 되돌린다」고 적은, 가장 지워지기 쉬운 줄이다.
           #   class="chkmiss" 도 CSS·v160 줄에 있어 무임승차한다 → 그 줄에만 있는 문구로.
           and '망설여진다면' in h,
           '내용 무삭제 접기 (v196) — 각주 3문단 검사는 아래 별도')
        # [v198] 바깥 링크 스트립 — 소유자 「너무 중요한 거라 최상단에」. 세 링크가 신호 화면에, 표는 설명서 맨 위(#links).
        if os.path.exists('guide.html'):
            gd = io.open('guide.html', encoding='utf-8').read()
            ok("화면: 바깥 링크 스트립(구글 파이낸스·네이버 증권·418660) + 설명서 #links",
               'id="extbar"' in h and 'google.com/finance' in h and 'm.stock.naver.com/' in h
               and 'stock/418660/total' in h and 'id="links"' in gd
               # ★ .index() 는 없으면 ValueError 로 **게이트를 통째로 죽인다**(ok 가 불리기 전에
               #   터져 I7·I10·I14·I9·I8 이 안 돈다). 존재 검사를 앞에 둔다.
               and '<section id="what"' in gd
               and gd.index('id="links"') < gd.index('<section id="what"'),
               '표는 설명서 최상단(§① 앞), 스트립은 신호 화면 (v198)')
        # [2026-09-04 코드리뷰] 종전 두 조건은 .glbl(261행)·.minibar(412행) 같은 **다른
        #   컴포넌트**가 대신 만족시켜, 성과표 고정열 규칙을 지워도 통과했다(실측).
        #   412px 가로 스크롤 금지가 걸린 그 규칙 자체를 본다.
        ok("화면: 모바일 고정열(Sticky)",
           "td.strat{position:sticky" in h.replace(" ", ""),
           '성과표 첫 열 고정 (v73) — 412px 가로 스크롤 금지의 근거')
        ok("화면: T4 그림자 패널 (평가 전용)",
           "function drawT4" in h and 'id="t4Panel"' in h and "채택안이 아닙니다" in h,
           'oos_log.csv 요약 표시 (v75)')
        # [v63] 같은 기간으로 맞춘 표 — 최종배수 세로비교 함정의 정면 해법
        ok("화면: 같은 기간 비교표가 있다",
           'function drawHoriz' in h and 'id="horizBody"' in h, '최근 5/10/15/20년')
        ok("화면: 기준마다 실제 구간을 적는다", 'class="per"' in h, '시작~끝 (n.n년)')
        # [v60] 6개를 다 그리는가. 최종배수를 빼면 실물 3.2년 구간이 왜곡돼 보인다.
        # [v61] 렌더가 cell(...) → row(...) 로 바뀌어 둘 다 허용했었다.
        # [v172] ★ v168 이 규칙 패널(drawPicker)을 지우면서 이 6개가 조용히 깨졌다.
        #   지표는 화면에 그대로 있다 — 성과표(drawPerf)가 그린다. 검사만 삭제된
        #   함수를 겨누고 있었다. 검사의 **뜻**(지표 6종이 화면에 다 있는가)은 그대로
        #   두고 **보는 곳**만 살아 있는 렌더로 옮긴다. 지표를 실제로 빼면 여전히 실패한다.
        #   ※ 라벨 대소문자도 화면을 따른다(옛 검사는 drawPicker 의 CALMAR 표기였다).
        for lab in ('최종배수', 'MDD', 'Calmar', 'Sortino', '회복기간', 'Ulcer'):
            ok("화면: %s 를 보여준다" % lab, ('>%s</th>' % lab) in h,
               '지표 6종 — 성과표 열 머리 (v172)')
        ok("화면: Ulcer 설명이 정의문이 아니다", '낙폭의 제곱평균' not in h,
           '「늘 얼마나 물속이었나」로 읽히게')
        # [v130] 지표 풀이(metkey) 패널과 체감 풀이 5종은 소유자 지시로 삭제됨
        #        (재도입 금지 — CLAUDE.md §4 v130). 대체 검사: 심사 줄 + 등급표.
        ok("화면: 전략별 심사 줄 (v130)", 'gCal(' in h and '통상 눈금' in h,
           '지표 풀이 패널 대신 성과표 아래 전략별 심사 한 줄')
        ok("화면: 등급표 3종 (v121→v130)",
           all(('const %s' % f) in h for f in ('gCal', 'gSor', 'gUlc')),
           'Calmar·Sortino·Ulcer 고정 등급 룩업')
        # 체결 시각이 한 화면에서 두 값으로 갈리면 안 된다 (v18 잔재)
        ok("화면: 체결 시각이 하나로 통일돼 있다",
           '09:30~15:00' not in h and h.count('09:05~15:20') >= 2,
           'LP 호가 의무 시간대 — 전략_v21 §13.4')
        # [v129·v131] 면책·54년 문장 삭제로 각주는 3문단(주의·전제·심사)이 현행.
        ok("화면: 비교표 각주가 문단으로 끊겨 있다", h.count('<p><span class="lead">') >= 3,
           '한 덩어리로 이어 쓰면 아무도 안 읽는다')
        # [v71] v67 감사 조건 ② — 집중도·급락 비대칭 공개가 화면에 있어야 한다
        # [v131] 96% → 약 97%(21세기 기준 재정렬) — 퍼센트 대신 서사 존재를 검사.
        ok("화면: 기여 집중(닷컴)·급락 무방비 공개", '급락은 거의 못 피합니다' in h
           and '닷컴 한 사건' in h, 'v67 C-1·C-3 — 최종배수 서사의 조건부를 명시')
        # [v60] I9 는 docs 만 훑는다. 화면 문구에 폐기된 방어자산 조합이 남아 있었다.
        for bad in ('배당50/금50', '배당50 / 금50'):
            ok("화면: 폐기 조합 '%s' 없음" % bad, bad not in h,
               'v23 채택안은 배당40/국채40/금20')
        # [v172] 같은 회귀. 옛 문자열은 drawPicker 의 기준 설명줄이었다 —
        # 그 역할(기간이 다른 최종배수를 정규화 수치와 함께 준다)은 지금 성과표의
        # CAGR 열 + 세로비교 경고가 맡는다. 둘 다 있어야 통과한다.
        ok("화면: 최종배수 옆에 CAGR 과 세로비교 경고가 있다",
           '>CAGR</th>' in h and '세로로 비교하면 안 됩니다' in h,
           '최종배수는 기간이 다르면 비교 불가 — 정규화 수치를 함께 준다 (v172)')

        # [v46] 화면 개정 시점 주입 자리. 없으면 배포 때 stamp_rev.py 가 실패한다.
        MARK = "const HTML_REV = '__HTML' + '_REV__';"
        ok('화면: 개정 시점 주입 자리가 있다', MARK in h,
           'deploy/stamp_rev.py 가 이 문자열을 찾는다')
        # [2026-09-04 코드리뷰] 종전엔 604행의 **주석**(「id=htmlRev 는 verify_all 검사
        #   대상이라 유지」)이 이 검사를 대신 통과시켰다 — div 를 지워도 초록불이었다.
        #   검사가 있다고 알리려고 쓴 주석이 그 검사를 무력화한 셈이다. 렌더 대상을 본다.
        ok('화면: 개정 표시가 종가일과 분리돼 있다',
           'class="rev" id="htmlRev"' in h and 'id="asof"' in h,
           '두 자리 모두 존재 — 주석이 아니라 실제 div')
        # 안 쓰는 글꼴을 참조하면 대체글꼴로 떨어진다 (v46 에서 전부 Pretendard 로 바꿨다)
        for f in ('IBM Plex Mono', 'Archivo'):
            ok('화면: %s 참조 없음' % f, f not in h, '전부 Pretendard')



# ------------------------------------------------------------------ I11
def i11_freeze():
    """[v57] 규칙 동결 — 2026-08-27 이후는 순수 OOS 표본이다.

    규칙이 바뀌면 그 표본이 사라진다. 그래서 **매 push 마다**(빠른 모드 포함)
    코드·화면이 data/freeze.json 과 일치하는지 확인한다.
    바꾸려면 freeze.json 을 **의도적으로** 고쳐야 한다 — 실수로는 안 바뀐다.
    """
    head("I11. 규칙 동결 — 동결 이후는 평가만 한다")
    if not os.path.exists('data/freeze.json'):
        ok('freeze.json 존재', False, '파일 없음', warn=True)
        return
    fz = json.load(io.open('data/freeze.json', encoding='utf-8'))
    R = fz['rule']
    ok('진입선 -0.16', abs(R['enter'] + 0.16) < 1e-9, 'freeze.json')
    ok('복귀선 -0.16', abs(R['exit'] + 0.16) < 1e-9, 'freeze.json')
    ok('룩백 252일', R['lookback'] == 252, 'freeze.json')
    if os.path.exists('deploy/update_signal.py'):
        u = io.open('deploy/update_signal.py', encoding='utf-8').read()
        ok('신호 생성기가 동결 규칙과 같다',
           '("B", "−16 / −16", -0.16, -0.16)' in u and 'DEFAULT = "B"' in u,
           'update_signal.py STRATS')
        # [v71] v67 감사 조건 ① — 라이브 신호원 = 수정 종가 (백테스트와 동일 기준).
        # 비수정으로 되돌아가면 27년 중 11일 신호가 백테스트와 갈린다.
        # [2026-09-04 코드리뷰] 종전 `'adjclose' in u` 는 **주석과 경고문으로도 통과**했다
        #   (실측: 코드 줄을 비수정 종가로 되돌려도 81·86행 문구가 남아 PASS).
        #   실제로 값을 뽑는 줄을 본다.
        ok('신호원이 수정 종가(adjclose)다',
           'ind.get("adjclose")' in u,
           'update_signal.py fetch — v67 B-1 해소 (11일 신호 갈림)')
    if os.path.exists('signal.html'):
        hh = io.open('signal.html', encoding='utf-8').read()
        ok('화면이 동결 규칙과 같다', 'enter:-0.16, exit:-0.16' in hh,
           'signal.html STRAT.B')
        # [2026-09-04 코드리뷰] ★ 동결 규칙 세 파라미터 중 **화면의 룩백만 아무 관문에도
        #   안 걸려 있었다**(verify_all 에 LOOKBACK 이 0회 등장). 252 → 200 으로 고쳐도
        #   freeze.json 은 그대로 252 라 위 검사가 통과하고, 'enter:-0.16, exit:-0.16'
        #   문자열도 그대로라 통과한다 — 초록불인 채 설명서 §⑩ 비상 수동 판정이 200일
        #   창으로 돌아간다(04 §5-25 가 한 세션을 다 써서 기각한 바로 그 대안이다).
        m = re.search(r'const\s+LOOKBACK\s*=\s*(\d+)', hh)
        ok('화면 룩백이 동결값과 같다', bool(m) and int(m.group(1)) == R['lookback'],
           'signal.html const LOOKBACK = %s vs freeze %s'
           % (m.group(1) if m else '(없음)', R['lookback']))
    if os.path.exists('deploy/update_signal.py'):
        uu = io.open('deploy/update_signal.py', encoding='utf-8').read()
        m2 = re.search(r'^LOOKBACK\s*=\s*(\d+)', uu, re.M)
        ok('신호 생성기 룩백이 동결값과 같다',
           bool(m2) and int(m2.group(1)) == R['lookback'],
           'update_signal LOOKBACK = %s vs freeze %s'
           % (m2.group(1) if m2 else '(없음)', R['lookback']))
    n = 0
    if os.path.exists('data/oos_log.csv'):
        n = sum(1 for _ in io.open('data/oos_log.csv', encoding='utf-8')) - 1
    # [2026-09-04 코드리뷰] 종전 `ok(..., n >= 1, ..., warn=(n < 1))` 은 조건이 거짓인
    #   경우가 전부 warn 이라 **FAIL 경로가 구조적으로 도달 불가**였다. 장부가 통째로
    #   비워져도 WARN 한 줄이 전부였다(§2 절대 수정 금지 실측 장부다).
    #   → 「아직 안 쌓임」은 그대로 WARN, **「있던 것이 줄었다」는 FAIL** 로 가른다.
    ok('OOS 장부가 쌓이고 있다', n >= 1,
       '%d영업일 (동결 %s 이후)' % (n, fz['frozen_at']), warn=(n < 1))
    try:
        prev = subprocess.run(['git', 'show', 'HEAD:data/oos_log.csv'], capture_output=True,
                              text=True, encoding='utf-8', check=True, timeout=20).stdout
        pn = max(0, len([l for l in prev.splitlines() if l.strip()]) - 1)
        ok('OOS 장부가 줄지 않았다', n >= pn,
           '작업본 %d행 vs HEAD %d행 — 줄었다면 장부가 잘린 것이다' % (n, pn))
    except Exception:
        pass                                  # 첫 커밋·git 부재는 이 검사의 대상이 아니다


# ------------------------------------------------------------------ I12
def i12_shadow():
    """[v82] T4 그림자 열 무결성 — 기록이 정의와 모순되면 잡는다.

    재계산 대조는 하지 않는다 — 수정주가 전체 갱신으로 과거 원자료가 미세 조정되므로
    기록 당시 값과 어긋나는 것이 정상이다(기록은 그날의 동결 코드가 본 값이다).
    여기서는 **정의상 불변식**만 본다: votes ∈ {0..4} · rv > 0 · w ∈ [0,1] ·
    (votes < 2 ⟺ w == 0). 위반은 기록 파이프라인 오염을 뜻한다.
    """
    head("I12. T4 그림자 열 무결성 (평가 전용 기록 — v69/v80)")
    p = 'data/oos_log.csv'
    if not os.path.exists(p):
        ok('oos_log.csv 존재', False, '파일 없음', warn=True)
        return
    import csv
    bad, n = [], 0
    with io.open(p, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if (r.get('t4_votes') or '') == '':
                continue                       # 그림자 실패일은 빈 칸이 정상
            n += 1
            try:
                v = int(r['t4_votes']); rv = float(r['t4_rv']); w = float(r['t4_w'])
                if not (0 <= v <= 4 and rv > 0 and 0 <= w <= 1
                        and ((v < 2) == (w == 0))):
                    bad.append(r['as_of'])
            except (KeyError, ValueError, TypeError):
                bad.append(r.get('as_of', '?'))
    ok('그림자 기록이 정의와 모순 없음', not bad,
       '%d행 검사%s' % (n, ' · 위반: ' + ','.join(bad[:3]) if bad else ''))
    # [2026-09-04 코드리뷰] 종전엔 t4_votes 가 **전부 비어도** continue 로 다 건너뛰어
    #   n=0 · bad=[] → 「0행 검사 PASS」가 떴다. 열 삭제·열명 변경·전체 공백 세 경우가
    #   전부 같은 초록불이었다 — 파이프라인 사망과 정상을 구별하지 못한다.
    tot = max(0, sum(1 for _ in io.open(p, encoding='utf-8')) - 1)
    ok('그림자 기록이 실제로 쌓여 있다', n > 0 or tot == 0,
       '장부 %d행 중 그림자 %d행 — 0 이면 T4 파이프라인이 죽은 것이다' % (tot, n),
       warn=(tot <= 3))

    # [v73] 01 문서 AUTO-STATS 블록이 최신 스냅샷과 같은 끝 날짜인가
    if os.path.exists('01_Strategy_Logic.md') and os.path.exists('data/strategy_stats.json'):
        doc = io.open('01_Strategy_Logic.md', encoding='utf-8').read()
        S2 = json.load(io.open('data/strategy_stats.json', encoding='utf-8'))
        i0, j0 = doc.find('<!-- AUTO-STATS:START'), doc.find('<!-- AUTO-STATS:END -->')
        endd = S2['scenarios'][0]['strategies']['B']['end']
        ok('01 문서 AUTO-STATS 블록 동기화', i0 >= 0 and j0 > i0 and endd in doc[i0:j0],
           '%s (build_stats 가 자동 갱신)' % endd)


# ------------------------------------------------------------------ I13
def i13_protocol():
    """[2026-09-02] B 자체의 OOS 판정 규약 — 사후 수정 방지.

    T4 에는 v80 §6 부속서가 있었지만 B 에는 없었다(04 §5-23). 등록된 규약은
    data/oos_protocol_b.json 이고 지문이 맞지 않으면 실패한다 — 사건이 쌓인 뒤
    관문을 손대는 것(사후 재량)을 **실수로는** 못 하게 한다. 고치려면 지문을
    의도적으로 갱신하고 02 §5-1 에 날짜·이유를 남겨야 한다.
    지문 규약 = research/oos_protocol_b.py fingerprint() 와 동일.
    """
    head("I13. B 판정 규약 지문 — 사후 수정 방지 (02 §5-1)")
    p = 'data/oos_protocol_b.json'
    if not os.path.exists(p):
        ok('oos_protocol_b.json 존재', False, '파일 없음', warn=True)
        return
    import hashlib
    j = json.load(io.open(p, encoding='utf-8'))
    body = {k: v for k, v in j.items() if k != 'fingerprint'}
    fp = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                   separators=(',', ':')).encode('utf-8')).hexdigest()[:16]
    ok('규약 지문 일치', fp == j.get('fingerprint'), f"재계산 {fp} vs 기록 {j.get('fingerprint')}")
    if os.path.exists('data/freeze.json'):
        F = json.load(io.open('data/freeze.json', encoding='utf-8'))
        ok('규약이 가리키는 동결 지문 = freeze.json',
           j['applies_to']['freeze_fingerprint'] == F['fingerprint'], F['fingerprint'])
    if os.path.exists('02_Risk_Management.md'):
        doc = io.open('02_Risk_Management.md', encoding='utf-8').read()
        ok('02 §5-1 이 같은 지문을 적고 있다', j['fingerprint'] in doc, '문서 ↔ JSON 결합')
    ok('평가기 존재', os.path.exists('research/oos_protocol_b.py'),
       'python research/oos_protocol_b.py --oos')


def i6_live():
    head("I6. 라이브 정합 — signal.json 이 재계산과 맞는가")
    if not os.path.exists('data/signal.json') or not os.path.exists('data/qqq.csv'):
        ok('signal.json 존재', False, '파일 없음', warn=True)
        return
    j = json.load(io.open('data/signal.json', encoding='utf-8'))
    px = pd.read_csv('data/qqq.csv')
    px['Date'] = pd.to_datetime(px['Date'])
    s = px.set_index('Date')['Close'].sort_index()
    dd = (s / s.rolling(252, min_periods=60).max() - 1)
    ok('as_of 가 데이터 마지막 날과 일치', j['as_of'] == str(s.index[-1].date()),
       f"json {j['as_of']} vs csv {s.index[-1].date()}")
    ok('낙폭 재계산 일치 (±0.01%p)', abs(j['dd'] - dd.iloc[-1] * 100) < 0.01,
       f"json {j['dd']}% vs 재계산 {dd.iloc[-1]*100:.2f}%")

    # [v45] signal.json 은 strategy_stats.json 의 **사본**을 안에 들고 있고
    # 화면은 그 사본을 우선한다. 둘이 어긋나면 라이브가 옛 수치를 보여준다.
    # v36(국채 정정) 뒤 실제로 그랬다: 화면 263,062 vs 실제 214,076 (23% 과대).
    if os.path.exists('data/strategy_stats.json'):
        S = json.load(io.open('data/strategy_stats.json', encoding='utf-8'))
        emb = (j.get('stats') or {}).get('generated_at')
        ok('signal.json 내장 stats 가 strategy_stats.json 과 같은 판',
           emb == S.get('generated_at'), f"내장 {emb} vs 원본 {S.get('generated_at')}")
        for sc in S['scenarios']:
            e = [x for x in (j.get('stats') or {}).get('scenarios', [])
                 if x['key'] == sc['key']]
            if not e:
                ok(f"내장 stats 에 {sc['key']} 있음", False, '없음'); continue
            for k in ('B', 'A'):
                v0 = sc['strategies'][k]['final']; v1 = e[0]['strategies'][k]['final']
                ok(f"내장 {sc['key']} {k} 최종배수 일치",
                   abs(v1 / v0 - 1) < 1e-6, f'{v1:,.1f} vs {v0:,.1f}')
                # [v60] 새 지표도 사본에 실려야 한다. 없으면 화면이 '—' 만 뜬다.
                for fld in ('ulcer', 'uw_months', 'dd_mean'):
                    a = sc['strategies'][k].get(fld)
                    b = e[0]['strategies'][k].get(fld)
                    ok(f"내장 {sc['key']} {k} {fld} 일치",
                       a is not None and b is not None and abs(b - a) < 1e-9,
                       f'{b} vs {a}')
            # [v63] 같은 기간 비교표가 읽는 값
            for k in ('B',):
                a = (sc['strategies'][k].get('horizons') or {}).get('20')
                b = (e[0]['strategies'][k].get('horizons') or {}).get('20')
                # [2026-09-04 코드리뷰] 종전 `(a is None and b is None)` 탈출구 때문에
                #   build_stats 가 horizons 를 안 내면 네 시나리오 전부 PASS 였다
                #   (kr_real 은 지금도 None vs None 으로 통과 중이다 — 아래 예외로 명시).
                #   바로 위 ulcer/uw_months/dd_mean 루프는 이미 둘 다 있어야 통과한다.
                need = sc['strategies'][k].get('years', 0) >= 20   # 20년 창을 낼 수 있는 표본만
                ok(f"내장 {sc['key']} {k} horizons 일치",
                   (a is not None and b is not None and abs(b - a) < 1e-9)
                   if need else (a is None and b is None) or
                   (a is not None and b is not None and abs(b - a) < 1e-9),
                   f'{b} vs {a}' + ('' if need else ' (표본 20년 미만 — 없을 수 있다)'))
            # [v61] 화면 눈금이 되는 벤치마크도 사본에 있어야 한다
            for bk in ('lev', 'def'):
                a = (sc.get('benchmarks') or {}).get(bk, {}).get('ulcer')
                b = (e[0].get('benchmarks') or {}).get(bk, {}).get('ulcer')
                ok(f"내장 {sc['key']} 벤치 {bk} 있음",
                   a is not None and b is not None and abs(b - a) < 1e-9,
                   f'{b} vs {a}')
    # [2026-09-04 코드리뷰] ★ 종전 I6 는 as_of·dd·state **셋만** 재계산했다. 변조 시험에서
    #   close 709.24→1.0 · high_252 745.34→999 · gap_pp 11.2→0.1 · next_line −16→−11 ·
    #   changed_today False→True · enter −16→−30 이 **여섯 개 전부 FAIL 0건**이었다
    #   (대조군으로 dd·state 는 정상 FAIL — 하네스는 유효했다).
    #   그런데 changed_today 는 화면의 전환일 체크리스트·signal_alert 카톡·watchdog switchday
    #   **셋을 동시에** 구동하고, high_252 는 전환 기준가(×0.84), gap_pp 는 근접 카톡을 구동한다.
    #   update_signal 의 prev 계산이 깨져 진짜 전환일에 changed_today=false 를 내면
    #   알림도 체크리스트도 안 뜨는데(04 §5-8 의 −96.5% 경로) I6 는 PASS 를 찍었다.
    #   → 화면·알림이 읽는 필드를 전부 재계산으로 대조한다.
    ok('close 재계산 일치', abs(float(j['close']) - float(s.iloc[-1])) < 0.005,
       "json %s vs csv %.2f" % (j['close'], s.iloc[-1]))
    rm = s.rolling(252, min_periods=60).max().iloc[-1]
    ok('high_252 재계산 일치 (전환 기준가의 재료)',
       abs(float(j['high_252']) - float(rm)) < 0.005, "json %s vs 재계산 %.2f" % (j['high_252'], rm))
    for k, en, ex in (('B', -0.16, -0.16), ('A', -0.16, -0.11)):
        st = []
        cur = 'QLD'
        for v in dd.values:
            if pd.isna(v):
                st.append(cur)
                continue
            if cur == 'QLD' and v <= en:
                cur = 'SCHD'
            elif cur == 'SCHD' and v > ex:
                cur = 'QLD'
            st.append(cur)
        e = j['strategies'][k]
        ok(f'상태 재계산 일치 ({k})', e['state'] == cur, f"json {e['state']} vs 재계산 {cur}")
        # 전환 여부 — 마지막 이틀의 상태가 다른가
        chg = len(st) >= 2 and st[-1] != st[-2]
        ok(f'changed_today 재계산 일치 ({k})', bool(e.get('changed_today')) == chg,
           "json %s vs 재계산 %s — 화면 체크리스트·카톡·파수꾼이 이 값을 쓴다"
           % (e.get('changed_today'), chg))
        ok(f'prev_state 재계산 일치 ({k})',
           'prev_state' not in e or e['prev_state'] == (st[-2] if len(st) >= 2 else cur),
           "json %s vs 재계산 %s" % (e.get('prev_state'), st[-2] if len(st) >= 2 else cur))
        # 다음 선과 거리 — 방어면 복귀선(exit), 공격이면 진입선(enter)
        line = ex if cur == 'SCHD' else en
        ok(f'next_line 재계산 일치 ({k})',
           'next_line' not in e or abs(float(e['next_line']) - line * 100) < 0.01,
           "json %s vs 재계산 %.1f" % (e.get('next_line'), line * 100))
        gap = abs(float(dd.iloc[-1]) * 100 - line * 100)
        ok(f'gap_pp 재계산 일치 ({k})',
           'gap_pp' not in e or abs(float(e['gap_pp']) - gap) < 0.06,
           "json %s vs 재계산 %.2f — 근접 알림이 이 값을 쓴다" % (e.get('gap_pp'), gap))
        ok(f'진입·복귀선이 동결값 그대로 ({k})',
           abs(float(e['enter']) - en * 100) < 1e-9 and abs(float(e['exit']) - ex * 100) < 1e-9,
           "enter %s exit %s" % (e.get('enter'), e.get('exit')))
    age = (pd.Timestamp.now(tz='UTC').normalize().tz_localize(None) - s.index[-1]).days
    ok('신호 신선도 (5일 이내)', age <= 5, f'{age}일 전', warn=True)


# ------------------------------------------------------------------ I7
def i7_stats(D):
    head("I7. 공표 수치 — strategy_stats.json 이 현재 코드와 맞는가")
    p = 'data/strategy_stats.json'
    if not os.path.exists(p):
        ok('strategy_stats.json 존재', False, '파일 없음', warn=True)
        return
    j = json.load(io.open(p, encoding='utf-8'))
    from axis_lib import rule_w
    from axis_defmix import materials, mix_monthly_from, sim_def
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, D['idx'])
    live = [x for x in j['scenarios'] if x['key'] == 'us_1972'][0]['strategies']['B']['final']
    now = float(sim_def(D, rule_w(D['ddv'], -0.16, -0.16), defr).iloc[-1])
    ok('us_1972 B 가 현재 코드와 일치 (±1%)', abs(now / live - 1) < 0.01,
       f'json {live:,.0f} vs 재계산 {now:,.0f}')
    # [v61] 화면 눈금이 되는 '2배 그냥 보유'가 실제로 2배 보유인가.
    #       I10 P1 이 재는 MDD(-90% 이하)와 같은 성질을 공표값에서 확인한다.
    for x in j['scenarios']:
        b = (x.get('benchmarks') or {}).get('lev')
        if not b:
            ok(f"{x['key']} 벤치 lev 존재", False, '없음'); continue
        st = x['strategies']['B']
        ok(f"{x['key']} 벤치가 전략과 같은 기간", abs(b['years'] - st['years']) < 0.05,
           f"{b['years']}년 vs {st['years']}년")
        # 장기 표본에서만 건다. kr_real(3.2년)은 2배 보유 MDD -41.0% 가 전략
        # -44.9% 보다 **얕다** — 그 구간엔 큰 폭락이 없어 잔전환 손실이 더 컸다.
        # 이건 버그가 아니라 표본이 얇다는 뜻이고, 화면도 그렇게 경고하고 있다.
        if st['years'] >= 20:
            ok(f"{x['key']} 벤치 lev 가 전략보다 깊게 빠진다", b['mdd'] < st['mdd'],
               f"{b['mdd']:.1f}% vs {st['mdd']:.1f}%")
        else:
            ok(f"{x['key']} 벤치 MDD 비교는 건너뜀 (표본 {st['years']}년)", True,
               f"{b['mdd']:.1f}% vs {st['mdd']:.1f}% — 얇은 표본", warn=True)


# ------------------------------------------------------------------ I8
SHARED_SEAL = {
    # [2026-09-04 코드리뷰] axis_lib 3종 갱신 — rule_w(중복 갈래 제거) ·
    # lev_r(c_k 인자 추가) · accumulate(0/1 가드 + rk/buy_cost 인자).
    # ★ 출력은 안 바뀐다: 문턱 격자 681조합 · dip/park 전 조합 · 세율 격자
    #   전수를 수정 전후로 재서 지문 15/15 동일함을 확인하고 갱신했다.
    'accumulate': ('axis_lib.py', 'e4c0d328080d'),
    'lev_r': ('axis_lib.py', '8d551b166196'),
    'mix_monthly': ('hist_defasset.py', 'da5c3ec9a7b3'),
    'mix_monthly_from': ('axis_defmix.py', 'adb498b68308'),
    'mix_monthly_parts': ('hist_defasset.py', '28e5cb665804'),
    'rule_w': ('axis_lib.py', 'dc1de1e02376'),
    # [2026-09-04 코드리뷰 2차] ust_tr 갱신 — ① y.bfill() 제거(원자료 시작 이전을
    # 첫 관측 금리로 소급해 채우던 미래 당겨쓰기: ^TYX 1972~77 의 1,311행 9.5%가
    # 연 7.70% 고정 · 일간 σ 8.4e-06 = 실제의 1/1000 이었다) · ② fee 를 futures
    # 블록 밖으로(현물형에서 조용히 무시되던 것).
    # ★ 사용처 재실행 결과: ust5/ust10(TNX 1962~)은 지문 불변 → MIX_V23·mix_monthly·
    #   공표 방어 바스켓 전부 그대로. 바뀐 것은 TYX 기반 ust20/ust30 뿐이고,
    #   공표 strategy_stats.json 의 전략 수치(B 217110.075 / A 128074.913 / us_2000
    #   B 167.315)는 재계산 결과 소수점까지 동일함을 확인했다.
    'ust_tr': ('hist_defasset.py', '2627b81cc9a8'),
}


def i8_deps():
    """공용 모형이 바뀌었는데 사용처를 안 돌린 것을 잡는다 (docstring ⑤ 유형).

    [2026-09-04 코드리뷰] ★ 종전 이 함수에는 **ok() 호출이 하나도 없었다** — 사용처 수를
      print 하고 「확인하라」는 사람용 문장으로 끝났다. 그런데 모듈 docstring 은 이것을
      「불변식 — 하나라도 깨지면 실패」 목록에 올려놓고 「⑤ 는 이 파일이 막는다」고 약속한다.
      막지 않았다. 실패할 수 없는 것은 관문이 아니다(§-1 ⑤).
    ★ 게다가 조사 범위가 glob('*.py')+glob('deploy/*.py') 라 **research/ 를 통째로 뺐다**.
      실측 오차: lev_r 「1개」로 찍혔지만 실제 34개 · accumulate 4 vs 55 · rule_w 3 vs 43.
      탐색어 'mix_monthly(' 는 mix_monthly_from( 을 부분일치 못 해 28개가 안 보였고,
      정의 파일 자신을 「사용처」로 셌다.

    → **봉인으로 바꿨다**: 공용 모형 7종의 함수 소스를 해시해 아래 상수와 대조한다.
      모형을 고치면 여기서 실패하고, 사용처를 다시 돌린 뒤 **의도적으로** 이 상수를
      갱신해야 통과한다. 공표 수치 쪽은 I7 이 us_1972 B 를 라이브 엔진으로 재계산해 지킨다.
    """
    head("I8. 의존성 — 공용 모형이 바뀌면 사용처를 다시 돌렸는가")
    import ast
    import glob
    files = sorted(set(glob.glob('*.py') + glob.glob('deploy/*.py')
                       + glob.glob('research/*.py') + glob.glob('audit/*.py')
                       + glob.glob('내가_보는_것/*.py')))
    srcs = {}
    for f in files:
        try:
            srcs[f] = io.open(f, encoding='utf-8').read()
        except Exception:
            pass
    drift = []
    for fn, (deffile, want) in sorted(SHARED_SEAL.items()):
        src = srcs.get(deffile)
        seg = None
        if src is not None:
            try:
                for node in ast.parse(src).body:
                    if isinstance(node, ast.FunctionDef) and node.name == fn:
                        seg = ast.get_source_segment(src, node)
            except Exception:
                seg = None
        got = hashlib.sha256((seg or '').encode('utf-8')).hexdigest()[:12] if seg else '(못찾음)'
        # 사용처는 **모듈 한정 호출까지** 세고 정의 파일은 뺀다 (DA.ust_tr(...) 형태)
        pat = re.compile(r'(?<!\w)' + re.escape(fn) + r'\s*\(')
        users = [f for f, t in srcs.items()
                 if f != 'verify_all.py'
                 and not re.search(r'^\s*def\s+' + re.escape(fn) + r'', t, re.M)
                 and pat.search(t)]
        if got != want:
            drift.append('%s (%s: %s → %s · 사용처 %d개)' % (fn, deffile, want, got, len(users)))
        print('    %-18s %-16s 사용처 %3d개' % (fn, deffile, len(users)))
    ok('공용 모형 7종이 봉인과 같다', not drift,
       ('바뀐 모형 %d개: %s — 사용처를 재실행하고 SHARED_SEAL 을 갱신하라'
        % (len(drift), '; '.join(drift[:3]))) if drift
       else '%d개 파일에서 사용처를 셌다 (research/·audit/ 포함)' % len(srcs))


# ------------------------------------------------------------------ I9
def i9_retired():
    """폐기된 공표 수치가 현행 문서·화면에 남아 있는가

    [왜 필요한가 — 2026-08-27]
    ISA 수치가 v33 에서 한 번, v36 에서 또 한 번 바뀌었다. 라이브 화면은 고쳤는데
    `docs/전략_v29.md`(현재 `docs/history/전략_v29.md`)에는 v36 이전 값(143.3배)이 그대로 남아 있었다.
    사용자가 "바뀐 걸 다 수정해줘" 라고 해서 발견했다.

    수치를 폐기할 때 `data/retired_numbers.json` 에 등록하면 이 검사가 막는다.
    정정 이력을 서술하는 문장(-> 나 '정정' 이 같이 있는 줄)은 통과시킨다.
    """
    import glob
    head("I9. 폐기 수치 — 옛 값이 현행 문서에 남아 있는가")
    p = 'data/retired_numbers.json'
    if not os.path.exists(p):
        ok('retired_numbers.json 존재', False, '파일 없음', warn=True)
        return
    cfg = json.load(io.open(p, encoding='utf-8'))
    allow_c = cfg.get('allow_context', [])
    CURRENT = cfg.get('current_docs', [])
    hits, missing = [], []

    # (a) '현행 상태' 문서는 폐기 수치가 있으면 안 된다 — 엄격
    # [2026-09-04 코드리뷰] ★ 두 가지를 고쳤다.
    #   ⓐ 종전엔 파일마다 13개 폐기값을 각각 훑느라 **같은 문서를 13번 다시 읽었다**
    #     (9문서 × 13값 = 117회 · 8.06MB). 한 번 읽고 줄을 한 번만 돈다.
    #   ⓑ 목록의 파일이 사라지면 조용히 continue 하고도 「9개 파일 검사」로 보고했다 —
    #     **실제로 검사한 수**를 찍고, 없는 파일은 WARN 으로 드러낸다.
    gone = [f for f in CURRENT if not os.path.exists(f)]
    if gone:
        ok('폐기 수치 검사 대상이 전부 있다', False,
           '%d개 없음: %s — 이름이 바뀌었다면 retired_numbers.json 을 고쳐야 한다'
           % (len(gone), ', '.join(gone)), warn=True)
    seen = [f for f in CURRENT if os.path.exists(f)]
    vals = [(it['value'], it['now']) for it in cfg['retired']]
    for f in seen:
        for i, line in enumerate(io.open(f, encoding='utf-8').read().splitlines(), 1):
            if any(a in line for a in allow_c):
                continue
            for v, now in vals:
                if v in line:
                    hits.append((f, i, v, now))

    # (b) 버전 문서는 그 시대의 기록이라 수치가 있는 게 맞다.
    #     대신 **정정 배너**가 있어야 한다 (읽는 사람이 현행으로 오인하지 않게).
    import glob
    # [v65] 버전 문서는 docs/history/ 로 이동했다 — 통폐합(01~04_*.md) 이후 보관층
    for f in sorted(glob.glob('docs/history/전략_v*.md')):
        txt = io.open(f, encoding='utf-8').read()
        for item in cfg['retired']:
            if item['value'] not in txt:
                continue
            if f.replace(os.sep, '/') in item.get('exempt_docs', []):
                continue
            tag = item['since']
            if not any(k in txt for k in (f'{tag} 정정', f'{tag} 수치 정정', f'{tag} 재정정',
                                          f'[{tag}]', f'{tag} 에서')):
                missing.append((f, item['value'], tag))

    for f, i, v, now in hits[:10]:
        print(f"    [현행문서] {f}:{i}  '{v}' 남아 있음 (현행 {now})")
    for f, v, tag in missing[:10]:
        print(f"    [배너없음] {f}  '{v}' 가 있는데 {tag} 정정 배너가 없다")
    ok('현행 문서에 폐기 수치 없음', not hits,
       f'{len(hits)}건' if hits else '%d개 파일 × %d개 수치 검사' % (len(seen), len(vals)))
    ok('버전 문서에 정정 배너 있음', not missing,
       f'{len(missing)}건 누락' if missing else f'{len(cfg["retired"])}종 확인', warn=True)

    # (c) [2026-09-04 코드리뷰] **정정 대장류** — CLAUDE.md 와 research/*.md 는 폐기된 주장을
    #     「이건 틀렸다」고 기록하려고 인용한다. 그래서 (a) 처럼 금지하면 오탐이 난다
    #     (실측: CLAUDE.md 의 「인용 오류 적발」 제목 줄이 걸렸다). 그러나 v186 의
    #     「자기 표본 3위」 오류는 실제로 research/ 로 번졌고 CLAUDE.md 는 그 재발 방지를
    #     「I9 관문이 막는다」고 적어 뒀는데 **I9 는 research/ 를 읽은 적이 없다.**
    #     → 값 자체는 허용하되 **가까이(±3줄) 정정 표시가 없으면** 실패시킨다.
    LEDGERS = ['CLAUDE.md'] + sorted(glob.glob('research/*.md'))
    loose = []
    for f in LEDGERS:
        if not os.path.exists(f):
            continue
        lines = io.open(f, encoding='utf-8').read().splitlines()
        for i, line in enumerate(lines):
            for it in cfg['retired']:
                if it['value'] not in line:
                    continue
                ctx = chr(10).join(lines[max(0, i - 3): i + 4])
                if not any(a in ctx for a in allow_c):
                    loose.append('%s:%d 「%s」' % (f, i + 1, it['value']))
    ok('정정 대장에 맨몸으로 남은 폐기 수치 없음', not loose,
       ('%d건: %s — 인용하려면 근처에 정정 표시를 달아라' % (len(loose), '; '.join(loose[:3])))
       if loose else '%d개 문서 확인 (CLAUDE.md · research/*.md)' % len(LEDGERS))


# ------------------------------------------------------------------ I10
def i10_premise(D):
    """전략의 전제가 아직 유효한가 — 나스닥 고유 성질에 의존한다

    [v44] 같은 규칙을 다른 지수에 적용해보니 S&P500·코스피에서는 그냥 보유에 진다.
    전략의 값어치는 「강한 장기 상승 + 극단적 레버리지 붕괴」라는 나스닥의 성질에서
    나온다. 그 성질이 변하면 우위도 사라진다. 그래서 세 가지를 감시한다.

      P1  2배 그냥 보유의 MDD 가 여전히 극단적인가 (-90% 수준)
          -> S&P500 처럼 -86% 로 얕아지면 전략의 존재 이유가 준다
      P2  기초지수가 여전히 장기 상승 추세인가
          -> 코스피처럼 횡보하면 지킬 상승이 없다
      P3  전략이 여전히 그냥 보유를 이기는가
    """
    head("I10. 전제 감시 — 나스닥 고유 성질이 유지되는가 (v44)")
    from axis_lib import rule_w, lev_r, COST
    from axis_defmix import materials, mix_monthly_from, sim_def
    idx = D['idx']
    comp = materials(D)
    defr = mix_monthly_from({k: comp[k] for k in ('div', 'ust5', 'gold')},
                            {'div': .4, 'ust5': .4, 'gold': .2}, idx)
    r2 = np.nan_to_num(lev_r(D, 2.0))
    bh = np.cumprod(1 + r2)
    bh_mdd = float((bh / np.maximum.accumulate(bh) - 1).min())
    ok('P1 2배 보유 MDD 가 -90% 이하 (전략의 존재 이유)', bh_mdd <= -0.90,
       f'{bh_mdd*100:.1f}%')

    px = D['px']
    n20 = 20 * 252
    tr = float((px.iloc[-1] / px.iloc[-n20]) ** (252 / n20) - 1) if len(px) > n20 else np.nan
    ok('P2 기초지수 최근 20년 연평균 상승 > 3%', tr > 0.03, f'{tr*100:.1f}%/년')

    st = float(sim_def(D, rule_w(D['ddv'], -0.16, -0.16), defr).iloc[-1])
    ok('P3 전략이 2배 그냥 보유를 이긴다', st > bh[-1],
       f'{st:,.0f} vs {bh[-1]:,.0f} ({st/bh[-1]:.1f}배)')


def i14_selftests():
    """[2026-09-03] 파수꾼·종가 대기 루프의 합성 셀프테스트 — 코드를 고치면 여기서 잡는다 (전체 모드만).

    v192 때 파수꾼 24경우가 스크래치에만 있었다 — 「검사를 추가했다」와 「검사가 돈다」는 다르다(v148)."""
    head("I14 셀프테스트 (파수꾼 · 종가 대기 루프)")
    import subprocess
    for label, args in (("파수꾼 모드 셀프테스트 (switchday·near·heartbeat 합성 30여 경우)",
                         ['deploy/watchdog.py', '--selftest']),
                        ("종가 대기 루프 셀프테스트 (v190 9경로)", ['deploy/wait_close.py', '--selftest'])):
        if not os.path.exists(args[0]):
            continue
        try:
            r = subprocess.run([sys.executable] + args, capture_output=True, text=True,
                               encoding='utf-8', timeout=240)
            last = (r.stdout.strip().splitlines() or ['(출력 없음)'])[-1]
            ok(label, r.returncode == 0, last[:140] if r.returncode == 0
               else (r.stderr.strip().splitlines() or [last])[-1][:140])
        except Exception as e:
            ok(label, False, f'{type(e).__name__}: {e}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fast', action='store_true', help='빠른 검사만 (CI 기본)')
    a = ap.parse_args()
    print("=" * 78)
    print("전략 검증 — 단일 진입점" + ("  [빠른 모드]" if a.fast else "  [전체]"))
    print("=" * 78)
    # [2026-09-04 코드리뷰] ★ 검사별 크래시 격리 — 종전엔 main() 에 try/except 가 없어
    #   한 검사가 예외를 던지면 **뒤따르는 불변식이 통째로 안 돌았고**(실측: guide.html 의
    #   섹션 이름만 바꿔도 I5 가 ValueError 로 죽어 I7·I10·I14·I9·I8 이 사라졌다),
    #   「실패 N건」 요약조차 안 찍혀 무엇이 빠졌는지 알 수 없었다.
    #   → 예외는 그 검사의 FAIL 로 바꾸고 나머지는 계속 돈다. 종료코드는 그대로 1 이다.
    def step(fn, *args):
        try:
            return fn(*args)
        except Exception as e:
            import traceback
            print(traceback.format_exc()[-1200:], file=sys.stderr)
            ok('%s 가 예외로 중단됐다' % fn.__name__, False,
               '%s: %s — 이 검사만 실패로 처리하고 나머지는 계속한다' % (type(e).__name__, e))
            return None

    D = step(i1_engine)
    if D is None:
        print('  ※ 엔진을 못 세워 D 가 필요한 검사는 건너뛴다', file=sys.stderr)
    else:
        step(i2_pit, D)
        step(i3_lag, D)
    step(i11_freeze)
    step(g_freeze_seal)
    step(i12_shadow)
    step(i13_protocol)
    step(i6_live)
    if not a.fast:
        if D is not None:
            step(i4_real, D)
            step(i5_decisions, D)
            step(i7_stats, D)
            step(i10_premise, D)
        step(i14_selftests)
    step(i9_retired)
    step(i8_deps)
    # 저장소 위생 관문 — 전략 불변식과 갈라 둔다(§2 경계). 빠른 모드에서도 전부 돈다:
    # 실측 전체 5.3초 · fast 1.8초라 비용이 없고, v168 회귀는 fast 만 돌려서 놓쳤다.
    for g in (g_repo_map, g_toc, g_isolation, g_notes_lag,
              g_deploy, g_signal_coupling, g_watchdog):
        step(g)
    head(f"결과  ({time.time()-T0:.0f}초)")
    if FAIL:
        print(f"  실패 {len(FAIL)}건")
        for f in FAIL:
            print(f"    - {f}")
    else:
        print("  실패 0건")
    if WARN:
        print(f"  경고 {len(WARN)}건: " + ', '.join(WARN))
    print("=" * 78)
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
