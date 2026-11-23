"""The household split: domestic nonbanks as five DFA wealth groups plus the rest.

Parties: H1..H5 (Bottom 50%, Next 40%, Next 9%, Remaining top 1%, Top 0.1%), Q
(the rest of the domestic nonbank sector), r (rest of the world), t (Treasury),
b (bank), f (central bank).

Known: every claim between the domestic sector as a whole and r, t, b, f, and
the domestic sector's claims on itself, from the stored completed balance
sheet (first balance sheet of the year, look-through, foreign issuers as
nonbanks, as in series.py); each group's loans owed, debt securities held
(government and municipal; corporate and foreign) and loans held, from the
Distributional Financial Accounts, each column rescaled so the five groups add
up to the March 2026 Z.1 (as slice_checks.py does for the split kernel);
and the published margins netting_range.py uses.

Unknown: who holds each group's debt and the rest's debt; who issued what each
group holds; how the domestic sector's nondeposit claims on banks split.

Each judgement call is labelled J1, J2, ... here and in README.md.

  J1  Groups may hold claims on other groups and on themselves (household
      mortgages held by households, and agency mortgage-backed securities,
      which the look-through representation turns into claims on the
      underlying mortgage borrowers). A group's claims on itself cancel.
  J2  Only debt securities and loans held count as a group's claims, as in the
      kernel's narrow bracket. Deposits and currency are money and never
      cancel; money-market fund shares, pensions, insurance, equities and
      businesses stay locked.
  J3  Bank bonds held by households are nondeposit claims on banks (as in the
      two-sector model, which treats bank-issued securities as bank funding).
      They sit inside each group's corporate and foreign bonds; together with
      foreign bonds held they are at most the group's corporate and foreign
      bonds, and in total at most households' corporate and foreign bonds
      (B.101.h).
  J4  Households hold no claims on the central bank other than currency: the
      domestic sector's other claims on it (reverse repurchase agreements,
      deposits of GSEs and others) belong to the rest.
  J5  The Treasury's claims on households are at least the federal student
      loans (L.222), and each group's at most its consumer credit.
  J6  Households' Treasury securities total B.101.h's figure, each group's at
      most its government and municipal securities.
  J7  Household debt held by banks and the central bank together lies between
      the bounds netting_range.py derives from L.218, L.222, B.101.h and the
      MBS capacity evidence.
  J8  For claim sets B and C (Treasury account, reserves, non-debt claims,
      advances, vault cash), non-debt claims of or on the domestic sector belong
      to the rest, not to households.
  J9  DFA sub-items are rescaled with their parent column's factor.
"""
import csv
import importlib.util
import io
import json
import os
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netting_lp import Network

M = 1e6
GROUPS = ['Bottom50', 'Next40', 'Next9', 'RemainingTop1', 'TopPt1']
H = ['H1', 'H2', 'H3', 'H4', 'H5']
DOM = H + ['Q']
DFA = 'paper-prep/sector-slicing/raw/dfa.zip'
VINTAGE = {'Debt securities': ['LM194022005.A'], 'Loans (Assets)': ['FL194023005.A'],
           'Loans (Liabilities)': ['FL194123005.A']}
SUB = {'U.S. government and municipal securities': 'Debt securities', 'Corporate and foreign bonds': 'Debt securities',
       'Consumer credit': 'Loans (Liabilities)'}


def _load(path, name):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


nr = _load('paper-prep/sector-slicing/netting_range.py', 'netting_range')
series = _load('paper-prep/broad-debt/series.py', 'series')


def dfa_groups():
    with zipfile.ZipFile(DFA) as z:
        r = list(csv.DictReader(io.StringIO(z.read('dfa-networth-levels-detail.csv').decode())))
    return {(int(x['Date'][:4]), x['Category']): {k: float(v) / M for k, v in x.items() if k not in ('Date', 'Category') and v != ''}
            for x in r if x['Date'].endswith('Q4')}


def b101h():
    z = zipfile.ZipFile(nr.ZIP)
    r = list(csv.reader(io.StringIO(z.read('csv/b101h.csv').decode())))
    h = r[0]
    return {int(x[0]): {h[k]: float(x[k]) / M for k in range(1, len(h)) if x[k] not in ('', 'ND')} for x in r[1:]}


def inputs():
    """Per year: stored opening (USD trillions), rescaled group items, margins."""
    X, B = dfa_groups(), b101h()
    q, a = nr.quarterly(nr.Q), nr.annual()
    ev = {y['year']: y for y in json.load(open(nr.EV))['years']}
    rec = {}
    for r in series.records():
        if r['representation'] == 'agency_lookthrough' and r['nonbank_foreign_security_issuers'] == 'nonbank' \
                and r['securities_repayable'] and not r['pooled']:
            rec.setdefault(int(r['id'][:4]), r)
    out = {}
    for y, r in sorted(rec.items()):
        o = {k: v / M for k, v in r['opening'].items()}
        g = lambda k: o.get(k, 0)
        cl = lambda h, t: g('l_' + h + t) + g('a_' + h + t) + g('z_' + h + t)
        scale = {col: sum(B[y][c] for c in codes) / sum(X[(y, G)][col] for G in GROUPS) for col, codes in VINTAGE.items()}
        grp = {}
        for i, G in zip(H, GROUPS):
            x = X[(y, G)]
            grp[i] = {k: x[k] * scale[k] for k in VINTAGE} | {k: x[k] * scale[p] for k, p in SUB.items()}   # J9
        e = ev[y]; sv = {k: v / M for k, v in e['source_values'].items()}
        pr = next(p for p in e['projections'] if p['id'] == r['id'])
        bank_lo, bank_hi = (v / M for v in pr['bank_one_to_four_capacity_bound'])
        fed_lo, fed_hi = (v / M for v in pr['fed_one_to_four_capacity_bound'])
        home_direct = sum(sv[k] for k in ('US_banks_direct_home_mortgages', 'affiliated_area_banks_direct_home_mortgages',
                                          'credit_unions_direct_home_mortgages', 'foreign_bank_offices_direct_home_mortgages'))
        cc_bank = q['CC_US'][y] + q['CC_CU'][y]
        bf_min = cc_bank + a['DEPNEC'][y] + max(0.0, home_direct + bank_lo + fed_lo - sv['noncorporate_business_home_mortgages'])
        bf_max = min(cc_bank + a['DEPNEC'][y] + home_direct + bank_hi, cl('b', 'd')) + min(fed_hi, cl('f', 'd'))
        out[y] = dict(o=o, D=r['opening_debt'] / M, groups=grp, SL=q['SL'][y], HGOV=a['HGOV'][y], HCORP=a['HCORP'][y],
                      bf=(bf_min, bf_max), id=r['id'])
    return out


def network(inp, variant='A', relax=()):
    """relax: judgement calls to drop for a sensitivity run, from ('J4', 'J8')."""
    o, grp = inp['o'], inp['groups']
    g = lambda k: o.get(k, 0)
    cl = lambda h, t: g('l_' + h + t) + g('a_' + h + t) + g('z_' + h + t)
    N = Network(DOM + ['r', 't', 'b', 'f'])
    u = {}
    def unk(name, lo, hi):
        N.unknown(name, lo, hi); u[name] = name; return name
    big = max(cl(h, 'd') for h in 'bfdr') + g('d_b') + g('s_d') + 10
    # domestic debt by holder (b, f, r, t, and every domestic party) and issuer (every domestic party)
    for hold in ['b', 'f', 'r', 't'] + DOM:
        for iss in DOM:
            N.claim(hold, iss, True, unk(f'D_{hold}_{iss}', 0, big))
    # domestic holdings of Treasuries and of foreign debt
    for hold in DOM:
        N.claim(hold, 't', True, unk(f'D_{hold}_t', 0, big))
        N.claim(hold, 'r', True, unk(f'D_{hold}_r', 0, big))
    # nondeposit claims on banks (J3); claims on the central bank belong to Q (J4)
    for hold in DOM:
        N.claim(hold, 'b', False, unk(f'N_{hold}_b', 0, big))
    if 'J4' in relax:                     # any domestic party may hold the claims on the central bank
        for hold in DOM:
            N.claim(hold, 'f', False, unk(f'N_{hold}_f', 0, big))
    else:
        N.claim('Q', 'f', False, g('d_qh'))
    # known claims not involving the domestic split
    for p in ('l_', 'a_', 'z_'):
        N.claim('r', 'r', True, g(p + 'rr')); N.claim('b', 'r', True, g(p + 'br')); N.claim('f', 'r', True, g(p + 'fr'))
    for k in ('s_r', 'a_tr', 'z_tr'):
        N.claim('t', 'r', True, g(k))
    N.claim('r', 't', True, g('r_b')); N.claim('r', 'b', False, g('r_qbh')); N.claim('r', 'f', False, g('r_qh'))
    N.claim('b', 't', True, g('bb')); N.claim('f', 't', True, g('bf'))
    if variant in 'BC':                                                   # J8
        N.claim('t', 'f', False, g('t')); N.claim('t', 'f', False, g('qg')); N.claim('b', 'f', False, g('r'))
        for h in 'bfdrt':
            for s in 'dr':
                amt = g('j_' + h + s) - g('a_' + h + s) - g('z_' + h + s)
                if 'J8' in relax and 'd' in (h, s) and amt > 0:   # any domestic party may hold or owe them
                    pairs = [(a, b) for a in (DOM if h == 'd' else [h]) for b in (DOM if s == 'd' else [s])]
                    names = []
                    for a, b in pairs:
                        names.append(unk(f'J_{a}_{b}_{h}{s}', 0, amt)); N.claim(a, b, False, names[-1])
                    N.constrain({n: 1 for n in names}, amt, amt)
                else:
                    N.claim('Q' if h == 'd' else h, 'Q' if s == 'd' else s, False, amt)
    if variant == 'C':
        N.claim('f', 'b', False, g('u')); N.claim('b', 'f', False, g('cb'))
    def eq(coeffs, value):
        N.constrain(coeffs, value, value)
    # stored domestic totals
    for hold in 'bfr':
        eq({f'D_{hold}_{i}': 1 for i in DOM}, cl(hold, 'd'))
    eq({f'D_t_{i}': 1 for i in DOM}, g('s_d') + g('a_td') + g('z_td'))
    eq({f'D_{a}_{b}': 1 for a in DOM for b in DOM}, cl('d', 'd'))
    eq({f'D_{i}_t': 1 for i in DOM}, g('d_b'))
    eq({f'D_{i}_r': 1 for i in DOM}, cl('d', 'r'))
    eq({f'N_{i}_b': 1 for i in DOM}, g('d_qbh'))
    if 'J4' in relax:
        eq({f'N_{i}_f': 1 for i in DOM}, g('d_qh'))
    # each group's own totals (DFA, rescaled)
    for i in H:
        x = grp[i]
        eq({f'D_{h}_{i}': 1 for h in ['b', 'f', 'r', 't'] + DOM}, x['Loans (Liabilities)'])
        eq({f'D_{i}_{s}': 1 for s in DOM + ['t', 'r']} | {f'N_{i}_b': 1}, x['Debt securities'] + x['Loans (Assets)'])   # J2
        N.constrain({f'D_{i}_t': 1}, None, x['U.S. government and municipal securities'])                              # J6
        N.constrain({f'D_{i}_r': 1, f'N_{i}_b': 1}, None, x['Corporate and foreign bonds'])                             # J3
        N.constrain({f'D_t_{i}': 1}, None, x['Consumer credit'])                                                       # J5
    N.constrain({f'D_t_{i}': 1 for i in H}, inp['SL'], None)                                                          # J5
    eq({f'D_{i}_t': 1 for i in H}, inp['HGOV'])                                                                        # J6
    N.constrain({f'D_{i}_r': 1 for i in H} | {f'N_{i}_b': 1 for i in H}, None, inp['HCORP'])                         # J3
    N.constrain({f'D_{h}_{i}': 1 for h in 'bf' for i in H}, *inp['bf'])                                              # J7
    return N
