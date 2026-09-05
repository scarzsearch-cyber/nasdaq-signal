# deploy/ — 라이브 파이프라인 (현행 안내 · 2026-09-05 재작성)

> **건드리지 말 것.** 이 폴더는 GitHub Actions 가 매일 돌리는 운영 코드다. 전략 판정값(−16/−16 ·
> 룩백 252 · 방어 40/40/20)은 `data/freeze.json` 에 동결돼 있고 `verify_all.py` I11 이 매 push 검사한다.
> 결함(버그·미래참조·조용한 실패)의 수정은 허용된다 — 절차는 `CLAUDE.md` §2(지문 전후 대조 · 셀프테스트 재현).
> 옛 v18 시절 설치 안내(stooq · 22:30 UTC 단일 슬롯 · 두 전략 선택 · build_stats 수동 커밋)는
> `docs/history/deploy_README_v18_원본.md` 로 옮겼다 — **현행과 정면으로 다르므로 그쪽을 따라 하지 마라.**

## 한 줄 요약

미국 종가가 굳는 순간(05:00 여름 · 06:00 겨울 KST) 5분 안에 `data/signal.json` 이 갱신·배포되고,
전환일엔 카톡이 온다. 한국장 중엔 5분마다 시세 배지가 갱신된다. 사람이 파이썬을 돌릴 일은 없다.

## 워크플로 6개 (`.github/workflows/`)

| 워크플로 | 언제 | 무엇 | 커밋 |
|---|---|---|---|
| `daily-signal.yml` 「일일 신호 갱신」 | 평일 **8슬롯**(마감 전 04:35·04:45·05:35·05:45 + 예비 05:17·06:17·07:47·09:17 KST) | `wait_close.py`(마감 대기 → `update_signal.py`) → `signal_alert.py` → `kakao_keepalive.py` → `nav_collect.py` → `oos_log.py` | `data/qqq.csv` `signal.json` `signal_alert_state.json` `nav_history.csv` `oos_log.csv` |
| `price.yml` 「price」 | 개장 전 슬롯에서 떠서 09:00:20 부터 **5분 경계마다** 12:26 인계 | `price_poll.py`(→ `price_now.py` · `kr_sources.py` 예비 체인) | **main 아님** — `price-data` 브랜치 항상 커밋 1개 (v176) |
| `pages.yml` 「GitHub Pages 배포」 | push · 위 두 워크플로 완료(`workflow_run`) · 월간 성과 완료 · 폴러의 `gh workflow run` | 세 화면 + `data/*` 복사, 시세는 price-data 브랜치에서 (못 읽으면 **싣지 않는다**) | 없음 |
| `watchdog.yml` 「자동 파수꾼」 | 평일 08:40 KST · 월요일 주간 | `watchdog.py` stale·rebalance·switchday·near·channel·stats·price / 월요일 check·heartbeat + `kr_holidays.py --emit` | `data/ops_check.json` `kr_holidays.json` (월요일) |
| `monthly-stats.yml` 「월간 성과 스냅샷 갱신」 | 매월 1일 16:17 KST | `refresh_hist.py`(원자료 연장) → `build_stats.py` → `emit_dd_distribution.py` → `verify_all` | `strategy_stats.json` `signal.json`(stats 사본) `dd_percentile.json` `data/hist/*` 원자료 |
| `verify.yml` 「검증」 | push · 평일 01:00 UTC | `verify_all.py --fast` + 전체 · 예약엔 `audit/audit_full.py` | 없음 — 실패는 **이슈(메일)** 로만, 배포는 멈추지 않는다(fail-open, `CLAUDE.md` §0) |

보조: `source-probe.yml`(수동 · 출처 생존 표) · `notify-test.yml`(수동 · 알림 채널 시험).

## 실패 규약 (전부 코드에 박혀 있고 `verify_all` 이 검사한다)

- **판정 경로는 fail-open, 장부는 fail-closed.** 대조 출처가 죽어도 진짜 폭락일 신호는 막지 않는다(v137).
  NAV·OOS 장부는 부분 기록 대신 실패하고 다음 슬롯이 재시도한다(v203).
- **push 경합은 rebase 하지 않는다**(v203) — 다음 슬롯이 최신 HEAD 에서 처음부터 재계산한다.
  [v206] 예약 실행은 큐에 들어갈 때의 커밋을 체크아웃하므로, 체크아웃 뒤 **최신 main 으로 맞추고**
  push 직전 원격이 이미 같은 종가를 반영했으면 중복 커밋을 조용히 버린다(정상 종료).
- **NAV 장부는 장 밖 슬롯에서만 적립한다**(v206) — 한국장 개장 중(09:00~15:30)에는 적립하지 않는다.
  그래서 `nav_history.csv` 의 `close` 는 직전 거래일의 공식 종가·NAV 다.
- 시세를 못 가져오면 **옛 값을 싣지 않는다** — 배지가 사라지는 것이 실패 표시다(v145·v176).
- 알림: 전환일 카톡(`signal_alert.py`) → 실패 시 이슈 · 08:40 재알림·근접 알림(`watchdog.py`) ·
  월 1회 생존 알림(**침묵이 고장 신호**인 유일한 알림, v177).

## 스크립트 지도

| 파일 | 역할 |
|---|---|
| `wait_close.py` | 마감 전 슬롯에서 떠서 20초 간격으로 종가가 굳는 순간을 잡는다 · `--selftest` 9경로 |
| `update_signal.py` | QQQ 종가(야후 2경로 → 네이버 → 캐시) → 252일 낙폭 → `signal.json`. B 가 판정, A 는 구버전 호환 미러 |
| `signal_alert.py` · `notify.py` | 전환일 카톡/텔레그램/디스코드 · 상태 파일로 중복 발송 방지 |
| `kakao_keepalive.py` · `kakao_setup.py` | 카카오 refresh 토큰 연명(새 토큰을 GH_PAT 로 secret 에 저장) · 최초 발급 |
| `nav_collect.py` | 국내 ETF 종가·NAV·괴리율 한 줄 적립(네이버 ETF 목록) · `--selftest` |
| `oos_log.py` | 동결(2026-08-27) 이후 하루 한 줄 — 순수 OOS 장부 |
| `price_now.py` · `price_poll.py` · `kr_sources.py` | 장중 시세 스냅샷 · 5분 폴러 · 예비 출처 6종 |
| `watchdog.py` | 파수꾼 9모드 · `--selftest` 61경우 |
| `build_stats.py` · `refresh_hist.py` | 성과지표 4시나리오 · 원자료 append-only 연장 |
| `stamp_rev.py` · `data_check.py` · `kr_holidays.py` | 화면 「전략 반영 vNN」 도장 · 원자료 무결성 · 휴장일 표 |

## 확인 명령

```bash
gh run list --workflow=daily-signal.yml --limit 8     # 새벽 슬롯이 돌았나 (둘째 슬롯은 23초 만에 「이미 최신」이 정상)
python verify_all.py                                   # 전체 모드 — 셀프테스트(I14)까지 돈다
python deploy/wait_close.py --selftest
python deploy/nav_collect.py --selftest
python deploy/watchdog.py --selftest
```

로컬에서 `update_signal.py` 를 수동 실행하면 야후에서 전체를 다시 받아 `data/signal.json` 을 다시 쓴다 —
장부 파일(`oos_log.csv` · `nav_history.csv`)은 건드리지 않는다.
