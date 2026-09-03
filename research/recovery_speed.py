# -*- coding: utf-8 -*-
"""
[가설 검증] 「나스닥은 최근으로 올수록 큰 하락 이후 회복이 빨라졌다」 — 소유자 가설 (2026-09-03)

소유자: 「나는 최근으로 올수록 폭락장에 대한 회복이 빨라졌다고 느껴. 물론 이건 폭락의 성질이 다를 수 있다고도 생각해.」
(외부 AI 가 짜 준 프롬프트 §1·§2 의 검증 부분. 전략 설계 부분은 04 무덤과 대조 — 이 파일은 **가설만** 잰다.)

⚠ 이 파일은 전략을 바꾸지 않는다. 규칙·문턱·비중 무접촉. 후보를 만들지 않는다.

무엇을 재나 (정의는 결과 전에 고정):
  사건 = 사상 최고가(러닝 ATH) 아래로 내려간 뒤 **다시 사상 최고가를 회복할 때까지**의 한 구간.
    깊이 = 그 구간의 최저 낙폭 · 저점일 · 고점→저점 일수 · **저점→회복 일수** · 회복 중 되밀림(중간 고점 대비 최대 낙폭).
  등급 = 깊이 ≤ −10 / −20 / −30 / −40 / −50%.
  시대 = **고점일** 기준 1970~89 · 1990~99 · 2000~09 · 2010~19 · 2020~ (저점일 기준은 감도로 따로).
  계열 = 엔진 px(나스닥 체인 1972~, Composite→NDX) · 대조 S&P500 · 실질(CPI 로 디플레이트).

반증 배터리 (사전 등록 — 가설을 지지하는 계산보다 **먼저** 적는다):
  F1 **창 절단(censoring)**: 2020년대 창은 6.7년뿐이다. 회복이 그보다 오래 걸리는 사건은 **관측 자체가 불가능**하다.
     과거 사건들을 「2020년에 시작했다면 오늘까지 회복이 보였겠나」로 다시 물어 몇 개가 안 보이는지 센다.
  F2 **깊이 통제** (§-1 ⑧): 최근 하락이 얕았다면 「시대」가 아니라 「깊이」가 원인이다. 같은 깊이 등급 안에서 시대를 비교한다.
  F3 **코로나 제외**: 2020 을 빼면 2020년대 표본에 무엇이 남나.
  F4 **표본 수**: 시대당 독립 사건 수 · 등급별 사건 수. 3개 미만이면 「시대 경향」을 말할 수 없다.
  F5 **순열 검정**: 고점연도 ↔ 회복일수의 Spearman 상관이 시대 라벨을 섞었을 때 얼마나 자주 나오나(10,000회).
  F6 **실질 기준**: CPI 로 디플레이트한 계열에서 같은 사건들의 회복일. 「체감 회복」은 명목이 아니다.
  F7 **다른 지수**: S&P500 에서도 같은 방향인가. 나스닥에만 있으면 「지수 구성 변화」 설명이 살아난다.
  F8 **B 에 무슨 뜻인가**: 사건마다 B vs 2배 계속보유. 빠른 회복이 늘면 B 에 유리한가 불리한가.

예측 (결과 보기 전 · 틀리면 그대로 적는다 §-1 ⑦):
  P1 명목·전고점 기준으로는 「빨라졌다」가 참으로 보인다 — 2020년대 중앙 회복일 < 2000년대 중앙.
  P2 그러나 F1 이 그것을 삼킨다 — 과거 ≥−20% 사건의 **3개 이상**이 2020년대 창에서는 「아직 회복 안 됨」으로 안 보인다.
  P3 F2 깊이 통제 후 시대 중앙 차이는 2배 미만으로 줄어든다.
  P4 F3 코로나를 빼면 2020년대 ≥−20% 사건은 **1개(2022)** 만 남는다.
  P5 F6 실질 기준에서 1970년대가 가장 나쁘고, 2022 도 명목보다 뚜렷이 길어진다.
  P6 F7 S&P500 에서도 같은 방향이 보인다(즉 나스닥 구성 변화만으로는 설명이 안 된다).
  P7 F8 B 는 **빠른 회복 사건에서 2배 보유에 지고** 느리고 깊은 사건에서 이긴다(§5-26 「빠른 급락 4/4」 재확인).

판정 규칙 (사전 — 「실패하면 무엇이 참? 통과하면 무엇이 참?」 §-1 ⑤):
  **참**   : 깊이를 통제해도 시대 중앙 회복일이 단조 감소 + 순열 p < 0.05 + 코로나 제외해도 유지.
  **판단 불가**: 방향은 맞으나 p ≥ 0.05 이거나 시대당 사건 < 3 이거나 F1 절단이 차이를 설명할 수 있을 때.
  **거짓** : 방향이 반대.
  ※ 「참」이 나와도 **전략은 안 바꾼다** — 가설이 참이면 그것은 B 에 **불리한** 정보이고(F8), 그 불리함의 대가는 이미
     04 §5-26·§5-8 에 측정돼 있으며 대안(분할매수·딥매수·필터)은 전부 더 나빴다(04 §1~§5). 이 파일은 사실 확인만 한다.

실행: python research/recovery_speed.py   (약 10초 · 네트워크 0 · 파일 쓰기 0)
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import io
import contextlib
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import eng_common as EC                                  # noqa: E402

L = '=' * 108
ERAS = [(1970, 1989, '1970~89'), (1990, 1999, '1990~99'), (2000, 2009, '2000~09'),
        (2010, 2019, '2010~19'), (2020, 2099, '2020~')]


def era_of(ts):
    for a, b, nm in ERAS:
        if a <= ts.year <= b:
            return nm
    return '?'


def episodes(s, min_depth=-0.10):
    """사상 최고가 아래로 내려갔다가 새 최고가를 회복할 때까지를 한 사건으로. 깊이 ≤ min_depth 인 것만."""
    v = s.values.astype(float); ix = s.index
    ath = np.maximum.accumulate(v)
    below = v < ath
    out = []
    i = 0
    n = len(v)
    while i < n:
        if not below[i]:
            i += 1; continue
        j = i
        while j < n and below[j]:
            j += 1
        seg = v[i:j]
        k = int(np.argmin(seg))
        depth = seg[k] / ath[i] - 1
        if depth <= min_depth:
            peak_i = i - 1 if i > 0 else 0
            trough = ix[i + k]
            recovered = j < n
            rec_end = ix[j] if recovered else ix[-1]
            # 회복 중 되밀림: 저점 이후 회복까지의 중간 고점 대비 최대 낙폭
            tail = seg[k:]
            rb = float(np.min(tail / np.maximum.accumulate(tail) - 1)) if len(tail) > 1 else 0.0
            out.append(dict(peak=ix[peak_i], trough=trough, end=rec_end, recovered=recovered,
                            depth=depth * 100,
                            fall_d=(trough - ix[peak_i]).days,
                            rec_d=(rec_end - trough).days,
                            rebound_dd=rb * 100,
                            era=era_of(ix[peak_i]), era_trough=era_of(trough)))
        i = j
    return pd.DataFrame(out)


def swings(s, T=0.20):
    """[D2 · 국지 고점 기준] 지그재그 — 고점에서 T 이상 떨어지면 그 고점을 확정하고, 저점에서 T 이상 오르면 저점을 확정.
    회복 = 저점 이후 **그 국지 고점 수준**을 되찾은 첫날. D1(사상 최고가)은 2000 고점을 2015 에야 회복하므로
    **2008 위기가 그 안에 통째로 숨는다** — 그래서 이 정의를 더한다.
    ⚠ 이 정의는 결과를 본 뒤에 **추가**했다(§-1: 사후 측정 변경 주의). 방향은 명시한다 — D2 는 2007 고점(느린 회복)을
    2000년대에 하나 더 넣으므로 **소유자 가설(최근일수록 빠름)에 유리한 쪽**이다. 판정을 지키려고 넣은 것이 아니다."""
    v = s.values.astype(float); ix = s.index
    n = len(v)
    piv = []                                   # (종류, 위치)
    mode = 'up'; ext = 0
    for i in range(1, n):
        if mode == 'up':
            if v[i] >= v[ext]:
                ext = i
            elif v[i] <= v[ext] * (1 - T):
                piv.append(('P', ext)); mode = 'down'; ext = i
        else:
            if v[i] <= v[ext]:
                ext = i
            elif v[i] >= v[ext] * (1 + T):
                piv.append(('T', ext)); mode = 'up'; ext = i
    out = []
    for a in range(len(piv) - 1):
        if piv[a][0] != 'P' or piv[a + 1][0] != 'T':
            continue
        pi, ti = piv[a][1], piv[a + 1][1]
        depth = v[ti] / v[pi] - 1
        back = np.where(v[ti:] >= v[pi])[0]
        recovered = len(back) > 0
        end = ix[ti + back[0]] if recovered else ix[-1]
        tail = v[ti:(ti + back[0] + 1)] if recovered else v[ti:]
        rb = float(np.min(tail / np.maximum.accumulate(tail) - 1)) if len(tail) > 1 else 0.0
        out.append(dict(peak=ix[pi], trough=ix[ti], end=end, recovered=recovered, depth=depth * 100,
                        fall_d=(ix[ti] - ix[pi]).days, rec_d=(end - ix[ti]).days, rebound_dd=rb * 100,
                        era=era_of(ix[pi]), era_trough=era_of(ix[ti])))
    return pd.DataFrame(out)


def cluster(df):
    """겹치는 사건을 하나로 — 긴 약세장은 지그재그가 여러 쌍을 만들지만 **독립 사건은 하나**다(2000~02 닷컴 6쌍 = 1건).
    묶음의 고점 = 첫 고점 · 저점 = 가장 깊은 저점 · 회복 = 그 첫 고점 수준을 되찾은 날."""
    d = df.sort_values('peak').reset_index(drop=True)
    out = []
    cur = None
    for r in d.itertuples():
        if cur is None or r.peak > cur['end']:
            if cur:
                out.append(cur)
            cur = dict(peak=r.peak, trough=r.trough, end=r.end, recovered=r.recovered, depth=r.depth,
                       fall_d=r.fall_d, rec_d=r.rec_d, rebound_dd=r.rebound_dd, era=r.era, era_trough=r.era_trough, n=1)
        else:
            cur['n'] += 1
            if r.depth < cur['depth']:
                cur['depth'] = r.depth; cur['trough'] = r.trough
            if r.end > cur['end']:
                cur['end'] = r.end; cur['recovered'] = r.recovered
            cur['fall_d'] = (cur['trough'] - cur['peak']).days
            cur['rec_d'] = (cur['end'] - cur['trough']).days
            cur['era_trough'] = era_of(cur['trough'])
    if cur:
        out.append(cur)
    return pd.DataFrame(out)


def era_table(df, label, col='rec_d'):
    print(f'\n  {label}')
    print(f"    {'시대':<9}{'사건':>4}{'중앙':>8}{'최소':>8}{'최대':>8}{'평균':>8}   깊이 중앙   미회복")
    for _, _, nm in ERAS:
        d = df[df.era == nm]
        if not len(d):
            print(f'    {nm:<9}{0:>4}       —'); continue
        r = d[d.recovered]
        med = f'{r.rec_d.median():.0f}일' if len(r) else '—'
        mn = f'{r.rec_d.min():.0f}' if len(r) else '—'
        mx = f'{r.rec_d.max():.0f}' if len(r) else '—'
        av = f'{r.rec_d.mean():.0f}' if len(r) else '—'
        print(f'    {nm:<9}{len(d):>4}{med:>8}{mn:>8}{mx:>8}{av:>8}   {d.depth.median():>7.1f}%   {int((~d.recovered).sum())}')


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        G, _ = EC.selfcheck()
    IDX = pd.DatetimeIndex(G.idx)
    PX = pd.Series(G.D['px'], index=IDX).astype(float)
    print(L); print('가설 검증 — 「최근일수록 폭락 후 회복이 빨라졌다」 (나스닥 체인 1972~2026 · 전략 무접촉)'); print(L)
    print(f'  계열: {IDX[0].date()} ~ {IDX[-1].date()} ({(IDX[-1]-IDX[0]).days/365.25:.1f}년) · 사건 정의: 사상 최고가 → 회복까지 · 시대는 고점일 기준')

    ep = episodes(PX, -0.10)
    print(f'\n[사건 목록] 깊이 ≤ −10% : {len(ep)}건')
    print(f"  {'고점':<12}{'저점':<12}{'회복':<12}{'깊이':>8}{'하락일':>7}{'회복일':>7}{'되밀림':>8}  시대")
    for r in ep.itertuples():
        rec = r.end.date() if r.recovered else '미회복'
        print(f'  {str(r.peak.date()):<12}{str(r.trough.date()):<12}{str(rec):<12}{r.depth:>7.1f}%{r.fall_d:>7}{r.rec_d:>7}{r.rebound_dd:>7.1f}%  {r.era}')

    for th, nm in ((-10, '≤ −10%'), (-20, '≤ −20%'), (-30, '≤ −30%'), (-40, '≤ −40%'), (-50, '≤ −50%')):
        d = ep[ep.depth <= th]
        if len(d):
            era_table(d, f'[등급 {nm}] {len(d)}건 — 저점→전고점 회복일(달력일)')

    # ── D2 국지 고점 기준 ─────────────────────────────────────────────────────
    print('\n' + L); print('[D2] 국지 고점 기준(지그재그 20%) — D1 은 2000 고점 회복이 2015 라 **2008 위기가 그 안에 숨는다**'); print(L)
    sw = swings(PX, 0.20)
    print(f"  {'고점':<12}{'저점':<12}{'회복':<12}{'깊이':>8}{'하락일':>7}{'회복일':>7}{'되밀림':>8}  시대")
    for r in sw.itertuples():
        print(f'  {str(r.peak.date()):<12}{str(r.trough.date()):<12}{str(r.end.date() if r.recovered else "미회복"):<12}'
              f'{r.depth:>7.1f}%{r.fall_d:>7}{r.rec_d:>7}{r.rebound_dd:>7.1f}%  {r.era}')
    era_table(sw, f'[D2] 하락 사건 {len(sw)}건 — 저점→그 국지 고점 회복일 (고점일 기준 시대) ⚠ 아래 D3 대로 겹침이 있다')
    CL = cluster(sw)
    print('\n' + L); print('[D3 · 판정용] 겹치는 사건을 묶은 **독립 사건** — 긴 약세장이 여러 건으로 세어지는 것을 막는다'); print(L)
    print(f"  {'고점':<12}{'저점':<12}{'회복':<12}{'깊이':>8}{'하락일':>7}{'회복일':>7}{'되밀림':>8}{'묶인쌍':>6}  시대")
    for r in CL.itertuples():
        print(f'  {str(r.peak.date()):<12}{str(r.trough.date()):<12}{str(r.end.date() if r.recovered else "미회복"):<12}'
              f'{r.depth:>7.1f}%{r.fall_d:>7}{r.rec_d:>7}{r.rebound_dd:>7.1f}%{r.n:>6}  {r.era}')
    era_table(CL, f'[D3] 독립 사건 {len(CL)}건 — 저점→고점 회복일 (고점일 기준)')
    print('  [감도] 같은 사건을 **저점일** 기준 시대로:')
    era_table(CL.assign(era=CL.era_trough), '(저점일 기준)')

    E20 = ep[ep.depth <= -20]
    # ── F1 창 절단 ────────────────────────────────────────────────────────────
    print('\n' + L); print('[F1] 창 절단 — 2020년대 창에서는 애초에 관측 불가능한 회복이 있다'); print(L)
    win = (IDX[-1] - pd.Timestamp('2020-01-01')).days
    print(f'  2020년대 창 길이: 오늘({IDX[-1].date()}) − 2020-01-01 = {win}일 ({win/365.25:.1f}년)')
    for lbl, dd in (('D1 사상최고가', E20), ('D3 독립사건', CL)):
        rr_ = dd[dd.recovered]
        inv_ = rr_[rr_.fall_d + rr_.rec_d > win]
        print(f'  [{lbl}] ≥−20% 사건 {len(rr_)}건 중 **고점→회복이 {win}일을 넘는 것 {len(inv_)}건** — 2020년에 시작했다면 오늘까지 「미회복」으로 보였을 사건:')
        for r in inv_.itertuples():
            print(f'    {r.peak.date()} 고점 {r.depth:.1f}% → 회복까지 {r.fall_d + r.rec_d}일 ({(r.fall_d+r.rec_d)/365.25:.1f}년)')
        if not len(inv_):
            print('    (없음)')
    inv = E20[E20.recovered & (E20.fall_d + E20.rec_d > win)]
    print('  → 2020년대의 「빠른 회복」 표본은 **느린 회복이 물리적으로 들어올 수 없는 창**에서 뽑힌 것이다(생존 편향의 시간판).')

    # ── F2 깊이 통제 ──────────────────────────────────────────────────────────
    print('\n' + L); print('[F2] 깊이 통제 — 「최근 하락이 얕아서」가 아닌가 (§-1 ⑧: 시대와 깊이를 같이 바꾸면 인과를 말할 수 없다)'); print(L)
    bins = [(-100, -40, '≤−40%'), (-40, -30, '−40~−30%'), (-30, -20, '−30~−20%'), (-20, -10, '−20~−10%')]
    print(f"    {'깊이대':<12}" + ''.join(f'{nm:>12}' for _, _, nm in ERAS))
    for lo, hi, bn in bins:
        d = CL[(CL.depth > lo) & (CL.depth <= hi) & CL.recovered]
        row = f'    {bn:<12}'
        for _, _, nm in ERAS:
            x = d[d.era == nm]
            row += f'{(f"{x.rec_d.median():.0f}일(n{len(x)})" if len(x) else "—"):>12}'
        print(row)
    r20 = E20[E20.recovered]
    cl_r = CL[CL.recovered]
    cc = np.corrcoef(cl_r.depth.values, cl_r.rec_d.values)[0, 1]
    print(f'  [D3] 깊이와 회복일의 상관: {cc:+.2f} (깊을수록 오래 걸리면 음수) · 독립 사건 {len(cl_r)}건 — 깊이가 회복일을 설명하는 정도')

    # ── F3 코로나 제외 ────────────────────────────────────────────────────────
    print('\n' + L); print('[F3] 코로나 제외 — 2020년대 주장이 몇 개 사건에 기대고 있나'); print(L)
    r2020 = CL[(CL.era == '2020~')]
    print(f'  2020년대 독립 사건 전부({len(r2020)}건): ' + ' · '.join(f'{r.peak.date()} {r.depth:.1f}% 회복 {r.rec_d}일' for r in r2020.itertuples()))
    nc = r2020[(r2020.depth <= -20) & (r2020.trough.dt.year != 2020)]
    print(f'  코로나(2020 저점) 제외 · ≥−20%: **{len(nc)}건** — ' + (' · '.join(f'{r.peak.date()} {r.depth:.1f}% 회복 {r.rec_d}일' for r in nc.itertuples()) if len(nc) else '없음'))

    # ── F4 표본 수 ────────────────────────────────────────────────────────────
    print('\n' + L); print('[F4] 표본 수 — 「시대 경향」을 말할 재료가 있나'); print(L)
    for _, _, nm in ERAS:
        a = ep[(ep.era == nm)]; b = a[a.depth <= -20]; c = a[a.depth <= -30]
        d3 = CL[CL.era == nm]
        print(f'  {nm:<9} [D1] ≤−10%: {len(a):>2}건 · ≤−20%: {len(b):>2}건 · ≤−30%: {len(c):>2}건   |   [D3 독립사건] {len(d3):>2}건 (≤−30%: {int((d3.depth <= -30).sum())}건)')
    print('  → 시대당 ≥−20% 사건이 3개 미만인 시대가 있으면 그 시대의 「중앙값」은 사실상 사건 1~2개다.')

    # ── F5 순열 검정 ──────────────────────────────────────────────────────────
    print('\n' + L); print('[F5] 순열 검정 — 「연도 ↔ 회복일」 관계가 우연으로도 나오나 (10,000회)'); print(L)
    def spear(a, b):
        ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
        return float(np.corrcoef(ra, rb)[0, 1])

    def perm(d, lbl):
        yy = d.peak.dt.year.values.astype(float); rr = d.rec_d.values.astype(float)
        obs = spear(yy, rr)
        rng = np.random.default_rng(7)
        null = np.array([spear(yy, rng.permutation(rr)) for _ in range(10000)])
        p = float(np.mean(null <= obs))
        print(f'  [{lbl}] Spearman(고점연도, 회복일) = {obs:+.3f} (음수면 「최근일수록 빠름」) · n={len(rr)} · p = {p:.3f} → '
              f'{"유의(<0.05)" if p < 0.05 else "**유의하지 않음**"}')
        return p
    p_one = perm(r20, 'D1 사상최고가 ≥−20%')
    p_d2 = perm(CL[CL.recovered], 'D3 독립사건')

    # ── F6 실질 기준 ──────────────────────────────────────────────────────────
    print('\n' + L); print('[F6] 실질(CPI 디플레이트) 기준 — 「체감 회복」'); print(L)
    cpi = pd.read_csv('data/hist/datahub_cpi_us.csv')
    cpi['Date'] = pd.to_datetime(cpi['Date'])
    ci = cpi.set_index('Date')['Index'].reindex(IDX, method='ffill').astype(float)
    ok = ci.notna()
    real = (PX[ok] / ci[ok]) * float(ci[ok].iloc[-1])
    print('  같은 사건(D2 국지고점)에서 **그 고점의 구매력**을 되찾은 날까지 — 명목 회복일 vs 실질 회복일')
    print(f"  {'고점':<12}{'깊이':>8}{'명목 회복':>10}{'실질 회복':>12}{'실질−명목':>10}  시대")
    rows = []
    for r in CL.itertuples():
        lvl = float(real.loc[r.peak]) if r.peak in real.index else np.nan
        after = real[real.index >= r.trough]
        hit = after[after >= lvl]
        rd = int((hit.index[0] - r.trough).days) if len(hit) else None
        rows.append((r.era, rd))
        print(f'  {str(r.peak.date()):<12}{r.depth:>7.1f}%{r.rec_d:>10}{(str(rd) if rd is not None else "미회복"):>12}'
              f'{(str(rd - r.rec_d) if rd is not None else "—"):>10}  {r.era}')
    for _, _, nm in ERAS:
        g = [x for e, x in rows if e == nm and x is not None]
        if g:
            print(f'    {nm}: 실질 회복일 중앙 {np.median(g):.0f}일 (n{len(g)})')

    # ── F7 S&P 대조 ───────────────────────────────────────────────────────────
    print('\n' + L); print('[F7] S&P500 대조 — 나스닥 구성 변화만으로 설명되나'); print(L)
    sp = pd.read_csv('data/hist/yahoo_GSPC.csv'); sp['Date'] = pd.to_datetime(sp['Date'])
    sps = sp.set_index('Date')['Close'].astype(float).sort_index()
    ep_s = episodes(sps, -0.10)
    era_table(ep_s[ep_s.depth <= -20], f'S&P500 ≥−20% {len(ep_s[ep_s.depth <= -20])}건')

    # ── F8 B 에 무슨 뜻인가 ───────────────────────────────────────────────────
    print('\n' + L); print('[F8] 사건마다 B vs 2배 계속보유 — 빠른 회복은 B 에 유리한가'); print(L)
    QLDR = np.nan_to_num(np.asarray(G.D['qldr'], float)); MIX = np.nan_to_num(np.asarray(G.Dm['schdr'], float))
    wB = EC.rule_dd(PX, -0.16, -0.16)
    cB = pd.Series(np.asarray(EC.sim2(wB, QLDR, MIX), float), index=IDX)
    c2 = pd.Series(np.cumprod(1 + QLDR), index=IDX)
    print('  (고점→회복 구간의 배수. 컷을 손으로 고르지 않으려고 순위상관도 같이 낸다 §-1 ⓑ)')
    print(f"  {'고점':<12}{'깊이':>8}{'회복일':>7}{'B':>9}{'2배보유':>9}{'B/2배':>8}")
    recs, rels = [], []
    for r in CL.itertuples():
        a, b = r.peak, r.end
        if a not in cB.index or b not in cB.index:
            continue
        rb = cB[b] / cB[a]; r2 = c2[b] / c2[a]; rel = rb / r2
        recs.append(r.rec_d); rels.append(rel)
        print(f'  {str(r.peak.date()):<12}{r.depth:>7.1f}%{r.rec_d:>7}{rb:>9.2f}{r2:>9.2f}{rel:>8.2f}')
    if len(recs) > 3:
        rc = spear(np.array(recs, float), np.array(rels, float))
        med = float(np.median(recs))
        f_ = [x for d, x in zip(recs, rels) if d <= med]; s_ = [x for d, x in zip(recs, rels) if d > med]
        print(f'  순위상관(회복일, B/2배) = {rc:+.2f} (양수면 회복이 느릴수록 B 가 유리) · 중앙({med:.0f}일) 아래 {len(f_)}건 중앙 {np.median(f_):.2f} · 위 {len(s_)}건 중앙 {np.median(s_):.2f}')
        print('  → 회복이 빠를수록 B 의 전환은 **비용**이고, 느리고 깊을수록 값을 한다. 가설이 참이면 B 에 불리한 정보다.')

    # ── 판정 ──────────────────────────────────────────────────────────────────
    print('\n' + L); print('판정 (사전 등록 규칙 적용)'); print(L)
    meds = {}
    for _, _, nm in ERAS:
        d = r20[r20.era == nm]
        meds[nm] = (d.rec_d.median(), len(d)) if len(d) else (np.nan, 0)
    print('  ≥−20% 사건 시대별 중앙 회복일: ' + ' · '.join(f'{k} {("—" if np.isnan(v[0]) else f"{v[0]:.0f}일")}(n{v[1]})' for k, v in meds.items()))
    vals = [meds[nm][0] for _, _, nm in ERAS if meds[nm][1] > 0]
    mono = all(x >= y for x, y in zip(vals, vals[1:]))
    thin = min(meds[nm][1] for _, _, nm in ERAS if meds[nm][1] > 0) < 3
    sw_r = CL[CL.recovered]
    m2 = {nm: (sw_r[sw_r.era == nm].rec_d.median(), int((sw_r.era == nm).sum())) for _, _, nm in ERAS}
    print('  [D3] 시대별 중앙 회복일: ' + ' · '.join(f'{k} {("—" if np.isnan(v[0]) else f"{v[0]:.0f}일")}(n{v[1]})' for k, v in m2.items()))
    v2 = [m2[nm][0] for _, _, nm in ERAS if m2[nm][1] > 0]
    mono2 = all(x >= y for x, y in zip(v2, v2[1:]))
    thin2 = min(m2[nm][1] for _, _, nm in ERAS if m2[nm][1] > 0) < 3
    print(f'  단조 감소? D1 {"예" if mono else "아니오"} · D2 {"예" if mono2 else "아니오"} | 순열 p D1 {p_one:.3f} · D2 {p_d2:.3f} | '
          f'시대당 3건 미만 존재? D1 {"예" if thin else "아니오"} · D2 {"예" if thin2 else "아니오"} | F1 절단 {len(inv)}건')
    ok_true = mono2 and p_d2 < 0.05 and not thin2
    verdict = '참' if ok_true else ('거짓' if (len(v2) > 1 and v2[-1] > v2[0]) else '판단 불가')
    print(f'  → **판정: {verdict}** (판정은 D3 독립 사건 — D1 은 2008 을 삼키고 D2 는 긴 약세장을 여러 건으로 센다)')
    print('  예측 대조: P1 ' + ('맞음' if (not np.isnan(m2["2020~"][0]) and not np.isnan(m2["2000~09"][0]) and m2["2020~"][0] < m2["2000~09"][0]) else '틀림')
          + f' · P2 절단 {len(inv)}건(예측 3건 이상 → {"맞음" if len(inv) >= 3 else "틀림"})'
          + f' · P4 코로나 제외 2020년대 ≥−20% {len(nc)}건(예측 1 → {"맞음" if len(nc) == 1 else "틀림"})')

    print('\n이 측정이 낳은 다음 질문 (§-1 ⑥):')
    print('  Q-a 「회복이 빠르다」와 「낙폭이 얕다」는 다른 말인데 프롬프트는 둘을 같이 쓴다 — B 에 중요한 것은 회복 속도가 아니라 **저점의 깊이와 전환의 톱니**다(04 §5-26 빠른 급락 4/4).')
    print('  Q-b 창 절단(F1)은 「최근 20년」류 주장 전체에 걸린다 — 04 의 다른 시대 비교표에도 같은 병이 있는지(§7 대장 후보).')


if __name__ == '__main__':
    main()
