"""Multilateral netting: the most debt that cancellation alone can remove.

Companion to series.py and netting.py (both unchanged). Same records: the
look-through representation, foreign security issuers as nonbanks, nonbank
securities repayable, sectors separate. Standard library only. From the
repository root:
    python3 -I paper-prep/broad-debt/netting_multilateral.py [--json | --self-test]

Netting as clearing on a network. The parties are the domestic sector d, the
rest of the world r, the Treasury t, the bank b and the central bank f. Each
eligible claim is an arc from holder to issuer. A netting cancels an amount
x_e <= c_e of each arc such that every party's claims fall by exactly as much
as its debts, so every net position (sectors, Treasury, bank and central-bank
equity) is unchanged; equivalently x is a circulation. Deposits and currency
are never cancelled, so money is unchanged. Claims a sector holds on itself
cancel in full, as in netting.py. The script finds the circulation that
removes the most debt, by cancelling negative cycles in the residual network
(debt arcs cost -1, other arcs 0), exact up to a tolerance of USD 1,000.

Pairwise netting (netting.py, series.py) is the special case of two-party
cycles, so it can only leave more debt. Any netting preserves money, net
positions and both equities, so it leaves an admissible balance sheet: it can
never leave less than the kernel.

Eligible arcs:
  A (the claims netting.py may cancel):
    debt: loans, additional loans and securities between sectors and held by
    the bank and central bank (l, a, z); Treasury-held federal loans and
    claims on sectors (s, a_t, z_t); Treasury bonds held by sectors, the bank
    and the central bank (d_b, r_b, bb, bf);
    non-debt: sectors' nondeposit claims on the bank (qbh) and on the central
    bank (qh).
  B (more generous): A plus the Treasury's account and other claims on the
    central bank (t, qg), bank reserves (r), and the non-debt part of the
    claims book (j - a - z).
  C (most generous): B plus central-bank advances to the bank (u) and vault
    cash (cb). Only money (deposits, currency), locked positions and equities
    stay fixed.

In the terms of D'Errico and Roukny (2021) this is conservative compression:
existing claims are reduced, none is created.

Checks. --self-test runs the solver on small networks with known answers.
Every run asserts, on every balance sheet, that every party's net position is
unchanged, that pairwise >= A >= B >= C, and that C >= the kernel. An
independent check with a general linear-programme solver, building the
network from this docstring's definitions without importing this file's
code, is netting_multilateral_check.py (needs numpy and scipy).
"""
import json
import sys

FILES = ['fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json',
         'broad-debt-model/corrected-results.json',
         'fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json']
T = 1e6
TOL = 1e-3
NODES = 'drtbf'
G = 'dr'


def records():
    for f in FILES:
        d = json.load(open(f))
        yield from (d['records'] if isinstance(d, dict) else d)


def arcs(o, variant):
    """Merged arcs (holder, issuer, is_debt) -> amount, without self-loops."""
    g = lambda k: o.get(k, 0)
    a = {}
    def add(h, i, debt, x):
        if h != i and x > TOL:
            a[(h, i, debt)] = a.get((h, i, debt), 0) + x
    for h in 'bfdr':
        for s in G:
            add(h, s, True, g('l_' + h + s) + g('a_' + h + s) + g('z_' + h + s))
    for s in G:
        add('t', s, True, g('s_' + s) + g('a_t' + s) + g('z_t' + s))
        add(s, 't', True, g(s + '_b'))
        add(s, 'b', False, g(s + '_qbh'))
        add(s, 'f', False, g(s + '_qh'))
    add('b', 't', True, g('bb'))
    add('f', 't', True, g('bf'))
    if variant in 'BC':
        add('t', 'f', False, g('t') + g('qg'))
        add('b', 'f', False, g('r'))
        for h in 'bfdrt':
            for s in G:
                add(h, s, False, g('j_' + h + s) - g('a_' + h + s) - g('z_' + h + s))
    if variant == 'C':
        add('f', 'b', False, g('u'))
        add('b', 'f', False, g('cb'))
    return a


def max_debt_cancelled(a):
    """Max-weight circulation by negative-cycle cancelling (Bellman-Ford)."""
    keys = list(a)
    flow = {k: 0.0 for k in keys}
    for _ in range(10000):
        # residual arcs: (u, v, cost, key, direction)
        res = []
        for k in keys:
            h, i, debt = k
            w = 1.0 if debt else 0.0
            if a[k] - flow[k] > TOL:
                res.append((h, i, -w, k, +1))
            if flow[k] > TOL:
                res.append((i, h, w, k, -1))
        dist = {n: 0.0 for n in NODES}
        pred = {n: None for n in NODES}
        last = None
        for _ in range(len(NODES)):
            last = None
            for u, v, c, k, s in res:
                if dist[u] + c < dist[v] - 1e-12:
                    dist[v] = dist[u] + c
                    pred[v] = (u, k, s)
                    last = v
        if last is None:
            break
        for _ in range(len(NODES)):
            last = pred[last][0]
        cycle, v = [], last
        while True:
            u, k, s = pred[v]
            cycle.append((k, s))
            v = u
            if v == last:
                break
        amt = min(a[k] - flow[k] if s > 0 else flow[k] for k, s in cycle)
        for k, s in cycle:
            flow[k] += s * amt
    else:
        raise RuntimeError('cycle cancelling did not converge')
    for n in NODES:  # every party's net position unchanged
        bal = sum(flow[k] for k in keys if k[0] == n) - sum(flow[k] for k in keys if k[1] == n)
        assert abs(bal) < 1e-2, (n, bal)
    return sum(flow[k] for k in keys if k[2])


def netting(o, D, variant):
    g = lambda k: o.get(k, 0)
    intra = sum(g(p + h + h) for h in G for p in ('l_', 'a_', 'z_'))
    return D - intra - max_debt_cancelled(arcs(o, variant))


def self_test():
    cases = [  # (arcs, debt that can be cancelled)
        ({('b', 'd', True): 10, ('d', 'r', True): 7, ('r', 'b', False): 4}, 8),   # a three-party loop
        ({('d', 'r', True): 3, ('r', 'd', True): 5}, 6),                          # a pair: both sides are debt
        ({('b', 'd', True): 10, ('d', 'b', False): 2, ('d', 'r', True): 7, ('r', 'b', False): 4}, 10),  # pair and loop
        ({('t', 'd', True): 5, ('d', 'b', False): 5, ('b', 't', True): 5}, 10),    # Treasury loan, bank funding, bank-held bond
        ({('d', 't', True): 100, ('d', 'b', False): 0.0, ('t', 'b', True): 0.0}, 0),  # the $100 example: no loop
    ]
    for a, want in cases:
        got = max_debt_cancelled({k: v for k, v in a.items() if v > TOL})
        assert abs(got - want) < 1e-9, (a, got, want)
    print(f'self-test: {len(cases)} networks, all correct')


def pairwise(o, D):  # as in series.py and netting.py
    g = lambda k: o.get(k, 0)
    cl = lambda h, s: g('l_' + h + s) + g('a_' + h + s) + g('z_' + h + s)
    intra = cl('d', 'd') + cl('r', 'r')
    cross = 2 * min(cl('d', 'r'), cl('r', 'd'))
    tres = 2 * (min(g('s_d') + g('a_td') + g('z_td'), g('d_b')) + min(g('s_r') + g('a_tr') + g('z_tr'), g('r_b')))
    bank = min(cl('b', 'd'), g('d_qbh')) + min(cl('b', 'r'), g('r_qbh'))
    fed = min(cl('f', 'd'), g('d_qh')) + min(cl('f', 'r'), g('r_qh'))
    return D - intra - cross - tres - bank - fed


def main():
    if '--self-test' in sys.argv:
        self_test()
        return
    rows = {}
    for r in records():
        if r['representation'] != 'agency_lookthrough' or r['nonbank_foreign_security_issuers'] != 'nonbank' \
                or not r['securities_repayable'] or r['pooled']:
            continue
        o, D, K = r['opening'], r['opening_debt'], r['kernel']
        x = dict(D=D, K=K, pair=pairwise(o, D), multi=netting(o, D, 'A'), gen=netting(o, D, 'B'), most=netting(o, D, 'C'))
        assert x['multi'] <= x['pair'] + 1 and x['gen'] <= x['multi'] + 1 and x['most'] <= x['gen'] + 1, r['id']
        assert x['most'] >= K - 1, ('netting below the kernel', r['id'], x['most'], K)
        rows.setdefault(int(r['id'][:4]), []).append(x)
    out = []
    for y in sorted(rows):
        xs = rows[y]; h = xs[0]
        rng = lambda f: (min(f(x) for x in xs), max(f(x) for x in xs))
        out.append(dict(year=y, debt=h['D'] / T, pairwise=h['pair'] / T, multilateral=h['multi'] / T,
                        generous=h['gen'] / T, most_generous=h['most'] / T, kernel=h['K'] / T,
                        ratio_pairwise=rng(lambda x: x['pair'] / x['K']),
                        ratio_multilateral=rng(lambda x: x['multi'] / x['K']),
                        ratio_generous=rng(lambda x: x['gen'] / x['K']),
                        ratio_most_generous=rng(lambda x: x['most'] / x['K']), n_sheets=len(xs)))
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
        return
    print('USD trillions; ratios are netting / kernel, range across the year\'s completed balance sheets')
    print('year | debt | pairwise | multilateral A | B | C | kernel | pairwise/K | A/K | B/K | C/K | sheets')
    f = lambda p: f'{p[0]:.2f}-{p[1]:.2f}'
    for x in out:
        print(f"{x['year']} | {x['debt']:.2f} | {x['pairwise']:.2f} | {x['multilateral']:.2f} | {x['generous']:.2f} | "
              f"{x['most_generous']:.2f} | {x['kernel']:.2f} | {f(x['ratio_pairwise'])} | {f(x['ratio_multilateral'])} | "
              f"{f(x['ratio_generous'])} | {f(x['ratio_most_generous'])} | {x['n_sheets']}")


if __name__ == '__main__':
    main()
