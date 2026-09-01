# -*- coding: utf-8 -*-
"""
[실험 · 2026-09-02 — 소유자 「실험 형태로 먼저 진행, 최종 컨펌은 내가」]
B 자체의 OOS 판정 규약을 사전 등록하기 위한 **기저율 측정** (+ 부수 2건)

왜 이 실험인가
  T4 그림자에는 사건 단위 판정 규약이 있다(docs/history/전략_v80 §6 — M1·M2 기전 관문,
  출혈 한도 −29%, 역사 기저율 73%/77% 를 근거로 사전 등록). **정작 돈이 실려 있는 B 에는
  없다.** 02 §5 는 「기록만 하고 판단하지 않는다」, 04 §5-13 은 「−16 이 옳았나는 순수
  OOS 로만 판정된다」고 적었지만 **무엇을 어떻게 재서 언제 판정하는지는 어디에도 없다.**
  규약 없이 OOS 가 쌓이면 판정은 결국 사후 재량이 된다 — 이 저장소가 가장 경계하는 형태.
  이 스크립트는 규칙을 건드리지 않는다. **동결 이전 데이터로 관문 후보의 역사 기저율을
  재서, 부속서 초안의 숫자를 채우는 것**이 전부다. 등록 여부는 소유자가 정한다.

사전 등록 (결과 보기 전에 적음 — §-1 ⑤ 「실패하면 뭐가 참 / 통과하면 뭐가 참」)
  사건    = 마감 판정 w 가 1→0 (도피 신호일). 직전 도피와 252거래일 초과 간격이면 독립.
            (v80 §6-2 와 같은 규약. 장부 `state` QLD→SCHD 에 대응.)
  사건창  = 도피일 −63 ~ +252 거래일 (v80 M2 와 같은 창). +252 가 안 찬 사건은 판정에 안 쓴다.
  M1 보험 지급: 사건창 안에서 B 의 MDD 가 2배 맨몸(H)보다 얕다.
      실패 = 판 직후 시장이 곧장 회복해 보험이 헛돈 것. 한 사건의 실패는 정상 범위
             (기저율이 말한다). **모든 독립 사건에서 실패**해야 「느린 약세장 보험」 기전 불발.
      통과 = 보험이 지급됐다 — 규칙 유지의 근거.
  M2 보험료 상한: 사건창 B/H 총수익비(프리미엄)가 역사 분포의 P05 안.
      실패 = 보험료가 역사 밖으로 비싸다 — 재검토 연구 개시(전제 Level 과 함께 읽는다).
      통과 = 역사 범위 안의 보험료.
  R  누적 출혈 가드: 3년 롤링 B/H 가 역사 P05 밖이면 사건과 무관하게 재검토 개시
      (v80 (b) 의 −29% 와 같은 자리 — 극단 출혈 방지용이지 평균 성적 판정이 아니다).
  이 규약이 **답하지 않는 것**: 「−16 이 −14 보다 나은가」. 이웃 문턱과의 차이는 OOS 몇
  십 년이 필요하다(04 §5-22 D). 이 규약은 「B 가 역사처럼 작동하는가」만 묻는다.
  판정 결합·실패 시 대응(k 인하·중단·재검토)은 **측정이 아니라 소유자 결정** — 여기서 정하지 않는다.

부수 측정 2건 (같은 엔진, 같은 사건 정의)
  [3] 룩백 200 그림자의 정보량 — §5-14 D 가 「표본 내 200 이 낫지만 사전 식별 불가 → 유지」로
      닫았다. 규칙을 안 바꾸고 답을 얻는 길은 T4 처럼 **평가 전용 그림자**뿐인데, 그 전에
      「두 규칙이 실제로 얼마나 자주 갈리는가」를 알아야 그림자가 언제 말할 수 있는지 안다.
  [4] 부재 비용 — 04 §5-8 의 전환 놓침 최악 −96.5% 는 「사람이 안 움직인 것」의 값이다.
      반대편 값(공격 중 N 거래일 자리를 비울 때 **미리 방어로 두고 가는** 비용)은 없다.
      둘을 나란히 놓아야 부재 규칙을 정할 수 있다. 판정 아님 — 표만 낸다.

엔진: eng_common (1972~ 54년 · 방어 40/40/20 · 2배 합성 = QLD 역산 드래그 · 편도 0.1%).
검산이 공표(217,110.075 / Calmar 0.418)와 안 맞으면 즉시 중단.
실행:  python research/oos_protocol_b.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import numpy as np
import pandas as pd
import eng_common as EC

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PRE, POST = 63, 252          # 사건창 (v80 M2 와 동일)
INDEP = 252                  # 독립 사건 간격
Y = 252


def mdd(seg):
    seg = np.asarray(seg, float)
    return float(np.min(seg / np.maximum.accumulate(seg) - 1.0))


def pct(a, q):
    a = np.asarray(a, float)
    return float(np.percentile(a, q)) if len(a) else float('nan')


# ---------------------------------------------------------------- [0] 검산
G, _X = EC.selfcheck()                    # 실패 시 예외 — 여기서 멈춘다
idx = pd.DatetimeIndex(G.idx)
n = len(idx)
PX = pd.Series(np.asarray(G.D['px'], float), index=idx)
QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
YEARS = (idx[-1] - idx[0]).days / 365.25

w252 = EC.rule_dd(PX, -0.16, -0.16)
B = np.asarray(EC.sim2(w252, QLDR, MIXR), float)
H = np.cumprod(1.0 + QLDR)                # 2배 맨몸(합성) — 매매 없음
DEF = np.cumprod(1.0 + MIXR)              # 방어 바스켓만 보유
print(f'표본 {idx[0].date()} ~ {idx[-1].date()} · {n:,}일 · {YEARS:.1f}년\n')


# ---------------------------------------------------------------- [1] 사건
def escapes(w):
    return [i for i in range(1, len(w)) if w[i] == 0 and w[i - 1] == 1]


def independent(ev):
    out, last = [], -10**9
    for i in ev:
        if i - last > INDEP:
            out.append(i)
        last = i
    return out


ev = escapes(w252)
ind = set(independent(ev))
rows = []
for i in ev:
    lo, hi = max(0, i - PRE), i + POST
    full = hi < n
    hi = min(hi, n - 1)
    b, h = B[lo:hi + 1] / B[lo], H[lo:hi + 1] / H[lo]
    j = next((k for k in range(i + 1, n) if w252[k] == 1), None)
    rows.append(dict(
        date=idx[i].date(), indep=(i in ind), full=full,
        dur=(j - i) if j is not None else n - i,
        mdd_b=mdd(b), mdd_h=mdd(h),
        prem=float(b[-1] / h[-1] - 1.0),          # 사건창 B/H 총수익비 − 1
    ))
E = pd.DataFrame(rows)
Ef = E[E.full].copy()
Ei = Ef[Ef.indep].copy()

print('=' * 78)
print('[1] 사건 — 도피 신호일 기준 (사건창 −63~+252 거래일, +252 미충족 사건 제외)')
print('=' * 78)
print(f'  도피 사건 {len(E)}회 · 창이 찬 사건 {len(Ef)}회 · **독립 사건 {len(Ei)}회** '
      f'(간격 >{INDEP}일) · 독립 사건 발생률 연 {len(Ei) / YEARS:.2f}회 '
      f'→ 독립 사건 1건에 평균 {YEARS / len(Ei):.1f}년')
print(f'  방어 체류 중앙 {int(Ef.dur.median())}일 · 독립 사건만 중앙 {int(Ei.dur.median())}일')

# ---------------------------------------------------------------- [2] 관문 후보 기저율
print('\n' + '=' * 78)
print('[2] 관문 후보의 역사 기저율 — 부속서 초안의 숫자 (판정 아님)')
print('=' * 78)
Ef['m1'] = Ef.mdd_b > Ef.mdd_h
Ei['m1'] = Ei.mdd_b > Ei.mdd_h
print(f'  M1 (사건창 MDD 에서 B 가 H 보다 얕다)')
print(f'     전체 사건 {Ef.m1.mean() * 100:.0f}% ({int(Ef.m1.sum())}/{len(Ef)}) · '
      f'**독립 사건 {Ei.m1.mean() * 100:.0f}% ({int(Ei.m1.sum())}/{len(Ei)})**')
print(f'     독립 사건에서 M1 실패가 연속 k 회 일어날 확률(역사 기저율이 유지된다면): '
      + ' · '.join(f'k={k} {(1 - Ei.m1.mean()) ** k * 100:.1f}%' for k in (1, 2, 3)))

# 맨몸 창 MDD 버킷별 — 「보험이 언제 지급되는가」
print('\n  M1 을 맨몸(H) 사건창 MDD 버킷으로 나누면 (보험 기전의 실체):')
print(f'  {"H 창 MDD":<14}{"사건":>5}{"독립":>5}{"M1 통과":>9}{"프리미엄 중앙":>12}{"프리미엄 P10":>12}')
for lo_, hi_, nm in ((-1.0, -0.5, '≤ −50%'), (-0.5, -0.3, '−50~−30%'), (-0.3, 0.0, '> −30%')):
    s = Ef[(Ef.mdd_h > lo_) & (Ef.mdd_h <= hi_)]
    if len(s) == 0:
        continue
    print(f'  {nm:<14}{len(s):>5}{int(s.indep.sum()):>5}{s.m1.mean() * 100:>8.0f}%'
          f'{s.prem.median() * 100:>+11.1f}%{pct(s.prem, 10) * 100:>+11.1f}%')

print('\n  M2 (사건창 프리미엄 = B/H 총수익비 − 1 · 음수 = 보험료)')
for nm, s in (('전체 사건', Ef), ('독립 사건', Ei)):
    print(f'     {nm:<6} 중앙 {s.prem.median() * 100:+.1f}% · 평균 {s.prem.mean() * 100:+.1f}% · '
          f'P10 {pct(s.prem, 10) * 100:+.1f}% · **P05 {pct(s.prem, 5) * 100:+.1f}%** · '
          f'최악 {s.prem.min() * 100:+.1f}% · 최선 {s.prem.max() * 100:+.1f}%')
worst = Ef.sort_values('prem').head(3)
print('     보험료 최악 3건: ' + ' · '.join(f'{r.date} {r.prem * 100:+.1f}% (H창MDD {r.mdd_h * 100:.0f}%)'
                                       for r in worst.itertuples()))

print('\n  R  (누적 출혈 가드 후보) 3년 롤링 B/H 총수익비 − 1 의 분포')
k = 3 * Y
roll = B[k:] / B[:-k] / (H[k:] / H[:-k]) - 1.0
print(f'     창 {len(roll):,}개(비중첩 {len(roll) / k:.1f}개) · 중앙 {np.median(roll) * 100:+.1f}% · '
      f'P10 {pct(roll, 10) * 100:+.1f}% · **P05 {pct(roll, 5) * 100:+.1f}%** · 최악 {roll.min() * 100:+.1f}%')
print(f'     역사에서 B 가 H 에 뒤진 3년 창 비율 {np.mean(roll < 0) * 100:.0f}% — '
      f'「보험은 평시에 진다」의 정량 (01 §4-1)')
print(f'     v80 이 T4 에 쓴 −29% 와 같은 자리에 올 숫자는 위 P05 다 — 대상이 다르므로 값도 다르다')

# ---------------------------------------------------------------- [3] 룩백 200 그림자 정보량
print('\n' + '=' * 78)
print('[3] 룩백 200 그림자 — 두 규칙이 얼마나 자주 갈리는가 (성과 재측정 아님 — §5-14 D 가 이미 쟀다)')
print('=' * 78)
w200 = EC.rule_dd(PX, -0.16, -0.16, win=200)
B200 = np.asarray(EC.sim2(w200, QLDR, MIXR), float)
diff = (w200 != w252)
print(f'  상태가 다른 날 {int(diff.sum()):,}일 = 연 {diff.mean() * Y:.1f}일 · 전환 횟수 252:{len(ev)}×2 vs 200:{len(escapes(w200)) * 2}')
# 독립 사건(252 기준)의 사건창 안에서 두 규칙이 갈렸는가 → 그림자가 「말할 수 있는」 사건
div, better = 0, 0
for i in sorted(ind):
    lo, hi = max(0, i - PRE), i + POST
    if hi >= n:
        continue
    if diff[lo:hi + 1].any():
        div += 1
        if B200[hi] / B200[lo] > B[hi] / B[lo]:
            better += 1
print(f'  독립 사건 {len(Ei)}건 중 사건창 안에서 갈린 사건 **{div}건** ({div / len(Ei) * 100:.0f}%) '
      f'→ 그림자가 판정 재료를 얻는 속도 = 약 {YEARS / max(div, 1):.1f}년에 1건')
print(f'  갈린 사건에서 200 이 사건창 수익으로 이긴 비율 {better}/{div} — 미래 그림자 판정의 사전 기저율')
print(f'  ⚠ 사건 3건이 모이는 데 약 {3 * YEARS / max(div, 1):.0f}년. 그림자는 「언젠가 답이 나온다」이지 '
      f'「몇 년 안에」가 아니다 — 등록한다면 이 속도를 알고 등록해야 한다')

# ---------------------------------------------------------------- [4] 부재 비용
print('\n' + '=' * 78)
print('[4] 부재 — 공격 중 N 거래일 자리를 비울 때 (판정 아님 · 부재 규칙의 재료)')
print('=' * 78)
att = np.where(w252 == 1)[0]
print(f'  {"N일":>4}{"미리 방어로 두는 비용(중앙)":>22}{"P05":>9}{"P95":>9}'
      f'{"그 N일 안에 도피신호 확률":>22}{"신호 났는데 못 팔면(중앙)":>22}{"최악":>9}')
for N in (5, 10, 20, 40):
    a = att[att + N < n]
    cost = DEF[a + N] / DEF[a] / (H[a + N] / H[a]) - 1.0          # 방어로 둔 값 − 공격 값
    # 부재 중 도피 신호가 나는 확률
    hit = np.array([(w252[i + 1:i + N + 1] == 0).any() for i in a])
    # 신호가 났는데 N일 뒤에야 판 경우: 신호일 다음날 종가 대비 N일 뒤 종가로 2배 자산 보유
    miss = []
    for i in ev:
        if i + 1 + N < n:
            miss.append(H[i + 1 + N] / H[i + 1] - 1.0)
    miss = np.asarray(miss)
    print(f'  {N:>4}{np.median(cost) * 100:>+21.2f}%{pct(cost, 5) * 100:>+8.1f}%{pct(cost, 95) * 100:>+8.1f}%'
          f'{hit.mean() * 100:>21.1f}%{np.median(miss) * 100:>+21.1f}%{miss.min() * 100:>+8.1f}%')
print('  읽는 법: 왼쪽은 「미리 방어로 두고 가는」 값(보통 소액 손해), 오른쪽은 「신호가 났는데 N일 못 판」 값.')
print('  04 §5-8 의 −96.5% 는 「아예 안 판」 값이라 이 표의 오른쪽 끝보다 더 나쁘다.')

# ---------------------------------------------------------------- [5] 파생 질문
print('\n' + '=' * 78)
print('[5] 이 측정이 낳은 다음 질문 (§-1 절대멈춤 6)')
print('=' * 78)
print('  · M1·M2·R 을 어떻게 결합하고, 실패 시 대응이 무엇인가(k 인하 / 중단 / 재검토만) — 소유자 결정.')
print('  · 독립 사건이 평균 수 년에 1건이면 「판정 시점」은 사건 수로 정해야 한다 — 몇 건인가.')
print('  · 그림자를 등록한다면 T4 와 같은 열 규약(사전 고정·빈 칸 허용·본 기록 무해)으로 — 열 3개가 5개가 된다.')
print('  · 부재 규칙은 화면(신호 카드)에 한 줄로 실을 수 있는가 — v140 「먼저 자동화·화면」 원칙.')
