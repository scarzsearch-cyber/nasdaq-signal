#!/usr/bin/env python3
"""
매일 QQQ 종가를 받아 신호를 계산하고 data/signal.json 을 갱신한다.
GitHub Actions에서 매일 자동 실행된다. 로컬에서 수동 실행도 가능:  python3 deploy/update_signal.py
"""
import json, os, sys, io
import datetime
import urllib.request
import pandas as pd
import numpy as np

ENTER, EXIT, LOOKBACK = -0.16, -0.11, 252
# stooq.com이 자동화 요청을 JS 챌린지로 차단해 Yahoo Finance chart API로 대체.
SRC = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ"
OUT_DIR = "data"
CSV_PATH = os.path.join(OUT_DIR, "qqq.csv")
JSON_PATH = os.path.join(OUT_DIR, "signal.json")

# 과거 4대 위기 (궤적 비교용) — 고점일 기준
CRISES = [
    ("닷컴 2000",  "2000-03-27"),
    ("GFC 2007",   "2007-10-31"),
    ("코로나 2020", "2020-02-19"),
    ("2022 베어",   "2021-11-19"),
]


def fetch():
    period1 = int(datetime.datetime(1999, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    period2 = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    url = f"{SRC}?period1={period1}&period2={period2}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = json.loads(r.read().decode("utf-8", "replace"))
    result = raw["chart"]["result"][0]
    ts = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    s = pd.Series(closes, index=idx, name="Close").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_cached():
    if not os.path.exists(CSV_PATH):
        return None
    df = pd.read_csv(CSV_PATH, parse_dates=["Date"]).set_index("Date")["Close"]
    return df.sort_index()


def compute(px: pd.Series):
    roll_max = px.rolling(LOOKBACK, min_periods=60).max()
    dd = (px / roll_max - 1)
    state, cur = [], "QLD"
    for i in range(len(px)):
        d = dd.iloc[i]
        if pd.isna(d):
            state.append(cur); continue
        if cur == "QLD" and d <= ENTER:
            cur = "SCHD"
        elif cur == "SCHD" and d > EXIT:
            cur = "QLD"
        state.append(cur)
    return dd, roll_max, pd.Series(state, index=px.index)


def trajectories(px: pd.Series, dd: pd.Series, days=400):
    """각 위기의 고점 이후 낙폭 궤적 + 현재 진행중인 낙폭 궤적"""
    out = {}
    for name, peak in CRISES:
        seg = dd.loc[peak:].iloc[:days]
        if len(seg) > 20:
            out[name] = [round(float(v) * 100, 2) for v in seg.values]
    # 현재 궤적: 최근 252일 고점 이후
    cur_dd = dd.iloc[-1]
    if cur_dd < -0.03:
        rm = px.rolling(LOOKBACK, min_periods=60).max().iloc[-1]
        recent = px.iloc[-LOOKBACK:]
        hits = recent[recent >= rm * 0.9999]
        if len(hits):
            seg = dd.loc[hits.index[-1]:]
            if len(seg) > 3:
                out["현재"] = [round(float(v) * 100, 2) for v in seg.values[:days]]
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        px = fetch()
        source = "stooq"
    except Exception as e:
        print(f"[경고] 다운로드 실패({e}) — 캐시 사용", file=sys.stderr)
        px = load_cached()
        source = "cache"
        if px is None:
            raise

    cached = load_cached()
    if cached is not None:
        px = pd.concat([cached, px])
        px = px[~px.index.duplicated(keep="last")].sort_index()

    px.rename("Close").to_frame().to_csv(CSV_PATH, index_label="Date")

    dd, roll_max, state = compute(px)
    last_state = state.iloc[-1]
    prev_state = state.iloc[-2] if len(state) > 1 else last_state
    d = float(dd.iloc[-1])
    next_line = ENTER if last_state == "QLD" else EXIT

    payload = {
        "as_of": px.index[-1].strftime("%Y-%m-%d"),
        "updated_at": pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC"),
        "source": source,
        "close": round(float(px.iloc[-1]), 2),
        "high_252": round(float(roll_max.iloc[-1]), 2),
        "dd": round(d * 100, 2),
        "state": last_state,
        "changed_today": bool(last_state != prev_state),
        "prev_state": prev_state,
        "next_line": round(next_line * 100, 0),
        "gap_pp": round(abs(d - next_line) * 100, 1),
        "enter": ENTER * 100,
        "exit": EXIT * 100,
        "recent": [
            {"d": px.index[i].strftime("%Y-%m-%d"),
             "c": round(float(px.iloc[i]), 2),
             "dd": round(float(dd.iloc[i]) * 100, 2),
             "s": state.iloc[i]}
            for i in range(max(0, len(px) - 12), len(px))
        ][::-1],
        "trajectories": trajectories(px, dd),
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"{payload['as_of']}  종가 {payload['close']}  낙폭 {payload['dd']}%  →  {last_state}"
          + ("   *** 전환 신호 ***" if payload["changed_today"] else ""))


if __name__ == "__main__":
    main()
