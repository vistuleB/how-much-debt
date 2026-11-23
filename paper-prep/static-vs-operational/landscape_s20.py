"""Static reading of the kernel of the bank-positions model.

The bank-positions model adds to the models of landscape_s9_s15.py bank
nondeposit funding, other claims (J), non-debt assets and locked positions.
A static linear programme over its balance sheets, with the quantities its
experiment conserves fixed and its one-way quantities bounded, is compared
with the kernel's closed form (central-bank advances fixed) on random
openings, for Treasury regimes R1-R5 (see landscape_s9_s15.py).
Run: python3 -I landscape_s20.py [instances] [seed]
"""
import random, sys
import numpy as np
from scipy.optimize import linprog

N = ['M', 'CH', 'CB', 'BH', 'BB', 'BF', 'LH', 'LB', 'LF', 'R', 'T', 'EB', 'EF', 'U',
     'NB', 'JB', 'XBres', 'QBH', 'QBres', 'NH', 'NF', 'JH', 'JF', 'XFres', 'QH', 'QG', 'Qlock']
I = {n: k for k, n in enumerate(N)}


def row(**kw):
    v = np.zeros(len(N))
    for k, x in kw.items(): v[I[k]] += x
    return v


BANK = row(BB=1, LB=1, R=1, CB=1, NB=1, JB=1, XBres=1, M=-1, EB=-1, U=-1, QBH=-1, QBres=-1)
FED = row(BF=1, LF=1, U=1, NF=1, JF=1, XFres=1, R=-1, T=-1, CH=-1, CB=-1, QH=-1, QG=-1, Qlock=-1, EF=-1)
D = row(BH=1, BB=1, BF=1, LH=1, LB=1, LF=1)
P = row(M=1, CH=1)
B = row(BH=1, BB=1, BF=1)
L = row(LH=1, LB=1, LF=1)
W = row(T=1, QG=1)


def opening(rng):
    while True:
        x = np.zeros(len(N))
        for n in N:
            if n in ('EB', 'EF'): continue
            x[I[n]] = rng.choice([0, 0, 0, rng.randint(1, 40)])
        x[I['EF']] = FED @ x
        x[I['EB']] = BANK @ x
        if x[I['EB']] >= 0 and D @ x > 0: return x


def static(x0, regime):
    eq = [row(EF=1), row(U=1), row(XBres=1), row(QBres=1), row(XFres=1), row(Qlock=1),
          row(NH=1, NB=1, NF=1), row(JH=1, JB=1, JF=1)]
    le = [L]                       # no new lending
    ge = [P, row(NH=1)]            # money and public non-debt floors
    if regime == 3: ge.append(W - B)
    if regime == 4: eq.append(W - B); le.append(B)
    if regime == 5: eq += [W, B]
    if regime in (2, 3, 4): le.append(B)  # no issuance
    A_eq = [BANK, FED] + eq; b_eq = [0, 0] + [r @ x0 for r in eq]
    A_ub = [-r for r in ge] + le; b_ub = [-(r @ x0) for r in ge] + [r @ x0 for r in le]
    bounds = [(None, None) if n == 'EF' else (0, None) for n in N]
    r = linprog(D, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    assert r.status == 0, r.message
    return r.fun


def closed_form(x0, regime):
    g = lambda n: x0[I[n]]
    pos = lambda v: max(0.0, v)
    m = P @ x0; Wv = W @ x0; Bv = B @ x0; Lv = L @ x0
    z = g('XBres') - g('QBres')
    h = g('BH') + g('LH') + g('EB') + g('JH') + g('QH') + g('QBH')
    e = g('EF') + g('Qlock') + g('QBres') - g('XFres') - g('NF') - g('JF') - (g('NB') + g('JB') + g('XBres')) - g('JH')
    # e = E_F + Q_lock + Q_B^res - X_F - X_B - J_H, with X_F = N_F + J_F + X_F^res
    sigma = pos(z - g('U') - m)
    if regime in (1, 2): return pos(m + e + sigma)
    if regime == 3: return pos(m + e + sigma + pos(Wv - Bv))
    if regime == 4: return pos(Bv - Wv) + pos(Lv - h + sigma)
    return Bv + pos(Lv - h + sigma)


def main(instances=1500, seed=3):
    rng = random.Random(seed)
    print(f'{instances} random openings, fixed advances')
    for regime in (1, 2, 3, 4, 5):
        bad = 0
        for _ in range(instances):
            x0 = opening(rng)
            bad += abs(static(x0, regime) - closed_form(x0, regime)) > 1e-6
        print(f'  R{regime}: static != closed form: {bad}')


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
