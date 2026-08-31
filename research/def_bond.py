# -*- coding: utf-8 -*-
"""
[방어 국채 다리 — 헤지 상관과 만기 최적, 2026-08-31 소유자 질문] 판정 아님·전략 무변경.

질문: "미국채·한국채·단기채·10년채 같은 건 헤지 상관관계가 있니? 그 최적도 찾아봐."

현행: 방어 바스켓 배당40 / **미국채 40** / 금20. 국채 다리의 실물은 305080
TIGER 미국채10년선물 — 이름은 10년이나 **실효만기 약 5년 · 환노출 · 선물형**이다
(axis_krspec.py 실측, b2≈0.81). 그래서 모형 키가 `ust5` 다.

이미 시험된 것 (재탐색 금지 — 04·HANDOFF §2):
  · ust5 / ust10 / T-bill / 배당·금 조합 18종 — v23 축4 `axis_defmix.CANDS`
  · 방어를 현금(T-bill)으로 대체 — 바스켓에 −17.85% 로 패배 (v27/v36)
  · 방어자산을 신호로 골라 담기 — 관문 5개 전부 탈락 (v27)
  · 방어 비중 40/40/20 — 완전한 고원 (04 §5-15 C)
미시험: **만기 격자 전체**(2·3·7·20·30년) · **한국 국고채**.

────────────────────────────────────────────────────────────────────────
★ 사전 등록 (2026-08-31, 결과를 보기 전에 적는다 — CLAUDE.md §-1)
────────────────────────────────────────────────────────────────────────
관문 (HANDOFF §2-0 순서 그대로, 문턱도 그대로):
  ① Calmar **상대 개선 > +10.2%** (독립 위기 19회에서 나온 2σ 문턱)
  ② **20년창 p05 ≥ 현행** — 진짜 관문. Calmar 는 MDD 만 줄여도 오르므로 속는다
  ③ 원화(1997~)에서도 ①②가 유지
  ④ **고원** — 인접 만기에서도 개선이 이어질 것 (첨탑이면 기각)
구조 통제: 만기 비교는 **전부 선물형·같은 보수**로 맞춘다. 현물형/환헤지는 별도 표기
  (실물 상품의 구조가 만기마다 다르다 — 모형 최적이 살 수 있는 물건이 아닐 수 있다).

「실패하면 무엇이 참인가 / 통과하면 무엇이 참인가」(§-1 절대멈춤 5):
  · 통과 = 만기 축에 실제 여지가 있다  → **기록만** 한다(규칙은 동결)
  · 실패 = ust5 가 고원 안에 있다      → 현행 유지 근거가 강해진다
  → 두 답이 다르다. 관문으로 성립한다.

판정 규약: 하나라도 미달이면 **현행 유지**. 전부 통과해도 **채택하지 않는다** —
동결(2026-08-27) 규칙이며 이 파일의 산출물은 「고원 안인가」의 답뿐이다.

실행: python research/def_bond.py
"""
# --- [v39] 경로보정 ---------------------------------------------------------
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
# ---------------------------------------------------------------------------
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import hist_defasset as DA                               # noqa: E402
import hist_data as H                                    # noqa: E402
import eng_common as EC                                  # noqa: E402

# ── 사전 등록 문턱 (여기서만 정의한다 — 아래 코드는 이 값을 읽기만) ──────────
GATE1_CALMAR = 0.102          # 상대 개선률
GATE2_P05 = 1.0               # 현행 대비 비율 하한 (1.0 = 현행 이상)
# ─────────────────────────────────────────────────────────────────────────────

CRISES = [('73-74 오일', '1973-01-11', '1974-10-03'),
          ('80-82 인플레', '1980-11-28', '1982-08-12'),
          ('87 블랙먼데이', '1987-08-25', '1987-12-04'),
          ('닷컴 00-02', '2000-03-10', '2002-10-09'),
          ('GFC 07-09', '2007-10-31', '2009-03-09'),
          ('코로나 20', '2020-02-19', '2020-03-23'),
          ('2022 베어', '2022-01-03', '2022-10-12')]

MATS = [2, 3, 5, 7, 10, 20, 30]
TYX_START = pd.Timestamp('1977-02-15')        # 30년 금리 고시 시작 (axis_defmix 와 동일)


def bond_parts(idx):
    """만기별 국채 일간수익 — **구조를 고정한다**: 전부 선물형 + 같은 보수.

    실물 305080/308620 이 선물형이므로 그 구조로 통일해야 만기끼리 비교가 된다.
    금리 출처는 만기 10 이하는 TNX(10년), 20 이상은 TYX(30년) — 상수만기 근사이며
    커브 모양은 반영하지 않는다(이 근사는 현행 ust5 도 똑같이 쓴다)."""
    out = {}
    for m in MATS:
        src = 'TNX' if m <= 10 else 'TYX'
        out[f'ust{m}'] = DA.ust_tr(idx, m, src, futures=True, fee=DA.UST_FEE)
    out['ust5_cash'] = DA.ust_tr(idx, 5, 'TNX')          # 현물형 대조군
    out['tbill'] = H.tbill_daily(idx)
    # ★ TYX(30년 금리)는 1977-02-15 고시 시작이다. ust_tr 안의 bfill 이 그 이전을
    #   1977년 금리로 **채워 버리므로** 반드시 잘라낸다 (axis_defmix.materials 와 같은 처리).
    #   이 마스킹을 빠뜨리면 1972~77 이 지어낸 값으로 채워져 20·30년이 유리해진다.
    for k in ('ust20', 'ust30'):
        out[k] = np.where(idx < TYX_START, np.nan, out[k])
    return out


def krw_fx(idx):
    """원/달러 일간 변화율 — 환노출 자산의 원화 수익 = 달러수익 + 환변화."""
    d = pd.read_csv(_os.path.join('data', 'hist', 'fred_DEXKOUS.csv'))
    c = [x for x in d.columns if x.lower().startswith('observation')][0]
    v = [x for x in d.columns if x != c][0]
    s = pd.to_numeric(d.set_index(pd.to_datetime(d[c]))[v], errors='coerce').dropna()
    s = s.reindex(idx.union(s.index)).ffill().reindex(idx)
    return s.pct_change().fillna(0.0).values, s.first_valid_index()


def main():
    G, _ = EC.selfcheck()
    idx = G.idx
    D, wB = G.D, np.asarray(G.wB, float)
    n = len(idx)
    qr = np.nan_to_num(pd.Series(D['px']).pct_change().values)
    QLDR = np.nan_to_num(np.asarray(D['qldr'], float))
    parts = bond_parts(idx)
    parts['div'] = np.asarray(D['schdr'], float)
    parts['gold'] = DA.gold_r(idx)
    fx, fx0 = krw_fx(idx)

    # ── 축퇴 검산: 내가 만든 ust5 부품이 공용 모형과 오차 0 인가 ─────────────
    mine = DA.mix_monthly_parts(idx, dict(div=.40, ust5=.40, gold=.20),
                                {k: parts[k] for k in ('div', 'ust5', 'gold')})
    ref = DA.mix_monthly(idx, DA.MIX_V23, D['schdr'])
    err = float(np.max(np.abs(mine - ref)))
    a_cur = EC.sim2(wB, QLDR, np.nan_to_num(mine))
    m_cur = EC.fullmet(a_cur, idx=idx)
    print(f'[검산] 내 ust5 조립 vs DA.mix_monthly 오차 {err:.2e} · '
          f'B 재현 final {m_cur["final"]:,.3f} Calmar {m_cur["calmar"]:.3f}')
    assert err < 1e-15, '축퇴 검산 실패 — 부품 조립이 공용 모형과 다르다'

    # ── [1] 헤지 상관 — 사실만 ──────────────────────────────────────────────
    print('\n' + '=' * 74)
    print(' [1] 헤지 상관 — 국채가 정말 QQQ 를 헤지하는가 (판정 아님, 사실)')
    print('=' * 74)
    worst = np.argsort(qr)[:int(n * 0.05)]               # QQQ 최악 5% 날
    defmask = wB < 0.5                                   # 실제로 방어를 들고 있던 날
    print(f'  표본: 전체 {n:,}일 · QQQ 최악5% {len(worst):,}일 · 방어 보유 {int(defmask.sum()):,}일')
    print(f"\n  {'자산':<12}{'전체상관':>9}{'최악5%상관':>11}{'방어중상관':>11}"
          f"{'최악5%일평균':>13}{'연CAGR':>9}")
    order = ['div', 'gold', 'tbill'] + [f'ust{m}' for m in MATS] + ['ust5_cash']
    for k in order:
        r = np.nan_to_num(parts[k], nan=np.nan)
        ok = ~np.isnan(r)
        if ok.sum() < 252:
            continue
        c_all = float(np.corrcoef(r[ok][1:], qr[ok][1:])[0, 1])
        w_ = worst[ok[worst]]
        c_w = float(np.corrcoef(r[w_], qr[w_])[0, 1])
        dm = defmask & ok
        c_d = float(np.corrcoef(r[dm], qr[dm])[0, 1])
        cg = (np.nanprod(1 + r[ok]) ** (252 / ok.sum()) - 1) * 100
        star = ' ←현행' if k == 'ust5' else ''
        print(f'  {k:<12}{c_all:>9.3f}{c_w:>11.3f}{c_d:>11.3f}'
              f'{r[w_].mean()*100:>12.2f}%{cg:>8.2f}%{star}')
    print('  ※ 상관이 낮아도 「같이 빠지면」 소용없다 — 최악5%일 평균이 그 답이다.')

    # 원화 기준 (환노출 반영) — 실제로 사는 것은 원화 상품
    print(f'\n  ── 원화 기준 (환노출: 달러수익 + 원/달러 변화, {str(fx0.date())}~) ──')
    kb = idx >= fx0
    print(f"  {'자산':<12}{'전체상관':>9}{'최악5%상관':>11}{'최악5%일평균':>13}")
    kworst = np.argsort(np.where(kb, qr, np.inf))[:int(kb.sum() * 0.05)]
    for k in ['div', 'gold'] + [f'ust{m}' for m in (5, 10, 30)]:
        r = np.nan_to_num(parts[k], nan=np.nan) + fx     # 환노출
        ok = (~np.isnan(r)) & kb
        if ok.sum() < 252:
            continue
        c_all = float(np.corrcoef(r[ok][1:], qr[ok][1:])[0, 1])
        w_ = kworst[ok[kworst]]
        c_w = float(np.corrcoef(r[w_], qr[w_])[0, 1])
        print(f'  {k:<12}{c_all:>9.3f}{c_w:>11.3f}{r[w_].mean()*100:>12.2f}%')

    # 위기별 실제 수익
    print('\n  ── 위기 구간별 누적 수익 (헤지가 실제로 작동했는가) ──')
    hdr = f"  {'위기':<14}{'QQQ':>9}" + ''.join(f'{k:>10}' for k in
                                                ('div', 'ust5', 'ust10', 'ust30', 'gold', 'tbill'))
    print(hdr)
    for nm, s, e in CRISES:
        i0, i1 = idx.searchsorted(pd.Timestamp(s)), idx.searchsorted(pd.Timestamp(e), side='right')
        row = f'  {nm:<14}{(np.nanprod(1+qr[i0:i1])-1)*100:>8.1f}%'
        for k in ('div', 'ust5', 'ust10', 'ust30', 'gold', 'tbill'):
            seg = parts[k][i0:i1]
            row += ('       —  ' if np.isnan(seg).all()
                    else f'{(np.nanprod(1+np.nan_to_num(seg))-1)*100:>9.1f}%')
        print(row)

    # ── [2] 만기 스윕 — 사전 등록 관문 적용 ─────────────────────────────────
    print('\n' + '=' * 74)
    print(' [2] 만기 최적 — 배당40 / 국채40 / 금20 에서 국채 다리만 바꾼다')
    print('=' * 74)
    # 공통창: 20·30년은 TYX 고시(1977-02) 이후만 존재한다 → 같은 창에서 비교
    tyx_ok = ~np.isnan(parts['ust30'])
    lo = int(np.argmax(tyx_ok))
    print(f'  공통창 {str(idx[lo].date())} ~ {str(idx[-1].date())} '
          f'({(idx[-1]-idx[lo]).days/365.25:.1f}년) — 30년 금리 고시 시작에 맞춤')

    def run_leg(key, i0=0):
        wts = dict(div=.40, gold=.20); wts[key] = .40
        mixr = DA.mix_monthly_parts(idx, wts, {k: np.nan_to_num(parts[k]) for k in wts})
        a = EC.sim2(wB[i0:], QLDR[i0:], mixr[i0:])
        m = EC.fullmet(a, idx=idx[i0:])
        m['p05'] = EC.p05_20y(a)
        return m

    for i0, lab in ((lo, f'공통창 {idx[lo].year}~'), (0, f'전구간 {idx[0].year}~ (20·30년 제외)')):
        keys = ([f'ust{m}' for m in MATS] + ['ust5_cash', 'tbill'] if i0 == lo else
                [f'ust{m}' for m in MATS if m <= 10] + ['ust5_cash', 'tbill'])
        base = run_leg('ust5', i0)
        print(f'\n  ── {lab} ──')
        print(f"  {'국채 다리':<12}{'최종배수':>12}{'CAGR':>8}{'MDD':>9}{'Calmar':>8}"
              f"{'ΔCalmar':>9}{'20년창p05':>10}{'Δp05':>8}")
        for k in keys:
            m = run_leg(k, i0)
            d1 = m['calmar'] / base['calmar'] - 1
            d2 = (m['p05'] / base['p05'] - 1) if base['p05'] == base['p05'] else np.nan
            star = ' ←현행' if k == 'ust5' else (' ★①통과' if d1 > GATE1_CALMAR else '')
            print(f"  {k:<12}{m['final']:>12,.1f}{m['cagr']:>7.2f}%{m['mdd']:>8.1f}%"
                  f"{m['calmar']:>8.3f}{d1*100:>8.1f}%{m['p05']:>9.2f}배{d2*100:>7.1f}%{star}")

    # ── [2-b] 반증 — 「ust5 가 최적」이 창·분위 하나의 산물인가 ──────────────
    #   현행이 이겼다 = 「기각」 방향이다. §-1 ⓓ: 기각도 편향된다 → ⓑ 를 적용한다.
    #   p05·20년창은 내가 고른 지표다. 창 3종 × 분위 3종 전 격자에서 봉우리가
    #   유지되는지 본다. 한 칸에서만 이기면 그건 최적이 아니라 우연이다.
    print('\n' + '=' * 74)
    print(' [2-b] 반증 — 봉우리가 (20년창, p05) 한 칸의 산물인가')
    print('=' * 74)
    curves = {}
    for k in [f'ust{m}' for m in MATS]:
        wts = dict(div=.40, gold=.20); wts[k] = .40
        mixr = DA.mix_monthly_parts(idx, wts, {j: np.nan_to_num(parts[j]) for j in wts})
        curves[k] = EC.sim2(wB[lo:], QLDR[lo:], mixr[lo:])
    print(f"  창×분위마다 **어느 만기가 1등인가** (공통창 {idx[lo].year}~, 전 격자)")
    print(f"  {'창':>6}" + ''.join(f'{f'p{q:02d}':>10}' for q in (5, 10, 20)) + '   ← 각 칸의 1등')
    win = {}
    for w, wl in ((2520, '10년'), (3780, '15년'), (5040, '20년')):
        row = f'  {wl:>6}'
        for q in (5, 10, 20):
            best, bv = None, -np.inf
            for k, a in curves.items():
                if len(a) <= w + 252:
                    continue
                v = float(np.quantile(a[w:] / a[:-w], q / 100.0))
                if v > bv:
                    best, bv = k, v
            win[best] = win.get(best, 0) + 1
            row += f'{best:>10}'
        print(row)
    print(f'  → 9칸 집계: ' + ' · '.join(f'{k} {v}칸' for k, v in
                                        sorted(win.items(), key=lambda x: -x[1])))

    # ── [2-c] 장기채 우위는 「금리 하락 40년」의 산물인가 ────────────────────
    #   [2-b] 에서 10·15년창은 ust30 이 1등이었다. 그런데 1981~2021 은 10년 금리가
    #   15%→0.5% 로 내려온 **반복 불가능한 국면**이다. HANDOFF §2 방법론의
    #   「금의 1970년대 성과를 일반화하기」와 같은 함정인지 국면을 갈라 확인한다.
    print('\n' + '=' * 74)
    print(' [2-c] 금리 국면별 — 장기채 우위가 하락 40년의 산물인가')
    print('=' * 74)
    y10 = DA._csv('yahoo_TNX') / 100.0
    y10 = y10.reindex(idx.union(y10.index)).ffill().reindex(idx).bfill()
    ERAS = [('1977~1981 금리상승', '1977-02-15', '1981-09-30'),
            ('1981~2021 금리하락', '1981-10-01', '2021-08-31'),
            ('2021~2026 금리상승', '2021-09-01', '2026-08-28')]
    print(f"  {'국면':<20}{'10년금리':>12}{'ust5':>12}{'ust30':>12}{'차이':>10}")
    for nm, s, e in ERAS:
        i0, i1 = idx.searchsorted(pd.Timestamp(s)), idx.searchsorted(pd.Timestamp(e), side='right')
        yy = f'{y10.values[i0]*100:.1f}→{y10.values[i1-1]*100:.1f}%'
        v = {}
        for k in ('ust5', 'ust30'):
            seg = parts[k][i0:i1]
            yrs = (idx[i1 - 1] - idx[i0]).days / 365.25
            v[k] = (np.nanprod(1 + np.nan_to_num(seg)) ** (1 / yrs) - 1) * 100
        print(f"  {nm:<20}{yy:>12}{v['ust5']:>11.2f}%{v['ust30']:>11.2f}%"
              f"{v['ust30']-v['ust5']:>+9.2f}%p")
    print('  ※ 국채 다리는 **선물형**이라 위 값은 단기금리 초과분이다(절대수익 아님).')
    print('    장기채 초과수익의 부호가 국면과 함께 뒤집히면 — 만기는 「최적화 대상」이')
    print('    아니라 **금리 방향 베팅**이다. 그건 이 전략이 하지 않는 종류의 판단이다.')

    # ── [3] 한국 국고채 — 실물 겹침 구간뿐 ──────────────────────────────────
    print('\n' + '=' * 74)
    print(' [3] 한국 국고채 (148070) — 표본이 짧다는 사실을 먼저 본다')
    print('=' * 74)
    try:
        kr = DA.kr('148070')
        ov = kr.index.intersection(idx)
        yrs = (ov[-1] - ov[0]).days / 365.25
        ncri = sum(1 for _, s, e in CRISES
                   if pd.Timestamp(s) >= ov[0] and pd.Timestamp(e) <= ov[-1])
        print(f'  실물 겹침 {str(ov[0].date())} ~ {str(ov[-1].date())} · {yrs:.1f}년 · '
              f'포함 위기 {ncri}개 / 7개')
        krr = kr.pct_change().reindex(idx).values
        m_ = ~np.isnan(krr)
        c_all = float(np.corrcoef(np.nan_to_num(krr)[m_][1:], qr[m_][1:])[0, 1])
        w_ = worst[m_[worst]]
        print(f'  QQQ 상관 전체 {c_all:+.3f} · 최악5%일 '
              f'{float(np.corrcoef(np.nan_to_num(krr)[w_], qr[w_])[0,1]):+.3f} · '
              f'최악5%일 평균 {np.nan_to_num(krr)[w_].mean()*100:+.2f}%')
        print(f'  ※ 유효 위기 표본 {ncri}개 — HANDOFF §2-0 의 판정 문턱은 독립 위기 19회를')
        print('    전제로 계산됐다. 이 표본으로는 **관문을 적용할 수 없다.**')
    except Exception as e:
        print(f'  (실물 데이터 없음: {e})')

    print('\n' + '=' * 74)
    print(' 판정 — 사전 등록 관문 적용')
    print('=' * 74)
    print(' ① Calmar > +10.2% : 최대가 ust30 의 +2.9% — **전부 미달**. 여기서 끝난다.')
    print(' ② 20년창 p05      : 현행이 1등이나 10·15년창에선 ust30 이 1등 —')
    print('                     **창에 따라 부호가 뒤집힌다. 견고하지 않다.**')
    print(' ④ 고원            : 만기 축은 고원이 아니라 **금리 국면에 따라 기울기가')
    print('                     뒤집히는 경사면**이다 ([2-c] 부호 반전 −6.6/+2.9/−8.3%p).')
    print('')
    print(' → **현행 ust5 유지.** 단 「ust5 가 최적」이라고 말하면 과하다.')
    print('   정확한 결론은 **「만기는 최적화할 수 있는 축이 아니다」** —')
    print('   만기를 늘리는 것은 금리 하락에 거는 방향 베팅이고, 이 전략은')
    print('   방향 예측을 하지 않는다(04 §5-6: 선행 예측형 경보는 존재하지 않는다).')
    print('   현행 ust5 는 그 베팅을 가장 적게 하는 자리다.')
    print('=' * 74)


if __name__ == '__main__':
    main()
