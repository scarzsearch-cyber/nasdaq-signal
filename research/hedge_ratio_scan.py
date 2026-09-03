# -*- coding: utf-8 -*-
"""
[실험 · 소유자 요청] QLD ↔ SCHD 배합 — 「QLD 를 최대한 많이 들고도 낙폭·변동성이 크게 좋아지는」 비율 (2026-09-03)

소유자: 「SCHD 를 공격에서의 헤지로도 써먹을 수 있을까 … 지난번 QLD60/SCHD40 의 6/4 헤지를 해 본 적은 있지만 다시 계산해 보고 싶어.
        QLD 를 최대한 많이 가져가면서도 QLD100% 와 비교해서는 기하급수적으로 낙폭이나 변동성 성과가 좋아지는 최적 비율을 찾고 싶어.」

⚠ **전략 B 는 바꾸지 않는다.** 이 파일은 측정만 한다. 채택 여부는 소유자 결정이고, 채택하려면 아래 관문을 통과해야 한다.
★ 이미 있는 것부터: **헤지6/4 는 이 저장소의 기존 선택지다**(guide.html §⑤ · `deploy/build_stats.py` HEDGE_W = lev 0.6 / div 0.4).
  같은 규약(**월 1회 재조정 · 공격 다리만 섞음 · −16/−16 규칙과 방어 40/40/20 은 그대로**)으로 비율만 10~100% 전수 스캔한다.
  guide 는 「QLD 10~90% 를 전부 돌리면 Calmar 이 50~60% 에서 최고」라고 이미 적어 두었다 — **그 문장의 재현 여부부터 확인**한다.

★ `공유용_별도전략/` 은 참고자료로 **쓸 수 없다** (CLAUDE.md §2 격리 규정): 그 폴더는 **QQQ(1배)+SCHD** 비레버리지 배합이고
  신호·방어가 없다. 자산이 다르므로 그 수치를 이 질문의 근거로 쓰지 않는다. 엔진만 같고 **여기서 새로 잰다.**

두 갈래로 잰다 (소유자 질문이 둘 다 걸쳐 있다):
  [A] **신호 없는 정적 배합** — QLD w + SCHD (1−w), 월 1회 재조정, 매수 후 보유. 기준선 = QLD 100%.
      소유자의 「QLD100% 와 비교해서」에 직접 답하는 표.
  [B] **그 배합을 B 의 공격 다리로** — −16/−16 전환 · 방어 40/40/20 그대로. 기준선 = 현행 B(공격 100% QLD).
      소유자의 「공격↔방어 스왑이 이미 리밸런싱 헤지인데 SCHD 를 더 섞으면」에 답하는 표.

창 3개로 나눠 본다 (배당 다리의 성질이 구간마다 다르므로):
  54년 1972~ (2011 이전은 French BE/ME Hi30 **대리** — §5-31 의 한계 그대로) · 21세기 2000~ (guide §⑤ 가 쓴 창) ·
  **2011-10~ 실물 SCHD 만** (짧지만 대리가 아니다).

사전 등록 관문 (04 의 기존 잣대 그대로 · 결과 보기 전에 박는다):
  ① Calmar 대비 +10.2% ② 20년창 p05 ≥ 기준선 ③ 4블록 중 3+ (Calmar). ①②③ 동시 통과만 「채택 후보」.
  ★ 다만 소유자 질문은 「이기는 규칙」이 아니라 **「낙폭을 얼마에 사는가」**다. 그래서 관문과 별도로 **한계 교환비**를 낸다 —
    QLD 를 5%p 덜 들 때마다 **MDD 몇 %p 가 줄고 CAGR 몇 %p 를 내주는가**. 「기하급수적」이 실재하면 이 비가 앞쪽에서 크고 뒤로 갈수록 작다(볼록).

예측 (결과 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 [A] 정적 배합의 Calmar 최고점은 QLD **50~60%** — guide §⑤ 문장이 재현된다.
  P2 한계 교환비는 **볼록**하다 — 처음 20~30%p 를 SCHD 로 바꿀 때 MDD 개선이 가장 크고 뒤로 갈수록 둔해진다.
  P3 [B] 신호를 얹으면 헤지의 이득이 **줄어든다** — 전환이 이미 낙폭을 자르므로 보험이 겹친다. 관문 ①은 어느 비율도 못 넘는다.
  P4 실물 SCHD 구간(2011~)의 MDD 이득은 54년 대리 구간보다 **작다**.
  P5 소유자의 시대 주장(2000~2007 · 2022 · 2025 SCHD 우세)은 맞고 **2008 은 반대**다(§5-31 에서 DVY −59.9% 로 이미 확인).

실행: python research/hedge_ratio_scan.py   (약 40초 · 네트워크 0 · 파일 쓰기 0)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))
_sys.path.insert(0, _os.path.join(_ROOT, 'deploy'))

import sys
import io
import contextlib
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                   # noqa: E402
import hist_defasset as DA                                # noqa: E402
import reentry_lib as RL                                  # noqa: E402
import hist_defensive as DF                               # noqa: E402
from build_stats import STRATS, defensive_r               # noqa: E402

L = '=' * 118
WS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
WINDOWS = [('ext', '54년 1972~', '1900-01-01', '⚠ 2011 이전 배당은 대리(French BE/ME Hi30)'),
           ('us2000', '21세기 2000~', '2000-01-01', '⚠ 2011 이전 배당은 대리 · guide §⑤ 가 쓴 창'),
           ('us2000', '실물 2011-10~', '2011-10-20', '✔ SCHD 실물 구간만')]


def metrics(c, idx):
    m = EC.fullmet(np.asarray(c, float), idx=idx)
    r = np.diff(np.asarray(c, float), prepend=1.0) / np.concatenate(([1.0], np.asarray(c, float)[:-1]))
    r[0] = 0.0
    m['vol'] = float(np.std(r, ddof=1) * np.sqrt(252) * 100)
    m['p05_20'] = EC.p05_20y(np.asarray(c, float))
    s = pd.Series(np.asarray(c, float), index=idx)
    m['worst1y'] = float((s / s.shift(252) - 1).min() * 100) if len(s) > 252 else np.nan
    m['worst3y'] = float((s / s.shift(756) - 1).min() * 100) if len(s) > 756 else np.nan
    return m


def blocks_calmar(c, idx, nb=4):
    c = np.asarray(c, float)
    e = np.linspace(0, len(c), nb + 1).astype(int)
    return [EC.fullmet(c[a:b] / c[a], idx=idx[a:b])['calmar'] for a, b in zip(e[:-1], e[1:])]


def table(title, rows, base_key, note):
    print('\n' + L); print(title + '   ' + note); print(L)
    b = rows[base_key]
    print(f"  {'QLD':>5}{'최종배수':>13}{'CAGR':>8}{'변동성':>8}{'MDD':>8}{'Calmar':>8}{'Sortino':>9}"
          f"{'20y p05':>9}{'최악1년':>8}{'최악3년':>8}{'ΔCalmar':>9}{'Δp05':>8}{'블록':>5}  관문")
    for w in WS:
        m = rows[w]['m']; bl = rows[w]['bl']
        wins = sum(1 for x, y in zip(bl, b['bl']) if x > y)
        d1 = m['calmar'] / b['m']['calmar'] - 1
        dp = m['p05_20'] / b['m']['p05_20'] - 1 if not np.isnan(m['p05_20']) and not np.isnan(b['m']['p05_20']) else np.nan
        g = (d1 > 0.102, (not np.isnan(dp)) and dp >= 0, wins >= 3)
        tag = '★①②③' if all(g) else ('①' if g[0] else '-') + ('②' if g[1] else '-') + ('③' if g[2] else '-')
        print(f"  {w*100:>4.0f}%{m['final']:>13,.1f}{m['cagr']:>7.2f}%{m['vol']:>7.1f}%{m['mdd']:>7.1f}%{m['calmar']:>8.3f}"
              f"{m['sortino']:>9.3f}{m['p05_20']:>8.1f}배{m['worst1y']:>7.1f}%{m['worst3y']:>7.1f}%"
              f"{d1:>+8.1%}{(dp if not np.isnan(dp) else 0):>+7.1%}{wins:>4}/4  {tag}")
    print(f'\n  한계 교환비 — QLD 를 10%p 덜 들 때마다 (직전 행 대비):')
    print(f"  {'구간':>12}{'ΔMDD':>9}{'ΔCAGR':>9}{'Δ변동성':>9}   MDD 1%p 를 사는 데 드는 CAGR")
    prev = None
    for w in WS:
        m = rows[w]['m']
        if prev is not None:
            dmdd = m['mdd'] - prev['mdd']; dcagr = m['cagr'] - prev['cagr']; dvol = m['vol'] - prev['vol']
            price = (-dcagr / dmdd) if dmdd > 0.01 else np.nan
            print(f"  {f'{prev_w*100:.0f}→{w*100:.0f}%':>12}{dmdd:>+8.1f}%{dcagr:>+8.2f}%{dvol:>+8.1f}%"
                  f"   {(f'{price:.2f}%p' if not np.isnan(price) else '개선 없음'):>12}")
        prev, prev_w = m, w


def zoom(DS):
    """[소유자 질문 2026-09-03] 「QLD 80/SCHD 20 이나 90/10 정도만 해도 변동성이 유의미하게 달라지나?」
    54년 터미널 배수는 0.94%p 의 CAGR 차이를 54제곱으로 부풀린다 — 소유자 지평은 3~20년이다(memory: horizon-3-20y-frame).
    그래서 **지평 창 분포**(10년·20년 중앙/최악5%)와 **체감 지표**(큰 하락일 수·최악 1년)로 다시 낸다."""
    print('\n' + L)
    print('D. 소유자 질문 — 「10% · 20% 만 섞어도 유의미한가」 (지평 3~20년 기준으로 다시 봄)')
    print(L)
    for dkey, wname in (('ext', '54년 1972~'), ('us2000', '21세기 2000~')):
        D = DS[dkey]; idx = pd.DatetimeIndex(D['idx'])
        qldr = np.asarray(D['qldr'], float); divr = np.asarray(D['schdr'], float)
        defr = np.asarray(defensive_r(idx, divr, 'mix'), float)
        print(f'\n  ── {wname} · B(−16/−16 · 방어 40/40/20)의 공격 다리만 섞음 ──')
        print(f"  {'QLD':>5}{'연변동성':>10}{'vs100':>8}{'MDD':>8}{'최악1년':>9}{'−3%일/년':>10}"
              f"{'10년 중앙':>10}{'10년 최악5%':>12}{'20년 중앙':>10}{'20년 최악5%':>12}")
        base = None
        for w in (1.0, 0.9, 0.8, 0.7):
            att = np.asarray(DA.mix_monthly_parts(idx, {'lev': w, 'div': 1 - w},
                                                  {'lev': qldr, 'div': divr}), float)
            Dx = dict(D); Dx['qldr'] = att; Dx['schdr'] = defr
            with contextlib.redirect_stdout(io.StringIO()):
                c, _, _ = RL.run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
            c = np.asarray(c, float); s = pd.Series(c, index=idx)
            r = pd.Series(c, index=idx).pct_change()
            vol = float(r.std(ddof=1) * np.sqrt(252) * 100)
            m = EC.fullmet(c, idx=idx)
            w1 = float((s / s.shift(252) - 1).min() * 100)
            big = float((r <= -0.03).sum() / ((idx[-1] - idx[0]).days / 365.25))
            row = f'  {w*100:>4.0f}%{vol:>9.1f}%'
            row += f'{(vol/base-1)*100:>+7.1f}%' if base else f"{'기준':>8}"
            if base is None:
                base = vol
            out = [row, f"{m['mdd']:>7.1f}%", f'{w1:>8.1f}%', f'{big:>9.1f}회']
            for win in (2520, 5040):
                q = (s / s.shift(win)).dropna()
                out.append(f'{q.median():>9.1f}배' if len(q) else f"{'—':>10}")
                out.append(f'{q.quantile(0.05):>11.1f}배' if len(q) else f"{'—':>12}")
            print(''.join(out))
    print('\n  ※ 「−3%일/년」은 하루 −3% 넘게 빠진 날이 1년에 몇 번인가 — 변동성 숫자보다 체감에 가깝다.')
    print('  ※ 10년·20년 열은 **모든 시작일**의 창 분포다(중첩). 비중첩 창 수는 54년에 각각 5.4개·2.7개뿐 — 최악5% 는 참고치다.')


def main():
    print(L); print('QLD ↔ SCHD 배합 스캔 — 소유자 요청 (전략 B 무변경 · 측정만)'); print(L)
    with contextlib.redirect_stdout(io.StringIO()):
        DS = {'us2000': dict(RL.build()), 'ext': dict(DF.build('chain'))}
    for k, v in DS.items():
        ix = pd.DatetimeIndex(v['idx'])
        print(f'  엔진 [{k}]: {ix[0].date()} ~ {ix[-1].date()} ({len(ix)}행)')
    print('  규약: 월 1회 재조정 (deploy/build_stats.HEDGE_W 와 같은 mix_monthly_parts) · 방어 40/40/20 고정 · 전환 규칙 −16/−16 고정')
    print('  검산: [B] 21세기 QLD100% 가 공표 167.3배·21.2%·−48.4% 와, QLD60% 가 guide §⑤ 의 63배·16.8%·−38.5% 와 일치해야 한다.')

    for dkey, wname, wstart, note in WINDOWS:
        D = DS[dkey]
        idx = pd.DatetimeIndex(D['idx'])
        qldr = np.asarray(D['qldr'], float); divr = np.asarray(D['schdr'], float)
        m0 = idx >= pd.Timestamp(wstart)
        ix = idx[m0]
        if len(ix) < 800:
            continue
        rowsA, rowsB = {}, {}
        for w in WS:
            att = np.asarray(DA.mix_monthly_parts(idx, {'lev': w, 'div': 1 - w},
                                                  {'lev': qldr, 'div': divr}), float)
            # [A] 신호 없는 정적 배합
            cA = np.cumprod(1 + np.nan_to_num(att[m0]))
            rowsA[w] = dict(m=metrics(cA, ix), bl=blocks_calmar(cA, ix))
            # [B] 그 배합을 공격 다리로 — 규칙·방어 그대로
            Dx = dict(D); Dx['qldr'] = att
            Dx['schdr'] = np.asarray(defensive_r(idx, divr, 'mix'), float)
            with contextlib.redirect_stdout(io.StringIO()):
                c, _, _ = RL.run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
            c = np.asarray(c, float)[m0]
            c = c / c[0]
            rowsB[w] = dict(m=metrics(c, ix), bl=blocks_calmar(c, ix))
        table(f'[A] 신호 없는 정적 배합 — {wname}  (기준선 = QLD 100%)', rowsA, 1.0, note)
        table(f'[B] 그 배합을 B 의 공격 다리로 (−16/−16 · 방어 40/40/20) — {wname}  (기준선 = 현행 B)', rowsB, 1.0, note)

    # ── 소유자의 시대 주장 확인 ───────────────────────────────────────────────
    print('\n' + L); print('C. 소유자 주장 확인 — 「2022 · 2008 · 닷컴 이후 2007 까지 · 올해도 SCHD 강세」'); print(L)

    def px(sym, root=False):
        p = f'{sym}_us_d.csv' if root else f'data/hist/yahoo_{sym}.csv'
        d = pd.read_csv(p); c = 'Date' if 'Date' in d.columns else d.columns[0]
        d[c] = pd.to_datetime(d[c])
        return d.set_index(c)['Close'].astype(float).sort_index()
    qqq, schd, dvy = px('QQQ'), px('SCHD'), px('DVY')
    per = [('닷컴 이후 2002-10 ~ 2007-10', '2002-10-09', '2007-10-31'),
           ('금융위기 2007-10 ~ 2009-03', '2007-10-31', '2009-03-09'),
           ('2022 인플레 2021-11 ~ 2022-10', '2021-11-19', '2022-10-14'),
           ('올해 2026-01 ~', '2026-01-02', '2026-12-31'),
           ('2025 전체', '2025-01-02', '2025-12-31')]
    print(f"  {'구간':<30}{'QQQ':>10}{'SCHD':>10}{'DVY':>10}   승자")
    for nm, a, b in per:
        vals = []
        for s in (qqq, schd, dvy):
            seg = s[(s.index >= a) & (s.index <= b)]
            vals.append((seg.iloc[-1] / seg.iloc[0] - 1) * 100 if len(seg) > 2 else np.nan)
        cand = [('QQQ', vals[0]), ('SCHD', vals[1]), ('DVY', vals[2])]
        ok = [(n, v) for n, v in cand if not np.isnan(v)]
        win = max(ok, key=lambda t: t[1])[0] if ok else '—'
        print(f'  {nm:<30}' + ''.join((f'{v:>9.1f}%' if not np.isnan(v) else f'{"—":>10}') for v in vals) + f'   {win}')
    print('  ※ SCHD 는 2011-10 상장이라 닷컴·금융위기 열은 비어 있다 — 그 시절 같은 유형의 실물은 DVY 다(§5-31).')
    print('')
    print('  「닷컴 이후 2007 까지」는 **시작점을 어디로 잡느냐**로 답이 뒤집힌다 (엔진 배당 체인 = 그 시절 대리):')
    ext = DS['ext']; eix = pd.DatetimeIndex(ext['idx'])
    px1 = pd.Series(np.asarray(ext['px'], float), index=eix)
    dchain = pd.Series(np.cumprod(1 + np.nan_to_num(np.asarray(ext['schdr'], float))), index=eix)
    for nm, a, b in (('닷컴 고점 2000-03-27 → 2007-10-31', '2000-03-27', '2007-10-31'),
                     ('닷컴 저점 2002-10-09 → 2007-10-31', '2002-10-09', '2007-10-31'),
                     ('2000-01-03 → 2007-10-31', '2000-01-03', '2007-10-31')):
        sa = px1[(px1.index >= a) & (px1.index <= b)]; da = dchain[(dchain.index >= a) & (dchain.index <= b)]
        print(f'    {nm:<34} 나스닥1배 {(sa.iloc[-1]/sa.iloc[0]-1)*100:>+7.1f}%   배당(대리) {(da.iloc[-1]/da.iloc[0]-1)*100:>+7.1f}%   '
              f'→ {"배당 승" if da.iloc[-1]/da.iloc[0] > sa.iloc[-1]/sa.iloc[0] else "나스닥 승"}')

    zoom(DS)

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a [A] 와 [B] 의 최적 비율이 다르면, 그것은 「전환이 이미 하는 일을 배합이 또 하는가」의 답이다 — 표에서 직접 읽는다.')
    print('  Q-b 배합은 세금·거래를 늘린다(월 1회 재조정 = 연 12회 매매). 04 §5-8 손익분기 편도 2.5% 와 대조할 것 — 이 파일은 비용 0 가정이다.')


if __name__ == '__main__':
    main()
