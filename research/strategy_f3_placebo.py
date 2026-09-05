"""F3 timing falsification: all 52 tests, 1999 fixed draws (d6f5bde section 16).

Read-only. Extend F1/F2 exact archived counts only after source/data/statistic
identity checks. All F3 null paths rebuild stateful execution from raw targets.
No personal accounts, parameter selection, orders, or live rule changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research'), str(ROOT/'deploy')]
import numpy as np
import pandas as pd
import strategy_f1_placebo as F
from research.strategy_f2_mix import FIXED, mixture, distribution
from research.strategy_f3_execution import PARENTS, parent_weights, archive_source_check, hashes
from research import execution_policy as P
from audit.test_execution_policy import units_reference

DRAWS = 1999
MODES = ('P1_target_blocks', 'P2_raw_return_blocks')
METRICS = ('calmar', 'weak_tail')


def recovered_count(probability, draws):
    value = float(probability)*(draws+1)-1
    count = int(round(value))
    if abs(value-count) > 1e-10 or not 0 <= count <= draws:
        raise ValueError('archived p is not an exact plus-one Monte Carlo count')
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--f1-result', type=Path, required=True)
    ap.add_argument('--f2-result', type=Path, required=True)
    ap.add_argument('--f3-gross', type=Path, required=True)
    args = ap.parse_args()
    paths = [args.f1_result, args.f2_result, args.f3_gross]
    archive_bytes = [p.read_bytes() for p in paths]
    old1, old2, old3 = [json.loads(x.decode('utf-8-sig')) for x in archive_bytes]
    assert old1['protocol_commit'] == 'eacb47a' and old1['draws'] == 999
    assert old2['protocol_commit'] == '4e1bfa5' and old3['protocol_commit'] == 'd6f5bde'
    assert len(old1['family_tests']) == 24 and len(old2['combined_tests']) == 36
    assert 52/(DRAWS+1) < .05 and DRAWS == 1999
    checked, bridges = archive_source_check(old3['source_code_sha256'])
    archive_source_check(old1['source_code_sha256'])
    archive_source_check(old2['source_code_sha256'])
    watched = list(checked)+['research/strategy_f3_placebo.py']
    before = hashes(watched)
    D, idx, lo, source, trade, returns, close, G, E, T, logs = F.load_material()
    dates = idx[lo:]
    raw = np.asarray(G.r_eq1, float)
    assert old1['asset_returns_sha256'] == old2['asset_returns_sha256'] == old3['asset_returns_sha256'] == F.digest(returns)
    assert old1['signal_returns_sha256'] == old3['signal_returns_sha256'] == F.digest(raw)
    assert (old1['start'], old1['end']) == (old3['start'], old3['end']) == (str(dates[0].date()), str(dates[-1].date()))
    seq = np.random.SeedSequence(F.SEED).spawn(2)[0]
    rows, orders, years, lengths = F.annual_permutations(dates, DRAWS, np.random.default_rng(seq))
    assert F.digest(rows[:999]) == old1['permutation_rows_sha256']
    assert F.digest(orders[:999]) == old1['permutation_orders_sha256'] == old2['permutation_orders_sha256']
    original = {n: close[n][lo:, 3 if n == 'Hold1' else 0] for n in F.NAMES}
    rebuilt = F.targets(pd.Series(np.cumprod(1+raw), index=idx), T.t4_w(raw), E.rule_dd)
    for name in F.NAMES:
        np.testing.assert_array_equal(rebuilt[name][lo:], close[name][lo:])
    # Two full raw streams for new F3; only the new 1000 draws for the other
    # old F1 families. Prefix returns remain fixed warm-up, exactly as F1.
    full_raw = {n: np.empty((DRAWS+1, len(dates))) for n in ('B', 'T4-mix')}
    extra_raw = {n: np.empty((1001, len(dates))) for n in ('A', 'MA200-mix', 'MOM252-mix')}
    for n in full_raw:
        full_raw[n][0] = original[n]
    for n in extra_raw:
        extra_raw[n][0] = original[n]
    for draw, row in enumerate(rows, 1):
        fake = raw.copy(); fake[lo:] = raw[lo:][row]
        w = F.targets(pd.Series(np.cumprod(1+fake), index=idx), T.t4_w(fake), E.rule_dd)
        for n in full_raw:
            full_raw[n][draw] = w[n][lo:, 0]
        if draw >= 1000:
            for n in extra_raw:
                extra_raw[n][draw-999] = w[n][lo:, 0]
        if draw % 200 == 0:
            print(f'F3 P2 raw signals rebuilt {draw}/{DRAWS}', file=sys.stderr, flush=True)
    baseline, _, _ = F.gross_batch(original['B'][source, None], 'B', returns, trade)
    bwm = F.window_metrics(baseline, dates)
    lower5 = {y: float(bwm[y]['lower5'][0]) for y in (7, 10)}
    tests, details, references = [], {}, []
    oldtests = {(x['mode'], x['name'], x['metric']): x for x in old2['combined_tests']}
    assert len(oldtests) == 36
    expected_old = {(mode, name, metric) for mode in MODES for name in [*F.FAMILIES, *FIXED] for metric in METRICS}
    assert set(oldtests) == expected_old
    parents = parent_weights(original['B'], original['T4-mix'])
    for mode in MODES:
        details[mode] = {}
        # Old comparisons: exact archived 999 exceedances plus 1000 new draws.
        for name in [*F.FAMILIES, *FIXED]:
            if name in FIXED:
                orig = parents[name]
                x = (np.vstack([orig, orig[rows[999:]]]) if mode.startswith('P1') else
                     mixture(full_raw['B'][np.r_[0, np.arange(1000, 2000)]],
                             full_raw['T4-mix'][np.r_[0, np.arange(1000, 2000)]], FIXED[name]))
                engine_name = 'T4-mix'
            else:
                orig = original[name]
                if mode.startswith('P1'):
                    x = np.vstack([orig, orig[rows[999:]]])
                elif name in ('B', 'T4-tb', 'T4-mix'):
                    x = full_raw['B' if name == 'B' else 'T4-mix'][np.r_[0, np.arange(1000, 2000)]]
                else:
                    x = extra_raw[name]
                engine_name = name
            assert x.shape == (1001, len(dates))
            executed = x[:, source].T
            curves, _, _ = F.gross_batch(executed, engine_name, returns, trade)
            scores = F.score(curves, dates, lower5)
            for metric in METRICS:
                prior = (old2['timing'][mode][name][metric] if name in FIXED else
                         old1['results'][mode][name]['scores'][metric])
                # This exact equality is stricter than the earlier display
                # tolerances; no approximate observation can inherit a count.
                assert float(scores[metric][0]) == prior['observed'], ('observed statistic drift', mode, name, metric)
                oldtest = oldtests[(mode, name, metric)]
                assert prior['tail'] == oldtest['raw_p']
                old_count = recovered_count(prior['tail'], 999)
                new_count = int(np.count_nonzero(scores[metric][1:] >= scores[metric][0]))
                tests.append(dict(scope='F2' if name in FIXED else 'F1', mode=mode, name=name, metric=metric,
                    observed=float(scores[metric][0]), old_999_count=old_count, new_1000_count=new_count,
                    exceedances=old_count+new_count, raw_p=(1+old_count+new_count)/2000,
                    old_999_raw_p=oldtest['raw_p'], old_999_combined36_p=oldtest['combined_36_holm_p']))
            ref = F.units_reference(executed[:, 1], engine_name, returns, trade)
            error = float(np.max(np.abs(curves[:, 1]/ref-1)))
            assert error < 2e-10
            references.append(dict(mode=mode, name=name, draw=1000, max_error=error))
            details[mode][name] = dict(kind='old999_counts_plus_new1000',
                new_null={m: distribution(scores[m][1:]) for m in METRICS}, actual_curve_sha256=F.digest(curves[:, 0]))
            print(f'F3 {mode} extends {name}: old999+new1000 checked', file=sys.stderr, flush=True)
        # New F3 candidates: ALL 1999 nulls, irrespective of account results.
        for name in PARENTS:
            x = (np.vstack([parents[name], parents[name][rows]]) if mode.startswith('P1') else
                 full_raw['T4-mix'] if name == 'T4-mix' else mixture(full_raw['B'], full_raw['T4-mix'], FIXED[name]))
            executed = x[:, source].T
            q = P.gross_batch(executed, returns, trade, fee=.001, band=.10)
            curves = q.pop('curves')
            candidate = name+'-E10'
            assert F.digest(curves[:, 0]) == old3['gross']['base']['fixed'][candidate]['curve_sha256']
            for key in ('forced_defense_violations', 'uninvested_cash_violations', 'closed_day_trade_violations'):
                assert q[key].sum() == 0, (mode, candidate, key)
            scores = F.score(curves, dates, lower5)
            for metric in METRICS:
                count = int(np.count_nonzero(scores[metric][1:] >= scores[metric][0]))
                tests.append(dict(scope='F3', mode=mode, name=candidate, metric=metric,
                    observed=float(scores[metric][0]), exceedances=count, raw_p=(1+count)/2000))
            for draw in (0, 1):
                p = F.make_positions(executed[:, draw], 'T4-mix')
                ref = units_reference(p, returns, trade, 0, len(dates)-1, [], [], 1., .001, 0.,
                                      np.zeros_like(returns), .10)
                error = float(np.max(np.abs(curves[:, draw]/ref['paths']-1)))
                assert error < 2e-10 and ref['trade_days'] == q['trade_days'][draw]
                references.append(dict(mode=mode, name=candidate, draw=draw, max_error=error))
            details[mode][candidate] = dict(kind='all1999_new', null={m: distribution(scores[m][1:]) for m in METRICS},
                actual_curve_sha256=F.digest(curves[:, 0]), full_curve_matrix_sha256=F.digest(curves),
                mean_attack_exposure=distribution(q['mean_attack_exposure']),
                original_trade_days=int(q['trade_days'][0]))
            print(f'F3 {mode} {candidate}: all1999 banded paths checked', file=sys.stderr, flush=True)
    assert len(tests) == 52 and len({(v['mode'], v['name'], v['metric']) for v in tests}) == 52
    for label, scopes in [('holm24_at1999', ('F1',)), ('holm36_at1999', ('F1', 'F2')),
                          ('holm52_at1999', ('F1', 'F2', 'F3'))]:
        selected = [t for t in tests if t['scope'] in scopes]
        for test, adjusted in zip(selected, F.holm_adjust([t['raw_p'] for t in selected])):
            test[label] = float(adjusted)
    # Constant controls are unaffected by either permutation, not a selected
    # profitable null. The complete draw axis is actually run and compared.
    negative = {}
    for name, attack in [('Hold1', 3), ('Hold2', 0)]:
        q = P.gross_batch(np.ones((len(dates), 2000)), returns, trade, band=.10, attack_index=attack)
        c = q['curves']
        np.testing.assert_array_equal(c, np.broadcast_to(c[:, :1], c.shape))
        prior, _, _ = F.gross_batch(np.ones((len(dates), 1)), name, returns, trade)
        np.testing.assert_array_equal(c[:, 0], prior[:, 0])
        negative[name] = dict(paths=2000, all_identical=True, trade_days=int(q['trade_days'].sum()))
    assert before == hashes(watched)
    assert archive_bytes == [p.read_bytes() for p in paths]
    survives = {name: all(t['holm52_at1999'] < .05 for t in tests if t['name'] == name)
                for name in [*F.FAMILIES, *FIXED, *[p+'-E10' for p in PARENTS]]}
    output = dict(protocol_commit='d6f5bde', draws=1999, family_size=52, seed=F.SEED,
        source_code_sha256=before, reference_fixture_bridges=bridges,
        archive_sha256=[hashlib.sha256(x).hexdigest() for x in archive_bytes],
        asset_returns_sha256=F.digest(returns), signal_returns_sha256=F.digest(raw),
        prefix999_rows_sha256=F.digest(rows[:999]), prefix999_orders_sha256=F.digest(orders[:999]),
        full1999_rows_sha256=F.digest(rows), full1999_orders_sha256=F.digest(orders),
        year_blocks=[dict(year=int(y), rows=int(n)) for y, n in zip(years, lengths)],
        exact_identity_all_signals=True, archived_counts_extended_after_exact_checks=True,
        tests=tests, timing_survives_combined52=survives, details=details, negative_controls=negative,
        independent_reference_paths=references, max_independent_relative_error=max(v['max_error'] for v in references),
        limitations=['Year-block exchangeability and joined regimes remain assumptions, not new OOS.',
          'Old 24/36 tests now use1999 draws; separate24/36/52 adjustments isolate family expansion.',
          'Even52 tests do not correct all historical 500+ searches or prove future profits.',
          'Gross inherited-state curves are not fresh-start deposit/tax accounts or adoption.'],
        next_question='Do any fixed execution candidates satisfy the joint account/economics and timing criteria without new parameter tuning?', diagnostics=logs)
    print('RESULT_JSON')
    print(json.dumps(output, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
