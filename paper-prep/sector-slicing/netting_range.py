"""Netting under the household split: a source-constrained range, 2001-2025.

Standard library only. Changes no other file. From the repository root:
    python3 -I paper-prep/sector-slicing/netting_range.py [--json]

Question. With households taken out of the domestic sector (five DFA wealth
groups, as in slice_corrected.py), how much debt does netting alone leave?
Netting is defined exactly as in paper-prep/broad-debt/netting.py (every
eligible offset cancels in full; deposits and currency never netted), applied
to the finer partition: offsets cancel within a slice, between two slices,
between a slice and the rest of the world, the Treasury, the banks or the Fed.

Conditions. Same debt perimeter and same permitted cancellations as the
two-sector figure; only the partition changes. Splitting can only remove
cancellations (a sum of minima is at most the minimum of sums, and claims
between slices cancel only bilaterally), so the two-sector figure N2 is a
lower bound on what netting leaves. The question is how much higher.

Margins used jointly (USD, March 19, 2026 Z.1 unless noted):
- household loans owed, HL (B.101.h line 21), and household debt securities
  and loans held (lines 9, 12);
- federal student loans (L.222), held by the Treasury (in s_d, not in any
  nonbank's claims);
- bank holdings that can only be household debt: consumer credit of U.S.
  depositories and credit unions (L.222), households' depository loans n.e.c.
  (B.101.h line 24);
- bank direct one-to-four-family mortgages (L.218) and the stored
  capacity intervals for the one-to-four-family part of bank- and Fed-held
  agency MBS principal (household-holder-bridge/evidence.json, same
  completion); one-to-four-family mortgages of noncorporate business (L.218)
  are assigned to those holders first when bounding household holdings from
  below, so no household share is assumed;
- the stored balance sheet's own cells: claims of domestic nonbanks on
  domestic nonbanks (cl_dd), on and from the rest of the world, Treasury-held
  claims, bank and Fed holdings, sectors' nondeposit claims on banks and Fed.

Let Y be household debt held by domestic nonbanks (households included) and X
the claims households hold on domestic nonbanks (households included). Split
netting loses the household part of the intra-domestic cancellation except
what cancels inside one slice or bilaterally, so the intra-domestic loss lies
between max(0, Y_min - X_max) and min(cl_dd, X_max + Y_max). Losses on the
foreign, Treasury, bank and Fed offsets lie between 0 and the bounds below,
each taken at the same extreme allocation as Y_max (no household debt held by
the rest of the world; households owe all domestic federal loans; banks and
the Fed hold as much household debt as their margins allow).
No allocation is chosen: both ends are bounds, not estimates.
"""
import csv, io, json, sys, zipfile, subprocess

ZIP = 'fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip'
EV = 'fed-balance-sheet-audit/household-holder-bridge/evidence.json'
M = 1e6
Q = {'SL': 'FL313066220.Q', 'CC_US': 'FL763066005.Q', 'CC_CU': 'FL473066000.Q'}
A = {'HL': 'FL194123005.A', 'DEPNEC': 'FL193168005.A', 'HSEC': 'LM194022005.A', 'HLA': 'FL194023005.A',
     'HCORP': 'LM193063005.A', 'HGOV': 'LM193061005.A'}
pos = lambda x: max(0.0, x)


def quarterly(codes):
    out = {}
    z = zipfile.ZipFile(ZIP)
    for n in z.namelist():
        if not n.endswith('.csv'):
            continue
        r = list(csv.reader(io.StringIO(z.read(n).decode('utf-8', 'replace'))))
        if not r:
            continue
        for k, c in codes.items():
            if k not in out and c in r[0]:
                i = r[0].index(c)
                out[k] = {int(x[0][:4]): float(x[i]) / M for x in r[1:] if x and x[0].endswith('Q4')}
    assert set(out) == set(codes), set(codes) - set(out)
    return out


def annual():
    z = zipfile.ZipFile(ZIP)
    r = list(csv.reader(io.StringIO(z.read('csv/b101h.csv').decode())))
    h = r[0]
    rows = {int(x[0]): dict(zip(h, x)) for x in r[1:]}
    return {k: {y: float(rows[y][c]) / M for y in rows if rows[y][c] not in ('', 'ND')} for k, c in A.items()}


def main():
    import importlib.util
    sp = importlib.util.spec_from_file_location('series', 'paper-prep/broad-debt/series.py')
    series = importlib.util.module_from_spec(sp); sp.loader.exec_module(series)
    ser = {x['year']: x for x in json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/broad-debt/series.py', '--json']))}
    split = {x['year']: x for x in json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/sector-slicing/slice_corrected.py', '--json']))}
    ev = {y['year']: y for y in json.load(open(EV))['years']}
    q = quarterly(Q); a = annual()
    rec = {}
    for r in series.records():
        if r['representation'] == 'agency_lookthrough' and r['nonbank_foreign_security_issuers'] == 'nonbank' \
                and r['securities_repayable'] and not r['pooled']:
            rec.setdefault(int(r['id'][:4]), r)
    out = []
    for y in sorted(rec):
        r = rec[y]; o = r['opening']; g = lambda k: o.get(k, 0) / M
        cl = lambda h, t: g('l_' + h + t) + g('a_' + h + t) + g('z_' + h + t)
        e = ev[y]; sv = {k: v / M for k, v in e['source_values'].items()}
        pr = next(p for p in e['projections'] if p['id'] == r['id'])
        bank_lo, bank_hi = (v / M for v in pr['bank_one_to_four_capacity_bound'])
        fed_lo, fed_hi = (v / M for v in pr['fed_one_to_four_capacity_bound'])
        home_direct = sum(sv[k] for k in ('US_banks_direct_home_mortgages', 'affiliated_area_banks_direct_home_mortgages',
                                          'credit_unions_direct_home_mortgages', 'foreign_bank_offices_direct_home_mortgages'))
        noncorp = sv['noncorporate_business_home_mortgages']
        cc_bank = q['CC_US'][y] + q['CC_CU'][y]
        HL, SL, DEP = a['HL'][y], q['SL'][y], a['DEPNEC'][y]
        X_max = a['HSEC'][y] + a['HLA'][y]
        # household debt held by banks and the Fed: bounds
        bf_min = cc_bank + DEP + pos(home_direct + bank_lo + fed_lo - noncorp)
        bf_max = min(cc_bank + DEP + home_direct + bank_hi, cl('b', 'd')) + min(fed_hi, cl('f', 'd'))
        s_d = g('s_d')
        Y_max = min(cl('d', 'd'), pos(HL - SL - bf_min))
        Y_min = pos(HL - s_d - bf_max - g('l_rd'))
        intra_lo = pos(Y_min - X_max)
        intra_hi = min(cl('d', 'd'), X_max + Y_max)
        # other offsets, worst case
        a_, b_ = cl('d', 'r'), cl('r', 'd')
        row_hi = 2 * min(a_, b_) - 2 * min(pos(a_ - a['HCORP'][y] - a['HLA'][y]), b_)
        td = g('s_d') + g('a_td') + g('z_td')
        tres_hi = 2 * min(td, g('d_b')) - 2 * min(g('a_td') + g('z_td'), pos(g('d_b') - a['HGOV'][y]))
        bank_hi_loss = min(cl('b', 'd'), g('d_qbh')) - min(pos(cl('b', 'd') - (cc_bank + DEP + home_direct + bank_hi)), pos(g('d_qbh') - a['HCORP'][y]))
        fed_hi_loss = min(cl('f', 'd'), g('d_qh')) - min(pos(cl('f', 'd') - fed_hi), g('d_qh'))
        N2 = ser[y]['netting']; D = ser[y]['debt']
        lo = N2 + intra_lo
        hi = N2 + intra_hi + row_hi + tres_hi + bank_hi_loss + fed_hi_loss
        m5 = split[y]['hh_five']
        out.append(dict(year=y, debt=D, netting_2=N2, netting_split_lo=lo, netting_split_hi=hi, split_min=m5,
                        Y=(Y_min, Y_max), X_max=X_max, parts=dict(intra=(intra_lo, intra_hi), row=row_hi, treasury=tres_hi,
                                                                    bank=bank_hi_loss, fed=fed_hi_loss)))
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1)); return
    print('USD trillions. Netting leaves, households split into five groups (range) vs two sectors; split minimum (unrescaled)')
    print('year | debt | netting 2 sectors | netting split: low - high | split minimum | ratio low - high | Y min-max | X max | loss parts hi (intra, row, tres, bank, fed)')
    for x in out:
        p = x['parts']
        print(f"{x['year']} | {x['debt']:.2f} | {x['netting_2']:.2f} | {x['netting_split_lo']:.2f} - {x['netting_split_hi']:.2f} | {x['split_min']:.2f} | "
              f"{x['netting_split_lo']/x['split_min']:.2f} - {x['netting_split_hi']/x['split_min']:.2f} | {x['Y'][0]:.2f}-{x['Y'][1]:.2f} | {x['X_max']:.2f} | "
              f"{p['intra'][1]:.2f}, {p['row']:.2f}, {p['treasury']:.2f}, {p['bank']:.2f}, {p['fed']:.2f}")


if __name__ == '__main__':
    main()
