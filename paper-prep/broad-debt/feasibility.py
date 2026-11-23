"""Feasibility check: debt securities and federal-government loans inside D.

Reads the stored completed balance sheets and the
executed minima in fed-balance-sheet-audit/z1-bank-positions/row-split/check.json
and two federal-loan series from the pinned Z.1 archive. Changes no project code.
Standard library only. From the repository root:
    python3 -I paper-prep/broad-debt/feasibility.py

Broad debt D' = Treasury bonds + selected loans (as now)
              + debt securities issued by the two nonbank sectors ("J", now held fixed)
              + loans held by the federal government (now outside the model).

For each stored balance sheet (Treasury may redeem from its account, advances
fixed, bank payouts to the domestic sector, i.e. key E3/fixed/R4) it

  0. validates the engine: with J frozen and no federal loans, the funded
     sequence below reproduces the stored executed minima at X1 (sectors
     separate) and X4 (sectors pooled);
  1. computes the broad lower bound
        [B - W - S]+ + sum_g [gap'_g]+        (separate)
        [B - W - S]+ + [sum_g gap'_g]+        (pooled)
     where W = Treasury account + other Treasury claims on the Fed, S = federal
     loans held, gap'_g = debt owed by g in D' minus what g can sell or collect;
  2. runs an explicit funded sequence in the stored state vector (existing
     moves plus two new ones: an issuer repays a Fed-held security; a borrower
     repays a federal loan to the Treasury), checking after every move the
     bank and Fed balance-sheet identities, non-negativity, the Treasury's net
     position and every money floor;
  3. reports whether the sequence reaches the bound.
"""
import json
import zipfile
import csv
import io

CHECK = 'fed-balance-sheet-audit/z1-bank-positions/row-split/check.json'
ZIP = 'fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip'
FED_LOANS = 'FL314023005.Q'      # Federal government; loans; asset (L.106)
ROW_FED_LOANS = 'FL263169203.Q'  # Rest of world; loans from US federal government; liability
STUDENT = 'FL313066220.Q'        # Federal government; consumer credit, student loans; asset
TOL = 1e-3                       # millions of dollars
T = 1e6


def read_series(codes, years):
    out = {}
    with zipfile.ZipFile(ZIP) as z:
        for n in z.namelist():
            if not n.endswith('.csv'):
                continue
            rows = list(csv.reader(io.StringIO(z.read(n).decode('utf-8', 'replace'))))
            if not rows:
                continue
            hdr = rows[0]
            for c in codes:
                if c in hdr and c not in out:
                    k = hdr.index(c)
                    vals = {r[0]: r[k] for r in rows[1:] if r}
                    out[c] = {y: float(vals[f'{y}:Q4']) for y in years}
    missing = set(codes) - set(out)
    assert not missing, missing
    return out


owned = lambda v, h: sum(v['j_' + h + i] for i in 'drt')
issued = lambda v, i: sum(v['j_' + h + i] for h in 'bfdr')
loans = lambda v, g: sum(v['l_' + h + g] for h in 'bfdr')
loan_assets = lambda v, g: sum(v['l_' + g + b] for b in 'dr')
money = lambda v, g: v[g + '_m'] + v[g + '_ch']
bonds = lambda v: v['bb'] + v['bf'] + v['d_b'] + v['r_b']


def debt(v, broad):
    d = bonds(v) + loans(v, 'd') + loans(v, 'r')
    if broad:
        d += sum(issued(v, i) for i in 'drt') + v['s_d'] + v['s_r']
    return d


def treasury_net(v):
    return v['t'] + v['qg'] + v['s_d'] + v['s_r'] - bonds(v)


def structural(v):
    assert all(x >= -TOL for k, x in v.items() if k != 'ef'), [k for k, x in v.items() if k != 'ef' and x < -TOL]
    bank = (v['d_m'] + v['r_m'] + v['u'] + v['eb'] + v['d_qbh'] + v['r_qbh'] + v['qbr']) - (
        v['bb'] + v['l_bd'] + v['l_br'] + v['r'] + v['cb'] + v['nb'] + v['xbr'] + owned(v, 'b'))
    fed = (v['bf'] + v['l_fd'] + v['l_fr'] + v['u'] + v['xf']) - sum(
        v[k] for k in ['r', 't', 'cb', 'd_ch', 'r_ch', 'd_qh', 'r_qh', 'qg', 'ql', 'ef'])
    assert abs(bank) < TOL and abs(fed) < TOL, ('sheet', bank, fed)
    assert v['xf'] >= v['nf'] + owned(v, 'f') - TOL, 'Fed inventory'


MOVES = {
    'BondToBank': lambda g: {g + '_b': -1, 'bb': 1, g + '_m': 1},
    'BankBondToFed': lambda: {'bb': -1, 'bf': 1, 'r': 1},
    'LoanToBank': lambda h, b: {'l_' + h + b: -1, 'l_b' + b: 1, h + '_m': 1},
    'BankLoanToFed': lambda g: {'l_b' + g: -1, 'l_f' + g: 1, 'r': 1},
    'PublicJToFed': lambda g, i: {'j_' + g + i: -1, 'j_f' + i: 1, 'xf': 1, 'r': 1, g + '_m': 1},
    'BankJToFed': lambda i: {'j_b' + i: -1, 'j_f' + i: 1, 'xf': 1, 'r': 1},
    'FundingRepaid': lambda g: {g + '_qbh': -1, g + '_m': 1},
    'FedClaimSettled': lambda g: {g + '_qh': -1, 'r': 1, g + '_m': 1},
    'Payout': lambda: {'eb': -1, 'd_m': 1},
    'TreasuryClaimSettled': lambda: {'qg': -1, 't': 1},
    'RedeemFed': lambda: {'bf': -1, 't': -1},
    'RepayFed': lambda g: {'l_f' + g: -1, g + '_m': -1, 'r': -1},
    'Transfer': lambda g, o: {g + '_m': -1, o + '_m': 1},
    # new
    'RepayJ': lambda i: {'j_f' + i: -1, 'xf': -1, i + '_m': -1, 'r': -1},
    'RepayTreasury': lambda g: {'s_' + g: -1, g + '_m': -1, 'r': -1, 't': 1},
}


class Run:
    def __init__(self, v, broad, pooled):
        self.v = dict(v); self.broad = broad; self.pooled = pooled
        self.floor = {g: money(v, g) for g in 'dr'}
        self.w0 = treasury_net(v); self.steps = 0
        structural(self.v)

    def move(self, name, a, *args):
        if a <= 0:
            return
        for k, x in MOVES[name](*args).items():
            self.v[k] += x * a
        self.steps += 1
        structural(self.v)
        assert abs(treasury_net(self.v) - self.w0) < TOL, 'Treasury net position'
        if self.pooled:
            assert sum(money(self.v, g) for g in 'dr') >= sum(self.floor.values()) - TOL, 'pooled floor'
        else:
            for g in 'dr':
                assert money(self.v, g) >= self.floor[g] - TOL, ('floor', g)

    def spare(self, g):
        return self.v[g + '_m'] + self.v[g + '_ch'] - self.floor[g]


def sequence(v0, broad, pooled):
    R = Run(v0, broad, pooled); v = R.v
    # (i) everything saleable ends at the central bank; sellers' money only rises
    for g in 'dr':
        R.move('BondToBank', v[g + '_b'], g)
        R.move('FundingRepaid', v[g + '_qbh'], g)
        R.move('FedClaimSettled', v[g + '_qh'], g)
        for b in 'dr':
            R.move('LoanToBank', v['l_' + g + b], g, b)
        if broad:
            for i in 'dr':
                R.move('PublicJToFed', v['j_' + g + i], g, i)
    R.move('Payout', v['eb'])
    R.move('BankBondToFed', v['bb'])
    for g in 'dr':
        R.move('BankLoanToFed', v['l_b' + g], g)
        if broad:
            R.move('BankJToFed', v['j_b' + g], g)
    R.move('TreasuryClaimSettled', v['qg'])
    # (ii) each sector repays from its receipts: federal loans first, then the rest
    def repay(g):
        if broad:
            R.move('RepayTreasury', min(v['s_' + g], R.spare(g)), g)
        R.move('RepayFed', min(v['l_f' + g], R.spare(g)), g)
        if broad:
            R.move('RepayJ', min(v['j_f' + g], R.spare(g)), g)
    for g in 'rd':
        repay(g)
    if pooled:   # one sector's surplus covers the other's remaining debt
        owing = lambda o: v['l_f' + o] + ((v['s_' + o] + v['j_f' + o]) if broad else 0.0)
        for g, o in ('rd', 'dr'):
            R.move('Transfer', min(max(0.0, R.spare(g)), owing(o)), g, o)
            repay(o)
    # (iii) Treasury redeems from its account
    R.move('RedeemFed', min(v['t'], v['bf']))
    return debt(v, broad), R


def bound(v, broad, pooled):
    w = v['t'] + v['qg']; S = v['s_d'] + v['s_r'] if broad else 0.0
    def gap(g):
        owe = loans(v, g) + ((issued(v, g) + v['s_' + g]) if broad else 0.0)
        can = v[g + '_b'] + v[g + '_qbh'] + loan_assets(v, g) + v[g + '_qh'] + v[g + '_n'] \
            + (v['eb'] if g == 'd' else 0.0) + (owned(v, g) if broad else 0.0)
        return owe - can
    t = max(0.0, bonds(v) - w - S)
    return t + (max(0.0, gap('d') + gap('r')) if pooled else max(0.0, gap('d')) + max(0.0, gap('r'))), gap


def main():
    RS = json.load(open(CHECK))
    BO = RS['border_order']; X1, X4 = BO.index('X1'), BO.index('X4')
    years = sorted({s['year'] for s in RS['scenarios']})
    fs = read_series([FED_LOANS, ROW_FED_LOANS, STUDENT], years)
    n = ok_engine = ok_bound = 0; rows = {}
    for s in RS['scenarios']:
        v = {x['name']: x['value'] for g in ('balances', 'holdings', 'positions') for x in s['state'][g]}
        y = s['year']
        v['s_r'] = fs[ROW_FED_LOANS][y]; v['s_d'] = fs[FED_LOANS][y] - v['s_r']
        R = {r['key']: r for r in s['results']}['E3/fixed/R4']['kernels']
        n += 1
        # 0. engine reproduces stored executed minima (narrow D)
        e1, _ = sequence(v, False, False); e4, _ = sequence(v, False, True)
        ok_engine += abs(e1 - R[X1]) < 1 and abs(e4 - R[X4]) < 1
        # 1-3. broad
        b1, gap = bound(v, True, False); b4, _ = bound(v, True, True)
        r1, run1 = sequence(v, True, False); r4, run4 = sequence(v, True, True)
        hit = abs(r1 - b1) < 1 and abs(r4 - b4) < 1
        ok_bound += hit
        if not hit:
            print('MISS', s['id'], r1 / T, b1 / T, r4 / T, b4 / T)
        rows.setdefault(y, []).append(dict(id=s['id'], rep=s['representation'], D=debt(v, False), Db=debt(v, True),
            n1=R[X1], n4=R[X4], b1=b1, b4=b4, gd=gap('d'), gr=gap('r'), S=v['s_d'] + v['s_r'], J=sum(issued(v, i) for i in 'drt')))
    print(f'engine reproduces stored executed minima (X1 and X4): {ok_engine}/{n}')
    print(f'broad funded sequence reaches broad bound (separate and pooled): {ok_bound}/{n}')
    print('\nheadline balance sheets, USD trillions')
    print('year | D now | D broad (J, fed loans) | min now sep/pool | min broad sep/pool | broad D/min | domestic gap broad | ROW gap broad')
    for y in years:
        hid = f'{y}/holder_correction/' + ('source_net_assets' if y == 2008 else 'equity_correction') + '/observed_us_mix/agency_lookthrough'
        h = next(r for r in rows[y] if r['id'] == hid)
        print(f"{y} | {h['D']/T:.2f} | {h['Db']/T:.2f} ({h['J']/T:.2f}, {h['S']/T:.2f}) | {h['n1']/T:.2f}/{h['n4']/T:.2f} | "
              f"{h['b1']/T:.2f}/{h['b4']/T:.2f} | {h['Db']/h['b1']:.2f} | {h['gd']/T:+.2f} | {h['gr']/T:+.2f}")
    print('\nranges of broad separate minimum across each year\'s balance sheets (look-through only)')
    for y in years:
        xs = [r['b1'] / T for r in rows[y] if r['rep'] == 'agency_lookthrough']
        print(y, f'{min(xs):.2f}-{max(xs):.2f}', len(xs))


if __name__ == '__main__':
    main()
