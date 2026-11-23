"""The government as one more group: a toy check.

Consolidate the Treasury and the central bank into one government sector G.
Seen from the banks, G is a depositor whose deposit is -R (reserves are its
overdraft) and whose debt is the bonds held outside the central bank. Its
net position is V_G = W_T + E_F (Treasury plus central-bank net positions).
Consolidated debt D_c = bonds held outside the central bank + all loans
(bonds the central bank holds are internal to G).

Hypotheses, on the static problem (fixed at the end: bank equity, each
household group's net position V_g with its money floor, and V_G):
  H1  no limit on G's overdraft:      min D_c = sum_g [m_g0 - V_g]+
  H2  overdraft may not grow, R<=R0:  min D_c = sum_g [m_g0 - V_g]+ + [-R0 - V_G]+
H2 is the household rule applied to G with deposit floor m_G0 = -R0.

Operational check: the menu of toy.py without transfers, taxes or spending
(they move net positions). Central-bank purchases repay a bond, in G's terms,
with overdraft. Optionally central-bank sales (quantitative tightening), and
the overdraft cap either at every step (like a money floor) or at the end.
Run from this directory:  python3 gov_as_group.py [instances] [seed]
"""
import random, sys
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0, '.')
import toy


def rows(lay, x0):
    VG = lay.single('T') - lay.bonds() + lay.single('EF')
    fixed = [lay.single('EB'), VG] + [lay.V(g) for g in range(lay.G)]
    return fixed, VG


def objective(lay):
    return lay.D() - lay.single('bF')


def static(lay, x0, cap_reserves):
    fixed, _ = rows(lay, x0)
    A_eq = [lay.bank_balance(), lay.fed_balance()] + fixed
    b_eq = [0, 0] + [r @ x0 for r in fixed]
    A_ub = [-lay.money(g) for g in range(lay.G)]; b_ub = [-(lay.money(g) @ x0) for g in range(lay.G)]
    if cap_reserves: A_ub.append(lay.single('R')); b_ub.append(x0[lay.i['R']])
    r = linprog(objective(lay), A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                bounds=toy.bounds_state(lay), method='highs')
    assert r.status == 0, r.message
    return r.fun


def hypothesis(lay, x0, cap_reserves):
    h = sum(max(0.0, lay.money(g) @ x0 - lay.V(g) @ x0) for g in range(lay.G))
    if cap_reserves:
        _, VG = rows(lay, x0)
        h += max(0.0, -x0[lay.i['R']] - VG @ x0)
    return h


def central_bank_sales(lay):
    """Central-bank sales (quantitative tightening): reverse of its purchases."""
    out = [('central bank sells bond to bank', 'C', lay.vec(bF=-1, bB=1, R=-1))]
    for g in range(lay.G):
        out.append((f'central bank sells loan on {g} to bank', 'C', lay.vec(**{f'lF_{g}': -1, f'lB_{g}': 1, 'R': -1})))
        out.append((f'central bank sells bond to {g}', 'C', lay.vec(**{'bF': -1, f'b{g}': 1, f'm{g}': -1, 'R': -1})))
    return out


def operational(lay, x0, cap_reserves, sales=False, cap_every_step=True, stages=8):
    """Time-expanded LP over the menu with every state between phases valid
    (the reserve cap at every step, or only at the end), then an exact
    transaction-by-transaction replay (toy.greedy)."""
    keep = toy.excluding('equity', 'taxes', 'spends', 'transfer')
    menu = [t for t in toy.transactions(lay) if keep(t[0])] + (central_bank_sales(lay) if sales else [])
    V = np.array([v for _, _, v in menu]).T; k = V.shape[1]
    subs = [ph for _ in range(stages) for ph in 'ABC']
    cols = [(s, t) for s, ph in enumerate(subs) for t in range(k) if menu[t][1] == ph]
    nv = len(cols)
    floors = [lay.money(g) for g in range(lay.G)]
    A_ub, b_ub = [], []
    for s in range(len(subs)):
        upto = np.zeros((lay.n, nv))
        for c, (s2, t) in enumerate(cols):
            if s2 <= s: upto[:, c] = V[:, t]
        for j, n in enumerate(lay.names):
            if n != 'EF': A_ub.append(-upto[j]); b_ub.append(x0[j])
        for f in floors: A_ub.append(-(f @ upto)); b_ub.append(0)
        if cap_reserves and cap_every_step: A_ub.append(upto[lay.i['R']]); b_ub.append(0)
    total = np.zeros((lay.n, nv))
    for c, (s2, t) in enumerate(cols): total[:, c] = V[:, t]
    if cap_reserves and not cap_every_step: A_ub.append(total[lay.i['R']]); b_ub.append(0)
    fixed, _ = rows(lay, x0)
    r = linprog(objective(lay) @ total, A_ub=A_ub, b_ub=b_ub, A_eq=[f @ total for f in fixed],
                b_eq=[0] * len(fixed), bounds=[(0, None)] * nv, method='highs')
    assert r.status == 0, r.message
    x = x0.copy(); ok = True; lo = [f @ x0 for f in floors]
    for s in range(len(subs)):
        lam = np.zeros(k)
        for c, (s2, t) in enumerate(cols):
            if s2 == s: lam[t] += r.x[c]
        done, x = toy.greedy(lay, menu, x, lam, floors, lo)
        ok = ok and done and (not (cap_reserves and cap_every_step) or x[lay.i['R']] <= x0[lay.i['R']] + 1e-6)
    ok = ok and (not cap_reserves or x[lay.i['R']] <= x0[lay.i['R']] + 1e-6)
    return objective(lay) @ x0 + r.fun, ok


def main(instances=200, seed=5):
    configs = [('H1 uncapped overdraft', False, False, True),
               ('H2 capped, purchases only', True, False, True),
               ('H2 capped, with sales', True, True, True),
               ('H2 capped at end only, with sales', True, True, False)]
    for label, cap, sales, every in configs:
        rng = random.Random(seed); bad = gap = fail = 0
        for _ in range(instances):
            lay = toy.Layout(rng.choice([1, 2])); x0 = toy.opening(lay, rng)
            s = static(lay, x0, cap); h = hypothesis(lay, x0, cap)
            o, ok = operational(lay, x0, cap, sales, every)
            bad += abs(s - h) > 1e-6; gap += o > s + 1e-6; fail += not ok
        print(f'{label:36s} static != hypothesis: {bad:3d}   operational above static: {gap:3d}   replay failed: {fail:3d}')
    print(f'({instances} openings each, one or two household groups)')


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
