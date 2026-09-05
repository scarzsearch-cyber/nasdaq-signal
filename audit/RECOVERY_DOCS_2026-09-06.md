# 운영 장애 후 복구 안내의 실행 가능성 (2026-09-06)

> 기준 cc73951. 기존 장애 시험(OPS_RECOVERY v222 · WATCHDOG_CHAIN · SURVIVAL)을 다시 돌리지 않고, **운영 문서에 적힌 복구 순서**가 현재 코드·워크플로·권한과 맞는지
> 대조했다. 실행 검증은 격리(읽기 전용 명령·격리 클론)에서만 — 실제 토큰 회전·알림 발송·예약 비활성화·운영 데이터 조작 없음.

## 1. 대조 표 (문서 → 현행)
| 문서 | 적힌 절차·명령 | 대조 | 판정 · 조치 |
|---|---|---|---|
| README §2 | 신호가 밀리면 「배너 링크 → Actions → 일일 신호 갱신 → Run workflow」 | `daily-signal.yml` `workflow_dispatch` 있음 · 마감 뒤 실행은 `wait_close` 「이미 마감」 즉시 경로 → `update_signal` · 화면 배너 링크 URL = 그 워크플로 | ✅ |
| README §2 | 수동 명령 3종(`build_stats.py` · `axis_isa.py --emit` · `kr_holidays.py --emit`) | 격리 클론에서 전부 실행됨(REPRO §2) | ✅ |
| README §3 · deploy/README 확인 명령 | `verify_all.py`(전체·--fast) · `wait_close/nav_collect/watchdog --selftest` · `gh run list --workflow=daily-signal.yml` | 전부 실행 OK(격리 클론 · 로컬) | ✅ |
| deploy/README 스크립트 지도 | `watchdog.py --selftest 61경우` | 실제 **67경우**(v225) | ❌ → **수정**(67 · csp_inject 도 지도에 등재) |
| deploy/README | 워크플로 6개 + 보조 2 | 8종 전부 `active`(`gh workflow list`) · 이름 일치 | ✅ |
| 03 §3 | 카카오 secrets 이름 4종 · 최초 발급 `deploy/kakao_setup.py` | 워크플로 8종의 `secrets.*` 이름과 일치 · 도우미 절차(REST 키 → Redirect URI → Client Secret → code → refresh) = 코드(`auth_url`·`token_body`) | ✅ |
| 03 §3 | 「GH_PAT 로 secret 자동 교체」 | `gh secret set` 은 PAT 에 secrets 쓰기 권한이 있어야 한다 — **필수 조건 누락** | ❌ → **수정**(classic `repo` / fine-grained Secrets: Read and write 명시) |
| 설명서 ⑧ | 「알림 채널 이상」 카톡이 오면 **재설정 요청** | 누구에게·무엇을 하는지·성공 확인법 없음 | ❌ → **수정**: 도우미 재실행 → Secrets 재등록 → Actions 「알림 테스트」 Run workflow 로 확인 · **계정 주인만** |
| 설명서 ⑧ | 「아예 안 도는 경우는 따로 봅니다」 | 복구 행동 없음(60일 규칙·Actions 비활성) | ❌ → **수정**: 월 1회 생존 카톡 부재 = 통째 정지 → Actions → Enable workflow → 「일일 신호 갱신」 Run workflow · **계정 주인만** |
| 설명서 ⑧ `#manual` | 30초 수동 판정(52주 고점 × 0.84) | v141 실측(6,700일 불일치 0) — 기존 | 제외 |
| 운영_점검표 §3 | `python 내가_보는_것/점검.py` | `--json` 스모크 실행 OK(키 as_of·aum·exec·level·todo…) | ✅ |
| notes `#opsRecovery` | v222 서술 | 설명문 · 절차 아님 | 제외 |

## 2. 계정 소유자만 할 수 있는 단계 (문서에 명시 · 자동화 불가)
- GitHub → Settings → Secrets 등록·갱신(KAKAO_REST_API_KEY · KAKAO_REFRESH_TOKEN · KAKAO_CLIENT_SECRET · GH_PAT) · GH_PAT 발급(권한 위 표).
- Actions → 워크플로 Enable/Disable · Run workflow(쓰기 권한자).
- 카카오 개발자 콘솔(동의항목 「카카오톡 메시지 전송」 · Redirect URI) — `kakao_setup.py` 도 이 값을 입력받는다.
- Pages 설정(Source: GitHub Actions) · 계정 복구 코드(v195 제안 그대로).

## 3. 격리 실행으로 확인한 것 / 하지 않은 것
- 했다: 셀프테스트 3종 · verify_all · 수동 명령 3종(클론) · `점검.py --json` · `gh workflow list`.
- 하지 않았다: 실제 `Run workflow`(배포·알림 유발) · `kakao_setup.py` 실발급 · `gh secret set` · Enable/Disable.

## 4. 남은 결정(제안)
- 복구 절차를 `내가_보는_것/운영_점검표.md` 한 절로 모을지(현재는 설명서 ⑧ + 03 + deploy/README 에 나뉨) — 소유자 판단(v140 「화면이 1순위」 원칙과의 균형).
