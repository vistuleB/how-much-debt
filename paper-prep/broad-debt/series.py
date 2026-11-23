"""US broad-debt series 2001–2025 for the paper's Table 2. Standard library only.

Reads the three stored result files of executed runs:
  fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json  (2001–2007)
  broad-debt-model/corrected-results.json                                              (2008, 2020–2025)
  fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json  (2009–2019)
Look-through representation; nonbank-held foreign bonds issued by nonbanks. For
each year it reports:
- debt;
- netting only (as in netting.py);
- the transaction-based debt kernel, sectors separate, securities repayable;
- the Treasury's net debt, and the domestic and foreign gaps;
- the pooled kernel;
- the kernel with securities not repayable;
- the spread of each of these across the year's completed balance sheets.
From the repository root:  python3 -I paper-prep/broad-debt/series.py [--json]
"""
import json
import sys

FILES = ['fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json',
         'broad-debt-model/corrected-results.json',
         'fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json']
T = 1e6


def records():
    for f in FILES:
        d = json.load(open(f))
        yield from (d['records'] if isinstance(d, dict) else d)


def netting_only(o, D):
    g = lambda k: o.get(k, 0)
    cl = lambda h, s: g('l_' + h + s) + g('a_' + h + s) + g('z_' + h + s)
    intra = cl('d', 'd') + cl('r', 'r')
    cross = 2 * min(cl('d', 'r'), cl('r', 'd'))  # both offsetting claims are debt
    tres = 2 * (min(g('s_d') + g('a_td') + g('z_td'), g('d_b')) + min(g('s_r') + g('a_tr') + g('z_tr'), g('r_b')))  # bond and loan are both debt
    bank = min(cl('b', 'd'), g('d_qbh')) + min(cl('b', 'r'), g('r_qbh'))
    fed = min(cl('f', 'd'), g('d_qh')) + min(cl('f', 'r'), g('r_qh'))
    return D - intra - cross - tres - bank - fed


def main():
    rows = {}
    for r in records():
        if r['representation'] != 'agency_lookthrough' or r['nonbank_foreign_security_issuers'] != 'nonbank':
            continue
        y = int(r['id'][:4]); o = r['opening']
        key = (r['securities_repayable'], r['pooled'])
        B = o['bb'] + o['bf'] + o['d_b'] + o['r_b']
        W = o['t'] + o['qg'] + o['s_d'] + o['s_r'] + o['j_td'] + o['j_tr']
        e = rows.setdefault(y, {})
        e.setdefault(key, []).append(dict(D=r['opening_debt'], K=r['kernel'], tnd=max(0, B - W),
                                          gd=r['signed_debt_receipt_gap']['d'], gr=r['signed_debt_receipt_gap']['r'],
                                          net=netting_only(o, r['opening_debt']), id=r['id']))
    out = []
    for y in sorted(rows):
        sep = rows[y][(True, False)]; pool = rows[y][(True, True)]; frz = rows[y][(False, False)]
        spread = lambda xs, k: (max(x[k] for x in xs) - min(x[k] for x in xs)) / T
        h = sep[0]
        out.append(dict(year=y, debt=h['D'] / T, netting=h['net'] / T, least=h['K'] / T, tnd=h['tnd'] / T,
                        dom=max(0, h['gd']) / T, gap_d=h['gd'] / T, gap_r=h['gr'] / T, pooled=pool[0]['K'] / T,
                        frozen=frz[0]['K'] / T, n_sheets=len(sep),
                        spread_least=spread(sep, 'K'), spread_debt=spread(sep, 'D'), spread_net=spread(sep, 'net')))
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1)); return
    print('year | debt | netting only | kernel | Treasury net debt | domestic term | gap_r | pooled | frozen | D/kernel | net/kernel | sheets | spreads (kernel, debt, netting)')
    for x in out:
        print(f"{x['year']} | {x['debt']:.2f} | {x['netting']:.2f} | {x['least']:.2f} | {x['tnd']:.2f} | {x['dom']:.2f} | {x['gap_r']:+.2f} | "
              f"{x['pooled']:.2f} | {x['frozen']:.2f} | {x['debt']/x['least']:.2f} | {x['netting']/x['least']:.2f} | {x['n_sheets']} | "
              f"{x['spread_least']:.3f}, {x['spread_debt']:.3f}, {x['spread_net']:.3f}")


if __name__ == '__main__':
    main()
