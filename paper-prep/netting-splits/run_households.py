"""Netting under the household split, 2001-2025, both ends.

For each year: the split kernel (households in five DFA wealth groups,
rescaled to the March Z.1, as slice_checks.py), and the debt netting leaves
under the allocation most favourable to netting and the one least favourable,
pairwise and multilateral (claim sets A and C; B is reported for the most
favourable end). Checks on every year:

  - pairwise: netting_range.py's hand bounds bracket the exact values;
  - most favourable <= least favourable; multilateral <= pairwise; C <= A;
  - netting never leaves less than the split kernel;
  - each least-favourable value has a witness allocation (see netting_lp.py).

The least-favourable figure reported is always certified: the debt netting
leaves under an allocation the published totals allow. With K = 2 it is the
exact worst case when 'witnessed' is true, and otherwise a lower bound on it
(the worst case can only be worse). The runner exits with status 1 if any
check fails. Tested with Python 3.14, NumPy 2.5 and SciPy 1.18; an older SciPy
(1.13) gave wrong results.

From the repository root (needs numpy and scipy):
    python3 -I paper-prep/netting-splits/run_households.py [years...] [--check | --resume] [--full-K]
Results accumulate in paper-prep/netting-splits/households-results.json.
With --check nothing is written: each year is recomputed and compared with the
stored results (most favourable end to 1e-6, least favourable end to 1e-3 USD
trillions, which absorbs differences between SciPy versions); the runner exits
with status 1 on any difference. With --resume, years already stored are
skipped. Without a year, all 25 years run, which takes hours; run one process
at a time, since the solver already uses several threads.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import households as hh

OUT = 'paper-prep/netting-splits/households-results.json'
pos = lambda x: max(0.0, x)


def split_minimum(inp, s):
    gaps = [x['Loans (Liabilities)'] - x['Debt securities'] - x['Loans (Assets)'] for x in inp['groups'].values()]
    return s['tnd'] + sum(pos(x) for x in gaps) + pos(s['gap_d'] - sum(gaps)) + pos(s['gap_r'])


def main():
    full = '--full-K' in sys.argv
    check = '--check' in sys.argv
    resume = '--resume' in sys.argv
    years = [int(a) for a in sys.argv[1:] if a.isdigit()]
    ser = {x['year']: x for x in json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/broad-debt/series.py', '--json']))}
    hand = {x['year']: x for x in json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/sector-slicing/netting_range.py', '--json']))}
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    stored = json.load(open(OUT)) if check else {}
    I = hh.inputs()
    failed = []
    for y in years or sorted(I):
        if resume and str(y) in res:
            continue
        inp = I[y]; D = inp['D']; K = None if full else 2
        row = dict(debt=D, split_min=split_minimum(inp, ser[y]))
        for name, variant, pw in (('pairwise', 'A', True), ('A', 'A', False), ('B', 'B', False), ('C', 'C', False)):
            N = hh.network(inp, variant)
            row[name + '_most'] = D - N.most_favourable(pairwise=pw)[0]
            if name != 'B':
                v, _, ok, attained = N.least_favourable(pairwise=pw, K=K)
                row[name + '_least'] = D - attained          # certified: an allowed allocation leaves this much
                row[name + '_least_bound'] = D - v           # what the solver's bound gives (equal when witnessed)
                row[name + '_witnessed'] = ok
        e = 1e-6
        h = hand[y]
        checks = {
            'hand bounds bracket pairwise': h['netting_split_lo'] - e <= row['pairwise_most'] <= row['pairwise_least'] <= h['netting_split_hi'] + e,
            'most <= least': all(row[k + '_most'] <= row[k + '_least'] + e for k in ('pairwise', 'A', 'C')),
            'multilateral <= pairwise, C <= B <= A': row['A_most'] <= row['pairwise_most'] + e and row['C_most'] <= row['B_most'] + e <= row['A_most'] + 2 * e
                                                    and row['A_least'] <= row['pairwise_least'] + e and row['C_least'] <= row['A_least'] + e,
            'netting >= split least debt': row['C_most'] >= row['split_min'] - 1e-3,
        }
        row['exact_worst_case'] = all(row[k + '_witnessed'] for k in ('pairwise', 'A', 'C'))   # information, not a check
        row['checks'] = checks; row['full_K'] = full
        if check:
            old = stored.get(str(y))
            tol = lambda k: 1e-3 if k.endswith('_least') or k.endswith('_least_bound') else 1e-6
            diff = ['missing'] if old is None else [k for k, v in row.items() if isinstance(v, float) and not abs(v - old.get(k, float('nan'))) <= tol(k)]
            checks['matches stored results'] = not diff
        else:
            res[str(y)] = row
            with open(OUT, 'w') as f:
                json.dump(res, f, indent=1)
                f.write('\n')
        print(y, f"split kernel {row['split_min']:.2f} | pairwise {row['pairwise_most']:.2f}-{row['pairwise_least']:.2f} | "
                 f"A {row['A_most']:.2f}-{row['A_least']:.2f} | B {row['B_most']:.2f} | C {row['C_most']:.2f}-{row['C_least']:.2f} | "
                 + ('' if row['exact_worst_case'] else 'worst case is a lower bound | ')
                 + ('all checks pass' if all(checks.values()) else 'FAILED: ' + ', '.join(k for k, v in checks.items() if not v)), flush=True)
        if not all(checks.values()):
            failed.append(y)
    if failed:
        print('checks failed in', failed)
        sys.exit(1)


if __name__ == '__main__':
    main()
