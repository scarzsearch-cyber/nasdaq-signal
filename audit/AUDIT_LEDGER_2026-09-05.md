# 전체 감사 대장 — 2026-09-05 (Claude Fable 5.1 · v206)

> **목적**: 소유자 지시(2026-09-05) 「프로젝트 전체에서 전수조사할 가치가 있는 모든 파일과 연결 관계를
> 검토하고 확인된 결함을 개선」. 변경 파일만 보는 리뷰가 아니라 코드·문서·지침·검증·자동화·데이터 계약 전체.
> **이 파일은 진행 기록이다** — 중단 후 다른 세션이 이어갈 수 있게 기준 커밋·검토 상태·미결을 남긴다.
> 결론 문서가 아니라 작업 장부다. 최종 보고 요지는 §6.

## 0. 기준과 경계

| | |
|---|---|
| 기준 커밋 | `53aab70` (v205 · 2026-09-05 05:4x KST · main = origin/main) → 수정 커밋은 v206 |
| 직전 검토 | Codex v204(`48da82d`) research 129+8 전수 · v205(`ab00046`·`53aab70`) 후속 — `research/CODE_REVIEW_2026-09-05.md` |
| 재사용 원칙 | v204 검토 결과는 **기준 커밋·입력·변경 여부가 확인된 파일**에만 재사용. research/*.py 는 v204 이후 `tax_us_direct.py`(ab00046) 외 무변경(`git diff --stat 48da82d..53aab70 -- research/` 확인) → 공용 엔진 계약·아티팩트 생성 경로·최근 수정분만 재판독 |
| 유지 경계 | 전략 B 동결값(252·−16/−16·40/40/20) · `data/freeze.json` · `data/oos_log.csv` · `data/nav_history.csv` 무수정(D-10 의 옛 4행도 그대로). 규칙 채택·새 최적화 없음. 자동 주문 없음 |
| 공표 지문 | `verify_all` I7·I11 PASS(us_1972 B 217,110.075) · 수정 전후 `strategy_stats.json` 무접촉 |
| 목표 분석 분리 | 소유자 장기 목표 **7년 5억 · 10년 10억(원화)**. 현재 투자금·월 납입·감수 손실·세후 기준·총자산/순수익 여부 **미확인** → 추측하지 않고 코드·문서 검토와 분리(§7) |
| 추론 강도 | 이 환경은 xhigh/max/ultra 전환 수단이 없다. 현 설정 그대로 진행했고 전환했다고 보고하지 않는다. `/code-review ultra` 는 소유자만 실행 가능 |

## 1. 파일 분류 (추적 448개 · 기준 커밋)

| 층 | 경로 | 수 | 검토 방식 |
|---|---|---:|---|
| ① 운영·계산·화면·자동화 | `deploy/*.py`(17) · `signal.html` `guide.html` `notes.html` · `.github/workflows/*.yml`(8) · 루트 엔진 14 (`reentry_lib` `axis_lib` `axis_defmix` `axis_volguard` `hist_*` 8 · `hyst_core` `research_kit`) · `내가_보는_것/점검.py` · `manifest.json` 아이콘 2 | 49 | 전문 판독 + 실행 |
| ② 테스트·검증·감사 | `verify_all.py` · `audit/*.py`(5) | 6 | 전문 판독 + 실행 + 반례 |
| ③ 현재 규칙·설명·결론 문서·AI 지침 | `CLAUDE.md` `AGENTS.md` `HANDOFF.md` `README.md` `FILES.md` `01~04_*.md` · `research/*.md`(9) · `내가_보는_것/*.md`(2) · `deploy/README.md` `archive/README.md` `docs/HANDOFF_전체이력.md` `공유용_별도전략/README.md` | 25 | 전문 판독 + 교차 대조 |
| ④ 원자료·장부·설정·산출물 | `data/*.json·csv`(14) · 루트 `qqq/qld/schd_us_d.csv` `hyst_wfa.csv` `fixed_wfa_hist.csv` · `data/hist/*`(82) | 101 | 기계 검증(구조·날짜·결측·중복·범위·생산자/소비자) |
| ⑤ 역사 보관·별도·캐시·개인 | `docs/history/*`(59) · `docs/raw/*`(40) · `archive/*`(29) · `공유용_별도전략/*`(13) · `.codex-remote-attachments/`(미추적) | 141+ | 존재·역할·현재 사용 여부만. 내용 전수 판독 제외 — 이유: §2 보관층·별도 전략(결론 혼입 금지). 대체 검증: I9 정정 배너 관문·격리 관문(g_isolation) |
| ⑥ 연구 재현 코드 | `research/*.py`(129) | 129 | v204 전수 재사용 + 표본 재판독 |

## 2. 파일별 검토 상태

기호: ✅ 전문 판독 · ▶ 실행 확인 · 🔁 v204 재사용(변경 없음 확인) · ➖ 제외(이유 §1) · 🧪 반례 재현

### ①② 운영·검증
| 파일 | 상태 | 비고 |
|---|---|---|
| `verify_all.py` | ✅▶🧪 | 전체 모드 실패 0·경고 0 (10초). 새 관문 3개(§3 W-2·D-10) — 훼손 시 FAIL 재현 |
| `.github/workflows/*.yml` 8종 | ✅ | W-1 · **W-2(P1)** |
| `deploy/update_signal.py` | ✅ | D-6 · docstring(A 선택) 정정 |
| `deploy/wait_close.py` | ✅▶ | `--selftest` 9경로 PASS |
| `deploy/oos_log.py` | ✅ | 이상 없음 |
| `deploy/nav_collect.py` | ✅▶🧪 | **D-10(P2)** 장중 적립 금지 · `--selftest` 반례 6개 추가 PASS |
| `deploy/watchdog.py` | ✅▶ | `--selftest` 28경우(I14) PASS |
| `deploy/refresh_hist.py` `build_stats.py` `data_check.py` `stamp_rev.py` `kr_holidays.py` | ✅ | 이상 없음 (I14 셀프테스트 PASS) |
| `deploy/price_poll.py` `price_now.py` `kr_sources.py` | ✅ | price_now docstring 「30분」 정정 |
| `deploy/notify.py` `signal_alert.py` `kakao_*.py` | ✅▶ | I14 PASS |
| 루트 엔진 14 | ✅ | v203 리뷰 반영 확인 · 공표 지문 불변 |
| `signal.html` | ✅ | `.opill.ok` 토큰 · 재조정 문구(D-6) · nav 주석 정정 |
| `guide.html` | ✅ | D-8 · D-3 |
| `notes.html` | ✅ | D-9 · v206 항목 |
| `audit/audit_all.py` `audit_full.py` `verify.py` `verify_volguard.py` `test_research_review.py` | ✅ | verify.py 표시(구 A 재현) · E 관문 앵커 보류(§3) |
| `내가_보는_것/점검.py` | ✅▶ | `--json` level 0 ok |

### ③ 문서·지침
| 파일 | 상태 | 비고 |
|---|---|---|
| `CLAUDE.md` `AGENTS.md` `HANDOFF.md` `README.md` `01~03` | ✅ | D-1·D-4·D-5·D-7 · v179 문단 · push 경쟁 항목 정정 · v206 항목 |
| `FILES.md` | ✅ | audit 수 · verify.py 표시 · 대장 등재 · deploy/README |
| `04_Rejected_Research.md` | ✅ (전 3,248줄) | 내부 모순 0 — §5-23 21건·§5-31 E 대리/DVY 정합·§5-38 정정 표기 |
| `research/*.md` 9 | ✅ | FINAL_AUDIT 설명서 절 번호 3곳 정정 · LEVERAGE_US §11-13 「아티팩트 미갱신」 줄은 아티팩트 재발행 뒤 갱신 |
| `내가_보는_것/*.md` | ✅ | D-3 |
| `deploy/README.md` | ✅ | **D-2 전면 재작성** · 옛 본문 `docs/history/deploy_README_v18_원본.md` |
| `archive/README.md` `공유용_별도전략/README.md` `docs/HANDOFF_전체이력.md`(개요) | ✅ | 이상 없음 |

### ④ 데이터 계약
| 파일 | 상태 | 비고 |
|---|---|---|
| `data/freeze.json` `oos_protocol_b.json` `ops_check.json` `signal_alert_state.json` `manifest.json` | ✅ | |
| `data/signal.json` `strategy_stats.json` `qqq.csv` `oos_log.csv` `nav_history.csv` `kr_holidays.json` `dd_percentile.json` `isa_stats.json` `retired_numbers.json` | ▶ | 구조·날짜·중복·연속성 통과 · **nav_history 09-01~04 행이 종가가 아님을 외부 대조로 확인**(D-10) |
| `data/hist/*` 82 | ➖ | 월간 `refresh_hist` 셀프테스트·`data_check.py`(I14)로 대체. 개별 내용 판독 안 함 |

### ⑥ research/*.py
| 대상 | 상태 | 비고 |
|---|---|---|
| 129개 | 🔁 | v204 전수 + `tax_us_direct.py --accum` 재실행(D-8 근거) · `test_research_review.py` 13건 CI 통과 |

## 3. 발견 사항 (심각도순 · 번호 고정)

> 등급: **P1** 실제 매매·알림·판정에 틀린 값이 갈 수 있음 / **P2** 계산·판정·기록이 틀리거나 검증이 비어 있음 / **P3** 낡은 설명·혼동 위험 / **P4** 개선

| ID | 등급 | 파일:위치 | 내용 · 조건 · 영향 · 근거 | 상태 |
|---|---|---|---|---|
| **W-2** | **P1** | `.github/workflows/daily-signal.yml` 체크아웃·「변경분 커밋」 | 예약 실행은 큐에 들어갈 때의 커밋(github.sha)을 체크아웃 → 마감 전 슬롯 둘이 함께 큐에 들면 둘째가 첫째 커밋 이전 main 으로 같은 종가를 재계산 → push non-fast-forward → **매일 실패 카톡 1통**(gh run list 09-03·04·05 04:48 슬롯 failure · 로그 「! [rejected] main -> main (fetch first)」 · 「카카오톡 나에게 보내기 전송 (1건)」). 전환일엔 둘째 슬롯의 옛 상태 파일로 **같은 전환 카톡이 두 번** 갈 구조 | **수정** — 체크아웃 뒤 `fetch`+`reset --hard origin/main` · push 직전 원격이 같은/더 새 as_of 면 정상 종료, 아니면 v203 실패-폐쇄. 로컬 git 사바독스 4케이스 재현 · `verify_all` 관문 2개(훼손 시 FAIL 재현) |
| **D-10** | **P2** | `deploy/nav_collect.py` · `data/nav_history.csv` | 09:17 슬롯(장 개장 뒤 09:3x)이 개장 직후 값을 그날 행으로 적고 그 행은 다시 고쳐지지 않음 → `close`·`nav`·`dev_pct` 가 종가 기준이 아님. **외부 대조**: 네이버 일봉 09-04 종가 38,585·거래량 178,498 vs 장부 38,680·47,392(09-01·02·03 도 불일치, 08-31 이전은 일치). 소비자: 화면 `curPx()` 폴백 · `price_now` 25% 가드 기준 · `exec_cost.py` NAV 대조 · 괴리율 σ 통계 | **수정** — 한국장 개장 중(거래일 09:00~15:30) 적립 금지 `kr_market_open()`, 다음 장 밖 슬롯이 직전 거래일 종가로 적음. 셀프테스트 반례 6(개장·마감·휴장·주말·fetch 미호출) · `verify_all` 관문. **옛 4행은 장부(§2)라 그대로** — CLAUDE·signal.html 주석에 「종가 아님」 명기 |
| D-6 | P2 | `deploy/update_signal.py` DEFENSIVE · `signal.html` defHtml | 카드가 「도피 구간 안에서 월 1회 (5%p …)」(v23) 를 그리면서 같은 카드의 D-day 는 「진입일부터 30일마다」(v117) → 규약 둘이 한 화면 | **수정** — 30일 규약 문구로 통일 · `data/signal.json` 의 그 필드 1개만 동일 교정(구조·판정 필드 불변 검증) |
| D-8 | P2 | `guide.html` ④-6 | ISA 한도 손해 「월 100만 · 20년 0.5% · 30년 3%」는 옛 세금 엔진 값. 현행 재계산: 20년 요인분해 한도 +1.82%(→ B −1.8%) · 30년 한도 무한 1,429.21억 vs 실제 1,391.07억(−2.7%) | **수정** — 약 1.8%·2.7% + 출처(§11-2·§11-7 · `--accum` 재실행으로 재현) |
| A-1 | P2 | 소유자 아티팩트 「전략 B 배합 탐색기」 배율 탭 | 「읽는 법」이 v203 교정 이전 값(146.1 vs 146.6 동률 · 손익분기 2.5~2.7 · 0.91배 · 62.8 vs 55.7 · 「세금 격차는 버블 탓 아님」 · 「환 효과 없음」)을 그대로 실음 — 결론 박스(원화 v2)와 한 화면 안에서 모순 | **재발행** — §5 ⑥ |
| D-2 | P3 | `deploy/README.md` | v18 설치 안내(stooq · 22:30 UTC 단일 슬롯 · 두 전략 화면 선택 · build_stats 수동 커밋)가 현행과 정면 충돌 | **수정** — 현행 안내로 재작성 · 옛 본문 `docs/history/deploy_README_v18_원본.md` 보관(배너) |
| D-1 | P3 | `README.md` §1 | 복귀 행이 규칙 A 를 선택지처럼 표기 | **수정** |
| D-3 | P3 | `내가_보는_것/운영_점검표.md` §5 · `guide.html` ⑧ | 「탭 두 개」「이 두 화면」 — v142 부터 세 개 | **수정** |
| D-4 | P3 | `03_System_Params.md` §3 · `README.md` §3 | verify.yml 이 push 에 `--fast` 만 부른다고 적힘(v172 부터 전체도) | **수정** |
| D-5 | P3 | `02_Risk_Management.md` §1-1 | 「10년 손실 0 (535창)」에 유효표본 병기 없음 — CLAUDE §4 측정감사 규약 | **수정** — 비중첩 5.5/2.8 · 부트 68% 병기 |
| D-7 | P3 | 02 §1-1 ↔ 설명서 ②·LEVERAGE_US §9 | 같은 지평 표가 규약(월/일 시작점 · 편도 0.2/0.1%)이 달라 값이 다름(10년 9.1 vs 9.96배) | **수정** — 02 에 규약 차이 병기(통일 안 함 — 둘 다 재현 스크립트 있음) |
| D-9 | P3 | `notes.html` v201 · `CLAUDE.md` v141·v201 | `#manual` 을 「설명서 ⑩」으로 지목(v167 재배열 뒤 ⑧) | **수정** |
| W-1 | P4 | `.github/workflows/pages.yml` | `workflow_run` 구독이 일일신호·price 뿐 — 월간 성과 봇 커밋은 다음 시세 폴링/일일 신호까지 미반영 | **수정** — 「월간 성과 스냅샷 갱신」 추가. 파수꾼은 09:00 시세 폴러 배포가 끌고 가므로(설계 주석) 미추가 |
| P4-a | P4 | `signal.html` `.opill.ok` | 정의된 적 없는 `--defense` 토큰(자동 점검 알약 색이 상속색) | **수정** → `--defend` |
| P4-b | P4 | `deploy/price_now.py` docstring · `update_signal.py` docstring | 「30분 간격」(v190 부터 5분) · 「화면에서 고른다」(v168 부터 B 만) | **수정** |
| P4-c | P4 | `CLAUDE.md` v179 문단 · `signal.html` curPx 주석 | 「당일분에 한해 종가가 아니다」 — 실제는 09:17 슬롯이 적은 행 전부 | **수정**(D-10 과 함께) |
| P4-d | P4 | `audit/verify.py` · `FILES.md` | v17 규칙 A(−16/−11·SCHD 단독) 재현인데 「채택안 단독 검산」으로 표기 | **수정** — 구 채택안 표시 |
| P4-e | P4 | `research/FINAL_AUDIT.md` | 옛 설명서 절 번호 3곳(§5·§6·§3-4) | **수정** |
| P4-f | P4 | `.gitignore` | `.codex-remote-attachments/`(외부 세션 첨부 jpg 2) 미등재 | **수정** |
| P4-g | P4 | `data/retired_numbers.json` | 옛 세금 엔진 값(146.6배 · 1.00배 동률 · 62.8 vs 55.7) 미등재 · allow_context 에 「철회」 없음 | **수정** — 3종 등재 + 철회 허용(I9 PASS) |
| P4-h | P4 | `audit/audit_all.py` E 관문 | 앵커 214,076(v36 시절)·현행 217,110 — ±2% 안에서 통과 | **보류** — 이력 앵커로 동작 중. 바꿀 이유 없음 |
| A-2 | P3 | 아티팩트 배합 탭 `DATA.rows` | 생성 스크립트가 저장소에 없음(재현 불가 표) | **판단 보류** — 표를 지우지 않고 「재현 스크립트 없음」 표시(§5 ⑥) |
| N-1 | 정보 | `04` §5-23·§2-0·CLAUDE v131 | 「독립 위기 19회」「독립 사건 21」「독립 사건 22→21」이 **정의가 다른 셋** — 04 가 이미 「섞어 쓰지 말 것」 명기 | 조치 없음 |

## 4. 통합·보관·폐기

| 대상 | 분류 | 근거 | 복구 |
|---|---|---|---|
| `deploy/README.md` 옛 본문 | **역사 보관** → `docs/history/deploy_README_v18_원본.md` | D-2 | 파일 그대로 남김(배너 포함) |
| `AGENTS.md` | 유지(한 줄 진입점) | v205 | — |
| `.codex-remote-attachments/` | 미추적 유지 · `.gitignore` 등재 | 외부 세션 첨부 | 로컬 폴더 무접촉 |
| `archive/` 3폴더 · `docs/raw/` 40 · `docs/history/` 59 | 유지 | 기각 근거·버전 원본 · I9 배너 관문 | — |
| `audit/verify.py` | 유지(구 A 참조 구현 표시) | P4-d | — |
| 폐기 | **0건** | 파일 수 축소는 목표가 아님(소유자) · 활성 .md 겹침 최대 6.0%(2026-09-03 실측) | — |

## 5. 실행한 검증 (읽기 ≠ 실행 구분)

1. `python verify_all.py`(전체) 수정 전·후 **실패 0·경고 0** (10초 · I1~I14 + 관문 전부).
2. **반례 재현**: 새 관문 3개를 각각 훼손 → FAIL 1건씩 · 복원 → 0건 (`gate_counterexample.py`, 스크래치).
3. **push 경쟁 로컬 재현**(`push_race_sim.sh`, 임시 bare 저장소): 원격 정지→push · 같은 as_of→exit 0 · 더 새 as_of→exit 0 · 코드만 이동→exit 1. 4/4 설계대로.
4. `deploy/nav_collect.py --selftest`(반례 6 추가) · `wait_close.py --selftest` · I14 의 16종 셀프테스트 PASS.
5. **외부 대조**(읽기 전용 HTTP): 네이버 일봉 418660 08-26~09-04 종가·거래량 vs `nav_history.csv` — 08-31 이전 일치, 09-01~04 불일치(D-10 근거). price-data 브랜치 09-04 15:55 스냅샷 38,585·178,498 = 네이버 종가.
6. `research/tax_us_direct.py --accum` 재실행: 요인분해 1.16643→1.42129→1.44709→1.45247→1.45241 · 30년 한도 무한 1,429.21억 vs 실제 1,391.07억 (D-8 근거).
7. YAML 파싱(daily-signal · pages) · `gh run list`(09-03~05 실패 슬롯 확인) · CI: 기준 커밋 검증·배포 success.
8. 데이터 구조 검사(§2 ④) · 점검.py `--json` level 0.
9. **실행하지 않은 것**: research/*.py 129 중 `tax_us_direct.py` 외 개별 재실행(v204 결과 재사용) · `audit/audit_full.py`(CI 예약 슬롯 몫) · 카톡 실제 도착(자동 검증 불가 — v178) · 새 워크플로 스텝의 GitHub 러너 실행(다음 거래일 새벽 슬롯에서 확인 — §6 남은 위험).

## 6. 보고 요지 (최종 보고는 대화에 — 여기엔 다음 세션용 요약)

- **전략 B·장부 무변경.** 공표 지문 불변. 바뀐 것은 자동화의 오탐 1(P1)·장부 의미 1(P2)·화면 문구 2(P2)·낡은 문서 다수.
- **다음 거래일(2026-09-08 월) 새벽에 확인할 것**: `gh run list --workflow=daily-signal.yml` — 04:35/04:45 두 슬롯 모두 success 이고 둘째가 「이미 최신」으로 짧게 끝나는가 · 실패 카톡이 안 오는가 · 09:17 슬롯 로그에 「한국장 개장 중 - 장중 값은 적립하지 않는다」가 찍히고 09-08 행이 09-09 새벽에 종가로 적히는가.
- **남은 위험(우선순위)**: ① 새 스텝의 러너 실측 전(위 확인) ② `nav_history` 09-01~04 행은 종가가 아님(인용 금지 표시만) ③ 아티팩트 배합 탭 표는 재현 스크립트 없음 ④ 30년 창 비중첩 1개 등 표본 한계(문서에 병기됨) ⑤ 카톡 도착은 자동 검증 불가.

## 7. 목표 분석 (코드 검토와 분리 · 미확인 입력은 추측하지 않음)

소유자 목표(2026-09-05): **7년 내 5억 · 10년 내 10억(원화)**. 현재 투자금·월 납입·감수 손실·세후 기준·총자산/순수익 여부는 **확인되지 않았다.**
저장소가 이미 잰 인접 결과(`research/goal_feasibility.py` · CLAUDE §4 2026-09-03 항목): 「1,000만 + 월 100만 · 5년 10억」은 달성률이 아니라 **국면 수(1개)** 로 읽어야 하며, 월 100만 유지 시 중앙 도달 **5억 2배 9.4년 / 3배 7.3년 · 10억 11.6 / 10.0년**. 새 목표(7년 5억 · 10년 10억)를 같은 도구로 재는 것은 입력 5개가 확정된 뒤의 별도 작업이다 — 이번 감사에서는 수치를 만들지 않았다.
