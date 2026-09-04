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
| B01 | ⏳ | | | | |
| B02 | ⏳ | | | | |
| B03 | ⏳ | | | | |
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

(아직 없음)

## 9. 총괄 보고 (전 배치 완료 뒤)

(미작성)
