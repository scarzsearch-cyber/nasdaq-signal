#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signal.html 의 전략 선택 카드에 띄울 성과지표를 미리 계산해 data/strategy_stats.json 에 굳힌다.

매일 도는 스크립트가 아니다. [v72] 매월 1일 monthly-stats.yml 이 refresh_hist.py 로
원자료를 연장한 뒤 이 스크립트를 돌려 커밋한다 (verify_all 통과 시에만).
원자료는 전부 저장소에 커밋돼 있어 Actions 러너에서도 돈다. 수동 실행:

    python deploy/build_stats.py          # 반드시 저장소 루트에서

[시나리오]
  us_2000  달러 · 2000-01~ · QQQ/QLD 실물, SCHD 상장 이전은 연 2% 현금   (verify.py 규약)
  us_1972  달러 · 1972-02~ · 나스닥 3구간 체인, 방어자산은 배당 실측 체인 (전략_v21 §2·§3)
  kr_1997  원화 · 1997-01~ · 환노출 2배 + 한국 거래일 체결 + 슬리피지 0.1% (전략_v21 §4)
  kr_real  원화 · 2023-06~ · 실물 TIGER 3종 시가 체결                     (전략_v21 §4.5)

[지표] 최종배수 / CAGR / MDD / Calmar / Sortino / Sharpe / 최장회복기간 / Ulcer / 전환횟수
  Sortino, Sharpe 는 reentry_lib.met() 정의 그대로 — 무위험수익률 0, 일간수익 연율화.
  [v60] 최장회복기간·Ulcer 는 reentry_lib.ulcer_uw(). MDD 가 못 재는 '낙폭의 넓이'다.
"""
import io
import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd

try:                       # [v60] cp949 콘솔에서 '−'(U+2212) 로 죽지 않게
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hist_data as H                 # noqa: E402
import hist_defasset as DA            # noqa: E402
import hist_defensive as DF           # noqa: E402
import hist_korea as K                # noqa: E402
import hist_krfinal as KF             # noqa: E402
import hist_krreal as KR              # noqa: E402
import reentry_lib as RL              # noqa: E402
from reentry_lib import met, run, ulcer_uw   # noqa: E402

OUT = os.path.join('data', 'strategy_stats.json')

# 방어자산 2안 — 전략_v23 에서 채택안이 바뀌었다.
DEFS = [
    ('mix', '배당40 / 국채40 / 금20', '전략_v23 채택안. 국내 상품 실측 사양(환노출·실효 5년). 월 1회 재조정.'),
    ('div', '배당100 (v21)', '2026-08 이전 채택안. 비교용으로 남겨 둔다.'),
]


def defensive_r(idx, base, kind):
    """kind='div' 면 배당체인 그대로, 'mix' 면 v23 바스켓(월간 재조정)."""
    if kind == 'div':
        return np.asarray(base, dtype=float)
    return DA.mix_monthly(idx, DA.MIX_V23, base)

STRATS = {
    'B': dict(enter=-0.16, exit=-0.16, name='−16 / −16', ladder=[(('dd', -0.16), 1.0, 0)]),
    'A': dict(enter=-0.16, exit=-0.11, name='−16 / −11', ladder=[(('dd', -0.11), 1.0, 0)]),
}


def json_text(value):
    """브라우저의 JSON.parse 도 읽을 수 있는 엄격한 JSON만 만든다.

    Python json 의 기본값은 NaN/Infinity 를 그대로 써 버린다. 이 파일은 결과를
    signal.json 에도 복사하므로, 비표준 숫자는 성과 카드 전체를 깨뜨린다.
    """
    return json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False)


def atomic_write(path, text):
    """같은 디렉터리의 임시 파일을 완성한 뒤 교체한다."""
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.' + os.path.basename(path) + '.',
                               suffix='.tmp', dir=parent, text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def metric_text(value, spec='.3f'):
    """정의되지 않은 선택 지표는 표에서 대시로 표시한다."""
    return '—' if value is None else format(value, spec)


def signal_stats_text(signal, payload):
    """사본이 다를 때만 갱신할 엄격 JSON을 반환한다."""
    if not isinstance(signal, dict):
        raise ValueError('signal.json 최상위 값이 객체가 아니다')
    if signal.get('stats') == payload:
        return None
    updated = dict(signal)
    updated['stats'] = payload
    return json_text(updated)


def horizons(curve, years=(5, 10, 15, 20)):
    """[v63] **끝 날짜를 맞춘** 최근 N년 배수.

    최종배수는 기준마다 시작일이 달라 세로로 비교할 수 없다(달러 26.6년 165배 vs
    원화 29.6년 2,761배). 넷 다 같은 날(마지막 종가)에 끝나므로 **끝에서 N년을
    잘라내면** 같은 창으로 맞출 수 있다. 구간이 모자라면 None.
    """
    end = curve.index[-1]
    out = {}
    for y in years:
        st = end - pd.DateOffset(years=y)
        if curve.index[0] > st:
            out[str(y)] = None
            continue
        i = int(curve.index.searchsorted(st))
        out[str(y)] = round(float(curve.iloc[-1] / curve.iloc[i]), 3)
    return out


def pack(curve, turn):
    values = np.asarray(curve, dtype=float)
    turns = np.asarray(turn, dtype=float)
    if not len(values) or len(turns) != len(values):
        raise ValueError('성과 곡선과 전환 배열의 길이가 다르거나 비어 있다')
    if not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise ValueError('성과 곡선에 비유한 값 또는 0 이하 값이 있다')
    if not np.all(np.isfinite(turns)):
        raise ValueError('전환 배열에 비유한 값이 있다')
    if hasattr(curve, 'index') and (not curve.index.is_monotonic_increasing
                                    or curve.index.has_duplicates):
        raise ValueError('성과 곡선 날짜가 정렬되지 않았거나 중복됐다')
    m = met(curve)
    ui, uwd, uwo, dmean = ulcer_uw(curve)
    return {
        'final': round(float(m['final']), 3),
        'cagr': round(float(m['cagr']) * 100, 2),
        'mdd': round(float(m['mdd']) * 100, 2),
        # [코드리뷰 2026-09-04] met() 는 calmar(mdd>=0) 와 sharpe(vol==0) 에서도 NaN 을 낸다.
        #   종전엔 sortino 만 막아서, 단조 벤치마크 하나면 json.dump 가 맨 NaN 토큰을 쓰고
        #   그 페이로드가 data/signal.json 에 통째로 박혀 화면이 판정 카드까지 잃는다.
        'calmar': round(float(m['calmar']), 3) if np.isfinite(m['calmar']) else None,
        'sortino': round(float(m['sortino']), 3) if np.isfinite(m['sortino']) else None,
        'sharpe': round(float(m['sharpe']), 3) if np.isfinite(m['sharpe']) else None,
        'years': round(float(m['years']), 1),
        # [v60] MDD 는 최악의 한 점이라 '얼마나 오래 물속이었나'를 못 잰다.
        'ulcer': round(float(ui), 2),
        'dd_mean': round(float(dmean), 2),   # [v62] '평균 몇 % 물속' 체감값
        'uw_months': round(uwd / 30.4375, 1),
        'uw_open': bool(uwo),
        'switches': int(np.sum(turns > 1e-9)),
        'horizons': horizons(curve),         # [v63] 끝을 맞춘 최근 5/10/15/20년 배수
        'start': curve.index[0].strftime('%Y-%m-%d'),
        'end': curve.index[-1].strftime('%Y-%m-%d'),
    }


def seg_of(D, curve):
    """전략 곡선이 차지하는 구간을 D 의 전체 인덱스 위에서 찾는다."""
    source = pd.Index(D['idx'])
    target = pd.Index(curve.index)
    lo = int(source.searchsorted(target[0]))
    segment = source[lo:lo + len(target)]
    if not segment.equals(target):
        raise ValueError('전략 곡선과 벤치마크 원재료의 날짜가 정확히 맞지 않는다')
    return slice(lo, lo + len(target))


def bench_pack(curve, rlev, rdef):
    """[v61] 전략과 **같은 구간·같은 재료**로 잰 두 벤치마크.

    지표 숫자만으로는 좋고 나쁨을 체감할 수 없다(Ulcer 22 는 어느 정도인가?).
    비교 대상이 있어야 읽힌다:
      lev  2배 그냥 보유  — 전략을 안 썼을 때. 이 전략이 존재하는 이유
      def  방어 단독      — 공격을 아예 안 했을 때. 아래쪽 경계
    """
    z = np.zeros(len(curve))
    out = {}
    for key, r in (('lev', rlev), ('def', rdef)):
        rr = np.asarray(r, dtype=float).copy()
        if len(rr) != len(curve) or not np.all(np.isfinite(rr)):
            raise ValueError(f'{key} 벤치마크 수익률이 비었거나 날짜/유한성 계약을 어겼다')
        rr[0] = 0.0
        out[key] = pack(pd.Series(np.cumprod(1 + rr), index=curve.index), z)
    return out


def sc_us_2000(kind):
    D = dict(RL.build())
    D['schdr'] = defensive_r(D['idx'], D['schdr'], kind)
    out, bm = {}, None
    for k, S in STRATS.items():
        c, w, t = run(D, S['ladder'], enter=S['enter'])
        out[k] = pack(c, t)
        if bm is None:
            sg = seg_of(D, c)
            bm = bench_pack(c, D['qldr'][sg], D['schdr'][sg])
    return out, bm


def sc_us_1972(kind):
    D = dict(DF.build('chain'))
    D['schdr'] = defensive_r(D['idx'], D['schdr'], kind)
    out, bm = {}, None
    for k, S in STRATS.items():
        c, w, t = run(D, S['ladder'], enter=S['enter'])
        out[k] = pack(c, t)
        if bm is None:
            sg = seg_of(D, c)
            bm = bench_pack(c, D['qldr'][sg], D['schdr'][sg])
    return out, bm


def kr_basket(idx, dfk, fr, kind):
    """원화 기준 방어 다리. [코드리뷰 2026-09-04] sc_kr_1997 과 hedge_kr_1997 에 글자
    그대로 복제돼 있던 레시피를 한 곳으로 모았다 — 한쪽만 고치면 같은 표의 두 열이
    말없이 갈라진다(두 함수가 kr_1997 행의 strategies 와 strategies_hedge 를 만든다).

    채택안 3종은 전부 환노출이다 - axis_krspec.py 의 실측(b2=0.8~1.0).
      TIGER 미국배당다우존스 / TIGER 미국채10년선물(실효 5년) / ACE KRX금현물
    [v36] ust5 는 **선물형**이다(305080). 현물 총수익에서 단기금리·보수를 뺀다.
    """
    if kind == 'div':
        return np.asarray(dfk, dtype=float)
    raw = {'div': np.asarray(dfk, dtype=float),
           'ust5': DA.ust_tr(idx, 5, 'TNX', futures=True, fee=DA.UST_FEE),
           'gold': DA.gold_r(idx)}
    parts = {k: (raw[k] if k == 'div' else (1 + raw[k]) * (1 + fr) - 1)
             for k in DA.MIX_V23}
    return DA.mix_monthly_parts(idx, DA.MIX_V23, parts)


def sc_kr_1997(kind):
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    krd = K.kr_caldays()
    sr = kr_basket(idx, dfk, fr, kind)
    Dx = dict(D); Dx['qldr'] = lev2; Dx['schdr'] = sr
    out, bm = {}, None
    for k, S in STRATS.items():
        c, w, t = K.run_kr(Dx, S, cost=0.001, slip=0.001, start=KF.ST, krdays=krd)
        out[k] = pack(c, t)
        if bm is None:
            sg = seg_of(Dx, c)
            bm = bench_pack(c, np.asarray(Dx['qldr'])[sg], np.asarray(Dx['schdr'])[sg])
    return out, bm


def sc_kr_real(kind):
    out, bm = {}, None
    for k, S in STRATS.items():
        c, hold, dd = KR.run_real(S['exit'], defmix=(kind == 'mix'))
        turn = hold.shift(1).fillna(1.0).diff().abs().fillna(0).values
        out[k] = pack(c, turn)
        if bm is None:
            kr, rl, rd = KR.legs_real(defmix=(kind == 'mix'))
            assert kr.equals(c.index), '벤치마크 달력이 전략과 다르다'
            bm = bench_pack(c, rl.values, rd.values)
    return out, bm


# ---------------------------------------------------------------- 헤지 변형 [v72]
# ③ 자산헤지: 상승장 QLD60/SCHD40(월 1회 재조정, mix_monthly_parts 규약 0.05%),
#    낙폭 -16% 이하면 전량 방어(배당40/국채40/금20), 회복 시 60/40 복귀.
#    신호·문턱·체결·비용은 채택안과 완전히 같다 — 다른 것은 공격 다리뿐이다.
#    방어를 mix 로 굳힌 근거: us_1972 실측에서 mix Calmar 0.453 vs 배당100 0.327
#    (MDD -46.1% vs -64.8%), kr_1997 은 사실상 동률 — 전략_v72 문서.
HEDGE_W = {'lev': 0.6, 'div': 0.4}


def hedge_us_2000(defkind='mix'):
    D = dict(RL.build())
    att = DA.mix_monthly_parts(D['idx'], HEDGE_W,
                               {'lev': np.asarray(D['qldr']), 'div': np.asarray(D['schdr'])})
    dr = defensive_r(D['idx'], D['schdr'], defkind)
    Dx = dict(D); Dx['qldr'] = np.asarray(att, float); Dx['schdr'] = np.asarray(dr, float)
    c, w, t = run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
    return {'B': pack(c, t)}


def hedge_us_1972(defkind='mix'):
    D = dict(DF.build('chain'))
    att = DA.mix_monthly_parts(D['idx'], HEDGE_W,
                               {'lev': np.asarray(D['qldr']), 'div': np.asarray(D['schdr'])})
    dr = defensive_r(D['idx'], D['schdr'], defkind)
    Dx = dict(D); Dx['qldr'] = np.asarray(att, float); Dx['schdr'] = np.asarray(dr, float)
    c, w, t = run(Dx, STRATS['B']['ladder'], enter=STRATS['B']['enter'])
    return {'B': pack(c, t)}


def hedge_kr_1997(defkind='mix'):
    D, idx, lev2, lev1, dfk, fr = KF.build_krw('chain')
    att = DA.mix_monthly_parts(idx, HEDGE_W,
                               {'lev': np.asarray(lev2), 'div': np.asarray(dfk)})
    dr = kr_basket(idx, dfk, fr, defkind)
    Dx = dict(D); Dx['qldr'] = np.asarray(att, float); Dx['schdr'] = np.asarray(dr, float)
    c, w, t = K.run_kr(Dx, STRATS['B'], cost=0.001, slip=0.001, start=KF.ST,
                       krdays=K.kr_caldays())
    return {'B': pack(c, t)}


def hedge_kr_real(defkind='mix'):
    defmix = (defkind == 'mix')
    kr, rl, rd_def = KR.legs_real(defmix=defmix)
    kr0, _, rd_div = KR.legs_real(defmix=False)
    if not kr0.equals(kr):
        raise ValueError('실물 헤지의 배당 공격다리와 전략 달력이 다르다')
    rd_div = rd_div.reindex(kr)
    if rd_div.isna().any() or rd_def.reindex(kr).isna().any():
        raise ValueError('실물 헤지의 방어/배당 수익률 정렬에 빈 날이 있다')
    att = pd.Series(DA.mix_monthly_parts(kr, HEDGE_W,
                                         {'lev': rl.values,
                                          'div': rd_div.values}), index=kr)
    _, hold, _ = KR.run_real(STRATS['B']['exit'], defmix=defmix)
    if not hold.index.equals(kr) or hold.isna().any():
        raise ValueError('실물 헤지의 보유 신호와 수익률 달력이 다르다')
    eff = hold.shift(1).fillna(1.0)
    r = eff * att + (1 - eff) * rd_def.reindex(kr).fillna(0)
    turn = eff.diff().abs().fillna(0)
    g = (1 + r) * (1 - 0.002 * turn)
    c = pd.Series(np.cumprod(g), index=kr)
    return {'B': pack(c, turn.values)}


HEDGES = {'us_2000': hedge_us_2000, 'us_1972': hedge_us_1972,
          'kr_1997': hedge_kr_1997, 'kr_real': hedge_kr_real}

SCENARIOS = [
    ('us_2000', '미국 달러 기준', 'QQQ 실물 · SCHD 상장 이전은 연 2% 현금. verify.py 와 같은 규약.', sc_us_2000),
    ('us_1972', '달러 · 54년 확장', '나스닥 3구간 체인 + 배당 실측 방어자산. 가장 긴 표본.', sc_us_1972),
    ('kr_1997', '원화 · 한국 체결', '환노출 2배 + 한국 거래일 체결 + 슬리피지 0.1%. 국내 ETF 상장 이전은 원화 환산 시뮬레이션.', sc_kr_1997),
    ('kr_real', '원화 · 실물 TIGER', 'TIGER 3종이 모두 상장된 이후만. 실제 시가 체결.', sc_kr_real),
]


def doc_parts(path='01_Strategy_Logic.md'):
    """AUTO-STATS 표식과 원문을 검증해 치환 경계를 반환한다."""
    S, E = '<!-- AUTO-STATS:START', '<!-- AUTO-STATS:END -->'
    if not os.path.exists(path):
        raise FileNotFoundError(f'{path} 가 없다 — AUTO-STATS 동기화를 보장할 수 없다')
    with io.open(path, encoding='utf-8') as f:
        txt = f.read()
    i, j = txt.find(S), txt.find(E)
    head_end = txt.find('-->', i, j) + 3 if 0 <= i < j else -1
    if (txt.count(S) != 1 or txt.count(E) != 1 or i < 0 or j < 0
            or j < i or head_end < 3):
        raise ValueError(f'{path} 의 AUTO-STATS 마커가 없거나 잘못됐다')
    return txt, head_end, j


def sync_doc(payload, path='01_Strategy_Logic.md'):
    """[v73] 최신 성과를 문서의 AUTO-STATS 블록에만 반영한다.
    마커 밖의 사람 글은 절대 건드리지 않으며, 계약 파손은 실패-폐쇄한다."""
    txt, head_end, j = doc_parts(path)
    rows = ['| 기준 | 구간 | 최종배수 | CAGR | MDD | 회복기간 | 전환 |',
            '|---|---|---:|---:|---:|---:|---:|']
    # [코드리뷰 2026-09-04] 종전엔 머리글에 scenarios[0] 의 끝 날짜 하나를 찍고 네 행 전부에
    #   그것을 씌웠다. 그런데 미국 달력과 한국 달력은 같은 날 끝나지 않는다 (실측:
    #   us_* / kr_1997 은 2026-08-28, kr_real 은 2026-09-01). 마지막 거래일은 **행마다** 적는다.
    for s in payload['scenarios']:
        m = s['strategies']['B']
        uw = f"{m['uw_months']/12:.1f}년" if m['uw_months'] >= 12 else f"{m['uw_months']:.0f}개월"
        rows.append(f"| {s['label']} | {m['start'][:7]}~{m['end']} ({m['years']}년) "
                    f"| **{m['final']:,.1f}배** | {m['cagr']:.2f}% | −{abs(m['mdd']):.1f}% "
                    f"| {uw}{'+' if m['uw_open'] else ''} | {m['switches']} |")
    block = (f"\n{payload['generated_at']} 생성 (월간 자동 갱신). "
             f"기준마다 시장 달력이 달라 마지막 거래일이 다르다 - 구간 열에 적었다.\n\n"
             + '\n'.join(rows) + '\n')
    out = txt[:head_end] + block + txt[j:]
    if out != txt:
        atomic_write(path, out)
        print('→', path, '(AUTO-STATS 블록 갱신)')


def main():
    if not os.path.exists('qqq_us_d.csv'):
        sys.exit('저장소 루트에서 실행해야 한다: python deploy/build_stats.py')
    scen = []
    for key, label, note, fn in SCENARIOS:
        row = dict(key=key, label=label, note=note)
        for dk, dlabel, dnote in DEFS:
            print('  계산 중 …', key, dk, flush=True)
            st, bm = fn(dk)
            row['strategies' if dk == 'mix' else 'strategies_' + dk] = st
            row['benchmarks' if dk == 'mix' else 'benchmarks_' + dk] = bm
        print('  계산 중 …', key, 'hedge', flush=True)
        row['strategies_hedge'] = HEDGES[key]('mix')      # [v72] ③ 자산헤지 60/40 · 방어 mix (추천)
        row['strategies_hedge_div'] = HEDGES[key]('div')  # [v73] ④ 자산헤지 60/40 · 방어 배당100
        scen.append(row)
    payload = dict(
        generated_at=pd.Timestamp.now('UTC').strftime('%Y-%m-%d %H:%M UTC'),
        strategies={k: dict(name=v['name'], enter=round(v['enter'] * 100),
                            exit=round(v['exit'] * 100)) for k, v in STRATS.items()},
        defensives=[dict(key=k, label=l, note=n) for k, l, n in DEFS],
        defensive_legs=DA.MIX_LEGS,
        scenarios=scen,
    )
    # json.dumps 기본값은 NaN/Infinity 를 허용한다. 브라우저는 그것을 JSON 으로
    # 인정하지 않으므로 쓰기 **전에** 전체 페이로드를 엄격하게 직렬화한다.
    payload_text = json_text(payload)

    # [v45·v60] signal.json 은 이 파일의 **사본**을 안에 들고 있고, 화면은 그 사본을
    # 우선한다(signal.html: if(AUTO && AUTO.stats) STATS = AUTO.stats).
    # 그래서 여기서 새로 굳히면 사본도 같이 갱신해야 한다. 안 하면 다음 일일
    # 실행 때까지 라이브가 옛 수치를 보여준다 — v36 정정 때 실제로 그랬다.
    sig = os.path.join('data', 'signal.json')
    signal_text = None
    if os.path.exists(sig):
        with open(sig, encoding='utf-8') as f:
            j = json.load(f)
        # [코드리뷰 2026-09-04] update_signal.load_stats() 는 원본이 없으면 None 을 쓴다.
        #   그때 j.get('stats', {}) 는 {} 가 아니라 None 이라 AttributeError 로 죽었고,
        #   OUT 은 이미 쓰인 뒤라 signal.json 사본과 01 문서만 옛 판으로 남았다.
        # generated_at 은 분 단위다. 같은 분 안에 원자료/코드가 달라져 재실행되면
        # 시각은 같아도 내용은 달라질 수 있으므로 페이로드 전체를 비교한다.
        signal_text = signal_stats_text(j, payload)

    # 출력 파일을 건드리기 전에 문서 계약도 먼저 검사한다. 표식 파손을 경고로만
    # 넘기면 새 JSON 과 옛 문서가 섞인 채 다음 단계로 진행될 수 있다.
    doc_parts()

    # 두 JSON 모두 완성·검증된 뒤에만 첫 파일을 건드린다. 파일별 쓰기도 원자적으로
    # 교체해 중간 종료가 반쪽 JSON 을 남기지 않게 한다.
    atomic_write(OUT, payload_text)
    if signal_text is not None:
        atomic_write(sig, signal_text)
        print('→', sig, '(내장 사본 갱신)')
    sync_doc(payload)          # [v73] 01 문서 AUTO-STATS 블록
    # [v60] 사본 갱신은 아래 요약 출력보다 **먼저** 한다 — 출력이 죽어도
    #       사본이 옛 판으로 남지 않도록.

    hdr = '%-16s %-9s %10s %7s %8s %8s %8s %9s %7s %6s' % (
        '시나리오', '전략', '최종배수', 'CAGR', 'MDD', 'Calmar', 'Sortino',
        '회복기간', 'Ulcer', '전환')
    print('\n' + hdr); print('-' * len(hdr))
    for s in scen:
        for k in ('B', 'A'):
            m = s['strategies'][k]
            o = s['strategies_div'][k]
            def uw(x):
                return '%.1f개월%s' % (x['uw_months'], '+' if x['uw_open'] else '')
            print('%-16s %-9s %10s %6.2f%% %7.2f%% %8s %8s %9s %7.2f %6d' % (
                s['label'] if k == 'B' else '', STRATS[k]['name'], f"{m['final']:,.1f}",
                m['cagr'], m['mdd'], metric_text(m['calmar']),
                '—' if m['sortino'] is None else f"{m['sortino']:.3f}",
                uw(m), m['ulcer'], m['switches']))
            print('%-16s %-9s %10s %6.2f%% %7.2f%% %8s %8s %9s %7.2f %6d   <- 배당100' % (
                '', '', f"{o['final']:,.1f}", o['cagr'], o['mdd'], metric_text(o['calmar']),
                '—' if o['sortino'] is None else f"{o['sortino']:.3f}",
                uw(o), o['ulcer'], o['switches']))
        for bk, blab in (('lev', '2배 보유'), ('def', '방어 단독')):
            b = s['benchmarks'][bk]
            print('%-16s %-9s %10s %6.2f%% %7.2f%% %8s %8s %9s %7.2f %6s   <- 벤치' % (
                '', blab, f"{b['final']:,.1f}", b['cagr'], b['mdd'], metric_text(b['calmar']),
                '—' if b['sortino'] is None else f"{b['sortino']:.3f}",
                '%.1f개월%s' % (b['uw_months'], '+' if b['uw_open'] else ''),
                b['ulcer'], '-'))
    print('\n→', OUT)


def selftest():
    assert metric_text(None) == '—'
    assert metric_text(1.23456) == '1.235'
    assert json.loads(json_text({'stats': None})) == {'stats': None}
    try:
        json_text({'bad': float('nan')})
    except ValueError:
        pass
    else:
        raise AssertionError('NaN 이 엄격한 JSON 검사를 통과했다')
    old = {'generated_at': 'same', 'value': 1}
    new = {'generated_at': 'same', 'value': 2}
    assert json.loads(signal_stats_text({'stats': old}, new))['stats'] == new
    assert signal_stats_text({'stats': new}, new) is None
    idx = pd.date_range('2026-01-01', periods=3)
    assert seg_of({'idx': idx}, pd.Series([1.0, 1.1], index=idx[1:])) == slice(1, 3)
    try:
        seg_of({'idx': idx}, pd.Series([1.0, 1.1], index=[idx[0], idx[2]]))
    except ValueError:
        pass
    else:
        raise AssertionError('날짜가 건너뛴 벤치마크 정렬이 통과했다')
    with tempfile.TemporaryDirectory() as td:
        bad_doc = os.path.join(td, 'bad.md')
        atomic_write(bad_doc, '<!-- AUTO-STATS:START -->\n끝 표식 없음')
        try:
            sync_doc({}, bad_doc)
        except ValueError:
            pass
        else:
            raise AssertionError('깨진 AUTO-STATS 표식이 통과했다')
    print('build_stats selftest: PASS (엄격 JSON · 선택 지표 · 달력 정렬)')



if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        main()
