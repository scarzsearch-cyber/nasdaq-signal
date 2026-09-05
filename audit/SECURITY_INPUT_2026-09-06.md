# 보안·입력 경계 감사 (2026-09-06)

> 기준 97cc391 · 작업트리 `review/doc-claims-10`. 합성 입력·로컬 사본·격리 클론으로만 재현했다 — 실제 서비스 공격·실제 토큰 사용·알림 발송 없음.
> 민감정보는 **위치와 종류만** 적는다(값 복사 없음). 소유자 규정(v198): 보유 수량 등 개인정보는 감사 대상이 아니다 — 토큰·키·자격증명만 본다.
> 회귀: `audit/test_repro6.py` S1 · `deploy/kakao_keepalive.py --selftest`(I14).

## 0. 기존 장부에서 이미 확인한 항목 — 이번에 제외
| 항목 | 기존 근거 | 이번 처리 |
|---|---|---|
| `#backup=` 링크 → `sanitizeBackup`(코드·날짜·side·수량 살균 · 조작 링크 4종 거부) · 확인창 · 되돌리기 | CLAUDE v186 · MOBILE_OPS v225 | 제외(재검 안 함) |
| CSV 임포터 행 검증(날짜 `^\d{4}-\d{2}-\d{2}$` · 종가 양수 · 버린 행 계수) | v202 · SCREEN_STATES v223 | 제외 — 이번엔 「검증된 행만 innerHTML 에 간다」만 코드로 재확인 |
| `drawOpsCheck` todo 는 textContent · `protocol_b.verdict` 고정 표 | v140 · v188 · v225 | 제외 |
| `paintRev` innerHTML(커밋 제목 → 버전·날짜만 추출) | v221 R2-24 | 제외 |
| `stamp_rev.py` JSON+`<>&` 이스케이프 | v220 | 제외 |
| 워크플로별 트리거·체크아웃 커밋·쓰기 권한·동시성 표 | 순회 B02 | 제외 — 이번엔 **permissions 블록 유무·이벤트 표현식 주입·액션 고정**만 |
| 토큰 회전 경로(GH_PAT 부재·secret 저장 실패·긴급 경고·rc) | SURVIVAL S2 · v203 | 제외 — 이번엔 **로그 노출(마스킹)** 만 |
| 코드·커밋의 토큰·키 문자열 0 | 순회 §12 · v197 | **재확인**(정규식 확장 + 전체 이력) |

## 1. 새로 검사한 범위와 결과

### 1-1. 입력 경로 → 화면 출력 (`signal.html` innerHTML 88곳 · guide/notes 0곳)
| 입력 | 경로 | 판정 |
|---|---|---|
| URL 해시 `#id`(세 화면 `openFoldTarget`) | `location.hash.slice(1)` → `document.getElementById` (querySelector 아님 → 선택자 주입·예외 없음) | ✅ |
| URL 쿼리 `?…` | 세 화면 어디도 `location.search`·`URLSearchParams` 를 읽지 않는다 | ✅ 해당 없음 |
| 체결 입력(`tlQty`·`tlPx`) · 수동 종가(`inClose`) · 환율 입력 | `pnum`/`parseFloat` 로 숫자만 저장 · 종목은 `<select>` 상수 · 날짜는 앱이 생성(`kstStamp`) 또는 `<input type=date>` | ✅ (`type=date` 미지원 브라우저의 자유 문자열은 **본인 입력 self-XSS** 범위 — 위험 아님) |
| 백업 파일(`tlImpFile`) | `applyBackup` → `sanitizeBackup`(v186 공용) | ✅(기존) |
| 외부 스크랩 문자열(네이버 종목명 · `price.json.source`) | `nav_history.csv` 의 name 열·`price.json.source` 는 **화면이 읽지 않는다**(px·d·chg_pct 숫자만) · 화면의 종목명은 `LEGS` 상수 | ✅ 스크랩 문자열이 innerHTML 에 닿는 경로 0 |
| 파이프라인 산출 JSON 문자열의 미이스케이프 삽입 | `ops_check.json.as_of` · `freeze.json.frozen_at` · `price.json.as_of_kst`(`cur.src`) · `signal.json.as_of` · `crisis_paths.json` 키 → innerHTML 직접 | ⚠ 관찰 — 전부 저장소 코드(`watchdog`·`update_signal`·`price_poll`·연구 스크립트)가 날짜·상수로 만든다. 신뢰 경계가 「저장소·Actions」라 공격면이 아니지만, 새 필드를 넣을 때 **문자열은 textContent 로** 가 규약(수정 0 · 제안 §3) |
| `guide.html` 검색 | textContent 대조 · 결과 표시에 질의 문자열을 innerHTML 로 넣지 않는다 | ✅ |

### 1-2. 백업·로그·배포 산출물의 민감정보
| 대상 | 결과 |
|---|---|
| 추적 파일 498개 정규식 스캔(GitHub PAT · AWS · Slack · Telegram bot · Discord webhook · 카카오 REST/refresh 형태 · JWT · PEM · 이메일) | **0건** |
| 전체 이력 557커밋 diff(+/− 줄 440,879 · 원자료·docs 제외) 같은 정규식 | **0건** · 토큰·키 이름의 파일이 추가된 적 없음 |
| 배포 산출물 `_site`(pages.yml 복사 목록) | 세 화면 · PWA 2 · `data/` 9종(전부 공개 저장소 파일) · `signal_alert_state.json`·`ops_check.json` 의 키는 상태·todo 뿐 |
| 백업 파일·링크(보유·평단·체결) | 소유자 규정대로 대상 아님(v186 확인창·v198) |
| Actions 로그 | **발견 S2**(아래) 외 토큰 값을 print 하는 경로 없음(`kakao_setup.py` 는 로컬 설정 도구라 의도적으로 출력) |

### 1-3. 워크플로 권한·외부 입력
| 검사 | 결과 |
|---|---|
| `permissions` 블록 | 8종 중 **notify-test.yml 만 없음** → 저장소 기본 권한(write · SURVIVAL 확인)을 물려받았다 — **발견 S1** |
| `run:` 안 `${{ }}` 이벤트 표현식 주입 | `steps.*.outcome`(daily-signal) · `github.event.schedule`(watchdog · env) · `github.event.inputs.mode`(price · env 경유) 뿐 — 공격자 통제 문자열(이슈 제목·PR 브랜치명 등) 0 |
| `pull_request` 트리거 | verify.yml 만 — 포크 PR 은 토큰 읽기 전용이라 이슈 스텝만 실패(노이즈) · `pull_request_target` 없음 |
| 제3자 액션 | 전부 GitHub 공식(`actions/*`) · 메이저 태그 고정(v4~v7) · 외부 저장소 액션 0 — SHA 고정은 제안(§3) |
| price-data 브랜치 → Pages | 못 읽으면 안 싣는다(v176) · 같은 신뢰 경계 |

## 2. 발견·수정 (재현 → 최소 수정 → 수정 전 실패/수정 후 통과 → 회귀)
| # | 발견 | 재현 근거 | 수정 | 검사 |
|---|---|---|---|---|
| **S1** | `notify-test.yml` 이 `permissions` 없이 저장소 기본 권한(write)으로 돈다 — 잡은 GITHUB_TOKEN 을 쓰지 않는다 | 8개 yml grep · SURVIVAL 「기본 토큰 권한 write」 | `permissions: contents: read` 추가 | `test_repro6.S1`(8종 전부 블록 존재 · notify-test 읽기 전용) — 수정 전 FAIL 확인 |
| **S2** | 회전된 카카오 refresh 토큰을 `GITHUB_ENV` 에 넘길 때 **마스킹이 없다** — `secrets` 문맥과 달리 러너가 자동으로 가리지 않아, 뒤 스텝이 환경을 찍거나 예외 문구에 실리면 로그에 남는다 | `activate_refresh_token` 판독 · 옛 코드로 stdout 캡처: `::add-mask::` 0 | 실제 Actions(GITHUB_ACTIONS=true · 명시 인자 없이 진짜 GITHUB_ENV)에서만 `::add-mask::<값>` 을 먼저 낸다(그 줄은 러너가 로그에서 지운다) · 로컬·명시 파일 인자에서는 출력 0 · 셀프테스트가 GITHUB_ACTIONS 도 격리 | `kakao_keepalive --selftest` 회전 토큰 마스킹 블록(옛 코드 mask 0 → 새 코드 정확히 한 줄 · 로컬은 토큰 미출력) · `notify --selftest` · I14 |

현재 워크플로 스텝 중 환경을 통째로 찍는 곳은 없어 **실제 노출 사례는 확인되지 않았다** — S2 는 예방 수정이다.

## 3. 제안(수정 안 함)
- 화면 규약 한 줄(설명서 아님 · 개발 규약): 파이프라인 JSON 의 **문자열 필드는 textContent** 로, innerHTML 은 숫자·상수·이스케이프된 값만 — `drawOpsCheck` 의 `as_of` 등 6곳은 현재 무해하나 새 필드를 붙일 때 같은 자리에 넣기 쉽다.
- 제3자 액션 SHA 고정(`actions/checkout@<sha>` 등): 공식 액션뿐이라 위험은 낮고 갱신 부담이 생긴다 — 소유자 판단.
- verify.yml `pull_request` 트리거: 포크 PR 에서 이슈 스텝이 실패하는 노이즈 — 저장소가 1인 운영이라 트리거 제거 여부는 판단 사항.

## 4. 미확인 (다음 자연 회전 때 · 확인용 회전 금지)
- S2 의 `::add-mask::` 가 실제 Actions 로그에 적용되는 모습은 **카카오가 다음에 자연스럽게 새 refresh 토큰을 줄 때**만 확인된다(시점 불명). 확인하려고 회전을 일으키거나 토큰·환경을 출력하지 않는다 — 격리 검사는 stdout 명령 문자열까지다.
- 카톡 도착·실기기는 기존대로 미확인.

## 5. 보안 강화 후보 (확인된 취약점이 아님 · 소유자 판단)
- **CSP 부재**: 세 화면에 Content-Security-Policy 가 없다. 이번 범위에서 외부 입력이 innerHTML 에 닿는 경로는 못 찾았고(「없음」의 증명은 아님), 같은 오리진 XSS 가 생기면 localStorage 장부 전체가 노출되는 구조는 그대로다. 정적 페이지라 `default-src 'self'` 계열 메타 한 줄로 시작할 수 있으나 인라인 스크립트 단일 파일 구조(v141 비상 판정 전제)와의 정합을 먼저 봐야 한다 — 후보로만 남긴다.
- 파이프라인 JSON 문자열의 textContent 규약 · 액션 SHA 고정 · verify.yml pull_request 노이즈(§3) 도 같은 등급(취약점 아님 · 강화 후보).
