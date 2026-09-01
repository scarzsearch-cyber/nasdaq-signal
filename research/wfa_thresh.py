# -*- coding: utf-8 -*-
"""
[2026-09-01 소유자 승인] 04 §5-13 정정2 의 **「정정 WFA」를 재현 가능하게 고정한다.**

★ 왜 이 파일이 필요했나 (04 §5-22 A 가 찾아낸 빈칸)

  §5-13 정정2 는 「누적 성과로 고르는 설계가 결함이었고, **직전 N년 창**으로 재설계하면
  선택 중앙값이 정확히 −16 이다」라는 표를 싣는다. 그런데 **그 표를 만든 코드가 없다.**
  `b_adversarial.py` 의 `test2()` 는 **결함판**(누적 선택)이고 문서가 스스로 그렇게 밝힌다.
  즉 **재현 불가능한 수치가 「−16 을 재조정하지 말라」의 근거 한 축으로 인용되고 있었다.**
  이 파일이 그 축을 재현 가능하게 만든다.

★ 결함이 정확히 어디였나 (한 줄 차이다)

    결함판  best = max(THS, key=lambda t: cs[t][i] / cs[t][**0**])      <- 역사 전체 누적
    정정판  best = max(THS, key=lambda t: cs[t][i] / cs[t][**i-train**]) <- 직전 N년 창

  누적으로 고르면 **초기 데이터가 영원히 지배한다** — 1985년에 좋았던 문턱이 2020년의
  선택까지 끌고 간다. 워크포워드의 취지(그 시점에 알 수 있던 것만 쓴다)는 지키면서도
  **가중치가 과거에 못 박히는** 설계다.

★ 사전 등록 — 결과 보기 전에 (§-1 ⑤ 실패/통과가 각각 무엇을 뜻하는가)

  · 선택 중앙값이 −16 에서 **벗어나면**  -> §5-13 정정2 의 표가 재현 불가. **문서를 고쳐야 한다.**
  · 선택 중앙값이 −16 이고 고정이 적응형을 이기면 -> 「과거 자료만으로 골라도 −16 이 나오고,
    그나마 고르는 것보다 고정이 낫다」 = 재조정 금지의 근거가 재현된 것.
  ⚠ **어느 쪽이 나와도 「−16 이 최적」은 증명되지 않는다.** 이 검사가 답하는 것은
    **「그 시점 자료만으로 골랐다면 무엇이 나왔나」**뿐이다(v56 T3 와 같은 계열).

  ★ 그리고 **문서 수치와 어긋나면 조용히 새 수치로 갈아치우지 않는다** — 어긋난 사실 자체를
    출력한다. 원본 코드가 없으므로 **규약 차이(지표·엠바고·격자)** 가 원인일 수 있다.

★ 실행 결과 — **문서 표는 재현된다. 단 조건이 둘 있었고, 문서엔 안 적혀 있었다.**
  ① **엔진**: `ext`(eng_common, **1972~ 54년**, 방어=40/40/20 실제 바스켓)라야 맞는다.
     `ndx`(b_adversarial 규약, 1985~, 방어=현금)로는 **12개 중 1개**만 맞는다.
  ② **「고정 승」의 뜻**: 적응형이 −16 을 고른 걸음은 두 곡선이 같아 **무승부**인데,
     문서는 그 무승부를 **고정 쪽에 세었다**(=「고정이 지지 않은 비율」).
     **엄격히 이긴 비율은 33~40%** 다. 이 규약을 밝히지 않으면 73%가 과장으로 읽힌다.
  두 조건을 맞추면 **12/12 일치**. 그래서 이 파일은 **문서를 고치지 않고 규약을 명시**한다.

규약: 두 엔진을 **모두** 돌려 문서와 대조한다 — 어느 쪽으로 쟀는지 문서에 없었기 때문이다.
  결함판과 정정판은 **같은 엔진에서 나란히** 돌린다(§-1 ⑧ — 한 번에 하나만 바꾼다).

평가 전용 · 전략 무변경. 실행: python research/wfa_thresh.py
"""
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
_sys.path.insert(0, _os.path.join(_ROOT, 'research'))

import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import b_adversarial as BA                              # noqa: E402

THS = [round(-0.24 + 0.01 * i, 2) for i in range(17)]    # −24% ~ −8%
FIX = -0.16
Y = 252
L = '=' * 96


def curves(engine='ndx'):
    """★ 원본 코드가 없으므로 **두 엔진 모두** 돌려 문서와 대조한다 (§-1 ④).

    'ndx' — b_adversarial 규약: yahoo_NDX.csv(**1985~**) · 방어=현금 0%
    'ext' — 저장소 본엔진: eng_common(**1972~**, 54년) · 방어=40/40/20 실제 바스켓
    §5-13 이 어느 쪽으로 쟀는지 문서에 안 적혀 있다. 둘 다 재서 그 사실을 드러낸다.
    """
    if engine == 'ndx':
        px = BA.load('data/hist/yahoo_NDX.csv')
        _, r2 = BA.prep(px)
        return px.index, {t: BA.curve(BA.rule_w(px, t), r2) for t in THS}
    import numpy as _np
    import pandas as _pd
    import eng_common as EC
    G, _X = EC.selfcheck()
    idx = G.idx
    PX = _pd.Series(G.D['px'], index=idx)
    QLDR = _np.nan_to_num(_np.asarray(G.D['qldr'], float))
    MIXR = _np.nan_to_num(_np.asarray(G.Dm['schdr'], float))
    return idx, {t: _np.asarray(EC.sim2(EC.rule_dd(PX, t, t), QLDR, MIXR), float)
                 for t in THS}


def wfa(cs, n, train_y, step_y, mode, metric='mult'):
    """mode='window' 정정판(직전 train_y년) · mode='cum' 결함판(역사 전체 누적)."""
    tr, st = train_y * Y, step_y * Y
    picks, fs, ff = [], [], []
    for i in range(tr, n - st, st):
        lo = 0 if mode == 'cum' else i - tr
        if metric == 'mult':
            key = lambda t: cs[t][i] / cs[t][lo]
        else:                                            # Calmar (반증용 변형)
            def key(t):
                seg = cs[t][lo:i] / cs[t][lo]
                mdd = abs(float(np.min(seg / np.maximum.accumulate(seg) - 1)))
                cagr = float(seg[-1]) ** (Y / len(seg)) - 1
                return cagr / max(mdd, 1e-9)
        best = max(THS, key=key)
        j = min(i + st, n - 1)
        picks.append(best)
        fs.append(cs[best][j] / cs[best][i])
        ff.append(cs[FIX][j] / cs[FIX][i])
    p, fs, ff = np.array(picks), np.array(fs), np.array(ff)
    return dict(n=len(p), med=float(np.median(p)),
                band=float(np.mean((p >= -0.18) & (p <= -0.14))),
                exact=float(np.mean(p == FIX)),
                fixwin=float(np.mean(ff > fs)),
                # ★ 적응형이 −16 을 고른 걸음은 **무승부**다(두 곡선이 같다).
                #   문서의 「고정 승」은 그 무승부를 고정 쪽에 센 값 = 「고정이 지지 않은 비율」.
                fixnl=float(np.mean(ff >= fs)),
                sel_tot=float(np.prod(fs)), fix_tot=float(np.prod(ff)),
                lo=float(p.min()), hi=float(p.max()), sd=float(p.std()))


def row(lab, d):
    print('  %-18s%6d회%10.2f%10.0f%%%11.0f%%%8.0f%%%9.0f%%   %s'
          % (lab, d['n'], d['med'], 100 * d['band'], 100 * d['exact'],
             100 * d['fixwin'], 100 * d['fixnl'], '%+.2f~%+.2f' % (d['lo'], d['hi'])))


SET = [('훈련10y/걸음3y', 10, 3), ('훈련15y/걸음3y', 15, 3), ('훈련10y/걸음5y', 10, 5)]
DOC = {'훈련10y/걸음3y': (-0.16, 0.47, 0.33, 0.73),
       '훈련15y/걸음3y': (-0.16, 0.62, 0.38, 0.77),
       '훈련10y/걸음5y': (-0.16, 0.44, 0.33, 0.67)}


def compare(cs, n, tag):
    print()
    print('  [%s] 정정판 — 직전 N년 창으로만 선택' % tag)
    print('  %-18s%8s%10s%10s%11s%9s%9s   %s'
          % ('설정', '걸음수', '선택 중앙', '−18~−14', '−16 정확히', '고정승', '무승부포함', '선택 범위'))
    got, hits, tot = {}, 0, 0
    for lab, tr, st in SET:
        d = wfa(cs, n, tr, st, 'window')
        got[lab] = d
        row(lab, d)
    print()
    print('  %-18s%12s%12s%12s%12s' % ('설정', '항목', '문서', '재현', '판정'))
    for lab, _, _ in SET:
        d, doc = got[lab], DOC[lab]
        for k, nm, dv, gv, tol in (('med', '선택 중앙', doc[0], d['med'], 0.005),
                                   ('band', '−18~−14', doc[1], d['band'], 0.06),
                                   ('exact', '−16 정확히', doc[2], d['exact'], 0.06),
                                   ('fixnl', '고정 승(무승부 포함)', doc[3], d['fixnl'], 0.02)):
            hit = abs(dv - gv) <= tol
            hits += hit; tot += 1
            f = (lambda x: '%.2f' % x) if k == 'med' else (lambda x: '%.0f%%' % (100 * x))
            print('  %-18s%12s%12s%12s%12s'
                  % (lab if k == 'med' else '', nm, f(dv), f(gv), '일치' if hit else '★어긋남'))
    print('  -> %s: 12개 항목 중 **%d개 일치**' % (tag, hits))
    return hits, got


def main():
    print(L)
    print('정정 WFA — 「직전 N년 창으로 골랐다면 −16 이 나왔을까」 (04 §5-13 정정2 재현 시도)')
    print(L)
    print()
    print('★ 문서에 **어느 엔진으로 쟀는지가 안 적혀 있다.** 그래서 둘 다 돌린다 (§-1 ④).')

    idx_n, cs_n = curves('ndx')
    idx_e, cs_e = curves('ext')
    print('   ndx  %s ~ %s (%d거래일) · 방어=현금 0%%'
          % (str(idx_n[0].date()), str(idx_n[-1].date()), len(idx_n)))
    print('   ext  %s ~ %s (%d거래일) · 방어=40/40/20 실제 바스켓'
          % (str(idx_e[0].date()), str(idx_e[-1].date()), len(idx_e)))

    print()
    print(L)
    print('[1~2] 두 엔진 × 문서 대조')
    print(L)
    h1, _ = compare(cs_n, len(idx_n), 'ndx 1985~')
    h2, got = compare(cs_e, len(idx_e), 'ext 1972~')
    print()
    if max(h1, h2) >= 12:
        print('  => **ext(1972~) 엔진에서 문서 표가 12/12 재현된다.**')
        print('     단 「고정 승」은 **무승부(적응형이 −16 을 고른 걸음)를 고정 쪽에 센 값**이다')
        print('     — 「고정이 지지 않은 비율」. 엄격히 이긴 비율은 33~40%% 다. 문서에 규약을 명시할 것.')
    elif max(h1, h2) >= 10:
        print('  => 한쪽 엔진이 문서를 대체로 재현한다. 문서에 **엔진을 명시**하면 끝난다.')
    else:
        print('  => **어느 엔진도 문서 표를 재현하지 못한다.**')
        print('     원본 코드가 없으므로 원인을 특정할 수 없다 — 지표·엠바고·격자·걸음')
        print('     기준이 달랐을 수 있다. **문서 수치를 그대로 두면 재현 불가 수치가 남는다.**')
    cs = cs_e
    n = len(idx_e)

    # ── §-1 ⑧ — 문서는 「창 수정 때문」이라 했는데, 정말 창 하나만 바뀌었나 ──
    print()
    print(L)
    print('[3] ★ 2×2 — 「창 수정 때문」이 맞나 (§-1 ⑧: A 만 바꾼 열이 있어야 인과를 말한다)')
    print(L)
    print()
    print('  문서는 **결함판 「중앙 −0.21 · −16 선택률 10%%」** 와')
    print('  **정정판 「중앙 −0.16」** 을 나란히 놓고 차이를 **창 수정** 탓으로 돌린다.')
    print('  그런데 두 값이 **같은 엔진에서 나온 것인지**가 문서에 없다. 네 칸을 다 채운다:')
    print()
    print('  %-12s%-14s%10s%12s%12s' % ('엔진', '선택 설계', '선택 중앙', '−16 정확히', '문서와'))
    cell = {}
    for eng, cs_, n_ in (('ndx 1985~', cs_n, len(idx_n)), ('ext 1972~', cs_e, len(idx_e))):
        for mode, mlab in (('cum', '결함(누적)'), ('window', '정정(직전10y)')):
            d = wfa(cs_, n_, 10, 3, mode)
            cell[(eng, mode)] = d
            doc = ''
            if abs(d['med'] + 0.21) < 0.005 and abs(d['exact'] - 0.10) < 0.03:
                doc = '<- 문서의 「결함」'
            if abs(d['med'] + 0.16) < 0.005 and abs(d['exact'] - 0.33) < 0.02:
                doc = '<- 문서의 「정정」'
            print('  %-12s%-14s%10.2f%11.0f%%   %s' % (eng, mlab, d['med'], 100 * d['exact'], doc))
    print()
    print('  -> **문서의 두 값은 서로 다른 엔진에서 나왔다.** 즉 정정2 는 **창과 엔진을')
    print('     동시에 바꿔 놓고 차이를 창 하나에 돌렸다** — §-1 ⑧ 이 금지한 서술이다.')
    print('     같은 엔진(ext)에서 창만 바꾸면 선택 중앙은 **%.2f -> %.2f** 로 **안 움직인다.**'
          % (cell[('ext 1972~', 'cum')]['med'], cell[('ext 1972~', 'window')]['med']))
    print()
    print('  ★ 그러나 **결론은 무너지지 않고 오히려 강해진다**: ext 엔진에서는')
    print('    **결함 설계로 골라도 −16 이 나온다.** 「과거 자료만으로 골라도 −16」이라는')
    print('    §5-13 의 주장은 설계에 의존하지 않는다 — 다만 **엔진(1972~ · 실제 방어)에는')
    print('    의존한다.** 1985~ · 방어=현금으로 재면 −0.19~−0.21 이 나온다.')

    print()
    print('[3-b] 결함판 세 설정 (ext 엔진) — 참고')
    print('  %-18s%8s%10s%10s%11s%9s%9s   %s'
          % ('설정', '걸음수', '선택 중앙', '−18~−14', '−16 정확히', '고정승', '무승부포함', '선택 범위'))
    for lab, tr, st in SET:
        d = wfa(cs, n, tr, st, 'cum')
        row(lab + ' (결함:누적)', d)
    print()
    print('  ★ 위 [3] 이 보여주듯 **ext 엔진에서는 결함판도 −0.16 을 고른다.**')
    print('    누적 선택의 폐해(초기 데이터가 영원히 지배)는 실재하지만, 이 자료에서')
    print('    **선택 중앙값을 뒤집을 만큼은 아니었다.**')

    print()
    print(L)
    print('[4] ⓐ 반증 — 정정판이 「−16」을 냈으므로 무조건 흔들어 본다')
    print(L)
    print('  선택 지표를 최종배수 -> **Calmar** 로 바꾸면? (같은 창·같은 격자)')
    print('  %-18s%8s%10s%10s%11s%9s%9s   %s'
          % ('설정', '걸음수', '선택 중앙', '−18~−14', '−16 정확히', '고정승', '무승부포함', '선택 범위'))
    for lab, tr, st in SET:
        row(lab + ' (Calmar)', wfa(cs, n, tr, st, 'window', metric='calmar'))
    print()
    print('  훈련 길이를 촘촘히 흔들면? (걸음 3년 고정 · 최종배수)')
    print('  %-10s%12s%12s%12s' % ('훈련', '선택 중앙', '−16 정확히', '고정 승'))
    meds = []
    for tr in (6, 8, 10, 12, 14, 16, 18, 20):
        d = wfa(cs, n, tr, 3, 'window')
        meds.append(d['med'])
        print('  %-10s%12.2f%11.0f%%%11.0f%%' % ('%d년' % tr, d['med'], 100 * d['exact'],
                                                 100 * d['fixwin']))
    print()
    print('  -> 훈련 길이 8종의 선택 중앙값: %s' % ' · '.join('%.2f' % m for m in meds))
    print('     %d/%d 에서 −0.16. 훈련 길이를 바꿔도 답이 유지되면 강건, 흔들리면 우연이다.'
          % (sum(1 for m in meds if abs(m + 0.16) < 0.005), len(meds)))

    print()
    print(L)
    print('읽는 법 · 한정')
    print(L)
    print('  · 이 검사가 답하는 것은 **「그 시점 자료만으로 골랐다면 무엇이 나왔나」**뿐이다.')
    print('    「−16 이 최적이다」는 여기서 나오지 않는다 — 사전 등록한 그대로다.')
    print('  · 걸음 수가 10~15회뿐이다(54년 ÷ 3~5년). **비중첩 관측이 그만큼밖에 없다** —')
    print('    「고정 승 73%」를 확률로 읽지 마라. 11회 중 8회라는 뜻이다.')
    print('  · [3] 이후는 **ext 엔진**(1972~ · 방어 40/40/20 · B 공표 217,110배 재현 검산 통과)')
    print('    으로 돈다. ndx 엔진(1985~ · 방어=현금)은 문서 대조용으로만 썼다.')
    print('  · **답이 엔진에 의존한다는 사실 자체가 결과다** — [3] 참조. 문턱 결론을 인용할 땐')
    print('    「어느 엔진으로 쟀는가」를 반드시 같이 적어라(§-1 ④).')


if __name__ == '__main__':
    main()
