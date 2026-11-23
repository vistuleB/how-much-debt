"""Execute the explicit histories of proofs.md and check them.

Each history is a list of named transactions from toy.transactions (plus the
central-bank sales of gov_as_group.py where stated). Every intermediate
balance sheet is checked: both balance sheets, non-negative holdings,
non-negative bank equity, and each household group's money floor (the total
money floor in the pooled cases). The end state is compared with the
static minimum from the linear programme and with the closed form.
Run from this directory:  python3 paths.py [instances] [seed]
"""
import random, sys
import numpy as np
sys.path.insert(0, '.')
import toy, gov_as_group as gg


class Run:
    def __init__(self, lay, x0, per_group):
        self.lay, self.x, self.x0 = lay, x0.copy(), x0
        self.per_group = per_group
        self.moves = {n: v for n, _, v in toy.transactions(lay) + gg.central_bank_sales(lay)}
        self.ok = True

    def __getitem__(self, name):
        return self.x[self.lay.i[name]]

    def do(self, name, amount):
        if amount <= 1e-12: return
        self.x = self.x + amount * self.moves[name]
        lay, x = self.lay, self.x
        neg = any(x[j] < -1e-7 for j, n in enumerate(lay.names) if n != 'EF')
        bal = abs(lay.bank_balance() @ x) > 1e-7 or abs(lay.fed_balance() @ x) > 1e-7
        if self.per_group:
            low = any(lay.money(g) @ x < lay.money(g) @ self.x0 - 1e-7 for g in range(lay.G))
        else:
            low = lay.money() @ x < lay.money() @ self.x0 - 1e-7
        if neg or bal or low:
            self.ok = False

    # building blocks ---------------------------------------------------
    def everything_to_central_bank(self):
        """Banks sell their bonds and loans to the central bank; the public
        sells its bonds and loans to banks, which sell them on."""
        lay, G = self.lay, self.lay.G
        self.do('Fed buys bond from bank', self['bB'])
        for g in range(G): self.do(f'Fed buys bank loan on {g}', self[f'lB_{g}'])
        for g in range(G):
            self.do(f'bank buys bond from {g}', self[f'b{g}'])
            for h in range(G):
                self.do(f'bank buys loan on {g} from {h}', self[f'l{h}_{g}'])
        self.do('Fed buys bond from bank', self['bB'])
        for g in range(G): self.do(f'Fed buys bank loan on {g}', self[f'lB_{g}'])

    def redeem_with_treasury_account(self):
        self.do('Treasury redeems Fed bond', min(self['T'], self['bF']))

    def repay(self, g, amount):
        self.do(f'{g} repays Fed loan', min(amount, self[f'lF_{g}']))


def case5(lay, x0):
    """Per-group floors; E_F, E_B, V_g fixed."""
    run = Run(lay, x0, True)
    c = {g: lay.V(g) @ x0 - lay.money(g) @ x0 + sum(x0[lay.i[f'l{h}_{g}']] for h in lay.holders) for g in range(lay.G)}
    L = {g: sum(x0[lay.i[f'l{h}_{g}']] for h in lay.holders) for g in range(lay.G)}
    run.everything_to_central_bank()
    run.redeem_with_treasury_account()
    for g in range(lay.G): run.repay(g, min(L[g], c[g]))
    return run


def case4(lay, x0):
    """Pooled floor and total V fixed; transfers between groups allowed."""
    run = Run(lay, x0, False)
    run.everything_to_central_bank()
    run.redeem_with_treasury_account()
    # gather all money in group 0, which then pays every group's Fed loans
    # through transfers placed just before each repayment
    total_c = sum(lay.V(g) @ x0 for g in range(lay.G)) - lay.money() @ x0 + \
        sum(x0[lay.i[f'l{h}_{g}']] for h in lay.holders for g in range(lay.G))
    budget = max(0.0, min(total_c, sum(run[f'lF_{g}'] for g in range(lay.G))))
    for g in range(lay.G):
        r = min(budget, run[f'lF_{g}'])
        for h in range(lay.G):
            if h != g and run[f'm{g}'] < r:
                run.do(f'transfer from {h} to {g}', min(run[f'm{h}'], r - run[f'm{g}']))
        run.repay(g, r); budget -= r
    return run


def case3(lay, x0, payouts=False):
    """Pooled floor; E_F (and E_B unless payouts) fixed; V free: taxes,
    spending and transfers allowed."""
    run = Run(lay, x0, False)
    if payouts: run.do('bank pays equity to 0', run['EB'])
    run.everything_to_central_bank()
    run.redeem_with_treasury_account()
    M0 = lay.money() @ x0
    loans = lambda: sum(run[f'lF_{g}'] for g in range(lay.G))
    excess = lambda: lay.money() @ run.x - M0
    # repay loans out of money above the floor (transfers to the borrower)
    for g in range(lay.G):
        r = min(run[f'lF_{g}'], excess())
        for h in range(lay.G):
            if h != g and run[f'm{g}'] < r:
                run.do(f'transfer from {h} to {g}', min(run[f'm{h}'], r - run[f'm{g}']))
        run.repay(g, r)
    # tax what is left above the floor, then redeem bonds with it
    for g in range(lay.G):
        run.do(f'Treasury taxes {g}', min(run[f'm{g}'], excess()))
    run.redeem_with_treasury_account()
    # spend what the Treasury still holds, and repay loans with it
    for g in range(lay.G):
        s = min(run['T'], run[f'lF_{g}'])
        run.do(f'Treasury spends to {g}', s); run.repay(g, s)
    return run


def gov_group(lay, x0, cap):
    """Government as a group: E_B, V_g, V_G fixed; household floors at every
    step; the reserve cap R <= R0 checked at the end only."""
    run = Run(lay, x0, True)
    c = {g: lay.V(g) @ x0 - lay.money(g) @ x0 + sum(x0[lay.i[f'l{h}_{g}']] for h in lay.holders) for g in range(lay.G)}
    L = {g: sum(x0[lay.i[f'l{h}_{g}']] for h in lay.holders) for g in range(lay.G)}
    run.everything_to_central_bank()
    for g in range(lay.G): run.repay(g, min(L[g], c[g]))
    if cap:
        R0 = x0[lay.i['R']]
        for g in range(lay.G):
            run.do(f'central bank sells loan on {g} to bank', min(run[f'lF_{g}'], max(0.0, run['R'] - R0)))
        run.do('central bank sells bond to bank', min(run['bF'], max(0.0, run['R'] - R0)))
        run.ok = run.ok and run['R'] <= R0 + 1e-7
    return run


def main(instances=500, seed=13):
    rng = random.Random(seed)
    fx = lambda spec: (lambda l, x: toy.fixed_rows(l, spec, x))
    gfx = lambda l, x: gg.rows(l, x)[0]
    checks = {
        'case 2 (payouts)': (lambda l, x: case3(l, x, payouts=True), lambda l, x: toy.static_min(l, 'M EF', False, x), lambda l: l.D(), fx('EF')),
        'case 3': (case3, lambda l, x: toy.static_min(l, 'M EF EB', False, x), lambda l: l.D(), fx('EF EB')),
        'case 4 (transfers)': (case4, lambda l, x: toy.static_min(l, 'M EF EB V', False, x), lambda l: l.D(), fx('EF EB V')),
        'case 5': (case5, lambda l, x: toy.static_min(l, 'M EF EB Vg', True, x), lambda l: l.D(), fx('EF EB Vg')),
        'government as group, uncapped': (lambda l, x: gov_group(l, x, False), lambda l, x: gg.static(l, x, False), gg.objective, gfx),
        'government as group, capped at end': (lambda l, x: gov_group(l, x, True), lambda l, x: gg.static(l, x, True), gg.objective, gfx),
    }
    for name, (history, static, obj, fixed) in checks.items():
        invalid = above = moved = 0
        for _ in range(instances):
            lay = toy.Layout(rng.choice([1, 2])); x0 = toy.opening(lay, rng)
            run = history(lay, x0); s = static(lay, x0)
            invalid += not run.ok
            above += obj(lay) @ run.x > s + 1e-6
            moved += any(abs(r @ run.x - r @ x0) > 1e-7 for r in fixed(lay, x0))
        print(f'{name:36s} invalid step: {invalid:3d}   fixed quantity moved: {moved:3d}   end above static minimum: {above:3d}')
    print(f'({instances} openings each, one or two household groups)')


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
