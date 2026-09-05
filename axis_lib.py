# -*- coding: utf-8 -*-
"""
[v22 공용 엔진] 지금까지 변수로 놓지 않았던 '축'을 재기 위한 확장 유틸

v18~v21 은 전부 **전환 타이밍 축** 하나만 변수로 놓았다(문턱·히스테리시스·룩백·
확인일·복귀지표·방어자산·신호 기준자산). 이 모듈은 그 축을 고정한 채 다음 세 축을 연다.

  축1  riskon leverage k   — 지금까지 항상 2배 고정.        lev_r()
  축2  파라미터 앙상블      — 문턱을 고르지 않고 평균낸다.   rule_w() 여러 개를 평균
  축3  적립식 목적함수      — 지금까지 항상 거치식.          accumulate()

[규약] reentry_lib.run() 과 완전히 동일하게 맞췄다. 바꾼 것이 없다.
  - 체결: 전일 종가 신호 -> 당일 체결 (pos = w.shift(1))
  - 비용: 편도 0.1%, 회전율 |Δpos| 에 비례
  - 방어자산: hist_defensive.build(kind) 가 준 schdr 그대로
  check() 가 reentry_lib.run() 대비 오차 0 을 매번 검산한다.

[비중 w 의 규약 — 2026-09-04 코드리뷰]
  sim()과 만기 1회 과세인 after_tax(per_switch=False)는 **분수 비중을 선형 혼합**한다
  (r = w·riskon + (1-w)·defensive · 비용은 |Δw| 비례). 축2 앙상블이 만드는
  0.33/0.67 같은 값이 그대로 통한다. 다만 중간 매도에 세금을 매기는
  after_tax(per_switch=True)·after_tax_annual()은 0/1 전용이다. 분수 정률혼합은
  자산별 취득원가와 내부 재조정을 따로 추적해야 하는데 이 엔진은 단일 원가만 갖는다.
  전부 실현한 것처럼 조용히 과세하지 않고 ValueError로 막는다.
  accumulate() 만은 **0/1 전용**이다 — 위험/현금 두 통을 통째로 옮기는 모형이라
  부분 비중이 정의되지 않는다. 분수 w 를 주면 조용히 틀리는 대신 ValueError 를 던진다.
  ⚠ 종전에는 셋 다 `pos >= 1` 로 이진화해 **분수 w 에서 조용히 틀렸다**
    (세율 0 에서 sim 79,225배 vs after_tax 36,565배 = 0.462배). check() 가 이제 막는다.
"""
import sys
import numpy as np
import pandas as pd

try:                                   # 윈도우 콘솔 cp949 대비
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

COST = 0.001
_WTOL = 1e-9                           # 비중 판정 허용오차


# ------------------------------------------------------------------ 공용 내부
def _win(idx, start, end):
    """구간 지정을 정수 인덱스 한 쌍으로 바꾼다.

    [2026-09-04 코드리뷰] 종전엔 이 모듈 안에 **구간 언어가 둘**이었다 —
      sim·after_tax 는 날짜 start/end, accumulate 은 정수 lo/hi. check_accum() 이
      직접 그 다리를 놓고 있었는데(`start=D['idx'][first], end=D['idx'][hi-1]`)
      그 대응이 어디에도 안 적혀 있었다. 이제 두 함수가 **양쪽 다** 받는다:
      정수면 그대로 인덱스, 날짜/문자열이면 searchsorted.
    """
    n = len(idx)
    if start is None:
        lo = 0
    elif isinstance(start, (int, np.integer)):
        lo = int(start)
    else:
        lo = int(idx.searchsorted(pd.Timestamp(start)))
    if end is None:
        hi = n
    elif isinstance(end, (int, np.integer)):
        hi = int(end)
    else:
        hi = int(idx.searchsorted(pd.Timestamp(end), side='right'))
    lo, hi = max(0, min(lo, n)), max(0, min(hi, n))
    if hi <= lo:
        raise ValueError(
            '빈 구간이다 (start=%r end=%r -> %d:%d, 자료 %d행 %s~%s). '
            '구간이 자료 범위를 벗어났는지 확인하라.'
            % (start, end, lo, hi, n, idx[0].date(), idx[-1].date()))
    return lo, hi


def _months(idx):
    """월 식별자 — 월이 바뀌는 지점만 찾으면 되므로 year*12+month 로 충분하다.

    [2026-09-04 코드리뷰] 종전 `pd.Series(idx).dt.to_period('M').values` 는
      accumulate() 호출마다 13,863행을 새로 만들어 **함수 실행시간의 절반**을 먹었다
      (실측 0.021s 중 0.010s). 격자 연구는 이것을 수천 번 부른다.
      비교는 `months[i] != months[i-1]` 뿐이라 Period 객체가 필요 없다.
    """
    return np.asarray(idx.year) * 12 + np.asarray(idx.month)


def _need_binary(w, lo, hi, who):
    """accumulate 계열은 유한한 0/1 전용 — 결측·분수 비중을 조용히 이진화하지 않는다."""
    seg = np.asarray(w[lo:hi], dtype=float)
    # NaN과의 크기 비교는 모두 False다. 거리 비교만으로는 결측이 통과한다.
    bad = ~np.isfinite(seg) | ((np.abs(seg) > _WTOL) & (np.abs(seg - 1.0) > _WTOL))
    if bad.any():
        i = int(np.argmax(bad))
        raise ValueError(
            '%s 는 유한한 0/1 비중만 받는다 (위험/현금 두 통을 통째로 옮기는 모형이라 '
            '부분 비중이 정의되지 않는다). w[%d] = %r. '
            '결측·무한값은 입력을 먼저 고쳐라. '
            '유한한 분수 비중(앙상블)은 sim() 또는 after_tax(per_switch=False) 를 써라.'
            % (who, lo + i, float(seg[i])))


# ------------------------------------------------------------------ 신호
def rule_w(ddv, enter, exit_, w0=1.0):
    """낙폭 규칙 -> QLD 비중 경로. reentry_lib.run() 의 ladder 와 동치.

    enter 이하로 내려가면 0, exit_ 를 초과 회복하면 1. 그 사이는 직전 상태 유지.

    [2026-09-04 코드리뷰] 종전엔 `if cur >= 1.0:` / `else:` 두 갈래였고 **두 갈래가
      `if ddv[i] <= enter: cur = 0.0` 을 똑같이 한 번씩** 갖고 있었다. 공격 중
      `ddv > exit_` 는 이미 1 인 것을 1 로 두는 무동작이라 갈래가 사실상 하나였다.
      `cur < 1.0` 조건만 남겨 평평하게 폈다 — 그 조건이 w0 > 1 로 시작한 경로가
      1.0 으로 내려앉지 않게 지킨다(원래 동작 보존).
      문턱 격자 681조합 + w0 5종 전수에서 출력 지문 동일.
    ⚠ 이 함수는 verify_all.py I8 의 SHARED_SEAL 로 봉인돼 있다 — 고치면 봉인도 갱신하라.
    """
    n = len(ddv)
    w = np.empty(n)
    cur = w0
    for i in range(n):
        if ddv[i] <= enter:
            cur = 0.0
        elif cur < 1.0 and ddv[i] > exit_:
            cur = 1.0
        w[i] = cur
    return w


def dd_from(px, lb):
    """룩백 lb 일 낙폭. hist_data.build_ext() 와 같은 min_periods 규약(= lb).

    ⚠ [2026-09-04 코드리뷰] **저장소에 min_periods 규약이 셋 있다.** 인용할 때 붙여라:
        hist_data.build_ext()      min_periods=252  ← 이 함수와 같다 (백테스트 엔진)
        reentry_lib.build()        min_periods=60
        deploy/update_signal.py    min_periods=60   ← 라이브 신호
      차이는 **워밍업 구간에만** 나타난다. 여기 규약은 첫 lb-1 일을 낙폭 0(=공격)으로
      두고, 60 규약은 60일 뒤부터 낙폭을 산다. 25년치를 쓰는 라이브에서는 무의미하나
      **짧은 계열**(연구용 캐시·타 시장 이식)에서는 결과가 갈린다.
      check() 는 run 과 sim 에 같은 D 를 넘기므로 이 차이를 못 본다 — 스스로 확인하라.
    """
    return (px / px.rolling(lb, min_periods=lb).max() - 1).fillna(0).values


# ------------------------------------------------------------------ 배수
def lev_r(D, k, c_k=None):
    """기초지수 일간수익 -> k 배 상품의 일간수익.

    합성비용은 2배 실물(QQQ/QLD 겹침)에서 역산한 c_daily 를 차입분에 비례해 늘린다:
        cost(k) = (k - 1) * c_daily          # c_daily = cost(2) = 1x차입 + 운용보수
    k=2 에서 기존 규약과 정확히 일치하고, k>2 에서는 **실제보다 비싸게** 잡힌다
    (운용보수는 k 에 비례하지 않으므로). 즉 고배수에 불리한 방향의 보수적 모형이다.

    ★ [2026-09-04 코드리뷰] 그 「비싸게」의 **크기가 이제 실측돼 있다.**
      실물 TQQQ(2010-02~ · data/hist/yahoo_TQQQ.csv)로 build_ext 와 같은 방법으로
      역산하면 c(3) = 연 **5.33%p** 인데 이 식은 연 **6.59%p** 를 매긴다 — **연 1.26%p
      과대**이고, 정체는 운용보수 이중과금(QLD 0.95%×2 − TQQQ 0.84% ≈ 1.06%p)이다.
      근거·재현은 research/LEVERAGE_US.md §1 · 상수는 research/tax_us_direct.py 의
      C3_REAL = 0.00021170.
      ⛔ **기본 동작은 바꾸지 않았다.** LEVERAGE_US.md §1~§9 의 배율 수치가 이 식으로
        발행됐고, 그 편향은 「3배에 박함」으로 §11-3 편향 대장에 이미 등재돼 있다.
        기본값을 옮기면 공표 수치가 통째로 움직인다(CLAUDE.md §-1: 「바꾸자」의 증거
        기준은 「그대로 두자」보다 훨씬 높다).
      → 정확한 값이 필요하면 **c_k 로 명시**하라. 그러면 그 표가 어느 모형인지
        호출부에 남는다.

    c_k : 일간 합성비용을 직접 지정한다(예: c_k=C3_REAL). None 이면 (k-1)*c_daily.
    """
    pxr = np.nan_to_num(D['px'].pct_change().values)
    c = (k - 1) * D['c_daily'] if c_k is None else c_k
    return k * pxr - c


# ------------------------------------------------------------------ 거치식
def sim(D, w, riskon_r=None, cost=COST, lag=1, start=None, end=None):
    """임의의 비중경로 w 로 거치식 곡선을 만든다. reentry_lib.run() 과 동일 규약.

    w 는 D['idx'] 전체 길이여야 한다(구간은 start/end 로 자른다).
    분수 비중을 선형 혼합하므로 축2 앙상블이 그대로 통한다.

    ⚠ [B03-3 · 2026-09-05] start= 는 **전체 경로 w 를 자를 뿐 상태를 리셋하지 않는다.**
      reentry_lib.run(start=) / hist_korea.run_kr(start=) 은 시작일에 상태기계를 w0=1(공격)로
      **다시 시작**한다 — 그래서 시작일이 방어 구간이면 run 은 첫날 1→0 「유령 전환」 비용
      0.1% 를 한 번 더 물고(실측 2008-12-01·2002-10-01·2022-06-01 시작 B: run/sim = 0.9990),
      히스테리시스 띠 안(A: −16<dd≤−11)에서 시작하면 상태 자체가 갈린다. 공표 4시나리오는
      전부 공격 상태에서 시작하므로 무관하나, **방어 중 시작하는 창을 두 엔진으로 섞어 비교하지 마라.**

    lag : 신호가 체결에 반영되기까지의 거래일. 규약은 1(전일 종가 -> 당일 체결).
          **lag=0 은 당일 신호로 당일 체결 = 미래훔쳐보기 대조군**이다.
          [2026-09-04 코드리뷰] 종전에는 `pos[lag:] = wv[:-lag]` 가 lag=0 에서
          `wv[:0]`(빈 배열)을 전체 길이에 대입해 **ValueError 로 죽었다.**
          그래서 audit/audit_all.py 의 미래참조 스캔이 `if lag > 0` 으로 우회하고
          곡선을 손으로 다시 짜고 있었다 — 엔진을 안 지나는 사본이라, 그 사본과
          엔진이 갈리면 감사는 통과하는데 규약은 달라진다. 이제 엔진이 직접 낸다.
    """
    idx = D['idx']
    lo, hi = _win(idx, start, end)
    sl = slice(lo, hi)
    rr = D['qldr'] if riskon_r is None else riskon_r
    wv = np.asarray(w[sl], dtype=float)
    pos = np.empty_like(wv)
    if lag:
        pos[:lag] = wv[0]
        pos[lag:] = wv[:-lag]
    else:
        pos[:] = wv                                    # 당일 신호 = 당일 체결
    r = np.nan_to_num(pos * rr[sl] + (1 - pos) * D['schdr'][sl])
    r[0] = 0.0
    turn = np.abs(np.diff(pos, prepend=pos[0]))
    curve = pd.Series(np.cumprod((1 + r) * (1 - cost * turn)), index=idx[sl])
    return curve, int((np.abs(np.diff(wv)) > 1e-9).sum())


# ------------------------------------------------------------------ 적립식
def accumulate(D, k, w, lo, hi, park=None, dip=None, cost=COST,
               rk=None, buy_cost=0.0, return_paths=False):
    """월초 1단위 적립. 반환 (총납입, 최종평가액, 경로MDD).

    park : 대기자금 수익률. None 이면 방어자산(schdr), 배열이면 그것(예: T-bill)
    dip  : None 이면 납입금을 전략이 지시하는 쪽에 바로 넣는다.
           숫자면 'QLD Dip Alert' 형 — 납입금을 전부 대기시켰다가
           낙폭이 dip 이하로 내려간 날 일괄 투입한다.

    납입 배치와 dip 판정 모두 **전일 신호**만 쓴다(미래 참조 없음).

    ⚠ **w 는 0/1 전용**이다 (모듈 docstring 참조). 분수를 주면 ValueError.
    lo/hi 는 정수 인덱스 또는 날짜 — _win() 이 둘 다 받는다.

    [2026-09-04 코드리뷰]
      rk       : lev_r(D, k) 를 미리 계산해 넘긴다. 종전엔 호출마다 전 구간
                 pct_change 를 다시 돌려 격자 연구에서 통째로 낭비였다.
      buy_cost : **월 납입에 붙는 매수 비용.** 종전에는 전환에만 (1-cost) 를 물리고
                 납입 매수에는 아무 비용도 안 물렸는데, 그 예외가 어디에도 안 적혀
                 있었다(30년 월납이면 360회가 전부 무료 = 납입 총액의 약 0.1%).
                 ⛔ **기본값 0.0 = 종전 동작** — 공표된 적립 수치(goal_feasibility·
                 axis_dca·def_equity)가 이 식으로 나왔으므로 기본을 옮기지 않는다.
                 비용을 넣고 재려면 buy_cost=COST 로 명시하라.
      return_paths : True 면 기존 3개 반환값 뒤에 평가액·누적납입 경로를 붙인다.
                     적립식 원금 대비 최저(mdd_vs_paid)를 계산할 때만 쓴다.
    """
    idx = D['idx']
    lo, hi = _win(idx, lo, hi)
    _need_binary(w, lo, hi, 'accumulate()')
    rk = lev_r(D, k) if rk is None else rk
    dfr = D['schdr'] if park is None else park
    ddv = D['ddv']
    months = _months(idx)

    R = C = paid = 0.0
    prev = w[lo]
    vals, pays = [], []
    for i in range(lo, hi):
        # [v33 정정] 전환을 그날 수익 적용 **전에** 한다.
        # 기존 순서(수익 -> 전환)는 전일 종가 신호가 하루 더 늦게 반영되는
        # 실질 2일 지연이었다. 규약은 pos = w.shift(1) = 1일 지연이며
        # reentry_lib.run / sim() 이 그렇게 돈다.
        # 검산: 납입 1회로 두면 거치식 sim() 과 오차 0 이어야 한다.
        pos = w[i - 1] if i > lo else w[lo]

        if pos != prev:                                    # 전략 전환
            if pos >= 1:
                R += C * (1 - cost); C = 0.0
            else:
                C += R * (1 - cost); R = 0.0
            prev = pos

        R *= (1 + rk[i])
        C *= (1 + dfr[i])

        if i > lo and months[i] != months[i - 1]:           # 월초 납입
            paid += 1.0
            if dip is not None or pos < 1:
                C += 1.0 - buy_cost
            else:
                R += 1.0 - buy_cost

        if dip is not None and C > 0 and pos >= 1 and ddv[i - 1] <= dip:
            R += C * (1 - cost); C = 0.0                    # dip 일괄 투입

        vals.append(R + C)
        pays.append(paid)

    v = pd.Series(vals, index=idx[lo:hi])
    base = (paid, float(v.iloc[-1]), float((v / v.cummax() - 1).min()))
    if return_paths:
        return base + (v.values.copy(), np.asarray(pays, dtype=float))
    return base


# ------------------------------------------------------------------ 세금
def after_tax(D, k, w, rate, per_switch, cost=COST, start=None, end=None,
              riskon_r=None):
    """계좌 규약별 세후 최종배수.

    per_switch=False : 과세이연(ISA). 만기에 총이익을 한 번만 과세
    per_switch=True  : 전환마다 실현이익 과세(손익통산 없음, 보수적)

    [2026-09-04 코드리뷰]
      ⓐ 분수 비중을 **혼합**한다. 종전 `rk[i] if pos >= 1 else dfr[i]` 는 0.67 을
         전량 방어로 읽어 세율 0 에서도 sim 대비 0.462배가 나왔다. 단, 중간실현
         과세는 자산별 원가가 필요한 분수 비중을 실패-폐쇄한다.
      ⓑ 비용도 `cost * |pos - prev|` 로 sim 의 회전율 규약과 맞췄다(이진이면 동일).
      ⓒ riskon_r 을 받는다. 종전엔 rk = lev_r(D,k) 를 안에 박아 둬서, 실물 TQQQ
         보정이나 환노출 2배처럼 다른 수익 계열을 쓰려면 **세금 루프 전체를 복제**해야
         했다(research/tax_us_direct.py 가 다섯 벌 복제했다). CLAUDE.md §5-38 이
         기록한 두 건의 반토막 사고가 전부 그렇게 새로 짠 루프에서 났다.
    """
    idx = D['idx']
    lo, hi = _win(idx, start, end)
    if per_switch:
        _need_binary(w, lo, hi, 'after_tax(per_switch=True)')
    rk = lev_r(D, k) if riskon_r is None else riskon_r
    dfr = D['schdr']
    V = B = 1.0
    prev = w[lo]
    paid = 0.0
    for i in range(lo + 1, hi):
        pos = w[i - 1]
        if pos != prev:
            V *= (1 - cost * abs(pos - prev))
            if per_switch:
                g = V - B
                if g > 0:
                    t = g * rate; V -= t; paid += t
                B = V
            prev = pos
        V *= (1 + pos * rk[i] + (1 - pos) * dfr[i])
    g = V - B
    if g > 0:
        t = g * rate; V -= t; paid += t
    return V, paid


def _withdraw_tax(V, B, tax):
    """보유분 일부를 팔아 세금을 낸다. 반환은 (잔액, 잔여원가, 실현손익).

    세금 ``tax`` 만큼을 계좌에서 꺼내려면 현재 보유분의 ``tax / V`` 를 판다.
    그 매도에 대응하는 취득원가도 같은 비율로 빠지고, 매도가와 빠진 원가의
    차이는 **세금을 낸 새 연도의 실현손익**이다. 이 2차 실현손익을 버리면
    수익 중인 자산에서 세금을 꺼낼 때 다음 연도 세금을 다시 과소 계산한다.
    """
    V, B, tax = float(V), float(B), float(tax)
    if tax <= 0:
        return V, B, 0.0
    if V <= 0 or tax > V + 1e-12:
        raise ValueError('보유자산으로 세금을 낼 수 없다 (V=%r tax=%r)' % (V, tax))
    tax = min(tax, V)                 # 부동소수점 끝자리만 V를 넘은 경우
    basis_sold = B * (tax / V)
    realized = tax - basis_sold
    return V - tax, B - basis_sold, realized


def after_tax_annual(D, k, w, rate=0.22, cost=COST, start=None, end=None,
                     riskon_r=None):
    """해외주식 양도소득세형 — 연간 실현손익을 통산한 뒤 과세.

    250만원 기본공제는 넣지 않았다(금액 단위가 없는 배수 모형이라 정의 불가).
    계좌가 커질수록 공제의 상대적 크기가 0 으로 가므로 큰 왜곡은 아니다.

    [2026-09-04 코드리뷰] 회전율 비례 비용 · riskon_r 을 after_tax 와 맞췄고,
      check() 가 이제 세율 0 축퇴를 검산한다(종전에는 **이 함수만 검산 밖**이었다).
      연간 중간실현은 자산별 원가가 없는 분수 비중을 실패-폐쇄하며 0/1만 받는다.

    연말 세금을 계좌에서 꺼내면 현재 보유분도 그 비율만큼 매도한 것이다. 따라서
    평가액과 취득원가 B를 같은 비율로 줄이고, 그 일부 매도의 실현손익은 새 연도
    손익통산으로 넘긴다. 세금은 새 연도 첫 수익을 적용하기 전에 뗀다.
    """
    idx = D['idx']
    lo, hi = _win(idx, start, end)
    _need_binary(w, lo, hi, 'after_tax_annual()')
    rk = lev_r(D, k) if riskon_r is None else riskon_r
    dfr = D['schdr']
    V = B = 1.0
    prev = w[lo]
    yr = idx[lo].year
    net = paid = 0.0
    for i in range(lo + 1, hi):
        if idx[i].year != yr:                       # 직전 연도 정산
            carry = 0.0
            if net > 0:
                t = net * rate
                V, B, carry = _withdraw_tax(V, B, t)
                paid += t
            # 세금 마련용 일부 매도는 새 연도의 실현손익이다. 이전 연도 손실은 이월하지 않는다.
            net = carry
            yr = idx[i].year
        pos = w[i - 1]
        if pos != prev:
            V *= (1 - cost * abs(pos - prev))
            net += V - B
            B = V
            prev = pos
        V *= (1 + pos * rk[i] + (1 - pos) * dfr[i])
    net += V - B
    if net > 0:
        t = net * rate; V -= t; paid += t
    return V, paid


# ------------------------------------------------------------------ 검산·출력
def check_accum(D):
    """[v33 신설 · B03-2 재작성] 적립 시뮬레이터 규약 검산 — accumulate() == Σ 거치식.

    v29~v32 까지 accumulate()/accum()/accum_tax() 가 '그날 수익 -> 전환' 순서라
    전일 종가 신호가 하루 더 늦게 반영되는 **실질 2일 지연**이었다. 이 검산이
    있었으면 바로 잡혔다. 새 적립 함수를 만들 때마다 이걸 통과시켜라.

    [2026-09-04 코드리뷰] 세 가지를 고쳤다.
      ⓐ `lo = 3000` 하드코딩 — 6,024행보다 짧은 D 로 부르면 검산이 실패를 보고하는
         대신 IndexError 로 터졌다(실측: 2,000행 D → index 3000 is out of bounds).
         호출부가 전부 `assert check(D)` 라 원인이 자료 길이인지 규약 위반인지
         구별되지 않았다. 이제 창을 자료 길이에서 끌어온다(54년 D 에서는 lo=3000 동일).
      ⓑ 쓰이지 않는 `k = int(np.where(...)[0][0])` 를 지웠다 — 값을 안 쓰면서
         창에 월 경계가 없으면 IndexError 를 던지는 줄이었다.
      ⓒ `first` 가 None 인 채 D['idx'][first] 로 들어가던 것을 막았다.
    """
    n = len(D['idx'])
    span = 12 * 252
    if n < span + 252:
        print('검산 적립  표본 %d행 - 12년 창을 못 잡아 건너뛴다' % n)
        return True                       # 못 재는 것과 틀린 것은 다르다
    lo = min(3000, n - span)
    hi = lo + span
    w = rule_w(D['ddv'], -0.16, -0.16)
    rk = lev_r(D, 2.0)
    # [B03-2 · 2026-09-05 코드리뷰] ★ 종전 검산은 accumulate() 를 부르고 그 결과(fin)를
    #   **버린 뒤** 납입 1회짜리 루프를 여기서 손으로 다시 짜 sim() 과 비교했다. 엔진을
    #   안 지나는 사본이라 accumulate() 가 어떻게 틀려도 통과했다(§-1 ⑤ 「실패할 수 없는
    #   것은 관문이 아니다」 · v203 ⓑ audit_all 우회와 같은 유형).
    #   이제 accumulate() 자체를 항등식으로 검산한다 — 납입 1단위는 그날부터 끝까지
    #   전략 곡선 배수만큼 자라고 전환 비용은 총액에 비례하므로(선형)
    #       최종평가액 == Σ_m  c[hi-1] / c[납입일_m]   (c = 같은 창의 sim 곡선)
    #   이 정확히 성립한다. 반례 재현: 순서를 「수익 → 전환」으로 바꾼 가짜 accumulate 는
    #   여기서 즉시 떨어진다(오차 1e-3 대).
    paid, fin, _ = accumulate(D, 2.0, w, lo, hi, rk=rk)
    months = _months(D['idx'])
    pays = [i for i in range(lo + 1, hi) if months[i] != months[i - 1]]
    if not pays:
        print('검산 적립  창 %d:%d 에 월 경계가 없다 - 검산 불가' % (lo, hi))
        return False
    c, _ = sim(D, w, rk, start=lo, end=hi)
    cv = c.values
    exp = float(sum(cv[-1] / cv[i - lo] for i in pays))
    err = abs(fin / exp - 1)
    ok = err < 1e-9 and int(paid) == len(pays)
    print('검산 적립(%d회 납입) vs Σ거치식  %.6f vs %.6f  오차=%.1e  납입 %d/%d'
          % (len(pays), fin, exp, err, int(paid), len(pays)))
    return ok


def check(D):
    """reentry_lib.run() 대비 오차 0 확인.

    ⚠ [2026-09-04 코드리뷰] 종전 docstring 은 「**모든 스크립트가** 시작할 때 부른다」
      였는데 사실이 아니다 — axis_lib 를 import 하는 66개 파일 중 이것을 부르는 것은
      **9개**다. 그 문장을 믿으면 나머지 57개의 산출을 「엔진 동치가 보장된 값」으로
      읽게 된다. 사실로 고쳐 적는다: **새 스크립트를 만들면 `assert check(D)` 를
      맨 앞에 넣어라** (기존 관행: axis_accum·axis_accum2·axis_defsel·axis_ens·
      axis_lev 등이 그렇게 한다).

    검산 항목:
      ① run == sim            (A·B 두 사다리)
      ② after_tax(세율 0)        == sim
      ③ after_tax_annual(세율 0) == sim   ← 2026-09-04 추가. 해외 직투 세후 수치의 출처인데
                                          **종전에는 검산 밖**이었다(CLAUDE.md §5-38:
                                          「그 계산을 끄면 원래 값이 나오는가를 먼저 찍어라」)
      ④ 분수 비중(앙상블)의 만기 1회 과세도 세율 0에서 sim 과 같은가
      ⑤ 중간실현 과세가 원가를 정의할 수 없는 분수 비중을 실패-폐쇄하는가
      ⑥ 매도일 새 자산 수익을 매도차익으로 잘못 과세하지 않는가
      ⑦ 세금 마련용 일부 매도의 원가·2차 실현손익이 다음 연도로 이어지는가
      ⑧ 적립 accumulate() == Σ 납입일별 거치식 배수  (B03-2: 엔진 자체를 검산한다)
    """
    from reentry_lib import run
    from hyst_core import A, B
    ok = True
    tv, tb, tg = _withdraw_tax(2.0, 1.0, 0.2)
    tax_err = max(abs(tv - 1.8), abs(tb - 0.9), abs(tg - 0.1))
    lv, lb, lg = _withdraw_tax(1.0, 2.0, 0.2)
    tax_err = max(tax_err, abs(lv - 0.8), abs(lb - 1.6), abs(lg + 0.2))
    print('검산 연간세금 인출 후 잔액/원가/실현  %.6f / %.6f / %.6f  오차=%.1e'
          % (tv, tb, tg, tax_err))
    ok = ok and tax_err < 1e-12
    # 손계산 가능한 2년 반례: 1년차 실현익 1, 연말 보유분의 미실현익 1.
    # 세율 20%면 첫 세금 0.2를 마련한 일부 매도도 새 연도 실현익 1/15를 만들고,
    # 남은 보유분 실현익 14/15와 합쳐 새 연도 과표가 다시 정확히 1이 된다.
    toy = {'idx': pd.DatetimeIndex(['2020-01-02', '2020-03-02', '2020-06-01',
                                    '2020-12-31', '2021-01-04']),
           'schdr': np.array([0.0, 0.0, 0.0, 0.5, 0.0])}
    toy_w = np.array([1.0, 0.0, 0.0, 0.0, 0.0])
    toy_r = np.array([0.0, 1.0, 0.0, 0.0, 0.0])
    toy_v, toy_paid = after_tax_annual(toy, 2.0, toy_w, rate=0.20, cost=0.0,
                                       riskon_r=toy_r)
    toy_err = max(abs(toy_v - 2.6), abs(toy_paid - 0.4))
    print('검산 연간세금 2차실현  최종 %.6f / 세금 %.6f  오차=%.1e'
          % (toy_v, toy_paid, toy_err))
    ok = ok and toy_err < 1e-12
    # 전환일에는 기존 자산을 먼저 팔고 새 자산의 그날 수익을 받는다. 순서를 뒤집으면
    # 새 자산 수익까지 직전 보유분 매도차익으로 과세한다.
    swtoy = {'idx': pd.DatetimeIndex(['2020-01-02', '2020-06-01', '2020-12-31']),
             'schdr': np.array([0.0, 0.0, 1.0])}
    sww = np.array([1.0, 0.0, 0.0])
    swr = np.array([0.0, 1.0, 0.0])
    sv, sp = after_tax(swtoy, 2.0, sww, rate=0.20, per_switch=True, cost=0.0,
                       riskon_r=swr)
    sw_err = max(abs(sv - 3.24), abs(sp - 0.56))
    print('검산 전환일 매도→새자산수익  최종 %.6f / 세금 %.6f  오차=%.1e'
          % (sv, sp, sw_err))
    ok = ok and sw_err < 1e-12
    yrtoy = {'idx': pd.DatetimeIndex(['2020-01-02', '2020-06-01', '2020-12-31',
                                      '2021-01-04', '2021-12-31']),
             'schdr': np.array([0.0, 0.0, 0.5, 0.0, 1.0])}
    yv, yp = after_tax_annual(yrtoy, 2.0, np.array([1.0, 0.0, 0.0, 0.0, 0.0]),
                              rate=0.20, cost=0.0,
                              riskon_r=np.array([0.0, 1.0, 0.0, 0.0, 0.0]))
    yr_err = max(abs(yv - 4.84), abs(yp - 0.96))
    print('검산 연간세금 전환순서    최종 %.6f / 세금 %.6f  오차=%.1e'
          % (yv, yp, yr_err))
    ok = ok and yr_err < 1e-12
    for S in (A, B):
        c0, _, _ = run(D, S['ladder'], enter=S['enter'], cost=COST)
        c1, sw = sim(D, rule_w(D['ddv'], S['enter'], S['ladder'][0][0][1]))
        err = abs(c0.iloc[-1] / c1.iloc[-1] - 1)
        ok = ok and err < 1e-12
        print('검산 %-11s  run=%.4f  sim=%.4f  오차=%.1e  전환=%d'
              % (S['name'], c0.iloc[-1], c1.iloc[-1], err, sw))
    wB = rule_w(D['ddv'], -0.16, -0.16)                 # 세율 0 이면 sim 과 같아야 한다
    rk2 = lev_r(D, 2.0)
    c, _ = sim(D, wB, rk2)
    for nm, fn in (('after_tax', lambda: after_tax(D, 2.0, wB, 0.0, True)[0]),
                   ('after_tax_annual', lambda: after_tax_annual(D, 2.0, wB, rate=0.0)[0])):
        v = fn()
        err = abs(v / c.iloc[-1] - 1)
        ok = ok and err < 1e-6
        print('검산 %-17s(세율0)  %.4f  vs sim %.4f  오차=%.1e' % (nm, v, c.iloc[-1], err))
    # 분수 비중은 만기 1회 과세만 정의된다. 중간 매도 과세는 자산별 원가가 없어 막는다.
    wf = (rule_w(D['ddv'], -0.14, -0.14) + rule_w(D['ddv'], -0.16, -0.16)
          + rule_w(D['ddv'], -0.18, -0.18)) / 3.0
    cf, _ = sim(D, wf, rk2)
    vf, _ = after_tax(D, 2.0, wf, 0.0, False)
    errf = abs(vf / cf.iloc[-1] - 1)
    ok = ok and errf < 1e-6
    print('검산 분수비중 만기과세(세율0)  %.4f  vs sim %.4f  오차=%.1e'
          % (vf, cf.iloc[-1], errf))
    blocked = 0
    for fn in (lambda: after_tax(D, 2.0, wf, 0.0, True),
               lambda: after_tax_annual(D, 2.0, wf, rate=0.0)):
        try:
            fn()
        except ValueError:
            blocked += 1
    print('검산 분수비중 중간실현 실패-폐쇄  %d/2' % blocked)
    ok = ok and blocked == 2
    ok = ok and check_accum(D)                          # [v33] 적립 규약도 함께 본다
    return ok


def row(nm, curve, sw, ref=None):
    from reentry_lib import met, rolling_stats
    m = met(curve)
    d = dict(name=nm, final=m['final'], cagr=m['cagr'] * 100, mdd=m['mdd'] * 100,
             calmar=m['calmar'], sharpe=m['sharpe'], sw=sw)
    if ref is not None:
        rs = rolling_stats(curve, ref)
        for k in (5, 10):
            if k in rs:
                d['w%dy' % k] = rs[k]['win']
    return d


def show(rows, title):
    df = pd.DataFrame(rows)
    print('\n===== %s =====' % title)
    with pd.option_context('display.width', 220):
        print(df.to_string(index=False, float_format=lambda x: format(x, ',.2f')))
    return df


def qqq_curve(D, start=None):
    c = pd.Series(np.cumprod(1 + np.nan_to_num(D['px'].pct_change().values)), index=D['idx'])
    if start:
        c = c.loc[start:]
        if len(c) == 0:
            raise ValueError('qqq_curve: start=%r 이후에 자료가 없다 (마지막 %s)'
                             % (start, D['idx'][-1].date()))
        c = c / c.iloc[0]
    return c
