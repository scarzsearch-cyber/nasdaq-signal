# -*- coding: utf-8 -*-
"""
[2026-09-02 — 소유자 「실험 형태로 먼저」 → 같은 날 「일단 규약 부속서 등록 해봐」]
B 자체의 OOS 판정 규약 — **기저율 측정**(기본 모드) + **평가기**(`--oos`)

왜 이 파일인가
  T4 그림자에는 사건 단위 판정 규약이 있다(docs/history/전략_v80 §6 — M1·M2 기전 관문,
  출혈 한도 −29%, 현행 완성 사건 기저율 M1 16/21=76%·M2 17/21=81%를 근거로 사전 등록). **정작 돈이 실려 있는 B 에는
  없었다.** 02 §5 는 「기록만 하고 판단하지 않는다」, 04 §5-13 은 「−16 이 옳았나는 순수
  OOS 로만 판정된다」고 적었지만 **무엇을 어떻게 재서 언제 판정하는지는 어디에도 없었다.**
  규약 없이 OOS 가 쌓이면 판정은 결국 사후 재량이 된다 — 이 저장소가 가장 경계하는 형태.
  → 등록: `data/oos_protocol_b.json`(기계용 원본·지문) · 02 §5-1(사람용) · verify_all I13(지문 검사).
  이 파일은 규칙을 건드리지 않는다. 기본 모드는 **동결 이전 데이터로 관문의 역사 기저율**을
  재고, `--oos` 는 등록된 규약을 동결 이후 사건에 **기계적으로** 적용한다.

사전 등록 (결과 보기 전에 적음 — §-1 ⑤ 「실패하면 뭐가 참 / 통과하면 뭐가 참」)
  사건    = 마감 판정 w 가 1→0 (도피 신호일). 직전 도피와 252거래일 초과 간격이면 독립.
            (v80 §6-2 와 같은 규약. 장부 `state` QLD→SCHD 에 대응.)
  사건창  = 도피일 −63 ~ +252 거래일 (v80 M2 와 같은 창). +252 가 안 찬 사건은 판정에 안 쓴다.
  A 재난 지급: H(2배 맨몸) 사건창 MDD ≤ −50% 인 사건에서 B 의 사건창 MDD 가 H 보다 얕다.
      실패 = 「느린 약세장 보험」 기전이 그 재난에서 작동하지 않았다 (역사 8/8 · v210 재등록 2026-09-05, 등록 당시 7/7 → 1회 실패 = 역사 밖).
      통과 = 보험이 지급됐다 — 규칙 유지의 근거.
  B 보험료 상한: 사건창 B/H 총수익비 − 1 이 역사 P05(−29.3% · 등록 당시 −33.3%) 아래면 주의, 역사 최악(−41.1%) 아래면 역사 밖.
      실패 = 보험료가 역사보다 비싸다 — 기전 붕괴가 아니라 국면 변화일 수 있다 → 재검토 연구 개시.
  R  누적 출혈: 3년 롤링 B/H − 1 이 P05(−33.1% · 등록 당시 −31.5%) 아래면 주의, 최악(−49.3%) 아래면 역사 밖. 상시.
  이 규약이 **답하지 않는 것**: 「−16 이 −14 보다 나은가」. 이웃 문턱과의 차이는 OOS 몇 십 년이
  필요하다(04 §5-22 D). 이 규약은 「B 가 역사처럼 작동하는가」만 묻는다.
  대응은 **재검토 연구 개시**까지다 — 자동 변경 없음. 결합·대응은 소유자 위임(2026-09-02).

부수 측정 2건 (같은 엔진, 같은 사건 정의 — 기본 모드 [3]·[4])
  [3] 룩백 200 그림자의 정보량 — §5-14 D 가 「표본 내 200 이 낫지만 사전 식별 불가 → 유지」로
      닫았다. 규칙을 안 바꾸고 답을 얻는 길은 T4 처럼 **평가 전용 그림자**뿐인데, 그 전에
      「두 규칙이 실제로 얼마나 자주 갈리는가」를 알아야 그림자가 언제 말할 수 있는지 안다.
  [4] 부재 비용 — 04 §5-8 의 전환 놓침 최악 −96.5% 는 「사람이 안 움직인 것」의 값이다.
      반대편 값(공격 중 N 거래일 자리를 비울 때 **미리 방어로 두고 가는** 비용)은 없다.
      둘을 나란히 놓아야 부재 규칙을 정할 수 있다. 판정 아님 — 표만 낸다.

엔진: eng_common (1972~ 54년 · 방어 40/40/20 · 2배 합성 = QLD 역산 드래그 · 편도 0.1%).
검산이 공표(strategy_stats · v210 뒤 220,985.206 / Calmar 0.418)와 안 맞으면 즉시 중단.
★ 기저율은 v210 자료로 2026-09-05 재등록했다(JSON revisions · 02 §5-1) — 원자료가 또 바뀌면 자기검산이 판정을 멈춘다.
실행:  python research/oos_protocol_b.py          (기저율 · 부수 2건)
       python research/oos_protocol_b.py --oos    (등록 규약을 동결 이후 사건에 적용)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
import hashlib
import io
import json
import numpy as np
import pandas as pd
import eng_common as EC

try:
    _sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

PROTO = 'data/oos_protocol_b.json'
PRE, POST = 63, 252          # 사건창 (v80 M2 와 동일)
INDEP = 252                  # 독립 사건 간격
Y = 252


def mdd(seg):
    seg = np.asarray(seg, float)
    return float(np.min(seg / np.maximum.accumulate(seg) - 1.0))


def pct(a, q):
    a = np.asarray(a, float)
    return float(np.percentile(a, q)) if len(a) else float('nan')


def fingerprint(obj):
    """verify_all I13 과 같은 규약 — 'fingerprint' 키를 뺀 정렬 JSON 의 sha256 앞 16자."""
    body = {k: v for k, v in obj.items() if k != 'fingerprint'}
    s = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]


# ---------------------------------------------------------------- 엔진
def load():
    G, _X = EC.selfcheck()                    # 검산 — 실패 시 예외로 중단
    idx = pd.DatetimeIndex(G.idx)
    PX = pd.Series(np.asarray(G.D['px'], float), index=idx)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float))
    MIXR = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    w = EC.rule_dd(PX, -0.16, -0.16)
    B = np.asarray(EC.sim2(w, QLDR, MIXR), float)
    H = np.cumprod(1.0 + QLDR)                # 2배 맨몸(합성) — 매매 없음
    DEF = np.cumprod(1.0 + MIXR)              # 방어 바스켓만 보유
    return dict(idx=idx, PX=PX, QLDR=QLDR, MIXR=MIXR, w=w, B=B, H=H, DEF=DEF)


def escapes(w):
    return [i for i in range(1, len(w)) if w[i] == 0 and w[i - 1] == 1]


def independent(ev):
    out, last = [], -10**9
    for i in ev:
        if i - last > INDEP:
            out.append(i)
        last = i
    return set(out)


def event_rows(D):
    idx, w, B, H = D['idx'], D['w'], D['B'], D['H']
    n = len(idx)
    ev = escapes(w)
    ind = independent(ev)
    rows = []
    for i in ev:
        lo, hi = max(0, i - PRE), i + POST
        full = hi < n
        hi = min(hi, n - 1)
        b, h = B[lo:hi + 1] / B[lo], H[lo:hi + 1] / H[lo]
        j = next((k for k in range(i + 1, n) if w[k] == 1), None)
        rows.append(dict(
            i=i, date=idx[i].date(), indep=(i in ind), full=full,
            dur=(j - i) if j is not None else n - i,
            mdd_b=mdd(b), mdd_h=mdd(h),
            prem=float(b[-1] / h[-1] - 1.0),          # 사건창 B/H 총수익비 − 1
        ))
    return pd.DataFrame(rows), ev


def rolling3y(B, H):
    k = 3 * Y
    return B[k:] / B[:-k] / (H[k:] / H[:-k]) - 1.0


# ---------------------------------------------------------------- 기본 모드: 기저율
def base_rates(D):
    idx, w, B, H, DEF, PX, QLDR, MIXR = (D[k] for k in ('idx', 'w', 'B', 'H', 'DEF', 'PX', 'QLDR', 'MIXR'))
    n = len(idx)
    YEARS = (idx[-1] - idx[0]).days / 365.25
    print(f'표본 {idx[0].date()} ~ {idx[-1].date()} · {n:,}일 · {YEARS:.1f}년\n')

    E, ev = event_rows(D)
    Ef = E[E.full].copy()
    Ei = Ef[Ef.indep].copy()
    print('=' * 78)
    print('[1] 사건 — 도피 신호일 기준 (사건창 −63~+252 거래일, +252 미충족 사건 제외)')
    print('=' * 78)
    print(f'  도피 사건 {len(E)}회 · 창이 찬 사건 {len(Ef)}회 · **독립 사건 {len(Ei)}회** '
          f'(간격 >{INDEP}일) · 독립 사건 발생률 연 {len(Ei) / YEARS:.2f}회 '
          f'→ 독립 사건 1건에 평균 {YEARS / len(Ei):.1f}년')
    print(f'  방어 체류 중앙 {int(Ef.dur.median())}일 · 독립 사건만 중앙 {int(Ei.dur.median())}일')

    print('\n' + '=' * 78)
    print('[2] 관문 후보의 역사 기저율 — 부속서의 숫자 (판정 아님)')
    print('=' * 78)
    Ef['m1'] = Ef.mdd_b > Ef.mdd_h
    Ei['m1'] = Ei.mdd_b > Ei.mdd_h
    print('  M1 (사건창 MDD 에서 B 가 H 보다 얕다)')
    print(f'     전체 사건 {Ef.m1.mean() * 100:.0f}% ({int(Ef.m1.sum())}/{len(Ef)}) · '
          f'**독립 사건 {Ei.m1.mean() * 100:.0f}% ({int(Ei.m1.sum())}/{len(Ei)})**')
    print('     독립 사건에서 M1 실패가 연속 k 회 일어날 확률(역사 기저율이 유지된다면): '
          + ' · '.join(f'k={k} {(1 - Ei.m1.mean()) ** k * 100:.1f}%' for k in (1, 2, 3)))
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
    roll = rolling3y(B, H)
    print('\n  R  (누적 출혈 가드) 3년 롤링 B/H 총수익비 − 1 의 분포')
    print(f'     창 {len(roll):,}개(비중첩 {len(roll) / (3 * Y):.1f}개) · 중앙 {np.median(roll) * 100:+.1f}% · '
          f'P10 {pct(roll, 10) * 100:+.1f}% · **P05 {pct(roll, 5) * 100:+.1f}%** · 최악 {roll.min() * 100:+.1f}%')
    print(f'     역사에서 B 가 H 에 뒤진 3년 창 비율 {np.mean(roll < 0) * 100:.0f}% — '
          f'「보험은 평시에 진다」의 정량 (01 §4-1)')

    print('\n' + '=' * 78)
    print('[3] 룩백 200 그림자 — 두 규칙이 얼마나 자주 갈리는가 (성과 재측정 아님 — §5-14 D 가 이미 쟀다)')
    print('=' * 78)
    w200 = EC.rule_dd(PX, -0.16, -0.16, win=200)
    B200 = np.asarray(EC.sim2(w200, QLDR, MIXR), float)
    diff = (w200 != w)
    print(f'  상태가 다른 날 {int(diff.sum()):,}일 = 연 {diff.mean() * Y:.1f}일 · '
          f'전환 횟수 252:{len(ev) * 2} vs 200:{len(escapes(w200)) * 2}')
    ind = independent(ev)
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

    print('\n' + '=' * 78)
    print('[4] 부재 — 공격 중 N 거래일 자리를 비울 때 (판정 아님 · 부재 규칙의 재료)')
    print('=' * 78)
    att = np.where(w == 1)[0]
    print(f'  {"N일":>4}{"미리 방어로 두는 비용(중앙)":>22}{"P05":>9}{"P95":>9}'
          f'{"그 N일 안에 도피신호 확률":>22}{"신호 났는데 못 팔면(중앙)":>22}{"최악":>9}')
    for N in (5, 10, 20, 40):
        a = att[att + N < n]
        cost = DEF[a + N] / DEF[a] / (H[a + N] / H[a]) - 1.0          # 방어로 둔 값 − 공격 값
        hit = np.array([(w[i + 1:i + N + 1] == 0).any() for i in a])
        miss = np.asarray([H[i + 1 + N] / H[i + 1] - 1.0 for i in ev if i + 1 + N < n])
        print(f'  {N:>4}{np.median(cost) * 100:>+21.2f}%{pct(cost, 5) * 100:>+8.1f}%{pct(cost, 95) * 100:>+8.1f}%'
              f'{hit.mean() * 100:>21.1f}%{np.median(miss) * 100:>+21.1f}%{miss.min() * 100:>+8.1f}%')
    print('  읽는 법: 왼쪽은 「미리 방어로 두고 가는」 값(보통 소액 손해), 오른쪽은 「신호가 났는데 N일 못 판」 값.')
    print('  04 §5-8 의 −96.5% 는 「아예 안 판」 값이라 이 표의 오른쪽 끝보다 더 나쁘다.')

    print('\n' + '=' * 78)
    print('[5] 이 측정이 낳은 다음 질문 (§-1 절대멈춤 6)')
    print('=' * 78)
    print('  · 관문 결합·판정 사건 수·실패 시 대응 → 2026-09-02 등록(02 §5-1). 등록 뒤 사건이 쌓이면 손대지 않는다.')
    print('  · 그림자를 등록한다면 T4 와 같은 열 규약(사전 고정·빈 칸 허용·본 기록 무해)으로 — 열 3개가 5개가 된다.')
    print('  · 부재 규칙은 화면(신호 카드)에 한 줄로 실을 수 있는가 — v140 「먼저 자동화·화면」 원칙.')
    print('  · 평가기(--oos)를 파수꾼 check 에 얹을 것인가 — deploy/* 수정이라 소유자 승인 필요.')


# ---------------------------------------------------------------- --oos: 등록 규약 적용
def evaluate_oos(D):
    P = json.load(io.open(PROTO, encoding='utf-8'))
    fp = fingerprint(P)
    print('=' * 78)
    print(f'등록 규약 {PROTO} · 등록일 {P["registered_at"]} · 지문 {P["fingerprint"]}')
    print('=' * 78)
    if fp != P['fingerprint']:
        print(f'  ⛔ 지문 불일치 (재계산 {fp}) — 규약이 수정됐다. verify_all I13 이 실패한다. 판정을 내지 않는다.')
        return 2
    idx, B, H = D['idx'], D['B'], D['H']
    n = len(idx)
    start = pd.Timestamp(P['applies_to']['oos_start'])
    gA, gB, gR = P['gates']['A_disaster_payout'], P['gates']['B_premium'], P['gates']['R_rolling_3y']

    # 기저율 자기검산 — 원자료 갱신으로 역사 값이 흔들리면 여기서 드러난다 (판정 불가로 처리)
    E, _ev = event_rows(D)
    pre = E[E.full & (pd.to_datetime(E.date) < start)]
    dis = pre[(pre.mdd_h <= -0.5) & pre.indep]              # A 의 등록값(8/8 · 등록 당시 7/7)은 **독립** 사건 기준
    a_pass, a_n = int((dis.mdd_b > dis.mdd_h).sum()), len(dis)
    p05 = pct(pre.prem, 5)                                    # B 의 P05 는 전체 사건(69 · 등록 당시 70) 기준
    print(f'  기저율 자기검산: A 독립 {a_pass}/{a_n} (등록 {gA["history"]["pass"]}/{gA["history"]["n"]}) · '
          f'B 전체 {len(pre)}건 P05 {p05 * 100:+.1f}% (등록 {gB["history"]["p05"] * 100:+.1f}%)')
    drift = (a_pass, a_n) != (gA['history']['pass'], gA['history']['n']) or abs(p05 - gB['history']['p05']) > 0.01
    if drift:
        print('  ⚠ 역사 기저율이 등록값과 다르다 — 원자료 갱신(수정주가 재조정 등) 때문일 수 있다. '
              '판정 전에 원인을 적고 지문을 의도적으로 갱신하라.')
        print('  → **판정 중단.** 등록 당시 저울이 달라졌으므로 OOS 정상/주의/역사 밖 판정을 내리지 않는다.')
        return 2

    # 동결 이후 사건
    oos = E[pd.to_datetime(E.date) >= start]
    print(f'\n  동결 이후 도피 사건 {len(oos)}건 (엔진 자료 마지막 날 {idx[-1].date()})')
    if len(oos) == 0:
        print('  → **판정 불가 — 정상.** 사건이 없다. (독립 사건은 역사상 2.6년에 1건)')
    outside, warn = [], []
    for r in oos.itertuples():
        tag = '독립' if r.indep else '종속'
        if not r.full:
            print(f'  · {r.date} [{tag}] 창 미충족 (+252 거래일 전) — 판정 보류')
            continue
        lines = []
        if r.mdd_h <= -0.5:
            okA = r.mdd_b > r.mdd_h
            lines.append(f'A 재난 지급 {"통과" if okA else "★역사 밖"} (B {r.mdd_b * 100:.1f}% vs H {r.mdd_h * 100:.1f}%)')
            if not okA and r.indep:
                outside.append(f'{r.date} A')
        else:
            lines.append(f'A 해당 없음 (H 창 MDD {r.mdd_h * 100:.1f}% > −50%)')
        if r.prem < gB['outside_history_below']:
            lines.append(f'B 보험료 ★역사 밖 ({r.prem * 100:+.1f}%)'); outside.append(f'{r.date} B')
        elif r.prem < gB['warn_below']:
            lines.append(f'B 보험료 주의 ({r.prem * 100:+.1f}%)'); warn.append(f'{r.date} B')
        else:
            lines.append(f'B 보험료 정상 ({r.prem * 100:+.1f}%)')
        print(f'  · {r.date} [{tag}] ' + ' · '.join(lines))

    # R — 동결 + 756 거래일 뒤부터
    i0 = int(np.searchsorted(idx.values, np.datetime64(start)))
    if n - 1 - i0 >= 3 * Y:
        roll = rolling3y(B, H)
        seg = roll[i0:]                       # 창 끝이 동결 이후인 것만
        cur = float(seg[-1])
        st = '★역사 밖' if cur < gR['outside_history_below'] else ('주의' if cur < gR['warn_below'] else '정상')
        print(f'\n  R 3년 롤링 B/H − 1: 현재 {cur * 100:+.1f}% → {st} · 동결 이후 최저 {seg.min() * 100:+.1f}%')
        if st == '★역사 밖':
            outside.append('R')
        elif st == '주의':
            warn.append('R')
    else:
        print(f'\n  R 계산 불가 — 동결 뒤 {max(n - 1 - i0, 0)}거래일 (756 필요)')

    print('\n  판정: ' + ('**역사 밖 — 재검토 연구 개시** (' + ', '.join(outside) + ')' if outside
                        else ('주의 (' + ', '.join(warn) + ') — 기록·알림만' if warn
                              else '재검토 사유 없음' + (' (판정 사건 0건)' if len(oos) == 0 else ''))))
    print('  이 출력은 자동으로 아무것도 바꾸지 않는다 — 규약 response 항목대로.')
    return 1 if outside else 0


if __name__ == '__main__':
    D = load()
    if '--oos' in _sys.argv:
        _sys.exit(evaluate_oos(D))
    base_rates(D)
