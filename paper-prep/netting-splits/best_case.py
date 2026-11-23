"""Netting under the household split: the allocation most favourable to netting.

The half of the problem the paper's claim needs: over every allocation of
household debt consistent with the published totals (households.py), the
smallest debt stock netting can leave. One linear programme per year and variant, a few
seconds in all. Reported for pairwise netting (the paper's benchmark) and the
most generous multilateral netting (C), with the judgement calls J4 and J8 kept
and dropped (dropping them can only help netting). Checks on every year:
pairwise >= multilateral, relaxed <= kept, and netting >= the split kernel.
From the repository root (needs numpy and scipy):
    python3 -I paper-prep/netting-splits/best_case.py [--json]
Exits with status 1 if a check fails.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import households as hh
from run_households import split_minimum


def main():
    ser = {x['year']: x for x in json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/broad-debt/series.py', '--json']))}
    I = hh.inputs(); out = []; bad = []
    for y in sorted(I):
        inp = I[y]; D = inp['D']; m = split_minimum(inp, ser[y])
        left = lambda variant, pw, relax=(): D - hh.network(inp, variant, relax).most_favourable(pairwise=pw)[0]
        r = dict(year=y, split_min=m, pairwise=left('A', True), pairwise_relaxed=left('A', True, ('J4', 'J8')),
                 multilateral=left('C', False), multilateral_relaxed=left('C', False, ('J4', 'J8')))
        e = 1e-6
        ok = (r['multilateral'] <= r['pairwise'] + e and r['pairwise_relaxed'] <= r['pairwise'] + e
              and r['multilateral_relaxed'] <= r['multilateral'] + e and r['multilateral_relaxed'] >= m - 1e-3)
        if not ok:
            bad.append(y)
        r['checks_pass'] = ok
        out.append(r)
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        print('USD trillions: debt netting leaves under the allocation most favourable to netting; ratio to the split kernel')
        print('year | split kernel | pairwise (J4, J8 dropped) | multilateral C (J4, J8 dropped) | checks')
        for r in out:
            f = lambda k: f"{r[k]:.2f} ({r[k] / r['split_min']:.3f})"
            print(f"{r['year']} | {r['split_min']:.2f} | {f('pairwise')}, {f('pairwise_relaxed')} | {f('multilateral')}, {f('multilateral_relaxed')} | "
                  + ('pass' if r['checks_pass'] else 'FAIL'))
        for k in ('pairwise', 'pairwise_relaxed', 'multilateral', 'multilateral_relaxed'):
            lo = min(out, key=lambda r: r[k] / r['split_min'])
            print(f"lowest ratio, {k}: {lo[k] / lo['split_min']:.3f} ({lo['year']})")
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
