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
  sim()·after_tax()·after_tax_annual() 은 **분수 비중을 선형 혼합**한다
  (r = w·riskon + (1-w)·defensive · 비용은 |Δw| 비례). 축2 앙상블이 만드는
  0.33/0.67 같은 값이 그대로 통한다.
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
    """accumulate 계열은 0/1 전용 — 분수 비중을 조용히 이진화하지 않는다."""
    seg = np.asarray(w[lo:hi], dtype=float)
    bad = (np.abs(seg) > _WTOL) & (np.abs(seg - 1.0) > _WTOL)
    if bad.any():
        i = int(np.argmax(bad))
        raise ValueError(
            '%s 는 0/1 비중만 받는다 (위험/현금 두 통을 통째로 옮기는 모형이라 '
            '부분 비중이 정의되지 않는다). w[%d] = %r. '
            '분수 비중(앙상블)은 sim()·after_tax() 를 써라.'
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
               rk=None, buy_cost=0.0):
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
    vals = []
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

    v = pd.Series(vals, index=idx[lo:hi])
    return paid, float(v.iloc[-1]), float((v / v.cummax() - 1).min())


# ------------------------------------------------------------------ 세금
def after_tax(D, k, w, rate, per_switch, cost=COST, start=None, end=None,
              riskon_r=None):
    """계좌 규약별 세후 최종배수.

    per_switch=False : 과세이연(ISA). 만기에 총이익을 한 번만 과세
    per_switch=True  : 전환마다 실현이익 과세(손익통산 없음, 보수적)

    [2026-09-04 코드리뷰]
      ⓐ 분수 비중을 **혼합**한다. 종전 `rk[i] if pos >= 1 else dfr[i]` 는 0.67 을
         전량 방어로 읽어 세율 0 에서도 sim 대비 0.462배가 나왔다. 이진 w 에서는
         `1·rk + 0·dfr = rk` 라 출력이 비트 단위로 같다.
      ⓑ 비용도 `cost * |pos - prev|` 로 sim 의 회전율 규약과 맞췄다(이진이면 동일).
      ⓒ riskon_r 을 받는다. 종전엔 rk = lev_r(D,k) 를 안에 박아 둬서, 실물 TQQQ
         보정이나 환노출 2배처럼 다른 수익 계열을 쓰려면 **세금 루프 전체를 복제**해야
         했다(research/tax_us_direct.py 가 다섯 벌 복제했다). CLAUDE.md §5-38 이
         기록한 두 건의 반토막 사고가 전부 그렇게 새로 짠 루프에서 났다.
    """
    idx = D['idx']
    lo, hi = _win(idx, start, end)
    rk = lev_r(D, k) if riskon_r is None else riskon_r
    dfr = D['schdr']
    V = B = 1.0
    prev = w[lo]
    paid = 0.0
    for i in range(lo + 1, hi):
        pos = w[i - 1]
        V *= (1 + pos * rk[i] + (1 - pos) * dfr[i])
        if pos != prev:
            V *= (1 - cost * abs(pos - prev))
            if per_switch:
                g = V - B
                if g > 0:
                    t = g * rate; V -= t; paid += t
                B = V
            prev = pos
    g = V - B
    if g > 0:
        t = g * rate; V -= t; paid += t
    return V, paid


def after_tax_annual(D, k, w, rate=0.22, cost=COST, start=None, end=None,
                     riskon_r=None):
    """해외주식 양도소득세형 — 연간 실현손익을 통산한 뒤 과세.

    250만원 기본공제는 넣지 않았다(금액 단위가 없는 배수 모형이라 정의 불가).
    계좌가 커질수록 공제의 상대적 크기가 0 으로 가므로 큰 왜곡은 아니다.

    [2026-09-04 코드리뷰] after_tax 와 같은 세 가지를 함께 고쳤다 —
      분수 비중 혼합 · 회전율 비례 비용 · riskon_r. check() 가 이제 세율 0 축퇴를
      검산한다(종전에는 **이 함수만 검산 밖**이었다. 해외 직투 세후 수치를 만드는
      함수가 바로 이것이다).
    """
    idx = D['idx']
    lo, hi = _win(idx, start, end)
    rk = lev_r(D, k) if riskon_r is None else riskon_r
    dfr = D['schdr']
    V = B = 1.0
    prev = w[lo]
    yr = idx[lo].year
    net = paid = 0.0
    for i in range(lo + 1, hi):
        pos = w[i - 1]
        V *= (1 + pos * rk[i] + (1 - pos) * dfr[i])
        if idx[i].year != yr:                       # 연말 정산
            if net > 0:
                t = net * rate; V -= t; paid += t
            net = 0.0
            yr = idx[i].year
        if pos != prev:
            V *= (1 - cost * abs(pos - prev))
            net += V - B
            B = V
            prev = pos
    net += V - B
    if net > 0:
        t = net * rate; V -= t; paid += t
    return V, paid


# ------------------------------------------------------------------ 검산·출력
def check_accum(D):
    """[v33 신설] 적립 시뮬레이터 규약 검산 — 납입 1회면 거치식과 같아야 한다.

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
        print('검산 적립(1회납입)  표본 %d행 — 12년 창을 못 잡아 건너뛴다' % n)
        return True                       # 못 재는 것과 틀린 것은 다르다
    lo = min(3000, n - span)
    hi = lo + span
    w = rule_w(D['ddv'], -0.16, -0.16)
    months = _months(D['idx'])
    paid, fin, _ = accumulate(D, 2.0, w, lo, hi)          # 여기선 60회 납입
    # 납입 1회짜리를 직접 만든다
    rk = lev_r(D, 2.0)
    dfr = D['schdr']
    R = C = 0.0
    prev = w[lo]
    first = None
    for i in range(lo, hi):
        pos = w[i - 1] if i > lo else w[lo]
        if pos != prev:
            if pos >= 1:
                R += C * (1 - COST); C = 0.0
            else:
                C += R * (1 - COST); R = 0.0
            prev = pos
        R *= (1 + rk[i]); C *= (1 + dfr[i])
        if i > lo and months[i] != months[i - 1] and first is None:
            first = i
            if pos >= 1:
                R += 1.0
            else:
                C += 1.0
    if first is None:
        print('검산 적립(1회납입)  창 %d:%d 에 월 경계가 없다 — 검산 불가' % (lo, hi))
        return False
    got = R + C
    c, _ = sim(D, w, rk, start=D['idx'][first], end=D['idx'][hi - 1])
    exp = float(c.iloc[-1])
    err = abs(got / exp - 1)
    print('검산 적립(1회납입) vs 거치식  %.6f vs %.6f  오차=%.1e' % (got, exp, err))
    return err < 1e-9


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
      ④ 분수 비중(앙상블)에서도 after_tax(세율 0) == sim   ← 2026-09-04 추가
      ⑤ 적립(1회납입) == 거치식
    """
    from reentry_lib import run
    from hyst_core import A, B
    ok = True
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
    # 분수 비중에서도 같은가 — 축2 앙상블이 세금·구간 함수를 그대로 탈 수 있어야 한다
    wf = (rule_w(D['ddv'], -0.14, -0.14) + rule_w(D['ddv'], -0.16, -0.16)
          + rule_w(D['ddv'], -0.18, -0.18)) / 3.0
    cf, _ = sim(D, wf, rk2)
    vf, _ = after_tax(D, 2.0, wf, 0.0, True)
    errf = abs(vf / cf.iloc[-1] - 1)
    ok = ok and errf < 1e-6
    print('검산 분수비중 after_tax(세율0)  %.4f  vs sim %.4f  오차=%.1e'
          % (vf, cf.iloc[-1], errf))
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
