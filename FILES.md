# 파일 분류

> **먼저 `내가_보는_것/전략_요약.md`(지도) → `01_Strategy_Logic.md` 를 읽으세요.** 그 다음이 `README.md` 입니다.
> [v65] 당시 버전 문서 43개는 `docs/history/` 로 이동했고, 현행 내용은 루트의 `01~04_*.md` 에 통합됐습니다.
> 이 파일은 스크립트별 상세 목록입니다.

## 폴더 구조 (2026-08-27 v39 정리)

- `research/STRATEGY_RESEARCH_2026-09-05.md` — 소유자가 허용한 A·T4·B 밖 구조의 분리 연구 사전 기록. 실제 B 동결과 분리한다.
- `research/rebalance_accounting.py` — 일별 목표 재조정의 실제 비중 표류·전 자산 편도 회전 공용 계산. 계좌 과세·납입·월별 보유 엔진은 아님.
- `research/strategy_f1_screen.py` — 사전 고정 F1 8개 달러 세전 1차 비교. 실제 금액 원장 대조·7/10년 모든 시작일·비용/지연 민감도. 원화 ISA 판정은 아님.

```
내가_보는_것/          ★ 소유자용 (한국어). 여기 밖의 파일은 소유자에게 시키지 않는다
  전략_요약.md          이것부터. 전략·근거·결론 5분 요약 + AI 문서 지도
  운영_점검표.md         「내가 언제 뭘 해야 하나」 — 직접 하는 일은 매매 2가지뿐(v140)
  점검.py               자동 점검을 직접 돌려보고 싶을 때만 (--json 은 파수꾼이 쓴다)

공유용_별도전략/        ⛔ 이 저장소의 전략이 **아니다**. 지인 공유용 별개 데모 (2026-09-02 격리)
  README.md             ★ 뭐든 하기 전에 이것부터 — 왜 별개인지·왜 건드리면 안 되는지
  share_variant_*.py    SCHD+QQQ 비레버리지 배합 연구 10개. 엔진을 **읽기만** 한다
                        (다른 세션이 research/ 안의 것을 연구자산으로 오인한 실사고 → 격리)
README.md               전략·자동화·파일지도·오류원인·체크리스트
HANDOFF.md              작업 시작 전 읽을 것 (하지 마라 목록)
AGENTS.md               Codex 진입점 — 같은 폴더의 CLAUDE.md 전문을 읽게 하는 한 줄 안내
CLAUDE.md               AI 공통 규칙의 단일 원천 — 수정 금지 목록·작업 규약·정정 이력 (v210)
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

audit/      (5)  audit_all · audit_full · verify · verify_volguard · test_research_review
            + AUDIT_LEDGER_2026-09-05.md(전체 감사 장부 — 기준 커밋·파일별 검토 상태·발견·처리)
            + CODE_REVIEW_SWEEP_2026-09-05.md(코드리뷰 전수 순회 지시서+진행 장부 — 15배치 · 이어받는 세션은 이 파일부터)
research/  (129.py+8.md) 기각 판정의 재현 코드 + build_crisis_paths.py(v127 화면 데이터 생성 —
            예외적으로 산출물 data/crisis_paths.json 이 배포됨) + hypo_*.py 8편(2026-08-30~31
            소유자 지시 가설 총력전 — 판정·검산은 04 §5-3) + audit_stat/exec/pbo ·
            cand_general · NEW_STRATEGY_RESEARCH.md(2026-08-31 통계 감사 — 04 §5-4) +
            eng_common/sp500/kospi · ENGINE_RESEARCH.md(엔진 교체 연구 — 04 §5-5) + FINAL_AUDIT.md(8항목 최종 감사) + surv_map/alert · SURVIVAL_MONITOR.md(생존성·감시 체계 — 04 §5-6) + lev_opt/lev_th · LEVERAGE_US.md(미국 배율) + ext_ibs/ext_vr · EXT_INFINITE.md(무한매수법·VR 비교+수집) + def_bond/def_equity(방어 국채 만기·통화 04 §5-16 · 방어 배합 코너 04 §5-17) + factcheck_qld_talk.py(외부 강연 QLD 주장 팩트체크 04 §5-19) + horizon_ess/dsr_b/isa_pension · MEASUREMENT_AUDIT.md(측정 감사 — 「손실 0 문턱 7년」의 유효표본 병기 규약).
            각 파일 상단에 경로보정 3줄
deploy/     라이브 파이프라인 — 건드리지 말 것
data/       화면이 읽는 것 — 워크플로 소유 (freeze.json · oos_log.csv 포함)
docs/       history/(59 — 전략_v18~v203 보관층) · raw/ · HANDOFF_전체이력
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
| `deploy/update_signal.py` | 매일 QQQ **수정종가**를 받아 두 규칙을 판정 → `data/signal.json`. 원본 날짜 중복·역순·미래, 수정주가 누락, 장중 판정 메타 부재를 실패-폐쇄 |
| `deploy/refresh_hist.py` | [v72/v203] 월 1회 원자료 11종 연장 (append-only · 비율 이음 · 장중 가드). 빈 응답·기존 끝 날짜 부재·낡은 HTTP 200·미래/중복/역순을 실패-폐쇄한다. FRED DEXKOUS는 공식 `graph/fredgraph.csv`에서 **마지막 물리 행 뒤만** 붙이고, 실패하면 검증된 Yahoo KRW=X 확정봉만 보강한다. 한국 ETF는 수정주가 없는 네이버 값으로 대체하지 않으며 **KOSPI 지수만** 네이버 일봉을 허용한다 |
| `deploy/data_check.py` | [v73/v203] 데이터 검증 게이트 — 0행·날짜·중복·역순·비유한/0이하·열별 절대범위·OHLC 모순·각 열의 이음새 급변·공백을 막아 기존 정상 데이터를 보존 |
| `deploy/notify.py` | [v73/v77/v203] 실패·전환 알림 (카카오톡/Discord/Telegram, GitHub Secrets). Kakao Client Secret ON/OFF 지원 · 응답 본문까지 확인 |
| `deploy/kakao_setup.py` | [v77/v203] 카카오 알림 최초 1회 설정 (본인 PC). Client Secret 선택 입력 · 토큰 비노출 오류 처리 · 실제 시험 발송 확인 |
| `deploy/kakao_keepalive.py` | [v77/v203] 카카오 refresh 토큰 매일 연명·자동 교체. 새 토큰 저장 실패 시 옛 토큰 즉시 무효 경고 + 실패 상태 |
| `deploy/signal_alert.py` | [v76/v203] 전환 신호일 폰 알림. 성공한 종가일만 별도 표시해 중복을 막고, 실패하면 OOS 장부와 무관하게 다음 슬롯에서 재시도 + 이슈(메일) |
| `deploy/watchdog.py` | **[v140/v203] 자동 파수꾼** — 신호·시세·성과·알림 채널·전환 실행일·근접 진입·재조정·주간 점검·월간 생존 알림을 감시한다. B 상태·날짜·휴장일 범위를 엄격히 검증하고 미래 날짜도 손상으로 알린다. `ops_check.json`은 원자 교체하며 전략에는 손대지 않는다. `--selftest`는 **61개** 합성 경로를 검증하고 I14가 실행한다 |
| `deploy/build_stats.py` | 화면에 띄울 Calmar·MDD·Sortino 를 미리 계산 → `data/strategy_stats.json`. **방어자산 2안(v23 바스켓 / v21 배당100)을 둘 다 계산.** 월간 원자료 연장 뒤 자동 실행하며, 모형 변경 직후에는 수동 재생성 |
| `deploy/nav_collect.py` | **실측 NAV 수집기** (네이버 전종목 NAV). 핵심 4종이 모두 있고 NAV·가격·괴리율·시장 종목수가 유효할 때만 원자적으로 하루를 적립한다. 가격뿐인 예비 출처로 NAV 성공을 가장하지 않으며 실패는 다음 슬롯 재시도+이슈로 남는다 |
| `data/nav_history.csv` | 적립되는 실측 NAV·괴리율 시계열 |
| `deploy/kr_holidays.py` | **한국 증시 휴장일 생성기** (음력 직접 계산 + KOSPI 실측 대조). `--emit` 로 `data/kr_holidays.json` 생성. **[v195] 파수꾼 주간 슬롯이 매주 돌린다** — 내용이 같으면 쓰지 않으므로 해가 바뀔 때만 커밋이 난다. **[v203] 2026-05-01 시행 노동절·제헌절 대체휴일, KST 연경계, 임시공휴일 충돌을 반영**. 임시공휴일·선거일은 SPECIAL 에 손으로 |
| `data/kr_holidays.json` | 휴장일 표(현재 2025~2032 · 135일). `signal.html` 시계 · `price_poll.py` · 파수꾼 `switchday` 가 읽는다(전부 오늘/미래만). **[v195] 매년 자동 연장** |
| `manifest.json` · `icon-192/512.png` | [v104] PWA 홈 화면 추가 (standalone). **pages.yml 복사 목록 필수** — verify_all 이 검사한다 |
| `deploy/README.md` | 배포 파이프라인 **현행** 안내 (2026-09-05 재작성 — 워크플로 6개·실패 규약·스크립트 지도). 옛 v18 설치 안내는 `docs/history/deploy_README_v18_원본.md` |
| `.github/workflows/daily-signal.yml` | 매일 신호 갱신 자동 실행. **예약 8슬롯**(마감 전 4+예비 4) 중 하나가 확정 종가를 잡는다. 허용한 5개 장부만 스테이징하고 예상 밖 변경은 멈춘다. non-fast-forward에서는 옛 산출물을 rebase하지 않고 실패-폐쇄해 다음 슬롯이 최신 HEAD에서 재계산한다. 알림/장부 이슈 API 실패는 커밋을 막지 않되 커밋 뒤 빨간 실행으로 드러내고 Pages는 결론과 무관하게 최신 main을 배포한다 |
| `.github/workflows/watchdog.yml` | **[v140] 자동 파수꾼** — 평일 08:40 KST 신선도·채널·**성과 스냅샷**[v171]·**시세 수집**[v176]·**전환 실행일 재알림·근접 진입**[v192] 감시 + 월요일 09:10 KST 자동 점검·**휴장일 표 연장**[v195]. 이상이면 카톡 + 이슈(label `watchdog`) |
| `.github/workflows/source-probe.yml` | **[2026-09-03] 출처 점검(수동)** — `kr_sources.py --probe` 를 GitHub 러너(미국 IP)에서 돌려 예비 출처가 거기서도 응답하는지 본다. 읽기만(커밋 0·알림 0). 정기 실행 없음 | 러너 IP 차단 여부 확인용 |
| `.github/workflows/pages.yml` | 갱신 후 Pages 재배포 |
| `data/signal.json` | 뷰어가 읽는 현재 상태 (두 전략 + 성과지표 + 위기 궤적) |
| `data/strategy_stats.json` | 두 전략 × 4개 기준의 성과지표. `build_stats.py` 산출물 |
| `data/crisis_paths.json` | 위기 타임머신(v127) 데이터 — 위기 4구간의 전략/2배보유 계좌가치 경로. `research/build_crisis_paths.py` 산출물, **로컬 수동 실행**(build_stats 와 같은 포지션 — 원자료 갱신 시 재실행) |
| `data/ops_check.json` | **[v140] 자동 점검 결과** — 전제 감시 Level·느린 변수 4종·4다리 AUM·체결비용 진행률. `deploy/watchdog.py check` 산출물(주 1회), 화면 `drawOpsCheck()` 가 읽는다. **[v177] `heartbeat` 키**(마지막 생존 알림 「달」)도 여기 얹혀 있다 — 새 파일을 안 만들려고 얹은 것이라 점검 내용과는 무관하다. **사람이 파이썬을 돌리지 않아도 되는 이유가 이 파일이다.** **[v188] `protocol_b` 키** — B 판정 규약(02 §5-1) 평가 요약(verdict·events·line·drift·todo)도 같은 이유로 여기 얹혔다 |
| `data/signal_alert_state.json` | **[v203] 전환 폰 알림의 마지막 성공 종가일.** 알림이 실제 도착한 뒤에만 원자 기록하며, OOS 장부와 분리해 실패한 발송을 다음 슬롯이 다시 시도하게 한다 |
| `data/retired_numbers.json` | **폐기된 공표 수치 대장** — v36 정정 등으로 죽은 값. `verify_all` I9 가 이 목록을 현행 문서에서 찾아 남아 있으면 실패시킨다(버전 문서는 그 시대 기록이라 허용하되 정정 배너를 요구) |
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
| `verify.py` | **구 채택안(v17 규칙 A −16/−11 · 방어 SCHD 단독)** 재현. 138.2배 검산 — 현행 B 의 검산이 아니다(그건 `verify_all.py` I7·I11) |
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
| `hyst_sigwfa.py` | 신호 계열별 Calmar WFA — 실물 구간 QQQ 121.31배 vs QLD 52.42배, 동일 구간 고정 B 122.36배 (2026-09-05 교정) |

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
| `axis_macro4.py` | **격자 감사** — 등록된 42칸 모두 MDD 개선(평지). v203에서 역방향 비교·잘못된 80칸 회귀를 교정, WFA는 Calmar로 선택 |
| `docs/raw/전략_v32_raw.txt` | 위 두 스크립트 원본 출력 |
| `axis_macro3.py` | **v30 방법론 감사 + 남은 3축 종결** — 시차상관 정정(변화량), 분위누수 제거, 금리차·복귀필터·변동성 조기방어. **권장 진입점** |
| `docs/raw/전략_v31_raw.txt` | 위 스크립트 원본 출력 |
| `axis_macro.py` | **매크로·심리 지표 기각(2011-)** — VIX·하이일드·공포탐욕 조기경보 5관문. v203에서 인과 지연·워밍업·비중첩 플라시보 교정 |
| `axis_macro2.py` | **같은 판정을 1972- 로 확장** — 짧은 창에서 통과한 역발상이 닷컴에서 붕괴. v203에서 OOS 상태 연속성 교정 |
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
| `docs/history/전략_v203_통합코드리뷰.md` | **최신.** 연구·배포 코드 통합 리뷰 정정표와 재검증 결과. **전략 B 규칙 변경 없음** |
| `docs/history/전략_v63.md` | 같은 기간으로 맞춘 표 — 최근 5·10·15년은 2배 보유 승, 20년에서 뒤집힘 |
| `docs/history/전략_v62.md` | 지표를 「그래서 얼마냐」로 번역 + 체결 시각 모순 정정(v18 잔재) |
| `docs/history/전략_v61.md` | A(−16/−11) 화면 제거 + 지표에 눈금(2배 보유·방어 단독) |
| `docs/history/전략_v60.md` | 165 vs 2,761 분해(전부 그 3년) + 회복기간·Ulcer 화면 반영 |
| `docs/history/전략_v40.md` ~ `v59.md` | 기각 축 14차수 · 동결(v57) · 감사. §6 표 참조 (v37~v39 는 문서 없음 — v36 다음이 v40) |
| `docs/history/전략_v36.md` | 국채 다리 선물형 정정 — 드리프트 +2.84%→−0.18%. 채택 결정 유지, 공표수치 −18.6% |
| `docs/history/전략_v35.md` | 전수조사(59파일, HIGH 0건 · 시점별 재계산 0/40) + 라이브 종가 미갱신 수정 |
| `docs/history/전략_v34.md` | 전면 감사 — 채택 결정 전부 유지, 실패 0건. 남은 경고는 국채 롤 비용 1건 |
| `docs/history/전략_v33.md` | 적립 시뮬레이터 2일 지연 버그 정정의 당시 기록. **ISA 현행 수치는 v203 재정정** |
| `docs/history/전략_v32.md` | 변동성 조기방어 재심 — v31 기각근거 2개는 틀렸지만 **적립식에서 재기각**. 전략 변경 없음 |
| `docs/history/전략_v31.md` | v30 감사(근거 3개 정정) + 금리차·복귀필터·변동성 조기방어 기각. 전략 변경 없음 |
| `docs/history/전략_v30.md` | 매크로·심리 지표 전부 기각 — 동행지표라 새 정보가 없다. **v31 로 정정됨** |
| `docs/history/전략_v29.md` | ISA 서민형 세후의 당시 기록. **현행 v210: 원화·5년 납입 후20년 결과, 일반계좌 대비+59.9%, 이득의 약84%는 과세이연** (`research/axis_isa.py`). v203의 +54.7%는 v210 정정 전 수치 |
| `docs/history/전략_v28.md` | 신호원은 미국 QQQ 종가 — 국내 종가로 재면 1997- −92%, MDD +21%p |
| `docs/history/전략_v27.md` | 방어 안에서의 선택 기각 + 월간 재조정 비용 버그 정정. 분산 자체가 알파 |
| `docs/history/전략_v26.md` | 적립식 재검증 — 불규칙 납입도 순위 불변. 실무 최소 월납입은 현재가에서 자동 계산 |
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
`verify.py` 는 여전히 **구 채택안(v17 A)** 곡선을 재현한다(현행 B 아님).

```bash
for f in verify.py hist_*.py hyst_*.py; do python "$f" > /dev/null && echo "OK $f"; done
```

---

## 5. 검증 도구 (v37 신설·정리)

| 파일 | 역할 | 언제 |
|---|---|---|
| `verify_all.py` | **단일 진입점.** 불변식 14종(I1~I14). 약 7초 | 뭔가 고쳤으면 항상 · **I14** 운영·알림·자료 갱신·배포 셀프테스트 16종(전체 모드) |
| `audit_full.py` | 59파일 AST 전수조사 + **시점별 재계산** | 정기 / CI |
| `audit_all.py` | 채택 결정 재검증 (달러·원화) | 모형을 바꿨을 때 |
| `verify.py` | 구 채택안(v17 A −16/−11) 단독 검산 (140.0배) — 현행 B 아님 | 참조 구현 |
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
| `research/axis_mech.py` | 운용 메커니즘 29라벨·중복 제거 27경로 (v55·v203) | G1~G6 전부 통과 0/27 |
| `research/axis_selbias.py` | 선택편향 감사 T1~T4 (v56) | 편향 지문 없음 |
| `research/axis_minimax.py` | 비중첩 6구간 미니맥스 순위 (v56) | 현행 3위/210 → v210 재실행 1위/210 (정정 2026-09-05) |
| `research/axis_selbias_disjoint.py` | v56 T3 정정 — 비중첩 창 (v57) | 0/4, −6~37% |
| `research/axis_meta.py` | Meta-Strategy 7종 + Oracle (v58) | 상한의 0% 이하 |
| `research/axis_meta_crisis.py` | 메타가 왜 못 고르는가 (v58·v203) | 완결된 다음 10년 기준 직전1등 일치 1/3 |
| `research/axis_forward.py` | 미래위험·CVaR·변화점·episode·반등의질 (v59) | Oracle +1030%, 포착 0 이하 |

**v60 은 연구가 아니라 표시 지표 추가다** — 전략을 바꾸지 않았다.

| 파일 | 무엇이 바뀌었나 |
|---|---|
| `reentry_lib.ulcer_uw()` | **신규.** 최장 회복기간 + Ulcer Index. MDD 가 못 재는 낙폭의 '넓이' |
| `deploy/build_stats.py` | 위 두 지표를 `strategy_stats.json` 에 넣는다. **사본 갱신을 요약 출력 앞으로** (출력이 죽어도 사본이 옛 판으로 안 남게) |
| `signal.html` | 카드 지표 4→6개, 기준 설명줄에 CAGR, 비교표 2열 추가 |
| `verify_all.py` | I5 +3(화면 대조) · I6 +16(내장 사본 대조) · **I14**[2026-09-03] 셀프테스트(파수꾼 `--selftest` · wait_close `--selftest`, 전체 모드) |
| `hist_krreal.legs_real()` | **신규(v61).** 실물 TIGER 공격·방어 일간수익 분리 — 벤치마크가 전략과 **같은 달력**을 쓰게 |
| `deploy/build_stats.py` | **(v61)** 기준마다 벤치마크 2종(2배 보유·방어 단독)을 같이 굳힌다 |
| `signal.html` | **(v61)** A 제거 · 카드 전체 폭 · 값 아래 눈금 · 비교표 벤치 2줄 |

## 7. 동결 (v57) — 건드리지 말 것

| 파일 | 역할 |
|---|---|
| `data/freeze.json` | **동결된 규칙**·자산·체결규약·비용 + 지문 + 날짜규약 |
| `data/oos_log.csv` | 동결 이후 하루 한 줄 (append-only). 워크플로가 쌓는다. T4 그림자 3열 포함 |
| `data/oos_protocol_b.json` | **[2026-09-02] B 자체의 OOS 판정 규약** (기계용 원본 + 지문). T4 는 v80 §6 에 있었는데 B 에는 없던 것 — 사건 정의·관문 A(재난 지급 7/7)·B(보험료 P05/최악)·R(3년 롤링)·대응(재검토까지). 사람용은 02 §5-1, 평가는 `research/oos_protocol_b.py --oos` |
| `verify_all.py` I13 | 위 JSON 의 지문이 다르면 **실패** — 사건이 쌓인 뒤 관문을 손대는 것(사후 재량)을 실수로는 못 하게 |
| `deploy/oos_log.py` | 위를 기록한다. **판단하지 않는다.** [v80] qqq.csv 날짜 가드 (미갱신 시 그림자 빈 칸) |
| `verify_all.py` I11 | 코드·화면이 동결 기록과 다르면 **매 push 마다 실패** |
| `verify_all.py` I12 | [v82] T4 그림자 열의 정의 위반 감지 |
| `docs/history/전략_v80` §6·§7 | **T4 그림자 판정 부속서** (사전 등록, 수정 금지) — v69 와 충돌 시 우선 |

**OOS 장부를 보고 문턱을 바꾸면 그 표본이 사라진다.**

---

## 8. v80~v83 — T4 그림자 심층 (2026-08-29)

| 파일 | 역할 |
|---|---|
| `research/axis_t4_shadow.py` | **T4 유일한 실행 가능 참조 구현** (v68 은 코드 미커밋). v203 공통 사건계약 21회: 공식 M1(<0.7) 76% · M2 81% · 동시 67% (민감도 M1<0.5는 67%), 무거래 밴드 기각 → v210 재실행(순회 B09): M1 76% · M2 19/21=90% · 동시 67% · A-1 앵커를 v210 기준(T4 254,088 · B 181,018 @2026-08-26)으로 갱신 |
| `research/axis_t4_synthcrash.py` | 합성 하락장 해부 — 닷컴형 B 60% 구조·2008 은 소수 추첨(~29%). 시간추세 없음 · ¼ 양자화 유효 · 혼합 프런티어 · 비용 민감도 |
| `research/axis_t4_krcost.py` | 한국비용(0.2%) 내성 변형 9종 — 관문 K1~K7 사전 고정, **전멸** |
| `research/axis_b_inspect.py` | B 동일 잣대 검사 P1~P4 — 비용 내성 · 사건승 15/21=71%(재난보험형) → v210 재실행 13/21=62% · 사각지대 최장 90일 · **P3 미달** (정정 2026-09-05 · 순회 B06-1) |
| `research/axis_nextgen.py` | [v87·v203] 평가행 24개 = 명목 신규 22 + 대조 2. 중복 제거 시 신규 20경로 — 관문 N1~N8 **전멸**. 괴리 비대칭·T4 분해·최소 후회 → **v210 재실행(2026-09-05 · 순회 B08): MIX(0.50) 이 N1~N8 통과**(혼합 하위호환 · 후반 2000~ 0.91×B · 뒤집힌 것은 N6 이웃 MIX(0.25) 의 N2 가 0.895→1.19×B 로 넘어간 것뿐 · v213 부분비중 비용 교정 전 경로) — **채택 아님** · 그림자 등록 논의 자격 여부는 소유자 결정 |
| `research/axis_finalverify.py` | [v88·v203] 최종 검증 — 현행 40/40/20 방어를 일관 적용, 비용·지연·사건창·실측 장부를 다시 계산. J1 생존 · J2/J3 대기 결론 유지 |
| `research/axis_horizon.py` | [v88 부록2·v203] 달력 월 시작 보유기간별 원금손실 — 1년 21.3% / 5년 1.0% / **10년+ 0.0%** (최악 20년 창 17.90배) |
| `docs/history/전략_v80~v83.md` | 기록 4편. **v80 §6·§7 = 판정 부속서 (수정 금지)** · v82 = 룰 감사 |

---

## 9. v84~v141 — 가설 프로그램 · 감사 · 운영 (2026-08-30 ~ 08-31)

> **이 절이 왜 생겼나**: §6·§8 이 v83(2026-08-29)에서 멈춰 있어 이틀치 연구 49개가
> 지도에 없었다(2026-08-31 정합성 감사에서 발견). §1 「실전 운용 파일」은 최신이었다 —
> 빠진 것은 **연구 스크립트 지도**뿐이다. 아래는 전부 **재현용**이며 실전 파일이 아니다.
> 판정 상세는 `04_Rejected_Research.md` §5-2~§5-18.

### 9-1. 가설 프로그램 (v84~v88, 소유자 지시 「어떤 수를 써도 좋다」)

| 파일 | 무엇을 쟀나 | 판정 |
|---|---|---|
| `research/hypo_gates.py` | 「무제약 이상형」을 국내·직투 도구로 구현 — HANDOFF §3 관문 통과 여부 | 통과 0 |
| `research/hypo_t4wide.py` | T4 이상화 — 국내 레버리지 라인업(주식·미국채30년·금 2x) 다자산 × 타깃 40% | 관문 미달 |
| `research/hypo_t4_real.py` | **정본 T4 스펙**으로 재실행 (앞 근사와 스펙이 달랐다) | 관문 미달 |
| `research/hypo_hex.py` | 「육각형」 — 관문 ①(위험조정)과 ②(부의 바닥)를 **동시에** 넘는 후보가 있나 | 존재하지 않음 |
| `research/hypo_escape.py` | B 의 손실 모드 해부 + 폭풍 문맥 조건부 브레이크 격자 전수 | 전멸 |
| `research/hypo_external2.py` | 외부 정보원 총동원의 마지막 빈 칸 — **공격 구간 사이징**에 외부 눈 | 통과 0 |
| `research/hypo_verify.py` | 일주일 실험(hypo_*) 결론을 공표 수치·규약과 대조하는 **자기감사** | — |

### 9-2. 통계 감사 · 일반화 (통합 연구 Part 1~4)

| 파일 | 무엇을 쟀나 | 판정·산출 |
|---|---|---|
| `research/audit_stat.py` | 혼합 x·B+(1−x)·T4 를 블록 부트스트랩·ESS·Deflated Sharpe 로 해부 | 고원은 채굴 산물 가능 |
| `research/audit_pbo.py` | 탐색한 후보 전부를 CSCV(Bailey–López de Prado 2014)에 — 「표본 내 1등 고르기」의 과적합도 | PBO 0.49~0.53 → v210 재실행 Sharpe 0.03 / Calmar 0.51 (혼합만 0.36 / 0.59) |
| `research/audit_exec.py` | 혼합의 실전 집행 근사 — 매일 움직이는 목표비중에서 고원이 사는가 | ¼ 양자화 필요 |
| `research/cand_general.py` | 「전략 간 분산」이 B×T4 특유인가, 아무 희석에나 생기나 | 일반화 실패 |
| `research/b_adversarial.py` | **「B 에게도 확증편향이 있는 것 아닌가」** (소유자 질문) — B 를 심판이 아닌 피고로 | 04 §5-15 |
| `research/what_we_know.py` | 「동전던지기·모른다로 도망치지 마라」 — 문턱·룩백·기전의 **식별 가능성** 분리 | 04 §5-14 |
| `research/thresh_window.py` | **「54년 통짜 1등」이 근거인가** (소유자 질문) — 문턱 격자 210개를 창별로 재정렬: 통짜 · 경계 민감도 · 비중첩 블록 | 04 §5-20 · 인용 오류 1건 적발 |
| `research/era_start.py` | **「인터넷이 당연해진 시기를 기점으로 잡으면」** (소유자 질문) — 기점별 비교 · 전 시작일 분포 · **가르는 축(창의 MDD)** | 04 §5-21 · 기점 가설 **기각** |
| `research/pbo_thresh.py` | **문턱 격자의 PBO** — `audit_pbo` 우주에 문턱이 없던 빈칸을 충전(CSCV S=8) + 잡음 대조군 + ⓐ 반증 | 04 §5-22 · PBO 0.40~0.83 |
| `research/wfa_thresh.py` | **정정 WFA 를 재현 가능하게 고정** — 두 엔진 × 결함/정정 2×2 · 훈련길이 8종 · Calmar 변형 | 04 §5-13 **정정3** · 12/12 재현 + §-1 ⑧ 위반 적발 |
| `research/oos_protocol_b.py` | **B 자체의 OOS 판정 규약 — 기저율 측정(기본) + 평가기(`--oos`)** (T4 는 v80 §6 에 있는데 B 에는 없었다). 사건 단위 A·B·R 관문의 역사 기저율 + 룩백 200 그림자 정보량 + 부재 비용 표. `--oos` 는 `data/oos_protocol_b.json` 을 동결 이후 사건에 기계적으로 적용(지문 검사 · 기저율 자기검산 · 사건 0 이면 「판정 불가 — 정상」) | 04 §5-23 · **등록 완료 2026-09-02** (02 §5-1 · I13) · 전략 무변경 · **[v188] 파수꾼 `check` 가 주 1회 자동 실행** |
| `research/free_design.py` | **[실험] 관문에서 자유로운 설계 3안 + 검증 배터리** (소유자 「이전 룰·관문에서 자유롭게, 검증은 전부」) — X1 장중 재난 스탑(NDX OHLC) · X2 방어 인버스 슬리브 · X3 SOX 2배 엔진. 배터리(10y p05·4블록·홀드아웃·CSCV PBO·집중도)·통과 기준·예측을 **결과 전 등록**. 자료 캐시 `data/hist/yahoo_{NDX,SOX}_ohlc.csv`(Yahoo · 월간 갱신 밖 · 실험 전용) | 04 §5-24 · **3/3 실패** · 선견 한 칸 적발(§5-24 E) |
| `research/lookback200.py` | **[실험] 룩백 200 검증** (소유자 「어떤 룰보다 최우선 — 왜 200 이어야 하는지 근거까지」, §5-14 D 재탐색 금지를 이 질문에 한해 해제) — §5-14 D 격자 표 **첫 재현(15/15)** · 정면 비교+관문 ①② · 갈린 구간 전수 분해(격차 = 재진입 4건) · 고원 · 전 시작일 · 사건 단위 · WFA 3종 · CSCV · 블록 · 타 시장 4개 · 약세장 군 시간 구조 · 동결 이후 OOS | 04 §5-25 · **유지** — Calmar +5.4% 관문① 미달 · 사전 식별 불가 · 타 시장 0/4 · 「하필 200」은 2023 의 산물 |
| `research/valuation_regime.py` | **[검증] 고평가·장기 횡보·대형 하락 환경에서 B** (소유자 지시 2026-09-02, ChatGPT 작성 프롬프트 · 전략 무변경) — CAPE 분위→이후 수익(Shiller 1871~) · 횡보 사건 표(하락/회복 분리 · 가격/총수익 · 명목/실질) · 같은 구간 B vs S&P·NDX·2배·방어만 · 고평가 시작월 vs 보통(엔진 표본) + 닷컴 제외 반증 · 시나리오 6종 + 니케이 붕괴형 · 강세장 기회비용 · 편향 점검표 · 사전 등록 판정. 캐시: `data/hist/shiller_sp500_monthly.csv`·`multpl_cape_monthly.csv`·`datahub_cpi_us.csv` | 04 §5-26 · **[강화]**(A · 통계는 C · 1972 이전 E) — 단서: 빠른 급락 4/4 B 가 더 깊음 · 니케이형에서 0.52배 |
| `research/near_zone.py` | **[운영 측정] 낙폭 게이지 「근접」 구간 빈도** — 근접 알림(v192)의 근거. 엔진 표본(1972~ 54년) + FRED NDX 1986~ 교차, 게이지 정의는 화면 paintProx 와 동일(gap<3%p). 진입 연 3.5회 · 55% 가 20일 안 전환 · 전환의 99% 가 직전 5일 안에 근접 · 「여유」에서 곧바로 전환 0회 | 04 §5-8 보강 · §7 Q5 · watchdog `near` 문구의 출처 |
| `research/q1_physical_bond.py` | **[연구 Q1] 현물형 미국채 ETF 상장 — 국채 다리 교체의 값** (2026-09-02, 반영 금지). 네이버 목록 실측 4종 · 현물 5/7/10/20/30년 vs 현행 선물 ust5 · 관문①②③④ 사전 등록 · 보수 감도 | 04 §7-3 · **305080 유지 · Q1 닫힘**(현물 10년 Calmar +4.4% 미달) |
| `research/q2_hedged_attack.py` | **[연구 Q2] 공격 다리 환헤지(409820형) vs 환노출** (2026-09-02, 반영 금지). 원화 1997~ · carry = 한−미 3개월 금리차 **실측**(FRED → OECD SDMX → 캐시 `data/hist/kr_3m_rate.csv` → ±1.5%p 감도, 09-03 보험) · 위기 5창 | 04 §7-4 · 갈아타면 **0.82배**(범위 0.4~0.8) · 2008형 −10.4%p · 전체 MDD 는 +2.0%p 얕음 |
| `research/q5_near_presell.py` | **[연구 Q5] 근접 알림을 보고 먼저 팔면 — 가격표** (2026-09-02, 반영 금지). −13/−14/−15 대칭 · 근접 절반 트랜치 · 에피소드 기대값 · 행동 측정 규약 | 04 §7-5 · 근접 매도 0.33배 · 행동은 미측정(사건 0) |
| `research/liquid_design.py` | **[자유 설계 · 가상] 「흐르는 전략」 6형태** (2026-09-03 · 반영 금지) — 엔진5·방어5 · 룩백3/6/12 · 창 둘 · 실제 보유금액·월/일 재조정 일정·회전비용(v207) | `research/CODE_REVIEW_2026-09-05.md` v207 R01: 기존 두 창 32개 후보·룩백 행 재실행, ①②③ 동시 통과 없음. EXPLORATION §A는 수정 전 이력 · §7 Q6/Q8 |
| `research/liquid_iter.py` | **[자유 설계 · 가상] 개량 라운드** (2026-09-03 · 반영 금지) — R1 9개 → 상위2의 R2 · 정/역 설계·보류 창 · 선택 일정과 실제 비중 재조정 분리(v207) | `research/CODE_REVIEW_2026-09-05.md` v207 R01: 양방향 보류 창 ①② 동시 통과 없음. 옛 +8.7%/−2.5%는 현재 근거에서 철회, EXPLORATION §A-2는 탐색 이력 |
| `research/new_paths.py` | **[새 길 탐구 · 가상] 병렬 슬리브(CTA) · 안전자산 단위 낙폭(÷금·÷국채·÷T-bill) · 고점 이후 시간** (2026-09-03 · 반영 금지) — 14후보(A5/C4/D5) · 관문①②③ · 일별 재조정 회전비용 교정(v207) | `research/CODE_REVIEW_2026-09-05.md` v207 R01: 재실행 ①②③ 동시 통과 없음. C3 ①② 통과·③ 미달 유지 → c3_falsify |
| `research/ml_policy.py` | **[새 길 탐구 · 가상] 기계가 배우는 정책** — 특징 15 · 걸어가며 재학습 로지스틱(뉴턴·L2) · 매년 570개 한 조건 규칙 탐색(규칙 재발견 검사) · OOS 1982~ | research/EXPLORATION.md §B · MDD −91~−99% · 낙폭 계열 재발견 3/45년 — 자유도의 가격 |
| `research/c3_falsify.py` | **[반증] C3 ÷T-bill 낙폭** — 사건 단위·블록·고원·전 시작일·금리 국면·타 시장·등가·비용 8종 | research/EXPLORATION.md §B · 이득은 고금리 시대 산물 · p05 첨탑 · 채택 후보 아님 · §7 Q7 조건부 관찰 |
| `research/frontier2.py` | **[새 길 탐구 2 · 가상] 원화 환 오버레이(5년 평균 대비 θ) · 계절 노출 · 평활 고점** (2026-09-03 · 반영 금지) — 관문 ①②③ · 위기 창 | research/EXPLORATION.md §B-2 · 전부 미달(환 오버레이 p05 +34% 는 1998 사건 1개) · 평활 고점 −18% |
| `research/EXPLORATION.md` | **[별도 탐구 이력] 본 전략과 별개의 가상 전략 39후보** (2026-09-03 당시 집계) — 자유 설계·개량·새 길·플라시보. 04 §5-27·5-28에서 분리 | 수정 전 표는 현재 정량 근거 사용 금지(v204/v207). 최신 교정 범위는 CODE_REVIEW_2026-09-05.md 참조; 39후보 전체 재감사 완료 아님 |
| `research/b_gate_noise.py` | **[이식 검산] B 의 무작위 이웃 분포를 정식 엔진으로** (2026-09-03, 04 §5-29 a) — 관문 ①②③ 의 파라미터 잡음 폭 · N1 넓게/N2 좁게 각 200 + 씨앗 감도 3 · 예측·판정 규칙 결과 전 등록 · 후보 선택 없음 | ① 잡음 위(경계선 · 상향 없음) · ①② 2~4.5% 잡음 통과 · ①②③ 0/800 |
| `research/recovery_speed.py` | **[가설 검증] 「최근일수록 폭락 회복이 빨라졌다」** (2026-09-03, 04 §5-30) — 사건 정의 3종(사상최고가·지그재그·독립사건) · 반증 8종(창 절단·깊이 통제·코로나 제외·순열·실질·S&P·B 영향) · 예측 결과 전 등록 | **판단 불가** · 깊이가 진짜 변수(−0.65) · B 의 승패는 회복 속도가 아니라 **하락 속도**(+0.90) · 2008 분리는 소유자 지적 |
| `research/schd_qqq_overlap.py` | **[사실 확인] QQQ ↔ 방어 배당 다리** (2026-09-03, 04 §5-31) — 전체 기간 B vs 2배보유 · 수익률 상관(평시/폭락) · 수익률 기반 섹터 역추정(11 섹터 NNLS) · 위기별 낙폭 | B 는 2배보유의 38배 · 섹터 겹침 7% · SCHD 금융 9%(DVY 2008 은 28%) · 2020 급락엔 SCHD 가 더 빠짐 |
| `research/hedge_ratio_scan.py` | **[실험] QLD↔SCHD 배합 비율 전수** (2026-09-03, 04 §5-32) — 정적 배합 / B 의 공격 다리 두 갈래 · 창 3개 · 한계 교환비 · 공표·guide §⑤ 검산 내장 | 신호 없으면 공짜 점심 · 신호 있으면 관문 ① 미달(+8.7%)·p05 전멸 → 현행 유지 |
| `research/forecast_check.py` | **[사실 확인] 외부 10년 수익 예측(골드만 3% vs JP모건 6.7%) 심판** (2026-09-03, 04 §5-33) — CAPE 예측력 R²·예측구간 · 저수익 10년 조건부 B 성과 · 인용 수치 확인 | R² 0.29 · 구간 폭 17%p 로 두 예측 구별 불가 · 고평가 증거는 국면 1개 |
| `research/attack_diversify.py` | **[실험] 공격 다리에 무엇을 섞어야 변동성이 비선형으로 주나** (2026-09-03, 04 §5-34) — 배당·국채·금·방어바스켓·현금 5종 × 비중 · 분산 보너스(같은 변동성 현금 대비) · 금 ①③ 통과 후 시대 반증 | 보너스 최대 +1.2%p · 금은 시대 산물 · 전환이 만든 +8.06%p 의 1/7 |
| `research/mdd_target.py` | **[조건부 설계] MDD 상한 50% 를 만족하는 경로별 가격표** (2026-09-03, 04 §5-35) — 배합 5종·배율·문턱·상시방어·조합 · 판정 기준(20년 p05) 결과 전 등록 | 공격 다리 20% 를 빼는 것이 가장 싸다 · 배율·문턱 조정이 가장 비싸다 |
| `research/plan30_withdraw.py` | **[조건부 설계] 소유자 계획(30년·7년차 인출 시작)으로 후보 재평가** (2026-09-03, 04 §5-36) — 비율/정액 인출 · 총 인출·최악 연 인출·소진·말잔액 | 현행 B 가 전 열 1위 · 비율 인출은 시퀀스 리스크를 없앤다 · 소득 흔들림만 B 가 열위 |
| `research/complement_sleeve.py` | **[사실 확인] QQQ 를 보완하는 주식 슬리브 17종** (2026-09-03, 04 §5-37) — 섹터 겹침·폭락일 상관·자체 수익 삼각형 · 위기 4구간 · 공통창 비교 | 필수소비가 삼각형 최적 · SCHD 는 폭락일 상관 최상위권 · 금광주는 자체 수익에서 탈락 |
| `research/tax_general_account.py` | **[사실 확인] 일반계좌 세후 — 배당 다리를 안 팔면 얼마나 아끼나** (2026-09-03, 04 §5-38) — 원가 추적 · 손실 상계 없음 · 전환/월재조정 과세 · 검산 내장 | 세금이 격차를 **줄인다**(세전 6.84 → 세후 5.37배) · 그래도 B 우위는 유지 |
| `research/c3_placebo.py` | **[반증 2 · 플라시보] C3 관문 통과가 우연인가** — B 무작위 변형 200 · 상수 드리프트 · **뒤섞은 T-bill 200** · 반대 부호 | research/EXPLORATION.md §B-2 · 뒤섞은 T-bill 의 13% 가 C3 만큼 · 27% 가 ①② 동시 → Calmar 이득은 시점 무관 효과 · **C3 닫음** |

### 9-3. 엔진 교체 (성장 엔진을 나스닥 아닌 것으로)

| 파일 | 무엇을 쟀나 | 판정 |
|---|---|---|
| `research/eng_common.py` | 엔진·규칙·집행·관문 **공용부** — 새 시뮬레이터는 기존 곡선과 오차 0 검산 필수 | 인프라 |
| `research/eng_sp500.py` | S&P500 2배 합성 엔진 (GSPC 1970~) — 가설 A | 기각 |
| `research/eng_kospi.py` | KOSPI 2배 합성 엔진 — 가설 B (데이터 한계 명시) | 기각 |
| `research/japan_stress.py` | **일본 1989** — 「지수가 수십 년 회복 못 하면?」 54년 표본에 0건인 경우 | 전제 스트레스 |

### 9-4. 배율 (미국 직투 프레임 — 번외, 규칙 무변경)

| 파일 | 무엇을 쟀나 | 산출 |
|---|---|---|
| `research/lev_opt.py` | QQQ+TQQQ 혼합으로 k 를 연속 조절할 때 최적 배율 | **k=2 권고** |
| `research/lev_5y.py` | 「5년 투자자에게 합리적인 배율」 — CE(γ) 한계 분석 | γ→k\* 지도 |
| `research/lev_th.py` | 배율이 오르면 문턱도 바뀌어야 하나 · T4 를 고배율에 얹으면? | **−16 이 모든 k 에서 봉우리** |
| `research/lev_signal_source.py` | 신호를 기초지수 vs 레버리지 상품 자체 낙폭으로 (2026-09-03) | **단위 변환일 뿐 · 경로 의존 유입** |
| `research/tax_us_direct.py` | 전략 B ISA vs TQQQ B 직투 **세후**(원화·실물 3배 보정 · 세금 엔진 정정) | **21세기 1.76배 3배 우위 · MDD 8.1%p 악화** · 지평별 우위는 비단조 |
| `research/t4_lev_post.py` | T4 배율 2.0~3.0 × 닷컴 이후 · 끝점 고정 모든 시작일 반증 | **기각 유지** — Calmar·지연 관문 미달, 단 2010 단일창 관문은 철회 |
| `research/horizon_study.py` | 지평 3~20년 전수 — 「내 수명은 유한하다」 | **손실 0 문턱 7년** |
| `research/post_dotcom.py` | 「닷컴 뒤로 T4·라오어와 비교하면?」 | — |
| `research/slice_scan.py` | 다지평 슬라이스 스캔 — 「CT 찍듯 여러 두께로」 | 시작일 분포 판정 도구 |
| `research/goal_feasibility.py` | 「초기금+적립으로 N년 안에 목표액이 되나」 전수 창 (2026-09-03) | **5년 10억 도달 국면 1개** |

### 9-5. 측정 감사 (2026-08-31 — 자기 대표 숫자에 같은 잣대)

| 파일 | 무엇을 쟀나 | 판정 |
|---|---|---|
| `audit/test_research_review.py` | 적립식 세금·거치식 환원·현금흐름·캐시 실패·재조정·결측 비중·원화 합성 범위/비용 잔차 구분 | 오프라인 회귀 검사 |
| `research/horizon_ess.py` | 「손실 0 문턱 7년」의 **유효표본** | 비중첩 **7.9개**, 견고한 0 은 15년 |
| `research/dsr_b.py` | Deflated Sharpe 를 **B 본체**에 | DSR 1.000 — 단 변별력 없음 |
| `research/isa_pension.py` | ISA 만기 → 연금계좌 이체 (조특법 91조의18 ④) | **기각** (레버리지 IRP 매매 불가) |
| `research/tranche.py` | 트랜치 / 리밸런스 타이밍 운 (Hoffstein et al. 2020) | **기각** — 관문 ①② 미달 |
| `research/drag_sigma.py` | 달러 합성 구간의 비용 잔차 시점 민감도 — 원화 전 구간 합성과 별개 | **v210 재실행**: 달러2000~ +0.5%, 전체진단+39.9%; 원화 영향0·비용 모형 보수성은 미입증; MEASUREMENT_AUDIT §9 |
| `research/withdraw.py` | **인출(decumulation) 엔진** — 형성기 반대편 | 인출기 1년 현금 완충 |

### 9-6. 운영 · 방어 다리 · 외부 전략

| 파일 | 무엇을 쟀나 | 산출 |
|---|---|---|
| `research/ops_risk.py` | 운영 위험 6축 — 전환 놓침·종가 오입력·연속 손실 등 | 운영 규칙 3개 (04 §5-8) |
| `research/exec_cost.py` | 체결비용 실측 하네스 — 방향을 반영한 체결가÷NAV 비용 · 같은 날 체결 묶음 · NAV 없는 날 제외 | 진행 중 (**NAV 일치 실제 체결일 20일** 필요, 백업 없으면 0/20) |
| `research/def_bond.py` | 방어 국채 다리 — 헤지 상관·만기 최적 (소유자 질문) | **기각** (04 §5-16) |
| `research/def_equity.py` | 방어에 배당(주식)이 왜 있나 — 거치 후 적립 | 현행 유지 (04 §5-17) |
| `research/takeprofit.py` | 익절 규칙 — 「수익률 n%마다 전량 매도하면?」 | **기각** (04 §5-9) |
| `research/ext_ibs.py` | 외부: 라오어 **무한매수법 V4.0** vs B — 같은 54년 잣대 | 3.2배 / MDD −99.4% |
| `research/ext_vr.py` | 외부: 라오어 **VR 5.0** (거치식) vs B | 맨몸 퇴화 구조 |
| `research/surv_map.py` | 생존성 ① — B 의 생존 조건 지도(드리프트 임계) | 밴드 확정 |
| `research/surv_alert.py` | 생존성 ② — 선행 경보 검증 (임계 사후 최적화 금지) | **선행경보 없음** |

### 9-7. 옛 축 — §6 이 누락했던 것 (v40~v44)

후속 전수리뷰 및 교정 장부: `research/CODE_REVIEW_2026-09-05.md` — v204 원대상137개 파일·61건 처리표, v205 설명 정정, v207 회계 결함R01, v208 입력 검사R02, v209 모형 범위R03, v210 거래일·공표/ISA 재생성R04. 각 차수의 검토·실행 범위와 남은 한계를 분리한다. v210 이전 장기 연구는 재실행 전 현재 근거로 쓰지 않는다.
코드리뷰 전수 순회(2026-09-05 소유자 지시 · 15배치 · 순차 · 인계용 프롬프트+장부): `audit/CODE_REVIEW_SWEEP_2026-09-05.md`.
전체 감사 장부(2026-09-05 · Claude Fable 5.1 · v206): `audit/AUDIT_LEDGER_2026-09-05.md` — 코드·문서·지침·검증·자동화·데이터 계약 전 층의 기준 커밋·파일별 검토 상태·발견(심각도순)·통합/보관/폐기·실행한 검증·보고.

| 파일 | 무엇을 쟀나 | 판정 |
|---|---|---|
| `research/axis_dipbuy.py` | 낙폭을 「싸게 사는 기회」로 쓸 수 있나 (v40) | 기각 |
| `research/axis_newrule.py` | −16/−16 · −16/−11 을 능가하는 규칙 재탐색 (v41) | 통과 0 |
| `research/axis_regime.py` | 국면 적응 — 평시 공격적, 폭락 조짐이면 후퇴 (v42) | 기각 |
| `research/axis_secondary.py` | **B 확정** + 보조전략 탐색 — v21 의 A 권고 근거 재측정 (v43) | A 근거 2개 오류 |
| `research/axis_objective.py` | 목적함수를 바꾸면 답이 달라지나 (v44) | 결론 불변 |
| `research/axis_hedge_cost.py` | 헤지 60/40 거래비용 민감도 — 구조적 견고성 (v73) | 견고 |

### 9-8. 배포 보조 · 워크플로

| 파일 | 역할 |
|---|---|
| `deploy/stamp_rev.py` | 배포본에 **화면 개정 시점**을 박는다 — signal.html 커밋 제목의 vNN 을 추출(그래서 커밋 제목에 vNN 필수) |
| `deploy/wait_close.py` | **[v75]** 종가 확정 대기 루프 — GitHub 예약 실행이 슬롯을 통째로 건너뛰는 실측 사례에 대응. **[v190] 마감 전에 뜨면 마감까지 자고 20초 간격으로 종가가 굳는 순간을 잡는다**(쓰기 전 30초 안정 확인 · 큰 움직임이면 대조 소스 CLOSE 까지 최대 15분 대기 · 마감 뒤 8분 안 굳으면 조용히 종료해 다음 슬롯에 맡김). `--selftest` 가짜 시계 9경로 |
| `.github/workflows/monthly-stats.yml` | 매월 1일 원자료·성과표·지평표 최신화. 정확한 산출물만 스테이징하고 검증 통과 시 커밋하며, push 경합은 rebase하지 않고 실패-폐쇄해 최신 HEAD 수동 재실행에 맡긴다 |
| `.github/workflows/notify-test.yml` | **[v76]** secret 등록 후 알림 채널 수동 연결 확인. 예약 실행 없음 |

### 9-9. 화면·시세 (v142~v147)

| 파일 | 역할 |
|---|---|
| `deploy/price_now.py` | **[v145] 4다리 시세 스냅샷** → `data/price.json`. 출처는 `nav_collect.py` 와 **같은 엔드포인트**(네이버 ETF 목록, cp949) — 새 의존성 0. 가격·등락률·NAV·괴리율. **★ 표시 전용 · 판정 무접촉** (실패해도 신호 무영향이라 항상 exit 0, 기존 파일을 덮어쓰지 않는다) **[2026-09-03] 1차(네이버 목록) 실패·종목 누락 시 `kr_sources` 예비 체인이 그 종목만 채움** — `source` 필드에 출처 표기 · **[v200] 예비 가격 가드** — nav_history 마지막 종가와 25% 넘게 어긋나면 싣지 않음 |
| `deploy/kr_sources.py` | **[2026-09-03] 한국 시세 예비 출처 체인** — 네이버 polling → 네이버 모바일 → 다음(카카오) → 토스 → 야후 → 구글(HTML). `quotes(codes)` 는 네이버 목록 모양(NAV 없음)으로 돌려줘 `price_now.build` 가 그대로 먹는다 · `history_df` 는 네이버 일봉 XML(수정주가 아님) · `--probe` 생존 표. **표시·기록·원자료 전용 — 판정 경로엔 없다**(verify_all 관문) | 실측 2026-09-03 KR IP: 6/6 응답 · 값 일치 |
| `deploy/price_poll.py` | **[v190/v203] 장중 시세 폴러** — 한 실행 안에서 5분 경계를 지킨다. 검증된 한국 휴장일 표가 없거나 범위 밖이면 거짓 신선도를 만들지 않고 중단한다. 값이 바뀌면 price-data 브랜치를 커밋 1개로 덮어쓰고 Pages를 깨운다. `--selftest`(요일·구간·정렬·휴장·하루 85스냅샷) |
| `.github/workflows/price.yml` | **[v145/v203]** 개장 전 08:30·08:40·08:50 KST **월~금** 슬롯(UTC 일~목)과 매시 예비 슬롯. 월요일 누락·토요일 오실행을 정적 관문으로 막는다 |
| `research/emit_dd_distribution.py` | **[v164] 낙폭 백분위 산출** → `data/dd_percentile.json`. `hist_defensive.build('chain')['ddv']` 를 **읽기 전용**으로 써 1~99 백분위 경계를 뽑는다. **[v197] `monthly-stats.yml` 이 원자료 연장 직후 매월 돌린다**(1초 · 같은 원자료면 산출 동일). v164 의 「연 1회 수동」은 원자료 연장이 자동인데 파생물만 수동이라 조용히 낡는 구조였다 |
| `data/dd_percentile.json` | **[v164]** 위 산출물. 화면이 「오늘 낙폭이 54년 중 어느 깊이인가」를 말할 때 읽는 자. **판정에 쓰지 않는다** |
| `data/price.json` | **[v145·v176]** 위 산출물. 화면 `loadPrice()` 가 읽어 배지·현재가 기본값에만 쓴다. **`update_signal.py` 가 이 파일을 읽으면 verify_all 이 실패한다**(동결 규칙 보호). ★ **v176 부터 main 에 없다** — `price-data` 브랜치(항상 커밋 1개)가 원본이고 `.gitignore` 에 있다. 배포가 그 브랜치에서 가져오며, **못 가져오면 싣지 않는다** (옛 값을 새 값인 척 보여주지 않는다) |
| `notes.html` | **[v142] 업데이트 노트 — 세 번째 탭.** 단일 파일·바닐라, guide.html 토큰 그대로. 항목마다 **무엇이 / 왜 / 결론** 3필드. 최상단에 「매매 규칙은 한 번도 바뀌지 않았습니다 · 변경 0회」 + 동결 후 경과일(`data/freeze.json` 을 읽고 실패 시 하드코딩 날짜). 필터 4종·시즌 5개·v122 이전은 접힘. **내용은 git 이력·CLAUDE.md §4 에서 뽑은 실제 사건만** |
