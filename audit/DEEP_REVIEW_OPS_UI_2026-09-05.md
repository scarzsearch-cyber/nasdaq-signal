# 운영·화면 20파일 2차 심층 코드리뷰 — 함수 단위 장부 (2026-09-05)

> **v221 교차검증 후속:** `audit/OPS_UI_CROSSCHECK_2026-09-05.md` 참조. R2-07은 가격 산술 이전의
> 검증까지 추가해야 했고, R2-12는 장중 동일 날짜 행 처리 순서를 보완했다. R2-13도 실패목록에
> 기록 후 나머지 점검을 계속하도록 수정했다. 아래 B8/D/F의 R2-07 ‘기록/수정’ 혼재는 v220 작성
> 시점의 잔존 문구이며 F의 수정 상태가 당시 최종이다. FX의 여름 ‘항상 실패’는 과도한 일반화다.

> 기준 SHA **e63af37** (origin/main == 로컬 HEAD · 깨끗한 트리). 브랜치 `review/ops-ui-2` · 별도 작업트리.
> 시작 전 기준 검사: `python verify_all.py`(전체) **실패 0 · 경고 0** (`rev2_baseline_verify_full.txt`).
> 대상: `deploy/` 17 + `signal.html`·`guide.html`·`notes.html`. 공용 함수·워크플로·데이터 계약은 필요한 만큼만 추적했다 —
> 이 장부를 읽었다고 저장소 전체 검토 완료로 쓰지 마라.
> 기록 형식: 함수 → 입력 계약 / 호출자 / 상태 변경 / 출력·소비자 / 실패 경로 / 재현 검사(확인 근거). 문제가 없어도 근거를 남긴다.
> 발견은 §F 에 `R2-nn` 으로 모은다(등급: P1 실제 매매·알림·판정 · P2 계산·기록·검증 · P3 낡은 설명·혼동 · P4 개선).

## A. 워크플로 ↔ 스크립트 호출 표 (모드·옵션이 맞는가)

| 워크플로 | 호출 | 확인 |
|---|---|---|
| `daily-signal.yml` (8슬롯 04:35~09:17 KST · 평일) | `git reset --hard origin/main` → `wait_close.py` → `signal_alert.py`(c-o-e, id sigalert) → 이슈 → `kakao_keepalive.py`(c-o-e) → `nav_collect.py`(c-o-e) → `oos_log.py`(c-o-e) → 이슈 → 커밋(허용 5파일만 add · 잔여 관문 · v206 중복 판별 · push) → 상태 확정(always) → 실패 알림 | 모드 인자 없음(각 스크립트 기본 동작) ✓ · `verify_all g_deploy` 12검사가 이 파일 구조를 고정 ✓ |
| `watchdog.yml` (08:40 평일 · 09:10 월) | `watchdog.py stale/rebalance/switchday/near`(월 09:10 제외) · `channel`(항상) · `stats/price`(월 09:10 제외) · WEEKLY: `check` · `heartbeat` · `kr_holidays.py --emit` · 커밋 · 이슈(9 모드 alert) | 9 모드 전부 `MODES` 에 존재 ✓ · `if:` 조건과 id 대응 ✓ (`g_watchdog`) |
| `price.yml` (08:30·40·50 · 예비 :20/:50) | `price_poll.py --mode $MODE` (schedule → poll · dispatch → 입력) | `main()` 의 choices 와 일치 ✓ · actions: write 필요(pages 깨우기) ✓ |
| `monthly-stats.yml` (매월 1일 16:17 KST) | `refresh_hist.py` → `build_stats.py` → `research/emit_dd_distribution.py` → `verify_all.py`(전체) → 허용 16파일 add → push | 순서·산출물 목록 `g_deploy` 가 고정 ✓ |
| `pages.yml` (push · workflow_run 3종 · dispatch) | 복사 목록 + `stamp_rev.py _site/index.html` + price-data 브랜치 | ⚠ `data/isa_stats.json`·`data/retired_numbers.json`·`data/oos_protocol_b.json` 은 화면이 fetch 하지 않으므로 미복사가 맞다(R2-확인) |
| `verify.yml` (push·PR·10:00 KST) | research_kit → unittest 10모듈 → `--fast` → 전체(always) → audit_full(예약·수동) → 이슈 | ✓ |
| `notify-test.yml`·`source-probe.yml` | 수동 전용 | ✓ |

## B. 운영 스크립트 — 함수 단위

### B1. `deploy/update_signal.py` (538줄) — 신호 생성 · **판정 경로**
| 함수 | 입력 계약 → 호출자 → 상태 변경 → 출력·소비자 → 실패 경로 | 확인 근거 |
|---|---|---|
| `_parse_yahoo_result(result, now_utc)` | Yahoo chart JSON(timestamp·adjclose·meta) → `fetch` → 없음 → `pd.Series(Close)` UTC 정규화 일자 → 중복/역순/NaN/미래/meta 불완전/장중 봉 제외 뒤 빈 결과 전부 `ValueError`(폴백 사슬로) | `--selftest` 8반례 PASS(I14) · 장중 판별은 `in_session` 한 곳 |
| `fetch(host)` | period1=1999-01-01~now · query1/query2 → `main` 사슬 → 없음 → 시리즈 → 네트워크/형식 예외 → 다음 소스 | 판독 · 실행은 네트워크라 미실행(캐시 경로로 대체 검사 §E) |
| `in_session(meta)` | qt·start·end → `_parse_yahoo_result`·`wait_close._in_session`·`sanity` → 없음 → bool → start 없으면 `qt<end`(구식) · qt/end 없으면 False | 롤오버·프리마켓·구형 meta 3경우 `wait_close --selftest` PASS |
| `fetch_naver()` | 네이버 해외종목 basic(marketStatus CLOSE 만) → 사슬 3번째·`sanity_check` 대조 → 없음 → 1행 시리즈(최신 확정 종가) → CLOSE 아님/캐시 없음/캐시보다 새롭지 않음 예외 | 판독 · 비수정 종가지만 최신 봉은 수정=비수정(v71) |
| `load_cached()` | `data/qqq.csv`(Date,Close) → `main`·`fetch_naver` → 없음 → 시리즈 or None → 헤더/중복/역순/NaN/미래 `ValueError` **(main 에서 잡지 않는다 → 캐시가 깨지면 갱신 전체 실패 · R2-05 기록)** | 실측: 현재 캐시 6,916행 정상 |
| `sanity_check(px, source)` | 최종 시리즈·출처 → `main`(CSV 쓰기 **전**) → 없음 → 통과/`RuntimeError` → 큰 움직임(>10%)일 때만 교차 대조 · 대조 소스 불통은 통과(fail open) · 두 소스 0.5% 초과 어긋나면 중단 | 판독 · 규약대로 fail-open/closed 갈래 명시 |
| `drawdown(px)` | rolling(252, min_periods=60).max → `main`·`history_shift` → 없음 → (dd, roll_max) | ⚠ 백테스트(hist_data)는 min_periods 252 — 캐시 시작 1999 라 현재 무영향(`dd_from` docstring 기재) |
| `history_shift(old,new)` | 두 시리즈 → `main` → 없음 → shift %p(로그만) → 예외는 삼키고 0.0 | 판독 · 막지 않는 설계(v137) |
| `states(dd, enter, exit)` | 낙폭·문턱 → `main` → 없음 → 상태 시리즈 → NaN 은 직전 상태 유지 | 규칙 정의와 일치(전량 전환 상태기계) · 동결값과 `oos_log` 가 교차검증 |
| `trajectories(px, dd)` | → `main` → 없음 → 위기 4구간+현재 궤적 dict(화면 trajPanel 은 crisis_paths.json 을 쓰고 이 필드는 미사용 — R2-확인) | 판독 |
| `load_stats()` | `strategy_stats.json` → `main` → 없음 → dict/None(경고) | 판독 |
| `main()` | 사슬(yahoo→yahoo2→naver→cache) → concat(keep=last) → 최종 계열 검증 → `sanity_check` → **CSV 쓰기(비원자)** → dd/상태/strategies/recent(최신 [0])/payload → **signal.json 쓰기(비원자)** | ⚠ 두 파일 비원자 쓰기 — Actions 에서는 잡 실패 시 커밋이 안 되므로 반쪽 커밋은 없음. 로컬 수동 실행 중단 시 CSV 만 새 값일 수 있음(다음 실행이 재계산) · R2-05 |
| `selftest()` | 합성 8경우 | I14 PASS |
계약 소비자: `signal.html`(strategies.B · recent[].B · as_of · close · high_252 · dd · stats · defensive) · `oos_log`(as_of·close·high_252·dd·strategies.B) · `signal_alert`·`watchdog`(strategies.B · recent[].B · as_of · dd · close) · `wait_close`(as_of) · `build_stats`(stats 사본).

### B2. `deploy/wait_close.py` (413줄) — 종가 확정 대기
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `fetch_meta()` | Yahoo 1d meta(qt·start·end·price·prev) → `main`·폴링 → 없음 → dict → 예외는 호출자 | 판독 |
| `closed(meta)` / `_in_session` | `update_signal.in_session` 재사용(규칙 한 곳) | selftest 롤오버·프리마켓 PASS |
| `expected_close_date(meta)` | 장중이면 'IN_SESSION' · end 없으면 날짜 반환(fail open) | selftest PASS |
| `wait_for_close(meta, now, sleep, refetch, xsrc_closed, big_move)` | 마감까지 ≤100분 대기 → 20초 폴링 ≤8분 → 30초 안정 확인 ≤5회 → 큰 움직임이면 대조 소스 CLOSE 대기 ≤15분(fail open) | selftest 9경로 PASS(가짜 시계) |
| `as_of_is_current` / `validate_signal_as_of` | 정규형·미래 거부(`ValueError`) | selftest PASS |
| `main()` | meta 조회 실패 → v75 루프 · 240초 간격 ≤170분 · `subprocess.call(update_signal)` · 시한 초과 exit 1 | 판독 · R2-06(예상일 조회 실패가 반복되면 갱신됐어도 exit 1 → 거짓 실패 알림 가능 · 기록만) |

### B3. `deploy/oos_log.py` (444줄) — 동결 장부(append-only)
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `qqq_snapshot(as_of)` | qqq.csv 전행 검증(헤더·ISO·양수·유한·중복·역순·마지막=as_of·≥252행) → (close, high252, prev) | selftest 원천 대조 반례 PASS |
| `t4_shadow(as_of)` | as_of 까지 종가 → (votes, rv%, w) · 마지막≠as_of 면 None(경고) | v68 정의 그대로(ddof=1 · 2배·√252) · 기존 행 재검증 `_validate_existing_row` 와 허용오차 정합(§E 계산) |
| `_atomic_append_row` | 원본 바이트 보존 + 임시파일 + `os.replace` | selftest 교체 실패 반례 PASS |
| `_validate_existing_row` / `_read_existing` | 기존 행 전부 동결 계약과 재대조(열·수치·낙폭·상태·규칙명·지문·T4 범위) | selftest 지문 훼손 반례 PASS · 실제 장부 6행 통과(§E) |
| `main()` | 존재/날짜/미래 → 기존 장부 검증 → 같은 날 no-op → 동결 전 skip → 중간 삽입 거부 → B 완전성·문턱=동결·수치·낙폭·상태 → QQQ 원천 대조(0.011) → changed 불리언 → T4 필수 → 연속 거래일이면 changed 대조 → append | selftest 12반례 PASS · R2-확인: `changed` 대조가 「직전 QQQ 거래일 = 마지막 기록」일 때만 걸리는 설계 = 빈 날 뒤 영구 거부 방지 |

### B4. `deploy/signal_alert.py` (218줄) — 전환 카톡
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `already_alerted(as_of)` / `mark_alerted` | 상태 파일(`last_success_as_of`) · 못 읽으면 보내는 쪽 · 성공 뒤에만 원자 기록 | selftest PASS |
| `_fraction` / `validate_changed_b` | signal(−16)·freeze(−0.16) 단위 맞춤 · 대칭 문턱 · 상태=낙폭 규칙 | selftest PASS · R2-확인: `_fraction` 은 |v|>1 이면 /100 — 문턱 −1%~+1% 는 규약상 없음 |
| `main(sender)` | B 없으면 2 · 검증 실패 2 · 전환 아님 0 · 이미 성공 0 · 발송 rc≠0 → rc(상태 미기록 · 다음 슬롯 재시도) · 기록 실패 2 | selftest PASS · 메시지의 dd·close·as_of 는 최상위(전략 무관 값) ✓ |
소비자: `daily-signal.yml` id sigalert(c-o-e) → 실패 시 이슈 · 상태 파일은 커밋 목록에 있음 ✓ (push 거부 시 상태 미보존 → 다음 슬롯 중복 발송 가능 = 「누락보다 중복」 설계).

### B5. `deploy/notify.py` (296줄) — 채널 발송
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `kakao_chunks(text)` | 180자 한도 · 줄 단위 분할 · (i/n) 머리 | selftest PASS |
| `post` / `telegram_ok` / `kakao_token_body` / `kakao_send` | HTTP 200 안 실패 코드까지 검사(`message_ok`) | selftest PASS |
| `main()` | Discord → Telegram → 카카오(토큰 갱신 → 회전 시 GITHUB_ENV + gh secret · 실패 시 긴급 경고) → 분할 발송 · 종료코드 0/2/3 | selftest 회전 저장/실패 PASS · R2-01(분할 발송 부분 실패 = 전체 실패 → 첫 건 중복 재발송, B01-2 기록 유지) |

### B6. `deploy/kakao_keepalive.py` (290줄) / B7. `deploy/kakao_setup.py` (213줄)
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `token_values` / `refresh_body` / `message_ok` / `set_github_secret` / `activate_refresh_token` / `rotation_warning` | 응답 형식·줄바꿈 거부 · gh 실행 실패는 False · GITHUB_ENV 반영 | selftest PASS · 토큰 값은 어떤 경로로도 출력 안 함(판독) |
| `keepalive.main()` | secret 없으면 None(생략) · 갱신 실패 2 · 새 refresh 없으면 0 · 저장 성공 0/2(잡 반영 실패) · 저장 실패 → 카톡 경고 2 · 경고도 실패 3 | selftest PASS · `watchdog.mode_channel` 은 `rc != 0` 을 죽음으로 봄 → None 은 secrets 없을 때만이라 도달 불가(`kk and kr` 가드) ✓ |
| `setup.main()` | 사람용 대화식 · HTTP 400 본문 노출은 error 필드만 · 시험 발송 뒤에만 「성공」 | selftest PASS · 실행 대상 아님(대화식) |

### B8. `deploy/nav_collect.py` (564줄) — NAV 장부
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `fetch()` / `decode_naver` | 네이버 ETF 목록 cp949 → 예외는 그대로(예비 없음 — 설계) | selftest PASS |
| `universe_stats(lst)` | nav 있는 종목만 · |괴리|<20% · n<10 이면 0 | 판독 · `i['nowVal']` KeyError 는 collect 실패로 드러남(fail-closed) |
| `kr_market_open(now)` / `trading_as_of(now)` / `_kr_holidays` | 휴장표 검증(없음·파싱·범위 밖 → RuntimeError) · 장중 09:00~15:30 적립 금지 · 장 밖은 「값이 속한 거래일」 | §E 실측: 15:29 open/09-04 · 15:30 closed/09-04 · 09-05(토) 04:35 → 09-04 · 09-07 08:59 → 09-04 · 09:00 → 09-07 ✓ |
| `_validate_nav_rows` / `_atomic_append_rows` | 열·ISO·같은 날짜·감시 종목·이름·양수·괴리 20%·정수 univ_n·dev 재계산 0.00011 | selftest 6반례 PASS |
| `collect(as_of, now)` | 장중 → [] · as_of 미래 거부 · 기존 장부 전수 재검증(헤더·키·순서·**모든 날짜의 핵심 4종 완전성**) · 같은 날 핵심 완료 no-op · 과거 삽입 거부 · fetch → 핵심 4종 필수 → append | §E 실측: 실제 장부 81행 9일 전수 재검증 통과 · 마지막 날짜 no-op(네트워크 0) ✓ · R2-07(비핵심 종목의 quant/marketSum 누락도 전체 append 실패 — 엄격 설계 · 기록) |
소비자: `signal.html`(close·nav·dev·as_of by code · 마지막 행) · `price_now._last_known` · `research/exec_cost` · `surv_map` AUM · verify_all.

### B9. `deploy/watchdog.py` (1,217줄) — 파수꾼 9모드
| 함수/모드 | 계약 · 경로 | 근거 |
|---|---|---|
| `out` / `atomic_write_json` / `kst_today` / `biz_days_since` / `repeat_gate` | GITHUB_OUTPUT · 원자 쓰기 · 평일 수(미국 휴장 미고려 — 문턱 3 이 흡수: 2026 Labor Day·Good Friday·추수감사절 전수 §E) | selftest 61경우 PASS |
| `notify()` | notify.py 호출 · rc≠0 → alert=1 | rc 3(채널 없음)도 alert → 이슈 = 마지막 통로(설계) |
| `mode_stale` | as_of 손상/미래 → alert+알림 · n≥3 이고 (n−3)%3==0 일 때만 | selftest PASS |
| `defense_entry` / `rebalance_due` / `mode_rebalance` | 장부 SCHD 연속 첫 행(장부 밖이면 미확정) · 30일 주기·주말 다음 평일 · 오늘=목표일 | 판독 · 화면 `getDefenseEntryDate` 와 규약 동일(§C 대조) |
| `kr_holidays` / `kr_biz_days_since` / `kr_next_trading_day` / `last_switch` / `switch_exec_day` / `switch_action` / `mode_switchday` | 장부 changed=1 1차 + signal changed_today 2차(늦은 쪽) · 실행일 = as_of+1 부터 첫 한국 거래일 · B 없으면 A 로 안 물러섬 | selftest 13경우 PASS |
| `near_gaps` / `mode_near` | strategies.B · recent[].B(최상위 A 미러 무시) · 진입일(g0<3≤g1) · 종가 1영업일 안 · 전환일 생략 | selftest 12경우 PASS |
| `mode_channel` | 카카오 keepalive 실제 갱신(부작용: 토큰 회전) · Telegram getMe · Discord 무확인 · 무설정은 주간만 이슈 | selftest PASS · R2-확인: 하루 2회 갱신(05시 keepalive + 08:40 channel) — 카카오 규약상 허용, 회전 시 GITHUB_ENV·secret 갱신으로 정합 |
| `mode_stats` / `mode_price` | generated_at·as_of_kst 정규형·미래 거부 · 45일/3영업일 · repeat_gate | selftest PASS |
| `protocol_status` / `merge_ops` / `mode_check` / `check_worsened` | 점검.py --json 마지막 줄 · 평가기 문구로 판정(rc 만으로 안 함) · heartbeat 키 이월 · 악화 시만 알림 | selftest PASS · 실측(재등록 뒤) verdict ok · drift False |
| `mode_heartbeat` | 같은 달 1회 · 발송 성공 뒤에만 기록 | selftest PASS |
| `main()` | 모드 예외는 alert=1 · 항상 exit 0 | 판독 · watchdog.yml `if:` 가 9 id 를 전부 읽음 ✓ |

### B10. `deploy/price_now.py` (225줄) / B11. `deploy/price_poll.py` (513줄) — 표시 전용 시세
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `_finite_number` / `json_text` / `atomic_json_write` | bool·NaN·Inf 거부 · allow_nan=False · 원자 교체 | `price_poll --selftest` PASS |
| `fetch()` / `_last_known` / `_plausible` / `build` | 1차 네이버 → 빠진 종목만 `kr_sources` 예비(±25% · 기준 없으면 fail-closed) · nav 없으면 dev 생략 | selftest PASS(NaN/bool/Inf 3종 · 원자 보존) |
| `price_now.main()` | 항상 0 · 실패 시 기존 파일 유지 | 판독 |
| `price_poll`: `load_holidays` / `is_trading_day` / `phase_end` / `next_slot` / `snapshot` / `branch_items` / `publish` / `wake_pages` / `handover` / `cycle` / `main` | 휴장표 fail-closed · 09:00:20~12:26/15:56 · 5분 경계+20초 · 값 같으면 브랜치·배포 생략 · push 실패 로그에서 토큰 마스킹 · 연속 3회 실패면 종료 | selftest(85스냅샷·once 관문·3회 실패) PASS · R2-08(값이 같으면 as_of_kst 도 안 밀림 → 화면 「N분 전」이 마지막 **변화** 시각 — 신선도 과소 표시 · 기록) |

### B12. `deploy/kr_sources.py` (263줄) — 한국 시세 예비 출처 6종 (표시·기록 전용)
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `_num` / `_item` | 문자열·쉼표 제거 → float · nowVal 없으면 예외 · 등락률 없으면 None(정상) | 판독 · `price_now.build` 가 None 을 `chg_pct=null` 로 싣고 화면은 px 만으로 게이트(v202) ✓ |
| `naver_poll` / `naver_mobile` / `daum` / `toss` / `yahoo_chart` / `google_html` | 12초 타임아웃 · 종목별 · 구글은 HTML 첫 ₩ 금액(취약, 맨 뒤) | 판독 · 값 오염은 `price_now._plausible`(±25%) 가 막는다(v200) — 기준(nav_history)이 없으면 싣지 않음 ✓ |
| `fetch_any(code)` | CHAIN 순서로 첫 성공 | 판독 · 어떤 출처도 NAV 를 안 줌 → 괴리 배지 숨김(v146) ✓ |
| `history(symbol, count)` / `history_df` | 네이버 일봉 XML(비수정) · adj=close · KST 15:40 전이면 오늘 봉 제거(벽시계) | 판독 · ETF 는 `splice_kr` 가 실패-폐쇄하고 KOSPI 만 허용(v203) ✓ · 주말엔 마지막 봉 날짜≠오늘이라 유지 ✓ |
| `probe()` | 생존표 출력 · 파일 무접촉 | 판독 · `source-probe.yml` 수동 전용 |
판정 경로(`update_signal`·`wait_close`)는 이 모듈을 임포트하지 않는다 — `verify_all g_signal_coupling` 이 고정 ✓.

### B13. `deploy/kr_holidays.py` (513줄) — 휴장일 표 산출
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| 음력 표·`SPECIAL`·`ERA`·`SUB_FROM` | 2027 이후 대체휴일 규칙은 `SUB_FROM` 으로 연도별 적용 · 임시공휴일은 손으로 | 판독 · 표 범위 밖 연도는 예외(조용한 빈 표 없음) |
| `holidays(year)` / `emit(path)` | y0=올해−1 … +7 · 연 최소 6일 검사 · 내용 같으면 쓰지 않음(커밋 소음 방지) | `--selftest` PASS(I14) · watchdog 주간 슬롯이 호출 ✓ · 2026-10-05 대체휴일 등 실제 표와 `nav_collect`·`price_poll`·화면 `krClock` 이 같은 파일을 읽음 ✓ |

### B14. `deploy/refresh_hist.py` (1,170줄) — 월간 원자료 연장 · **R2-11·R2-12 수정**
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `_bar_index(ts, meta)` **(신설)** | 봉 라벨 = 거래소 시간대 달력일(야후 화면과 같은 날짜) · 시간대 모르면 UTC | 신규 검사 §E-7 · 미국 13:30Z·한국 00:00Z·시카고 12:20Z 는 라벨 불변, FX(런던 23:00Z 시작·서머타임)만 바뀜 |
| `_drop_intraday_bar(df, meta, now)` **(수정)** | `start<=qt<end` 이고 **벽시계가 마감 전**일 때만 세션 시작일부터 제거 | 옛 코드: ^TNX 는 qt=18:59<end=19:00 이 마감 뒤에도 참 → 확정봉 삭제(실측 §E-5·§E-6) · 새 선택검사 4경우 |
| `_drop_kr_intraday_bar(df, now)` | 네이버 일봉 KOSPI 전용 · 09:00~15:30 KST 벽시계 | selftest PASS |
| `chart(symbol, years, require_adj, now)` | 배열 길이·중복·역순·placeholder 제거·장중 제거·결측 검증 · 수정주가 필수 경로는 raw 대체 금지 | selftest PASS(placeholder·부분 결측·오염·adj 없음 반례) |
| `_validate_download` / `_already_current` / `append_rows` / `_atomic_append_*` / `_csv_header` | 0행=실패 · 이음날 필수 · 신선도(미국 8일·한국 16일) · prefix 바이트 보존 · 교체 실패 시 원본 유지 | selftest PASS |
| `splice_us` / `splice_kr` / `splice_tnx` / `splice_gold` | 비율 이음(k) · OHL 동비율 · 한국 두 형식 · TNX 수준값(±75%·0.01~30) · GLD 수익률 이음 | selftest PASS · R2-13: `splice_tnx` 만 `chart()` 예외를 잡지 않아 야후 장애 시 traceback 종료(뒤 8파일 미시도 · 실패-폐쇄 자체는 유지) — P4 기록 |
| `refresh_fx` / `_validate_fred_payload` / `_fred_last_valid` / `_fred_last_date` | FRED 원문 검증(열·날짜·비수치·후퇴·미래·신선도·길이) · 물리 마지막 날 뒤만 append · 실패 시 야후 KRW=X strict append · 둘 다 낡으면 실패 | selftest PASS · **R2-12**: 야후 라벨이 하루 일러 금요일 FRED 꼬리를 못 이었다(§E-7) · 문서 불일치 P4: `_validate_fred_payload` docstring 은 `.` 행을 파일에 남긴다고 하나 `refresh_fx` 는 값 있는 행만 붙인다(코드가 맞고 설명이 낡음) |
| `main()` | 순서 고정 · FAILURES 있으면 1(build_stats 차단) | 2026-09-01 실행 로그(§E-5) 로 실제 동작 확인 |

### B15. `deploy/build_stats.py` (513줄) — 월간 성과 스냅샷
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `json_text` / `atomic_write` / `metric_text` / `signal_stats_text` | allow_nan=False · 임시파일 교체 · 사본 같으면 None | `--selftest` PASS |
| `horizons(curve)` | 끝 맞춘 5/10/15/20년 배수 · 구간 부족 None | 판독 · 화면 `drawHoriz`·각주 h20 소비 ✓ |
| `pack(curve, turn)` | 유한·양수·정렬 검증 · calmar/sortino/sharpe 비유한이면 **None** | 화면이 calmar None 을 못 받던 것 R2-22 수정(signal.html) |
| `seg_of` / `bench_pack` / `sc_*` / `kr_basket` / `hedge_*` / `sync_doc` / `main` | 벤치마크 같은 구간·재료 · 문서 마커 검증 후 쓰기 · 두 JSON 원자 쓰기 | selftest PASS · §E 대조: 화면 정적 수치(설명서 ①③④⑤⑫)가 현행 `strategy_stats.json` 과 일치 · P4: `sync_doc` 이 두 JSON 뒤에 돌아 그 단계 실패 시 문서만 옛 판(다음 달 자가 치유) |

### B16. `deploy/data_check.py` (201줄) — 다운로드 검증 게이트
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `validate_frame(...)` | None/0행 실패 · 열 누락 · 날짜 결측/중복/시각 포함/역전 · 이음새 공백(prev_date) · 결측/무한/0이하 · 절대범위 · 열별 이음새 변동 · OHLC 관계 | `--selftest` 10반례 PASS · 호출자 4곳이 prev_date/prev_values 를 넘김 ✓(2026-09-04 정정 유지) |

### B17. `deploy/stamp_rev.py` (126줄) — 화면 개정 도장
| 함수 | 계약 · 경로 | 근거 |
|---|---|---|
| `parse_git_rev` / `git_rev` / `stamp_text` / `atomic_write` / `main` | TZ=Asia/Seoul · 정확히 1개 표식 · JSON+`<>&` 이스케이프 · 인자 3개 초과 거부 | `--selftest` PASS · pages.yml 인자 2개 ✓ · P4: 화면 `paintRev` 가 innerHTML 로 넣지만 값은 저장소 커밋 제목(외부 입력 아님) |

## C. 화면 3개 — 함수 단위 (signal.html 3,559 · guide.html 916 · notes.html 1,046 전문 판독)

### C1. `signal.html`
| 묶음 | 함수 | 계약 · 상태 · 실패 경로 | 근거 |
|---|---|---|---|
| 부팅·렌더 | `boot` → `redraw` → `renderAuto`/`render` · `paintState` · `paintProx` · `clearCard` · `setMsg` | signal.json 실패 → 수동 모드 + 배너(http 만) · `strategies.B` 없으면 수동 · 60행 미만은 판정 안 그림(v202) · resize 마다 재렌더 | §E-9 브라우저: 자동 모드 정상 · 412px 가로 스크롤 0 · 콘솔 오류 0(price.json 404 만 — 로컬엔 그 브랜치 파일이 없어 배지 숨김 = 설계) |
| 시세(표시 전용) | `loadPrice` · `priceAgeMin` · `priceOf` · `chgBadge` · `devBadge` · `refreshPrice` · `startPriceTicker` · `loadNav` · `curPx` · `paintVpx` | 단일 진입점 `curPx`(더 최신 쪽) · PRICE null 이면 재도색 · 5분 티커는 한국장 중만 · 판정 무접촉 | 판독 · R2-08(가격 불변 시 as_of 정체)은 발행 쪽 설계 |
| 포트폴리오 | `portAssets` · `drawPort` · `portCompute` · `wrongSideWeight` · `drawPending` · `orderMemo` · `tlogChips` · `drawGoal` · `drawFx` | 목표비중은 signal.json 의 risk/defensive · 2%p·한 주 값어치 분기(v202) · 미체결 경고는 보유 반대편 | 판독 · 문구 「137번 중 70번(51%)」 정정(R2-23) |
| 체결·백업 | `tlAdd` · `drawTlogList` · `tradeDelayMap` · `applyState` · `applyBackup` · `sanitizeBackup` · `backupLink` · `consumeBackupLink` · `abInit/abWrite` · `dlBlob` | 살균(코드 6자리·ISO 날짜·side·숫자) 뒤 innerHTML · dq 로 취소 · fragment 링크는 처리 전 제거 | 판독 · 외부 입력이 HTML 로 들어가는 경로는 살균 뒤뿐 ✓ |
| 방어 경과·재조정 | `getDefenseEntryDate` · `drawVDday` · `drawDefDays` · `drawDefDur` · **`daysSince`(수정)** | 프라미스 캐시(실패 미기억) · 진입일부터 30일·2일 유예 · **달력일(KST) 차이** | §E-9: 08:40 KST 가짜 시계에서 30일째 → 「재조정일」(옛 코드 D-1) · 파수꾼 `rebalance_due` 와 같은 정의 |
| 신선도 | **`bizDaysSince`(수정)** · `showStale` · `freshDot` · `paintFreeze` | 평일 수 · 미국장 진행 중엔 오늘 제외 · 문턱 2/4 | §E-9: 01:00 KST 장중 → 1(옛 2) · 08:40 → 2(파수꾼과 동일) · 미국 휴장은 파수꾼과 같이 세지 않음(문턱 3 흡수, 변경 안 함) |
| 성과표 | `drawPerf` · `drawHoriz` · CSV 내보내기 · `gCal/gSor/gUlc` | STATS(signal.json 사본 우선) · 20년 각주는 같은 원천 · **calmar null 가드(수정)** | §E-9: calmar null 주입 → 예외 0 · 「—」 표시 |
| 시계·달력 | `tzParts` · `wall` · `usHolidays` · `usEarly` · `usSession` · `usClock` · `krClock` · `drawClock` · `stamp` | NYSE 휴장 규칙(신정 토요일 미관측·굿프라이데이·Juneteenth 관측 등)·조기마감 3종 · 한국 휴장표 | 판독 + node 재계산(§E-8) · 2026-09-07 노동절 = 휴장으로 인식 ✓ |
| 보조 | `drawOpsCheck` · `drawOosHist` · `drawTogether` · `drawMissed` · `t4Agreement` · `drawT4` · `paintFact` · `paintDdPct` · `initTimeMachine` · `drawTrajectory` · `setupFold` | ops_check 는 textContent 만 · verdict 고정 표 · 파일 없으면 숨김 | 판독 · `FACTS[1]` 정정(R2-23) |

### C2. `guide.html` · C3. `notes.html`
| 항목 | 확인 | 근거 |
|---|---|---|
| 설명서 정적 수치 ↔ `strategy_stats.json` | ① 26.7년·21.2%·−98.8→−48.4 ✓ · ③ −60.5 vs −68.1 ✓ · ④-4 −56%·4.7년(kr_1997 −55.97·56.6개월) ✓ · ④-6 −37%·−17% ✓ · ⑤ 167/21.2/63/16.8/−48.4/−38.5 ✓ · ⑤ 배당100 −65 vs −46(us_1972 hedge_div −64.82/hedge −46.15) ✓ · ⑫ −56% ✓ | §E-4 스크립트 대조 |
| 설명서 ③ 전환 통계 | 139/75(54%)/102/20 → **137/70(51%)/103/21**(ops_risk v210 재실행) | R2-23 · §E-3 |
| 설명서 ⑥ 인출 소득 | −51.3% → **연 5% 예시 최악 −55.9%**(withdraw [5]·[6] 재실행, 이전 인출 반영) | R2-23 · §E-3 |
| 설명서 ⑩·⑪ | LEVERAGE_US §11·T4 v215 재계산값 그대로(연구 영역 — 이 리뷰에서 변경 안 함) | 판독 |
| 설명서 JS | `openFoldTarget`(앵커로 접힌 절 펼침) · `setupFold` 3상태 · 검색은 textContent | 판독 · 412px 가로 스크롤 0 · 콘솔 오류 0(§E-9) |
| 업데이트 노트 | 히어로 동결일 fetch(실패 시 하드코딩) · `revCnt` 첫 항목에서 · 필터/접기 · v220 항목 추가 | 판독 · P4: v205 「탐색기 원본 못 찾아 미갱신」 vs v206 「원본 확인해 다시 발행」이 서로 다른 말을 한다(문서 정합 — 통합 담당 확인 요망, 이 리뷰에서 손대지 않음) |

## D. 데이터 계약 (생산자 → 소비자)
| 파일 | 생산자 | 소비자·필드 | 확인 |
|---|---|---|---|
| `data/signal.json` | update_signal | 화면(as_of·close·high_252·dd·strategies.B·recent[].B·stats·risk·defensive·updated_at_iso) · signal_alert·watchdog(strategies.B·recent[].B) · oos_log · wait_close(as_of) | 최상위 state/exit 는 A 미러 — 새 소비자 0 ✓ |
| `data/qqq.csv` | update_signal(전체 재작성) | oos_log 원천 대조 · fetch_naver 기준 | 비원자 쓰기지만 커밋 경계가 원자(§B1) |
| `data/strategy_stats.json` | build_stats | 화면 drawPerf/drawHoriz/각주 · signal.json 사본 | calmar None 가능 → 화면 가드(R2-22) |
| `data/nav_history.csv` | nav_collect(장 밖 슬롯 · 직전 거래일 종가) | 화면 curPx(as_of 비교) · price_now 기준 · research | 비핵심 행 결측이 핵심 장부를 막던 것 수정(R2-07) |
| `data/price.json`(price-data 브랜치) | price_poll/price_now | 화면(items[code].px/chg_pct/nav/dev_pct · as_of_kst·as_of_iso) | 없으면 숨김 · 값 불변 시 as_of 정체(R2-08 기록) |
| `data/oos_log.csv` | oos_log | 화면(as_of·state·changed·t4_*) · watchdog · research | append-only · 전행 재검증 |
| `data/ops_check.json` | watchdog check/heartbeat | 화면 drawOpsCheck(as_of ISO 날짜·todo·protocol_b) | as_of 는 날짜만 → Date.parse 안전 ✓ |
| `data/kr_holidays.json` | kr_holidays --emit(주간) | 화면 krClock · nav_collect · price_poll · watchdog | 범위 밖은 fail-closed(price_poll·nav_collect) · 화면은 주말만(설계) |
| `data/freeze.json` · `dd_percentile.json` · `crisis_paths.json` | 동결·월간·수동 | 화면 | 없으면 숨김/기본값 ✓ |
| 원자료 CSV(`qqq/qld/schd_us_d`·`data/hist/*`) | refresh_hist(월간 append) | build_stats·research | **^TNX 하루 누락(R2-11)·FX 라벨(R2-12) 수정** — 이미 저장된 행은 손대지 않음(다음 월간 실행이 08-28 부터 붙인다) |

## E. 실행한 검사 (전부 네트워크 부작용 0 · 실측 장부 무접촉)
1. 기준 `python verify_all.py`(전체) 실패 0·경고 0 → 수정 뒤 `--fast` 실패 0 · 전체 실패 0(10초).
2. I14 셀프테스트 16종 PASS(수정한 `refresh_hist`·`nav_collect` 는 새 경우 포함).
3. 연구 재실행(읽기 전용): `research/ops_risk.py` → 전환 137회 · 손실 70(51%) · 최장 연속 10회 −20.4% · 놓쳐도 이득 103 · 10% 초과 손실 21 · 최악 −96.5%(2000-09-06) / `research/withdraw.py` [5]·[6] → 전략 B 5% 인출 롤링 1년 최악 −55.9%(위상 중앙 −40.5% · 이전 고점 대비 41.1%) · 무인출 −53.6%.
4. 설명서 정적 수치 ↔ `strategy_stats.json` 스크립트 대조(§C2 표).
5. 2026-09-01 월간 실행 로그(run 33482041769) 판독: 미국 3종·TNX 「추가 0행(이미 최신)」 — 당시 코드의 `qt<end` 가드가 개장 전 전일 확정봉을 지운 것(2026-09-04 정정 전) · FRED 타임아웃 후 「기존 유지」(옛 코드).
6. git 이력: `yahoo_TNX.csv` 마지막 날짜가 9704ac0 에서 08-27(QQQ 08-28) · 그 부모에서 08-25(QQQ 08-26) — 매 실행 하루 누락(R2-11).
7. 야후 메타 읽기 전용 조사(2026-09-05 07:49 UTC · 스크래치 저장): QQQ qt=20:00=end(장중 아님) · 418660 qt=06:30≥end 06:00 · **^TNX qt=18:59<end 19:00 → 현행 가드가 09-04 확정봉을 지움** · KRW=X 봉 시작 23:00Z(런던 서머타임) → UTC 라벨이 하루 이름. 이 응답을 고정 응답으로 삼아 `audit/test_ops_review2.py` 3검사 작성 — 옛 사본(e63af37)에서 3실패+1오류, 수정 뒤 11/11 통과(`OPS_REVIEW2_OLD` 로 재현 가능).
8. `signal.html` 의 `daysSince`·`bizDaysSince`·시계 함수 본문을 node 로 가짜 시계 실행(같은 검사 파일): 08:40 KST 30일째 → 30(옛 29) · 미국 장중 01:00 KST → 1(옛 2) · 08:40 → 2(파수꾼 동일).
9. 브라우저(로컬 정적 서버 · 수정본): signal.html 데스크톱/412×915 — 판정 카드·성과표 정상, 가로 스크롤 0, 콘솔 오류 0(price.json 404 만), calmar null 주입 시 예외 0·「—」, 가짜 시계+가짜 장부로 `drawVDday`/`drawDefDays` 「재조정일 · 30일 경과」 확인 뒤 원상복구 · guide.html 412 — 정정 문구 4곳 렌더, 가로 스크롤 0 · notes.html — 통합 뒤 확인(§G).
10. `nav_collect` 실장부 드라이런(네트워크 0 · 마지막 날짜 no-op) · `trading_as_of` 경계 5경우.
**실행하지 않은 것**: 실제 야후·FRED·네이버 호출을 수반하는 월간 갱신 본실행 · 알림 발송·토큰 회전 · `price_poll` 발행 · 파수꾼 실모드 · 배포 사이트 반영 확인(§G 에서 push 뒤 별도).

## F. 발견 (심각도 · 발생 조건 · 영향 · 처리)
| ID | 등급 | 위치 | 조건 → 영향 | 처리 |
|---|---|---|---|---|
| R2-11 | **P2** | `refresh_hist._drop_intraday_bar` | 마감 뒤에도 qt<end 인 지수(^TNX 18:59) → 월간 실행마다 전일 확정봉 삭제 → `yahoo_TNX.csv` 가 늘 하루 짧고 국채 다리 마지막 날 수익이 이월값(다음 달 자가 보충) | **수정** + 셀프테스트·회귀검사 · 저장 행 무접촉 |
| R2-12 | **P2** | `refresh_hist.chart` 라벨 · `refresh_fx` 야후 보강 | 서머타임 FX 봉 라벨 하루 이름 → 금요일 FRED 꼬리를 못 이어 예비 경로 실패-폐쇄(월간 갱신 전체 실패로 드러남) · 월~목 꼬리면 하루 어긋난 날짜로 붙음 | **수정**(거래소 시간대 라벨) + 검사 |
| R2-07 | **P3** | `nav_collect.collect` | 비핵심 감시 종목 한 줄의 결측이 핵심 4종 장부까지 차단 → 실측 괴리 표본 공백 | **수정**(비핵심만 격리·경고) + 셀프테스트·회귀검사 |
| R2-21 | **P3** | `signal.html daysSince` | UTC 자정 기준 → 재조정 확인일 00:00~09:00 KST(08:40 카톡 시각 포함) 화면 D-1 · 장부 일수·백업 리마인더도 09시 경계 | **수정**(KST 달력일) + node 회귀검사 |
| R2-23 | **P3** | 설명서 ③·⑥ · 신호 화면 FACTS·체크리스트 | v210 정정 뒤 재실행 안 된 전환 통계(139/75/102/20)와 옛 인출 최악(−51.3%)이 화면에 남음 | **수정**(재실행값 137/70/103/21 · −55.9%) + 정적 대조 검사 |
| R2-22 | **P4** | `signal.html drawPerf/CSV/심사` | build_stats 가 calmar null 을 낼 수 있는데 화면은 toFixed → redraw 전체 중단(현재 자료로는 발생 안 함) | **수정**(null 가드) + 검사 |
| R2-20 | **P4** | `signal.html bizDaysSince` | 미국 장중(00:00~05:00 KST) 매일 「2거래일 경과·확인 필요」 노란 점 | **수정**(장중엔 오늘 제외 · 파수꾼 정의 불변) |
| R2-13 | P4 | `refresh_hist.splice_tnx` | `chart` 예외를 안 잡아 야후 장애 시 traceback 종료(실패-폐쇄는 유지 · 뒤 8파일 미시도) | 기록(통합 담당 판단) |
| R2-05 | P4 | `update_signal` CSV/JSON 비원자 쓰기 · `load_cached` 예외 미포착 | 로컬 수동 실행 중단 시만 해당 · Actions 는 커밋 경계가 원자 | 기록 |
| R2-06 | P4 | `wait_close.main` | 예상일 조회가 계속 실패하면 갱신됐어도 시한 뒤 exit 1(거짓 실패 알림 · 8슬롯이 재시도) | 기록 |
| R2-08 | P4 | `price_poll.cycle` | 4종 가격이 5분간 불변이면 as_of_kst 정체 → 화면 「N분 전」 과소 표시 | 기록(설계상 값 불변 시 배포 생략) |
| R2-01 | P4 | `notify` 분할 발송 | 부분 실패 = 전체 실패 → 다음 슬롯 첫 조각 중복 | 기록(누락보다 중복 설계) |
| R2-24 | P4 | `paintRev` innerHTML · `refresh_fx` docstring · notes v205/v206 문장 · `sync_doc` 순서 | 외부 입력 아님 / 설명 낡음 / 문서 정합 / 실패 순서 | 기록 |
**P1 없음.** 실제 매매 규칙·판정·실측 장부·원자료 저장 행은 이 리뷰에서 바꾸지 않았다.

## G. 통합·검증 (push 뒤 기입)
- 통합 직전 `origin/main` = e63af37(기준과 동일 · 겹친 변경 0) → `review/ops-ui-2` 를 빨리감기로 push → **d27b90f**.
- CI: 검증 run 33954865758 success(unittest 154개 OK · `audit.test_ops_review2` 11개 포함 · `--fast`·전체 실패 0) · Pages 배포 run 33954865759 success.
- 배포 사이트 실측(curl · 2026-09-05 17:2x KST): index.html `HTML_REV = v220 · 2026-09-05 17:17` · 체크리스트 「137번의 전환 중」 · guide.html 「137번 중」·「−55.9%」·「139번」 0 · notes.html v220 항목·시즌 v186–v220.
- 소유자 작업 폴더(main)는 깨끗한 e63af37 상태였고 손대지 않았다 — `git pull` 로 빨리감기된다.
