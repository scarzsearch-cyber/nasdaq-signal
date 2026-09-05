# pages.yml 취소 연쇄 수정 (2026-09-06)

> 기준 21c0a53 · 별도 작업트리 `review/pages-concurrency-8`. 발단: `audit/SCREEN_MATRIX2_2026-09-06.md` ②의 발견(09-04 :25/:55 스냅샷 3건이 다음 스냅샷까지
> 341~349s 늦게 반영). 전략·판정·장부·화면 무변경 · 워크플로 한 파일(`pages.yml`)의 잡 헤더만.

## 경로 확인 (실측 · 09-04)
1. `price.yml` 예비 슬롯(매시 :20·:50)은 `concurrency: group: price · cancel-in-progress: false` 그룹에서 **대기**하다가 다음 예약이 오면 **취소**된다(하루 12건).
2. 취소가 `completed` 이므로 `pages.yml` 의 `workflow_run: workflows: [..., "price", ...] · types: [completed]` 가 발화 → Pages 새 실행이 생긴다(예: 02:55:32Z).
3. 종전 `concurrency` 는 **워크플로 수준**이라 그 실행이 생기는 순간 그룹에 들어가 **진행 중인 5분 dispatch 배포(02:55:24Z)를 취소**(02:55:35Z)했다.
4. 그 실행 자신은 `deploy` 잡 skipped(0 스텝)로 끝난다 — 배포된 것이 없다. 결과: 그 스냅샷은 다음 스냅샷(5분 뒤)까지 사이트에 안 올라갔다.

## 가장 작은 수정 (`pages.yml` deploy 잡)
```yaml
    if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion != 'cancelled'
    concurrency:
      group: pages
      cancel-in-progress: true
```
- 워크플로 수준 `concurrency` 블록을 없애고 **잡 수준**으로 내렸다 → `if` 로 건너뛴 잡은 그룹에 들어가지 않아 진행 중 배포를 못 죽인다.
- 건너뛰는 것은 **취소된** 선행 실행뿐 — 취소된 실행은 아무것도 푸시하지 않았다. **실패(failure)한 선행 실행은 v203 규약대로 계속 재배포**한다
  (`g_deploy` 의 「`workflow_run.conclusion == 'success'` 금지」 검사와 충돌 없음 · verify_all 통과).
- 트리거·복사 목록·배포 스텝 무변경.

## 회귀 검사 `audit/test_pages_concurrency.py`
- 정적 계약: 워크플로 수준 `concurrency:` 없음 · deploy 잡의 `if`(cancelled 건너뜀)·잡 수준 `concurrency` · `== 'success'` 없음 · 트리거 3종 그대로.
  **옛 pages.yml(21c0a53)에서 2실패 → 수정본 OK.**
- 이벤트 순서 모형 5경우(정상 완료 · 선행 실행 취소 · 연속 갱신 · 수동 dispatch · 실패한 선행 실행): 옛 정책은 「선행 취소」에서 배포 0·취소 1·skipped 1(09-04 실측 재현),
  새 정책은 배포 1(v1)·취소 0·skipped 1. 연속 갱신은 두 정책 모두 마지막(v2)만 배포.
- `verify.yml` 회귀 목록 등재. ⚠ 첫 push(8dec74f)·둘째(58a26cb)는 **내 검사 파일의 오타**(줄 앵커·heredoc 줄바꿈)로 CI 검증이 두 번 빨갰다 — 73488a2 에서 정정.
  기존 열린 이슈 #1(verify-fail)에 그 두 번의 실패 댓글이 달렸다(수정본 이후 초록).

## dispatch 실측 (수정본 73488a2 · 2026-09-06 03:25~03:30 KST · 일요일이라 데이터 정적 — `price-data` 09-04 15:55 · main 신호 09-04)

| 경우 | 절차 | 결과 |
|---|---|---|
| 정상 완료 · 수동 dispatch | `gh workflow run pages.yml` | run 33984030723 success · 생성→완료 18s · 사이트 `price.json` as_of 09-04 15:55 = 브랜치 · `signal.json` as_of 09-04 = main |
| 연속 갱신 | dispatch 두 번(4s 간격) | 앞 run cancelled(잡 수준 cancel-in-progress 동작) · 뒤 run success 21s · 사이트 = 최신(내용 동일) |
| 선행 실행 **취소** (문제의 경로) | dispatch A → 2s 뒤 `price.yml` once 를 dispatch 하고 큐 단계에서 즉시 `gh run cancel` | price run **cancelled**(18:29:03→06Z) → workflow_run pages run 33984206076 **skipped**(18:29:08→09Z · 0 스텝) → **A 33984199949 success**(18:29:02→24Z · 취소되지 않음). 종전(09-04)엔 이 자리에서 A 가 취소됐다. |
| (부수) 선행 실행 **성공** | 첫 시도에서 price once 가 11s 만에 성공으로 끝남 | workflow_run(success) run 이 진행 중 dispatch A 를 취소하고 자신이 배포(success) — **설계대로**(더 새 실행이 이긴다 · 실패/성공한 선행 실행은 계속 재배포) |

- 「최종 배포가 최신 유효 데이터를 담는가」: 일요일이라 브랜치·main 이 정적이어서 **동일성**으로만 확인했다(사이트 = 브랜치 = main). 장중 갱신 값의 순서 보장은
  모형(연속 갱신 → 마지막 버전)과 09-03·09-04 로그(발행된 157건 전부 dispatch 와 짝) 위에 있다 — 월요일 라이브 표본(관찰 대기)에서 다시 본다.
- 부작용 없음: cancelled price run 은 큐/설정 단계에서 끝나 발행·알림 없음(price.yml 에는 알림 스텝이 없다) · 장부·원자료 무접촉.

## 남은 한계
- 잡 수준 concurrency 에서 「건너뛴 잡은 그룹에 안 들어간다」는 문서가 아니라 **실측 1회**(위 T2)로 확인한 동작이다 — 재현되면 회귀로 남지만 GitHub 쪽 변경엔 무방비.
- 정상적인 `workflow_run(success)` 는 여전히 진행 중 dispatch 를 취소한다(설계 — 더 새 데이터). 취소된 쪽 스냅샷은 그 새 실행이 같은 브랜치를 다시 읽으므로 유실이 아니다.
- 이틀 로그 + 일요일 실측이다. 장중 분포는 월요일 표본 뒤 `SCREEN_MATRIX2` ②에 병기한다.

## G. 통합
- 커밋 8dec74f(수정) → 58a26cb → **73488a2**(검사 정정 · CI 검증 success · Pages success). dispatch 실측은 73488a2 기준.
- b303eb8(장부·CLAUDE): CI 검증이 **무관한 회귀 `test_ops_recovery3.S6` 의 로컬 bare 클론 exit 128** 로 한 번 빨갰고 재실행(attempt 2)은 통과 — 간헐 실패. 원인은 그 검사의 git 헬퍼가 stderr 를 삼켜 안 보였다 → 다음 커밋에서 stderr 를 예외에 붙였다(재시도 없음).
