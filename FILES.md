# 파일 분류

> **먼저 `전략_요약.md`(지도) → `01_Strategy_Logic.md` 를 읽으세요.** 그 다음이 `README.md` 입니다.
> [v65] 버전 문서 43개는 `docs/history/` 로 이동했고, 현행 내용은 루트의 `01~04_*.md` 에 통합됐습니다.
> 이 파일은 스크립트별 상세 목록입니다.

## 폴더 구조 (2026-08-27 v39 정리)

```
전략_요약.md            ★ 이것부터. 전략·근거·결론 5분 요약
README.md               전략·자동화·파일지도·오류원인·체크리스트
HANDOFF.md              작업 시작 전 읽을 것 (하지 마라 목록)
CLAUDE.md               AI 세션 자동 로드 규칙 — 수정 금지 목록·작업 규약 (v128)
FILES.md                이 파일

verify_all.py           ★ 검증 단일 진입점 —  python verify_all.py
research_kit.py         새 분석용 도구 (설계 오류를 API 에서 차단)
signal.html             화면 전부

── 공용 엔진 (루트, 12개) — 고치면 사용처 전부 재실행 ──
reentry_lib.py          체결·비용 규약의 단일 원천
axis_lib.py             rule_w / sim / accumulate / lev_r / check
axis_defmix.py          materials / sim_hold / check_hold
axis_volguard.py        zc / exp_q (변동성 유틸)
hist_data.py            1972- 나스닥 3구간 접합
hist_defensive.py       배당체인 build()
hist_defasset.py        ust_tr / gold_r / mix_monthly
hist_korea.py           한국 거래일 체결
hist_krfinal.py         원화 환산
hist_krreal.py          실물 TIGER 시가 체결
hist_divetf.py          배당 ETF 교차검증
hist_tiger.py           국내 ETF 원자료
hyst_core.py            A/B 전략 정의
qqq/qld/schd_us_d.csv   미국 ETF 원자료

audit/      (4)  audit_all · audit_full · verify · verify_volguard
research/   (56) 기각 판정의 재현 코드 + build_crisis_paths.py(v127 화면 데이터 생성 —
            예외적으로 산출물 data/crisis_paths.json 이 배포됨). 각 파일 상단에 경로보정 3줄
deploy/     라이브 파이프라인 — 건드리지 말 것
data/       화면이 읽는 것 — 워크플로 소유 (freeze.json · oos_log.csv 포함)
docs/       history/(56 — 전략_v18~v83 보관층) · raw/ · HANDOFF_전체이력
archive/    (4)  v19~v20 폐기본
```

### 폴더를 나눠도 실험에 지장 없다

`audit/` 와 `research/` 의 모든 파일 상단에 **경로 보정 3줄**이 들어 있다:

```python
import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_sys.path.insert(0, _ROOT); _os.chdir(_ROOT)
```

이 3줄이 루트를 `sys.path` 에 넣고 작업 디렉터리를 루트로 옮긴다. 그래서
`python research/axis_isa.py` 든 다른 폴더에서 절대경로로 부르든 **똑같이 돈다.**
루트 엔진 import 도, `data/hist/...` 상대경로도 그대로 작동한다.
검증 완료: `audit/verify.py`, `research/axis_krspec.py`, `research/hyst_wfa.py` 를
임의 폴더에서 실행해 정상 동작 확인.

**새 연구 스크립트를 만들 때도 이 3줄을 복사해 넣으면 된다.**

---

아래는 스크립트별 상세다. (2026-08-26 분류 + v37 정리 반영)

---

## 1. 최종 실전 운용에 필요한 파일 — 건드리지 말 것

매일 자동으로 도는 라이브 파이프라인이다.

| 파일 | 역할 |
|---|---|
| `signal.html` | GitHub Pages 로 서비스되는 신호 뷰어. **−16/−16 단일 규칙**(A 선택지는 v61 에서 화면 제거). 내 포트폴리오·체결 기록·계산기·백업(파일/CSV)·다크 모드까지 화면 전부 (v103, 기구현 목록은 CLAUDE.md §4). **한국 공휴일 반영 시계** |
| `deploy/update_signal.py` | 매일 QQQ 종가 받아 **두 규칙을 모두** 판정 → `data/signal.json` 갱신 |
| `deploy/refresh_hist.py` | [v72] 월 1회 원자료 11종 연장 (append-only · 비율 이음 · 장중 가드) |
| `deploy/data_check.py` | [v73] 데이터 검증 게이트 — 이상 데이터가 정상 데이터를 덮어쓰지 못하게 |
| `deploy/notify.py` | [v73/v77] 실패·전환 알림 (카카오톡/Discord/Telegram, GitHub Secrets) |
| `deploy/kakao_setup.py` | [v77] 카카오 알림 최초 1회 설정 (본인 PC에서 실행) |
| `deploy/kakao_keepalive.py` | [v77] 카카오 refresh 토큰 매일 연명·자동 교체 |
| `deploy/signal_alert.py` | [v76] 전환 신호일 폰 알림 |
| `deploy/build_stats.py` | 화면에 띄울 Calmar·MDD·Sortino 를 미리 계산 → `data/strategy_stats.json`. **방어자산 2안(v23 바스켓 / v21 배당100)을 둘 다 계산.** **매일 돌지 않음**(로컬 수동) |
| `deploy/nav_collect.py` | **실측 NAV 수집기** (네이버 전종목 NAV). daily-signal.yml 이 매일 한 줄씩 적립. `--report` 로 괴리율 |
| `data/nav_history.csv` | 적립되는 실측 NAV·괴리율 시계열 |
| `deploy/kr_holidays.py` | **한국 증시 휴장일 생성기** (음력 직접 계산 + KOSPI 실측 대조). `--emit` 로 `data/kr_holidays.json` 생성. **매일 돌지 않음**(로컬 수동) |
| `data/kr_holidays.json` | 2026~2032 휴장일 110일. `signal.html` 시계가 읽는다 |
| `manifest.json` · `icon-192/512.png` | [v104] PWA 홈 화면 추가 (standalone). **pages.yml 복사 목록 필수** — verify_all 이 검사한다 |
| `deploy/README.md` | 배포 구조 설명 |
| `.github/workflows/daily-signal.yml` | 매일 신호 갱신 자동 실행 |
| `.github/workflows/pages.yml` | 갱신 후 Pages 재배포 |
| `data/signal.json` | 뷰어가 읽는 현재 상태 (두 전략 + 성과지표 + 위기 궤적) |
| `data/strategy_stats.json` | 두 전략 × 4개 기준의 성과지표. `build_stats.py` 산출물 |
| `data/crisis_paths.json` | 위기 타임머신(v127) 데이터 — 위기 4구간의 전략/2배보유 계좌가치 경로. `research/build_crisis_paths.py` 산출물, **로컬 수동 실행**(build_stats 와 같은 포지션 — 원자료 갱신 시 재실행) |
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
| `docs/raw/전략_v21_3자비교_raw.txt` | 위 스크립트 원본 출력 (표 수치의 출처) |

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
| `docs/raw/전략_v22_raw.txt` | 위 3개 스크립트 원본 출력 (전략_v22.md 표 수치의 출처) |

### 2-6C. [v23 신규] 방어자산 위기유형 분산 — 국채 · 금

v22 §5.1 이 최우선 과제로 지목한 것. 방어자산을 배당 100% 에서 3자 바스켓으로 바꾼다.

| 파일 | 역할 |
|---|---|
| `hist_fetch.py` | **원자료 다운로더.** Yahoo ^TNX/^TYX/IEF/TLT/GLD/GC=F + LBMA 금 + KRX 6종(거래대금 포함) |
| `hist_defasset.py` | 상수만기 국채 총수익 합성(파 채권 완전재평가) + 금 + 실물 교차검증 + `MIX_V23`·`MIX_LEGS` 정의 |
| `axis_krspec.py` | **국내 상품 사양 실측** — 환노출 여부·실효 듀레이션 주간회귀 + 교차검증. 표기가 아니라 가격으로 확인한다 |
| `axis_krspread.py` | 괴리율 상한·시초가 갭·일중 되돌림·모형 대비 이탈 (v24 §3) |
| `axis_accum2.py` | **적립식 재검증** — 납입 규약 6종(고정·불규칙·거르기·몰아넣기·추격·역추격) x 롤링 3창 + 최소 월납입 계산 |
| `docs/raw/전략_v26_raw.txt` | 위 스크립트 원본 출력 |
| `audit_full.py` | **전수조사** — 59개 파일 AST 파싱 + **시점별 재계산**(미래참조 결정적 검사). 정기 실행 |
| `docs/raw/전략_v35_raw.txt` | 위 스크립트 원본 출력 |
| `audit_all.py` | **전면 감사** — 엔진정합·미래참조·데이터무결성·채택결정 재검증·공표수치 대조. 정기적으로 돌릴 것 |
| `docs/raw/전략_v34_raw.txt` | 위 스크립트 원본 출력 |
| `verify_volguard.py` | **검증 관문 6종** — 엔진 정합·공표치 재현·미래참조·적립규약. v33 의 2일 지연 버그를 잡은 도구 |
| `docs/raw/전략_v33_raw.txt` | 위 스크립트 원본 출력 |
| `axis_volguard.py` | **변동성 조기방어 본판정** — 실제 40/40/20 바스켓·원화·A/B 두 규칙, 고정 vs 선택 대조. v31 기각을 취소시킨 근거 |
| `axis_macro4.py` | **격자 감사** — MDD 표면이 평지인지 확인(42칸), 프론티어 대조, 앙상블 |
| `docs/raw/전략_v32_raw.txt` | 위 두 스크립트 원본 출력 |
| `axis_macro3.py` | **v30 방법론 감사 + 남은 3축 종결** — 시차상관 정정(변화량), 분위누수 제거, 금리차·복귀필터·변동성 조기방어. **권장 진입점** |
| `docs/raw/전략_v31_raw.txt` | 위 스크립트 원본 출력 |
| `axis_macro.py` | **매크로·심리 지표 기각(2011-)** — VIX·하이일드·공포탐욕 조기경보 5관문. 체결규약 위반 시 부호가 뒤집히는 사례 |
| `axis_macro2.py` | **같은 판정을 1972- 로 확장** — 짧은 창에서 통과한 역발상이 닷컴에서 −51%p |
| `docs/raw/전략_v30_raw.txt` | 위 두 스크립트 원본 출력 |
| `axis_isa.py` | **ISA 세후 판정** — 과세이연/세율/비과세 4단계 분해 + 3년해지 비교. `--emit` 로 `data/isa_stats.json` |
| `docs/raw/전략_v29_raw.txt` | 위 스크립트 원본 출력 |
| `axis_sigsrc.py` | **신호원 판정** — 미국 QQQ 종가 vs 원화환산 vs 국내 실물 ETF vs 1일지연. 체결 고정, 신호원만 교체 |
| `docs/raw/전략_v28_raw.txt` | 위 스크립트 원본 출력 |
| `axis_defsel.py` | **방어자산 동적 선택 — 기각.** 선택규칙 11종 x 관문 5개(예측력·적중·첨탑·플라시보·워크포워드). 무작위 대조 200회 |
| `docs/raw/전략_v27_raw.txt` | 위 스크립트 원본 출력 |
| `axis_vrhybrid.py` | **VR 밴드 리밸런싱 하이브리드 — 기각.** 롤링 15년 승률 0.2%, 87 톱니 MDD 개선 0.00 |
| `docs/raw/전략_vr하이브리드_raw.txt` | 위 스크립트 원본 출력 |
| `axis_defmix.py` | **본 판정 전체.** 진단·상관·후보 14종·MDD분해·재조정규약·관문·가중치평지·원화·국내실물·유동성. `check_hold()` 가 규약 검산 |
| `docs/raw/전략_v23_raw.txt` | 위 스크립트 원본 출력 (전략_v23.md 표 수치의 출처) |

### 2-7. 문서 (읽기용, 루트 유지)

| 파일 | 역할 |
|---|---|
| `docs/history/전략_v64.md` | **최신.** 지표 풀이 네 줄 + 값에 강조색 · MDD 방향 표시 정정. **규칙 변경 없음** |
| `docs/history/전략_v63.md` | 같은 기간으로 맞춘 표 — 최근 5·10·15년은 2배 보유 승, 20년에서 뒤집힘 |
| `docs/history/전략_v62.md` | 지표를 「그래서 얼마냐」로 번역 + 체결 시각 모순 정정(v18 잔재) |
| `docs/history/전략_v61.md` | A(−16/−11) 화면 제거 + 지표에 눈금(2배 보유·방어 단독) |
| `docs/history/전략_v60.md` | 165 vs 2,761 분해(전부 그 3년) + 회복기간·Ulcer 화면 반영 |
| `docs/history/전략_v37.md` ~ `v59.md` | 기각 축 14차수 · 동결(v57) · 감사. §6 표 참조 |
| `docs/history/전략_v36.md` | 국채 다리 선물형 정정 — 드리프트 +2.84%→−0.18%. 채택 결정 유지, 공표수치 −18.6% |
| `docs/history/전략_v35.md` | 전수조사(59파일, HIGH 0건 · 시점별 재계산 0/40) + 라이브 종가 미갱신 수정 |
| `docs/history/전략_v34.md` | 전면 감사 — 채택 결정 전부 유지, 실패 0건. 남은 경고는 국채 롤 비용 1건 |
| `docs/history/전략_v33.md` | 적립 시뮬레이터 2일 지연 버그 정정 — v29 ISA +48.8%→+48.8%. 결론 불변 |
| `docs/history/전략_v32.md` | 변동성 조기방어 재심 — v31 기각근거 2개는 틀렸지만 **적립식에서 재기각**. 전략 변경 없음 |
| `docs/history/전략_v31.md` | v30 감사(근거 3개 정정) + 금리차·복귀필터·변동성 조기방어 기각. 전략 변경 없음 |
| `docs/history/전략_v30.md` | 매크로·심리 지표 전부 기각 — 동행지표라 새 정보가 없다. **v31 로 정정됨** |
| `docs/history/전략_v29.md` | ISA 서민형 세후 — 일반계좌 대비 +48.8%, 이득의 80%는 과세이연. 화면 반영 |
| `docs/history/전략_v28.md` | 신호원은 미국 QQQ 종가 — 국내 종가로 재면 1997- −92%, MDD +21%p |
| `docs/history/전략_v27.md` | 방어 안에서의 선택 기각 + 월간 재조정 비용 버그 정정. 분산 자체가 알파 |
| `docs/history/전략_v26.md` | 적립식 재검증 — 불규칙 납입도 순위 불변. 실무 최소 월납입 15만원 |
| `docs/history/전략_v25.md` | 남은 과제 3건 완결 — 실측 괴리율·레버리지 검증·제헌절. **v24 §3.3/§3.4 정정** |
| `docs/history/전략_v24.md` | 상품 사양 실측·공휴일. §3.3/§3.4 는 v25 에서 정정됨 |
| `docs/history/전략_v23.md` | **채택안.** 방어자산 = 배당40 / 미국채40 / 금20 (전부 국내 상장·환노출) |
| `docs/history/전략_v22.md` | 새 축 3개 판정 — 배수(조건부) / 앙상블(기각) / 적립식(현행 강화) |
| `docs/history/전략_v21.md` | **현행 채택안의 근거.** 방어자산 실측화 + 한국 실전 + 3자 비교 |
| `docs/history/전략_v20.md` | 54년 확장·히스테리시스. §11.11 이 인용하는 유의성 통계의 출처 |
| `docs/history/전략_v19.md` | 복귀로직 294+576개 전부 기각 기록 |
| `docs/history/전략_v18.md` | 진입선 45개 변형 기각 + 기본 규약 정의 |
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

---

## 5. 검증 도구 (v37 신설·정리)

| 파일 | 역할 | 언제 |
|---|---|---|
| `verify_all.py` | **단일 진입점.** 불변식 12종(I1~I12). 4초 | 뭔가 고쳤으면 항상 |
| `audit_full.py` | 59파일 AST 전수조사 + **시점별 재계산** | 정기 / CI |
| `audit_all.py` | 채택 결정 재검증 (달러·원화) | 모형을 바꿨을 때 |
| `verify.py` | 채택안 단독 검산 (140.0배) | 참조 구현 |
| `verify_volguard.py` | v32/33 관문 6종 | 변동성 가드 관련 |
| `.github/workflows/verify.yml` | 위를 자동 실행. **실패하면 이슈 자동 생성** | 자동 |

---

## 6. v46~v60 신규 연구·표시 코드

전부 **기각** 판정이다. 실전 파일이 아니라 **재현용**이다.

| 파일 | 무엇을 쟀나 | 판정 |
|---|---|---|
| `research/axis_dca.py` | 적립식으로 RSI·이평·현금비중·평단가매수 14종 (v47) | 14전 14패 |
| `research/axis_dca_grid.py` | 적립식으로 문턱 격자 210개 (v48) | 통과 0 |
| `research/axis_momentum.py` | 절대·이중 모멘텀 · DD+모멘텀 · 사다리 (v49) | 13전 13패 |
| `research/axis_krreal_decomp.py` | 실물 3.2년 A 우세 분해 (v46) | 9거래일이 전부 |
| `research/axis_wide.py` | 광역 49후보 × 6관문 (v50) | 통과 0 (최고 4/6) |
| `research/axis_wide_probe.py` | v50 생존후보 G 정밀검증 | 첨탑·MDD 악화 |
| `research/axis_external.py` | 외부정보 1차 — VIX·breadth·신용 (v51) | 통과 0 |
| `research/axis_vixstate.py` | VIX 를 상태변수로 (v52) | 4블록 검증 불가 |
| `research/axis_rvstate.py` | 실현변동성 상태변수 (v53) | **10관문 통과** → G11 탈락 |
| `research/axis_gate11.py` | G11 집중도 + leave-one-crisis-out (v53) | 독립위기 9개 |
| `research/axis_ext2.py` | 외부정보 2차 — 상태변수·SPY 제외 (v54) | 26전 0승 |
| `research/axis_ext2_probe.py` | v54 최선후보 G1 정밀검증 | 4블록 2/4 |
| `research/axis_mech.py` | 운용 메커니즘 29후보 (v55) | 4/6 도달 0 |
| `research/axis_selbias.py` | 선택편향 감사 T1~T4 (v56) | 편향 지문 없음 |
| `research/axis_minimax.py` | 비중첩 6구간 미니맥스 순위 (v56) | 현행 3위/210 |
| `research/axis_selbias_disjoint.py` | v56 T3 정정 — 비중첩 창 (v57) | 0/4, −6~37% |
| `research/axis_meta.py` | Meta-Strategy 7종 + Oracle (v58) | 상한의 0% 이하 |
| `research/axis_meta_crisis.py` | 메타가 왜 못 고르는가 (v58) | 직전1등 일치 1/4 |
| `research/axis_forward.py` | 미래위험·CVaR·변화점·episode·반등의질 (v59) | Oracle +1030%, 포착 0 이하 |

**v60 은 연구가 아니라 표시 지표 추가다** — 전략을 바꾸지 않았다.

| 파일 | 무엇이 바뀌었나 |
|---|---|
| `reentry_lib.ulcer_uw()` | **신규.** 최장 회복기간 + Ulcer Index. MDD 가 못 재는 낙폭의 '넓이' |
| `deploy/build_stats.py` | 위 두 지표를 `strategy_stats.json` 에 넣는다. **사본 갱신을 요약 출력 앞으로** (출력이 죽어도 사본이 옛 판으로 안 남게) |
| `signal.html` | 카드 지표 4→6개, 기준 설명줄에 CAGR, 비교표 2열 추가 |
| `verify_all.py` | I5 +3(화면 대조) · I6 +16(내장 사본 대조) |
| `hist_krreal.legs_real()` | **신규(v61).** 실물 TIGER 공격·방어 일간수익 분리 — 벤치마크가 전략과 **같은 달력**을 쓰게 |
| `deploy/build_stats.py` | **(v61)** 기준마다 벤치마크 2종(2배 보유·방어 단독)을 같이 굳힌다 |
| `signal.html` | **(v61)** A 제거 · 카드 전체 폭 · 값 아래 눈금 · 비교표 벤치 2줄 |

## 7. 동결 (v57) — 건드리지 말 것

| 파일 | 역할 |
|---|---|
| `data/freeze.json` | **동결된 규칙**·자산·체결규약·비용 + 지문 + 날짜규약 |
| `data/oos_log.csv` | 동결 이후 하루 한 줄 (append-only). 워크플로가 쌓는다. T4 그림자 3열 포함 |
| `deploy/oos_log.py` | 위를 기록한다. **판단하지 않는다.** [v80] qqq.csv 날짜 가드 (미갱신 시 그림자 빈 칸) |
| `verify_all.py` I11 | 코드·화면이 동결 기록과 다르면 **매 push 마다 실패** |
| `verify_all.py` I12 | [v82] T4 그림자 열의 정의 위반 감지 |
| `docs/history/전략_v80` §6·§7 | **T4 그림자 판정 부속서** (사전 등록, 수정 금지) — v69 와 충돌 시 우선 |

**OOS 장부를 보고 문턱을 바꾸면 그 표본이 사라진다.**

---

## 8. v80~v83 — T4 그림자 심층 (2026-08-29)

| 파일 | 역할 |
|---|---|
| `research/axis_t4_shadow.py` | **T4 유일한 실행 가능 참조 구현** (v68 은 코드 미커밋). 판정 규약 전력 분석(3년 창 동전던지기) + 기전 직접 측정(M1 73%·M2 77%) + 무거래 밴드 기각 |
| `research/axis_t4_synthcrash.py` | 합성 하락장 해부 — 닷컴형 B 60% 구조·2008 은 소수 추첨(~29%). 시간추세 없음 · ¼ 양자화 유효 · 혼합 프런티어 · 비용 민감도 |
| `research/axis_t4_krcost.py` | 한국비용(0.2%) 내성 변형 9종 — 관문 K1~K7 사전 고정, **전멸** |
| `research/axis_b_inspect.py` | B 동일 잣대 검사 P1~P4 — 비용 무적 · 기전 68%(재난보험형) · 사각지대 최장 112일 |
| `research/axis_nextgen.py` | [v87] B+T4 구조 결합 23종 — 관문 N1~N8 사전 고정, **전멸**. 괴리 비대칭·T4 분해·최소 후회 |
| `research/axis_finalverify.py` | [v88] 최종 검증 — B 비용 ×3 생존(J1) · 지연 비선형(1987 lag=2 −72%) · 감속 회피 23%/기회 77% · 그림자 채점 템플릿 · 실측 수집 감사 |
| `research/axis_horizon.py` | [v88 부록2] 보유기간별 원금손실 — 1년 21.6% / 5년 0.7% / **10년+ 0.0%** (최악 20년 창 15.9배) |
| `docs/history/전략_v80~v83.md` | 기록 4편. **v80 §6·§7 = 판정 부속서 (수정 금지)** · v82 = 룰 감사 |
