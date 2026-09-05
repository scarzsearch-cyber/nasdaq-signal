# 자동 파수꾼 연결 검증 (2026-09-05 · 4차 · v222 후속)

> 기준 **700d7c4**(v222 S2 보완까지 반영된 main) · 별도 작업트리 `review/watchdog-4`.
> 대상: `deploy/watchdog.py`(9모드) + `.github/workflows/watchdog.yml` + 그것이 부르는 `내가_보는_것/점검.py --json`·
> `research/oos_protocol_b.py --oos`(읽기·실행만 · 수정 없음 — research 는 돈전략 담당). 방법: 모드끼리 **이어 돌릴 때**의
> 파일 상태·GITHUB_OUTPUT·알림·커밋을 가짜 하위 프로세스(실제 출력 문자열)·임시 디렉터리·로컬 bare 원격으로 본다.
> 실제 알림·토큰 회전·운영 장부·원자료 변경 없음. 회귀 검사: `audit/test_watchdog_chain4.py`(16개 ·
> 700d7c4 deploy 사본에서 W1 기저율 표류 1실패, 옛 워크플로에서 W4 휴장일 스텝 1실패 → 수정 뒤 16/16 · `WATCHDOG4_OLD`).
> 이 문서는 파수꾼 연쇄의 검증이다 — 저장소 전체 검토 완료를 뜻하지 않는다.

## 발견한 실제 장애 → 사용자 영향 → 수정 → 증거

| # | 연결 경로 | 실제 장애 | 사용자 영향 | 수정 | 증거 |
|---|---|---|---|---|---|
| W1 | `mode_check` → `protocol_status` ← `oos_protocol_b.py --oos` 출력 | 평가기가 「역사 기저율이 등록값과 다르다 → **판정 중단**」(rc 2)으로 끝나면 파서가 else 로 떨어져 todo 를 **「평가기 출력을 읽지 못했다」**로 적었다. 표류는 읽힌 것이지 못 읽은 것이 아니다(v218 이 실제로 겪은 상황). | 주간 카톡·화면 배너·이슈 본문이 원인(원자료 갱신 → 재등록 절차)이 아니라 「파서 실패」를 가리켜 사람이 엉뚱한 곳을 본다. | `protocol_status` 에 표류 분기 추가: line 「기저율 표류 — 판정 중단」, todo 「기저율이 등록값과 다르다 … 02 §5-1 절차대로 재등록」(verdict 는 그대로 `error` · 화면 라벨 변경 없음). | 실제 평가기 출력 문자열(사건 0건 · 2026-09-05 실행분)을 기준으로 ok/warn/outside/invalid/drift/crash 6경우 계약 검사. 옛 코드: 표류가 「읽지 못했다」(실패) → 수정 뒤 통과. |
| W4 | `watchdog.yml` 주간 순서: check → heartbeat → **휴장일 표 연장** → 점검 결과 커밋 | 휴장일 표 연장(`kr_holidays.py --emit`)이 실패하면(음력 표 소진 등) 뒤 스텝인 **점검 결과 커밋까지 건너뛴다** — 이미 쓴 ops_check.json(주간 점검·heartbeat 표시)이 그 주에 커밋되지 않는다. 두 산출물은 서로 무관하다. | 화면 「자동 점검」 줄이 낡은 채로 남고(21일 뒤 「점검 낡음」), heartbeat 표시 유실로 다음 주 생존 카톡이 한 번 더 간다. | 스텝에 `id: hol` + `continue-on-error: true`, 이슈 조건에 `steps.hol.outcome == 'failure'` 추가, 이슈 본문에 한 줄. `git add data/ops_check.json data/kr_holidays.json` 은 그대로(verify_all g_watchdog 문자열 유지). | 워크플로 텍스트 계약 검사(스텝 순서·c-o-e·id·이슈 조건). 옛 워크플로: 실패 → 수정 뒤 통과. |

## 설계와 실제 동작이 일치함을 확인한 것 (수정 없음)

| # | 연쇄 | 확인 | 검사 |
|---|---|---|---|
| W2 | 주간 check: `점검.py --json`(마지막 줄 JSON) → 평가기 → `merge_ops` → 원자 쓰기 → `check_worsened` → 알림 | 첫 실행에서 `protocol_b`·`health_errors` 키가 새로 생겨도 「악화」가 아니다 · `heartbeat` 는 이월 · 새로 나빠질 때 한 번만 알리고 같은 상태 반복은 조용 · 평가기 크래시(rc 1)는 `error`+todo 로 파일에 남고 악화로 알린다 · `점검.py` 자체가 깨지면 기존 파일을 보존하고 알린다 | `W2_*` 4검사 |
| W3 | 「점검 결과 커밋」 셸(실제 YAML 에서 추출) · 로컬 bare 원격 | 변경 없으면 커밋 없음 · 원격 그대로면 push · 원격이 움직였으면(일일 신호 슬롯이 먼저 밀음) `git push` 실패 = 실패-폐쇄(옛 체크아웃의 점검 산출물을 새 코드 위에 얹지 않음 · 다음 주간 슬롯이 새 HEAD 로 재계산) | `W3_*` 3검사 |
| W4 | 워크플로 ↔ `MODES`: 9모드 전부 스텝·id 가 있고 이슈 조건이 모든 alert 를 읽는다 · 일간 6모드는 월 09:10 슬롯에서 빠지고(`schedule != '10 0 * * 1'`) · 주간 2모드+커밋은 `WEEKLY` 로 게이트 · channel 은 매일 | 텍스트 계약 | `W4_*` 3검사 |
| W5 | `mode_channel` 의 카카오 연명이 refresh 토큰을 회전 → 같은 잡의 뒤 알림 | `activate_refresh_token` 이 os.environ 과 GITHUB_ENV 에 반영 → `notify`(subprocess) 가 새 토큰을 상속 | `W5` 1검사 |
| W6 | heartbeat 상태의 저장처가 ops_check.json 커밋 | 같은 달 재발송 없음 · 발송 실패면 표시를 남기지 않아 다음 주 재시도 · **커밋 유실이면 다음 주 한 번 더 간다(설계: 누락보다 중복)** | `W6` 1검사 |

## 실패 전후 불변조건
- `data/ops_check.json` 은 점검 실패·평가기 실패·원자 교체 실패 어느 경우에도 마지막 성공 판(또는 error 가 기록된 새 판)으로 파싱된다. `heartbeat` 키는 주간 점검이 지우지 않는다.
- 파수꾼은 어떤 모드도 non-zero 로 끝나지 않으며, 사람이 봐야 할 상태는 `alert=1` 출력 → 이슈 조건이 **9모드 + 휴장일 스텝 outcome** 을 읽는다.
- 주간 커밋은 원격이 움직였으면 실패-폐쇄(재베이스 없음). 휴장일 표 스텝 실패는 점검 커밋을 막지 않는다.

## 인계 — 공용 판정·검증 규약에 걸리는 항목 (이번에 바꾸지 않음 · 결정은 통합 담당)
1. **신호 신선도 셈의 미국 휴장 반영** — `biz_days_since`(파수꾼)·`bizDaysSince`(signal.html)는 평일만 센다. 미국 휴장 주엔 실제 누락 1일 만에 문턱 3에 닿는다(예: 노동절 다음 수요일 08:40 · 화요일 갱신 실패 → Fri·Mon·Tue = 3 → 알림 · 문구 「3영업일째 그대로」는 과장). v222 가 `wait_close.nyse_holidays` 를 만들었으므로 같은 달력을 쓰면 「미마감 세션 수」로 통일할 수 있다. **영향 범위**: `deploy/watchdog.py biz_days_since`(stale·near·heartbeat 문구) · `signal.html bizDaysSince/showStale/freshDot/paintFreeze`(화면 규약 · vNN) · `STALE_N` 문턱 의미 · CLAUDE v140/v202 항목·설명서 ⑧ 「파수꾼」 문구 · watchdog 셀프테스트 61경우 중 날짜 경우. 보수적(조기 알림)이라 방치해도 위험은 없다.
2. **기저율 표류의 화면 라벨** — 이번 수정은 verdict 를 `error` 로 두어 화면 `PBV` 표가 「평가 실패」로 그린다(todo 줄이 원인을 말한다). 전용 verdict(`drift`)를 두려면 `signal.html drawOpsCheck` 의 고정 표를 늘려야 한다(화면 변경 · vNN · notes). 지금은 문구만 정확해졌다.
3. **주간 커밋의 non-fast-forward** — 실패-폐쇄가 설계(v203)이며 그때 이슈 본문은 일반 문구다(「점검 커밋이 원격 변경에 밀렸다」를 말하지 않는다). 일일 신호 슬롯(09:17)과 겹칠 때만 나며 다음 주에 자가 회복. 문구 보강은 워크플로 변경이라 인계.
4. **`점검.py` 가 부르는 research 스크립트**(`surv_map.py`·`exec_cost.py`)의 출력 서식이 바뀌면 `health_errors` 코드(`var_missing:*`·`exec_parse:*`)가 바뀌어 파수꾼 「악화」 판정이 한 번 울린다 — research 쪽 변경 때 알려 달라(파수꾼은 코드 집합의 차집합만 본다).

## 검증
- 옛 사본(700d7c4 deploy)에서 W1 표류 1실패 · 옛 워크플로에서 W4 휴장일 스텝 1실패 → 수정 뒤 16/16.
- `watchdog --selftest` 61경우 PASS · `verify_all --fast`·전체 실패 0(`g_watchdog` 문자열 유지).
- 화면 변경 없음. 통합 결과는 §G.

## G. 통합
- (push 뒤 기입)
