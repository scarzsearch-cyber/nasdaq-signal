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
| B04 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋 · v211) | 0/1/3/5 | 12파일 12,179줄(04 는 감사 전문+diff) · verify_all 전체 · I9 관문이 정정 자리 지목(FAIL1·WARN10 → 0) |
| B05 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋 · v212) | 0/1/4/4 | 14파일 3,338줄(변경분은 diff · 미변경 5편은 감사 판독 재사용+표적 grep) · `horizon_study.py` 재실행으로 guide ② 원천 대조 · verify_all 전체 |
| B06 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/1/7 | 13파일 4,167줄 전문 · 실행 6(ens·dipbuy·accum·b_inspect·dca_grid + finalverify --selftest) · **적발 1(P3)**: `axis_b_inspect` P3 사건승 v210 자료 재실행 62%(13/21) — 문서의 「15/21=71% · 통과」와 다름. 병기 2곳 · 3곳은 보류(다른 세션 미커밋 파일) |
| B07 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/0/7 | 13파일 3,700줄 전문 · 실행 7(gate11·horizon·hedge_cost·krspec·krreal_decomp·lev·mech — 판정 전부 계산 생성 · 기존 결론 재현) · 수정 0 |
| B08 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋 · v214) | 0/1/2/6 | 13파일 2,955줄 전문 · **실행 13/13** + 세 작업트리(v203·v209·v210) 대조 · **적발**: `axis_nextgen` 앵커 사망→갱신→**판정 뒤집힘(MIX 0.50 통과 · 채택 아님)** · T4 계열 v210 민감도 +57.7% · 문서 수치 4종 정정+등재 |
| B09 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋 · v215) | 0/1/2/6 | 13파일 3,194줄 전문 · **실행 13/13** · 재현 앵커 2개(t4_shadow v68 · gate_noise 217,110) v210 기준 갱신 · **설명서 ⑪ T4 성적표 v80 값 → 재계산(P2)** · 결론 변경 0 |
| B10 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/1/7 | 13파일 2,540줄 전문 · **실행 13/13** · 검산 전부 통과 · C3 관문 수치 v210 뒤 하락(+13.4→+10.5% · p05 +26→+1.7%) 3곳 병기 · 배포 산출물 dd_percentile diff 0 |
| B11 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/0/8 | 13파일 2,411줄 전문 · 실행 12/13(hist_fetch 네트워크 제외) · 사전 등록 예측 대조 전부 문서와 동일 · 수정 주석 1·표시 3 |
| B12 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/1/6 | 13파일 1,770줄 전문 · 실행 12/13 · 검산 전부 통과 · MEASUREMENT §1 유효표본 표 v210 재실행 병기(B05-8 해소) · T4 1978~ 공통창 0.50×B 기록 |
| B13 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/2/6 | 13파일 2,909줄 전문 · **실행 13/13** · 룩백200 표본 내 우위(승률 100→78% · 5/8→3/7)·기계정책 3/45→14/45·hyst_wfa 세 작업트리로 원인 가름(v210 / v204 / v210) · 문서 19곳 병기 · 결론 변경 0 |
| B14 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋 v218) | 1/0/1/6 | 13파일 2,770줄 전문 · **실행 13/13** · **P1 B 판정 규약 기저율이 v210 뒤 등록값과 어긋나 평가기 판정 중단·월요일 파수꾼 경고 예정 → 판정 사건 0건 상태에서 재등록(새 지문 74387a5c73c0fc06 · I13 FAIL→PASS 재현)** · 「38배」→49배 등 8건 병기 · post_dotcom 판정문 계산화 |
| B15 | ✅ | Claude Fable 5.1 · 2026-09-05 | (이 커밋) | 0/0/3/5 | 11파일 3,075줄 전문 · **실행 14/14** + 데이터 계약 14개 자동 대조 · v210 뒤 wfa 12/12→7/12·withdraw 위상 의존(−51.3→−16.0%)·tax 1981~ 1.75→1.82 를 wt209 로 가름 · 하드코딩 판정 2건 계산화 · 21세기 세후 표 동일 |

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

### B04 화면·규칙 문서 12 (2026-09-05 · v211)

**세 줄 요약** — ① `signal.html`(3,548줄)·`guide.html`·`notes.html`·`CLAUDE.md`(§4 최신 항목·diff)·`HANDOFF`·`README`·`FILES`·`AGENTS`·`01`~`03` 을 전문으로, `04`(3,257줄)는 감사 때 전문 판독한 뒤 53aab70 이후 diff 로 읽었다. 화면은 값의 단일 진입점(`curPx`·`clearCard`·`stateLabel`·`getDefenseEntryDate`)을 지나는지, 문서는 숫자가 무엇에 대해 잰 값인지(§-1 ④)를 봤다. ② **매매·판정에 닿는 결함 0.** 화면 각주 숫자 오기 1(P3) · 설명서 낡은 % 2(P3) · 01 §7 낡은 v63 수치·중복 배너(P3) · **폐기 수치 대장 미등재+낡은 `now` 16건(P2 — 검증 대장이 틀려 있음)** · 날짜 UTC(P4→수정). ③ 전부 고쳤고 I9 관문이 정정 표시 자리를 지목해 그대로 채웠다. 화면 변경이라 **v211** 로 도장(CLAUDE §4·notes 등재).

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B04-1 | P2 | `data/retired_numbers.json` | v210(다른 세션)이 ISA 공표값을 바꾸면서 | 옛 값(135.24/114.38/87.44/149.99배·+54.7%·과세이연 83%) **미등재** + 기존 16항목의 `now` 필드가 그 폐기값을 「현행」으로 가리킴 → I9 가 옛 값의 잔존을 못 잡는 상태 | `grep 135.24 data/retired_numbers.json` → `now` 6곳 · 등재 0 | **수정** — 6종 등재(since v210) · `now` 16곳 갱신 → I9 가 지목한 CLAUDE 3곳·02 §7·FILES 에 정정 표시, 버전 문서 2편(v29·v203 리뷰)에 v210 배너. 실측: 등재 직후 FAIL 1·WARN 10 → 처리 후 0 |
| B04-2 | P3 | `signal.html` drawPerf 각주 「최근 20년으로 맞추면 136배 vs 168배」 | 항상 | 168 은 원화 B(189.3)가 아니라 원화 **2배 보유**(168.2)의 값 — 같은 화면의 「같은 기간」 표(189배)와 모순(v179 유형) | `strategy_stats.json` kr_1997 B 20y 189.295 · lev 168.218 | **수정** — STATS 에서 읽는 `h20` 로 교체(표와 같은 원천) |
| B04-3 | P3 | `guide.html` ④-6 「ISA 대비 약 −35%」·「3년 해지 약 −15%」 | v210 뒤 | 현행 88.57/141.61 = −37.5% · 118.05/141.61 = −16.6% | 02 §7 v210 표 | **수정** — −37% / −17% + 근거 배수 병기 |
| B04-4 | P3 | `01_Strategy_Logic.md` §7 불릿 (22.0/27.9 · 93.5/118.5 · 186.7/165.9) · 머리 v210 배너 2회 | — | v63 시절 값이 현행 문서에 그대로 · 배너가 두 번 붙어 있음(v210 커밋) | JSON horizons: B 21.884/90.771/189.295 · lev 27.732/115.032/168.218 | **수정** — 현행 값 + 출처 병기 · 중복 배너 제거 |
| B04-5 | P4→수정 | `signal.html` `savePort`·`inDate` 기본값·`chkKey` 예비 | 00:00~09:00 KST | `toISOString()` 의 UTC 날짜라 전날로 적힘(「마지막 입력 N일 전」·수동 입력 날짜) — v202 가 `bizDaysSince` 에서 고친 것과 같은 유형 | 코드 판독 | **수정** — `kstISO()`(inDate 는 `SEOUL` 상수 정의 뒤인 boot 에서) |
| B04-6 | P4 | `signal.html` 「−11% ~ −16% 회색지대」 안내(v61 잔재) | 공격 상태 dd∈(−16,−11] | B 는 히스테리시스가 없어 「회색지대」라는 말이 규칙과 안 맞고 게이지(접근/근접)와 중복 | 코드 판독 | 기록만 — 문구 취향 영역(v61 이 의도적으로 남김) |
| B04-7 | P4 | `02_Risk_Management.md` §1 「29.6년」·§3 「13,861일·140회」 | v210 뒤 | 현행 29.7년 · 13,749일 · 138회 — v210 배너가 「당시 기록」으로 덮는다 | JSON·04 v210 배너 | 기록만 |
| B04-8 | P4 | `guide.html` ④-2 「닷컴 약 97%」 vs `02` §3 「닷컴 1건 96%」 | — | 분모가 다르다(2000~ 33배 분해 vs 54년 에피소드 70개) — 둘 다 출처 표기 있음 | — | 기록만 |
| B04-9 | 판단 보류 | `guide.html` ② 기간별 확률표(12,099창 · 1972~) | v210 이 1972~85 구간 114행을 제거 | 54년 창 통계가 미세하게 움직였을 수 있음 — 재현 스크립트(`LEVERAGE_US` §9 / `horizon_*`) 재실행 여부는 B05 에서 확인 | 04 v210 배너 「장기 연구는 재실행 전 인용 보류」 | B05 로 이월 |

읽기 vs 실행: 전문 판독 11/12 + 04 는 감사 전문 판독 + diff · 실행: `verify_all` 전체(실패 0) · `node` 구문 검사(signal.html 스크립트 2개) · 배포 후 화면 확인은 push 뒤 브라우저에서(§5 보고).

### B05 연구 문서·안내 14 (2026-09-05 · v212)

**세 줄 요약** — ① `CODE_REVIEW_2026-09-05.md` 의 v207~v210 절(다른 세션 작성 · 346줄 신규)·`MEASUREMENT_AUDIT`·`FINAL_AUDIT`·`EXPLORATION`·`운영_점검표` 는 53aab70 이후 diff 를, `전략_요약`·`운영_점검표`·`deploy/README`·`archive/README`·`STRATEGY_RESEARCH_2026-09-05`(다른 세션 신규) 는 전문을, 미변경 5편(`LEVERAGE_US`·`SURVIVAL`·`ENGINE`·`EXT_INFINITE`·`NEW_STRATEGY`·`공유용 README`)은 감사 때 전문 판독을 재사용하고 v210 전 수치·재현 스크립트 유무를 grep 으로 봤다. **B04-9(설명서 ② 확률표가 v210 이후 재실행됐는가)를 실제로 재실행해 답했다.** ② **매매·판정에 닿는 결함 0.** 설명서 ②·`LEVERAGE_US` §9·02 §1-1·신호 화면 팩트 한 줄의 지평 표가 **v203 엔진 정정·v210 거래일 정정 이전 값**이었다(P2 — 화면의 낡은 수치 · 중앙 1~8% 저평가 · 창 수 12,099→11,985). 연구 문서 5편은 v210 배너 없이 옛 값(217,110 등)을 들고 있었고(P3), 안내 문서의 파수꾼 셀프테스트 수가 세 곳에서 세 값(28/30여/61)이었다(P3). ③ 지평 표는 같은 스크립트 재실행값으로 교체(결론 불변: 손실 0 문턱 7년·최악 +6%·최악 시작 시점 동일), 옛 값 2종 등재·정정 표시, 배너 5편, 안내 수치 정정. 화면 문자열 변경이라 **v212**.

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B05-1 | P2 | `guide.html` ② 표 · `research/LEVERAGE_US.md` §9 표 A · `02` §1-1 · `signal.html` FACTS[4] | v203(국채 bfill·DVY·워밍업)·v210(FRED 114행) 이후 재실행 안 됨 | 중앙값 3년 1.95→1.96 · 5년 3.08→3.16 · 7년 5.43→5.70 · 10년 9.96→10.79 · 15년 29.1→30.0 · 20년 115.6→121.3배 · 7년 창 12,099→11,985 · 1년 손실 22.5→22.7% · B>맨몸 37~79%→42~81%. **손실 0 문턱 7년·최악 +6%·최악 시작일(1987/2000-03)·p05 는 사실상 그대로** | `python research/horizon_study.py` 2026-09-05 (n=13,749 · 1972-02-07~2026-08-28) + 1년 행은 같은 엔진(`eng_common.sim2`)으로 계산 | **수정** — 네 곳 재실행값으로 교체(재실행 날짜·옛 값 병기) · `12,099`·`9.96배` 를 `retired_numbers.json` 등재(since v211) · 인용 자리(04 §5 표 2곳·CLAUDE §4·MEASUREMENT §1·§8·SURVIVAL §E)에 정정 표시 |
| B05-2 | P3 | `research/ENGINE_RESEARCH.md`·`EXT_INFINITE.md`·`NEW_STRATEGY_RESEARCH.md`·`SURVIVAL_MONITOR.md`·`LEVERAGE_US.md` 머리 | v210 뒤 | 다른 세션이 04·MEASUREMENT·FINAL·EXPLORATION 에는 v210 배너를 달았으나 이 5편은 옛 엔진 값(54년 B 217,110 등)을 배너 없이 든다 | grep 217,110 | **수정** — 한 줄 주의 배너(재실행 전 인용 금지 · 결론 방향 불변) |
| B05-3 | P3 | `deploy/README.md` 「--selftest 28경우」 · `verify_all.py` I14 라벨 「30여 경우」 · `FILES.md` 「61개」 | — | 같은 셀프테스트 수가 세 문서에서 다르다 | `python deploy/watchdog.py --selftest` → **61경우** | **수정** — 61 로 통일 |
| B05-4 | P3 | `02` §1 「29.6년」·Calmar 0.547/Sortino 1.143 · `내가_보는_것/전략_요약.md` 「29.6년」·「화면 2개」 · `운영_점검표.md` §0 「화면 2개」 | v65 이후 갱신 안 됨 | 현행 29.7년 · 0.548/1.145(벤치 0.183/0.785) · 화면 3개(v142) | `strategy_stats.json` kr_1997 | **수정** |
| B05-5 | P4 | `research/CODE_REVIEW_2026-09-05.md` v207~v210(다른 세션) | — | 표마다 재현 스크립트·기준 커밋이 있고 「미검증」 절이 명시돼 있다 — 이 배치가 요구하는 형식을 갖췄다. 단 v210 R04 가 재생성 대상으로 `horizon_study` 를 빼놓아 B05-1 이 남았다 | 판독 | 기록만 — 04 §7 Q10 의 「전체 연구 재실행 아님」에 포함 |
| B05-6 | P4 | `research/STRATEGY_RESEARCH_2026-09-05.md`(다른 세션 · 사전 기록) | — | 기준 코드로 `f9d0558` 을 적고 있어 이 순회의 B02 커밋을 기준선에 포함한다 — 두 작업이 같은 작업 트리를 쓴다는 증거 | 판독 | 기록만 — §9 총괄의 동시 작업 항에 반영 |
| B05-7 | P4 | `공유용_별도전략/README.md` · `archive/README.md` | — | 미변경 · 감사 판독과 동일 · 격리 규정 그대로 | — | 기록만 |
| B05-8 | P4 | `research/MEASUREMENT_AUDIT.md` §1 표(3~30년 창 수·비중첩·AR-ESS) | v210 뒤 | 창 수가 114 씩 줄어 비중첩·AR-ESS 도 미세 이동 가능(7.9→7.8) — Codex 의 v210 배너가 「재검증 전」으로 덮는다 | `horizon_study` 비중첩 열 7.8 | 기록만 — `horizon_ess.py` 재실행은 B07 이후 연구 코드 배치에서 |

읽기 vs 실행: 전문·diff 판독 14/14 · 실행 3(`horizon_study.py` 재실행 · `eng_common` 1년 행 계산 · `watchdog.py --selftest` 계수) · 화면 문자열 변경이라 `verify_all` 전체 모드 실행.

### B06 research axis 1 (2026-09-05)

**세 줄 요약** — ① `axis_accum`·`axis_accum2`·`axis_b_inspect`·`axis_dca`·`axis_dca_grid`·`axis_defsel`(842줄)·`axis_dipbuy`·`axis_ens`·`axis_ext2`·`axis_ext2_probe`·`axis_external`·`axis_finalverify`(697줄)·`axis_forward` 13파일 4,167줄을 전문으로 읽었다. 본 것: 신호 계산이 전일까지만 쓰는가(shift/lag) · 적립 루프의 「전환 → 수익」 순서 · 검산이 실제 엔진을 지나는가 · 판정문이 계산값에서 나오는가 · 관문 표기와 실제 실행의 일치. 실행: 5편을 끝까지 돌려 내장 검산(accumulate 동치 · mix_dyn 동치 · 룩백 절단 · 경계값)을 확인했고 `axis_finalverify --selftest` 는 I14 가 돈다. ② **매매·판정에 닿는 결함 0 · 계산 결함 0.** v203(2026-09-04)이 이 배치의 인과 지연·부호·미검증=탈락 혼동·판정문 누락을 이미 고쳐 두었고, 그 수정이 코드에 그대로 있음을 확인했다. **단 적발 1건(P3)**: `axis_b_inspect` 를 v210 자료로 다시 돌리니 B 의 「동일 잣대」 관문 P3(독립 21사건창 MDD 승률 ≥70%)가 **62%(13/21)로 미통과**다 — 저장소 다섯 문서가 v203 값 「15/21=71% · 통과」를 들고 있다. 매매 규칙엔 무관하지만(동결은 이 관문의 결과가 아니라 결정) 「재난보험형」 서술의 근거 수치는 갱신 대상이다. 나머지는 P4(죽은 가지·모듈 수준 실행·하드코딩 판정문·달러 T-bill 을 원화 현금 다리로 쓴 표기·출력 서식). ③ 수정은 문서 병기 2곳뿐 — 나머지 인용처 3곳은 다른 세션의 미커밋 변경을 든 파일이라 **보류**(아래). 특기: `axis_dca_grid.dca_fast` 의 항등식(최종/납입 = mean(c[T]/c[t_m]))은 B03-2 가 `axis_lib.check_accum` 에 넣은 것과 같은 식이라, 그 검산이 이 저장소의 기존 관행과 일치함을 독립 확인한 셈이다.

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B06-1 | P3 | `research/axis_b_inspect.py` P3 관문 · 인용처 `FILES.md:405`(「15/21=71% … v203 교정 후 문턱 통과」) · `CLAUDE.md` v203 항목(「B 15/21=71%」) · `04` §5 서문(「70% 문턱을 통과한다」) · `research/MEASUREMENT_AUDIT.md` §7 · `research/NEW_STRATEGY_RESEARCH.md` | v210(FRED 빈 행 114 제거) 뒤 재실행 | **2026-09-05 재실행: B vs 2배보유 사건승 62%(21사건 중 13) · T4 vs 보유 90% → P3 미통과 · 종합 「기각」.** v203 기록(B 15/21=71% · T4 20/21=95%)과 다르다. 이 스크립트는 v203(d9606ed) 뒤 안 바뀌었고(git log) 그 사이 바뀐 것은 자료(v210)뿐이다. P1(비용 내성 ≤0.3% 전부 B>보유)·P2(B≥A)·P4(사각지대 최장 90일 ≤252)는 통과. 뜻: 「B 가 자기 잣대 P3 를 통과한다」는 사후 확인 문장이 현행 자료에선 성립하지 않는다 — **동결 규칙·장부엔 무관**(04 §5 서문 스스로 「사후 확인이지 채굴 아님」). ⚠ `04` §5-23 표의 「독립 71% (15/21)」은 별개 스크립트 `oos_protocol_b.py`(M1) 값이고 그 기저율 JSON(`data/oos_protocol_b.json`, I13 지문)은 v210 전 표본으로 등록돼 있다 — JSON 자체가 「엔진을 바꾸면 기저율도 다시 재야 한다」고 적어 두었다. **B14 에서 `oos_protocol_b.py` 를 재실행해 기저율 이동 여부를 본다**(움직였으면 지문을 의도적으로 갱신하고 02 §5-1 에 날짜·이유) | 실행 출력 `P3 … B vs 보유 62% (21사건)` · `X * P3 기전 실증 (사건승 ≥70%)` | **부분 처리** — `MEASUREMENT_AUDIT` §7·`NEW_STRATEGY_RESEARCH` 두 곳에 재실행값 병기(이 커밋). `FILES.md`·`CLAUDE.md`·`04` 세 곳의 정정 표시와 `retired_numbers.json` 등재(15/21=71%)는 **보류** — 세 파일이 다른 세션(v213)의 미커밋 변경을 들고 있어 내 변경만 떼어 커밋할 수 없다. 착지 뒤 후속 커밋(아래 「보류 정정」) |
| B06-2 | P4 | `axis_defsel.py` `s8_krw` `tb = H.tbill_daily(idx)` (원화 검증의 현금 다리) | 원화 §8 표에서 현금100·절대모멘텀의 현금 몫 | 달러 T-bill 금리를 환효과 없이 원화 현금 수익으로 쓴다(주석에 「대용·환효과 없음」 명시). 현금100 은 4위권 밖이라 판정에 무영향 | 코드 판독 | 기록만 |
| B06-3 | P4 | `axis_defsel.py` `s_cost` `ms = np.where(...) if False else [...]` | — | 죽은 가지(항상 else). 결과 무영향 | 코드 판독 | 기록만 — 정리는 값 없는 변경 |
| B06-4 | P4 | `axis_forward.py` episode 정의 루프의 두 번째 `k` while | — | j 가 이미 −16 위로 나간 뒤라 k==j 로 즉시 끝나는 죽은 루프 · `eps` 정의는 정확 | 코드 판독 | 기록만 |
| B06-5 | P4 | `axis_ext2_probe.py` | import 시 | 모듈 최상위에서 `DF.build`·전 계산이 돈다 · `sys.stdout.reconfigure` 가 try 밖 | 코드 판독 | 기록만 — 단독 실행 전용 스크립트 |
| B06-6 | P4 | `axis_accum.py:92-99` · `axis_ens.py:148-150` | — | 판정 문장이 하드코딩(v22 시절) — `research_kit.verdict` 이전 관행. 계산과 어긋난 문장은 없음(재실행으로 확인) | 실행 출력 대조 | 기록만 — HANDOFF §2 「판정문 하드코딩 금지」는 v38 이후 신규 파일에 적용 |
| B06-7 | P4 | `axis_finalverify.py` `audit_nav` | 2026-09-01~04 NAV 행 | 그 4행이 개장 직후 값(v206 P2)이라는 것은 이 감사가 잡을 수 없다(값 범위·괴리 정합만 본다) — J3 유효세션 수엔 포함됨 | v206 감사 대장 | 기록만 — 4행은 실측 장부(§2) |
| B06-8 | P4 | `axis_b_inspect.py` 판정 표 P1·P2 행 | — | `'%.1f%%에서 …'` 가 이중 이스케이프로 「0.3%%에서」로 찍힌다 — 표시만, 값은 맞다 | 실행 출력 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · 실행 6/13(`axis_ens`·`axis_dipbuy`·`axis_accum`·`axis_b_inspect`·`axis_dca_grid` 전체 + `axis_finalverify --selftest`) · 미실행 7(`axis_accum2` 12씨앗×6규약 · `axis_dca` · `axis_defsel` 플라시보 400회 · `axis_ext2`·`axis_ext2_probe`·`axis_external`·`axis_forward` 오라클 — 수십 분급 · 판독으로 대체, v204 가 61건 교정 때 재실행한 기록 있음).

**보류 정정 (다른 세션 v213 의 미커밋 변경을 든 파일 — 착지 뒤 후속 커밋으로)**: ⓐ `FILES.md:405` `axis_b_inspect` 행 「사건승 15/21=71% … v203 교정 후 문턱 통과」 → 「v210 자료 재실행 13/21=62% · P3 미통과 · 최장 90일」 ⓑ `CLAUDE.md` v203 항목 「B 15/21=71%」 옆 정정 표시 ⓒ `04` §5 서문 「15/21=71%로 등록된 70% 문턱을 통과한다」 정정 ⓓ `retired_numbers.json` 에 「15/21=71%」 등재(since v213 이후 번호) — 등재는 ⓐ~ⓒ 표시와 **같은 커밋**이어야 I9 가 안 깨진다.

### B07 research axis 2 (2026-09-05)

**세 줄 요약** — ① `axis_gate11`·`axis_hedge_cost`·`axis_horizon`·`axis_isa`·`axis_krreal_decomp`·`axis_krspec`·`axis_krspread`·`axis_lev`·`axis_macro`·`axis_macro2`·`axis_macro3`·`axis_macro4`·`axis_mech` 13파일 3,700줄을 전문으로 읽었다. 본 것: 지표가 과거만 쓰는가(z-score 롤링·`lagged_positions`·OOS 절단 뒤 상태 초기화 여부) · 판정문이 계산에서 나오는가 · 하드코딩 상수(창 끝 날짜·독립 사건 수·분배율) · `deploy/` 결합 방향. 실행 7편을 끝까지(`gate11`·`horizon`·`hedge_cost`·`krspec`·`krreal_decomp`·`lev`·`mech`) — 판정 전부 계산 생성이고 기존 결론과 같다(RV 상태변수 집중도 기각 · 메커니즘 27후보 G1~G6 0통과 · 실물 3.2년 A 우세는 우연 38% · 미국채선물 2종 환노출 · 헤지6/4 비용 선형 감쇠). ② **매매·판정에 닿는 결함 0 · 계산 결함 0.** 남은 것은 전부 P4: 독립 사건 수 9 를 `assert` 로 못 박아 자료가 바뀌면 진단 대신 죽는 구조(이번엔 9 그대로) · 창 끝 날짜 하드코딩 2곳 · 매크로 4편의 기준선이 규칙 A(−16/−11)인 v30~v32 산출물 · 지평 표 두 종의 규약 차이 · 방어 분배율 상수 · `deploy` 상수 읽기. ③ 수정 0 — 증거 기준 미달(§3).

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B07-1 | P4 | `research/axis_gate11.py:116` `assert r['n_indep'] == 9` | 자료 갱신 뒤 독립 사건 수가 9 에서 벗어날 때 | 사전 고정값이라 뜻은 있으나 벗어나면 진단 대신 AssertionError 로 죽는다(메시지에 행 목록은 담긴다). 2026-09-05 재실행 **9 → 통과** · 판정 「기각」 재현(갈린 사건 31 · 독립 9 · 상위 1개 제외 시 기여 +8.4%→−3.6% · 위기 하나씩 제외 1/8 유지) | 실행 | 기록만 — 값이 벗어나는 날 의도적으로 갱신 |
| B07-2 | P4 | `axis_lev.py:52` `'2026-08-24'` · `axis_macro4.py:269` `'2026-08-26'` | — | 구간 끝이 자료 끝(2026-08-28)보다 2~4일 짧다 — 마지막 며칠만 제외, 결론 무영향 | 판독 | 기록만 |
| B07-3 | P4 | `axis_macro.py`·`axis_macro2.py`·`axis_macro3.py`·`axis_macro4.py` 기준선 `(-0.16, -0.11)` = 규칙 A | — | v30~v32 산출물 · 머리 docstring 이 「초판/정정본」을 밝히고 04 §5 표도 그 시절 판정으로 인용. 매크로 필터 기각(5종 악화)은 **A 위에서 잰 것** — B 위에서 다시 재지 않았다는 사실을 인용 시 붙일 것(`axis_macro4` 는 −16/−16 도 같이 본다) | 판독 | 기록만 |
| B07-4 | P4 | `axis_horizon.py`(각 달 첫 거래일 시작 643창 · 편도 0.2%) vs `horizon_study.py`(매일 시작 11,985창 · 0.1%) | — | 같은 「지평별 배수」인데 규약이 달라 10년 중앙 **9.8 vs 10.79** · 20년 **101.8 vs 121.3** — 화면·설명서는 후자(B05-1). 두 표를 섞어 인용하지 말 것 | 실행 | 기록만 |
| B07-5 | P4 | `axis_hedge_cost.py:25` `from build_stats import HEDGE_W, STRATS` | — | 연구가 `deploy/` 상수를 읽는다(읽기만 · 쓰기 0). `g_isolation` 은 공유용 폴더만 보므로 관문 밖 — 방향은 허용(§2 「빌려쓰기 자유·쓰기 차단」) | 판독 | 기록만 |
| B07-6 | P4 | `axis_isa.py:59` `DIV_YIELD = 0.013` | — | 방어 바스켓 분배율을 상수(배당40%×3.3%)로 두고 국채·금 분배는 0 가정. v210 이 분해식(`rate/exempt` 분모)은 고쳤고 이 상수는 그대로 — 과세이연 몫(84%)의 절대값에 영향, 순위엔 무관 | 판독 | 기록만 |
| B07-7 | P4 | `axis_lev.py` §8 출력 「1972-2026」 세후 표 | — | 54년 통짜 세후 배수(ISA x2 225,943 등)가 콘솔에 나온다 — v131 규약은 문서·화면 머리가 대상이라 위반은 아니나, 문서로 옮길 땐 바로 위 21세기 표(2000-2026: ISA x2 137.0 · 해외 x3 164.9)만. ⚠ 그 21세기 값은 `tax_us_direct.py` 의 원화·실물보정 161.5/283.9 와 **규약이 다른 달러 모형**이라 병기 금지 | 실행 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · 실행 7/13 · 미실행 6(`axis_isa` 롤링 3지평×6모드 — v210 R04 가 재실행 · `axis_krspread` · `axis_macro`~`axis_macro3` 플라시보 200회·앙상블 — 수분급, 판독 대체).

### B08 research axis 3 (2026-09-05 · v214)

**세 줄 요약** — ① `axis_meta`·`axis_meta_crisis`·`axis_minimax`·`axis_momentum`·`axis_newrule`·`axis_nextgen`·`axis_objective`·`axis_regime`·`axis_rvstate`·`axis_secondary`·`axis_selbias`·`axis_selbias_disjoint`·`axis_sigsrc` 13파일 2,955줄 전문. 본 것: 점수·지표가 선택 시점 이전 자료만 쓰는가(`scorer(lo, i, i)` · expanding·shift(1)) · 상태머신의 「전환 → 그날 수익」 · 재현 앵커가 현행 자료와 맞는가 · 판정문 생성 · 하드코딩 상수. **13편 전부 끝까지 실행**했다. ② **매매·판정에 닿는 결함 0.** 그러나 **v210(FRED 빈 가격 행 114개 제거)이 이 배치의 숫자를 광범위하게 움직였고 한 편은 판정까지 뒤집었다**: `axis_nextgen` 이 v81 재현 앵커와 안 맞아 0단계에서 죽어 있었고(P2), 앵커를 현행 자료로 맞춰 돌리니 v87·v203 「N1~N8 전멸」이 **MIX(0.50) 통과**로 바뀌었다. 원인은 §-1 ⑧ 대로 한 열만 바꿔 확인했다 — v203·v209 작업트리가 옛 값을 소수점까지 재현하고 v210 작업트리가 현행 값을 재현한다. T4 가 +57.7% 움직인 것은 T4 의 자료 민감도 자체가 붉은 깃발이고, 통과자는 후반(2000~) 0.91×B · 혼합 하위호환 · v213 이 지적한 부분비중 표류 비용 **미교정** 경로 위의 값이다. ③ 수정: 앵커 갱신(옛 앵커 병기) · 문서의 v210 전 수치 4종 정정 표시+등재 · B06 보류분 3곳 표시(v213 착지로 해제). **채택 0 · 결론 변경 0 · 소유자 결정 항목 1(그림자 등록 논의 자격)**.

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B08-1 | P2 | `research/axis_nextgen.py:85` `V81` 재현 앵커(±1.5%) · 인용처 `FILES.md` nextgen 행 「N1~N8 전멸」 · `04` §5 서문(v81 혼합 평가 전용) | v210 뒤 실행 | ⓐ 스크립트가 0단계 `SystemExit('재현 실패')` 로 죽어 v87 결론을 재검증할 수 없었다(B +7.46% · T4 +57.68% · MIX25 +43.19%). ⓑ 앵커를 v210 값으로 맞춰 돌리니 **MIX(0.50) 이 N1~N8 전부 통과 → 판정 「채택(혼합 하위호환)」**. v209 작업트리에서는 같은 후보가 N1~N5·N7·N8 을 이미 통과하고 **N6(고원)만** 미달이었다 — 이웃 MIX(0.25) 의 N2(최종 ≥0.9×B)가 0.895×B 로 0.5% 모자랐던 것이 v210 에서 1.19×B 로 넘어갔다. 즉 「전멸」은 원래 종이 한 장 차이였다. 통과자의 한계: 후반 2000~ **0.91×B(진다)** · Calmar 0.447 < MIX25 0.481 · 회전 4.9/yr(B 2.5) · `axis_lib.sim` 은 부분비중의 **일일 표류 재조정 비용을 안 문다**(v213 R05 「미교정 사본」 목록) — 비용이 보수적이면 N2·N7 이 먼저 흔들린다 | 실행 3회(HEAD · v209 작업트리 · 앵커 갱신 후 전체) · `$S/repro_t4.py` 세 작업트리 대조 | **부분 수정** — 앵커를 `V210` 로 갱신하고 `V81` 은 병기(주석에 원인·재현 방법). **채택하지 않는다** — 파일 자신의 규약대로 「그림자 등록 논의 자격」 여부는 소유자 결정(04 §7 Q10 · FILES 행 정정). 반증(ⓐ)으로 v213 비용 경로 재측정은 B09(`axis_t4_shadow`) 뒤에 |
| B08-2 | P3 | T4 그림자 계열 전체 — `axis_t4_shadow.build('tbill')` 을 쓰는 모든 표(v80~v88 · 04 §5-11 · `data/oos_protocol_b.json` 기저율 · `axis_t4_krcost.py:23` 의 T4 0.2% 109,451 상수) | v210 뒤 | 같은 코드에서 자료만 바꿔 **T4 0.1% 163,161→257,279(+57.7%) · 0.2% 109,451→172,259**. B 는 +7.5%. 1972~85 의 가짜 0수익 행 114개(0.8%)가 T4 를 58% 움직인다는 것은 **T4 의 우위가 그 시대의 자료 품질에 걸려 있다**는 뜻 — 04 §5-11 의 「닷컴 한 사건 97%」와 같은 방향의 붉은 깃발 | 세 작업트리 실측(v203=v209 소수점 일치 · v210=HEAD 소수점 일치) | 기록 — **B09 에서 `axis_t4_shadow`·`axis_t4_krcost`·`axis_t4_synthcrash` 재실행 뒤 문서 정정** · B14 `oos_protocol_b` 기저율 |
| B08-3 | P3 | `01`:58 · `02`:98·142 · `04`:34·229·238·265·399·1142·1311·1341·1364·2155·2471 · `CLAUDE` 4곳 · `FILES`:363·405 · `README`:237 · `FINAL_AUDIT`:53 | v210 뒤 | 재실행값과 다른 수치 4종: 미니맥스 **3위/210·최악 126위 → 1위·94위**(`axis_minimax`) · v18 미관측 28년 **상위 79% → 90%**(22위 · `axis_selbias` T2) · 메타 **Oracle +288% → +251%** · 포착 **0~−28% → −32%~+8%**(E 미니맥스 +8% · 통과 0 · `axis_meta`) · `axis_b_inspect` P3 **15/21=71% → 13/21=62%**(B06-1 보류분). 결론은 전부 동일 | 실행 출력 | **수정** — 전 인용처에 재실행값·정정 표시, `retired_numbers.json` 4종 등재(since v214), 역사 문서 5편 배너. `04`:1335 의 「46위」는 `thresh_window.py` 표라 **B15 재실행 뒤** |
| B08-4 | P4 | `axis_rvstate.py:274` G11 검사 문자열 하드코딩(`axis_gate11.py` 결과를 글자로) | gate11 결과가 바뀔 때 | 다른 파일의 판정을 문자열로 박아 두었다 — 이번 재실행에서 gate11 은 「기각」(독립 9 · 상위 1개 제외 시 −3.6%)이라 아직 일치. 기록만 | 실행(B07-1·B08) | 기록만 — 바뀌면 이 줄도 같이 |
| B08-5 | P4 | `axis_momentum.py` ④ 사다리(부분비중) `curve_of`·`loop_dca` | — | 부분비중을 「매일 목표로 무비용 재조정」으로 모형화(머리에 명시) — 검산 ②도 같은 가정이라 경제성은 검증 안 됨. v213 R05 「미교정 사본」 계열. 사다리는 어차피 전 관문 탈락이라 **보수적 방향**(비용을 더 물리면 더 진다) | 판독 | 기록만 |
| B08-6 | P4 | `axis_meta.py:75` · `axis_minimax.py:53` · `axis_selbias.py:58·104` · `axis_selbias_disjoint.py:42` `'2026-08-26'` | — | 창 끝이 자료 끝(08-28)보다 2일 짧다 — 결론 무영향 | 판독 | 기록만 |
| B08-7 | P4 | `axis_selbias_disjoint.py` · `axis_meta_crisis.py` · `axis_minimax.py` | import 시 | 모듈 수준에서 전 계산 · `selbias_disjoint` 는 `axis_selbias` T3b 와 **같은 계산의 사본**(0/4 동일) | 실행 | 기록만 |
| B08-8 | P4 | `axis_newrule.py` 판정 | — | 격자 −12/−7·−13/−12·−12/−11·−12/−5 가 Calmar +10.4~11.6% 로 문턱(10.2%)을 넘되 **좌측꼬리(20년 p05 18.6~22.5 vs 36.8) 탈락** → 기각 — v41 결론 그대로 | 실행 | 기록만 |
| B08-9 | P4 | `axis_objective`·`axis_regime`·`axis_secondary`·`axis_sigsrc` | — | 재실행 결론 동일(−15/−15 3/6 · 메타 M1~M4 전부 좌측꼬리 탈락 · B/A 1.28 역전 슬리피지 1.0% · QQQ 신호원 유지 채택). 숫자는 소폭 이동(§5-22 S15 신호 재확인) | 실행 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · **실행 13/13**(+ 세 작업트리 대조 3회 · nextgen 앵커 갱신 후 재실행). 화면 문자열(notes.html) 변경이라 `verify_all` 전체 모드.

**소유자 결정 항목**: `axis_nextgen` 통과자 MIX(0.50) 의 「그림자 등록 논의」 개시 여부. 권고는 하지 않는다 — 다만 판단 재료로 「v210 이전엔 0.5% 차이로 미달 · 후반 0.91×B · 비용 미교정」을 같이 봐야 한다(§-1 ⓐ: 통과했을 때가 가장 위험하다).

### B09 research axis 4 + audit·b (2026-09-05 · v215)

**세 줄 요약** — ① `axis_t4_krcost`·`axis_t4_shadow`(487줄)·`axis_t4_synthcrash`·`axis_vixstate`·`axis_vrhybrid`·`axis_wide`·`axis_wide_probe`·`audit_exec`·`audit_pbo`·`audit_stat`·`b_adversarial`·`b_gate_noise`·`build_crisis_paths` 13파일 3,194줄 전문 + **13편 전부 실행**(`audit_pbo` CSCV 70분할 · `b_gate_noise` 1,000이웃 포함). 본 것: 재현 앵커가 현행 자료와 맞는가 · 판정문 생성 · 미래참조(사건창 저점 탐색은 진단용인가) · 산출물이 배포되는 `build_crisis_paths` 의 동치 검증. ② **매매·판정 결함 0.** B08 과 같은 병이 둘 더 — `axis_t4_shadow` A-1(v68 앵커)·`b_gate_noise` setup(217,110 앵커)이 v210 뒤 죽어 있었다(P3). **설명서 ⑪ T4 성적표는 v80 값**이라 화면이 낡았다(P2) — T4 최악 낙폭·Calmar·「최종배수는 채택안 +5%」 문장·사건 방어 승률(95/71). ③ 앵커 2개를 v210 기준으로 갱신(옛 값 병기) · 설명서 표·문장 재계산 · FILES 2행 · 04·CLAUDE 표시. **결론 변경 0 · 채택 0.** `build_crisis_paths` 산출물은 날짜만 바뀌고 값 diff 0(us_2000 레시피는 1972~85 행에 안 걸린다) — 복원했다.

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B09-1 | P2 | `guide.html` ⑪ 「성적표」 표 3행 + 아래 문단 2개 | v210 뒤 | 화면이 v80 값: T4 최악 낙폭 −53.4% → **−50.9%** · Calmar 0.392/0.461 → **0.394/0.503** · 「최종배수는 이 잣대에서 채택안이 소폭(+5%) 앞서며」 → 실제는 **비용에 따라 갈린다**(0.1% T4 +40% · 0.2% +8% · 0.3% 채택안 +17%) · 「사건 방어 승률 95% vs 71%」 → **90% vs 62%**(19/21 vs 13/21) · 닷컴 −47 vs −53 → −47 vs −51. 1987 −46% 와 「21번 중 76% 사전 감속」은 그대로 | `axis_t4_shadow` 재실행 sec A(V68_END 창)·sec B | **수정** — 표·문장 재계산값으로, 「2026-09-05 재계산」 명시 · T4 가 비용에 민감한 이유(회전 3배) 한 줄 |
| B09-2 | P3 | `research/axis_t4_shadow.py:70` `V68` 앵커 · `research/b_gate_noise.py:72` `assert abs(fin - 217110.075)` | v210 뒤 실행 | 전자는 A-1a/A-1b 가 실패해 「구현·기록 건전성 기각」이 찍힌다(A-2 장부 동치 250세션 0건·A-3 는 통과 — 즉 장부 구현은 멀쩡하고 앵커만 옛 자료) · 후자는 setup() 에서 AssertionError 로 **파일 전체가 안 돈다** | 실행 | **수정** — `V210` 앵커(같은 종료일 재현값) + v68 병기 · `b_gate_noise` 앵커 220,985.206(`strategy_stats.json` us_1972 B) + 주석. 재실행: t4_shadow **A 4/4 통과 확인**(MDD 오차 −0.03%p · 최종 0.0%) · gate_noise N2 4씨앗 p95 +8.8~+9.1% · 0/4 · ①②③ 0/800 — 04 §5-29 결론 동일 |
| B09-3 | P3 | T4 계열 문서 수치(B08-2 후속) — `FILES.md:403`·`CLAUDE` v203 항목 「T4 20/21=95%」 | v210 뒤 | 재실행 M2 19/21=90% · M1 16/21=76%(동일) · M1∧M2 14/21=67%(동일) | 실행 | **수정** — 표시 |
| B09-4 | P4 | `research/audit_stat.py` [2] 잭나이프 | — | mix40−B 의 **Δp05 부호가 연도 11개 제거에서 뒤집힌다**(1990·1999·2003·2009·2012~14·2017·2019~21) · DSR 0.02~0.07 · 비중첩 20년 2.7 — 혼합 고원의 p05 우위는 소수 연도에 매달려 있다. 04 §5-3 「채굴 산물 가능」 방향 그대로 | 실행 | 기록만 |
| B09-5 | P4 | `research/audit_pbo.py` | — | v210 재실행 PBO Sharpe 0.029(전체)/0.357(혼합만) · Calmar 0.514/0.586 — FILES 의 「0.49~0.53」은 Calmar 쪽. IS 1등은 gatesA/T4/합의체가 번갈아 — 「1등 고르기 = 동전던지기」 결론 동일 | 실행 | 기록만 — FILES 행에 병기 |
| B09-6 | P4 | `research/axis_t4_krcost.py:23-24` docstring | — | K1·K2 괄호 숫자(109,451 · −54.7%)가 v210 전 값 — 코드는 refs 를 실행 시점에 다시 재므로 판정(전멸)엔 무관 | 판독·실행 | **수정** — docstring 에 재실행값 병기 |
| B09-7 | P4 | `research/axis_vrhybrid.py:244` `'2026-08-24'` · `axis_t4_shadow` C 절 3년 창 「승률 62%」 | — | 창 끝 하드코딩(자료 끝 08-28) · C-3 「3년 판정 판별력」은 v80 때도 미통과였던 규약 품질 검사(보강은 소유자 결정 사항이라 보고만) — 재실행 62%/59% | 실행 | 기록만 |
| B09-8 | P4 | `research/axis_t4_synthcrash.py` S1e · `axis_vixstate.py` · `axis_wide*.py` · `b_adversarial.py` | — | 재실행 결론 전부 동일: 합성 생성기 S1b~e 미통과(진단 전용) · S2 전반 90%/후반 91% · S3 ¼ 양자화 −4.1% · S4 x=0.125·0.25 · VIX S1 5지표 우위지만 4블록 불가 · 광역 0/48(G 4/6 최고) · G 첨탑(이웃 2/5·MDD −63.3%) · B 무작위 귀무 백분위 97.1% | 실행 | 기록만 |
| B09-9 | P4 | `research/build_crisis_paths.py` | — | 재실행 산출물 값 diff 0 · `generated` 날짜만 변경 → 복원. 검증 ① final 167.315 == 공표 · 4위기 400일 | 실행 · `git diff` | 기록만 — 배포 산출물 무변경 |

읽기 vs 실행: 전문 판독 13/13 · **실행 13/13**(`b_gate_noise` 는 앵커 갱신 뒤 재실행 · `axis_t4_shadow` 는 앵커 갱신 뒤 재실행해 A 4/4 통과 확인). 화면(guide·notes) 변경이라 `verify_all` 전체 모드.

### B10 research c~e (2026-09-05)

**세 줄 요약** — ① `c3_falsify`·`c3_placebo`·`cand_general`·`complement_sleeve`·`def_bond`(364줄)·`def_equity`(360줄)·`drag_sigma`·`dsr_b`·`emit_dd_distribution`·`eng_common`(공용 엔진 · 30여 파일이 import)·`eng_kospi`·`eng_sp500`·`era_start` 13파일 2,540줄 전문 + **13편 전부 실행**. 본 것: `eng_common.sim2` 의 지연·회전 과금(v213 `daily_turnover` 경유 — 이진 w 에서 |Δpos| 와 동치인지) · 한국 마감 시각의 미래참조(`_us_curve_known_at_korea_close`) · 재현 앵커 · 배포 산출물 `dd_percentile.json` 의 동치 · 사전 등록 예측의 대조. ② **매매·판정 결함 0 · 계산 결함 0.** 검산 전부 통과(selfcheck rule_dd==wB · sim2==three_way 0오차 · B 공표 220,985.206 재현 · def_bond 부품 조립 0오차 · def_equity 선형식 vs accumulate · era_start 84.3 · emit_dd 산출물 diff 0). **v210 뒤 움직인 것**: C3(÷T-bill 낙폭)의 관문 수치가 Calmar +13.4→**+10.5%** · p05 +26.1→**+1.7%** 로 내려앉았고 플라시보 기준선(절단 350일)에선 **① 자체 미달(+9.8%)** — 「우연과 구별 불가 → 닫음」 결론은 그대로이고 오히려 강해졌다(P3 · 문서 3곳 병기). ③ 수정: 04·EXPLORATION 의 C3 수치 3곳에 재실행값 병기. **결론 변경 0.**

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B10-1 | P3 | `04`:2051(§5-29 b) · `research/EXPLORATION.md` 머리·§B-2 표·G1/G3 표 | v210 뒤 | C3 Calmar +13.4→+10.5% · 20y p05 +26.1→+1.7%(41.7 vs 41.0) · 최종 1.07→0.80× · 플라시보(공통 절단 350일) C3 +9.8%/+2.4% 로 ① 미달 · G1 ①② 1.0→1.5% · G3 뒤섞은 T-bill 「C3 만큼」 13→25% · ①② 27→14.5%. 결론(닫음) 동일 | `c3_falsify`·`c3_placebo` 재실행 | **수정** — 3곳 병기 |
| B10-2 | P4 | `research/def_equity.py` 판정 | v210 뒤 | 사전등록 관문 「현행 유지 조건 **실패**」(주식0 50/50 P5 +6.2% · P20 +6.0%) — v204 가 이미 「배당 −40·국채 +10·금 +30 을 동시에 바꿔 인과 미식별」로 판정을 유지했고 04 §5-15C·§5-17 이 그 기록. 무작위 300 배합 현행 37백분위 · 실제 체결 구간 방어 최악 −24.5% | 실행 | 기록만 |
| B10-3 | P4 | `research/cand_general.py` | — | B×T4 고원 7칸(x 0.30~0.60) · C1/C2 대조군 0칸(디레버리징 아님) · WFA 1992~ 1,664 vs B 6,112(x* 0.05→0.25 표류) — 04 §5-3 방향 동일 | 실행 | 기록만 |
| B10-4 | P4 | `research/emit_dd_distribution.py` → `data/dd_percentile.json`(배포) | — | 재실행 산출물 diff 0(v210 때 다른 세션이 재생성한 것과 일치 · n 13,749 · −16% 보다 깊었던 날 19.36%) | 실행 · `git diff` | 기록만 |
| B10-5 | P4 | `research/eng_common.py:55` `sim2` → `rebalance_accounting.daily_turnover` | — | v213 이 회전 과금을 표류 포함으로 바꿨다 — 이진 w 에선 |Δpos| 와 동치(selfcheck sim2==three_way 0.0e+00 · B 공표 재현) · 부분 비중 호출자(`c3_*`·`liquid_*`)는 v213 R05 범위 | 실행 | 기록만 |
| B10-6 | P4 | `research/era_start.py:94` `84.3` · `research/c3_placebo.py`·`era_start.py` 모듈 수준 실행 | — | 2010~ B@2 84.3 재현(v210 은 1985 이전만 바꿔 무영향) · 두 파일은 import 만 해도 전체 계산이 돈다(단독 실행 전용) | 실행 | 기록만 |
| B10-7 | P4 | `research/def_bond.py`·`eng_kospi.py`·`eng_sp500.py`·`dsr_b.py`·`drag_sigma.py` | — | 재실행 결론 동일: 만기 축은 금리 국면 경사면(현행 유지 · ust5_cash 대조군만 ②+1.9%) · KOSPI2x 54칸 0 · SPX2x 54칸 0(WFA 63.5 vs B 6,112) · B Sharpe 1/153 · DSR 1.000 · κσ² 시변 드래그 +39.9%(합성 구간만 · 2000~ +0.5%) | 실행 | 기록만 |
| B10-8 | P4 | `research/complement_sleeve.py` | — | 2011~ 공통창 표 재현(필수소비 폭락일 상관 +0.610 · SCHD +0.749 · 헬스케어 수익/변동성 0.85) — §5-37 그대로 | 실행 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · **실행 13/13**(`def_equity` 무작위 300×3 포함).

### B11 research e~h (2026-09-05)

**세 줄 요약** — ① `exec_cost`·`ext_ibs`·`ext_vr`·`factcheck_qld_talk`·`forecast_check`·`free_design`(392줄)·`frontier2`·`goal_feasibility`·`hedge_ratio_scan`·`hist_defchain`·`hist_defdiag`·`hist_defrun`·`hist_fetch` 13파일 2,411줄 전문. 본 것: 외부 계열의 미래참조(ffill 만·bfill 금지) · 사전 등록 예측의 대조 · 재현 앵커 · 배포 산출물 생산자(없음 — `exec_cost` 는 파수꾼이 읽기만) · 네트워크 코드의 가드. **12편 실행**(`hist_fetch` 는 원자료 다운로더라 안 돌렸다 — `save_guarded` 의 10%·날짜 후퇴 가드와 원자 교체를 판독). ② **매매·판정 결함 0 · 계산 결함 0.** 사전 등록 예측 대조 전부 문서와 같다: `free_design` 3/3 실패(X2 만 0.997→1.013× 로 v210 뒤 소폭 이동 · 실패 동일) · `frontier2` P4 맞음(θ=15% 환 오버레이 ①−②③ · X3 갈린 사건 176) · `forecast_check` P1~P4 맞음 · `hedge_ratio_scan` 검산(21세기 QLD100% 167.3 · QLD60% 63.0) 재현 · `goal_feasibility` 5년 10억 달성 국면 1개. ③ 수정: 주석 1곳(`goal_feasibility` 옛 217,110 앵커 문구) · `04`·`CLAUDE` 의 X2 0.997× 에 재실행값 병기. **결론 변경 0.**

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B11-1 | P4 | `research/free_design.py` X2 · 인용처 `04`:1713 · `CLAUDE` v187 항목·v196 항목 | v210 뒤 | 최종/R 0.997× → **1.013×**(ΔMDD −1.3p · ② 4블록 X · ④ 홀드아웃 X 로 실패 동일). X1 0.711 · X3 0.005 는 소수점까지 그대로 | 실행 | **수정** — 세 인용처에 재실행값 병기 |
| B11-2 | P4 | `research/goal_feasibility.py:50` 주석 | — | 「final 217110 / Calmar 0.418」 — v210 뒤 220,985.206. 코드는 `strategy_stats.json` 을 읽으므로 동작엔 무관 | 판독 | **수정** — 주석 |
| B11-3 | P4 | `research/exec_cost.py` NAV 괴리 표 | 2026-08-26~09-04 8영업일 | 그 중 09-01~04 4행은 v206 P2(개장 직후 값) — 괴리 통계에 섞여 있으나 판정 표본(체결일 0/20)이 아니고 60일 관문도 미달이라 무영향. `nav_collect` v206 수정 뒤 행부터 종가 | 실행 · v206 감사 | 기록만 |
| B11-4 | P4 | `research/ext_ibs.py`·`ext_vr.py` | — | 외부 전략 근사(종가 체결·LOC 근사·소수점 주식) — 2000~ 창에서 무한매수 0.30× · VR 0.52×(닷컴 재난) · 2010~ 창 VR/10 229배(MDD −80%) vs B 84배(−45%). 04 외부 절과 방향 동일 · 근사 한계는 docstring 에 명시 | 실행 | 기록만 |
| B11-5 | P4 | `research/hist_defchain.py`·`hist_defdiag.py`·`hist_defrun.py` | import 시(`defdiag` 모듈 수준) | v20 시절 A/B 방어자산 대체 스크립트 — 결과는 현행 문서와 무관한 역사 기록. `defdiag` 는 모듈 수준 실행 | 실행 | 기록만 |
| B11-6 | P4 | `research/frontier2.py` X1 θ=15% | — | ①− ②③ 통과(Calmar +5.3% · p05 +46%) — 예측 P1 「①②③ 미달」 맞음. 헤지 교체 편도 회전 과금(`_overlay_extra_turn`) 검산 3건 통과 | 실행 | 기록만 |
| B11-7 | P4 | `research/hist_fetch.py` | 네트워크 | 미실행. `save_guarded`: 행 10% 감소·마지막 날짜 후퇴 시 거부 · 임시파일 후 `os.replace` · LBMA 도 try 안(v204) — 판독 OK | 판독 | 기록만 |
| B11-8 | P4 | `research/hedge_ratio_scan.py` · `forecast_check.py` · `factcheck_qld_talk.py` | — | 재실행 결론 동일(검산 재현 · P1~P4 맞음 · 슬라이드 ⑤ 표 = S&P 패턴). `hedge_ratio_scan` 은 `deploy/build_stats` 의 HEDGE_W·STRATS 를 읽기만(B07-5 와 같은 방향) | 실행 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · 실행 12/13(`hist_fetch` 제외 — 네트워크 다운로더).

### B12 research h (2026-09-05)

**세 줄 요약** — ① `hist_krtax`·`hist_three`·`horizon_ess`·`horizon_study`·`hypo_escape`·`hypo_external2`·`hypo_gates`(213줄 · 6편이 import 하는 재료 모듈)·`hypo_hex`·`hypo_t4_real`·`hypo_t4wide`·`hypo_verify`·`hyst_signal`·`hyst_sigwfa` 13파일 1,770줄 전문. 본 것: 미래참조(`sig_trend/sig_vol` shift(1) · 학습 라벨 purge · WFA 경계 상태 `state_before`) · 3-way 엔진의 회전 과금(`daily_turnover`) · 퇴화 검산(혼합 x=1==B · x=0==T4 · 발동 0==B) · 재현 앵커. **12편 실행**(`horizon_study` 는 B05 에서 재실행). ② **매매·판정 결함 0 · 계산 결함 0.** 검산 전부 통과(hypo_hex 퇴화 2건 · t4_real 장부 대조 (3, 36.7, 1.0) · 벡터화 20일 · 멀티엔진 0오차 · hypo_gates 퇴화·월간 복원 · horizon_ess [0] 6지평 OK · hist_krtax 세율 0 축퇴). 관문 결과는 문서와 같은 방향(escape 0/12 · external2 0/8 · t4wide 0/3 · gates ① 통과·② 탈락). **v210 뒤 움직인 것 둘**: `hypo_hex` 혼합 x=0.50·0.55 가 두 정의 동시 통과(그림자 후보 논의 대상 — B08-1 MIX(0.50) 과 같은 대상 · 채택 아님) · T4 정본 1978~ 공통창에서 B 의 0.50×(1972~ 전창에선 1.40×) — B08-2 「T4 우위는 1972~77 자료에 걸려 있다」의 직접 증거. ③ 수정: 주석 1(hypo_verify 옛 217,110 앵커) · MEASUREMENT §1 유효표본 표에 재실행값 한 줄 병기(B05-8 해소). **결론 변경 0.**

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B12-1 | P3 | `research/MEASUREMENT_AUDIT.md` §1 표 (B05-8 후속) | v210 뒤 | 겹친 창 −114 · 비중첩 7.9→7.8 · 20년 AR-ESS 9.7→10.4 · 최악5% 사건수 5년 5→4 · 10년 4→3 · 15년 6→3. 결론(7년 문턱은 소수 사건 통계 · 견고한 0 은 15년) 동일 | `horizon_ess.py` 재실행 | **수정** — 표 아래 재실행값 병기 · §8 「7.9개」 옆 7.8 |
| B12-2 | P4 | `research/hypo_t4_real.py` 공통창 1978~ | — | **T4 정본 77,479 vs B 153,821 = 0.50×**(Calmar 0.488 vs 0.460 · p05 27.5 vs 58.6). 1972~ 전창(B08)에선 T4 257,279 vs B 183,542 = 1.40×. 즉 v210 뒤 T4 의 총수익 우위는 **1972-02~1977-12 여섯 해**에서 나온다 — B08-2·B09-2 의 「자료 품질 민감」 판단을 지지. 04 §5-11 의 T4 서술을 다시 쓸 때 창을 붙일 것 | 실행 | 기록만 — B14/B15 뒤 04 §5-11 정정 시 반영 |
| B12-3 | P4 | `research/hypo_hex.py` 부록 혼합 전선 | v210 뒤 | x=0.50·0.55 「두 정의(p05·p20) 동시 통과」(v?? 실행 땐 x=0.40~0.55 ①·p20 만 · p05 X). B08-1 의 `axis_nextgen` MIX(0.50) 통과와 같은 현상 · 같은 한계(비용 미교정 경로 · 후반 열세) | 실행 | 기록만 — 소유자 결정 항목(B08)에 포함 |
| B12-4 | P4 | `research/hypo_verify.py:6-7` 주석 · [검증D] | — | 주석의 「final 217110.075」는 v210 전 값 · [검증D] 는 T4 1978~ 창 77,479 를 v68 54년 공표 155,279 와 나란히 찍어 −50% 「잔차」로 보이나 **창이 다르다**(같은 창 재현은 `axis_t4_shadow` A-1 이 담당) | 실행 | **수정** — 주석에 v210 값 · 검증D 는 「창이 다르다」가 코드 주석에 이미 있어 그대로 |
| B12-5 | P4 | `research/hyst_wfa.py`·`hyst_sigwfa.py`·`hyst_signal.py` | — | v20 시절 WFA — `state_before` 로 학습창 경계 상태를 리셋 안 함(v204) ✓ · `hyst_wfa` 는 실행 시 루트의 `hyst_wfa.csv`(추적 파일)를 다시 쓴다 → B13 실행 뒤 diff 확인 | 판독·실행 | 기록만 |
| B12-6 | P4 | `research/hypo_gates.py` `sim_multi` 부록 `TARGET` 전역 덮어쓰기(`g['TARGET']=0.40`) · `hypo_t4wide` 도 같은 방식 | — | 전역 상수를 실행 중 바꾸고 되돌린다 — 예외가 나면 0.40 이 남는다. 단독 실행 스크립트라 실해 없음 | 판독 | 기록만 |
| B12-7 | P4 | `research/hist_krtax.py` | — | 세후 B/A +19.9%(일반계좌) · 과세이연 +21.7% — 순서 「전환 → 그날 수익」·세율 0 축퇴 검산 v203 그대로 | 실행 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · 실행 12/13(`horizon_study` 는 B05 재실행분 재사용).

### B13 research h~n (2026-09-05)

**세 줄 요약** — ① `hyst_wfa`·`isa_pension`·`japan_stress`·`lev_5y`·`lev_opt`·`lev_signal_source`·`lev_th`·`liquid_design`·`liquid_iter`·`lookback200`(288줄)·`mdd_target`·`ml_policy`(학습기 · 라벨 purge)·`near_zone`(파수꾼 `near` 의 근거) 13파일 2,909줄 전문 + **13편 전부 실행**. 본 것: WFA 학습창 경계·라벨 purge(`ml_policy` 136개 제외 검산)·재현 앵커·사전 등록 예측 대조·파수꾼 근거 수치. ② **매매·판정 결함 0 · 계산 결함 0.** 검산 전부 통과(selfcheck 220,985.206 · `lev_th` T4 k=2 일반화 0오차 · `ml_policy` purge 136 · `lookback200` 격자 표 14/15). **v210 뒤 움직인 것 셋** — 원인은 세 작업트리(v203·v209·v210)로 한 변수씩 갈랐다(§-1 ⑧): ⓐ 룩백 200 의 표본 내 우위 수치(20년 창 승률 100→**78%** · 갈린 사건 5/8→**3/7** — v209 까지 문서와 일치 · v210 에서 어긋남 = **자료 정정 단독**), ⓑ 기계 정책의 낙폭 계열 재발견 3/45→**14/45**(v203 3 · v204 라벨 정정 H02·M05 뒤 **13** · v210 뒤 14 = **v204 가 코드를 고치고 문서 수치를 안 옮긴 것** — 「실행은 됐는데 기록이 안 따라온」 v148 유형), ⓒ `hyst_wfa` 복귀선 WFA(v209 = v204 기록 47,724/54,966/111,166 그대로 · v210 47,384/**38,578/79,845** · 50→49구간 = 자료 정정 단독). **결론은 셋 다 그대로**(200 은 사전 근거 없음·유지 / 재발견 못 함 / v20 진단). ③ 수정: 04 10곳 · CLAUDE 5곳 · EXPLORATION·FILES·LEVERAGE_US 각 1곳 병기 · docstring 2 · 추적 산출물 `hyst_wfa.csv` 재생성 커밋(v204 선례). **결론 변경 0.**

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B13-1 | P3 | `research/lookback200.py` · `04` §5-14 D(:848)·§5-23 D(:1619)·§5-25(:1790-1791·:1833) · `CLAUDE` 룩백200 항목 | v210 뒤 | 격자 표 15/15→14/15(54년 행 252 순위) · 전 시작일 20년 승률 **100%→78%**(중앙 1.209→1.164 · p05 1.058→0.890) · 7년 85→60% · 10년 92→68% · 갈린 독립 사건 **8(5승 p=0.73)→7(3승 p=1.00)** · 비독립 35건 22승→33건 16승. CSCV PBO 0.129 · 타 시장 0/4 그대로. 「200 이 낫다」의 표본 내 근거가 v210 뒤 더 약해짐 — §5-25 결론(유지) 동일·강화 | 재실행 · wt209 일치·wt210 어긋남 | **수정** — 04 5곳·CLAUDE 2곳 병기 · docstring 검산 문구 |
| B13-2 | P3 | `research/ml_policy.py` · `04`:2073(§5-29 d) · `research/EXPLORATION.md`:166 · `CLAUDE` 탐구 항목 · `FILES.md`:460 | v204 뒤 | 낙폭 계열 재발견 **3/45(7%) → 13/45(v204) → 14/45(31%, v210)**. M1 0.02→0.08×B · M3 Calmar 0.103→0.109 · P1·P2·P4 틀림·P3 맞음 그대로. v204 H02(63일 라벨 purge)·M05(이중 지연 제거)가 값을 옮겼는데 세 문서가 옛 3/45 를 들고 있었다 | wt203 3 · wt209 13 · wt210 14 | **수정** — 4곳 병기(결론 동일) |
| B13-3 | P4 | `research/mdd_target.py` · `04` §5-35(:2623·:2637·:2639) · `CLAUDE` §5-35 항목 | v210 뒤 | 현행 20년 p05 34.7→36.6 · 10년 중앙 10.0→10.8 · 금 80% p05 비 0.84→0.89 · 현금 80% 0.78→0.76(27.9배 · 값 20~22%→24%) · 순위 금 > 배당 > 현금 > 바스켓 > 국채=배율 > 문턱 **동일** · 문턱 −11.5 전환 272→268 | 재실행 | **수정** — 4곳 병기 |
| B13-4 | P4 | `research/near_zone.py` · `04` §5-8(:447-450) · `CLAUDE` v192 · `deploy/watchdog.py`:47-48·:442 주석 | v210 뒤 | 근접 진입 연 3.5→3.4 · 20일 안 전환 55→**60%** · 전환 140/138→138/136(99%) · 헛걸음 1.6→1.4 · NDX 교차 3.8/56/99 동일. 알림 설계 판정 동일. `watchdog.py` 는 **주석 2곳**만 옛 값(동작 무관 · deploy 무수정) | 재실행 | **수정** — 04·CLAUDE 병기 · watchdog 주석은 그대로(기록) |
| B13-5 | P4 | `research/hyst_wfa.py` → 루트 `hyst_wfa.csv`(추적 산출물) · `research/CODE_REVIEW_2026-09-05.md`:29-30(v204 기록) | v210 뒤 | 5년 학습·1년 평가 **50→49구간** · 선택형 47,724→47,384 · 고정 A 54,966→**38,578** · 고정 B 111,166→**79,845**(WFA>A 13/50→14/49). 1976-12 시작 격자가 v210 거래일 정정으로 움직인 것(wt209 = v204 기록 소수점 일치). v20 시절 진단이라 현행 판정 무관 | 재실행 · wt209/wt210 | **수정** — `hyst_wfa.csv` 재생성 커밋(v204 선례) · v204 기록 줄은 다른 세션 문서라 여기 대장에만 |
| B13-6 | P4 | `research/liquid_design.py`·`liquid_iter.py`(v207 교정 뒤) | — | 사전 등록 대조: design P1·P3·P6 맞음 / P2·P4·P5 틀림 · iter P1·P2 맞음 / P3 틀림 / P4 부분 · **①②③ 동시 통과 0 · 보류 창 ①② 통과 0** — EXPLORATION F5 −30.9% 등 v207 표와 일치(1994~ 창이라 v210 무영향) | 실행 | 기록만 |
| B13-7 | P4 | `research/lev_th.py`·`lev_opt.py`·`lev_5y.py`·`lev_signal_source.py`(:21 docstring) · `research/LEVERAGE_US.md`:304 | v210 뒤 | `lev_th` 54년 k* = **1.9 ← 동결 2.0 일치** · 모든 k 에서 −16 봉우리 · `lev_signal_source` −48@3x 2.69M/0.441→2.20M/0.438 vs 현행 3.10M/0.398→3.22M/0.403(환산 −46.1→−45.8%) 「격자 이웃 잡음 안」 동일 · `lev_opt`/`lev_5y` 표는 LEVERAGE_US 의 B05 v210 배너 범위 | 실행 | **수정** — docstring·LEVERAGE_US:304 병기 |
| B13-8 | P4 | `research/isa_pension.py`·`japan_stress.py` | — | 연금 이체: 세전 배수비 중앙만 출력·세후 우열은 v204 철회 그대로 · 니케이 1989 고점 시작 0.52배(§5-26) — 「다른 지수·다른 통화 · 판정 아님」 문구 그대로 | 실행 | 기록만 |

읽기 vs 실행: 전문 판독 13/13 · **실행 13/13** · 원인 가르기 재실행: `lookback200` wt209·wt210 · `ml_policy` wt203·wt209·wt210 · `hyst_wfa` wt209·wt210.

### B14 research n~s (2026-09-05)

**세 줄 요약** — ① `new_paths`·`oos_protocol_b`(파수꾼 `check` 가 매주 돌리는 평가기)·`ops_risk`·`pbo_thresh`·`plan30_withdraw`·`post_dotcom`·`q1_physical_bond`·`q2_hedged_attack`·`q5_near_presell`·`recovery_speed`·`schd_qqq_overlap`·`slice_scan`·`surv_alert`(감시 밴드의 근거) 13파일 2,770줄 전문 + **13편 전부 실행**(`oos_protocol_b` 는 기본·`--oos` 둘 다). 본 것: 등록 규약의 지문·자기검산·파수꾼 연결 · 사전 등록 예측 대조 · 하드코딩 판정문 · 네트워크 코드의 캐시 가드 · 감시 밴드 원천. ② **매매·판정 결함 0 · 계산 결함 0.** 그러나 **운영 결함 1(P1)**: v210 자료 정정 뒤 B 판정 규약의 등록 기저율이 역사와 어긋나 평가기가 「판정 중단」을 내고 있었고, 다음 월요일(2026-09-07) 파수꾼이 「기저율 표류」 경고를 낼 상태였다 — 세 작업트리로 v210 단독임을 확인하고 **동결 이후 판정 사건 0건**인 지금 같은 정의로 다시 재 재등록(I13 FAIL→PASS 재현). ③ 그 밖에 v210 뒤 움직인 연구 수치 8건 병기(결론 동일) · `post_dotcom` 판정문 계산화. **결론 변경 0.**

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B14-1 | **P1** | `data/oos_protocol_b.json` · `research/oos_protocol_b.py:250-263` · `deploy/watchdog.py:713` · `02` §5-1 · `04` §5-23 | v210 뒤 매주 월요일 08:40 KST | 자기검산 A 독립 **8/8 vs 등록 7/7** · B 전체 69건 P05 **−29.3% vs 등록 −33.3%** → `--oos` exit 2 「판정 중단」 · 파수꾼 `mode_check` 가 「기저율 표류」 todo → 배너·알약·카톡(v188 「악화」 규약). 2026-09-01 점검 파일엔 아직 `protocol_b` 키 없음(v188 뒤 첫 월요일 실행 전) | wt203·wt209 등록값 일치 · wt210 어긋남 | **수정** — 같은 정의로 재계산해 재등록(A 8/8 · B P05 −0.293·최악 −0.411 · R P05 −0.331·최악 −0.493 · 진 창 58% · n 69 · `revisions` 에 옛 값·옛 지문) · 새 지문 `74387a5c73c0fc06` · 02 §5-1 재등록 문단·표 · 04 §5-23 표시 · 평가기 docstring·주석 · notes v218 · **I13 FAIL(값만 교체)→PASS(지문 갱신) 재현** · `--oos` 「판정 불가 — 정상」 |
| B14-2 | P3 | `research/schd_qqq_overlap.py` A · `04`:2181(§5-31) · `CLAUDE` §5-31 ⓐ | v210 뒤 | 「B 는 2배 보유의 **38배**」→ **49배**(B 217,110→220,985 · 2배 계속보유 **5,760→4,552**) · 1970년대 2.61→2.34 · 2020년대 0.84~0.98→0.90 · 상관·섹터·위기 표(2011~·2003~)는 v210 무영향으로 동일. 2배 계속보유가 줄어든 것은 v210 이 뺀 114행이 드래그 모형(κσ²)의 변동성 추정에 들어가 있던 탓 — B 우위 결론 동일 | 재실행 · wt209 38배 재현 | **수정** — 2곳 병기 |
| B14-3 | P4 | `research/post_dotcom.py:136-148` [4] 판정 | 실행 시 | 판정문이 **하드코딩** — v210 뒤 표는 VR 0.52배인데 문장은 0.57배. 나머지(34.9→1.09 · 0.87 · −49.7/−83.2 · 0.499/0.293 · 176배)는 우연히 일치. [0] 검산(2010~ 무한매수 17.2 · B 84.3)은 통과 | 실행 | **수정** — 표의 계산값으로 출력 |
| B14-4 | P4 | `research/pbo_thresh.py` · `04`:1516(§5-22) · `CLAUDE` §5-22 항목 | v210 뒤 | 격자 PBO Sharpe 0.714 / Calmar 0.600 · 대각선 0.514 / 0.400(옛 0.400~0.829) · 잡음 섞으면 0.843(옛 0.914) · 잡음이 IS 1등 36/70(옛 26/70) · 현행 OOS 중앙 **91% · 1위/17 동일** — 「IS 1등 고르기 동전던지기 이하」 결론 동일 | 실행 | **수정** — 2곳 병기 |
| B14-5 | P4 | `research/ops_risk.py` · `04`:434 · `CLAUDE` §5-8 항목 | v210 뒤 | 놓침 137회 중 103회 이득(옛 139/102) · 중앙 +1.9% · 최악 −96.5% 동일 · ±10% 오류 51/200(옛 49) · 손익분기 편도 3.00%(격자 2→3% 사이 · 문서 「≈2.5%」는 보간 표기 — 오류 아님) · 연속 손실 10회 −20.4% 동일 · 2022 −32.6/−4.8 동일 | 실행 · wt209 49/102 재현 | **수정** — 2곳 병기 |
| B14-6 | P4 | `q1_physical_bond`·`q5_near_presell`·`plan30_withdraw`·`recovery_speed` · `04` §7-3·§7-5·§5-36·§5-30 · `CLAUDE` 해당 항목 | v210 뒤 | Q1 현물 10년 Calmar +4.4→**+4.8%**(① 미달 동일 · P2 틀림 동일) · Q5 0.33→**0.30배** · 절반 0.62→0.59 · 에피소드 −0.66→−0.75% · plan30 B 149.93→**156.25**(금 20% 75.95 > 현금 20% 72.70 로 3·4위만 교대 · B 1위 동일) · recovery 순열 p 0.315→**0.162**(D3 · 여전히 유의하지 않음) · 순위상관 +0.62/+0.90→+0.66/+0.88 · 시대별 중앙 380/94/2,634/109/79 | 실행 | **수정** — 04 5곳·CLAUDE 5곳 병기 |
| B14-7 | P4 | `research/surv_alert.py` [D] · `내가_보는_것/점검.py:114-118` BANDS · `research/SURVIVAL_MONITOR.md` §F | v210 뒤 | 재실행 밴드: 10년 CAGR p10 **4.0%**·최저 **−8.0%** · 5년 −1.1/−20.1 · 3년 변동성 p90 **36.0%**·최고 51.9 · 드래그 11.7/29.4 vs 점검.py 하드코딩 4.1/−8.1 · 35.6/51.9 · 11.7/29.4(20년 CAGR 9.5/3.1 은 `surv_map` 몫). 차이 ≤0.4%p · 하드코딩 쪽이 **보수적**(먼저 경고) · 현재값(20.6% · 20.5%)은 밴드에서 멀다. [B] 최악 전방 5년 사건 2개(1983-05 · 2000-02) 동일 | 실행 | 기록만 — B15 `surv_map` 재실행 뒤 밴드 갱신 여부 판단 |
| B14-8 | P4 | `research/q2_hedged_attack.py`(FRED 타임아웃 → OECD 성공 · 캐시 diff 0) · `new_paths.py`(①②③ 0 · C3 는 B10-1) · `slice_scan.py`(T4@3÷B@2 54년 10년 창 승률 54% · 2000~ 45%) · `oos_protocol_b.py:39` docstring 217,110 | — | Q2 0.82배·carry +1.85·MDD +2.0·p05 +83.7%·2008 −10.4 **전부 동일**(원화 1997~ 창) · 슬라이스는 04 §5-11 의 「85~88%」와 창이 달라 직접 대조 불가(기록) | 실행 | docstring 만 수정 |

읽기 vs 실행: 전문 판독 13/13 · **실행 13/13**(+`--oos`) · 원인 가르기: `oos_protocol_b --oos` wt203·wt209·wt210 · `schd_qqq_overlap`·`ops_risk` wt209.

### B15 research s~w + data 계약 (2026-09-05)

**세 줄 요약** — ① `surv_map`·`t4_lev_post`·`takeprofit`·`tax_general_account`·`tax_us_direct`(688줄 · 4모드)·`thresh_window`·`tranche`·`valuation_regime`(553줄)·`wfa_thresh`·`what_we_know`·`withdraw` 11파일 3,075줄 전문 + **14편 실행**(tax_us_direct 기본·`--c21`·`--accum`·`--windows`) + `data/` 최상위 json 11·csv 3 의 **생산자↔소비자 키 계약 자동 대조**(스크립트 `b15_contracts.py`: 키 187개 검사 · 소비자 미등장 키는 전부 사람용 설명 필드 · CSV 열 미등장 0). ② **매매·판정 결함 0 · 계산 결함 0 · 운영 결함 0.** 축퇴·재현 검산 전부 통과(`tax_us_direct` 세율 0 assert 3종 · `tranche` 축퇴 · `t4_lev_post` 정본 오차 0 · `thresh_window`·`valuation_regime` 판정 동일). **v210 뒤 움직인 것 셋(전부 wt209 로 v210 단독 확인)**: ⓐ `wfa_thresh` 문서 대조 **12/12 → 7/12**(선택 중앙 −0.16 은 3/3 유지 — 어긋난 것은 「고정 승」 백분율 · 걸음 8~14회라 1~2걸음 차이) 그리고 **결함판(누적) 중앙이 −0.16 → −0.12** 로 움직였는데 코드는 「안 움직인다」를 하드코딩해 자기모순 문장을 찍고 있었다 · ⓑ `withdraw` [5] 「최악 연간 소득 −51.3%」가 **연 1회 관측 위상 하나**의 값이라 같은 코드가 v210 뒤 **−16.0%** 를 냈다(위상 252개 최악 −53.6% · 중앙 −37.4%) — 위상 전수·롤링 1년으로 재정의 · ⓒ `tax_us_direct` 1981~ 전체창 145,135/253,390(1.75배 · 전환 120) → **144,804/264,133(1.82배 · 124회)** · 5년 비중첩 B승 **6/9 → 4/9** · 지평 1.15/1.45/1.17/1.65 → 1.11/1.38/1.16/1.63 — **21세기 표(161.5/283.9 = 1.76배)·손익분기 k(2.6/2.5/2.8/2.7/2.8)는 소수점까지 동일**(화면·아티팩트 기준은 21세기). ③ 수정: 코드 2(withdraw [5][6] 계산화 · wfa_thresh 문장·docstring) · 문서 병기 04 8곳·CLAUDE 11곳·01·MEASUREMENT·LEVERAGE_US 3·SURVIVAL §F. **결론 변경 0.**

| ID | 등급 | 파일:줄 | 조건 | 영향 | 근거 | 처리 |
|---|---|---|---|---|---|---|
| B15-1 | P3 | `research/withdraw.py:111-123` [5] · `:156-163` [6] 하드코딩 · `04`:410 · `CLAUDE` 측정 감사 항목 · `research/MEASUREMENT_AUDIT.md`:356 | 실행 시 | `ys = a[::Y]` 한 위상으로 연간 소득 변동을 재 값이 표본 격자에 매달렸다 — v210 뒤 B 최악 연간 감소 **−51.3% → −16.0%**(위상 252개: 최악 −53.6% · 중앙 −37.4% · 최선 −16.0% · <−50% 인 위상 24/252). [6] 판정문은 −51.3%·48.7% 하드코딩. 설계 요건(1년치 현금 완충)은 롤링 1년 최악 −53.6% 로 그대로 성립 | 위상 전수 재계산 | **수정** — [5] 위상 252개 전수 + 롤링 1년 · [6] 계산값 출력 · 문서 3곳 정정 표시 |
| B15-2 | P3 | `research/wfa_thresh.py:219`(하드코딩 「안 움직인다」) · `:33-39` docstring · `04`:722·1487 · `CLAUDE` §5-22 항목 | v210 뒤 | ext 엔진 문서 대조 12/12 → **7/12**(고정 승(무승부 포함) 73/77/67 → 79/92/75% · 걸음5y 밴드 44→38% · 정확히 33→25%) · 결함판(누적) 선택 중앙 −0.16 → **−0.12**(정정판 −0.16 · 훈련 길이 8/8 유지) → 「창만 바꾸면 안 움직인다」 문장이 값(−0.12 → −0.16)과 모순. §5-13 의 핵심(과거 자료만으로 골라도 −16)은 정정판에서 유지 | wt209 12/12 · wt210 7/12 | **수정** — 문장을 값에 맞춰 조건화 · docstring 주의 · 문서 4곳 병기 |
| B15-3 | P3 | `research/tax_us_direct.py` 기본·`--windows`·`--accum` · `CLAUDE` 세후 배율 항목(6곳) · `research/LEVERAGE_US.md`:331·344·462 · v205 항목 | v210 뒤 | 1981~ 전체창 ISA 145,135 → 144,804 · 3배 직투 253,390 → **264,133** · 1.75 → **1.82배** · 전환 120 → 124 · 지평 중앙 1.15/1.45/1.17/1.65 → 1.11/1.38/1.16/1.63 · 비중첩 5년 B승 **6/9 → 4/9**(창 경계가 거래일 수 기준이라 날짜가 밀림) · 적립 20년 요인분해 1.16643→1.16450 등 소폭 · **`--c21` 21세기 표 161.5/283.9/1.76배·MDD −53.2/−61.3 과 손익분기 k 는 동일** | wt209 재현 | **수정** — 병기 10곳(LEVERAGE_US 는 B05 v210 배너 위에 핵심 3행만) |
| B15-4 | P4 | `research/tranche.py` · `CLAUDE` 측정 감사 항목 | v210 뒤 | 무작위 5트랜치 200회: MDD·Calmar 100% 개선 동일 · 20년 p05 개선 24% → **0%** · 최종 31% → 13% · Calmar +5.0% → +3.9% — **기각 동일(더 명확)** | 실행 · wt209 24% 재현 | **수정** — 1곳 병기 |
| B15-5 | P4 | `research/thresh_window.py` · `04` §5-20(:1327·:1336) · `CLAUDE`:1112 · `01`:68 | v210 뒤 | 54년 1위 · 21세기 1위 · v18 미관측 28년 22위(B08 병기 그대로) · 경계 이동 순위 범위 1~56 → **1~50**(중앙 6 → 1 · 1등 창 7/20 → 11/20) · 미니맥스 K=2/3/6 5/1/7 → **1/1/1** · 1등의 90% 이내 1개/210 — 「통짜 1위는 근거 아님」 결론 동일 | 실행 | **수정** — 4곳 병기 |
| B15-6 | P4 | `research/tax_general_account.py` · `04` §5-38(:2917·:2927·:3011) · `CLAUDE` §5-38 항목 2곳 | v210 뒤 | 세후 B 57,578 → 58,009 · 헤지6/4 10,719 → 10,591 · 격차 6.84→7.04(세전)/5.37→5.48(세후) · ISA vs 일반 10년 −20.5→−20.9% · 20년 104.2/65.1 → 104.5/66.2 · 30년 1,335/624 → 1,465/651 · 54년 195,616/46,212 → 199,108/46,672 — v210 항목이 「재실행 전 인용 보류」로 둔 값이 이제 재실행됨 · 결론 동일 | 실행 | **수정** — 5곳 병기 |
| B15-7 | P4 | `research/surv_map.py` [5]·[6] · `research/surv_alert.py` [D] · `research/SURVIVAL_MONITOR.md` §F · `내가_보는_것/점검.py:114-118` | v210 뒤 | 현재값(10년 20.6 · 20년 16.9 · 변동성 20.5 · 드래그 8.1)은 §F 와 동일 · AUM 4다리 정상(418660 6,421억) · 재계산 분위 4.0/−8.0 · 36.0/51.9 · 11.7/29.4 · 20년 9.5/**2.8** vs 하드코딩 4.1/−8.1 · 35.6 · 3.1 — 차이 ≤0.4%p · 전부 보수적 방향 · 현재값 밴드에서 멂 | 실행 · 재계산 | SURVIVAL §F 에 주석 · **밴드 갱신은 소유자 결정 항목**(점검.py 무수정) |
| B15-8 | P4 | `data/` 최상위 14개 계약 (`b15_contracts.py`) | — | JSON 키 187개 중 소비자 미등장 32개는 전부 사람용 설명(`freeze.json` principle·reference·date_convention · `oos_protocol_b.json` engine·event·judgment 등 · `isa_stats.json` y10/y15/y20 은 `audit/test_research_review.py` 회귀검사만 소비 · `ops_check.json` vars · `retired_numbers.json` _note) · CSV 3(nav_history 11열 · oos_log 11열 · qqq 2열) 열 미등장 0 · 생산자: `crisis_paths`/`dd_percentile`/`isa_stats` 는 research 수동·월간 · `signal`/`oos_log`/`nav_history`/`signal_alert_state`/`ops_check` 는 deploy 자동 · `freeze`/`oos_protocol_b`/`retired_numbers`/`kr_holidays` 는 등록·규약(지문·관문) | 자동 대조 | 기록만 |

읽기 vs 실행: 전문 판독 11/11 · **실행 14/14** · 원인 가르기: `wfa_thresh`·`tax_us_direct(기본·--windows)`·`tranche` wt209 · 데이터 계약 자동 대조 1회.

## 9. 총괄 보고 (전 배치 완료 뒤)

**작성 2026-09-05 · Claude Fable 5.1 · 순회 B01~B15 완료 (커밋 v211~v218 + review 커밋 5개).** 소유자용 풀이는 세션 마지막 답변에 따로 적었다 — 이 절은 이어받는 세션(Codex 포함)용 사실 기록이다.

### 9-1. 범위와 방법
- **범위**: 15배치 · 파일 ≈ 210개 · ≈ 58,000줄(운영 17 · 자동화·검증 15 · 엔진 14 · 화면·문서 12 · 연구 문서 14 · research .py 116 · data 계약 14). §6 목록의 배치를 **순서대로 혼자** 돌았다.
- **방법**: 전문 판독 → **실행**(연구 129편 중 **117편 실제 실행** · 미실행 12: 네트워크 다운로더 `hist_fetch` · B05 에서 재실행분 재사용 등 — 배치별 「읽기 vs 실행」 줄 참조) → 문서 수치와 대조 → 어긋나면 **세 작업트리(v203 d9606ed · v209 4c01375 · v210 330e1c7)에서 같은 코드를 돌려 원인을 한 변수씩 가름**(§-1 ⑧) → 수정 → `verify_all`(문서·py 만이면 `--fast`, 화면 건드리면 전체) → 명시 경로 커밋 → push → CI 확인.
- **판정 규약**: 「채택」은 한 번도 쓰지 않았다. 관문을 넘은 후보는 전부 **소유자 결정 항목**으로만 적었다(9-5).

### 9-2. 발견 — 심각도별 (P1 1 · P2 6 · P3 22 · P4 85 = 114건)
| 등급 | 건수 | 내용 | 처리 |
|---|---:|---|---|
| **P1** | 1 | B14-1 **B 판정 규약 기저율 표류** — v210 거래일 정정 뒤 등록값(7/7 · P05 −33.3%)과 역사(8/8 · −29.3%)가 어긋나 평가기가 「판정 중단」, 다음 월요일 파수꾼이 「기저율 표류」 카톡을 낼 상태 | **수정** — 판정 사건 0건 상태에서 같은 정의로 재등록(새 지문 74387a5c73c0fc06 · `revisions` 보존 · I13 FAIL→PASS 재현 · 02 §5-1·04 §5-23·notes v218) |
| **P2** | 6 | B03 `axis_defmix.real_run` 수익→전환 순서 · `check_accum` 가짜 검산 · B04 신호 화면 각주 168 이 원화 2배보유 값 · B05 설명서 ② 확률표 원천 미재실행 · B08 `axis_nextgen` v81 앵커 사망(재실행 시 MIX 0.50 관문 통과) · B09 설명서 ⑪ T4 성적표가 v80 값 | **전부 수정**(v211·v212·v214·v215) |
| **P3** | 22 | 거의 전부 **「v210 자료 정정 뒤 문서 수치가 옛 값」** 유형(T4 계열 +57.7% · 룩백200 승률 100→78% · 기계정책 3/45→14/45 · C3 관문 · 38배→49배 · 12/12→7/12 · 1.75→1.82배 등)과 **하드코딩 판정문 3건**(post_dotcom · wfa_thresh · withdraw) · 위상 의존 통계 1건(withdraw) | **전부 병기·정정 표시 또는 계산화** — 옛 수치는 지우지 않고 「v210 재실행 값」을 옆에 적었고, 옛 결론이 살아 있는 문서엔 `retired_numbers.json` 등재(I9 관문) |
| **P4** | 85 | 주석·docstring 앵커(217,110 등) · 모듈 수준 실행 · 전역 덮어쓰기 · 재실행 결론 동일 확인 기록 | 주석은 수정 · 나머지 기록만 |

**전략 B 동결값(−16/−16 · 252 · 40/40/20) · 실측 장부(freeze/oos_log/nav_history) · 판정 로직 · 공표 4시나리오: 15배치 어디에서도 변경 0.** 화면(signal/guide/notes)은 v211·v212·v214·v215·v218 에서 **표시 수치·설명만** 바뀌었다.

### 9-3. 바뀐 계산 (동작이 달라진 것)
- 연구 엔진: `axis_defmix.real_run` 순서(B03) · `axis_lib.check_accum` 항등식(B03) · `post_dotcom` [4] 판정문 계산화(B14) · `wfa_thresh` 문장 조건화(B15) · `withdraw` [5][6] 위상 전수·롤링(B15). 재현 앵커 4개를 v210 기준으로 갱신(`axis_nextgen` · `axis_t4_shadow` · `b_gate_noise` + docstring 다수).
- 등록·산출물: `data/oos_protocol_b.json` 재등록(B14) · `hyst_wfa.csv` 재생성(B13) · `data/retired_numbers.json` 등재 추가(B04·B08).
- 운영 코드(`deploy/*` · 워크플로): **수정 0**(B01 cp949 디코드 단위검사 추가만). `내가_보는_것/점검.py` 밴드는 v210 전 분위이나 보수적 방향이라 **미수정**(9-5).

### 9-4. 검토 vs 미검토
- **전문 판독**: §6 의 15배치 전부. **실행**: 운영 셀프테스트(I14 16종) · verify_all 전체 · 연구 117/129편 · 데이터 계약 자동 대조.
- **미검토·부분**: `공유용_별도전략/`(§2 격리 규약 · 읽지 않음) · `docs/history/*`(§2 · B04 에서 diff 만) · `data/hist/*` 82 원자료(구조·범위만 · **출처 교차검증은 04 §7 Q10 미결**) · 외부 아티팩트 「전략 B 배합 탐색기」(원본 미확인 · v205) · 카카오 도착(자동 검증 불가 · v178) · GitHub 러너 환경 차이(`source-probe.yml` 로만) · 개인 세후·납입 조건(미확인 입력은 추측하지 않음).
- **동시 작업**: 순회 중 다른 세션(Codex)이 v207~v217 · F1~F4 연구 커밋을 main 에 넣었다. 순회는 그 뒤 코드를 읽었고 수정 파일은 겹치지 않았다(B01~B02 사이 v207~v210 · B13~B15 사이 v216~v217). Codex 의 미커밋 파일은 어느 커밋에도 넣지 않았다.

### 9-5. 남은 위험 · 소유자 결정 항목
1. **혼합 그림자 후보** — `axis_nextgen` MIX(0.50) · `hypo_hex` x=0.50·0.55 가 v210 자료에서 관문을 통과(B08-1 · B12-3). 비용 미교정 경로 위의 값이고 후반(2000~) 0.91×B. **채택 아님 — 「그림자 등록 논의 자격」 여부는 소유자.**
2. **T4 계열 수치는 v210 에 민감**(+57.7%) — 총수익 우위가 1972~77 여섯 해에 걸려 있다(1978~ 공통창 0.50×B · B12-2). 04 §5-11 T4 서술을 다시 쓸 때 **창을 붙일 것**.
3. **감시 밴드 갱신 여부** — `점검.py`·SURVIVAL §F 의 4 밴드가 v210 전 분위(차이 ≤0.4%p · 보수적 방향). 갱신하면 「먼저 경고」가 미세하게 늦어진다. 현재값은 밴드에서 멀다.
4. **v210 전 수치를 든 연구 문서 5편**(ENGINE·EXT_INFINITE·NEW_STRATEGY·SURVIVAL·LEVERAGE_US)은 배너만 — 전면 재생성은 하지 않았다(옛 수치 = 당시 기록).
5. **다음 거래일(2026-09-08 월) 확인**: `daily-signal` 05:0x 종가 · `nav_collect` 장 밖 슬롯 적립(v206) · **파수꾼 `check` 첫 `protocol_b` 기록**(재등록 뒤 「사건 0건 — 재검토 사유 없음」이어야 한다) · 재조정 D-day.
6. 원자료 출처 교차검증(04 §7 Q10) · ISA 원화 납입형 시점 뒤섞기 반증(v213) 은 순회 범위 밖 미결 그대로.

### 9-6. 이어받는 세션에게
- 이 대장 §7·§8 이 단일 진실. 새 수치를 인용하기 전 **그 값이 v210 뒤 재실행 값인지** 확인하라(§-1 ④) — 옛 값 옆에 「v210 재실행」 병기가 없으면 재실행 전 값이다.
- 재현 앵커를 다시 갱신할 일이 생기면 **세 작업트리 방식**(§9-1)으로 원인을 가른 뒤 옛 값을 병기하라. 조용히 넓히지 마라.
- 작업트리 `scratchpad/wt203·wt209·wt210` 은 순회 종료와 함께 제거했다.
