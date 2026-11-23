"""How far could netting alone reduce debt?

Reads the stored run broad-debt-model/corrected-results.json,
look-through representation, nonbank-held foreign bonds issued by nonbanks,
securities repayable, observed-US-mix completion. Stdlib only. From the
repository root:
    python3 -I paper-prep/broad-debt/netting.py

Netting cancels claims that already offset one another, and nothing else:
- within each nonbank sector, its claims on itself (loans, selected J, securities);
- between the domestic and foreign sectors, mutual claims up to the smaller side;
- against the Treasury, a sector's Treasury bonds against its federal loans and
  Treasury-held securities;
- against banks and the Fed, a sector's non-money claims on them (bank funding
  q_bh, Fed claims q_h) against their loans to it.
Deposits and currency are never netted, because that would reduce money.
Netting is treated as perfect: every eligible offset cancels in full. This is
generous to netting. Where both offsetting claims are debt (domestic-foreign,
Treasury bonds against Treasury loans) both are cancelled, so debt falls by
twice the smaller side; claims on banks and the Fed are not debt, so there
it falls by the smaller side once.
"""
import json

SRC = 'broad-debt-model/corrected-results.json'
T = 1e6


def main():
    d = json.load(open(SRC))
    print('year | debt | netting only | kernel | netting / kernel')
    for y in ('2008', '2020', '2021', '2022', '2023', '2024', '2025'):
        r = next(r for r in d['records'] if r['id'].startswith(y) and 'observed_us_mix' in r['id']
                 and r['representation'] == 'agency_lookthrough' and r['nonbank_foreign_security_issuers'] == 'nonbank'
                 and r['securities_repayable'] and not r['pooled'])
        o = r['opening']; g = lambda k: o.get(k, 0)
        cl = lambda h, s: g('l_' + h + s) + g('a_' + h + s) + g('z_' + h + s)
        intra = cl('d', 'd') + cl('r', 'r')
        cross = 2 * min(cl('d', 'r'), cl('r', 'd'))  # both offsetting claims are debt
        tres = 2 * (min(g('s_d') + g('a_td') + g('z_td'), g('d_b')) + min(g('s_r') + g('a_tr') + g('z_tr'), g('r_b')))  # bond and loan are both debt
        bank = min(cl('b', 'd'), g('d_qbh')) + min(cl('b', 'r'), g('r_qbh'))
        fed = min(cl('f', 'd'), g('d_qh')) + min(cl('f', 'r'), g('r_qh'))
        D, K = r['opening_debt'], r['kernel']
        net = D - intra - cross - tres - bank - fed
        print(f'{y} | {D/T:.2f} | {net/T:.2f} | {K/T:.2f} | {net/K:.2f}')


if __name__ == '__main__':
    main()
