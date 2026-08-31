# 03 — 시스템 파라미터 · 데이터 · 자동화

> 현행 파일. 기계용 원본은 `data/freeze.json` — **이 문서와 다르면 freeze.json 이 맞다.**
> 작성 2026-08-29 (v65 통폐합).

---

## 1. 동결 파라미터 (freeze.json 사본)

| 파라미터 | 값 |
|---|---|
| 신호 | QQQ 미국 종가, 252거래일 rolling 최고가 대비 낙폭 |
| 진입 / 복귀 | **−0.16 / −0.16** · 전량 전환 |
| 공격 | TIGER 미국나스닥100레버리지(합성) 418660 |
| 방어 | 458730 40% / 305080 40% / 411060 20% · 월 1회 재조정 |
| 체결 | `pos = w.shift(1)` — 전일 미국 종가 → 다음 한국 거래일 |
| 비용 (매매) | 편도 0.1% + 슬리피지 0.1% — 전환 시에만 |
| 비용 (보유) | 2배 합성 드래그 **연 3.30%** — QLD vs 2×QQQ 실측 역산(`hist_data.c_daily`)이 매일 차감. **총보수(418660 연 0.25%)·스왑 비용이 이 안에 포함** — 매매비용과 별개 층 (v88 부록2) |
| 실행 시간대 | 한국장 **09:05~15:20** (LP 호가 의무 시간대) |
| 동결일 | `frozen_at` 2026-08-27 (KST) / `oos_start` 2026-08-28 (미국 종가일) |
| 지문 | `16201b974d4e383b` |

## 2. 데이터

| 자료 | 출처·구성 |
|---|---|
| 일일 신호 | `data/qqq.csv` — **수정 종가(배당 조정)**, Yahoo query1 → query2 미러 → 네이버 증권 → 캐시 예비 사슬 (`deploy/update_signal.py`). v71: 비수정→수정 통일 — 백테스트와 같은 기준, 신호 불일치 0일/6,908일 검증 (비수정은 11일 갈렸다, v67 B-1) |
| 54년 체인 | 나스닥종합(1972-)→NDX→QQQ 를 **일간수익률로 접합** — 같은 자산 아님, 대리 시계열 |
| 방어 재료 | 배당 실측 체인 · 국채 **선물형 모형**(현물TR − 미 단기금리 − 보수 0.29%) · 금 현물 |
| 환율 | USD/KRW (FRED DEXKOUS) — 원화 시나리오는 환노출 **2배** 구조: `2×((1+지수)(1+환율)−1)` |
| 실물 대조 | TIGER 3종 시가/종가 + iNAV (`deploy/nav_collect.py` 가 매일 적립) |
| 한국 달력 | KOSPI 실거래일 + `data/kr_holidays.json` (제헌절 2026 복원 반영) |

## 3. 자동화 파이프라인 (GitHub Actions)

```
daily-signal.yml   [v75] 대기 루프 체제 — 트리거 4개(05:17/06:17/07:47/09:17 KST) 중
                   **하나만 떠도** wait_close.py 가 종가 반영까지 240초 간격 재시도(최대 170분).
                   GitHub 이 슬롯을 건너뛰어도(실측 8/26·8/27·8/29) 커버. 이미 최신이면 무커밋 종료.
  ① wait_close.py → update_signal.py   qqq.csv 갱신 → signal.json (신호·낙폭·내장 stats 사본)
  ② nav_collect.py     실물 NAV·괴리율 적립
  ③ oos_log.py         동결 이후 하루 한 줄 append-only (판단하지 않음)
                       + T4 그림자 3열 (t4_votes/t4_rv/t4_w — 평가 전용, v68·v69. 채택안 아님)
                       + [v80] 날짜 가드 (qqq.csv 미갱신 시 전일 값 오기록 대신 빈 칸)
                       판정 규약: docs/history/전략_v80 §6·§7 부속서가 v69 에 우선
                       (사건 단위 M1·M2 기전 관문 · 한도 −29% 고정 · 혼합 0.25B 평가 전용 병기)
pages.yml            push 시 배포 + stamp_rev.py 가 화면 개정일·커밋 주입
notify.py            [v73/v77] 실패·전환 알림 — 카카오톡 "나에게 보내기"(권장:
                     KAKAO_REST_API_KEY+KAKAO_REFRESH_TOKEN, 최초 발급은 deploy/kakao_setup.py)
                     또는 Discord/Telegram. 미설정이면 조용히 생략
kakao_keepalive.py   [v77] 카카오 refresh 토큰(2개월 시한부)을 매일 갱신해 연명.
                     교체 신호 시 GH_PAT 로 secret 자동 교체, 없으면 카톡 만료 예고
data_check.py        [v73] 월간 연장의 검증 게이트 — 결측·중복·역순·0이하·±30%·공백·열누락 시
                     해당 파일 갱신 거부(기존 유지) + 종료코드 1 (build_stats 미실행 = downstream 보호)
monthly-stats.yml    매월 1일 07:17 UTC (미·한 장 모두 휴장 시각) — refresh_hist.py 로
                     원자료 연장(append-only·수정주가 비율 이음·장중 가드) 후
                     build_stats.py 재계산, verify_all 통과 시에만 커밋 (v72)
verify.yml           push 마다 verify_all.py --fast — 실패하면 GitHub 이슈 자동 생성
watchdog.yml         [v140] 자동 파수꾼 — **「실패」가 아니라 「아예 안 돈 것」을 잡는다**
                     (기존 알림은 전부 if: failure() 라 워크플로가 스킵되면 침묵했다)
  ① watchdog.py stale    평일 08:40 KST — signal.json as_of 가 3영업일 밀리면 카톡
                         (3영업일마다 1회만 · 한국장 개장 20분 전)
  ② watchdog.py channel  평일 — 카카오 refresh 교환·Telegram getMe 로 **무발송** 생존 확인.
                         죽었으면 살아 있는 다른 채널 + GitHub 이슈(메일)로 알린다
  ③ watchdog.py check    월요일 09:10 KST — 내가_보는_것/점검.py --json →
                         data/ops_check.json (전제 Level·느린 변수 4종·4다리 AUM·비용 진행률).
                         화면이 읽는다(drawOpsCheck). 알림은 **상태가 나빠졌을 때만**
                         (Level 상승·새 AUM 경보) — 밴드·규약은 무변경, 주기만 분기→주
```

- 예약 실행은 부하 시 **통째로 건너뛸 수 있다** (2026-08-26 실제 발생) — 그래서 예비 슬롯 2개
  + 화면 신선도 배너(미국장 기준 경과 거래일로 계산)가 있다.
- 화면 3줄 표기: `종가 기준일·자동갱신 시각` / `전략 반영(화면 마지막 커밋)` / `규칙 동결·경과 N영업일`.

## 4. 불변식 I1~I12 (`verify_all.py`, 전체 4초)

| | 무엇을 막는가 |
|---|---|
| I1 | 엔진 동치 — 시뮬레이터마다 다른 답 |
| I2 | 미래 미참조 — 시점별 재계산 일치 |
| I3 | 체결 규약 — 미래를 당기면 좋아져야 정상 |
| I4 | 모형 vs 실물 ETF 드리프트 ±1.5%p |
| I5 | 채택 결정(B>A·40/40/20·미국종가) + **화면이 결정·지표를 그대로 그리는가** |
| I6 | signal.json 재계산 일치 + 내장 stats 사본 정합 + 신선도 |
| I7 | 공표 수치가 현재 코드와 일치 + 벤치마크 정합 |
| I8 | 공용 모형 사용처 목록 (수정 시 재실행 안내) |
| I9 | **폐기 수치 12종**이 현행 문서(`retired_numbers.json`의 current_docs)에 없는가 + 보관 문서 정정 배너 |
| I10 | 전제 감시 — 나스닥 고유 성질(2배 MDD ≤−90% · 장기 상승 · 전략>보유) 유지 |
| I11 | **규칙 동결** — 코드·화면이 freeze.json 과 다르면 실패 |
| I12 | T4 그림자 열 무결성 — votes 0~4 · rv>0 · w∈[0,1] · votes<2 ⟺ w=0 (v82) |

## 5. 파일 지도 (핵심층만)

```
01~04_*.md            ← 현행 문서 (이 4개 + 내가_보는_것/전략_요약.md 목차가 읽기 층)
data/freeze.json      ← 동결 규칙 (기계용 truth)
data/signal.json      ← 오늘의 신호 (매일 덮어씀)
data/oos_log.csv      ← 전향적 OOS 장부 (append-only)
signal.html           ← 화면 (단일 파일)
deploy/               ← 라이브 파이프라인 5개 — 건드리지 말 것
verify_all.py         ← 불변식 I1~I12
reentry_lib.py 등     ← 엔진·데이터 체인 (FILES.md 상세)
docs/history/         ← 전략_v18~v83 보관 (56개, 온디맨드 참조. v80 §6·§7 = T4 판정 부속서)
docs/raw/             ← 각 버전 문서의 원본 출력
research/             ← 기각 축 재현 스크립트 (04 문서와 1:1)
```

## 6. 운영 사고 이력 (재발 방지 장치 포함)

| 사고 | 원인 | 장치 |
|---|---|---|
| 종가 미갱신 (08-26) | GitHub 예약 실행 스킵 | 예비 슬롯 2개 + 신선도 배너 |
| 종가 6시간 지각 (08-27→28) | 예약 3슬롯 전부 스킵/지연 — 15:04 KST 에야 반영 | [v66] 슬롯 3→7개, 혼잡한 :30 분 회피(:17/:47) |
| 장중가가 종가로 둔갑할 뻔 | 실행이 미국장 개장 뒤로 밀리면 Yahoo 가 진행 중 봉을 줌 | [v66] update_signal.py 장중 가드 (regularMarketTime < 정규장 마감이면 마지막 봉 제외) |
| 화면이 옛 수치 표시 | signal.json 내장 stats 가 옛 판 | I6 사본 대조 + build_stats 가 사본 동시 갱신 |
| 문서 결정 ≠ 화면 | v43 결정을 코드에 반영 안 함 | I5 가 화면을 직접 읽어 대조 |
| 폐기 수치 잔존 | 정정 후 옛 문서 방치 | I9 + retired_numbers.json |
