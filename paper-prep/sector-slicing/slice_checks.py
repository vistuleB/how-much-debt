"""Checks behind the household split, 2001-2025.

Standard library only. Reads the same records as
paper-prep/broad-debt/series.py (look-through, foreign security issuers as
nonbanks, securities repayable, sectors separate), the DFA (Sept 2026) and
B.101.h of the pinned March 19, 2026 Z.1. Changes no other file.
From the repository root:
    python3 -I paper-prep/sector-slicing/slice_checks.py

1. Vintage: DFA household totals (sum of the five wealth groups) against
   B.101.h of the March release, item by item.
2. Containment: the household slices must fit inside the domestic sector of the
   stored balance sheet. With c = what a sector can sell or collect and o = its
   repayable debt (the certificate's receipts and repayable amounts), the rest
   of the domestic sector keeps c_rest = c_d - sum c_i >= 0 and
   o_rest = o_d - sum o_i >= 0, and its Treasury-owed part stays >= 0.
3. Attainment: an explicit funded witness on the split. Every sellable claim
   goes to the central bank (sellers' money rises by c_i); each sector repays
   what it owes the Treasury first, then the rest, from that money only; the
   Treasury redeems. Checked after each step: no sector's money below its
   opening level, reserves non-negative, Treasury net position unchanged.
   Two Treasury menus:
     paper:      the Treasury may also sell loans it holds (the general statement of the result);
     collection: it may only collect them (the menu of the executed runs).
   Household student loans (federal) are allocated across wealth groups in
   proportion to DFA consumer credit; extremes reported for the collection
   menu.
"""
import csv, io, json, sys, zipfile, importlib.util

ZIP = 'fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip'
DFA = 'paper-prep/sector-slicing/raw/dfa.zip'
GROUPS = ['Bottom50', 'Next40', 'Next9', 'RemainingTop1', 'TopPt1']
STUDENT = 'FL313066220.Q'
M = 1e6
TOL = 1e-6  # trillions

spec = importlib.util.spec_from_file_location('series', 'paper-prep/broad-debt/series.py')
series = importlib.util.module_from_spec(spec); spec.loader.exec_module(series)


def b101h():
    z = zipfile.ZipFile(ZIP)
    r = list(csv.reader(io.StringIO(z.read('csv/b101h.csv').decode())))
    h = r[0]
    return {int(x[0]): {h[k]: float(x[k]) for k in range(1, len(h)) if x[k] not in ('', 'ND')} for x in r[1:]}


def student():
    z = zipfile.ZipFile(ZIP)
    for n in z.namelist():
        if n.endswith('.csv'):
            r = list(csv.reader(io.StringIO(z.read(n).decode('utf-8', 'replace'))))
            if r and STUDENT in r[0]:
                k = r[0].index(STUDENT)
                return {int(x[0][:4]): float(x[k]) / M for x in r[1:] if x and x[0].endswith('Q4')}
    raise KeyError(STUDENT)


def dfa():
    with zipfile.ZipFile(DFA) as z:
        r = list(csv.DictReader(io.StringIO(z.read('dfa-networth-levels-detail.csv').decode())))
    return {(x['Date'], x['Category']): {k: float(v) / M for k, v in x.items() if k not in ('Date', 'Category') and v != ''} for x in r}


SEPT = 'paper-prep/sector-slicing/raw/z1-20260911-S14_b.csv'  # Z.1 table S.14.b, September 2026
SEPT_CODES = {'FL194023005.A': 'FL194035005.A', 'FL194123005.A': 'FL194135005.A'}  # renamed loan totals


def s14b():
    r = list(csv.reader(open(SEPT))); h = r[0]
    return {int(x[0]): {h[k]: float(x[k]) for k in range(1, len(h)) if x[k] not in ('', 'ND')} for x in r[1:] if x[0][:4].isdigit()}


VINTAGE = [  # DFA column, B.101.h series (or sum)
    ('Deposits', ['FL193020005.A', 'FL193030205.A']),
    ('Money market fund shares', ['FL193034005.A']),
    ('Debt securities', ['LM194022005.A']),
    ('Loans (Assets)', ['FL194023005.A']),
    ('Loans (Liabilities)', ['FL194123005.A']),
    ('Home mortgages', ['FL153165105.A']),
    ('Consumer credit', ['FL153166000.A']),
]


def sequence(parts, tnd_inputs, rho, treasury_sells):
    """parts: name -> dict(c, o, s). Returns debt reduction and checks."""
    B, W = tnd_inputs  # bonds outstanding; T + q_G + Treasury-held claims (all)
    money = {k: 0.0 for k in parts}           # change from opening
    reserves = rho                             # after every sale to the Fed
    t_cash = W - sum(p['s'] for p in parts.values())  # T + q_G (Treasury claims held separately)
    held = {k: p['s'] for k, p in parts.items()}      # still owed to the Treasury
    repaid = 0.0
    for k, p in parts.items():
        money[k] += p['c']
    def check():
        assert min(money.values()) >= -TOL and reserves >= -TOL
    check()
    for k, p in parts.items():   # Treasury first
        a = min(p['s'], money[k]); money[k] -= a; reserves -= a; held[k] -= a; t_cash += a; repaid += a; check()
    for k, p in parts.items():   # then the central bank
        a = min(p['o'] - p['s'], money[k]); money[k] -= a; reserves -= a; repaid += a; check()
    if treasury_sells:           # Treasury sells the rest of its claims to the Fed
        t_cash += sum(held.values()); held = {k: 0.0 for k in held}
    redeemed = min(B, t_cash)
    # Treasury net position: t_cash + held - B_remaining is constant
    assert abs((t_cash - redeemed + sum(held.values()) - (B - redeemed)) - (W - B)) < TOL
    return repaid + redeemed


def main():
    H = b101h(); X = dfa(); SL = student()
    global series_out
    import subprocess
    series_out = json.loads(subprocess.check_output([sys.executable, '-I', 'paper-prep/broad-debt/series.py', '--json']))
    seen = {}
    for r in series.records():
        if r['representation'] != 'agency_lookthrough' or r['nonbank_foreign_security_issuers'] != 'nonbank' \
                or not r['securities_repayable'] or r['pooled']:
            continue
        seen.setdefault(int(r['id'][:4]), r)
    print('1. VINTAGE: DFA (Sept 2026) minus B.101.h (March 2026), USD trillions; worst year shown')
    for col, codes in VINTAGE:
        diffs = [(y, sum(X[(f'{y}:Q4', g)][col] for g in GROUPS) - sum(H[y][c] for c in codes) / M) for y in sorted(seen)]
        y, w = max(diffs, key=lambda t: abs(t[1]))
        ref = sum(H[y][c] for c in codes) / M
        print(f'   {col:28s} max |diff| {abs(w):.3f} ({y}, {100*w/ref:+.1f}% of {ref:.2f})')
    S = s14b()
    print('\n1b. SAME VINTAGE: DFA minus S14.b of the September 11, 2026 Z.1 (the DFA is built on it)')
    for col, codes in VINTAGE:
        diffs = [sum(X[(f'{y}:Q4', g)][col] for g in GROUPS) - sum(S[y][SEPT_CODES.get(c, c)] for c in codes) / M for y in sorted(seen)]
        print(f'   {col:28s} max |diff| {max(map(abs, diffs)):.4f}')
    print('   March minus September (revision), worst year:')
    for col, codes in VINTAGE:
        diffs = [(y, sum(H[y][c] for c in codes) / M - sum(S[y][SEPT_CODES.get(c, c)] for c in codes) / M) for y in sorted(seen)]
        y, w = max(diffs, key=lambda t: abs(t[1]))
        print(f'   {col:28s} {w:+.3f} ({y})')
    print('\n2-3. CONTAINMENT AND ATTAINMENT, USD trillions')
    print('year | c_rest | o_rest | s_rest | formula | paper menu | collection menu (proportional, worst) | reserve cap | repaid')
    worst = 0.0
    for y in sorted(seen):
        r = seen[y]; o = r['opening']; cert = r['certificate']
        c_d, o_d = cert['receipts']['d'] / M, cert['repayable']['d'] / M
        s_d = cert['treasury_receivables']['d'] / M
        c_r, o_r, s_r = cert['receipts']['r'] / M, cert['repayable']['r'] / M, cert['treasury_receivables']['r'] / M
        rho = cert['prepared_reserve_cap'] / M
        assert abs((o_d - c_d) - r['signed_debt_receipt_gap']['d'] / M) < 1e-5
        B = (o['bb'] + o['bf'] + o['d_b'] + o['r_b']) / M
        W = (o['t'] + o['qg'] + o['s_d'] + o['s_r'] + o['j_td'] + o['j_tr']) / M
        tnd = max(0.0, B - W)
        hh = {g: X[(f'{y}:Q4', g)] for g in GROUPS}
        cc = sum(h['Consumer credit'] for h in hh.values())
        def parts(alloc):
            p = {g: dict(c=hh[g]['Debt securities'] + hh[g]['Loans (Assets)'], o=hh[g]['Loans (Liabilities)'], s=alloc[g]) for g in GROUPS}
            p['rest'] = dict(c=c_d - sum(x['c'] for x in p.values()), o=o_d - sum(x['o'] for x in p.values()),
                             s=s_d - sum(alloc.values()))
            p['row'] = dict(c=c_r, o=o_r, s=s_r)
            return p
        prop = {g: SL[y] * hh[g]['Consumer credit'] / cc for g in GROUPS}
        P = parts(prop)
        for k in ('rest',):
            assert P[k]['c'] >= 0 and P[k]['o'] >= 0 and P[k]['s'] >= 0, (y, P[k])
        D = r['opening_debt'] / M
        formula = tnd + sum(max(0.0, x['o'] - x['c']) for x in P.values())
        paper = D - sequence(P, (B, W), rho, True)
        coll = D - sequence(P, (B, W), rho, False)
        # worst allocation for collection: all student loans on the bottom 50%
        Pw = parts({g: (SL[y] if g == 'Bottom50' else 0.0) for g in GROUPS})
        collw = D - sequence(Pw, (B, W), rho, False)
        repaid = sum(min(x['o'], x['c']) for x in P.values())
        assert abs(paper - formula) < 1e-6, (y, paper, formula)
        worst = max(worst, collw - formula)
        print(f"{y} | {P['rest']['c']:.2f} | {P['rest']['o']:.2f} | {P['rest']['s']:.2f} | {formula:.2f} | {paper:.2f} | "
              f"{coll:.2f} (+{coll-formula:.2f}), {collw:.2f} (+{collw-formula:.2f}) | {rho:.1f} | {repaid:.1f}")
    print(f'\npaper menu reaches the formula in every year; collection menu exceeds it by at most {worst:.2f}')
    print('\n4. VINTAGE-ADJUSTED: each DFA item rescaled so the five groups sum to March B.101.h')
    print('year | 5 groups, DFA as published | rescaled to March | difference')
    for y in sorted(seen):
        r = seen[y]; s_ = [x for x in series_out if x['year'] == y][0]
        def gaps(scale):
            out = []
            for g in GROUPS:
                h = X[(f'{y}:Q4', g)]
                out.append(h['Loans (Liabilities)'] * scale['Loans (Liabilities)'] - h['Debt securities'] * scale['Debt securities'] - h['Loans (Assets)'] * scale['Loans (Assets)'])
            return out
        def split(xs):
            return s_['tnd'] + sum(max(0.0, x) for x in xs) + max(0.0, s_['gap_d'] - sum(xs)) + max(0.0, s_['gap_r'])
        one = {k: 1.0 for k in ('Loans (Liabilities)', 'Debt securities', 'Loans (Assets)')}
        sc = {col: sum(H[y][c] for c in codes) / M / sum(X[(f'{y}:Q4', g)][col] for g in GROUPS) for col, codes in VINTAGE if col in one}
        a, b = split(gaps(one)), split(gaps(sc))
        print(f'{y} | {a:.2f} | {b:.2f} | {b-a:+.2f}')


if __name__ == '__main__':
    main()
