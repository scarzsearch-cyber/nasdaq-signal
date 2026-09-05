# verify_all 관문 변별력 검사 (2026-09-05 · 5차)

> 기준 **e0b7491** · 별도 작업트리 `review/verify-gates-5`. 질문 하나: **「verify_all 의 관문은 실패해야 할 때 실제로 실패하는가.」**
> 방법: 임시 클론(작업본 반영)에 관문마다 **그 관문이 막으려는 결함을 실제로 주입**하고 그 관문 함수만 따로 돌려
> FAIL(설계상 WARN 이면 WARN)이 나는지 본다. 도구 `audit/gate_mutation.py`(변조 125 + 실행기 2 = **127**). 실제 저장소·장부·원자료 무접촉.
> 전략·판정·화면·장부 무변경. verify_all 의 위생 관문(g_*) 두 곳만 강화했다(§2 경계 밖 · I1~I14 본문 무수정).

## 결과 한 줄
- **강화 뒤 127/127 잡힘.** 강화 전 verify_all(e0b7491)로 같은 변조를 돌리면 **4개를 못 잡는다**(아래) — 나머지 121개는 강화 전에도 잡혔다.

## 발견한 실제 약점 → 영향 → 수정 → 증거

| # | 관문 | 약점 | 사용자 영향 | 수정 | 증거 |
|---|---|---|---|---|---|
| G1 | `g_deploy` 「전환 알림 실패가 OOS 기록과 무관하게 이슈로 남는다」 · 「NAV·OOS 장부 실패가 …」 · 「비차단 보고·토큰 실패가 …」 | `'id: sigalert' in daily` 같은 **부분문자열** 검사라 `id: sigalertx` 처럼 id 만 바뀌고 `steps.sigalert.outcome` 참조가 남은 워크플로를 통과시켰다. 그 상태에선 이슈 스텝 조건이 영원히 거짓이라 **발송 실패가 아무 데도 안 남는다**. | 전환 알림·장부 실패의 마지막 보고 통로(이슈·메일)가 조용히 죽어도 관문이 초록. | `_step_id(text, id)` — 줄 단위 `^\s*id:\s*<id>\s*(#…)?$`. 6개 id(sigalert·navlog·ooslog·sigissue·ledgerissue·keepalive). | 옛 verify_all: `dep_sigalert_id`·`dep_navlog_id`·`dep_finalizer` **MISSED** → 강화 뒤 CAUGHT. |
| G2 | `g_watchdog` 「재알림·근접 알림이 모드와 스텝 양쪽에」 | `'watchdog.py near' in wy` 가 `watchdog.py near2` 를 포함으로 통과. | 워크플로 스텝이 다른 모드를 부르게 바뀌어도(근접 알림이 안 도는 상태) 관문이 초록. | `_run_line(text, cmd)` — 줄 끝 일치. | 옛: `wd_step_missing` **MISSED** → CAUGHT. |

## 잡히는 것을 확인한 관문 (변조 121개 · 강화 전후 동일)
| 관문 | 변조 수 | 대표 변조 |
|---|---|---|
| I2 미래 미참조 | 1 | 엔진 `ddv` 를 하루 앞 값으로(`shift(-1)`) → 「QQQ 낙폭 시점별 일치」 FAIL |
| I3 체결 규약 | 1 | `sim(lag=1→0)` → 「미래훔쳐보기가 규약보다 유리」 FAIL |
| I4 모형 vs 실물 | 1 | `UST_FEE +3%p` → 국채 드리프트 FAIL |
| I11 동결 | 10 | freeze enter/lookback · update_signal STRATS/adjclose 값 줄/LOOKBACK · signal.html 규칙/LOOKBACK · 장부 지문 · 장부 절단(HEAD 대비) · 장부 비움(안 쌓임 WARN + 줄었다 FAIL) |
| g_freeze_seal | 5 | 비중·비용·체결·공격자산 + **rule 밖 항목 한 글자**(내용 봉인만 잡는 경우) |
| I12 그림자 | 4 | 필드 누락 · 정의 모순(w≠min(1,40/rv)) · 전 행 공백(파이프라인 사망) · 01 AUTO-STATS 옛 날짜 |
| I13 규약 | 4 | 본문 변경 · freeze 지문 연결 · 02 문서 지문 · 평가기 파일 삭제 |
| I6 라이브 | 16 | as_of·dd·stats 판·final·ulcer·horizons(값·**통째 누락**)·벤치·close·high_252·state·changed_today·prev_state·next_line·gap_pp·enter |
| I7 공표 | 3 | us_1972 B ×1.05 · 벤치 기간 · 벤치 MDD 얕게 |
| I8 봉인 | 2 | rule_w 본문 한 줄 · rule_w 이름 변경(못찾음) |
| I9 폐기 수치 | 3 | 현행 문서 인용 · CLAUDE.md 맨몸 인용 · 검사 대상 문서 소실(WARN 설계) |
| I14 셀프테스트 | 2 | 셀프테스트 exit 1 · 스크립트 삭제 |
| I5 화면 | 32 | ORDER·sel·SKEY·추천 파랑·탭 2·loadPrice 전부·paintProx·portCompute·drawPending·체크리스트 한 줄·extbar·sticky·drawT4·drawHoriz·per·MDD 열·Ulcer 정의문·심사 줄·등급표·체결 시각·집중 서사·폐기 조합·CAGR 열·개정 자리·개정 div·글꼴 + 설명서 must/검증 12종 + 각주 문단 수 |
| g_review_context | 6 | AGENTS 전문 · 보장 문구 · 15배 · 아이콘 · ISA 라벨 · 철회 접두어 |
| g_repo_map · g_toc | 3 | 새 추적 파일 · **basename 무임승차 시도(research/watchdog.py)** · 04 새 절 |
| g_isolation | 4 | 폴더 밖 쓰기 · `../` 우회 · deploy 임포트 · 동적 경로(WARN 설계) |
| g_notes_lag | 3 | §4 `- **v999` · `- v999:` · 「변경 0회」 |
| g_deploy | 19 | 복사 줄 주석화 · dd_percentile 소실 · PWA 소실 · 월간 순서/`git add data/`/rebase · 일일 id 4종 · 이슈 스텝 차단 · `git add data/` · rebase · reset 소실 · exit 0 소실 · 토큰 재주입 · GH_PAT 누락 · cron · FRED URL · pages conclusion |
| g_signal_coupling | 4 | price.json 문자열 · 판정 경로 kr_sources · CORE_CODES · kr_market_open |
| g_watchdog | 4 | 모드 누락 · 스텝 누락 · 휴장일 커밋 줄 · MIN_DAYS_PER_YEAR |
| 실행기 | 2 | 실패 1건 → 종료코드 1 · 관문 예외(strategy_stats.json 손상) → 그 관문만 FAIL + 뒤 관문(I8·g_*) 계속 |

## 변조하지 않은 것(대상이 아니거나 변조로 잴 수 없다)
- **I1 `axis_lib.check`·`check_hold`** — 엔진 내부 검산(다른 검사가 엔진을 바꾸면 I3·I7 이 잡는 것으로 대신 확인).
- **I5 「B > A」·「원화 좌측꼬리」·「신호원」·I10 P1~P3** — 자료가 바뀔 때 실패하도록 둔 **전제 감시**다. 코드 변조로는 뜻 있게 깨뜨릴 수 없고 깨뜨려서도 안 된다.
- **I9 docs/history 정정 배너(WARN)** — 실측 값이 든 옛 문서를 고르는 변조는 문서 내용 의존이라 넣지 않았다(WARN 설계 확인만).
- 화면 검사 32개는 **문자열이 그 자리에만 있는지**를 먼저 정적으로 셌다: 55개 검사 문자열 전부 signal.html 에서 주석·CSS 가 아닌 코드에만 있다(2026-09-04 코드리뷰가 걷어낸 무임승차 재발 0).

## 도구 자체에서 난 오류 2건 (관문이 아니라 잣대의 오류 · 그대로 적는다)
1. **부분문자열 변조 12건** — 첫 실행에서 `function paintProx → paintProx2` 처럼 **원문을 포함하는 대체 문자열**을 써서 12개가 「못 잡음」으로 나왔다. 8개(I5)는 잣대 오류라 변조를 고쳤고, **4개(G1·G2)는 관문 쪽도 같은 병**이라 강화했다. 「못 잡음」이 뜨면 먼저 변조가 진짜 결함인지 본다(§-1 ⑤ 의 반대편).
2. **`git clone` 은 작업본이 아니라 HEAD 를 준다** — 강화한 verify_all 을 커밋 전이라 두 번째 실행도 옛 관문을 재고 있었다(4개 그대로 MISSED). 이제 도구가 미커밋 변경을 클론에 복사해 커밋한 뒤 잰다(「작업본 반영 N파일」 출력으로 확인).

## 인계·후속
- 실행 비용 ~220초(로컬) — `verify.yml` 의 **예약·수동 실행 스텝**에만 얹었다(push 마다는 아님). verify_all 을 고치면 손으로 `python audit/gate_mutation.py` 를 먼저 돌려라.
- 새 관문을 verify_all 에 넣을 때 이 파일에 변조 하나를 같이 넣는 것이 규약이 되면 「검사를 추가했다 ≠ 검사가 돈다」(v148)가 관문으로 막힌다 — 강제는 안 했다(도구가 verify_all 의 `ok(` 수와 변조 목록을 대조하는 관문은 오탐 위험이 커서 보류).
- research 무접촉. 공용 판정 규약 변경 없음.

## G. 통합
- (push 뒤 기입)
