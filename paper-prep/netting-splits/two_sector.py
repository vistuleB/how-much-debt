"""The two-sector network (domestic d, rest of the world r) from a stored balance
sheet: every amount known. Used to check netting_lp.py against the existing
scripts. Claim sets A, B, C as in paper-prep/broad-debt/netting_multilateral.py."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from netting_lp import Network


def network(o, variant='A'):
    v = lambda k: o.get(k, 0)
    N = Network(['d', 'r', 't', 'b', 'f'])
    for h in 'bfdr':
        for s in 'dr':
            for p in ('l_', 'a_', 'z_'):
                N.claim(h, s, True, v(p + h + s))       # includes self-claims d->d, r->r
    for s in 'dr':
        for k in ('s_' + s, 'a_t' + s, 'z_t' + s):
            N.claim('t', s, True, v(k))
        N.claim(s, 't', True, v(s + '_b'))
        N.claim(s, 'b', False, v(s + '_qbh'))
        N.claim(s, 'f', False, v(s + '_qh'))
    N.claim('b', 't', True, v('bb')); N.claim('f', 't', True, v('bf'))
    if variant in 'BC':
        N.claim('t', 'f', False, v('t')); N.claim('t', 'f', False, v('qg')); N.claim('b', 'f', False, v('r'))
        for h in 'bfdrt':
            for s in 'dr':
                N.claim(h, s, False, v('j_' + h + s) - v('a_' + h + s) - v('z_' + h + s))
    if variant == 'C':
        N.claim('f', 'b', False, v('u')); N.claim('b', 'f', False, v('cb'))
    return N


def main():
    """Compare all stored look-through openings; no unknown-allocation search."""
    import importlib.util
    import time
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, root / path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    multi = load('multi_reference', 'paper-prep/broad-debt/netting_multilateral.py')
    series = load('series_reference', 'paper-prep/broad-debt/series.py')
    started = time.perf_counter()
    count = 0
    failures = []
    for record in series.records():
        if (record['representation'] != 'agency_lookthrough'
                or record['nonbank_foreign_security_issuers'] != 'nonbank'
                or not record['securities_repayable'] or record['pooled']):
            continue
        opening, debt = record['opening'], record['opening_debt']
        for variant in 'ABC':
            graph = network(opening, variant)
            cancelled, _ = graph.most_favourable()
            actual = debt - cancelled
            expected = multi.netting(opening, debt, variant)
            if abs(actual - expected) > 0.01:  # USD 10,000, LP roundoff
                failures.append((record['id'], variant, actual, expected))
            if variant == 'A':
                cancelled, _ = graph.most_favourable(pairwise=True)
                actual = debt - cancelled
                expected = series.netting_only(opening, debt)
                if abs(actual - expected) > 0.01:
                    failures.append((record['id'], 'pairwise', actual, expected))
        count += 1
    if count != 240:
        failures.append(('opening count', count, 240))
    for failure in failures:
        print('FAIL:', failure)
    print(f'{count} openings, {count * 4} comparisons, {len(failures)} failures; '
          f'{time.perf_counter() - started:.3f} seconds')
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
