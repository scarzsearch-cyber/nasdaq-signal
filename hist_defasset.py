# -*- coding: utf-8 -*-
"""
[v23] 방어자산 확장 — 장기국채 · 금

v21 까지 시험한 방어자산 4종은 전부 주식 계열이었다(현금·T-bill·가치주·배당주).
v21 §2.3 은 "방어자산의 유효성은 위기의 성격에 달려 있다 — 기술주 국지 위기에는
작동하고 시스템 위기에는 작동하지 않는다"고 적고도, 그 다음 단계인
**"성격이 다른 것을 섞자"** 를 하지 않았다. 이 모듈이 그 재료를 만든다.

[1] 상수만기 국채 총수익 합성
    원자료는 미 재무부 상수만기(CMT) 고시 금리다(Yahoo ^TNX 10Y / ^TYX 30Y).
    금리만 있고 가격이 없으므로, **매일 액면가에 재발행되는 파 채권**을 가정해
    총수익을 만든다. 근사(듀레이션 전개)가 아니라 완전 재평가다:

        P(y; c, M) = c * (1 - (1+y)^-M) / y + (1+y)^-M
        r_t        = y_{t-1}/252 + [ P(y_t; c=y_{t-1}, M) - 1 ]
                     └ 이자수입 ┘   └────── 자본손익 ──────┘

    이 방식은 Swinkels(2019) 등이 쓰는 표준이고, 실물 IEF/TLT 와 교차검증한다
    (crosscheck() 참고). 다만 **실물 ETF 의 롤오버·보수·호가 마찰은 안 들어간다.**

[2] 금
    LBMA 런던 오후 고시(USD/oz), 1968-04-01~. 배당이 없으므로 가격수익 = 총수익이다.
    보유비용(보관료·ETF 보수)은 basket() 의 fee 인자로 뺀다.

[3] 국내 실물 ETF
    실제로 살 수 있는 물건과 대조하기 위해 KRX 6종을 함께 받아 둔다(hist_fetch.py).
    이 모듈은 원자료 로더만 제공하고, 판정은 axis_defmix.py 가 한다.

실행:  python hist_defasset.py     # 교차검증 리포트
"""
import numpy as np
import pandas as pd

DIR = 'data/hist'

# 국내 상장 실물 (전부 KRX, ISA 편입 가능)
KR_ETF = {
    '132030': ('KODEX 골드선물(H)', '금', '환헤지'),
    '411060': ('ACE KRX금현물', '금', '환노출'),
    '305080': ('TIGER 미국채10년선물', '미국채10Y', '사실상 헤지(선물)'),
    '308620': ('KODEX 미국채10년선물', '미국채10Y', '사실상 헤지(선물)'),
    '453850': ('ACE 미국30년국채액티브(H)', '미국채30Y', '환헤지'),
    '148070': ('KOSEF 국고채10년', '한국국채10Y', '원화자산'),
}


# ---------------------------------------------------------------- 로더
def _csv(name, col='Close'):
    d = pd.read_csv('%s/%s.csv' % (DIR, name), parse_dates=['Date'])
    return d.set_index('Date')[col].astype(float).sort_index()


def kr(code, col='Close'):
    return _csv('kr_%s_KS' % code, col)


# ---------------------------------------------------------------- 국채
def par_price(y, c, M):
    """액면 1, 연 1회 이표 c, 만기 M 년, 할인율 y 인 채권의 가격."""
    y = np.asarray(y, dtype=float)
    c = np.asarray(c, dtype=float)
    disc = (1.0 + y) ** (-M)
    ann = np.where(np.abs(y) < 1e-12, M, (1.0 - disc) / np.where(np.abs(y) < 1e-12, 1.0, y))
    return c * ann + disc


def ust_tr(idx, maturity=10, source='TNX'):
    """상수만기 국채의 일간 총수익을 idx 에 맞춰 돌려준다."""
    y = _csv('yahoo_%s' % source) / 100.0
    y = y[y > 0]
    y = y.reindex(idx.union(y.index)).ffill().reindex(idx)
    y = y.bfill()
    y0 = y.shift(1)
    px = par_price(y.values, y0.values, maturity)
    r = y0.values / 252.0 + (px - 1.0)
    r[0] = 0.0
    return np.nan_to_num(r)


# ---------------------------------------------------------------- 금
def gold_r(idx, fee=0.0):
    """LBMA 오후 고시 기준 금의 일간 수익률. fee 는 연율 보유비용."""
    g = _csv('lbma_gold_pm')
    g = g[g > 0]
    g = g.reindex(idx.union(g.index)).ffill().reindex(idx).bfill()
    r = g.pct_change().fillna(0.0).values - fee / 252.0
    r[0] = 0.0
    return np.nan_to_num(r)


# ---------------------------------------------------------------- 바스켓
def basket(idx, weights, fee=0.0, base=None):
    """일간 재조정 바스켓의 수익률.

    weights: {'div': 0.5, 'ust10': 0.3, 'gold': 0.2} 형태. 합이 1 이 아니면 정규화.
    base   : 'div' 성분에 쓸 배당체인 수익률 배열(hist_defensive.defensive 산출물).
             None 이면 div 비중이 0 이어야 한다.

    ※ 일간 재조정은 낙관적인 규약이다. 실전은 도피 시점에 비율대로 사서 복귀까지
      들고 있는다. 그 차이는 axis_defmix.py 가 'hold' 규약으로 따로 잰다.
    """
    tot = float(sum(weights.values()))
    comp = {}
    if weights.get('div', 0) > 0:
        if base is None:
            raise ValueError('div 비중이 있으면 base(배당체인 수익률)를 줘야 한다')
        comp['div'] = np.asarray(base, dtype=float)
    if weights.get('ust10', 0) > 0:
        comp['ust10'] = ust_tr(idx, 10, 'TNX')
    if weights.get('ust30', 0) > 0:
        comp['ust30'] = ust_tr(idx, 30, 'TYX')
    if weights.get('gold', 0) > 0:
        comp['gold'] = gold_r(idx)
    r = np.zeros(len(idx))
    for k, w in weights.items():
        if w > 0:
            r = r + (w / tot) * comp[k]
    return r - fee / 252.0


def components(idx, base=None):
    """성분별 일간수익 딕셔너리 (진단·분해용)."""
    out = {'ust10': ust_tr(idx, 10, 'TNX'), 'ust30': ust_tr(idx, 30, 'TYX'),
           'gold': gold_r(idx)}
    if base is not None:
        out['div'] = np.asarray(base, dtype=float)
    return out


# ---------------------------------------------------------------- 교차검증
def _stats(r, idx):
    c = np.cumprod(1 + np.asarray(r))
    yrs = (idx[-1] - idx[0]).days / 365.25
    s = pd.Series(c, index=idx)
    return (c[-1] ** (1 / yrs) - 1, np.std(r) * np.sqrt(252),
            float((s / s.cummax() - 1).min()))


def crosscheck():
    """합성 국채 vs 실물 IEF/TLT, 합성 금 vs 실물 GLD."""
    print('===== 합성 국채 총수익 vs 실물 ETF (2002-07-30 ~) =====')
    print('%-28s %8s %8s %8s %8s' % ('', 'CAGR', '변동성', 'MDD', '상관(일간)'))
    for nm, real, M, src in [('IEF (7-10Y)', 'yahoo_IEF', 8, 'TNX'),
                             ('TLT (20+Y)', 'yahoo_TLT', 25, 'TYX')]:
        rp = _csv(real)
        idx = rp.index
        rr = rp.pct_change().fillna(0).values
        sr = ust_tr(idx, M, src)
        cr = float(np.corrcoef(rr[1:], sr[1:])[0, 1])
        a = _stats(rr, idx); b = _stats(sr, idx)
        print('%-28s %7.2f%% %7.2f%% %7.2f%%' % ('  실물 ' + nm, a[0] * 100, a[1] * 100, a[2] * 100))
        print('%-28s %7.2f%% %7.2f%% %7.2f%% %8.3f' %
              ('  합성 M=%d (%s)' % (M, src), b[0] * 100, b[1] * 100, b[2] * 100, cr))

    print('\n===== 합성 금(LBMA) vs 실물 GLD (2004-11-18 ~) =====')
    gp = _csv('yahoo_GLD')
    idx = gp.index
    rr = gp.pct_change().fillna(0).values
    sr = gold_r(idx)
    cr = float(np.corrcoef(rr[1:], sr[1:])[0, 1])
    a = _stats(rr, idx); b = _stats(sr, idx)
    print('  실물 GLD          CAGR %6.2f%%  변동성 %5.2f%%  MDD %7.2f%%' % (a[0] * 100, a[1] * 100, a[2] * 100))
    print('  LBMA PM 고시      CAGR %6.2f%%  변동성 %5.2f%%  MDD %7.2f%%  상관 %.3f'
          % (b[0] * 100, b[1] * 100, b[2] * 100, cr))
    print('  ※ 일간 상관이 1 이 아닌 것은 고시 시각(런던 15:00) vs 뉴욕 종가 시차 때문이다.')
    print('    누적·변동성·MDD 가 맞으면 방어자산 용도로는 충분하다.')

    print('\n===== 국내 상장 실물 ETF (ISA 편입 가능) =====')
    print('%-8s %-26s %-11s %-14s %-12s %s' % ('코드', '이름', '기초', '환', '상장', '거래일'))
    for code, (nm, kind, fx) in KR_ETF.items():
        try:
            s = kr(code)
            print('%-8s %-26s %-11s %-14s %-12s %d' %
                  (code, nm, kind, fx, str(s.index[0].date()), len(s)))
        except Exception as e:
            print('%-8s %-26s  로드 실패 %s' % (code, nm, e))


if __name__ == '__main__':
    crosscheck()
