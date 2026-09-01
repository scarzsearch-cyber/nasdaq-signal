# -*- coding: utf-8 -*-
"""
[v37] 단일 검증 진입점 — 이것 하나만 통과하면 된다

사용자는 파이썬을 직접 돌리지 않는다. 그래서 **검증이 자동으로 돌아야** 하고,
실패하면 **CI 가 막아야** 한다. `.github/workflows/verify.yml` 이 매 push 마다 부른다.
**이 파일은 루트에 있어야 한다** — 사용자와 CI 의 진입점이다.

    python verify_all.py            # 전체 (느림, 5~15분)
    python verify_all.py --fast     # 빠른 것만 (CI 기본, 1~2분)

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
  I8  의존성         공용 모형 사용처가 전부 최신인가
  I9  폐기 수치      옛 공표값이 현행 문서·화면에 남아 있지 않은가
  I10 전제 감시      나스닥 고유 성질(극단 MDD·장기 상승)이 유지되는가
"""
import argparse
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


def ok(name, cond, detail='', warn=False):
    tag = 'PASS' if cond else ('WARN' if warn else 'FAIL')
    print(f"  [{tag}] {name}" + (f"   {detail}" if detail else ''))
    if not cond:
        (WARN if warn else FAIL).append(name)
    return cond


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
        if abs(dv[-1] - full[t]) > 1e-12:
            b[0] += 1
        if rule_w(dv, -0.16, -0.16)[-1] != wf[t]:
            b[1] += 1
        z = V.zc(c.pct_change().rolling(10, min_periods=10).std().values)
        if abs(z[-1] - rvf[t]) > 1e-10:
            b[2] += 1
        q = V.exp_q(z, 0.925)
        if abs(np.nan_to_num(q[-1]) - np.nan_to_num(qf[t])) > 1e-10:
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
        s = syn[k].reindex(a.index).fillna(0)
        y = len(a) / 252.0
        d = ((1 + s).prod() / (1 + a).prod()) ** (1 / y) - 1
        ok(f'{nm} {code} 드리프트 ±1.5%p', abs(d) < 0.015, f'{d:+.2%}/년 ({y:.1f}년)')


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
    if os.path.exists('signal.html'):
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
        if os.path.exists('.github/workflows/pages.yml'):
            pg = io.open('.github/workflows/pages.yml', encoding='utf-8').read()
            ok("배포: guide.html 이 Pages 복사 목록에 있다", 'guide.html' in pg,
               '빠지면 라이브에서 404 (v78 실사고)')
            ok("배포: notes.html 이 Pages 복사 목록에 있다", 'notes.html' in pg,
               'guide.html 과 같은 404 유형 (v142)')
            ok("배포: price.json 이 Pages 복사 목록에 있다", 'price.json' in pg,
               '빠지면 시세 배지가 라이브에서만 안 뜬다 (v145)')
            ok("배포: dd_percentile.json 이 Pages 복사 목록에 있다",
               'dd_percentile.json' in pg or not os.path.exists('data/dd_percentile.json'),
               '같은 404 유형 — 로컬에선 보이고 라이브에서만 안 뜬다 (v164)')
            ok("배포: PWA 파일이 Pages 복사 목록에 있다",
               'manifest.json' in pg and 'icon-192.png' in pg and 'icon-512.png' in pg
               and os.path.exists('manifest.json') and os.path.exists('icon-192.png')
               and os.path.exists('icon-512.png') and 'rel="manifest"' in h,
               '홈 화면 추가 (v104) — 누락 시 라이브 404, guide.html 사고와 동일 유형')
        if os.path.exists('guide.html'):
            g = io.open('guide.html', encoding='utf-8').read()
            ok("설명서: 필수 절 존재",
               'id="t4"' in g and '반드시 이해' in g and '그림자' in g and 'href="./"' in g,
               'T4 상세 + 이해 필수 6가지 + 돌아가기 탭')
        # [v145] 시세 스냅샷은 **표시 전용**이다. 신호 생성 경로가 이 파일을 읽는
        # 순간 동결 규칙(QQQ 미국 종가만)이 깨진다 — 그 결합을 기계로 막는다.
        if os.path.exists('deploy/price_now.py'):
            up = (io.open('deploy/update_signal.py', encoding='utf-8').read()
                  if os.path.exists('deploy/update_signal.py') else '')
            ok("시세: 신호 생성이 price.json 을 읽지 않는다",
               'price.json' not in up and 'price_now' not in up,
               '판정은 QQQ 종가만 — 시세는 화면 표시 전용 (v145)')
            ok("시세: 화면이 시세를 표시 경로로만 쓴다",
               'loadPrice' in h and 'chgBadge' in h,
               'price.json 은 배지·현재가 기본값에만 (v145)')
        if os.path.exists('notes.html'):
            n = io.open('notes.html', encoding='utf-8').read()
            # [v142] 업데이트 노트의 핵심 메시지는 「규칙은 안 바뀌었다」 — 이게 사라지면
            # 이 화면은 그냥 변경 목록이 되고, 동결의 의미가 화면에서 사라진다.
            ok("업데이트 노트: 규칙 무변경 선언 + 돌아가기 탭",
               '매매 규칙은 한 번도 바뀌지 않았습니다' in n and '변경 0회' in n
               and 'href="./"' in n and 'href="guide.html"' in n,
               '동결 사실이 화면에 남아 있어야 한다 (v142)')
            # [v148] 패치노트가 구현을 못 따라가는 사고가 한 세션에 두 번 났다
            # (v144~v147 을 만들고 노트를 안 고침). 자각 대신 관문으로 막는다 —
            # CLAUDE.md §4 의 최신 vNN 보다 노트가 뒤처지면 실패시킨다.
            # ※ 「배포가 멈춘다」가 아니다 — verify.yml 과 pages.yml 은 둘 다 push 트리거로
            #   **독립 실행**된다. 검증 실패는 이슈(메일)를 열 뿐 배포를 막지 않으며,
            #   그게 맞다: 문서 검사가 신호 화면을 얼릴 수 있으면 v137 의 fail-open
            #   원칙(인프라 문제로 진짜 폭락일 신호를 막지 마라)과 정면으로 어긋난다.
            if os.path.exists('CLAUDE.md'):
                cm = io.open('CLAUDE.md', encoding='utf-8').read()
                # 「v154~v160」 같은 범위 표기도 있으므로 줄 안의 모든 vNN 을 본다
                # (앞 숫자만 읽으면 최신이 v160 인데 v154 로 비교해 관문이 헐거워진다)
                cv = [int(x) for ln in re.findall(r'^- \*\*.*$', cm, re.M)
                      for x in re.findall(r'v(\d+)', ln)]
                nvs = [int(x) for x in re.findall(r'class="v">v(\d+)', n)]
                ok("업데이트 노트가 최신 버전까지 담고 있다",
                   bool(cv) and bool(nvs) and max(nvs) >= max(cv),
                   '노트 최신 v%s vs CLAUDE §4 최신 v%s — 뒤처지면 실패 (v148)'
                   % (max(nvs) if nvs else '?', max(cv) if cv else '?'))
        # [v172] 파일 지도가 실제 파일을 못 따라가는 사고 — v148 에 49건 났다
        # (research/*.py 를 만들고 FILES.md 에 안 올림). 자각 대신 관문으로 막는다.
        # ★ 폭을 좁게 잡는다: 사람이 새로 만드는 자리(스크립트·워크플로·화면·산출물)만
        #   본다. data/hist/** 같은 원자료까지 넣으면 오탐이 나 관문이 무시당한다.
        # ★ git 은 한글 경로를 \353\263\265 처럼 이스케이프해 뱉는다(실측 131건) —
        #   core.quotepath=false 가 없으면 「내가_보는_것/」이 통째로 검사에서 빠진다.
        if os.path.exists('FILES.md'):
            fmap = io.open('FILES.md', encoding='utf-8').read()
            try:
                import subprocess
                tk = subprocess.run(['git', '-c', 'core.quotepath=false', 'ls-files'],
                                    capture_output=True, text=True, encoding='utf-8',
                                    timeout=60).stdout.splitlines()
            except Exception:
                tk = []
            tk = [t.strip().replace('\\', '/') for t in tk if t.strip()]

            def _watched(p):
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

            miss = [p for p in tk if _watched(p)
                    and os.path.basename(p) not in fmap]
            ok("파일 지도가 실제 파일을 따라잡았다",
               not miss,
               ('FILES.md 미등재 %d건: %s (v172)' % (len(miss), ', '.join(miss[:5])))
               if miss else '검사 대상 %d개 전부 등재' % sum(1 for p in tk if _watched(p)))
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
        ok("화면: 모바일 고정열(Sticky)",
           "position:sticky" in h and "td.strat" in h, '기준·전략명 열 고정 (v73)')
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
        ok('화면: 개정 표시가 종가일과 분리돼 있다',
           "id=\"htmlRev\"" in h and "id=\"asof\"" in h, '두 자리 모두 존재')
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
        ok('신호원이 수정 종가(adjclose)다', 'adjclose' in u,
           'update_signal.py fetch — v67 B-1 해소')
    if os.path.exists('signal.html'):
        hh = io.open('signal.html', encoding='utf-8').read()
        ok('화면이 동결 규칙과 같다', 'enter:-0.16, exit:-0.16' in hh,
           'signal.html STRAT.B')
    n = 0
    if os.path.exists('data/oos_log.csv'):
        n = sum(1 for _ in io.open('data/oos_log.csv', encoding='utf-8')) - 1
    ok('OOS 장부가 쌓이고 있다', n >= 1,
       '%d영업일 (동결 %s 이후)' % (n, fz['frozen_at']), warn=(n < 1))


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
            except (KeyError, ValueError):
                bad.append(r.get('as_of', '?'))
    ok('그림자 기록이 정의와 모순 없음', not bad,
       '%d행 검사%s' % (n, ' · 위반: ' + ','.join(bad[:3]) if bad else ''))

    # [v73] 01 문서 AUTO-STATS 블록이 최신 스냅샷과 같은 끝 날짜인가
    if os.path.exists('01_Strategy_Logic.md') and os.path.exists('data/strategy_stats.json'):
        doc = io.open('01_Strategy_Logic.md', encoding='utf-8').read()
        S2 = json.load(io.open('data/strategy_stats.json', encoding='utf-8'))
        i0, j0 = doc.find('<!-- AUTO-STATS:START'), doc.find('<!-- AUTO-STATS:END -->')
        endd = S2['scenarios'][0]['strategies']['B']['end']
        ok('01 문서 AUTO-STATS 블록 동기화', i0 >= 0 and j0 > i0 and endd in doc[i0:j0],
           '%s (build_stats 가 자동 갱신)' % endd)


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
                ok(f"내장 {sc['key']} {k} horizons 일치",
                   (a is None and b is None) or
                   (a is not None and b is not None and abs(b - a) < 1e-9), f'{b} vs {a}')
            # [v61] 화면 눈금이 되는 벤치마크도 사본에 있어야 한다
            for bk in ('lev', 'def'):
                a = (sc.get('benchmarks') or {}).get(bk, {}).get('ulcer')
                b = (e[0].get('benchmarks') or {}).get(bk, {}).get('ulcer')
                ok(f"내장 {sc['key']} 벤치 {bk} 있음",
                   a is not None and b is not None and abs(b - a) < 1e-9,
                   f'{b} vs {a}')
    for k, en, ex in (('B', -0.16, -0.16), ('A', -0.16, -0.11)):
        cur = 'QLD'
        for v in dd.values:
            if pd.isna(v):
                continue
            if cur == 'QLD' and v <= en:
                cur = 'SCHD'
            elif cur == 'SCHD' and v > ex:
                cur = 'QLD'
        ok(f'상태 재계산 일치 ({k})', j['strategies'][k]['state'] == cur,
           f"json {j['strategies'][k]['state']} vs 재계산 {cur}")
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
def i8_deps():
    head("I8. 의존성 — 공용 모형 사용처가 전부 최신인가")
    print("  공용 모형을 바꾸면 사용처를 전부 재실행해야 한다 (v36 교훈).")
    SHARED = {'ust_tr': '국채 모형', 'mix_monthly': '바스켓', 'accumulate': '적립',
              'rule_w': '비중경로', 'lev_r': '레버리지'}
    import glob
    for fn, nm in SHARED.items():
        users = []
        for f in sorted(glob.glob('*.py') + glob.glob('deploy/*.py')):
            if f in ('verify_all.py',):
                continue
            try:
                if fn + '(' in io.open(f, encoding='utf-8').read():
                    users.append(f)
            except Exception:
                pass
        print(f"    {nm:<10} {fn+'()':<14} 사용처 {len(users)}개: {', '.join(users[:6])}"
              + (' ...' if len(users) > 6 else ''))
    print("  ※ 이 목록의 파일을 고쳤으면 관련 raw 출력을 재생성했는지 확인하라.")


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
    for item in cfg['retired']:
        v = item['value']
        for f in CURRENT:
            if not os.path.exists(f):
                continue
            for i, line in enumerate(io.open(f, encoding='utf-8').read().splitlines(), 1):
                if v in line and not any(a in line for a in allow_c):
                    hits.append((f, i, v, item['now']))

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
       f'{len(hits)}건' if hits else f'{len(CURRENT)}개 파일 검사')
    ok('버전 문서에 정정 배너 있음', not missing,
       f'{len(missing)}건 누락' if missing else f'{len(cfg["retired"])}종 확인', warn=True)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fast', action='store_true', help='빠른 검사만 (CI 기본)')
    a = ap.parse_args()
    print("=" * 78)
    print("전략 검증 — 단일 진입점" + ("  [빠른 모드]" if a.fast else "  [전체]"))
    print("=" * 78)
    D = i1_engine()
    i2_pit(D)
    i3_lag(D)
    i11_freeze()
    i12_shadow()
    i6_live()
    if not a.fast:
        i4_real(D)
        i5_decisions(D)
        i7_stats(D)
        i10_premise(D)
    i9_retired()
    i8_deps()
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
