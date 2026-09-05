# 저장소 검사 현황표 (2026-09-06 · 검사 실행 없음 · 추적 파일 × 감사 장부 대조)

> 기준 017e2e6. `git ls-files` 추적 파일 전부(492)를 **파일·기능 묶음**으로 나누고, 기존 감사 장부(audit/*.md · research/CODE_REVIEW_2026-09-05.md)·
> 회귀 모듈(audit/test_*.py)·상시 관문(verify_all)·셀프테스트(I14)에서 그 파일이 **실제로 다뤄진 근거**를 대조했다(`audit/coverage_map.py` 가 생성 ·
> 검사를 새로 돌리지 않았다). **이 표는 저장소 전수검사 완료를 뜻하지 않는다** — 근거가 있는 곳과 없는 곳, 근거의 강도를 가르는 지도다.

## 검사 수준 (같은 「완료」로 섞지 않는다)
| 수준 | 뜻 | 근거 예 |
|---|---|---|
| L0 미검증 | 어떤 장부·회귀·관문에도 이름이 없다 | — |
| L1 열람·대조 | 열어 봤거나 결과 수치만 대조 · 문자열 관문 | 인계 교차검증 · verify_all 문자열 검사 · 장부 언급 |
| L2 전문 판독 | 파일 전문을 읽고(대개 실행·수정 포함) 판정 | 순회 B01~B15 · v206 전체 감사 · research 리뷰 v204~v209 |
| L3 함수 검토·회귀·관문 | 함수 단위 반례·회귀 모듈·재계산 관문·셀프테스트 | v220/v221 · test_*.py · verify_all I1~I13 · I14 |
| L4 연결·실측 | 여러 부품을 **이어서** 돌리거나 실제 환경(브라우저·러너·dispatch)에서 잰 것 | v222 · 파수꾼 연결 · pages 실측 · 화면 상태 행렬 |
| L5 변조 | 관문 자체가 실패해야 할 때 실패하는지 | 관문 변별력(verify_all 만) |
| n/a | 검사 **대상**이 아니거나 내용 검증이 정의되지 않는 파일 | 보관본 · 격리 폴더 · 원자료(갱신 코드 기준) · 생성물(생성자 기준) · 장부(지문 감시) · 검사 도구 자신 |

## 담당 구분 (확인 가능한 근거로만)
- **돈전략(확인)** — 소유자 지시(2026-09-05 「배당·가격조정·보유시점 연구·원자료」 · 2026-09-06 「research·F계열·전략 계산·동결값·실측 장부·원자료」)로
  확인된 범위: `research/strategy_f1~f4_*.py`(8) · 루트 전략 계산 엔진(13) · `data/freeze.json`·`oos_protocol_b.json`·`oos_log.csv`·`nav_history.csv` · 원자료(87).
- **담당 확인 필요** — 그 밖의 research 스크립트(134)·research 문서(10)·`research_kit.py` 계열 1: 「research 전체」가 돈전략인지, 배당·가격조정·보유시점 세 주제만인지
  인계문으로 확정되지 않았다. 일괄 제외하지 않고 표시만 한다.
- **운영(이번 범위)** — deploy·워크플로·화면·검사 도구·문서·생성물·소유자 안내.

## 묶음별 요약과 미검증 범위
| 묶음 | 근거의 성격 | 미검증·한계(장부 「남은 한계」에서) |
|---|---|---|
| 운영 스크립트(18) | v220/v221 함수 검토 → v222·파수꾼·pages 연결 실측 · I14 셀프테스트 | 실제 카톡 도착(자동 검증 불가) · 러너 지역 차단은 source-probe 1회 · 특별 휴장 · 분할 발송 중복(설계) · 60일 무활동 규칙(문서 없음) |
| 워크플로(8) | g_deploy 문자열 관문 + 셸 추출 연결 검사(daily-signal · watchdog 주간 커밋) + pages dispatch 실측 | 잡 수준 concurrency 「건너뛴 잡 미진입」은 실측 1회 · 주간 커밋 non-ff 이슈 본문 · monthly-stats·notify-test·source-probe 는 문자열 관문·열람 수준 |
| 화면(6) | v202 15건 실측 · v223 15상태 · v224/v225 412px 8흐름 · 다크 모드 신호 화면 | PWA standalone 실행 · 폰 실기기 Web Share 도착 · 설명서·노트의 다크 모드 희귀 상태 · 라이트 알약 대비 4.0:1 · 접힌 참고 패널의 **수치** 정확성(표시 검사만) |
| 검사 진입점(2) | verify_all: 변조 127/127 · research_kit 자기검사(CI) | 변조로 못 재는 I1 엔진 내부·I5 「B>A」류·I10 전제 감시(자료 의존) |
| 검사 도구·회귀·장부(35) | 도구 자신은 대상 아님 · audit_all/verify.py 는 순회 B02 전문 | 회귀 모듈이 옛 사본에서 실제 FAIL 하는지는 각 장부에 기록(전부 확인) · 간헐 실패 1건 원인 미확정(bare 클론) |
| 전략 계산 엔진(13 · 돈전략) | 2026-09-04 역사 엔진 14건 · v203 axis_lib · 순회 B03 · I1~I3·I7·I8 봉인·재계산 | v210 자료 변경 뒤 재실행은 공표 4시나리오·96조건 지문에 한정 · 원자료 교차 출처 차이 미판정(04 §7 Q10) · **담당 돈전략** |
| research F계열(8 · 돈전략) | test_f1~f4 회귀 + research 리뷰 | 원화 계좌·세금·시점 반증 미완료(CLAUDE v213) · **담당 돈전략** |
| research 스크립트(134 · 담당 확인 필요) | 순회 B05~B15 전문 판독+실행(2026-09-05) · v204~v209 리뷰 · 22편은 회귀 모듈 | 「재실행 없이 불변이라 쓰지 마라」(v210) — 이후 변경 0 이지만 자료가 바뀌면 다시 돌려야 함 · 연결 검사 없음 |
| research 문서(10) | 순회 B05 · v212 정정 | v210 전 수치 배너 5편 · 요약 오류(주어 바뀜) 유형은 관문 밖(04 §7) |
| 문서(루트·docs 10) | v206 전체 감사 · I9 폐기수치·g_toc·g_notes_lag 관문 | 01~04 요약 행의 인용 오류 전수 대조 미완(04 §7 대장) |
| 생성물(9) | 생성자 코드(build_stats·update_signal·emit_dd·kr_holidays·watchdog) + I6/I7 재계산 대조 | 파일 내용 자체를 독립 검산한 것은 signal.json(I6)·strategy_stats(I7 us_1972 B)뿐 |
| 원자료(87 · 돈전략) | 갱신 코드 refresh_hist(v220·v222) · data_check 셀프테스트 | 내용 검증 아님 · 교차 출처 차이 미판정 · **담당 돈전략** |
| 실측 장부·동결값(4 · 돈전략) | I11 지문·행수 · I13 규약 지문 · g_freeze_seal 봉인 | 내용은 §2 불변 · 2026-09-01~04 NAV 4행은 종가 아님(v206) |
| 보관본(130) · 공유용 격리(14) | 대상 아님(§2 · g_isolation 만) | — |
| 소유자 안내·점검(3) | v206 전문 · 파수꾼 연결(점검.py 출력 계약) | 감시 밴드 v210 재계산 반영은 소유자 결정 대기 |

**검사 후 변경**(부록 「변경」열): `signal.html`·`notes.html`·`CLAUDE.md`·`verify_all.py` 는 v225/v226(문자열·CSS·라벨 한 줄)이 마지막 실측 장부보다 뒤 커밋이다 —
그 변경분은 각 커밋의 회귀(test_ops_review2 Node 하네스 · 대비 실측 · verify_all)로 덮였고 전면 재실측은 하지 않았다. `audit/test_f4_products.py`·`CODE_REVIEW_SWEEP` 는
다른 세션 커밋(F4 후속)이다.

## 최종 인계에 명시할 규약 변경 (2026-09-06)
1. **`biz_days_since` / `bizDaysSince` 의 뜻이 바뀌었다** — 「평일 수」→「**미국 거래일 수**(주말 + NYSE 정기 휴장 제외)」. 신호 `as_of` 는 미국 종가일이라서다.
   판정(state)과 무관 · 파수꾼 stale/near/heartbeat 와 화면 신선도 점·배너·「동결 후 N거래일」 표시만. 한국 시세·NAV 는 종전대로 한국 달력(`kr_biz_days_since`).
   특별 휴장은 표에 없어 하루 이르게 센다(보수적). 이 함수를 쓰는 다른 도구가 있으면 의미 변경을 반영할 것.
2. **`ops_check.json` → `protocol_b.verdict` 에 `drift` 추가** — 평가기 rc 2(기저율 표류)를 `error`(평가 실패)와 갈랐다. `PB_RANK` 는 warn/error 와 같은 1등급(악화 알림 규칙 동일).
   화면 PBV 「기저율 표류 — 재등록 필요」. 평가기(research/oos_protocol_b.py)는 무변경.

## 남은 검사 후보 (돈전략 담당 외 · 영향도 순 · 제안만 · 착수하지 않음)
1. **알림 도착의 실기기 확인** — 전환일 실행 사슬의 마지막 고리(카톡 도착·Web Share)는 자동 검증이 불가능하다(v178·v193). 다음 실제 전환·근접 알림 때 소유자가 받았는지 한 번 확인.
2. **60일 무활동 규칙 실증** — 봇 커밋이 「활동」으로 쳐지는지 문서가 없다(v176 ⓕ). 실패하면 전 자동화가 멈춘다. v177 생존 알림이 감시하지만 실증은 아직.
3. **01~04 요약 행의 인용 오류 전수 대조** — 「주어가 바뀐 요약」 유형(v186)은 관문 밖이다(04 §7). research 수치와 맞닿아 **담당 확인 필요** 부분이 있다.
4. **PWA standalone·폰 실기기 표시** — 에뮬레이션 불가 항목. 소유자 실기기 한 번.
5. **설명서·노트의 다크 모드 희귀 상태와 라이트 알약 대비(4.0:1)** — 낮은 영향.
6. **verify_all 관문 변별력이 못 재는 자료 의존 감시(I1·I5 「B>A」·I10)** — 자료가 바뀔 때 실패하는 검사라 변조로 못 잰다. 대안은 자료 변경 시 재실행 규약(이미 v210 원칙).

## 요약 (묶음별)

| 묶음 | 파일 수 | L0 | L1 | L2 | L3 | L4 | L5 | n/a | 검사 후 변경 | 담당 |
|---|---|---|---|---|---|---|---|---|---|---|
| research 연구 스크립트 | 134 | 0 | 0 | 111 | 22 | 1 | 0 | 0 | 0 | 담당 확인 필요 |
| 보관본 | 130 | 0 | 0 | 0 | 0 | 0 | 0 | 130 | 0 | 검사 대상 아님(§2 읽기 전용 · 보관) |
| 원자료 | 87 | 0 | 0 | 0 | 0 | 0 | 0 | 87 | 0 | 돈전략(확인 · 원자료) |
| 검사 도구·회귀·장부 | 35 | 0 | 1 | 2 | 1 | 2 | 0 | 29 | 2 | 운영(이번 범위) |
| 운영 스크립트 | 18 | 0 | 0 | 0 | 5 | 13 | 0 | 0 | 0 | 운영(이번 범위) |
| 공유용_별도전략(격리) | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 14 | 0 | 검사 대상 아님(격리 · g_isolation 관문만) |
| 전략 계산 엔진(루트) | 13 | 0 | 0 | 5 | 8 | 0 | 0 | 0 | 0 | 돈전략(확인 · 전략 계산) |
| 문서(루트·docs) | 10 | 0 | 0 | 7 | 1 | 2 | 0 | 0 | 1 | 운영(이번 범위) |
| research 문서 | 10 | 0 | 0 | 10 | 0 | 0 | 0 | 0 | 0 | 담당 확인 필요 |
| 생성물(파이프라인 산출) | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 운영(이번 범위 · 생성자 코드로 검사) |
| 워크플로 | 8 | 0 | 0 | 0 | 2 | 6 | 0 | 0 | 0 | 운영(이번 범위) |
| research F계열 | 8 | 0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 돈전략(확인 · F계열) |
| 화면 | 6 | 0 | 1 | 1 | 0 | 4 | 0 | 0 | 2 | 운영·화면(이번 범위) |
| 실측 장부·동결값 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 돈전략(확인 · 동결값·실측 장부) |
| 소유자 안내·점검 | 3 | 0 | 0 | 2 | 0 | 1 | 0 | 0 | 0 | 운영(이번 범위) |
| 검사 진입점 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 1 | 운영(이번 범위) |
| 기타 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 담당 확인 필요 |
| 계약 파일 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 운영(이번 범위) |

## 부록 — 파일별

| 묶음 | 파일 | 종류 | 담당 | 수준 | 근거(최강) | 그 외 근거 | 변경 |
|---|---|---|---|---|---|---|---|
| research F계열 | `research/strategy_f1_kr.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py |  |  |
| research F계열 | `research/strategy_f1_placebo.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_f1_placebo.py·회귀 test_f2_mix.py·회귀 test_f3_design.py |  |  |
| research F계열 | `research/strategy_f1_screen.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py |  |  |
| research F계열 | `research/strategy_f2_mix.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_f2_mix.py·회귀 test_f3_design.py |  |  |
| research F계열 | `research/strategy_f3_execution.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_f3_design.py |  |  |
| research F계열 | `research/strategy_f3_placebo.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_f3_design.py |  |  |
| research F계열 | `research/strategy_f4_basket.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_f4_design.py |  |  |
| research F계열 | `research/strategy_f4_products.py` | 실행 코드 | 돈전략(확인 · F계열) | L3 함수 검토·회귀·관문 | 회귀 test_f4_products.py | 인계문 |  |
| research 문서 | `research/CODE_REVIEW_2026-09-05.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | v206 전체 감사·순회 B01~B15 | 인계문 |  |
| research 문서 | `research/ENGINE_RESEARCH.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 문서 | `research/EXPLORATION.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 문서 | `research/EXT_INFINITE.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | 인계문 |  |
| research 문서 | `research/FINAL_AUDIT.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |  |
| research 문서 | `research/LEVERAGE_US.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 | v220 심층(언급)·인계문 |  |
| research 문서 | `research/MEASUREMENT_AUDIT.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 문서 | `research/NEW_STRATEGY_RESEARCH.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 문서 | `research/STRATEGY_RESEARCH_2026-09-05.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 문서 | `research/SURVIVAL_MONITOR.md` | 문서 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/account_ledger.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_account_ledger.py·회귀 test_basket_accounting.py·회귀 test_execution_policy.py·회귀 test_f1_placebo.py | research 리뷰 v204~v209 |  |
| research 연구 스크립트 | `research/attack_diversify.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209 |  |  |
| research 연구 스크립트 | `research/audit_exec.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_execution_bands.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/audit_pbo.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/audit_stat.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_accum.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_accum2.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_b_inspect.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_dca.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/axis_dca_grid.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_defsel.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_dipbuy.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_ens.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_ext2.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_ext2_probe.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_external.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_finalverify.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | 셀프테스트(I14)(언급) |  |
| research 연구 스크립트 | `research/axis_forward.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_gate11.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_hedge_cost.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_horizon.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_isa.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/axis_krreal_decomp.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_krspec.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_krspread.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_lev.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_macro.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_macro2.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_macro3.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_macro4.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_mech.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_meta.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_meta_crisis.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_minimax.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_momentum.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_newrule.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_nextgen.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15·인계 교차검증·인계문 |  |
| research 연구 스크립트 | `research/axis_objective.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_regime.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_rvstate.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_secondary.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_selbias.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_selbias_disjoint.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_sigsrc.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_t4_krcost.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_t4_shadow.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_execution_bands.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/axis_t4_synthcrash.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_vixstate.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_vrhybrid.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_wide.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/axis_wide_probe.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/b_adversarial.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/b_gate_noise.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/band_accounting.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_execution_bands.py | research 리뷰 v204~v209 |  |
| research 연구 스크립트 | `research/basket_accounting.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_basket_accounting.py·회귀 test_f4_design.py |  |  |
| research 연구 스크립트 | `research/build_crisis_paths.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/c3_falsify.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/c3_placebo.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/cand_general.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/complement_sleeve.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/def_bond.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/def_equity.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/drag_sigma.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/dsr_b.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/emit_dd_distribution.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | v220 심층(언급) |  |
| research 연구 스크립트 | `research/eng_common.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/eng_kospi.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/eng_sp500.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/era_start.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/exec_cost.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층(언급)·순회 B01~B15·파수꾼 연결(언급) |  |
| research 연구 스크립트 | `research/execution_policy.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_execution_policy.py | research 리뷰 v204~v209 |  |
| research 연구 스크립트 | `research/ext_ibs.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/ext_vr.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/factcheck_qld_talk.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/forecast_check.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/free_design.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/frontier2.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/goal_feasibility.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hedge_ratio_scan.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hist_defchain.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hist_defdiag.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hist_defrun.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hist_fetch.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15·인계문 |  |
| research 연구 스크립트 | `research/hist_krtax.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hist_three.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/horizon_ess.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/horizon_study.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | 인계문 |  |
| research 연구 스크립트 | `research/hypo_escape.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hypo_external2.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hypo_gates.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hypo_hex.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15·인계 교차검증·인계문 |  |
| research 연구 스크립트 | `research/hypo_t4_real.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/hypo_t4wide.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hypo_verify.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hyst_signal.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/hyst_sigwfa.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/hyst_wfa.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15·인계문 |  |
| research 연구 스크립트 | `research/isa_pension.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/japan_stress.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/lev_5y.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/lev_opt.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/lev_signal_source.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/lev_th.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/liquid_design.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/liquid_iter.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/lookback200.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/mdd_target.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/ml_policy.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/near_zone.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/new_paths.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/oos_protocol_b.py` | 실행 코드 | 담당 확인 필요 | L4 연결·실측 | 회귀 test_watchdog_chain4.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층(언급)·순회 B01~B15·인계 교차검증·인계문·파수꾼 연결(언급) |  |
| research 연구 스크립트 | `research/ops_risk.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_ops_review2.py | research 리뷰 v204~v209·v220 심층(언급)·순회 B01~B15 |  |
| research 연구 스크립트 | `research/pbo_thresh.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/plan30_withdraw.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/post_dotcom.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | 인계문 |  |
| research 연구 스크립트 | `research/q1_physical_bond.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/q2_hedged_attack.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/q5_near_presell.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/rebalance_accounting.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_account_ledger.py·회귀 test_execution_bands.py·회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/recovery_speed.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/schd_qqq_overlap.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/slice_scan.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/surv_alert.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/surv_map.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | v220 심층(언급)·파수꾼 연결(언급) |  |
| research 연구 스크립트 | `research/t4_lev_post.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| research 연구 스크립트 | `research/takeprofit.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/tax_general_account.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/tax_us_direct.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·관문 verify_all(문자열·목록)·순회 B01~B15·인계 교차검증·인계문 |  |
| research 연구 스크립트 | `research/thresh_window.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/tranche.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/valuation_regime.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/wfa_thresh.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 | 인계문 |  |
| research 연구 스크립트 | `research/what_we_know.py` | 실행 코드 | 담당 확인 필요 | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| research 연구 스크립트 | `research/withdraw.py` | 실행 코드 | 담당 확인 필요 | L3 함수 검토·회귀·관문 | 회귀 test_ops_review2.py·회귀 test_research_review.py | research 리뷰 v204~v209·v220 심층(언급)·순회 B01~B15·인계 교차검증·인계문 |  |
| 검사 도구·회귀·장부 | `audit/AUDIT_LEDGER_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | 순회 B01~B15 |  |  |
| 검사 도구·회귀·장부 | `audit/CODE_REVIEW_SWEEP_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | research 리뷰 v204~v209 | 인계문 | 검사 후 변경 |
| 검사 도구·회귀·장부 | `audit/DEEP_REVIEW_OPS_UI_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | 회귀 test_ops_review2.py |  |  |
| 검사 도구·회귀·장부 | `audit/GATE_MUTATION_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/HANDOFF_CROSSCHECK_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | 순회 B01~B15 |  |  |
| 검사 도구·회귀·장부 | `audit/HANDOFF_TO_CODEX_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/MOBILE_OPS_2026-09-06.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/OPS_RECOVERY_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/OPS_UI_CROSSCHECK_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | v220 심층·회귀 test_ops_review2.py |  |  |
| 검사 도구·회귀·장부 | `audit/PAGES_CONCURRENCY_2026-09-06.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/SCREEN_MATRIX2_2026-09-06.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | pages 실측 |  |  |
| 검사 도구·회귀·장부 | `audit/SCREEN_STATES_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/WATCHDOG_CHAIN_2026-09-05.md` | 문서 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/audit_all.py` | 실행 코드 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 |  |  |
| 검사 도구·회귀·장부 | `audit/audit_full.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층 | v206 전체 감사·순회 B01~B15 |  |
| 검사 도구·회귀·장부 | `audit/check_handoff_20260905.py` | 실행 코드 | 운영(이번 범위) | L1 열람·대조 | 인계 교차검증 |  |  |
| 검사 도구·회귀·장부 | `audit/gate_mutation.py` | 실행 코드 | 운영(이번 범위) | n/a 검사 도구 자신(대상 아님) |  |  |  |
| 검사 도구·회귀·장부 | `audit/screen_states.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v223 화면 실측 |  |  |
| 검사 도구·회귀·장부 | `audit/test_account_ledger.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | 회귀 test_basket_accounting.py·회귀 test_execution_policy.py |  |  |
| 검사 도구·회귀·장부 | `audit/test_basket_accounting.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_execution_bands.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_execution_policy.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_f1_placebo.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_f2_mix.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_f3_design.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_f4_design.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) |  |  |  |
| 검사 도구·회귀·장부 | `audit/test_f4_products.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | 인계문 |  | 검사 후 변경 |
| 검사 도구·회귀·장부 | `audit/test_fold_anchor.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | v224 화면 실측 |  |  |
| 검사 도구·회귀·장부 | `audit/test_ops_recovery3.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | pages 실측·v222 연결·v225 모바일 실측 |  |  |
| 검사 도구·회귀·장부 | `audit/test_ops_review2.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | v225 모바일 실측 | v220 심층 |  |
| 검사 도구·회귀·장부 | `audit/test_pages_concurrency.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | pages 실측 |  |  |
| 검사 도구·회귀·장부 | `audit/test_research_review.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |  |
| 검사 도구·회귀·장부 | `audit/test_watchdog_chain4.py` | 실행 코드 | 운영(이번 범위) | n/a 근거 문서/회귀 모듈(도구) | v225 모바일 실측·파수꾼 연결 |  |  |
| 검사 도구·회귀·장부 | `audit/verify.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | pages 실측 | research 리뷰 v204~v209·v206 전체 감사·v220 심층·순회 B01~B15·인계문 |  |
| 검사 도구·회귀·장부 | `audit/verify_volguard.py` | 실행 코드 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 |  |  |
| 검사 진입점 | `research_kit.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층 | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |
| 검사 진입점 | `verify_all.py` | 실행 코드 | 운영(이번 범위) | L5 변조 | 관문 변별력 | pages 실측·research 리뷰 v204~v209·v206 전체 감사·v220 심층·v221 교차·v222 연결·v223 화면 실측·순회 B01~B15·인계 교차검증·인계문·파수꾼 연결·회귀 test_research_review.py | 검사 후 변경 |
| 계약 파일 | `data/retired_numbers.json` | 계약 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층·관문 verify_all(재계산·지문) | v206 전체 감사·순회 B01~B15·인계문 |  |
| 공유용_별도전략(격리) | `공유용_별도전략/README.md` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_2006_final.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_crisis.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_divqqq.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_final_check.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_finalize.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_monthly_curves.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_multi_period.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_oos_pbo.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_ratio_scan.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_regime_probe.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_regimes_final.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_rolling.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 공유용_별도전략(격리) | `공유용_별도전략/share_variant_threshold_scan.py` | 실행 코드 | 검사 대상 아님(격리 · g_isolation 관문만) | n/a 격리(g_isolation 만) |  |  |  |
| 기타 | `.gitignore` | 기타 | 담당 확인 필요 | L2 전문 판독 | v206 전체 감사 |  |  |
| 문서(루트·docs) | `01_Strategy_Logic.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | 순회 B01~B15 | 관문 verify_all(문자열·목록) |  |
| 문서(루트·docs) | `02_Risk_Management.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 | 관문 verify_all(문자열·목록)·인계문 |  |
| 문서(루트·docs) | `03_System_Params.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 |  |  |
| 문서(루트·docs) | `04_Rejected_Research.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 | 관문 verify_all(문자열·목록) |  |
| 문서(루트·docs) | `AGENTS.md` | 문서 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | 회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·관문 verify_all(문자열·목록)·순회 B01~B15 |  |
| 문서(루트·docs) | `CLAUDE.md` | 문서 | 운영(이번 범위) | L4 연결·실측 | pages 실측·파수꾼 연결 | research 리뷰 v204~v209·v206 전체 감사·관문 verify_all(문자열·목록)·순회 B01~B15·인계 교차검증·인계문·회귀 test_research_review.py | 검사 후 변경 |
| 문서(루트·docs) | `FILES.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 | 관문 verify_all(문자열·목록) |  |
| 문서(루트·docs) | `HANDOFF.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 | 인계문 |  |
| 문서(루트·docs) | `README.md` | 문서 | 운영(이번 범위) | L4 연결·실측 | 회귀 test_ops_recovery3.py·회귀 test_watchdog_chain4.py | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |
| 문서(루트·docs) | `docs/HANDOFF_전체이력.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사 |  |  |
| 보관본 | `archive/README.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_cd.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_cost.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_crisis.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_edge.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_final.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_grid.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_plateau.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_plateau.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_results.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_staged.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_vshape.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_wfa.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v19_복귀로직/reentry_wfa.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_blocks.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_cost.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_crisis.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_decomp.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_episodes.csv` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_episodes.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_focus.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_mdd.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_mech.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_robust.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/v20_히스테리시스/hyst_signif.py` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/지시프롬프트/복귀로직_연구프롬프트.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/지시프롬프트/외부AI_개선요청_v90.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/지시프롬프트/외부AI_연구감사_v131.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/지시프롬프트/제미나이.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `archive/지시프롬프트/제미나이2.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/deploy_README_v18_원본.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v18.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v19.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v20.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v203_통합코드리뷰.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v21.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v22.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v23.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v24.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v25.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v26.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v27.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v28.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v29.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v30.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v31.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v32.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v33.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v34.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v35.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v36.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v40.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v41.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v43.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v44.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v45.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v46.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v47.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v48.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v49.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v50.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v51.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v52.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v53.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v54.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v55.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v56.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v57.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v58.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v59.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v60.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v61.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v62.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v63.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v64.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v67_독립감사.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v68_추세추종.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v69_그림자추적.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v70_교차시장검증.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v71_감사조건이행.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v72_월간갱신_3전략표.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v73_기능추가.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v76_UI정리.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v78_헤지최적화_설명서.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v80_T4그림자_심층분석.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v81_T4가상검증.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v82_한국비용변형_룰감사.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v83_B동일잣대검사.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v87_차세대구조탐색.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/history/전략_v88_최종검증.md` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v21_3자비교_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v22_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v23_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v24_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v25_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v26_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v27_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v28_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v29_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v30_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v31_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v32_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v33_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v34_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v35_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v36_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v40_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v41_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v43_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v44_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v46_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v47_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v48_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v49_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v50_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v50b_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v51_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v52_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v53_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v53b_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v54_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v54b_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v55_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v56_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v56b_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v57_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v58_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v58b_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_v59_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 보관본 | `docs/raw/전략_vr하이브리드_raw.txt` | 보관본 | 검사 대상 아님(§2 읽기 전용 · 보관) | n/a 보관본 |  |  |  |
| 생성물(파이프라인 산출) | `data/crisis_paths.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | v220 심층 | research 리뷰 v204~v209·순회 B01~B15 |  |
| 생성물(파이프라인 산출) | `data/dd_percentile.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | v220 심층 | v206 전체 감사·관문 verify_all(문자열·목록)·순회 B01~B15 |  |
| 생성물(파이프라인 산출) | `data/isa_stats.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | v220 심층·회귀 test_research_review.py | v206 전체 감사·순회 B01~B15 |  |
| 생성물(파이프라인 산출) | `data/kr_holidays.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | 파수꾼 연결·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·관문 verify_all(재계산·지문)·순회 B01~B15 |  |
| 생성물(파이프라인 산출) | `data/ops_check.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | v223 화면 실측·v224 화면 실측·v225 모바일 실측·파수꾼 연결·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·순회 B01~B15·인계문 |  |
| 생성물(파이프라인 산출) | `data/qqq.csv` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | v222 연결·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·관문 verify_all(재계산·지문) |  |
| 생성물(파이프라인 산출) | `data/signal.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | pages 실측·v222 연결·v223 화면 실측·v224 화면 실측·v225 모바일 실측·파수꾼 연결·회귀 test_ops_recovery3.py·회귀 test_watchdog_chain4.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·v221 교차·관문 verify_all(재계산·지문)·순회 B01~B15·인계문·회귀 test_fold_anchor.py·회귀 test_ops_review2.py·회귀 test_research_review.py |  |
| 생성물(파이프라인 산출) | `data/signal_alert_state.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | 회귀 test_ops_recovery3.py | v206 전체 감사·순회 B01~B15 |  |
| 생성물(파이프라인 산출) | `data/strategy_stats.json` | 생성물 | 운영(이번 범위 · 생성자 코드로 검사) | n/a 생성물(생성자 코드 기준) | 회귀 test_ops_recovery3.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·관문 verify_all(재계산·지문)·순회 B01~B15 |  |
| 소유자 안내·점검 | `내가_보는_것/운영_점검표.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 |  |  |
| 소유자 안내·점검 | `내가_보는_것/전략_요약.md` | 문서 | 운영(이번 범위) | L2 전문 판독 | 순회 B01~B15 |  |  |
| 소유자 안내·점검 | `내가_보는_것/점검.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | 파수꾼 연결·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·순회 B01~B15·인계문 |  |
| 실측 장부·동결값 | `data/freeze.json` | 장부 | 돈전략(확인 · 동결값·실측 장부) | n/a 장부(관문 I11·I13 지문·행수 감시 · 내용은 §2 불변) | 회귀 test_ops_recovery3.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·관문 verify_all(재계산·지문)·순회 B01~B15·인계문 |  |
| 실측 장부·동결값 | `data/nav_history.csv` | 장부 | 돈전략(확인 · 동결값·실측 장부) | n/a 장부(관문 I11·I13 지문·행수 감시 · 내용은 §2 불변) | v222 연결·회귀 test_ops_recovery3.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·순회 B01~B15·인계문 |  |
| 실측 장부·동결값 | `data/oos_log.csv` | 장부 | 돈전략(확인 · 동결값·실측 장부) | n/a 장부(관문 I11·I13 지문·행수 감시 · 내용은 §2 불변) | v222 연결·v223 화면 실측·회귀 test_ops_recovery3.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·관문 verify_all(재계산·지문)·순회 B01~B15·인계문 |  |
| 실측 장부·동결값 | `data/oos_protocol_b.json` | 장부 | 돈전략(확인 · 동결값·실측 장부) | n/a 장부(관문 I11·I13 지문·행수 감시 · 내용은 §2 불변) | 파수꾼 연결·회귀 test_watchdog_chain4.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·관문 verify_all(재계산·지문)·순회 B01~B15·인계 교차검증·인계문 |  |
| 운영 스크립트 | `deploy/README.md` | 문서 | 운영(이번 범위) | L4 연결·실측 | 회귀 test_ops_recovery3.py·회귀 test_watchdog_chain4.py | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/build_stats.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·회귀 test_ops_recovery3.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·셀프테스트(I14)·순회 B01~B15·회귀 test_ops_review2.py |  |
| 운영 스크립트 | `deploy/data_check.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층·셀프테스트(I14) | v206 전체 감사·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/kakao_keepalive.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | 회귀 test_watchdog_chain4.py | v220 심층·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/kakao_setup.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층·셀프테스트(I14) | 순회 B01~B15 |  |
| 운영 스크립트 | `deploy/kr_holidays.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | 파수꾼 연결·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/kr_sources.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층 | v206 전체 감사·관문 verify_all(문자열·목록)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/nav_collect.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v225 모바일 실측·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·v221 교차·관문 verify_all(문자열·목록)·셀프테스트(I14)·순회 B01~B15·인계문·회귀 test_ops_review2.py |  |
| 운영 스크립트 | `deploy/notify.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·파수꾼 연결·회귀 test_ops_recovery3.py·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/oos_log.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·v223 화면 실측·회귀 test_ops_recovery3.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·셀프테스트(I14)·순회 B01~B15·인계문 |  |
| 운영 스크립트 | `deploy/price_now.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층 | v206 전체 감사·관문 verify_all(문자열·목록)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/price_poll.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·v224 화면 실측·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/refresh_hist.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·v221 교차·관문 verify_all(문자열·목록)·셀프테스트(I14)·순회 B01~B15·회귀 test_ops_review2.py |  |
| 운영 스크립트 | `deploy/signal_alert.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/stamp_rev.py` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층·셀프테스트(I14) | v206 전체 감사·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/update_signal.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·v223 화면 실측·v225 모바일 실측·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·관문 verify_all(재계산·지문)·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/wait_close.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·v225 모바일 실측·파수꾼 연결·회귀 test_ops_recovery3.py·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·셀프테스트(I14)·순회 B01~B15 |  |
| 운영 스크립트 | `deploy/watchdog.py` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v224 화면 실측·v225 모바일 실측·파수꾼 연결·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·셀프테스트(I14)·순회 B01~B15·인계문 |  |
| 워크플로 | `.github/workflows/daily-signal.yml` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·순회 B01~B15·인계문 |  |
| 워크플로 | `.github/workflows/monthly-stats.yml` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v222 연결·회귀 test_ops_recovery3.py | v220 심층·관문 verify_all(문자열·목록)·순회 B01~B15 |  |
| 워크플로 | `.github/workflows/notify-test.yml` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층 | 순회 B01~B15 |  |
| 워크플로 | `.github/workflows/pages.yml` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | pages 실측·v224 화면 실측·회귀 test_pages_concurrency.py | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록) |  |
| 워크플로 | `.github/workflows/price.yml` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | pages 실측·회귀 test_ops_recovery3.py | v220 심층·관문 verify_all(문자열·목록)·순회 B01~B15 |  |
| 워크플로 | `.github/workflows/source-probe.yml` | 실행 코드 | 운영(이번 범위) | L3 함수 검토·회귀·관문 | v220 심층 | 순회 B01~B15·인계문 |  |
| 워크플로 | `.github/workflows/verify.yml` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | pages 실측 | research 리뷰 v204~v209·v206 전체 감사·v220 심층·순회 B01~B15·인계문 |  |
| 워크플로 | `.github/workflows/watchdog.yml` | 실행 코드 | 운영(이번 범위) | L4 연결·실측 | v224 화면 실측·v225 모바일 실측·파수꾼 연결·회귀 test_watchdog_chain4.py | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·순회 B01~B15·인계문 |  |
| 원자료 | `data/hist/datahub_cpi_us.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/ff_F-F_Research_Data_Factors_daily_CSV.zip` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/ff_Portfolios_Formed_on_BE-ME_daily_CSV.zip` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/ff_Portfolios_Formed_on_D-P_CSV.zip` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/fred_DEXKOUS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/fred_DTB3.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/fred_NASDAQ100.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/fred_NASDAQCOM.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_research_review.py |  |  |
| 원자료 | `data/hist/kr_132030_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/kr_133690_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/kr_148070_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/kr_305080_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/kr_308620_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/kr_3m_rate.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/kr_411060_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/kr_418660_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/kr_453850_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/kr_458730_KS.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/kr__5EKS11.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/lbma_gold_pm.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `data/hist/multpl_cape_monthly.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/shiller_sp500_monthly.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_BRK_B.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_DVY.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_EEM.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_EFA.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_EWJ.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_EWY.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_GCF.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_GDX.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_GLD.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_GSPC.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_HYG.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_IEF.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_IJR.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_IWN.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_IXIC.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_N225.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_NDX.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_research_review.py |  |  |
| 원자료 | `data/hist/yahoo_NDX_ohlc.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_NYA.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_QLD.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_QQQ.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_RSP.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_RUT.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_SCHD.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_SDY.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_SOX_ohlc.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_SPY.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_TLT.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_TNX.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py | v220 심층·회귀 test_ops_review2.py |  |
| 원자료 | `data/hist/yahoo_TQQQ.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_TYX.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_VIX.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_VXN.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_VYM.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLB.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLC.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLE.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLF.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLI.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLK.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLP.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLRE.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLU.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLV.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_XLY.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_005830.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_055550.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_069500.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_086790.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_105560.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_114260.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_132030.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_139280.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_148070.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_161510.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_229200.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_329200.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_379800.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_418660.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `data/hist/yahoo_kr_466940.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) |  |  |  |
| 원자료 | `fixed_wfa_hist.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | v206 전체 감사 |  |  |
| 원자료 | `hyst_wfa.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15·인계문 |  |
| 원자료 | `qld_us_d.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py |  |  |
| 원자료 | `qqq_us_d.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py | 회귀 test_research_review.py |  |
| 원자료 | `schd_us_d.csv` | 원자료 | 돈전략(확인 · 원자료) | n/a 원자료(갱신 코드 refresh_hist 기준 · 내용 검증 아님) | 회귀 test_ops_recovery3.py | v206 전체 감사·v220 심층·순회 B01~B15 |  |
| 전략 계산 엔진(루트) | `axis_defmix.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문)·회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15·인계문 |  |
| 전략 계산 엔진(루트) | `axis_lib.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문)·회귀 test_research_review.py | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15·인계 교차검증·인계문 |  |
| 전략 계산 엔진(루트) | `axis_volguard.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문) | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15 |  |
| 전략 계산 엔진(루트) | `hist_data.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | v220 심층·관문 verify_all(재계산·지문)·회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| 전략 계산 엔진(루트) | `hist_defasset.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문)·회귀 test_f4_design.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| 전략 계산 엔진(루트) | `hist_defensive.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문) | research 리뷰 v204~v209·순회 B01~B15 |  |
| 전략 계산 엔진(루트) | `hist_divetf.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| 전략 계산 엔진(루트) | `hist_korea.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| 전략 계산 엔진(루트) | `hist_krfinal.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문)·회귀 test_research_review.py | research 리뷰 v204~v209·순회 B01~B15 |  |
| 전략 계산 엔진(루트) | `hist_krreal.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| 전략 계산 엔진(루트) | `hist_tiger.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L2 전문 판독 | research 리뷰 v204~v209·순회 B01~B15 |  |  |
| 전략 계산 엔진(루트) | `hyst_core.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L2 전문 판독 | v206 전체 감사·순회 B01~B15 | 인계문 |  |
| 전략 계산 엔진(루트) | `reentry_lib.py` | 실행 코드 | 돈전략(확인 · 전략 계산) | L3 함수 검토·회귀·관문 | 관문 verify_all(재계산·지문) | research 리뷰 v204~v209·v206 전체 감사·순회 B01~B15·인계 교차검증·인계문 |  |
| 화면 | `guide.html` | 화면 | 운영·화면(이번 범위) | L4 연결·실측 | v224 화면 실측·v225 모바일 실측 | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·순회 B01~B15·회귀 test_fold_anchor.py·회귀 test_ops_review2.py·회귀 test_research_review.py |  |
| 화면 | `icon-192.png` | 화면 | 운영·화면(이번 범위) | L2 전문 판독 | research 리뷰 v204~v209 | 관문 verify_all(문자열·목록) |  |
| 화면 | `icon-512.png` | 화면 | 운영·화면(이번 범위) | L1 열람·대조 | 관문 verify_all(문자열·목록) |  |  |
| 화면 | `manifest.json` | 화면 | 운영·화면(이번 범위) | L4 연결·실측 | v225 모바일 실측 | v206 전체 감사·관문 verify_all(문자열·목록) |  |
| 화면 | `notes.html` | 화면 | 운영·화면(이번 범위) | L4 연결·실측 | v222 연결·v224 화면 실측 | v206 전체 감사·v220 심층·관문 verify_all(문자열·목록)·순회 B01~B15·회귀 test_fold_anchor.py·회귀 test_research_review.py | 검사 후 변경 |
| 화면 | `signal.html` | 화면 | 운영·화면(이번 범위) | L4 연결·실측 | pages 실측·v222 연결·v223 화면 실측·v224 화면 실측·v225 모바일 실측·파수꾼 연결·회귀 test_ops_recovery3.py·회귀 test_watchdog_chain4.py | research 리뷰 v204~v209·v206 전체 감사·v220 심층·v221 교차·관문 verify_all(문자열·목록)·순회 B01~B15·인계문·회귀 test_fold_anchor.py·회귀 test_ops_review2.py·회귀 test_research_review.py | 검사 후 변경 |
