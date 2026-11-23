"""Static versus operational minimum debt: a toy check.

Isolated toy (no project imports). Cash-free balance sheets with public
groups, one consolidated bank, a Treasury and a central bank (Fed).

State, all >= 0 except Fed equity EF:
  m[g]   deposits of public group g          (bank liability)
  b[g]   bonds held by group g; bB, bF        bonds held by bank, Fed
  l[h,g] loans owed by group g, held by h in {B, F, groups}
  R      reserves (Fed liability, bank asset)
  T      Treasury account (Fed liability, Treasury asset)
  EB     bank equity (>= 0);  EF Fed equity (free sign)
Balance:   bank  sum_g l[B,g] + bB + R = sum_g m[g] + EB
           Fed   bF + sum_g l[F,g]     = R + T + EF
Derived:   B = sum b, L = sum l, D = B + L
           V[g] = m[g] + b[g] + sum_g' l[g,g'] - sum_h l[h,g]  (group net position)
           WT = T - B                                         (Treasury net position)
Sector net positions sum to zero: sum V + EB + EF + WT = 0.
Notation (paper): EB = V_B, EF = V_F, WT = V_T, T = R_T, R = R_B.

Policy: fixed quantities are imposed on the END state only; money is a floor
at EVERY step (total money for a pooled public, each group's otherwise).

For each case: (1) static LP minimum of D over end states; (2) operational
minimum: LP over non-negative transaction amounts of a named menu, then a
replay in a fixed order checking every intermediate state (non-negativity,
EB >= 0, money floors). Run:  python3 -I toy.py [instances] [seed]
"""
import random, sys
import numpy as np
from scipy.optimize import linprog


class Layout:
    def __init__(self, G):
        self.G = G
        self.names = []
        for g in range(G): self.names += [f'm{g}', f'b{g}']
        self.names += ['bB', 'bF', 'R', 'T', 'EB', 'EF']
        self.holders = ['B', 'F'] + list(range(G))
        for h in self.holders:
            for g in range(G): self.names.append(f'l{h}_{g}')
        self.i = {n: k for k, n in enumerate(self.names)}
        self.n = len(self.names)

    def vec(self, **kw):
        v = np.zeros(self.n)
        for k, x in kw.items(): v[self.i[k]] += x
        return v

    def lin(self, terms):
        v = np.zeros(self.n)
        for name, c in terms: v[self.i[name]] += c
        return v

    # linear functionals
    def money(self, g=None):
        gs = range(self.G) if g is None else [g]
        return self.lin([(f'm{x}', 1) for x in gs])

    def D(self):
        t = [(f'b{g}', 1) for g in range(self.G)] + [('bB', 1), ('bF', 1)]
        t += [(f'l{h}_{g}', 1) for h in self.holders for g in range(self.G)]
        return self.lin(t)

    def V(self, g=None):
        gs = range(self.G) if g is None else [g]
        t = []
        for x in gs:
            t += [(f'm{x}', 1), (f'b{x}', 1)]
            t += [(f'l{x}_{y}', 1) for y in range(self.G)]
            t += [(f'l{h}_{x}', -1) for h in self.holders]
        return self.lin(t)

    def bank_balance(self):
        t = [(f'l{"B"}_{g}', 1) for g in range(self.G)] + [('bB', 1), ('R', 1), ('EB', -1)]
        t += [(f'm{g}', -1) for g in range(self.G)]
        return self.lin(t)

    def fed_balance(self):
        t = [('bF', 1)] + [(f'lF_{g}', 1) for g in range(self.G)] + [('R', -1), ('T', -1), ('EF', -1)]
        return self.lin(t)

    def bonds(self):
        return self.lin([(f'b{g}', 1) for g in range(self.G)] + [('bB', 1), ('bF', 1)])

    def fed_holdings(self):
        return [self.lin([('bF', 1)])] + [self.lin([(f'lF_{g}', 1)]) for g in range(self.G)]

    def single(self, name):
        return self.lin([(name, 1)])


def transactions(lay):
    """Named transaction directions. Phase: A raises money, B leaves money,
    C lowers money. Within a replay, phases run in order A, B, C."""
    G = lay.G; T = []
    def add(name, phase, **kw): T.append((name, phase, lay.vec(**kw)))
    for g in range(G):
        add(f'bank buys bond from {g}', 'A', **{f'b{g}': -1, 'bB': 1, f'm{g}': 1})
        add(f'bank pays equity to {g}', 'A', **{'EB': -1, f'm{g}': 1})
        add(f'Fed buys bond from {g}', 'A', **{f'b{g}': -1, 'bF': 1, f'm{g}': 1, 'R': 1})
        add(f'Treasury spends to {g}', 'A', **{'T': -1, f'm{g}': 1, 'R': 1})
        add(f'Treasury redeems bond of {g}', 'A', **{f'b{g}': -1, 'T': -1, f'm{g}': 1, 'R': 1})
        for h in range(G):
            add(f'bank buys loan on {g} from {h}', 'A', **{f'l{h}_{g}': -1, f'lB_{g}': 1, f'm{h}': 1})
        add(f'Fed buys bank loan on {g}', 'B', **{f'lB_{g}': -1, f'lF_{g}': 1, 'R': 1})
        add(f'{g} repays bank loan', 'C', **{f'lB_{g}': -1, f'm{g}': -1})
        add(f'{g} repays Fed loan', 'C', **{f'lF_{g}': -1, f'm{g}': -1, 'R': -1})
        add(f'Treasury taxes {g}', 'C', **{f'm{g}': -1, 'T': 1, 'R': -1})
        for h in range(G):
            if h != g:
                add(f'transfer from {h} to {g}', 'B', **{f'm{h}': -1, f'm{g}': 1})
    add('Fed buys bond from bank', 'B', **{'bB': -1, 'bF': 1, 'R': 1})
    add('Treasury redeems bank bond', 'B', **{'bB': -1, 'T': -1, 'R': 1})
    add('Treasury redeems Fed bond', 'B', **{'bF': -1, 'T': -1})
    return T


def opening(lay, rng):
    """Random balanced opening with EB >= 0 (EF may be negative)."""
    while True:
        x = np.zeros(lay.n)
        for n in lay.names:
            if n in ('EB', 'EF', 'R'): continue
            x[lay.i[n]] = rng.choice([0, 0, rng.randint(1, 40)])
        # reserves and Fed equity close the Fed; bank equity closes the bank
        x[lay.i['R']] = rng.randint(0, 30)
        x[lay.i['EF']] = lay.fed_balance() @ x   # Fed: assets - R - T - EF = 0
        eb = lay.bank_balance() @ x               # bank residual with EB = 0
        if eb >= 0:
            x[lay.i['EB']] = eb
            assert abs(lay.bank_balance() @ x) < 1e-9 and abs(lay.fed_balance() @ x) < 1e-9
            if lay.D() @ x > 0: return x


# No move changes central-bank equity: no model in the project allows the
# central bank to cancel or forgive a claim (debt is reduced only by funded
# repayment or redemption). So every menu here preserves EF.
EB_MOVES = ('equity',)
FISCAL = ('taxes', 'spends')
def excluding(*words):
    return lambda n: not any(w in n for w in words)

CASES = {
    # name: (fixed functionals, per-group floors?, menu filter)
    '1 {M}': ('M', False, excluding()),
    '2 {M, EF}': ('M EF', False, excluding()),
    '3 {M, EF, EB}': ('M EF EB', False, excluding(*EB_MOVES)),
    '4 {M, EF, EB, V}, no transfers': ('M EF EB V', False, excluding(*EB_MOVES, *FISCAL, 'transfer')),
    '4 {M, EF, EB, V}, with transfers': ('M EF EB V', False, excluding(*EB_MOVES, *FISCAL)),
    '5 {m_g, EF, EB, V_g}': ('M EF EB Vg', True, excluding(*EB_MOVES, *FISCAL, 'transfer')),
    'three operations {m_g, EB, V_g, B, T, Fed}': ('M EB Vg B T FED', True,
                        lambda n: n.startswith('bank buys') or 'repays bank loan' in n),
}


def fixed_rows(lay, spec, x0):
    rows = []
    for k in spec.split():
        if k == 'EF': rows.append(lay.single('EF'))
        elif k == 'EB': rows.append(lay.single('EB'))
        elif k == 'V': rows.append(lay.V())
        elif k == 'Vg': rows += [lay.V(g) for g in range(lay.G)]
        elif k == 'B': rows.append(lay.bonds())
        elif k == 'T': rows.append(lay.single('T'))
        elif k == 'FED': rows += lay.fed_holdings()
    return rows


def bounds_state(lay):
    return [(None, None) if n == 'EF' else (0, None) for n in lay.names]


def static_min(lay, spec, per_group, x0):
    A_eq = [lay.bank_balance(), lay.fed_balance()] + fixed_rows(lay, spec, x0)
    b_eq = [0, 0] + [r @ x0 for r in A_eq[2:]]
    if per_group: A_ub = [-lay.money(g) for g in range(lay.G)]; b_ub = [-(lay.money(g) @ x0) for g in range(lay.G)]
    else: A_ub = [-lay.money()]; b_ub = [-(lay.money() @ x0)]
    r = linprog(lay.D(), A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds_state(lay), method='highs')
    assert r.status == 0, r.message
    return r.fun


def greedy(lay, menu, x0, lam, floors, lo):
    """Scheduler. Apply money-raising and money-neutral transactions (phases
    A, B) as far as validity allows; only when they are stuck apply one
    money-lowering transaction (phase C), preferring taxes, which can unblock
    redemptions. Every intermediate state is checked: non-negative coordinates
    (EF free) and money floors."""
    x = x0.copy(); rem = lam.copy()
    def room(t, v):
        step = rem[t]
        for j, n in enumerate(lay.names):
            if n != 'EF' and v[j] < 0: step = min(step, max(0.0, x[j]) / -v[j])
        for f, l in zip(floors, lo):
            d = f @ v
            if d < 0: step = min(step, max(0.0, f @ x - l) / -d)
        return step
    order_c = sorted([t for t, m in enumerate(menu) if m[1] == 'C'],
                     key=lambda t: 0 if 'taxes' in menu[t][0] else 1)
    for _ in range(20000):
        moved = False
        for t, (name, ph, v) in enumerate(menu):
            if ph == 'C' or rem[t] <= 1e-10: continue
            s_ = room(t, v)
            if s_ > 1e-12: x = x + s_ * v; rem[t] -= s_; moved = True
        if moved: continue
        for t in order_c:
            if rem[t] <= 1e-10: continue
            s_ = room(t, menu[t][2])
            if s_ > 1e-12:
                x = x + s_ * menu[t][2]; rem[t] -= s_; moved = True; break
        if not moved or rem.max() <= 1e-8: break
    return rem.max() <= 1e-6, x

def operational(lay, spec, per_group, x0, menu, stages=8):
    """Operational minimum as a time-expanded LP: `stages` rounds, each with
    phases A, B, C; every state between sub-steps must be valid. Then an exact
    replay: within each sub-step its moves are applied by the greedy scheduler,
    checking every intermediate state. Returns (min debt, replay succeeded)."""
    V = np.array([v for _, _, v in menu]).T
    k = V.shape[1]
    subs = [ph for _ in range(stages) for ph in 'ABC']
    cols = [(s, t) for s, ph in enumerate(subs) for t in range(k) if menu[t][1] == ph]
    nv = len(cols)
    floors = [lay.money(g) for g in range(lay.G)] if per_group else [lay.money()]
    A_ub, b_ub = [], []
    for s in range(len(subs)):
        upto = np.zeros((lay.n, nv))
        for c, (s2, t) in enumerate(cols):
            if s2 <= s: upto[:, c] = V[:, t]
        for j, n in enumerate(lay.names):
            if n != 'EF': A_ub.append(-upto[j]); b_ub.append(x0[j])
        for f in floors: A_ub.append(-(f @ upto)); b_ub.append(0)
    total = np.zeros((lay.n, nv))
    for c, (s2, t) in enumerate(cols): total[:, c] = V[:, t]
    fixed = fixed_rows(lay, spec, x0)
    A_eq = [r @ total for r in fixed]
    r = linprog(lay.D() @ total, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq or None,
                b_eq=[0] * len(A_eq) or None, bounds=[(0, None)] * nv, method='highs')
    assert r.status == 0, r.message
    x = x0.copy(); ok = True
    lo = [f @ x0 for f in floors]
    for s in range(len(subs)):
        lam = np.zeros(k)
        for c, (s2, t) in enumerate(cols):
            if s2 == s: lam[t] += r.x[c]
        done, x = greedy(lay, menu, x, lam, floors, lo)
        ok = ok and done
    for row in [lay.bank_balance(), lay.fed_balance()]:
        assert abs(row @ x) < 1e-6
    return lay.D() @ x0 + r.fun, ok

def closed_form(case, lay, x0):
    """Closed forms derived in the note for the pooled cash-free cases."""
    M = lay.money() @ x0; EF = x0[lay.i['EF']]; EB = x0[lay.i['EB']]
    WT = x0[lay.i['T']] - lay.bonds() @ x0; V = lay.V() @ x0
    if case.startswith('1'): return 0.0
    if case.startswith('2'): return max(0.0, M + EF)
    if case.startswith('3'): return max(0.0, M + EF + EB)
    if case.startswith('4'):
        # Valid when the Fed's reserve constraint does not bind (see note).
        return max(0.0, WT) + max(M, V) + EB + EF
    if case.startswith('5'):
        return max(0.0, WT) + sum(max(lay.money(g) @ x0, lay.V(g) @ x0) for g in range(lay.G)) + EB + EF
    if case.startswith('paper'):
        i = lay.i; K = lay.bonds() @ x0
        for g in range(lay.G):
            L = sum(x0[i[f'l{h}_{g}']] for h in lay.holders); f = x0[i[f'lF_{g}']]
            c = x0[i[f'b{g}']] + sum(x0[i[f'l{g}_{y}']] for y in range(lay.G))
            K += max(f, L - c)
        return K
    return None


def main(instances=400, seed=3):
    rng = random.Random(seed)
    print(f'{instances} random openings per case (1 or 2 public groups; always 2 where floors are per group)')
    for case, (spec, per_group, keep) in CASES.items():
        gap = 0; order_fail = 0; cf_bad = 0; case1_not_case2 = 0
        for _ in range(instances):
            lay = Layout(2 if per_group else rng.choice([1, 2]))
            x0 = opening(lay, rng)
            menu = [t for t in transactions(lay) if keep(t[0])]
            s = static_min(lay, spec, per_group, x0)
            o, ok = operational(lay, spec, per_group, x0, menu)
            if o > s + 1e-6: gap += 1
            if not ok: order_fail += 1
            cf = closed_form(case, lay, x0)
            if cf is not None and abs(cf - s) > 1e-6: cf_bad += 1
            if case.startswith('1') and abs(o - closed_form('2', lay, x0)) > 1e-6: case1_not_case2 += 1
        print(f'{case:36s} operational above static: {gap:4d}   replay order failed: {order_fail:4d}'
              + f'   closed form mismatches: {cf_bad}'
              + (f'   operational != [M0+EF]+: {case1_not_case2}' if case.startswith('1') else ''))


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
