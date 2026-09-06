# 운영·설정 미반영 항목 처리 — 설치·인코딩 · 복구 입구·개발 규칙 · 액션 SHA 고정 (2026-09-06)

> 기준 ce17a6d · 작업트리 `review/doc-claims-10`. 새 전수검사·연구 재계산 없음 — 기존 장부(`REPRO`·`RECOVERY_DOCS`·`SECURITY_INPUT`·`CSP`)의 제안만 처리.
> 사용자 전역 환경·원자료·연구 엔진·`verify.yml`·돈전략 담당 문서(01/02/04)·OOS 규약·BANDS·타임머신 생성 무변경. 실제 카톡·토큰 회전·운영 장부 조작 없음.

## 1. 설치·실행 안내와 인코딩 잔여물 (REPRO §5 · R3)
| 항목 | 확인한 근거 | 처리 |
|---|---|---|
| README 「설치」 없음 | 워크플로 5개 `pip install pandas numpy`(미고정) · 저장소 `.py` 전체의 서드파티 import = **numpy·pandas 둘뿐**(정규식 전수) · Python 3.12(price.yml 3.11) | **적용** — README §2 끝에 「설치 — 처음 한 번」: 의존성 두 개 · 정적 서버(`python -m http.server`) · `file://` 경고가 정상 · Git Bash·gh |
| `requirements.txt` 제안 | 직접 의존성 2개가 워크플로 5곳에 이미 적혀 있고, `verify.yml` 은 돈전략 편입 판단과 겹쳐 참조 전환 불가 → 파일을 만들면 같은 두 줄의 6번째 사본 | **현행 유지** — 만들지 않음(README 에 이유 명시) |
| README 137행 「어디서 실행하든」 | R1(8fc6a08)로 `verify_all.py` 도 자기 위치를 cwd 로 잡는다 | **적용** — 한 문장 추가 |
| **R3** `audit/test_ops_recovery3.py:761` 인코딩 없는 `open` | 읽는 파일 = 테스트가 만든 `signal.json`(ASCII) — 그러나 **실제 `data/signal.json` 은 UTF-8 한글 342자**. 같은 파일을 **`daily-signal.yml` 「변경분 커밋」 셸의 `python3 -c` 두 곳**(`json.load(open(...))` · `json.load(sys.stdin)`)도 인코딩 없이 읽는다. 러너(ubuntu)는 UTF-8 로캘이라 CI 오류는 아니다 | **적용** — 테스트 읽기에 `encoding='utf-8'` · 셸 두 곳을 명시 UTF-8(`open(..., encoding='utf-8')` · `io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')`) · verify_all g_deploy 의 `REMOTE_ASOF` 관문 유지 |
| 한글 경로·내용 회귀 | S6 `_seed`·`_set_asof` 가 `{'as_of', 'note': '한글 내용 · 종가 확정'}`(ensure_ascii=False)을 쓰고, 중복 커밋 검사는 임시 폴더 `경쟁_race_*` 에서 돈다 | **적용** — 변조 검사: 셸의 인코딩 명시를 지우면 Windows cp949 에서 S6 **3/5 FAIL**(`UnicodeDecodeError cp949 … 0xed`) · 복원 후 5/5 OK |

## 2. 복구 안내와 개발 규칙 (RECOVERY_DOCS §4 · SECURITY_INPUT §3)
| 항목 | 처리 |
|---|---|
| 복구 절차 통합 | **적용(복제 아님)** — `내가_보는_것/운영_점검표.md` §6 끝에 「장애 뒤 복구 — 어디서 시작하나」 표 4행: **시작 조건**(화면 점·배너·카톡) → **누가**(쓰기 권한자 / **계정 주인만**: Secrets·Enable) → **절차가 있는 곳**(README §2 · 설명서 ⑧ `guide.html#auto` · 03 §3 · `#manual`) → **됐는지 확인**(실행 success · 화면 점 초록 · 알림 테스트 카톡). 절차 본문은 설명서 ⑧이 유일한 최신본 |
| 파이프라인 JSON 문자열 출력 규칙 | **적용** — `CLAUDE.md` §3 「★ 화면 문자열 출력 규약」: 문자열 필드는 `textContent`류 · `innerHTML` 엔 숫자·상수·이스케이프된 값만 · 의도된 HTML 조립은 기존 살균 경로(`sanitizeBackup` 형식 검사) 뒤에만 · 신뢰 경계 「저장소 산출물도 데이터」 · **기존 6곳 일괄 치환 금지**(날짜·상수 · SECURITY §2). 화면 코드 무변경 |

## 3. 외부 액션 SHA 고정 (SECURITY §3)
대상 = `uses:` 23줄 중 `verify.yml` 3줄 제외 **20줄 · 워크플로 7개**. 전부 GitHub 공식 `actions/*` · 외부 저장소 액션 0.
**동등성 확인 방법**: 공식 저장소의 태그가 지금 가리키는 커밋을 `git ls-remote --tags https://github.com/actions/<repo>` 로 읽고(가벼운 태그 — `^{}` 없음 · 곧 커밋), `gh api repos/actions/<repo>/commits/<sha>` 로 커밋 객체임을 확인했다. **버전 업그레이드 없음** — 태그가 오늘 가리키는 커밋 = 어제까지 `@vN` 이 받아오던 것.
| 액션 | 쓰던 태그 | 고정 SHA | 같은 커밋의 정식 태그 | 커밋 날짜 |
|---|---|---|---|---|
| actions/checkout | v7 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | v7.0.1 | 2026-07-17 |
| actions/checkout (price.yml) | v4 | `11d5960a326750d5838078e36cf38b85af677262` | v4.4.0 | 2026-07-16 |
| actions/setup-python | v7 | `5fda3b95a4ea91299a34e894583c3862153e4b97` | v7.0.0 | 2026-07-20 |
| actions/setup-python (price.yml) | v5 | `a26af69be951a213d495a4c3e4e4022e16d87065` | v5.6.0 | 2025-04-24 |
| actions/github-script | v7 | `f28e40c7f34bde8b3046d885e986cb6290c5673b` | v7.1.0 | 2025-06-06 |
| actions/configure-pages | v6 | `45bfe0192ca1faeb007ade9deae92b16b8254a0d` | v6.0.0 | 2026-03-24 |
| actions/upload-pages-artifact | v5 | `fc324d3547104276b827a68afc52ff2a11cc49c9` | v5.0.0 | 2026-04-08 |
| actions/deploy-pages | v5 | `368f82528645a54fb793d4d04e342629a3f51346` | v5.0.1 | 2026-09-01 |
적용 파일: daily-signal(3 · github-script 2곳) · monthly-stats(2) · notify-test(2) · pages(4) · price(2) · source-probe(2) · watchdog(3). 각 줄 끝 주석 `# vN = vN.x.y (2026-09-06 SHA 고정 · 이 장부)`.
권한 확대·새 secrets·새 외부 서비스·`pull_request` 트리거 추가 없음. Dependabot(`.github/dependabot.yml`)은 새 자동화라 도입하지 않았다(선택지로만).

**갱신 절차(기록)**: ① 공식 저장소 releases 로 새 버전 확인 → ② `git ls-remote --tags https://github.com/actions/<repo> refs/tags/vN.x.y` 로 커밋 SHA(주석 태그면 `^{}` 줄) → ③ `gh api repos/actions/<repo>/commits/<sha>` 로 커밋 객체 확인 → ④ `uses:` SHA 와 주석 태그를 같이 바꾸고 이 표 갱신 → ⑤ `python -m unittest audit.test_repro6 audit.test_pages_concurrency audit.test_watchdog_chain4 audit.test_screen8` + `verify_all.py` → ⑥ push 뒤 Pages·검증 run success 확인.

**`verify.yml` 제안(수정 안 함 · 돈전략 검사 편입 판단과 같은 파일)**: `actions/checkout@v4` → `11d5960a326750d5838078e36cf38b85af677262 # v4 = v4.4.0` · `actions/setup-python@v5` → `a26af69be951a213d495a4c3e4e4022e16d87065 # v5 = v5.6.0` · `actions/github-script@v7` → `f28e40c7f34bde8b3046d885e986cb6290c5673b # v7 = v7.1.0`.

## 4. 회귀·통합
- `python -m unittest audit.test_ops_recovery3 audit.test_repro6 audit.test_pages_concurrency audit.test_watchdog_chain4 audit.test_screen8` → **64 OK** · `verify_all.py` 전체 **실패 0**(g_deploy 관문 — 스텝 id·`REMOTE_ASOF`·reset 순서 유지).
- 변조 검사(§1) 3/5 FAIL → 복원 5/5 OK. 라이브 확인은 §5(push 뒤 기입).

## 5. 통합 기록
- 커밋 **69e31ca** → main(기준 ce17a6d 에서 main 이동 0 · 충돌 없음). 검증 run 34010827889 **success** · Pages run 34010827965 **success**(deploy 잡 success — 고정 SHA 의 checkout·configure-pages·upload-pages-artifact·deploy-pages 로 실제 배포).
- 라이브: 사이트 루트 200 · CSP meta 존재 · `data/signal.json` as_of 2026-09-04(변경 없음 — 이 묶음은 데이터를 안 건드린다).
- 고정된 나머지 워크플로(daily-signal·watchdog·price·monthly-stats)는 예약 실행에서 확인된다 — 월요일 09:31/09:52 KST 관찰이 price·watchdog 을, 화요일 새벽 슬롯이 daily-signal 을 처음 돈다(**실제 관찰 대기**). notify-test·source-probe 는 수동 전용(실행 안 함 — 카톡·네트워크 탐침).
