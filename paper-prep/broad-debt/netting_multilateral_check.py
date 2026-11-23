"""Independent check of netting_multilateral.py with a linear-programme solver.

Rebuilds the netting network on every balance sheet from the definitions in
netting_multilateral.py's docstring, without importing its code, and solves
each variant (A, B, C) as a linear programme: maximise the debt cancelled,
over cancellations x_e between 0 and each claim's amount, such that every
party's claims fall by as much as its debts (every net position unchanged).
Claims a sector holds on itself cancel in full. Compares, for every year, the
first balance sheet's netting and the range of netting / kernel across the
year's balance sheets with netting_multilateral.py --json, to USD 1,000.
Needs numpy and scipy. From the repository root:
    python3 -I paper-prep/broad-debt/netting_multilateral_check.py
"""
import json
import subprocess
import sys

import numpy as np
from scipy.optimize import linprog

FILES = ['fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json',
         'broad-debt-model/corrected-results.json',
         'fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json']
PARTIES = ['d', 'r', 't', 'b', 'f']
SECTORS = ['d', 'r']


def claims(o, variant):
    """List of (holder, issuer, is_debt, amount), self-claims excluded."""
    v = lambda k: o.get(k, 0)
    out = []
    for h in ['b', 'f', 'd', 'r']:                       # loans, additional loans, securities
        for s in SECTORS:
            for p in ['l_', 'a_', 'z_']:
                out.append((h, s, True, v(p + h + s)))
    for s in SECTORS:
        out += [('t', s, True, v('s_' + s)), ('t', s, True, v('a_t' + s)), ('t', s, True, v('z_t' + s)),
                (s, 't', True, v(s + '_b')),             # Treasury bonds held by sectors
                (s, 'b', False, v(s + '_qbh')),          # nondeposit claims on the bank
                (s, 'f', False, v(s + '_qh'))]           # claims on the central bank
    out += [('b', 't', True, v('bb')), ('f', 't', True, v('bf'))]
    if variant in ('B', 'C'):
        out += [('t', 'f', False, v('t')), ('t', 'f', False, v('qg')), ('b', 'f', False, v('r'))]
        for h in ['b', 'f', 'd', 'r', 't']:
            for s in SECTORS:
                out.append((h, s, False, v('j_' + h + s) - v('a_' + h + s) - v('z_' + h + s)))
    if variant == 'C':
        out += [('f', 'b', False, v('u')), ('b', 'f', False, v('cb'))]
    return [c for c in out if c[0] != c[1] and c[3] > 1e-9]


def netting(o, D, variant):
    cs = claims(o, variant)
    A = np.zeros((len(PARTIES), len(cs)))
    for j, (h, i, _, _) in enumerate(cs):
        A[PARTIES.index(h), j] += 1
        A[PARTIES.index(i), j] -= 1
    r = linprog([-1.0 if c[2] else 0.0 for c in cs], A_eq=A, b_eq=np.zeros(len(PARTIES)),
                bounds=[(0, c[3]) for c in cs], method='highs')
    assert r.status == 0, r.message
    intra = sum(o.get(p + s + s, 0) for s in SECTORS for p in ['l_', 'a_', 'z_'])
    return D - intra + r.fun


def main():
    rows = {}
    for f in FILES:
        d = json.load(open(f))
        for r in (d['records'] if isinstance(d, dict) else d):
            if r['representation'] != 'agency_lookthrough' or r['nonbank_foreign_security_issuers'] != 'nonbank' \
                    or not r['securities_repayable'] or r['pooled']:
                continue
            o, D, K = r['opening'], r['opening_debt'], r['kernel']
            rows.setdefault(int(r['id'][:4]), []).append({v: netting(o, D, v) for v in 'ABC'} | {'K': K})
    ref = {x['year']: x for x in json.loads(subprocess.check_output(
        [sys.executable, '-I', 'paper-prep/broad-debt/netting_multilateral.py', '--json']))}
    names = {'A': 'multilateral', 'B': 'generous', 'C': 'most_generous'}
    bad = n = 0
    for y, xs in sorted(rows.items()):
        for v, name in names.items():
            n += len(xs)
            lo, hi = min(x[v] / x['K'] for x in xs), max(x[v] / x['K'] for x in xs)
            # levels in USD trillions: 1e-9 is USD 1,000
            ok = abs(xs[0][v] / 1e6 - ref[y][name]) < 1e-9 and \
                abs(lo - ref[y]['ratio_' + name][0]) < 1e-9 and abs(hi - ref[y]['ratio_' + name][1]) < 1e-9
            bad += not ok
            if not ok:
                print('MISMATCH', y, v, xs[0][v] / 1e6, ref[y][name])
    print(f'{n} netting problems on {sum(map(len, rows.values()))} balance sheets solved independently; '
          f'{"all agree with netting_multilateral.py" if not bad else str(bad) + " year-variants disagree"}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
