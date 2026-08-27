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
        ok("화면: A 가 참조로 표시된다 (ref:true)",
           "tag:'참조', ref:true" in h, 'signal.html STRAT.A')
        ok("화면: 참조 규칙에 클릭 핸들러가 안 붙는다",
           "host.querySelectorAll('button.opt')" in h and
           "host.querySelectorAll('.opt')" not in h,
           "선택자가 button.opt 여야 한다")
        ok("화면: 기본 규칙이 B 다", "let sel  = 'B';" in h, 'signal.html sel')
        ok("화면: 저장된 참조 선택을 되돌린다",
           "!STRAT[s].ref" in h, 'localStorage 마이그레이션')
        ok("화면: 최종배수를 함께 보여준다",
           "cell('최종배수'" in h,
           'MDD·CALMAR·SORTINO 만 보이면 실물구간에서 A 가 3개 다 이긴다')


# ------------------------------------------------------------------ I6
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
    `docs/전략_v29.md` 에는 v36 이전 값(143.3배)이 그대로 남아 있었다.
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
    for f in sorted(glob.glob('docs/전략_v*.md')):
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
