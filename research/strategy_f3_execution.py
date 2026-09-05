"""F3 gross execution study, section 16 / d6f5bde. Read-only, no private inputs.

This stage is descriptive gross economics, NOT the 52-test timing falsification
or fresh-start deposit-account study. Both remain separate required stages.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'research'), str(ROOT/'deploy')]
import numpy as np
import strategy_f1_placebo as F
from research.strategy_f2_mix import FIXED, mixture, distribution
from research import execution_policy as P
from audit.test_execution_policy import units_reference

PARENTS = ['T4-mix', *FIXED]
FIXED_BANDS = [0., .05, .10, .15]


def random_bands():
    return np.random.default_rng(np.random.SeedSequence(F.SEED).spawn(4)[3]).uniform(.05, .15, 200)


def name_for(parent, band):
    return parent if band == 0 else f'{parent}-E{round(band*100):02d}'


def parent_weights(b, t):
    return {'T4-mix': np.asarray(t, float), **{n: mixture(b, t, x) for n, x in FIXED.items()}}


def hashes(paths):
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}


def archive_source_check(expected):
    """Fail closed except the independently verified historical TEST fixture."""
    current = hashes(expected)
    bridges = []
    for path, old in expected.items():
        if current[path] == old:
            continue
        assert path == 'audit/test_account_ledger.py', ('source drift', path)
        assert old == '7a48cc8d72804299fb007addd0d0d630e92cc001d7467ff875343a36401eabc4'
        assert current[path] == '245998b71effb6129a29b83a9c6c0b9dc06de5bd5b9ce0bb086e9f9f729e3a70'
        prior = subprocess.check_output(['git', 'show', 'b6778e0'], cwd=ROOT, text=True, encoding='utf-8')
        def functions(source):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name in ('trade_reference', 'path_reference')}
        a, b = functions(prior), functions((ROOT/path).read_text(encoding='utf-8'))
        assert len(a) == 2 and a == b
        bridges.append('One public synthetic fixture changed; independent trade/path function ASTs unchanged.')
    return current, bridges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--f1-result', type=Path, required=True)
    ap.add_argument('--f2-result', type=Path, required=True)
    args = ap.parse_args()
    archives = [args.f1_result.read_bytes(), args.f2_result.read_bytes()]
    old1, old2 = [json.loads(x.decode('utf-8-sig')) for x in archives]
    assert old1['protocol_commit'] == 'eacb47a' and old2['protocol_commit'] == '4e1bfa5'
    checked, bridges = archive_source_check(old2['source_code_sha256'])
    watched = list(checked)+['research/rebalance_accounting.py', 'research/execution_policy.py',
                            'research/strategy_f3_execution.py', 'audit/test_execution_policy.py']
    before = hashes(watched)
    D, idx, lo, source, trade, returns, close, G, E, T, logs = F.load_material()
    dates = idx[lo:]
    assert old1['asset_returns_sha256'] == old2['asset_returns_sha256'] == F.digest(returns)
    assert old1['signal_returns_sha256'] == F.digest(np.asarray(G.r_eq1, float))
    assert (old1['start'], old1['end']) == (str(dates[0].date()), str(dates[-1].date()))
    parents = parent_weights(close['B'][lo:, 0], close['T4-mix'][lo:, 0])
    bands = np.r_[FIXED_BANDS, random_bands()]
    close_w = np.column_stack([np.tile(parents[n][:, None], (1, len(bands))) for n in PARENTS])
    bandvec = np.tile(bands, len(PARENTS))
    import hist_korea as K
    late, late_trade = F.execution_events(idx, K.kr_caldays(), lo, 1)
    conditions = [('base', .001, source, trade), ('cost2', .002, source, trade),
                  ('delay1', .001, late-lo, late_trade), ('cost0', 0., source, trade)]
    seq = np.random.SeedSequence(F.SEED).spawn(2)[1]
    s, e, months = F.random_intervals(dates, 5000, np.random.default_rng(seq))
    pairs_hash = F.digest(np.column_stack([s, e, months]))
    assert pairs_hash == old1['random_intervals']['pairs_sha256'] == old2['random_interval_pairs_sha256']
    gross, refs, reductions = {}, [], []
    span = (dates[-1]-dates[0]).days/365.25
    for condition, fee, src, mask in conditions:
        bw = close['B'][lo:, 0][src, None]
        bc, bt, bd = F.gross_batch(bw, 'B', returns, mask, fee)
        windows = F.window_metrics(bc, dates)
        tail = {y: float(windows[y]['lower5'][0]) for y in (7, 10)}
        out = P.gross_batch(close_w[src], returns, mask, fee=fee, band=bandvec)
        curves = out.pop('curves')
        stats = F.score(curves, dates, tail)
        stats.update(trade_days_per_year=out['trade_days']/span, turnover_per_year=out['turnover']/span,
                     volatility=np.std(curves[1:]/curves[:-1]-1, axis=0, ddof=1)*np.sqrt(252),
                     mean_attack_exposure=out['mean_attack_exposure'], max_target_gap=out['max_target_gap'])
        bs = F.score(bc, dates, tail)
        bs.update(trade_days_per_year=bd/span, turnover_per_year=bt/span,
                  volatility=np.std(bc[1:]/bc[:-1]-1, axis=0, ddof=1)*np.sqrt(252))
        gross[condition] = dict(fixed={'B': {k: float(v[0]) for k, v in bs.items()}},
                                random_bands={}, violations={})
        for key in ('forced_defense_violations', 'uninvested_cash_violations', 'closed_day_trade_violations'):
            count = int(out[key].sum()); assert count == 0, (condition, key, count)
            gross[condition]['violations'][key] = count
        for i, parent in enumerate(PARENTS):
            first = i*len(bands)
            # All parents, all cost/delay conditions: exact old monetary curve.
            original, ot, od = F.gross_batch(parents[parent][src, None], 'T4-mix', returns, mask, fee)
            np.testing.assert_array_equal(curves[:, first], original[:, 0])
            np.testing.assert_array_equal(out['trade_days'][first], od[0])
            np.testing.assert_array_equal(out['turnover'][first], ot[0])
            reductions.append(dict(condition=condition, parent=parent, exact=True))
            if condition != 'cost0':
                prior = old2['gross'][condition]['fixed'][parent]
                for metric in ('cagr', 'mdd', 'volatility', 'trade_days_per_year'):
                    np.testing.assert_allclose(stats[metric][first], prior[metric], rtol=2e-11, atol=2e-11)
            for j, band in enumerate(FIXED_BANDS):
                col = first+j
                n = name_for(parent, band)
                row = {k: float(v[col]) for k, v in stats.items()}
                row.update(parent=parent, band=band, curve_sha256=F.digest(curves[:, col]))
                values = curves[e, col]/curves[s, col]/(bc[e, 0]/bc[s, 0])
                row['random_interval_ratios_to_B'] = dict(**distribution(values), fraction_above_B=float(np.mean(values > 1)))
                gross[condition]['fixed'][n] = row
            gross[condition]['random_bands'][parent] = {k: distribution(v[first+4:first+len(bands)]) for k, v in stats.items()}
            # Primary every condition, zero and two fixed random neighbours in base.
            check_cols = [first+2]+([first, first+4, first+5] if condition == 'base' else [])
            for col in check_cols:
                p = F.make_positions(close_w[src, col], 'T4-mix')
                ref = units_reference(p, returns, mask, 0, len(dates)-1, [], [], 1., fee, 0.,
                                      np.zeros_like(returns), bandvec[col])
                error = float(np.max(np.abs(curves[:, col]/ref['paths']-1)))
                assert error < 2e-10, (condition, parent, col, error)
                assert out['trade_days'][col] == ref['trade_days']
                refs.append(dict(condition=condition, parent=parent, band=float(bandvec[col]), max_error=error))
        print(f'F3 gross {condition}: four parents, fixed and 200 common random bands checked', file=sys.stderr, flush=True)
    assert hashes(watched) == before
    assert [args.f1_result.read_bytes(), args.f2_result.read_bytes()] == archives
    output = dict(protocol_commit='d6f5bde', start=str(dates[0].date()), end=str(dates[-1].date()),
        source_code_sha256=before, reference_fixture_bridges=bridges,
        asset_returns_sha256=F.digest(returns), signal_returns_sha256=F.digest(np.asarray(G.r_eq1, float)),
        archive_sha256=[hashlib.sha256(x).hexdigest() for x in archives],
        random_band_values=bands[4:].tolist(), random_band_sha256=F.digest(bands[4:]),
        random_interval_pairs_sha256=pairs_hash, gross=gross,
        zero_band_reductions=reductions, independent_reference_paths=refs,
        max_independent_relative_error=max(v['max_error'] for v in refs),
        rolling_windows={str(y): dict(starts=windows[y]['starts'], nonoverlap=windows[y]['nonoverlap']) for y in (7, 10)},
        limitations=['Gross proxy, not fresh-start deposit accounts or actual Korean ETF tax-base taxation.',
          'Random-band and inherited-state intervals are descriptive; no parameter promotion.',
          '52-test/1999-draw timing falsification not performed by this script.',
          'No new OOS, internal basket order count, whole shares, live signal changes or actual orders.'],
        next_question='Do fewer actual trades preserve fresh-start 7/10-year funded outcomes, including the two neighbouring bands?',
        diagnostics=logs)
    print('RESULT_JSON')
    print(json.dumps(output, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
