"""F2 fixed B/T4 target mixtures; protocol 4e1bfa5, section 14.

Read-only gross study. No personal inputs/outputs, live signals or orders.
The archived F1 JSON supplies 24 existing tests for the combined Holm family.
Random alpha draws are descriptive only; never select a winner among them.
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

FIXED = {'BTmix25': .25, 'BTmix50': .5, 'BTmix75': .75}


def mixture(b, t, x):
    """Elementwise target mixture; caller explicitly supplies broadcasting axes."""
    b, t, x = (np.asarray(v, float) for v in (b, t, x))
    for v in (b, t, x):
        if not np.isfinite(v).all() or (v < 0).any() or (v > 1).any():
            raise ValueError('finite weights in [0,1] required')
    return x*b+(1-x)*t


def random_alphas():
    rng = np.random.default_rng(np.random.SeedSequence(F.SEED).spawn(3)[2])
    x = rng.uniform(0., 1., 200)
    assert ((x > 0) & (x < 1)).all()
    return x


def distribution(values):
    v = np.asarray(values, float)
    return dict(minimum=float(v.min()), lower5=float(np.quantile(v,.05)),
                median=float(np.median(v)), upper95=float(np.quantile(v,.95)),
                maximum=float(v.max()), sha256=F.digest(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--f1-result', type=Path, required=True,
                    help='archived F1 timing JSON, read only; path is not emitted')
    args = ap.parse_args()
    archive_bytes = args.f1_result.read_bytes()
    old = json.loads(archive_bytes.decode('utf-8-sig'))
    assert old['protocol_commit'] == 'eacb47a' and old['seed'] == F.SEED and old['draws'] == 999
    assert len(old['family_tests']) == 24 and 36/(F.DRAWS+1) < .05
    expected = {(m,n,s) for m in ('P1_target_blocks','P2_raw_return_blocks')
                for n in F.FAMILIES for s in ('calmar','weak_tail')}
    assert {(v['mode'],v['name'],v['metric']) for v in old['family_tests']} == expected
    watched = list(old['source_code_sha256'])+['research/strategy_f2_mix.py']
    before = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in watched}
    for p, value in old['source_code_sha256'].items():
        assert before[p] == value, ('F1 source drift', p)
    D, idx, lo, source, trade, returns, close, G, E, T, logs = F.load_material()
    dates = idx[lo:]
    assert old['asset_returns_sha256'] == F.digest(returns)
    assert old['signal_returns_sha256'] == F.digest(np.asarray(G.r_eq1,float))
    assert (old['start'],old['end']) == (str(dates[0].date()),str(dates[-1].date()))
    b, t = close['B'][lo:,0], close['T4-mix'][lo:,0]
    x = np.r_[1., 0., list(FIXED.values()), random_alphas()]
    names = ['B','T4-mix',*FIXED]
    close_w = mixture(b[:,None],t[:,None],x[None,:])
    np.testing.assert_array_equal(close_w[:,0], b)
    np.testing.assert_array_equal(close_w[:,1], t)
    import hist_korea as K
    late, late_trade = F.execution_events(idx,K.kr_caldays(),lo,1)
    conditions = [('base',.001,source,trade),('cost2',.002,source,trade),
                  ('delay1',.001,late-lo,late_trade)]
    gross, refs, actual = {}, [], {}
    for label, fee, src, mask in conditions:
        w = close_w[src]
        curves, turnover, ndays = F.gross_batch(w,'T4-mix',returns,mask,fee)
        bw = F.window_metrics(curves[:,:1], dates)
        baseline = {y:float(bw[y]['lower5'][0]) for y in (7,10)}
        scores = F.score(curves,dates,baseline)
        span = (dates[-1]-dates[0]).days/365.25
        scores['trade_days_per_year'] = ndays/span
        scores['turnover_per_year'] = turnover/span
        scores['volatility'] = np.std(curves[1:]/curves[:-1]-1,axis=0,ddof=1)*np.sqrt(252)
        gross[label] = dict(fixed={}, random_alpha={k:distribution(v[5:]) for k,v in scores.items()})
        for j,name in enumerate(names):
            p = np.array([F.make_positions([v],'T4-mix')[0] for v in w[:,j]])
            single = F.account_windows(p,returns,mask,[0],[len(dates)-1],np.empty((0,1),int),[],
                1.,fee=fee,record_paths=True)['paths'][:,0]
            np.testing.assert_allclose(curves[:,j],single,rtol=2e-12,atol=1e-12)
            ref = F.units_reference(w[:,j],'T4-mix',returns,mask,fee)
            err = float(np.max(np.abs(curves[:,j]/ref-1))); refs.append(err)
            assert err < 2e-10
            gross[label]['fixed'][name] = {k:float(v[j]) for k,v in scores.items()}
            gross[label]['fixed'][name]['curve_sha256'] = F.digest(curves[:,j])
            if label == 'base':
                actual[name] = curves[:,j].copy()
                if name in ('B','T4-mix'):
                    for k,v in old['results']['P1_target_blocks'][name]['scores'].items():
                        np.testing.assert_allclose(scores[k][j],v['observed'],rtol=2e-12,atol=2e-12)
        print(f'F2 {label}: 3 fixed, 2 controls, 200 random alpha paths',file=sys.stderr,flush=True)
    seq_perm, seq_window = np.random.SeedSequence(F.SEED).spawn(2)
    rows, orders, _, _ = F.annual_permutations(dates,F.DRAWS,np.random.default_rng(seq_perm))
    assert F.digest(rows) == old['permutation_rows_sha256']
    assert F.digest(orders) == old['permutation_orders_sha256']
    raw_b, raw_t = np.empty((1000,len(dates))), np.empty((1000,len(dates)))
    raw_b[0],raw_t[0] = b,t
    raw = np.asarray(G.r_eq1,float)
    identity = F.targets(pd.Series(np.cumprod(1+raw),index=idx),T.t4_w(raw),E.rule_dd)
    np.testing.assert_array_equal(identity['B'][lo:,0],b)
    np.testing.assert_array_equal(identity['T4-mix'][lo:,0],t)
    for draw,row in enumerate(rows,1):
        fake = raw.copy(); fake[lo:] = raw[lo:][row]
        signals = F.targets(pd.Series(np.cumprod(1+fake),index=idx),T.t4_w(fake),E.rule_dd)
        raw_b[draw],raw_t[draw] = signals['B'][lo:,0],signals['T4-mix'][lo:,0]
    bw = F.window_metrics(actual['B'][:,None],dates)
    lower5 = {y:float(bw[y]['lower5'][0]) for y in (7,10)}
    tests = [dict(v, scope='F1') for v in old['family_tests']]
    timing = {}
    for mode in ('P1_target_blocks','P2_raw_return_blocks'):
        timing[mode] = {}
        for name,alpha in FIXED.items():
            original = mixture(b,t,alpha)
            close_paths = (np.vstack([original,original[rows]]) if mode.startswith('P1')
                           else mixture(raw_b,raw_t,alpha))
            w = close_paths[:,source].T
            curves,_,_ = F.gross_batch(w,'T4-mix',returns,trade)
            np.testing.assert_allclose(curves[:,0],actual[name],rtol=2e-12,atol=2e-12)
            ref = F.units_reference(w[:,1],'T4-mix',returns,trade)
            err = float(np.max(np.abs(curves[:,1]/ref-1))); refs.append(err)
            assert err < 2e-10
            scores = F.score(curves,dates,lower5)
            timing[mode][name] = {}
            for metric, values in scores.items():
                pval = F.tail_probability(values[0],values[1:])
                timing[mode][name][metric] = dict(observed=float(values[0]),tail=pval,
                                                 null=distribution(values[1:]))
                if metric in ('calmar','weak_tail'):
                    tests.append(dict(scope='F2',mode=mode,name=name,metric=metric,raw_p=pval))
            print(f'F2 {mode} {name}: 999 paths',file=sys.stderr,flush=True)
    adjusted = F.holm_adjust([v['raw_p'] for v in tests])
    for v,padj in zip(tests,adjusted):
        if 'holm_p' in v:
            v['original_F1_24_holm_p'] = v.pop('holm_p')
        v['combined_36_holm_p'] = float(padj)
    survives = {n:all(v['combined_36_holm_p'] < .05 for v in tests if v['name']==n)
                for n in [*F.FAMILIES,*FIXED]}
    s,e,months = F.random_intervals(dates,5000,np.random.default_rng(seq_window))
    pairs_hash = F.digest(np.column_stack([s,e,months]))
    assert pairs_hash == old['random_intervals']['pairs_sha256']
    base = actual['B'][e]/actual['B'][s]
    intervals = {}
    for n,c in actual.items():
        values = c[e]/c[s]/base
        intervals[n] = dict(**distribution(values),fraction_above_B=float(np.mean(values>1)))
    after = {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in watched}
    assert before == after, 'code changed during run'
    output = dict(protocol_commit='4e1bfa5',source_code_sha256=before,
        f1_archive_sha256=hashlib.sha256(archive_bytes).hexdigest(),
        asset_returns_sha256=F.digest(returns),permutation_orders_sha256=F.digest(orders),
        random_alpha_values=x[5:].tolist(),random_alpha_sha256=F.digest(x[5:]),
        gross=gross,timing=timing,combined_tests=tests,timing_survives_combined_36=survives,
        random_intervals=intervals,random_interval_pairs_sha256=pairs_hash,
        independent_reference_paths=len(refs),max_independent_relative_error=max(refs),
        limitations=['No deposits/tax/real ETF execution; gross proxy only.',
         'Random-alpha gross distribution is not account-parameter robustness or a winner search.',
         'Same reused history; Holm36 differs from F1 Holm24, neither corrects all past research.',
         'No new OOS, orders, live strategy changes or investment recommendation.'],
        next_question='Do the fixed mixtures retain goal-account economics after turnover and deposits?',diagnostics=logs)
    print('RESULT_JSON')
    print(json.dumps(output,ensure_ascii=True,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
