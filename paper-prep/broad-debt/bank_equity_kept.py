"""The transaction-based debt kernel with bank equity kept, 2001-2025. Standard library only.

In Table 2 banks may pay out their equity to the domestic sector. Netting
cannot do that (bank equity is not a debt), so the like-for-like comparison
with netting is the kernel with bank equity kept. This script computes it
on every stored completed balance sheet (look-through representation, nonbank
issuers of nonbank-held foreign bonds), for both protections (sectors separate
and pooled) and both repayment profiles, from the certificate of
broad-debt-model/CORRECTED.md with the payout left out of the domestic
sector's receipts.

Check: with the payout included, the same formula must reproduce every stored
executed kernel; the script exits with status 1 if it does
not, or if the values differ between the completed balance sheets of a year.

From the repository root:  python3 -I paper-prep/broad-debt/bank_equity_kept.py [--json]
"""
import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location('series', 'paper-prep/broad-debt/series.py')
series = importlib.util.module_from_spec(spec); spec.loader.exec_module(series)
G = ('d', 'r'); H = ('b', 'f', 'd', 'r', 't')
T = 1e6
TOL = 1.0  # USD millions


def certificate(v, pooled, repayable, payout):
    owned = lambda h: sum(v['j_' + h + g] for g in G)
    loans = lambda g: sum(v['l_' + h + g] for h in 'bfdr')
    issued = lambda g: sum(v['a_' + h + g] + v['z_' + h + g] for h in H)
    bonds = v['bb'] + v['bf'] + v['d_b'] + v['r_b']
    debt = bonds + sum(loans(g) + v['s_' + g] + issued(g) for g in G)
    receipts = {g: v[g + '_b'] + v[g + '_qh'] + v[g + '_qbh'] + owned(g) + sum(v['l_' + g + b] for b in G)
                + (v['eb'] if g == 'd' and payout else 0) for g in G}
    due = {g: loans(g) + v['s_' + g] + sum(v['a_' + h + g] + (v['z_' + h + g] if repayable else 0) for h in H) for g in G}
    to_treasury = {g: v['s_' + g] + v['a_t' + g] + (v['z_t' + g] if repayable else 0) for g in G}
    if pooled:
        q = min(sum(receipts.values()), sum(due.values())); collect = min(sum(to_treasury.values()), q)
    else:
        quota = {g: min(receipts[g], due[g]) for g in G}
        q = sum(quota.values()); collect = sum(min(quota[g], to_treasury[g]) for g in G)
    reserve_cap = (v['r'] + v['nb'] + v['bb'] + sum(v[g + '_b'] + v[g + '_qh'] for g in G)
                   + sum(v['l_' + h + g] for h in 'bdr' for g in G) + sum(owned(h) for h in 'bdr'))
    q = min(q, reserve_cap); collect = min(collect, q)
    redeemed = min(bonds, v['t'] + v['qg'] + collect)
    return debt - q - redeemed


def netting_not_repayable(o, D):
    g = lambda k: o.get(k, 0)
    cl = lambda h, s: g('l_' + h + s) + g('a_' + h + s)
    intra = cl('d', 'd') + cl('r', 'r')
    cross = 2 * min(cl('d', 'r'), cl('r', 'd'))
    tres = 2 * (min(g('s_d') + g('a_td'), g('d_b')) + min(g('s_r') + g('a_tr'), g('r_b')))
    bank = min(cl('b', 'd'), g('d_qbh')) + min(cl('b', 'r'), g('r_qbh'))
    fed = min(cl('f', 'd'), g('d_qh')) + min(cl('f', 'r'), g('r_qh'))
    return D - intra - cross - tres - bank - fed


def main():
    bad = []
    per_year = {}
    for r in series.records():
        if r['representation'] != 'agency_lookthrough' or r['nonbank_foreign_security_issuers'] != 'nonbank':
            continue
        o = r['opening']; y = int(r['id'][:4])
        pooled, repayable = r['pooled'], r['securities_repayable']
        if abs(certificate(o, pooled, repayable, True) - r['kernel']) > TOL:
            bad.append(r['id'])
        key = ('pooled' if pooled else 'separate') + ('' if repayable else '_not_repayable')
        e = per_year.setdefault(y, {})
        e.setdefault(key, set()).add(round(certificate(o, pooled, repayable, False), 0))
        e.setdefault('payout', set()).add(round(o['eb'], 0))
        if not pooled and repayable:
            e.setdefault('netting', set()).add(round(series.netting_only(o, r['opening_debt']), 0))
            e.setdefault('debt', set()).add(round(r['opening_debt'], 0))
            e.setdefault('least_with_payout', set()).add(round(r['kernel'], 0))
        if not pooled and not repayable:
            e.setdefault('netting_not_repayable', set()).add(round(netting_not_repayable(o, r['opening_debt']), 0))
            e.setdefault('least_not_repayable_with_payout', set()).add(round(r['kernel'], 0))
    out = []
    for y in sorted(per_year):
        e = per_year[y]
        for k, vals in e.items():
            if k not in ('payout', 'netting', 'netting_not_repayable', 'debt') and max(vals) - min(vals) > TOL:
                bad.append(f'{y} {k} differs across completed balance sheets')
        row = dict(year=y, **{k: max(v) / T for k, v in e.items()})
        row['netting_ratio'] = row['netting'] / row['separate']
        row['netting_ratio_with_payout'] = row['netting'] / row['least_with_payout']
        row['netting_ratio_not_repayable'] = row['netting_not_repayable'] / row['separate_not_repayable']
        out.append(row)
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1))
    else:
        print('year | debt | netting | kernel: with payout, bank equity kept | pooled, kept | '
              'not repayable: with payout, kept | payout | netting / kernel kept | netting not repayable / kernel kept')
        for x in out:
            print(f"{x['year']} | {x['debt']:.2f} | {x['netting']:.2f} | {x['least_with_payout']:.2f}, {x['separate']:.2f} | "
                  f"{x['pooled']:.2f} | {x['least_not_repayable_with_payout']:.2f}, {x['separate_not_repayable']:.2f} | "
                  f"{x['payout']:.2f} | {x['netting_ratio']:.3f} | {x['netting_ratio_not_repayable']:.3f}")
        for k in ('netting_ratio', 'netting_ratio_with_payout', 'netting_ratio_not_repayable'):
            vals = [x[k] for x in out]
            print(f'{k}: {min(vals):.3f}-{max(vals):.3f}')
        print('check: the formula with the payout reproduces every stored executed kernel:',
              'yes' if not bad else 'NO')
    if bad:
        print('FAILED:', bad[:10], file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
