# 코드리뷰 전수 순회 — 프롬프트 + 진행 장부 (2026-09-05 · 소유자 지시)

> **이 파일은 「지시서」이자 「진행 장부」다.** 어느 세션(Claude · Codex · 그 밖의 AI)이 이어받든
> **이 파일만 읽으면 같은 규칙으로 다음 배치를 이어갈 수 있게** 쓴다. 다른 요약을 만들지 말고 이 파일을 갱신하라.
>
> **소유자 지시 원문 요지 (2026-09-05)**: 「폴더를 코드리뷰 형태로 다시 전수조사 — `/code-review max` 수준으로.
> 여러 세션이 겹쳐서 서로 건드리는 게 불편하니 **혼자서 하나씩 순차로**. 지난번처럼 **6개씩** 자르지 말고
> **최소 10~12개 이상**을 한 배치로. 토큰이 부족해 막힐 테니 **프롬프트 형태로** 만들어 Codex 에게도 이어 건넬 수 있게.」

---

## 0. 이어받는 세션이 맨 처음 할 일 (순서대로)

1. `CLAUDE.md` 를 **전문** 읽는다 — 특히 §-1(오류 비용 비대칭 · 절대 멈춤 5개 · 반증 방아쇠) · §2(수정 금지 vs 결함 수정 허용의 경계) · §3(작업 규약 · 커밋 규칙). `AGENTS.md` 는 그 파일로 가는 한 줄 진입점이다.
2. `git pull` 뒤 `python verify_all.py`(전체 모드) — **실패 0** 이어야 시작한다. 실패면 그것부터 고친다(그 자체가 발견이다).
3. 이 파일 §7 진행표에서 **첫 번째 ⏳ 배치**를 찾는다. 그 배치의 파일 목록을 §6 에서 본다. 배치 안에 ✅ 표시된 파일은 건너뛴다(중단됐던 자리).
4. 직전 감사 두 건을 **재사용하되 정답으로 믿지 않는다**: `research/CODE_REVIEW_2026-09-05.md`(Codex v204·v205 · research 129+8) · `audit/AUDIT_LEDGER_2026-09-05.md`(Claude v206 · 전 층). 거기 「수정됨」이라 적힌 것도 **현재 파일에서 다시 확인**한다.

## 1. 한 배치를 끝내는 절차 (모든 배치 공통 · 생략 금지)

| 단계 | 무엇 | 증거 |
|---|---|---|
| ① 판독 | 배치의 **모든 파일을 줄 단위로 전문** 읽는다(grep 발췌만으로 끝내지 않는다). `signal.html` 처럼 긴 파일은 나눠 읽되 **빠진 구간이 없게** 줄 범위를 장부에 적는다 | 읽은 줄 범위 |
| ② 실행 | 실행 가능한 것은 실행한다: `--selftest` 가 있으면 그것, 없으면 본체(네트워크·파일 쓰기가 있는 deploy 는 **드라이런·구문검사**만). 출력의 검산(「공표 재현 OK」 등)을 눈으로 확인 | 명령 · 종료코드 · 핵심 출력 한 줄 |
| ③ 교차 | 그 파일이 **읽는 것/쓰는 것/부르는 것/불리는 곳**을 grep 으로 확인한다(열 이름 · 날짜 형식 · 단위 · 인코딩 · 키 이름). 계약 한쪽만 바뀐 곳이 진짜 결함이다 | grep 결과 요지 |
| ④ 반례 | 결함이라 판단한 것은 **반례를 실제로 실행**해 재현한다(입력을 훼손해 관문이 FAIL 하는가 · 지연을 한 칸 밀면 값이 어떻게 움직이는가 · 빈/짧은/휴장 입력). 재현 못 하면 「판단 불가」로 적는다 | 재현 명령과 결과 |
| ⑤ 수정 | §3 원칙 안에서 고친다. **고치기 전 출력 지문**(공표값·검산값)을 뜨고 고친 뒤 대조. `SHARED_SEAL`·`FREEZE_SEAL` 이 걸린 함수면 봉인 갱신 + **FAIL→PASS 재현** | 지문 전후 |
| ⑥ 관문 | `python verify_all.py`(전체) 실패 0 · 화면 파일을 건드렸으면 412px 가로 스크롤 0·콘솔 오류 0 | 결과 줄 |
| ⑦ 기록 | §8 발견 대장에 배치 번호로 등재(형식 §4) · §7 진행표 갱신 · **배치당 커밋 1개** 제목 `review(Bnn): <한 줄>` — 큰따옴표 금지 · `signal.html` 을 바꿨으면 제목에 vNN 과 `notes.html`·`CLAUDE.md` §4 항목 필수(노트 지연 관문) | 커밋 해시 |
| ⑧ push | `git push` 까지가 한 배치다. CI(검증·배포) 초록 확인 | run 결과 |

**중단됐다면**: 파일 단위로 ✅ 를 남기고 §7 에 「B03 진행 중 — 7/14」처럼 적은 뒤 커밋한다. 다음 세션은 거기서 잇는다.

## 2. 파일마다 묻는 것 (체크리스트 · 답이 「해당 없음」이어도 훑는다)

1. **미래참조** — 신호·특징·라벨이 같은 날 또는 뒤 날 값을 쓰는가. `shift(1)` 규약(`pos = w.shift(1)`) · `lag=1` · 워밍업 창이 절단 **전**에 계산되는가.
2. **지연 한 칸의 재림** — 이미 lag 가 걸린 배열에 `[i-1]` 을 또 쓰는가 · 전환 처리가 그날 수익 **앞**에 오는가 · 「축퇴시키면 공표 곡선이 나오는가」 검산이 있는가.
3. **조용한 실패** — `except: pass` · 빈 결과를 성공으로 · `continue-on-error` · 파일이 없을 때 옛 값 사용 · 부분 응답(HTTP 200 절단)을 정상 처리.
4. **하드코딩** — 문턱·비중·룩백·세율·비용·날짜·종목코드가 코드에 박혀 있는데 `data/freeze.json`·문서와 어긋나는가. 앵커 숫자(예: 214,076)가 무엇의 값인지 적혀 있는가.
5. **데이터 계약** — CSV 열 이름·정렬·중복 키·날짜 형식(YYYY-MM-DD)·단위(만원/억/배/%p)·인코딩(네이버 cp949)·시간대(KST/UTC)·거래일(휴장·주말·서머타임). 쓰는 쪽과 읽는 쪽이 같은 계약을 갖는가.
6. **경계** — 빈 배열 · 창보다 짧은 자료 · 첫/마지막 행 · 0 나눗셈 · NaN 전파 · `min_periods`.
7. **세금·비용 회계** — 실현 시점 · 취득원가 갱신 · 연말 정산 순서 · 상계 규칙 · 비용을 어느 매도에 포함하는가.
8. **통계 오용** — 겹치는 창을 독립처럼 세는가 · 둥근 시작일 하나로 판정하는가 · 꼬리 위험에 중앙값을 쓰는가 · 손으로 고른 조합을 분포 없이 채택/기각하는가 · 「A 때문에 B」인데 표에 A 만 바꾼 열이 없는가(§-1 ⑧).
9. **관문 변별력** — 검사가 「실패하면 무엇이 참 · 통과하면 무엇이 참」을 가르는가. 계산만 하고 관문에 안 건 값(verify_volguard G3 의 옛 사고)이 있는가. 새 검사는 **일부러 훼손해 FAIL 이 뜨는지** 봤는가.
10. **문서-코드 불일치** — docstring · 파일 머리 주석 · `CLAUDE.md` §4 · `04_Rejected_Research.md` · `FILES.md` 설명이 지금 코드와 같은가. 「재현 스크립트 없는 표」가 있는가.
11. **출력·환경** — 런타임 메시지의 em-dash(cp949 `UnicodeEncodeError`) · `sys.stdout.reconfigure` · 경로 보정 3줄 · Windows/Linux 차이 · 종료코드(FAIL 인데 0).
12. **비밀·개인정보** — 토큰·키·계좌·실보유 수량이 코드·로그·커밋에 들어가는가(소유자 규정: 보유 수량은 적혀 있어도 되나 **토큰·키는 절대 금지**).

## 3. 수정 원칙 (CLAUDE.md 를 따른다 — 여기서는 요지만)

- **바꾸자의 증거 기준은 그대로 두자보다 훨씬 높다**(§-1). 의심스러우면 기록만 하고 바꾸지 않는다.
- **전략 B 동결값(−16/−16 · 룩백 252 · 방어 40/40/20)·`data/freeze.json`·`oos_log.csv`·`nav_history.csv` 는 결함 수정의 대상이 아니다.** 수익률 개선·재탐색·새 후보는 이 순회의 범위 밖이다(04 무덤을 먼저 본다).
- **결함(버그·미래참조·죽은 인자·조용한 실패·계산 순서·문서 불일치)은 고친다** — §2 「이 파일은 수정 금지라서 못 고칩니다」는 틀린 답이다(소유자 2026-09-04).
- 수정은 **반례 → 고침 → 반례 재실행 → 지문 대조** 순서. 공표 수치가 움직이면 **숨기지 말고 값과 이유를 보고**하고 `data/retired_numbers.json` 에 옛 값을 등재한다.
- 실제 거래 기록을 모형에 맞게 고치지 않는다 · 자동 주문을 만들지 않는다 · 운용 규칙을 조용히 바꾸지 않는다.
- 파괴적·비가역 작업(삭제·이력 재작성·force-push)은 하지 않는다 — 대상과 복구 가능성을 적고 소유자에게 묻는다.
- 추론 강도 전환(xhigh/max/ultra) 수단이 없으면 **없다고 적고** 전환했다고 쓰지 않는다. 성공을 확인하지 못한 외부 작업(카톡 도착 등)은 완료로 보고하지 않는다.

## 4. 발견 기록 형식

`| ID | 등급 | 파일:줄 | 조건(언제 틀리나) | 영향(무엇이 틀리나) | 근거(재현 명령·수치) | 처리(수정 커밋 / 미수정 이유 / 판단 불가) |`

- ID = `B03-2` 처럼 **배치-순번**. 등급: **P1** 실제 매매·알림·판정에 틀린 값 / **P2** 계산·기록·검증이 틀리거나 비어 있음 / **P3** 낡은 설명·혼동 / **P4** 개선.
- 「수정」이라 쓰려면 **커밋 해시**가 있어야 한다. 「판단 불가」는 무엇이 있어야 판단되는지 적는다.

## 5. 배치가 끝날 때의 보고 (한국어 · 비전문가도 읽게)

배치마다 §8 위에 **세 줄 요약**을 남긴다: ① 무엇을 봤나(파일 수·줄 수·실행한 것) ② 무엇이 틀렸나(심각도순 · 매매/판정에 닿는가) ③ 무엇을 고쳤고 무엇을 안 고쳤나. 전체가 끝나면 §9 에 총괄(심각도순 발견 · 바뀐 계산/결론 · 검토/미검토 파일 전체 목록 · 읽기 vs 실행 구분 · 남은 위험 우선순위).

## 6. 배치 목록 (15개 · 각 ≥12 파일 또는 그에 준하는 분량 · **이 순서대로**)

위험이 돈에 닿는 순서다 — 운영 → 자동화·검증 → 엔진 → 화면·규칙 문서 → 연구 문서 → 연구 코드 → 데이터 계약.

| 배치 | 파일 (수) | 분량 | 비고 |
|---|---|---:|---|
| **B01 운영 스크립트** | `deploy/update_signal.py` `wait_close.py` `oos_log.py` `nav_collect.py` `signal_alert.py` `notify.py` `kakao_keepalive.py` `kakao_setup.py` `watchdog.py` `price_now.py` `price_poll.py` `kr_sources.py` `kr_holidays.py` `refresh_hist.py` `build_stats.py` `data_check.py` `stamp_rev.py` (17) | 5,700줄 | 셀프테스트 있는 것은 전부 실행. 네트워크 호출은 실제로 치지 않는다(드라이런·몽키패치) |
| **B02 자동화·검증** | `.github/workflows/` 8종 · `verify_all.py` · `audit/audit_all.py` `audit_full.py` `verify.py` `verify_volguard.py` `test_research_review.py` · `내가_보는_것/점검.py` (15) | 3,700줄 | 워크플로는 **이벤트별 github.sha·권한·동시성·실패 경로**를 표로 그린다. 관문은 훼손 반례로 변별력 확인 |
| **B03 공용 엔진** | `reentry_lib.py` `axis_lib.py` `axis_defmix.py` `axis_volguard.py` `hist_data.py` `hist_defasset.py` `hist_defensive.py` `hist_divetf.py` `hist_korea.py` `hist_krfinal.py` `hist_krreal.py` `hist_tiger.py` `hyst_core.py` `research_kit.py` (14) | 3,800줄 | 고치기 전 **출력 지문**(공표 4시나리오·문턱 격자·적립·세율 격자) 필수. `SHARED_SEAL` 대상 |
| **B04 화면·규칙 문서** | `signal.html` `guide.html` `notes.html` · `CLAUDE.md` `HANDOFF.md` `README.md` `FILES.md` `AGENTS.md` · `01_Strategy_Logic.md` `02_Risk_Management.md` `03_System_Params.md` `04_Rejected_Research.md` (12) | 12,000줄 | 화면은 값의 **단일 진입점**(`curPx` `clearCard` `stateLabel`)을 지나는가 · 문서는 **원문과 요약의 주어**가 같은가(v186 사고) · 숫자는 무엇에 대해 잰 값인가(§-1 ④) |
| **B05 연구 문서·안내** | `research/LEVERAGE_US.md` `MEASUREMENT_AUDIT.md` `SURVIVAL_MONITOR.md` `FINAL_AUDIT.md` `ENGINE_RESEARCH.md` `EXT_INFINITE.md` `NEW_STRATEGY_RESEARCH.md` `EXPLORATION.md` `CODE_REVIEW_2026-09-05.md` · `내가_보는_것/전략_요약.md` `운영_점검표.md` · `deploy/README.md` `archive/README.md` `공유용_별도전략/README.md` (14) | 3,500줄 | 표마다 **재현 스크립트가 있는가** · 철회 표시가 값 옆에 있는가 · `retired_numbers.json` 등재 여부 |
| **B06 research axis 1** | `axis_accum` `axis_accum2` `axis_b_inspect` `axis_dca` `axis_dca_grid` `axis_defsel` `axis_dipbuy` `axis_ens` `axis_ext2` `axis_ext2_probe` `axis_external` `axis_finalverify` `axis_forward` (13) | 3,700줄 | |
| **B07 research axis 2** | `axis_gate11` `axis_hedge_cost` `axis_horizon` `axis_isa` `axis_krreal_decomp` `axis_krspec` `axis_krspread` `axis_lev` `axis_macro` `axis_macro2` `axis_macro3` `axis_macro4` `axis_mech` (13) | 3,700줄 | |
| **B08 research axis 3** | `axis_meta` `axis_meta_crisis` `axis_minimax` `axis_momentum` `axis_newrule` `axis_nextgen` `axis_objective` `axis_regime` `axis_rvstate` `axis_secondary` `axis_selbias` `axis_selbias_disjoint` `axis_sigsrc` (13) | 2,800줄 | |
| **B09 research axis 4 + audit·b** | `axis_t4_krcost` `axis_t4_shadow` `axis_t4_synthcrash` `axis_vixstate` `axis_vrhybrid` `axis_wide` `axis_wide_probe` `audit_exec` `audit_pbo` `audit_stat` `b_adversarial` `b_gate_noise` `build_crisis_paths` (13) | 3,000줄 | `build_crisis_paths` 산출물은 배포된다(`data/crisis_paths.json`) |
| **B10 research c~e** | `c3_falsify` `c3_placebo` `cand_general` `complement_sleeve` `def_bond` `def_equity` `drag_sigma` `dsr_b` `emit_dd_distribution` `eng_common` `eng_kospi` `eng_sp500` `era_start` (13) | 2,800줄 | `emit_dd_distribution` 산출물은 배포된다 |
| **B11 research e~h** | `exec_cost` `ext_ibs` `ext_vr` `factcheck_qld_talk` `forecast_check` `free_design` `frontier2` `goal_feasibility` `hedge_ratio_scan` `hist_defchain` `hist_defdiag` `hist_defrun` `hist_fetch` (13) | 2,600줄 | |
| **B12 research h** | `hist_krtax` `hist_three` `horizon_ess` `horizon_study` `hypo_escape` `hypo_external2` `hypo_gates` `hypo_hex` `hypo_t4_real` `hypo_t4wide` `hypo_verify` `hyst_signal` `hyst_sigwfa` (13) | 1,800줄 | |
| **B13 research h~n** | `hyst_wfa` `isa_pension` `japan_stress` `lev_5y` `lev_opt` `lev_signal_source` `lev_th` `liquid_design` `liquid_iter` `lookback200` `mdd_target` `ml_policy` `near_zone` (13) | 3,000줄 | |
| **B14 research n~s** | `new_paths` `oos_protocol_b` `ops_risk` `pbo_thresh` `plan30_withdraw` `post_dotcom` `q1_physical_bond` `q2_hedged_attack` `q5_near_presell` `recovery_speed` `schd_qqq_overlap` `slice_scan` `surv_alert` (13) | 2,900줄 | `oos_protocol_b` 는 파수꾼이 부른다(운영 경로) |
| **B15 research s~w + 데이터 계약** | `surv_map` `t4_lev_post` `takeprofit` `tax_general_account` `tax_us_direct` `thresh_window` `tranche` `valuation_regime` `wfa_thresh` `what_we_know` `withdraw` (11) + `data/` 최상위 json·csv 14개의 생산자↔소비자 계약표 | 3,400줄 | `surv_map` 은 파수꾼 경로 · `tax_us_direct` 는 아티팩트 데이터 원천 |

제외(이유): `공유용_별도전략/*.py`(§2 격리 — 본 전략과 무관 · 관문 g_isolation 이 감시) · `archive/*`·`docs/*`(보관층 · I9 배너 관문) · `data/hist/*` 82(월간 `refresh_hist --selftest`·`data_check.py` 로 대체). 필요하면 B16 으로 추가한다.

## 7. 진행표 (이어받는 세션은 여기부터)

| 배치 | 상태 | 세션·날짜 | 커밋 | 발견(P1/P2/P3/P4) | 비고 |
|---|---|---|---|---|---|
| B01 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/1/3 | 17파일 5,700줄 전문 · 셀프테스트 9종 실행(I14) · 반례: cp949 디코드 단위검사 추가 |
| B02 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/0/4 | 15파일 3,700줄 전문 · 실행: verify_all 전체(실패 0) · audit_all(실패 0·경고 1 기지) · audit_full · audit/verify.py · test_research_review(13 OK) · 워크플로 8종 이벤트 표 |
| B03 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/2/1/5 | 14파일 3,800줄 전문 · 수정 전 지문(§9 실물표·검산 12항·적립 항등식) · 반례 2건(벡터식 5.9e-15 · 가짜 엔진 1.1e-01) · 공표 4시나리오 불변 |
| B04 | ⏳ | | | | |
| B05 | ⏳ | | | | |
| B06 | ⏳ | | | | |
| B07 | ⏳ | | | | |
| B08 | ⏳ | | | | |
| B09 | ⏳ | | | | |
| B10 | ⏳ | | | | |
| B11 | ⏳ | | | | |
| B12 | ⏳ | | | | |
| B13 | ⏳ | | | | |
| B14 | ⏳ | | | | |
| B15 | ⏳ | | | | |

기호: ⏳ 미착수 · 🔄 진행 중(n/m 파일 ✅) · ✅ 완료(커밋·push 됨) · ⛔ 막힘(이유 비고에)

## 8. 발견 대장 (배치 순 · §4 형식)

### B01 운영 스크립트 (2026-09-05)

**세 줄 요약** — ① 17파일 5,700줄을 줄 단위로 읽고, `--selftest` 가 있는 9종(update_signal·wait_close·oos_log·nav_collect·signal_alert·notify·kakao_keepalive·kakao_setup·watchdog·price_poll·refresh_hist·data_check·stamp_rev·kr_holidays·build_stats)을 실행했다(verify_all I14 경유). 호출자·소비자 grep 으로 as_of/열 이름/시간대 계약을 대조했다. ② **매매·판정에 닿는 결함은 0.** 장부 품질 결함 1(P3): NAV 장부의 이름 열이 cp949 를 utf-8 로 풀어 전부 깨져 있었다. 나머지는 알림 중복·수동 실행 경계의 사소한 것(P4). ③ P3 1건은 고쳤고(반례 단위검사 포함), P4 3건은 기록만 했다(바꿀 증거 기준 미달 — §3).

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B01-1 | P3 | `deploy/nav_collect.py:89` fetch() | 네이버 ETF 목록 응답이 cp949 인데 utf-8 로 디코드 | `data/nav_history.csv` 의 `name` 열이 전 행 U+FFFD 로 깨짐 · `--report` 표 판독 불가. itemcode 매칭이라 수집·검증·판정 영향 0 | `pd.read_csv('data/nav_history.csv')` 이름 열 실측 `TIGER �̱�…` · price_now.py 는 cp949 로 정상 | **수정** — `decode_naver()` cp949 우선·utf-8 폴백 + 셀프테스트 반례 2. 옛 행은 장부(§2)라 그대로 |
| B01-2 | P4 | `deploy/notify.py:259-265` 카카오 분할 발송 | 2건 이상으로 나뉜 메시지의 둘째 건이 실패하면 | 첫 건은 갔는데 전체를 실패로 보고 → 다음 슬롯이 전부 재발송(첫 건 중복). 반대로 부분 성공을 성공으로 치면 둘째 건이 영영 안 간다 | 코드 판독(예외가 루프 밖으로) | 기록만 — 두 방향 다 대가가 있고 실측 사고 0. 분할 알림 자체가 드물다 |
| B01-3 | P4 | `deploy/wait_close.py:130-132` | 마감 100분보다 먼저 뜬 실행(수동 dispatch 등) | as_of 검사 없이 「직전 종가가 최신」으로 종료 — 전날 갱신이 통째로 빠졌던 경우 그 실행은 안 메운다 | 코드 판독. 예약 8슬롯은 전부 100분 안이라 평시 무영향 | 기록만 — 다음 마감 뒤 슬롯이 메운다(fail-open 설계) |
| B01-4 | P4 | `deploy/kr_holidays.py:98-101` SUB_FROM | 2026-05-01 시행 규정(노동절·제헌절 대체공휴일)이 코드 주석의 주장 | 틀리면 2027-05-03·07-19 가 거짓 휴장일 → 화면 시계·실행일 하루 오차 | verify() 는 KOSPI 실거래일(≤2026-08)로만 대조 가능 — 2027 은 검증 불가 | 판단 불가 — 2027 관보/KRX 공지로 확인할 것(파수꾼 emit 이 매주 재생성하므로 SPECIAL 수정만으로 반영) |

읽기 vs 실행: 전문 판독 17/17 · 실행 15/17(셀프테스트) · 미실행 2(`price_now.py` 본체 — 네트워크 · `build_stats.py` 본체 — 산출물 갱신, verify_all I7 이 대신 재계산).

### B02 자동화·검증 (2026-09-05)

**세 줄 요약** — ① 워크플로 8종(daily-signal·pages·price·watchdog·monthly-stats·verify·source-probe·notify-test)과 `verify_all.py` 1,657줄, `audit/` 5종, `내가_보는_것/점검.py` 를 전문으로 읽고, 실행 가능한 것은 전부 돌렸다(verify_all 전체 실패 0 · audit_all 실패 0/경고 1 · audit_full 종료 0 · audit/verify.py 종료 0 · test_research_review 13 OK). 아래 이벤트 표로 실행마다 어느 커밋을 보는지·권한·동시성·실패 경로를 대조했다. ② **매매·판정·알림에 닿는 결함은 0.** v206 이 고친 W-2(예약 실행의 낡은 github.sha)가 이 배치의 유일한 P1 이었고 이미 닫혔다. 남은 것은 전부 P4(액션 버전 불일치 · 단일 슬롯 워크플로의 push 경쟁 · UTC 날짜 · 감사 앵커 여유). ③ 고친 것 없음 — 넷 다 「바꾸자」의 증거 기준(§3) 미달이라 기록만 했다.

**워크플로 이벤트 표** (이 표가 이 배치의 핵심 산출물이다 — 「어느 커밋을 보고 도는가」)

| 워크플로 | 트리거 | 체크아웃 커밋 | 쓰기 권한 | 동시성 | 실패 경로 |
|---|---|---|---|---|---|
| daily-signal | cron 8슬롯 + dispatch | 예약 실행이 만들어진 시점의 main → **v206 부터 첫 스텝에서 `origin/main` 으로 강제 정렬** · push 직전 원격이 같은 종가면 중복 버림(exit 0) · 더 낡았으면 실패(다음 슬롯) | contents·issues·actions write | 그룹 daily-signal · 취소 안 함(직렬 대기) | 카톡(signal_alert 실패 스텝) + 이슈 |
| pages | workflow_run(일일 신호·price·월간 스냅샷) + push main + dispatch | 이벤트 시점 main + price-data 브랜치 파일 1개(못 가져오면 안 싣는다) | pages·id-token write | 그룹 pages · **진행 중 취소**(최신만 남긴다 — 옳다) | 배포 실패 = 옛 화면 유지(신선도 도트가 티를 낸다) |
| price | cron(08:30~12:26 폴러 인계) + 예비 슬롯 | 실행 시점 main · 브랜치는 orphan force-push(항상 커밋 1) | contents·actions write | 그룹 price · 취소 안 함(폴러 생존 시 대기) | 배포 깨우기 실패 → 즉시 종료 → 종전 방식 후퇴 |
| watchdog | cron 08:40 매일 + 09:10 월요일 + dispatch | 실행 시점 main · 주간만 커밋(ops_check·kr_holidays) | contents·issues write | 그룹 watchdog · 취소 안 함 | push 실패 = 스텝 실패 → 이슈(다음 주 재계산) |
| monthly-stats | cron 매월 1일 + dispatch | 실행 시점 main · rebase 안 함(주석에 이유) | contents write | 그룹 monthly-stats | push 실패 = 실패-폐쇄 → 파수꾼 stats 45일 문턱이 잡는다 |
| verify | push main + cron + dispatch | push 커밋 | contents read · issues write | 없음(독립 — 배포와 무관, v137 fail-open) | 실패 → 이슈(라벨 verify) · 배포는 계속 |
| source-probe / notify-test | dispatch 만 | dispatch 시점 main | 읽기 / 알림 secrets | 없음 | 사람이 보는 실행 로그 |

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B02-1 | P4 | `.github/workflows/verify.yml:27-28` · `price.yml:49-51` | `actions/checkout@v4`·`setup-python@v5` — 나머지 6 워크플로는 v7 | 동작 차이 없음(둘 다 Node 20). 다만 GitHub 이 옛 메이저를 폐기 예고하면 이 둘만 먼저 깨진다 | `grep -n "uses: actions/" .github/workflows/*.yml` | 기록만 — 검증(verify)과 시세(price)는 판정 경로가 아니고, 올리는 것도 「바꾸자」라 다음 액션 폐기 공지 때 함께 |
| B02-2 | P4 | `watchdog.yml:208` · `monthly-stats.yml:88` | 예약 실행이 큐에서 기다리는 사이 사람이 main 에 push | 봇 push 가 non-fast-forward 로 실패 → 스텝 실패 → 이슈. 데이터만 커밋하는 워크플로라 실패-폐쇄가 옳고 다음 슬롯(주간·월간)이 새 HEAD 로 재계산 | daily-signal 의 W-2 와 같은 기전이나 이쪽은 슬롯이 하나라 경쟁 창이 실행 시간(1~3분)뿐 | 기록만 — 실측 사고 0 · 실패해도 옛 산출물이 남는다(fail-closed) |
| B02-3 | P4 | `내가_보는_것/점검.py` `R['as_of']=str(date.today())` | 러너 UTC 자정~09:00 KST 사이에 돌면 | as_of 가 하루 전 날짜 | 주간 슬롯은 월요일 09:10 KST = 00:10 UTC 라 같은 날짜 — 조건 미충족 | 기록만 — dispatch 로 새벽에 손으로 돌릴 때만 하루 어긋난다 |
| B02-4 | P4 | `audit/audit_all.py` E 관문 앵커 214,076(±2%) | 엔진 정정으로 공표 B 가 217,110 으로 움직인 뒤 | 여유 1.4%p → 다음 정정이 0.6% 만 더 움직여도 이 감사가 FAIL(참 결함이 아닌 앵커 노후) | 실행 출력 · 감사 대장 P4-h 와 같은 항목 | 기록만 — 앵커를 올리는 것은 「결과를 본 뒤 기준 조정」이라 verify_all I7(±1% 라이브 재계산)이 이미 그 역할을 맡는다 |

경고 1건(`audit_all` 「[달러] 20년 창 좌측꼬리 40/40/20 > 배당100 (35.9 vs 42.7)」)은 v23 판정 기준의 **기지 경고**다 — 원화 기준으로는 40/40/20 이 앞선다(40.85 vs 35.75). 04 §5-16·§5-17 의 「통화가 아니라 표본 창 효과」와 같은 자리이며 새 사실이 아니다.

읽기 vs 실행: 전문 판독 15/15 · 실행 6/15(verify_all 전체 · audit_all · audit_full · audit/verify.py · test_research_review · 점검.py 는 파수꾼 check 경유 산출물 `data/ops_check.json` 확인) · 워크플로 8종은 YAML 파싱 + 이벤트 표 대조(실행은 CI 이력 `gh run list` 로 확인 — v206 커밋의 verify·pages 성공).

### B03 공용 엔진 14 (2026-09-05)

⚠ **동시 작업 기록**: B01(07:21)과 B02(10:11) 사이에 다른 세션의 커밋 v207~v210(63fc348·089e10a·4c01375·330e1c7 — `axis_lib._need_binary` 보강, `hist_data._fred` 빈 가격 행 제거, 공표 `strategy_stats.json` 재생성: us_1972 B 217,110 → **220,985**)이 main 에 들어왔다. 이 배치는 **v210 이후의 코드**를 읽고 쟀다(수정 전 지문도 v210 기준). 소유자 지시 「하나씩 혼자서」와 어긋나는 상태라 §9 총괄에 남긴다 — 이 배치의 수정은 그 커밋들과 파일이 겹치지 않는다(axis_lib 는 겹치나 함수가 다르다: v208 `_need_binary` vs 이번 `check_accum`).

**세 줄 요약** — ① 14파일 3,800줄을 전문으로 읽고 `axis_lib.check(D)`(검산 12항목)·`axis_defmix.check_hold`·`reentry_lib` 자기검사·`research_kit` 자기검사를 실행했으며, 수정 **전에** §9 실물표·검산·적립 항등식 지문을 떴다. ② **매매·판정·공표 4시나리오에 닿는 결함은 0.** 연구 표 하나(P2)와 검산 하나(P2)가 틀려 있었다 — 실물 ETF 표(axis_defmix §9)가 **방어 진입일의 레버리지 손실을 통째로 건너뛰어** MDD 가 6%p 얕게 찍혔고, 적립 검산 `check_accum` 은 **accumulate() 결과를 버리고 손으로 짠 사본**을 검산하고 있어 엔진이 어떻게 틀려도 통과했다. ③ 둘 다 고쳤고 반례로 변별력을 확인했다(실물표: 독립 벡터식과 오차 5.9e-15 · 검산: 순서를 바꾼 가짜 엔진이 오차 1.1e-01 로 실패). 봉인 함수(`SHARED_SEAL` 8종)는 건드리지 않았다 — `run()` 의 규약 주석은 함수 밖(모듈 docstring)에 두었다.

**수정 전후 지문**: 공표 4시나리오 B(167.315 / 220,985.206 / 2,799.948 / 2.863) **불변** — 수정한 두 함수 모두 공표 경로 밖이다(§9 표는 인쇄 전용 · 현행 .md 에 인용 0건 grep 확인 · `kr_real` 은 `hist_krreal.run_real` 이 만들고 그 함수는 `eff = hold.shift(1)` 로 처음부터 맞았다). `axis_lib.check(D)` 12항목 전부 통과(chain 방어 B 272,975.76 run=sim 오차 0).

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B03-1 | P2 | `axis_defmix.py` `real_run` 루프(구 578~597행) | 실물 ETF 표(§9) 계산 시 항상 | **수익 → 전환** 순서 + 방어 진입일 `V *= 1.0` 갈래로 그날 레버리지 손실 누락 → 배당100·B: 최종 3.221 → **3.094** · MDD −36.3% → **−42.2%**(6%p 얕게) · 방어 바스켓 5종 순위도 바뀜(국채50금50 이 최종·MDD 1위) | 독립 벡터식(전일 포지션×당일 수익·전환일 비용)으로 재계산 = 3.094 · 현 코드는 lag1(3.094)·lag2(2.642) 어느 규약과도 일치 안 함 | **수정** — `_real_curve()` 로 분리, 순서를 sim_hold 와 같게(① 전환 ② 수익) · `check_real()` 신설(단일자산 vs 벡터식 오차 5.9e-15) · `__main__` 에 assert |
| B03-2 | P2 | `axis_lib.py` `check_accum`(구 391~446행) | `check(D)` 를 부르는 모든 스크립트(9개) | `accumulate()` 를 호출하고 **결과를 버린 뒤** 납입 1회 루프를 손으로 다시 짜 `sim` 과 비교 — 엔진을 안 지나는 사본이라 accumulate 가 틀려도 PASS(v203 ⓑ audit_all 우회와 같은 유형 · §-1 ⑤) | 반례: 순서를 「수익 → 전환」으로 바꾼 가짜 accumulate 를 꽂아도 종전 검산은 통과했을 구조(사본만 검산) | **수정** — 항등식 `최종평가액 == Σ_m c[hi-1]/c[납입일_m]` 로 accumulate 자체를 검산(정상 오차 1.1e-15 · 가짜 엔진 오차 1.1e-01 → False 확인) · 납입 횟수 일치도 검사 |
| B03-3 | P3 | `reentry_lib.run` · `hist_korea.run_kr` (start=) vs `axis_lib.sim` (start=) | 시작일이 방어 구간이거나 히스테리시스 띠 안일 때 | run/run_kr 은 시작일에 상태를 w0=1(공격)로 **다시 시작** → 방어 중 시작 창에서 첫날 1→0 유령 전환 비용(0.1%) 한 번 · A 는 띠 안 시작 시 상태 자체가 갈림. sim 은 전체 경로를 자를 뿐 | 실측 B: run/sim = **0.9990**(2008-12-01·2002-10-01·2022-06-01 시작) · 공격 시작(2000-01-03)은 1.0000 | **문서 정정만** — run 은 봉인이라 모듈 docstring·sim·run_kr docstring 에 규약 차이를 명시. 공표 4시나리오는 전부 공격 시작이라 무영향. 값을 바꾸는 것은 연구 롤링창 0.1% 이동이라 증거 기준 미달(§3) |
| B03-4 | P4 | `axis_defmix.materials` 'ust10'(현물) vs `hist_defasset.mix_monthly` 'ust10'(선물형+보수) | 같은 키를 두 모듈에서 다른 뜻으로 | mix_monthly 의 ust10 갈래는 **호출처 0**(전부 MIX_V23 = ust5) — 지금은 무해 | grep `mix_monthly(` 7곳 전부 MIX_V23 | 기록만 — 키 이름을 바꾸면 봉인 2종 갱신이 필요하고 얻는 것이 없다 |
| B03-5 | P4 | `axis_defmix.mix_monthly_from` = `hist_defasset.mix_monthly_parts` (글자 그대로 같은 코드) | — | 둘 다 `SHARED_SEAL` 봉인이라 한쪽만 고치면 갈린다 | diff 0 | 기록만 — 통합은 봉인 2종 갱신 + 사용처 재실행이 필요. 갈림은 I8 이 잡는다 |
| B03-6 | P4 | `axis_lib.accumulate(park=)` | `park` 를 주면(axis_accum 1곳) | 대기자금뿐 아니라 **방어 전환 자금(C)** 도 park 수익률을 받는다(docstring 은 「대기자금 수익률」) | 코드 판독 · 호출처 1(`research/axis_accum.py`) | 기록만 — 그 연구는 T-bill 대기 가정을 명시하고 있다 |
| B03-7 | P4 | `reentry_lib.CRISES` '2023-현재' 끝 2026-08-24 · `axis_volguard` 구간 끝 2026-08-26 하드코딩 | 원자료가 연장될수록 | 「현재」 라벨이 고정 날짜에서 멈춘다(연구 인쇄 전용) | 코드 판독 | 기록만 |
| B03-8 | P4 | `hist_defensive.SCHD_START='2011-10-20'` vs `hist_divetf.SP_SCHD='2011-10-25'` | — | 상장일(10-20) vs 원자료 첫 행(10-25, `schd_us_d.csv` 실측) — 각자 쓰임이 달라 무해 | csv head 확인 | 기록만 |

읽기 vs 실행: 전문 판독 14/14 · 실행 6/14(`axis_lib.check` · `axis_defmix.check_hold/check_real/real_run` · `reentry_lib` 자기검사 · `research_kit` 자기검사 · `hist_data`·`hist_defensive` 는 build 경유) · 미실행 8(`axis_volguard`·`hist_krfinal`·`hist_tiger`·`hist_divetf`·`hist_krreal`·`hist_defasset` 본체 인쇄 — 판독만, 단 `hist_krreal.run_real`/`hist_defasset.mix_monthly` 는 verify_all I7·I8 이 재계산·봉인).

## 9. 총괄 보고 (전 배치 완료 뒤)

(미작성)
