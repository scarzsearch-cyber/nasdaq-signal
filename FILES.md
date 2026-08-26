# 파일 분류 (2026-08-26 정리)

전체 파일을 4분류하고 이동·삭제를 마쳤다. 루트에는 **1·2번만** 남아 있다.

---

## 1. 최종 실전 운용에 필요한 파일 — 건드리지 말 것

매일 자동으로 도는 라이브 파이프라인이다.

| 파일 | 역할 |
|---|---|
| `signal.html` | GitHub Pages 로 서비스되는 신호 뷰어. **−16/−16 · −16/−11 선택 + 방어자산 2안 토글**. 도피 상태에서 바스켓 비중·종목코드 표시. **한국 공휴일 반영 시계** |
| `deploy/update_signal.py` | 매일 QQQ 종가 받아 **두 규칙을 모두** 판정 → `data/signal.json` 갱신 |
| `deploy/build_stats.py` | 화면에 띄울 Calmar·MDD·Sortino 를 미리 계산 → `data/strategy_stats.json`. **방어자산 2안(v23 바스켓 / v21 배당100)을 둘 다 계산.** **매일 돌지 않음**(로컬 수동) |
| `deploy/nav_collect.py` | **실측 NAV 수집기** (네이버 전종목 NAV). daily-signal.yml 이 매일 한 줄씩 적립. `--report` 로 괴리율 |
| `data/nav_history.csv` | 적립되는 실측 NAV·괴리율 시계열 |
| `deploy/kr_holidays.py` | **한국 증시 휴장일 생성기** (음력 직접 계산 + KOSPI 실측 대조). `--emit` 로 `data/kr_holidays.json` 생성. **매일 돌지 않음**(로컬 수동) |
| `data/kr_holidays.json` | 2026~2032 휴장일 110일. `signal.html` 시계가 읽는다 |
| `deploy/README.md` | 배포 구조 설명 |
| `.github/workflows/daily-signal.yml` | 매일 신호 갱신 자동 실행 |
| `.github/workflows/pages.yml` | 갱신 후 Pages 재배포 |
| `data/signal.json` | 뷰어가 읽는 현재 상태 (두 전략 + 성과지표 + 위기 궤적) |
| `data/strategy_stats.json` | 두 전략 × 4개 기준의 성과지표. `build_stats.py` 산출물 |
| `data/qqq.csv` | 라이브 파이프라인용 QQQ 시계열 |
| `.gitignore` | — |

`build_stats.py` 는 루트의 `hist_*.py` / `reentry_lib.py` / `data/hist/**` 에 의존한다.
즉 **2번 파일들이 없으면 성과지표를 다시 만들 수 없다** — 그래서 루트 스크립트를 지우면 안 된다.
신호 판정 자체는 `update_signal.py` 만으로 돌아간다.

---

## 2. 현재 최종 검증에 필요한 파일 — 루트 유지

### 2-1. 엔진·원자료 (전부가 이것에 의존)

| 파일 | 역할 |
|---|---|
| `reentry_lib.py` | **공용 엔진.** 데이터 생성·체결(`pos = w.shift(1)`)·비용 규약의 단일 원천 |
| `verify.py` | 채택안(−16/−11) 기준 재현. 138.2배 검산 |
| `hist_data.py` | **1972–2026 확장 데이터 빌더.** Composite→NDX→QQQ 3구간 접합 |
| `hyst_core.py` | A/B 전략 정의 + 요약 테이블 (여러 스크립트가 import) |
| `qqq_us_d.csv` `qld_us_d.csv` `schd_us_d.csv` | 미국 ETF 수정주가 원자료 |
| `data/hist/**` | FRED·Yahoo·French·KRX 원자료 (아래 상세) |

### 2-2. 방어자산 실측화 (과제 ①④ / v21 §2·§3)

| 파일 | 역할 |
|---|---|
| `hist_defensive.py` | French BE/ME·D/P 파서, 자율규약1 일간화, `build(kind)` 로 방어자산 교체 |
| `hist_divetf.py` | 실물 배당 ETF(DVY/VYM/SDY) 교차검증, 자율규약2 배당체인 |
| `hist_defrun.py` | 방어자산 4안별 A vs B 재판정, SCHD 피신 vs 현금 피신 |
| `hist_defchain.py` | 배당체인 적용 후 최종 A vs B |
| `hist_defdiag.py` | MDD 발생 위치 추적, 방어자산 위기별 성과 |

### 2-3. QQQ 신호 vs QLD 신호 (v21 §5)

| 파일 | 역할 |
|---|---|
| `hyst_signal.py` | 9개 후보 3구간 비교, QLD 진입선 Plateau 검증 |
| `hyst_sigwfa.py` | 신호 계열별 WFA — QQQ 122.74배 vs QLD 41.04배 |

### 2-4. −16/−16 vs −16/−15 vs −16/−11 (v21 §11)

| 파일 | 역할 |
|---|---|
| `hist_three.py` | **3자 비교 전체.** Kelly f*, 조건부 f*, 회색지대 분해, 톱니, 위기, WFA, 비용 |
| `전략_v21_3자비교_raw.txt` | 위 스크립트 원본 출력 (표 수치의 출처) |

### 2-5. 고정 WFA / OOS

| 파일 | 역할 |
|---|---|
| `hyst_wfa.py` | 연속상태 워크포워드 (복귀선 격자 −16%~−6%) |
| `hyst_wfa.csv` | 그 출력 |
| `fixed_wfa_hist.csv` | 3자 고정 WFA 결과 (1972~, 50창). **생성 스크립트가 없어 재현 불가 → 반드시 보존** |

### 2-6. 실제 한국 ETF 적용 (과제 ③ / v21 §4)

| 파일 | 역할 |
|---|---|
| `hist_korea.py` | KRX 실거래일 달력 매핑, 원화 환산, 한국 체결 엔진 |
| `hist_tiger.py` | TIGER 3종 추적오차·시초가 갭 실측 |
| `hist_krfinal.py` | 환노출 2배 구조 반영 최종 원화 시뮬레이션 |
| `hist_krreal.py` | **2023-06-20~ 실물 TIGER 시가 체결 검증** (2025-04 자연실험) |
| `hist_krtax.py` | **세금·계좌 반영 A vs B** (v21 §13). 계좌 선택이 규칙 선택보다 4배 크다는 결론의 출처 |

### 2-6B. [v22 신규] 새 축 탐색 — 배수 · 앙상블 · 적립식

v18~v21 이 전부 「전환 타이밍」 축 하나 위에 있었다는 것을 확인하고 다른 축 3개를 연다.
전부 `reentry_lib` 규약을 그대로 쓰고, 시작 시 `axis_lib.check()` 로 오차 0 을 검산한다.

| 파일 | 역할 |
|---|---|
| `axis_lib.py` | **v22 공용 엔진.** `rule_w` / `lev_r`(배수 합성) / `sim` / `accumulate`(적립식) / `after_tax*`(계좌) / `check` |
| `axis_lev.py` | **축1 리스크온 배수.** 격자 + 관문 8종(지연·비용·구간·위기·꼬리·롤링) + 계좌 상쇄 |
| `axis_ens.py` | 축2 파라미터 앙상블 (기각 근거) |
| `axis_accum.py` | 축3 적립식 + **QLD Dip Alert 형 매수 타이밍 검증** |
| `전략_v22_raw.txt` | 위 3개 스크립트 원본 출력 (전략_v22.md 표 수치의 출처) |

### 2-6C. [v23 신규] 방어자산 위기유형 분산 — 국채 · 금

v22 §5.1 이 최우선 과제로 지목한 것. 방어자산을 배당 100% 에서 3자 바스켓으로 바꾼다.

| 파일 | 역할 |
|---|---|
| `hist_fetch.py` | **원자료 다운로더.** Yahoo ^TNX/^TYX/IEF/TLT/GLD/GC=F + LBMA 금 + KRX 6종(거래대금 포함) |
| `hist_defasset.py` | 상수만기 국채 총수익 합성(파 채권 완전재평가) + 금 + 실물 교차검증 + `MIX_V23`·`MIX_LEGS` 정의 |
| `axis_krspec.py` | **국내 상품 사양 실측** — 환노출 여부·실효 듀레이션 주간회귀 + 교차검증. 표기가 아니라 가격으로 확인한다 |
| `axis_krspread.py` | 괴리율 상한·시초가 갭·일중 되돌림·모형 대비 이탈 (v24 §3) |
| `axis_accum2.py` | **적립식 재검증** — 납입 규약 6종(고정·불규칙·거르기·몰아넣기·추격·역추격) x 롤링 3창 + 최소 월납입 계산 |
| `전략_v26_raw.txt` | 위 스크립트 원본 출력 |
| `axis_sigsrc.py` | **신호원 판정** — 미국 QQQ 종가 vs 원화환산 vs 국내 실물 ETF vs 1일지연. 체결 고정, 신호원만 교체 |
| `전략_v28_raw.txt` | 위 스크립트 원본 출력 |
| `axis_defsel.py` | **방어자산 동적 선택 — 기각.** 선택규칙 11종 x 관문 5개(예측력·적중·첨탑·플라시보·워크포워드). 무작위 대조 200회 |
| `전략_v27_raw.txt` | 위 스크립트 원본 출력 |
| `axis_vrhybrid.py` | **VR 밴드 리밸런싱 하이브리드 — 기각.** 롤링 15년 승률 0.2%, 87 톱니 MDD 개선 0.00 |
| `전략_vr하이브리드_raw.txt` | 위 스크립트 원본 출력 |
| `axis_defmix.py` | **본 판정 전체.** 진단·상관·후보 14종·MDD분해·재조정규약·관문·가중치평지·원화·국내실물·유동성. `check_hold()` 가 규약 검산 |
| `전략_v23_raw.txt` | 위 스크립트 원본 출력 (전략_v23.md 표 수치의 출처) |

### 2-7. 문서 (읽기용, 루트 유지)

| 파일 | 역할 |
|---|---|
| `전략_v28.md` | **최신.** 신호원은 미국 QQQ 종가 — 국내 종가로 재면 1997- −92%, MDD +21%p |
| `전략_v27.md` | 방어 안에서의 선택 기각 + 월간 재조정 비용 버그 정정. 분산 자체가 알파 |
| `전략_v26.md` | 적립식 재검증 — 불규칙 납입도 순위 불변. 실무 최소 월납입 15만원 |
| `전략_v25.md` | 남은 과제 3건 완결 — 실측 괴리율·레버리지 검증·제헌절. **v24 §3.3/§3.4 정정** |
| `전략_v24.md` | 상품 사양 실측·공휴일. §3.3/§3.4 는 v25 에서 정정됨 |
| `전략_v23.md` | **채택안.** 방어자산 = 배당40 / 미국채40 / 금20 (전부 국내 상장·환노출) |
| `전략_v22.md` | 새 축 3개 판정 — 배수(조건부) / 앙상블(기각) / 적립식(현행 강화) |
| `전략_v21.md` | **현행 채택안의 근거.** 방어자산 실측화 + 한국 실전 + 3자 비교 |
| `전략_v20.md` | 54년 확장·히스테리시스. §11.11 이 인용하는 유의성 통계의 출처 |
| `전략_v19.md` | 복귀로직 294+576개 전부 기각 기록 |
| `전략_v18.md` | 진입선 45개 변형 기각 + 기본 규약 정의 |
| `HANDOFF.md` | 다음 세션 인수인계 |
| `FILES.md` | 이 문서 |

### 2-8. `data/hist/` 상세

| 파일 | 출처 | 쓰는 곳 |
|---|---|---|
| `fred_NASDAQCOM.csv` `yahoo_NDX.csv` | FRED / Yahoo | `hist_data.py` 1972~1999 구간 |
| `fred_NASDAQ100.csv` `yahoo_IXIC.csv` | FRED / Yahoo | `hist_data.crosscheck()` 출처 대조 |
| `fred_DTB3.csv` | FRED | T-bill 방어자산 (과제④) |
| `fred_DEXKOUS.csv` | FRED | 원달러 (과제③) |
| `ff_*.zip` + `ff_tmp/*.csv` | Kenneth French | 배당·가치 방어자산 (과제①). zip 은 백업, `ff_tmp` 가 실제 읽는 파일 |
| `yahoo_TNX/TYX.csv` | Yahoo | 미 10Y·30Y 국채금리 (v23). FRED 접속 차단 대체 |
| `yahoo_IEF/TLT.csv` | Yahoo | 합성 국채 교차검증 (v23) |
| `lbma_gold_pm.csv` | LBMA | 금 런던 오후 고시 1968~ (v23) |
| `yahoo_GLD/GCF.csv` | Yahoo | 금 교차검증 (v23) |
| `kr_132030/411060/305080/308620/453850/148070_KS.csv` | Yahoo | 국내 상장 금·국채 ETF + 거래대금 (v23) |
| `yahoo_DVY/VYM/SDY/SPY.csv` | Yahoo | 2008년 방어자산 낙폭 실측 |
| `kr__5EKS11.csv` | Yahoo `^KS11` | KRX 실거래일 달력 |
| `kr_133690/418660/458730_KS.csv` | Yahoo | TIGER 3종 시가·종가 |

---

## 3. 보관만 하는 파일 → `archive/` 로 이동 완료

| 이동 위치 | 파일 수 | 내용 |
|---|---:|---|
| `archive/v19_복귀로직/` | 13 | `reentry_cd/edge/final/grid/plateau/staged/vshape/wfa.py` + 결과 CSV 5개 |
| `archive/v20_히스테리시스/` | 11 | `hyst_decomp/episodes/focus/mdd/mech/robust/signif.py` + 결과 CSV 4개 |
| `archive/지시프롬프트/` | 3 | `복귀로직_연구프롬프트.md`, `제미나이.md`, `제미나이2.md` |

전부 **결론이 상위 문서에 흡수돼 다시 돌릴 필요가 없다.** 다만 "왜 기각됐는가"의
근거가 여기에만 있으므로 삭제하지 않았다. 실행이 필요하면 루트에서:

```bash
PYTHONPATH=. python archive/v20_히스테리시스/hyst_mech.py
```

---

## 4. 삭제한 파일

| 파일 | 이유 |
|---|---|
| `__pycache__/` (152KB) | 재생성됨. `.gitignore` 에도 이미 등록 |
| `data/hist/kr_195930_KS.csv` | TIGER 유로스탁스50. 티커 탐색 중 잘못 받은 것으로 이 전략과 무관 |

**그 외에는 아무것도 지우지 않았다.** 특히 다음은 "중복처럼 보이지만" 보존했다.

- `fixed_wfa_hist.csv` — 생성 스크립트가 없어 재현 불가
- `hyst_wfa.csv` — `fixed_wfa_hist.csv` 와 격자·형식이 달라 중복 아님
- `data/hist/ff_*.zip` — `ff_tmp/` 가 유실될 경우의 복구원본 (2MB)
- `data/hist/fred_NASDAQ100.csv`, `yahoo_IXIC.csv` — 출처 교차검증에 실제로 쓰임

---

## 검증

정리 후 루트 16개 스크립트 **전부 재실행 성공**, 아카이브 스크립트도 `PYTHONPATH=.` 로 정상 동작.
`verify.py` 는 여전히 채택안 곡선을 재현한다.

```bash
for f in verify.py hist_*.py hyst_*.py; do python "$f" > /dev/null && echo "OK $f"; done
```
