"""Netting when securities cannot be retired early, against the matching kernel.

Companion to netting.py. Same records and
netting rules, except that debt securities (z) cannot be cancelled: cancelling
a security before maturity is early retirement, which the frozen profile
forbids. Compared with the kernel when securities may be sold but not
repaid (the paper's Table 2, column 8). From the repository root:
    python3 -I paper-prep/broad-debt/netting_frozen.py
"""
import importlib.util

spec = importlib.util.spec_from_file_location('series', 'paper-prep/broad-debt/series.py')
series = importlib.util.module_from_spec(spec); spec.loader.exec_module(series)
T = 1e6


def main():
    seen = {}
    for r in series.records():
        if r['representation'] == 'agency_lookthrough' and r['nonbank_foreign_security_issuers'] == 'nonbank' \
                and not r['securities_repayable'] and not r['pooled']:
            seen.setdefault(int(r['id'][:4]), r)
    print('year | debt | netting, securities not cancellable | kernel, securities not repayable | ratio')
    for y in sorted(seen):
        r = seen[y]; o = r['opening']; g = lambda k: o.get(k, 0)
        cl = lambda h, s: g('l_' + h + s) + g('a_' + h + s)
        intra = cl('d', 'd') + cl('r', 'r')
        cross = 2 * min(cl('d', 'r'), cl('r', 'd'))
        tres = 2 * (min(g('s_d') + g('a_td'), g('d_b')) + min(g('s_r') + g('a_tr'), g('r_b')))
        bank = min(cl('b', 'd'), g('d_qbh')) + min(cl('b', 'r'), g('r_qbh'))
        fed = min(cl('f', 'd'), g('d_qh')) + min(cl('f', 'r'), g('r_qh'))
        D, K = r['opening_debt'], r['kernel']
        net = D - intra - cross - tres - bank - fed
        print(f'{y} | {D/T:.2f} | {net/T:.2f} | {K/T:.2f} | {net/K:.2f}')


if __name__ == '__main__':
    main()
