"""Static readings of the three-operation kernel under central-bank regimes
F2 and F3.

Two-group toy of toy.py. Static programme: per-group money floors; bank
equity, each group's net position, total bonds, Treasury account and the
central bank's bonds and equity fixed (so its loans minus reserves is fixed);
under F2 its loans may only fall, under F3 they are fixed. Compared with
the closed forms of the three-operation kernel. The F2 run is repeated without the
one-way bound to show it is needed.
Run from this directory: python3 landscape_s22_f2.py [instances] [seed]
"""
import random, sys
sys.path.insert(0, '.')
import toy
from scipy.optimize import linprog


def static(lay, x0, profile, one_way=True):
    i = lay.i
    fixed = [lay.single('EB'), lay.bonds(), lay.single('T'), lay.single('bF'), lay.single('EF')] + \
            [lay.V(g) for g in range(lay.G)]
    if profile == 'F3': fixed += [lay.single(f'lF_{g}') for g in range(lay.G)]
    A_eq = [lay.bank_balance(), lay.fed_balance()] + fixed; b_eq = [0, 0] + [r @ x0 for r in fixed]
    A_ub = [-lay.money(g) for g in range(lay.G)]; b_ub = [-(lay.money(g) @ x0) for g in range(lay.G)]
    if profile == 'F2' and one_way:
        for g in range(lay.G): A_ub.append(lay.single(f'lF_{g}')); b_ub.append(x0[i[f'lF_{g}']])
    return linprog(lay.D(), A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                   bounds=toy.bounds_state(lay), method='highs').fun


def closed_form(lay, x0, profile):
    i = lay.i; K3 = lay.bonds() @ x0; G = 0.0
    for g in range(lay.G):
        L = sum(x0[i[f'l{h}_{g}']] for h in lay.holders); f = x0[i[f'lF_{g}']]
        c = x0[i[f'b{g}']] + sum(x0[i[f'l{g}_{y}']] for y in range(lay.G)); H = L - f
        K3 += max(f, L - c); G += min(f, max(0.0, c - H))
    return K3 if profile == 'F3' else K3 - min(x0[i['R']], G)


def main(instances=600, seed=4):
    for profile, one_way in (('F3', True), ('F2', True), ('F2', False)):
        rng = random.Random(seed); bad = 0
        for _ in range(instances):
            lay = toy.Layout(2); x0 = toy.opening(lay, rng)
            bad += abs(static(lay, x0, profile, one_way) - closed_form(lay, x0, profile)) > 1e-6
        label = profile + ('' if one_way else ' without the one-way bound')
        print(f'{label:34s} static != closed form: {bad} of {instances}')


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
