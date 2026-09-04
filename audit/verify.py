"""
나스닥 레버리지 전환전략 v17 — 채택안 검증 재현 스크립트 (단일 파일)

사용: python3 verify.py            (qqq_us_d.csv, qld_us_d.csv, schd_us_d.csv 같은 폴더)

채택안: QQQ 252일 고점대비 낙폭 <= -16% -> SCHD 전량 / 낙폭 > -11% -> QLD 전량

⚠ [2026-09-05 전수 감사] 위 「채택안」은 **v17 시절의 규칙 A(−16/−11 · 방어 SCHD 단독)** 다.
   현행 동결 전략 B(−16/−16 · 방어 40/40/20)의 검산이 아니다 — 현행 검산은 `verify_all.py` I7·I11.
   이 파일은 v17 공표값(138.2배 / 140.0배)의 참조 구현으로만 남긴다.
"""
# --- [v39] 하위 폴더에서도 루트의 엔진·데이터를 그대로 쓴다 -------------------
# 이 3줄이 없으면 `python research/axis_isa.py` 가 import 와 data/ 경로를 못 찾는다.
# 폴더를 나눠도 실험에 지장이 없게 하는 장치다. 지우지 말 것.
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
# ---------------------------------------------------------------------------

import sys
import pandas as pd, numpy as np

ENTER, EXIT, LOOKBACK = -0.16, -0.11, 252
COST = 0.001   # 편도 0.1%
# SCHD 미상장(2011-10 이전) 구간의 피신처 수익 가정 (연율).
# 문서 수치는 2% 기준. --cash 0 으로 보수적(무이자) 확인 가능.
CASH_RATE = 0.02
if '--cash' in sys.argv:
    # [2026-09-04 코드리뷰] 종전엔 argv[i+1] 을 그대로 float() 에 넣어
    # `--cash` 가 마지막 인자면 IndexError, `--cash --grid` 면 ValueError 로
    # 아무 안내 없이 죽었다. 150행이 사용법을 인쇄하는데 강제하는 것이 없었다.
    _i = sys.argv.index('--cash') + 1
    try:
        CASH_RATE = float(sys.argv[_i]) / 100
    except (IndexError, ValueError):
        sys.exit('--cash 뒤에는 연 이자율(%)을 숫자로 적어야 합니다. 예: --cash 2')

def load(p):
    df = pd.read_csv(p, parse_dates=['Date']).set_index('Date').sort_index()
    return df['Close']

qqq, qld, schd = load('qqq_us_d.csv'), load('qld_us_d.csv'), load('schd_us_d.csv')

# --- QLD를 QQQ의 2배로 1999년까지 합성 확장 (겹치는 구간에서 일일비용 역산) ---
qqq_r, qld_r = qqq.pct_change(), qld.pct_change()
ov = qqq_r.index.intersection(qld_r.index); ov = ov[ov >= '2006-06-22']
x, y = qqq_r.reindex(ov).dropna(), qld_r.reindex(ov).dropna()
cm = x.index.intersection(y.index); x, y = x.reindex(cm), y.reindex(cm)
c_daily = (2*x - y).mean()
pre = qqq_r.index[qqq_r.index < '2006-06-22']
synth = (2*qqq_r.reindex(pre) - c_daily).dropna()
full = pd.concat([synth, y]); full = full[~full.index.duplicated()].sort_index()
qld_ext = (1+full).cumprod()

IDX = qqq.index.intersection(qld_ext.index).sort_values()
IDX = IDX[IDX >= '2000-01-03']
qqqx = qqq.reindex(IDX)
dd = (qqqx / qqqx.rolling(LOOKBACK, min_periods=60).max() - 1).fillna(0)
qldr = qld_ext.reindex(IDX).pct_change().fillna(0)
# SCHD 미상장(2011-10 이전)은 현금(CASH_RATE)으로 대용
schdr = schd.reindex(IDX).pct_change().fillna(CASH_RATE/252)

def run(enter=ENTER, exit_=EXIT):
    st, cur, events = [], 'QLD', []
    for i in range(len(IDX)):
        if cur == 'QLD' and dd.iloc[i] <= enter:
            cur = 'SCHD'; events.append((IDX[i], 'SCHD'))
        elif cur == 'SCHD' and dd.iloc[i] > exit_:
            cur = 'QLD'; events.append((IDX[i], 'QLD'))
        st.append(cur)
    s = pd.Series(st, index=IDX); ex = s.shift(1)
    # [2026-09-04 코드리뷰] 종전엔 `sw = (ex != ex.shift(1)).fillna(False)` 였다.
    # ex[0]·ex.shift(1)[0..1] 이 NaN 인데 **pandas 에서 NaN != NaN 은 True** 라
    # 전환이 0회인 경로에서도 i=0,1 에 비용이 두 번 붙었다(실측 sw.sum()==2).
    # object dtype 비교라 결과가 NaN 이 아니므로 .fillna(False) 는 한 번도 안 먹었다.
    # 엔진 규약(axis_lib.sim)은 np.diff(pos, prepend=pos[0]) 로 첫날 회전을 0 으로
    # 둔다 — 여기도 같게 맞춘다. 첫 두 칸을 False 로 박으면 전환 횟수(events)와
    # 비용을 무는 날의 수가 다시 일치한다.
    sw = (ex != ex.shift(1)) & ex.notna() & ex.shift(1).notna()
    r = np.where(ex.values == 'QLD', qldr.values, schdr.values)
    r = np.nan_to_num(r); r[0] = 0
    g = np.where(sw.values, (1+r)*(1-COST), 1+r)
    return pd.Series(np.cumprod(g), index=IDX), events, s

def met(c):
    yrs = (c.index[-1]-c.index[0]).days/365.25
    cagr = c.iloc[-1]**(1/yrs)-1
    mdd = (c/c.cummax()-1).min()
    ret = c.pct_change().dropna(); vol = ret.std()*np.sqrt(252)
    return dict(final=c.iloc[-1], cagr=cagr, mdd=mdd, calmar=cagr/abs(mdd),
                sharpe=(ret.mean()*252)/vol, years=yrs)

curve, events, states = run()
m = met(curve)

print("="*78)
print(f"  채택안: QQQ 낙폭 <= {ENTER*100:.0f}% -> SCHD  /  낙폭 > {EXIT*100:.0f}% -> QLD")
print(f"  기간: {IDX[0].date()} ~ {IDX[-1].date()} ({m['years']:.1f}년)")
print("="*78)
print(f"  최종배수 {m['final']:.1f}배 | CAGR {m['cagr']*100:.1f}% | MDD {m['mdd']*100:.1f}% "
      f"| Calmar {m['calmar']:.3f} | Sharpe {m['sharpe']:.2f}")
print(f"  전환 {len(events)}회 (연 {len(events)/m['years']:.1f}회)")

qld_only = (1+qldr).cumprod(); mq = met(qld_only)
qqq_only = (1+qqqx.pct_change().fillna(0)).cumprod(); mn = met(qqq_only)
print(f"\n  [대조] QLD 계속보유: {mq['final']:.1f}배 CAGR {mq['cagr']*100:.1f}% MDD {mq['mdd']*100:.1f}%")
print(f"  [대조] QQQ 계속보유: {mn['final']:.1f}배 CAGR {mn['cagr']*100:.1f}% MDD {mn['mdd']*100:.1f}%")

print("\n" + "-"*78)
print("  위기 구간별 성적")
print("-"*78)
per = {"닷컴 2000-2002":('2000-01-01','2002-12-31'), "GFC 2007-2009":('2007-10-01','2009-03-31'),
       "코로나 2020":('2020-02-01','2020-04-30'), "2022 베어":('2022-01-01','2022-12-31')}
print(f"  {'구간':18s}{'채택안':>10s}{'QLD보유':>11s}{'QQQ보유':>11s}")
for k,(s,e) in per.items():
    def seg(c):
        z = c.loc[s:e]; return (z.iloc[-1]/z.iloc[0]-1)*100
    print(f"  {k:18s}{seg(curve):9.1f}%{seg(qld_only):10.1f}%{seg(qqq_only):10.1f}%")

print("\n" + "-"*78)
print("  전환 이력")
print("-"*78)
for d,s in events:
    print(f"  {d.date()}  ->  {s}")
print(f"\n  현재 상태: {states.iloc[-1]}  (낙폭 {dd.iloc[-1]*100:.1f}%)")

if '--grid' in sys.argv:
    print("\n" + "-"*78)
    print("  진입 문턱 스윕 (복귀는 진입+5%p, 5점이동평균으로 평지 확인)")
    print("-"*78)
    print(f"  {'진입':>7s}{'전환':>6s}{'최종배수':>11s}{'CAGR':>8s}{'MDD':>9s}")
    fs=[]
    grid=[round(-0.10-0.005*i,3) for i in range(21)]
    for de in grid:
        c,ev,_ = run(de, round(de+0.05,3)); mm = met(c); fs.append(mm['final'])
        print(f"  {de*100:6.1f}%{len(ev):6d}{mm['final']:10.1f}x{mm['cagr']*100:7.1f}%{mm['mdd']*100:8.1f}%")
    print("\n  5점이동평균:", " ".join(f"{np.mean(fs[max(0,i-2):i+3]):.0f}x" for i in range(len(fs))))

if '--rolling' in sys.argv:
    print("\n" + "-"*78)
    print("  롤링윈도우: 채택안 vs QLD보유 / QQQ보유")
    print("-"*78)
    a,b,c_ = curve.values, qld_only.values, qqq_only.values
    for W in [1,3,5,10,15]:
        n=W*252
        if n>=len(IDX): continue
        w1=w2=0; tot=0; cg=[]
        for s in range(0,len(IDX)-n,5):
            e=s+n; p=a[e-1]/a[s]
            if p>b[e-1]/b[s]: w1+=1
            if p>c_[e-1]/c_[s]: w2+=1
            cg.append(p**(252/n)-1); tot+=1
        print(f"  {W:2d}년: QLD보유 대비 승률 {w1/tot*100:3.0f}% | QQQ보유 대비 {w2/tot*100:3.0f}% "
              f"| CAGR 중앙값 {np.median(cg)*100:5.1f}% 최악 {min(cg)*100:6.1f}%")

if '--lag' in sys.argv:
    print("\n" + "-"*78)
    print("  체결 지연 민감도")
    print("-"*78)
    for lag in [1,2,3,5]:
        s = states.shift(lag)
        sw = (s != s.shift(1)) & s.notna() & s.shift(1).notna()   # [코드리뷰] run() 과 같은 규약
        r = np.where(s.values=='QLD', qldr.values, schdr.values); r=np.nan_to_num(r); r[0]=0
        g = np.where(sw.values,(1+r)*(1-COST),1+r)
        mm = met(pd.Series(np.cumprod(g),index=IDX))
        print(f"  {lag}일 지연: {mm['final']:7.1f}배  CAGR {mm['cagr']*100:5.1f}%  MDD {mm['mdd']*100:6.1f}%")

print("\n  옵션: --grid  --rolling  --lag  --cash <연%>\n")
