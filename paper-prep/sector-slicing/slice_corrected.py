"""Household slicing on the corrected broad debt, 2001-2025.

The Treasury's net debt and the domestic and foreign gaps come from the
broad-debt series (paper-prep/broad-debt/series.py: look-through
representation, foreign security issuers as nonbanks).
From the repository root:
    python3 -I paper-prep/sector-slicing/slice_corrected.py [--json]

A slice's term is [o - h]+ : debt owed minus debt claims it can sell
(narrow bracket: debt securities and loans held; pensions, insurance, fund
shares, equities and private business locked). Gaps add before [ ]+, so the
rest of the domestic sector has gap_d - sum of household gaps.

    D_min(split) = TND + sum_i [x_i]+ + [gap_d - sum_i x_i]+ + [gap_r]+

DFA: September 2026 release (Z.1 of 11 Sept 2026); the series uses the March
19, 2026 Z.1. Vintages differ: provisional.
"""
import csv, io, json, subprocess, sys, zipfile

DFA = 'paper-prep/sector-slicing/raw/dfa.zip'
GROUPS = ['Bottom50', 'Next40', 'Next9', 'RemainingTop1', 'TopPt1']
pos = lambda a: max(0.0, a)


def dfa_rows():
    with zipfile.ZipFile(DFA) as z:
        r = list(csv.DictReader(io.StringIO(z.read('dfa-networth-levels-detail.csv').decode('utf-8'))))
    return {(x['Date'], x['Category']): {k: float(v) for k, v in x.items() if k not in ('Date', 'Category') and v != ''} for x in r}


def gap(x):  # USD trillions
    return (x['Loans (Liabilities)'] - x['Debt securities'] - x['Loans (Assets)']) / 1e6


def main():
    rows = dfa_rows()
    ser = json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/broad-debt/series.py', '--json']))
    out = []
    for s in ser:
        y = s['year']; xs = {g: gap(rows[(f'{y}:Q4', g)]) for g in GROUPS}
        assert abs(s['gap_d'] - s['dom']) < 1e-9 and s['gap_d'] > 0
        def split(parts):
            return s['tnd'] + sum(pos(p) for p in parts) + pos(s['gap_d'] - sum(parts)) + pos(s['gap_r'])
        two_s = split([])  # households not separated: must equal the series' kernel
        assert abs(two_s - s['least']) < 1e-6, (y, two_s, s['least'])
        one = split([sum(xs.values())]); five = split(list(xs.values()))
        out.append(dict(year=y, debt=s['debt'], netting=s['netting'], least=s['least'], hh_one=one, hh_five=five,
                        hh_gaps=xs, rest=s['gap_d'] - sum(xs.values()),
                        hh_deposits=sum(rows[(f'{y}:Q4', g)]['Deposits'] for g in GROUPS) / 1e6))
    if '--json' in sys.argv:
        print(json.dumps(out, indent=1)); return
    print('year | debt | kernel (2 sectors) | +households | +5 wealth groups | ratio debt/5grp | gaps B50 N40 N9 RT1 T.1 | rest of domestic')
    for o in out:
        g = o['hh_gaps']
        print(f"{o['year']} | {o['debt']:.2f} | {o['least']:.2f} | {o['hh_one']:.2f} | {o['hh_five']:.2f} | {o['debt']/o['hh_five']:.2f} | "
              + ' '.join(f'{g[k]:+.2f}' for k in GROUPS) + f" | {o['rest']:+.2f}")


if __name__ == '__main__':
    main()
