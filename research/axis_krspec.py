# -*- coding: utf-8 -*-
"""
[v24] 국내 상장 ETF 의 실제 사양을 실측한다 — 환노출 여부와 미국채 실효 듀레이션

왜 필요한가: v23 초판은 "국내 미국채 ETF 는 선물형이라 사실상 환헤지"라고 **가정**했고,
그 가정 위에서 "국채 다리는 원화 기준 값어치가 없다 → 금으로 간다"는 결론을 냈다.
**가정이 틀렸다.** 실측하면 미국채10년선물 2종은 환노출이다(b2 ≈ 0.8).
상품명·표기를 믿지 말고 가격으로 확인해야 한다.

[방법] 주간(금요일) 수익률 회귀
    r_ETF = a + b1·r_기초 + b2·r_환율
  - b2 ≈ 1 → 환노출,  b2 ≈ 0 → 환헤지
  - 미국채 ETF 는 b1 이 1 이 되는 합성만기 M* 을 **실효 듀레이션**으로 본다
  - 외부 미국/FRED 값은 각 한국 관측일보다 날짜가 엄격히 앞선 최신 값만 쓴 뒤
    주간 집계한다. 날짜만 있는 자료라 정확한 장중 시점 정렬은 주장할 수 없다.
  - 일간이 아니라 주간을 쓰는 이유: 한국장은 15:30 KST 에 마감해 미국 시세를 하루 늦게
    반영한다. 일간으로 재면 계수가 lag0/lag1 로 쪼개져 둘 다 과소추정된다.

148070 은 한국 금리 시계열이 저장소에 없으므로 실효 만기를 재지 않는다. 미국 금리를
대용하지 않고 환율 beta 만 음성 대조군으로 표시한다.

[교차검증] 같은 기초자산의 환노출/환헤지 쌍의 차이를 환율로 회귀하면 b ≈ 1 이어야 한다.
  둘 다 환노출인 쌍이면 b ≈ 0 이어야 한다. 두 검증을 모두 통과한다.

실행:  python axis_krspec.py
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys

try:                       # [코드리뷰 2026-09-04] 이 파일은 콘솔에 표를 찍는다.
    _sys.stdout.reconfigure(encoding='utf-8')   # cp949 콘솔에서 em-dash 로 죽지 않게
except Exception:
    pass
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import numpy as np
import pandas as pd

import hist_defasset as DA

FXP = 'data/hist/fred_DEXKOUS.csv'

# (코드, 이름, 기초종류, 만기격자)  만기격자 None 이면 금 또는 별도 대조군
PROBE = [
    ('305080', 'TIGER 미국채10년선물', 'TNX', (4, 5, 6, 7, 8, 10)),
    ('308620', 'KODEX 미국10년국채선물', 'TNX', (4, 5, 6, 7, 8, 10)),
    ('453850', 'ACE 미국30년국채액티브(H)', 'TYX', (18, 20, 22, 25, 30)),
    ('148070', 'KIWOOM 국고채10년', 'TNX', (5, 10)),
    ('132030', 'KODEX 골드선물(H)', None, None),
    ('411060', 'ACE KRX금현물', None, None),
]

PAIRS = [
    ('411060', '132030', '금: 환노출 − 환헤지', 1.0),
    ('305080', '308620', '미국채선물: 환노출 − 환노출', 0.0),
]


def fx():
    d = pd.read_csv(FXP)
    d.columns = ['Date', 'v']
    d = d[d['v'] != '.']
    d['Date'] = pd.to_datetime(d['Date'])
    return d.set_index('Date')['v'].astype(float).sort_index()


def _ols(y, X):
    A = np.column_stack([np.ones(len(y))] + X)
    b, *_ = np.linalg.lstsq(A, y, rcond=None)
    p = A @ b
    return b, 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def strictly_prior(s, target):
    """각 target 보다 날짜가 **엄격히 앞선** 마지막 관측값과 그 원자료 날짜."""
    s = s.dropna().sort_index()
    if s.index.has_duplicates:
        s = s.groupby(level=0).last()
    target = pd.DatetimeIndex(target)
    pos = s.index.searchsorted(target, side='left') - 1
    valid = pos >= 0
    value = np.full(len(target), np.nan, dtype=float)
    source_date = np.full(len(target), np.datetime64('NaT'), dtype='datetime64[ns]')
    if valid.any():
        value[valid] = s.iloc[pos[valid]].to_numpy(dtype=float)
        source_date[valid] = s.index.to_numpy(dtype='datetime64[ns]')[pos[valid]]
        assert np.all(source_date[valid] < target.to_numpy(dtype='datetime64[ns]')[valid])
    return pd.Series(value, index=target), pd.Series(source_date, index=target)


def _external_base(idx, maturity, source):
    """한국 관측일에 실제로 알 수 있었던 외부 기초자산 수준."""
    if source is None:
        level, _ = strictly_prior(DA._csv('lbma_gold_pm'), idx)
        return level

    y = DA._csv('yahoo_%s' % source) / 100.0
    y = y[y > 0]
    y, _ = strictly_prior(y, idx)
    y0 = y.shift(1)
    with np.errstate(invalid='ignore', divide='ignore'):
        px = DA.par_price(y.to_numpy(), y0.to_numpy(), maturity)
        r = y0.to_numpy() / 252.0 + (px - 1.0)
    r[0] = 0.0
    return pd.Series(1.0 + r, index=idx).cumprod()


def weekly(etf, base, f):
    df = pd.DataFrame({'e': etf, 'b': base, 'f': f})
    return df.resample('W-FRI').last().pct_change().dropna()


def weekly_fx_only(etf, f):
    df = pd.DataFrame({'e': etf, 'f': f})
    return df.resample('W-FRI').last().pct_change().dropna()


def _selfcheck():
    src = pd.Series([10.0, 30.0], index=pd.to_datetime(['2020-01-01', '2020-01-03']))
    target = pd.to_datetime(['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04'])
    got, used = strictly_prior(src, target)
    assert np.isnan(got.iloc[0])
    assert got.iloc[1:].tolist() == [10.0, 10.0, 30.0]
    assert pd.isna(used.iloc[0])
    assert used.iloc[1:].tolist() == list(pd.to_datetime(['2020-01-01',
                                                          '2020-01-01',
                                                          '2020-01-03']))


def probe():
    F = fx()
    print('===== 주간 회귀  r_ETF = a + b1·r_기초 + b2·r_환율 =====')
    print('※ 외부 미국/FRED 값은 각 한국 관측일보다 엄격히 앞선 최신 날짜 값만 사용한다.')
    print('※ 날짜만 있는 자료라 정확한 장중 시점 정렬은 주장할 수 없다.')
    print('%-28s %-8s %9s %9s %7s %6s' % ('상품', '합성만기', 'b1 기초', 'b2 환율', 'R2', 'n'))
    out = {}
    for code, nm, src, grid in PROBE:
        s = DA.kr(code)
        idx = s.index
        f, _ = strictly_prior(F, idx)
        if code == '148070':
            W = weekly_fx_only(s, f)
            b, r2 = _ols(W['e'].values, [W['f'].values])
            b2 = b[1]
            print('%-28s %-8s %9s %9.3f %7.3f %6d'
                  % (nm, '미측정', '-', b2, r2, len(W)))
            out[code] = dict(name=nm, M=None, b1=np.nan, b2=b2, r2=r2,
                             fx='원화자산')
            print('%-28s -> 실효만기 미측정  환율 beta %.2f (음성 대조군)\n'
                  % ('', b2))
            continue
        cand = grid if grid else (None,)
        best = None
        for M in cand:
            base = _external_base(idx, M, src)
            W = weekly(s, base, f)
            b, r2 = _ols(W['e'].values, [W['b'].values, W['f'].values])
            print('%-28s %-8s %9.3f %9.3f %7.3f %6d'
                  % (nm if M in (cand[0], None) else '', '금' if M is None else '%gY' % M,
                     b[1], b[2], r2, len(W)))
            if best is None or abs(b[1] - 1) < abs(best[1] - 1):
                best = (M, b[1], b[2], r2)
        M, b1, b2, r2 = best
        tag = '환노출' if b2 > 0.6 else ('환헤지' if abs(b2) < 0.35 else '중간')
        out[code] = dict(name=nm, M=M, b1=b1, b2=b2, r2=r2, fx=tag)
        print('%-28s -> 실효만기 %-6s 환 %-5s (b1=%.2f, b2=%.2f)\n'
              % ('', '금' if M is None else '%gY' % M, tag, b1, b2))
    return out


def cross():
    F = fx()
    print('===== 교차검증 — 같은 기초자산 쌍의 차이를 환율로 회귀 =====')
    print('%-34s %9s %9s %7s %s' % ('쌍', 'beta', '기대', 'R2', '판정'))
    for a, b, label, expect in PAIRS:
        sa, sb = DA.kr(a), DA.kr(b)
        ii = sa.index.intersection(sb.index)
        f, _ = strictly_prior(F, ii)
        W = pd.DataFrame({'a': sa.reindex(ii), 'b': sb.reindex(ii), 'f': f}) \
            .resample('W-FRI').last().pct_change().dropna()
        bb, r2 = _ols((W['a'] - W['b']).values, [W['f'].values])
        ok = abs(bb[1] - expect) < 0.35
        print('%-34s %9.3f %9.1f %7.3f %s'
              % (label, bb[1], expect, r2, 'OK' if ok else '불일치'))
    print('  ※ 두 검증이 모두 통과하면 회귀 방법 자체가 신뢰할 만하다는 뜻이다.\n')


def summary(res):
    print('===== 판정 — 표기 vs 실측 =====')
    print('%-28s %-16s %-16s %s' % ('상품', 'v23 초판 가정', '실측', ''))
    ASSUMED = {'305080': '사실상 환헤지', '308620': '사실상 환헤지',
               '453850': '환헤지', '132030': '환헤지',
               '411060': '환노출', '148070': '원화자산'}
    for code, r in res.items():
        same = (ASSUMED[code].replace('사실상 ', '') == r['fx'])
        print('%-28s %-16s %-16s %s'
              % (r['name'], ASSUMED[code], r['fx'] + (' %gY' % r['M'] if r['M'] else ''),
                 '' if same else '  <-- 가정이 틀렸다'))
    print()
    print('결론 3가지')
    print('  1. 미국채10년선물 2종(305080/308620)은 **환노출**이다. v23 초판의 핵심 가정이 틀렸다.')
    print('     -> 국채 다리는 원화 기준으로도 값어치가 있다. 전략_v23.md §5 를 다시 썼다.')
    print('  2. 그 상품의 실효 듀레이션은 10년이 아니라 **약 5~6년**이다(10년물 선물의 CTD 효과).')
    print('     -> 백테스트에서 ust10 이 아니라 ust5 로 모형화해야 한다.')
    print('  3. 148070은 한국 금리 자료가 없어 실효 만기를 **미측정**으로 둔다.')
    print('     -> 미국 금리를 한국 국채의 만기 추정에 대용하지 않았다.')


if __name__ == '__main__':
    _selfcheck()
    res = probe()
    assert res['148070']['M'] is None and np.isnan(res['148070']['b1'])
    cross()
    summary(res)
