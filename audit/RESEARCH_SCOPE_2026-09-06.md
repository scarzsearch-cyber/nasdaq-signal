# 계산·보조 도구의 미검증 범위 선정 (2026-09-06 · 읽기 전용 대조 · 계산 실행·코드 수정 없음)

> 기준 0b80097 · 작업트리 `review/doc-claims-10`. 대상: `COVERAGE_MAP` 이 「담당 확인 필요」로 남긴 research 스크립트 134 · research 문서 10 · `research_kit.py` ·
> `내가_보는_것/점검.py`. 파일 목록·import 그래프·호출자(워크플로·verify_all·deploy·점검.py·audit·화면·문서)·산출물 소비처를 스크래치 스캔(`scope_scan.py` · 저장소 밖)으로
> 뽑고 기존 감사 근거(COVERAGE_MAP 수준)와 대조했다. **돈전략이 진행 중인 미국 ETF 분배금·분할·수정주가·총수익률·세후 경로와 기존 인계(01·02·04 정정 · sim_hold 검사 편입)는
> 후보에서 뺐다.** 최근 작업에 안 나왔다는 이유로 담당 밖이라 단정하지 않았다 — 보관·불명확 묶음은 「담당 미확정」으로 둔다.

## 0. 스캔 한계
- import 는 정적 정규식(`import x` / `from x import`) · 호출자는 파일명 언급(실행 호출과 주석 언급을 사람이 갈랐다). `git ls-files` 의 한글 경로 이스케이프로 `점검.py` 는 스캔에서 빠져 손으로 넣었다.
- 「산출물」은 `data/*.json` 쓰기만 세었다(원자료 `data/hist/*` 읽기는 제외).

## 1. 네 갈래 분류

### A. 현재 운영·문서·판단에 실제로 사용되는 도구 (실행 경로가 있음)
| 파일 | 호출자(실행) | 산출물 → 소비처 | 기존 검사 수준 | 비고 |
|---|---|---|---|---|
| `research/emit_dd_distribution.py` | `monthly-stats.yml`(원자료 연장 직후 매월) · verify_all 스텝 순서 문자열 관문 | `data/dd_percentile.json` → `signal.html paintDdPct`(낙폭 백분위 한 줄) | **L2**(전문 판독 · v164 검산 1건 · REPRO 재생성 diff 0) | 표시 전용 · 판정 무관 |
| `research/oos_protocol_b.py` | `deploy/watchdog.py check`(주간 · `--oos`) · verify_all **I13**(등록 지문) | `data/oos_protocol_b.json`(등록) · `ops_check.protocol_b` → 화면 알약/todo · 악화 시 카톡 | **L4**(파수꾼 연결 · 출력 파서 계약 · v218 재등록) | **B 판정 규약 평가기** — 규약 소유는 소유자·전략 쪽(담당 확인 필요) |
| `research/surv_map.py` | `내가_보는_것/점검.py`(subprocess · 주간 파수꾼 check) | stdout → `점검.py` 정규식 → `ops_check.json`(vars·level·aum) → 화면 점검 줄·배너 · 악화 카톡 | **L2**(전문 판독 · 순회 B15 실행) — 연결은 WATCHDOG_CHAIN(대역 출력) | 밴드 4종은 v210 전 분위(소유자 결정 대기 · SURVIVAL §F) |
| `research/exec_cost.py` | `내가_보는_것/점검.py`(subprocess) | stdout → `ops_check.exec`(진행률 n/20) → 화면 | **L3**(selfcheck + 단위 2 · test_research_review) | 표본 0/20 이라 판정 없음 |
| `research/axis_isa.py --emit` | 수동(README) | `data/isa_stats.json` → 설명서 ④·신호 화면 계좌 패널 | L3(회귀) | **세후 계열 — 돈전략 진행 중 · 제외** |
| `research/build_crisis_paths.py` | 수동(pages.yml 주석 · README 미등재) | `data/crisis_paths.json`(2026-08-31 생성) → `signal.html initTimeMachine`(위기 타임머신 4구간) | **L2** + 내장 검증 3(final 167.315 = 공표 · 정합 · 길이/유한) | v210 이후 us_2000 무변화라 현재 일치 · 갱신 누락 감시 없음 |
| `research/axis_finalverify.py --selftest` | verify_all **I14**(CI) | 공표 장부 감사 셀프테스트 | L3 | — |
| `research_kit.py` | `verify.yml`(CI) · research 29편이 import | 설계 가드 자기검사 | L4 | — |
| 문서 근거로만 쓰이는 것 | `near_zone.py`(파수꾼 근접 알림 문턱 근거) · `ops_risk.py`(화면 FACTS 수치 출처) · `axis_krspec.py`(deploy docstring 실측 인용) · `axis_t4_shadow.py`(oos_log 의 T4 열 A-2 대조) | 런타임 호출 없음 | L2~L3 | 수치 인용 정합은 DOC_CLAIMS 계열 |

### B. 다른 계산이 호출하는 공용 도구 (import 피호출 수 · 검사 모듈 제외)
`eng_common.py` 58 · `hypo_gates.py` 19 · `hypo_t4_real.py` 13 · `rebalance_accounting.py` 11(+`axis_defmix` 루트 엔진) · `hypo_hex.py` 9 · `axis_t4_shadow.py` 6 · `account_ledger.py` 5 · `liquid_design.py` 4 · `band_accounting.py` 2 · `hypo_external2.py` 2 · `hypo_t4wide.py` 2 · `strategy_f1_placebo/f1_screen/f2_mix/f1_kr/f3_execution.py`(F계열 · 돈전략) · `axis_ext2·axis_meta·axis_nextgen·axis_rvstate·b_adversarial·ext_ibs·ext_vr·hypo_escape.py` 각 1.
기존 검사: `eng_common`·`rebalance_accounting`·`account_ledger`·`band_accounting`·`liquid_design`·`hypo_hex`·`hypo_t4_real` 은 회귀 모듈(test_research_review·test_account_ledger·test_execution_bands 등) L3 · `hypo_gates` 는 L2.

### C. 과거 실험·보관용으로만 남은 파일 (04·감사 장부 언급만 · 런타임 호출 0 · 담당 미확정) — 73
attack_diversify · audit_exec · audit_pbo · audit_stat · axis_accum2 · axis_dca · axis_dca_grid · axis_defsel · axis_ext2_probe · axis_external · axis_forward · axis_horizon · axis_macro3 · axis_macro4 · axis_mech · axis_minimax · axis_momentum · axis_regime · axis_selbias · axis_t4_krcost · axis_t4_synthcrash · axis_vixstate · axis_wide · b_gate_noise · basket_accounting(F4 · 돈전략) · cand_general · complement_sleeve · def_bond · def_equity · drag_sigma · dsr_b · eng_kospi · eng_sp500 · era_start · execution_policy(F3) · factcheck_qld_talk · forecast_check · free_design · hedge_ratio_scan · hist_fetch · horizon_ess · horizon_study · hypo_verify · hyst_sigwfa · hyst_wfa · isa_pension(세후) · japan_stress · lev_5y · lev_opt · lev_th · lookback200 · mdd_target · near_zone · pbo_thresh · post_dotcom · q1_physical_bond · q2_hedged_attack · q5_near_presell · recovery_speed · schd_qqq_overlap · slice_scan · strategy_f3_placebo(F3) · strategy_f4_basket/f4_products(F4) · surv_alert · t4_lev_post · takeprofit · tax_general_account(세후) · thresh_window · tranche · valuation_regime · wfa_thresh · what_we_know · **plan30_withdraw · withdraw · tax_us_direct**(verify_all 언급은 관문 주석·문맥 검사뿐 · 세후·인출 계열 — 돈전략 인접).
기존 검사: 대부분 L2(순회 B05~B15 전문 판독+실행) · 일부 L3(회귀 모듈).

### D. 사용처나 담당이 불명확한 파일 (FILES·CODE_REVIEW 언급 외 참조 0) — 34
axis_accum · axis_b_inspect · axis_dipbuy · axis_ens · axis_gate11 · axis_hedge_cost · axis_krreal_decomp · axis_krspec(deploy docstring 인용은 있음) · axis_krspread · axis_lev · axis_macro · axis_macro2 · axis_meta_crisis · axis_newrule · axis_objective · axis_secondary · axis_selbias_disjoint · axis_sigsrc · axis_vrhybrid · axis_wide_probe · c3_falsify · c3_placebo · frontier2 · goal_feasibility · hist_defchain · hist_defdiag · hist_defrun · hist_krtax(세후) · hist_three · hyst_signal · lev_signal_source · liquid_iter · ml_policy · new_paths.
→ 삭제·통합 판단은 하지 않는다(v205 「파일 수를 줄이기 위한 정리는 하지 않는다」). 담당 확인 뒤 C 로 옮기거나 유지.

### research 문서 10 (전부 L2 전문 판독)
CODE_REVIEW · ENGINE_RESEARCH · EXPLORATION · EXT_INFINITE · FINAL_AUDIT · LEVERAGE_US(설명서 참조) · MEASUREMENT_AUDIT · NEW_STRATEGY_RESEARCH · STRATEGY_RESEARCH · SURVIVAL_MONITOR(파수꾼 밴드 근거). v210 전 수치 배너 5편(v212).

## 2. 후보 — 현재 사용 · 기존 근거 약함 · 돈전략과 분리 가능 (최대 3 · **착수하지 않음**)
| # | 파일 | 호출자 | 결과 사용처 | 기존 검사 수준 | 미검증 위험(의심 아님 · 검사가 없는 지점) | 권장 검증 방법 |
|---|---|---|---|---|---|---|
| 1 | `research/emit_dd_distribution.py` | `monthly-stats.yml`(매월 · 원자료 연장 직후) | `data/dd_percentile.json` → `signal.html paintDdPct` 「이보다 깊었던 날 N%」(n=13,749 · edges 99) | L2 · v164 검산 1건(−16% ↔ 방어 보유일 18.1%) · 재생성 diff 0 | ① 백분위 정의(보간 방식·경계 포함)와 화면 문구의 계약이 독립 재계산으로 대조된 적 없음 ② edges 단조·`edges[98]=0` 경계(v202 가 문구를 뒤집어 고친 자리)가 관문에 없음 ③ 원자료가 바뀔 때 화면이 옛 분포를 읽는 것을 알 수 없음(n 과 거래일 수 대조 없음) | 별도 구현으로 `data/hist` 에서 252일 낙폭 계열·백분위를 재계산해 JSON 과 대조(읽기 전용) · 계약 검사(단조·n=거래일 수·start/end=엔진 구간) · `paintDdPct` node 하네스(합성 edges 로 문구 경계) · 실패 주입(경계 하나 뒤집기)으로 탐지력 확인 |
| 2 | `research/surv_map.py` + `내가_보는_것/점검.py` 파싱 결합 | 주간 파수꾼 `check` → `점검.py --json` → subprocess | `data/ops_check.json`(vars 4종·level·aum·exec) → 화면 점검 줄·알약·배너 · Level 악화 시 카톡 | surv_map L2(전문 판독·실행) · 연결은 WATCHDOG_CHAIN(대역 출력·health_errors 규약) · exec_cost L3 | ① 감시 변수 4종(지수 10y/20y CAGR · 3y 변동성 · 2배 드래그 3y)의 값이 독립 계산으로 대조된 적 없음(정의는 docstring 에만) ② AUM 밴드(정상/주의/경보 300·100억)의 nav_history 파싱·최신 행 선택이 검사 밖 ③ 정규식 파서 ↔ surv_map 출력 서식의 계약이 실제 출력이 아니라 대역으로만 고정(서식이 바뀌면 health_errors 로 알리는 설계는 있음) ④ Level 산정(p10/p90 밖 개수)의 재현 없음 | 같은 엔진 계열(또는 원자료)에서 4변수를 별도 코드로 재계산해 surv_map 출력과 대조 · 실제 surv_map 출력을 고정 문자열로 삼는 파서 계약 검사(양방향: 서식 변경 → health_errors · 값 → BANDS 판정) · AUM 밴드 합성 nav_history 3갈래 · **밴드 값(v210 전 분위)은 손대지 않는다**(소유자 결정 대기) |
| 3 | `research/build_crisis_paths.py` | 수동(자동 편입 안 됨 · pages.yml 주석) | `data/crisis_paths.json`(2026-08-31) → `signal.html initTimeMachine`(위기 타임머신 · 1,000만원 환산 · 재생) | L2 + 내장 검증 3(final=공표 · 정합 · 길이/유한/시작 1.0) | ① 공표값(`strategy_stats us_2000`)이 바뀌어도 이 파일은 수동이라 낡을 수 있고 그것을 재는 관문이 없음(v171 유형 · 지금은 v210 이 us_2000 을 안 바꿔 일치) ② 위기 고점일(`update_signal.CRISES`)·400일 슬라이스·시작 1.0 정규화가 화면 표기(구간명·날짜)와 대조된 적 없음 ③ 화면의 환산·재생 계산(클라이언트 근사 0 규약)이 검사 밖 | 정합 관문(unittest): `_meta.engine_check` 의 final = 현재 `strategy_stats us_2000 B.final`(어긋나면 재생성 필요를 알림) · CRISES 날짜 → JSON 구간 시작·길이 대조 · `initTimeMachine`/재생 node 하네스(합성 경로로 환산·최대·최종 표시) · 자동 편입 여부는 제안만(monthly 뒤 재생성 · v127 「수동」 결정과 충돌 → 소유자 판단) |

- **제외 근거**: `oos_protocol_b.py`(사용·근거 L4 이지만 **B 판정 규약** 자체의 사건 감지 논리는 규약 소유자 판단 대상 — 합성 사건으로 `evaluate_oos` 를 재는 것은 가능하나 담당 확인 뒤) · `axis_isa.py`·세후·인출 계열(돈전략 진행 중) · F계열 · `research_kit.py`·`axis_finalverify.py`(CI 가 매번 돈다 · L3~L4).
- 후보 셋은 전부 **표시·감시 전용**(판정·동결값·원자료 무접촉)이라 돈전략 경로와 겹치지 않는다.

## 3. 후보 검사 착수 여부 — 미착수(소유자·아스트라 판단 대기).
