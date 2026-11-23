"""Static readings of the proved kernels: models with currency, a central
bank and Treasury regimes.

For each kernel, proved for a menu of transactions, a static linear programme
over balance sheets of that model, with the quantities the menu preserves
fixed and its one-way quantities bounded on one side, is compared with the
kernel's closed form on random openings. Where they agree, the least debt
reachable by the transactions equals the static minimum for that model.

Notation (paper): E_B = V_B, E_F = V_F, T = R_T, R = R_B, T - B = V_T when the
Treasury holds no loans. Treasury regimes: R1, R2 may tax and spend; R3 may
not spend; R4 may neither tax nor spend; R5 is fixed.

Model (no loans held by the public, L_H = 0): public deposits M and currency C_H;
bank vault currency C_B; bonds held by public, banks, Fed (B_H, B_B, B_F);
bank- and Fed-held loans (L_B, L_F); reserves R; Treasury account T; bank
equity E_B >= 0; Fed equity E_F (free); Fed miscellaneous assets X_F and
liabilities Q_F; Fed advances to banks U.
  bank:  B_B + L_B + R + C_B = M + U + E_B
  Fed:   B_F + L_F + X_F + U = R + T + C_H + C_B + Q_F + E_F
  D = B_H + B_B + B_F + L_B + L_F
Run: python3 -I landscape_s9_s15.py [instances] [seed]
"""
import random, sys
import numpy as np
from scipy.optimize import linprog

N = ['M', 'CH', 'CB', 'BH', 'BB', 'BF', 'LB', 'LF', 'R', 'T', 'EB', 'EF', 'XF', 'QF', 'U']
I = {n: k for k, n in enumerate(N)}


def row(**kw):
    v = np.zeros(len(N))
    for k, x in kw.items(): v[I[k]] += x
    return v


BANK = row(BB=1, LB=1, R=1, CB=1, M=-1, U=-1, EB=-1)
FED = row(BF=1, LF=1, XF=1, U=1, R=-1, T=-1, CH=-1, CB=-1, QF=-1, EF=-1)
D = row(BH=1, BB=1, BF=1, LB=1, LF=1)
MONEY = row(M=1, CH=1)
B = row(BH=1, BB=1, BF=1)
WT = row(T=1) - B


def opening(rng):
    while True:
        x = np.zeros(len(N))
        for n in N:
            if n in ('EB', 'EF'): continue
            x[I[n]] = rng.choice([0, 0, rng.randint(1, 40)])
        x[I['EF']] = FED @ x          # close the Fed with its equity
        x[I['EB']] = BANK @ x         # close the bank with its equity
        if x[I['EB']] >= 0 and D @ x > 0: return x


def static(x0, eq, ge=(), le=(), floor=MONEY):
    A_eq = [BANK, FED] + list(eq); b_eq = [0, 0] + [r @ x0 for r in eq]
    A_ub = [-floor] + [-r for r in ge] + list(le)
    b_ub = [-(floor @ x0)] + [-(r @ x0) for r in ge] + [r @ x0 for r in le]
    bounds = [(None, None) if n == 'EF' else (0, None) for n in N]
    r = linprog(D, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    assert r.status == 0, r.message
    return r.fun


def main(instances=2000, seed=1):
    rng = random.Random(seed)
    pos = lambda v: max(0.0, v)
    EF_, XF_, QF_ = row(EF=1), row(XF=1), row(QF=1)
    fed_fixed = [EF_, XF_, QF_]
    cases = {
        # name: (static constraints, closed form)
        'cash-free; central-bank equity fixed':
            (lambda x: dict(eq=fed_fixed), lambda x, e, m, h: pos(m + e)),
        'money = deposits + currency':
            (lambda x: dict(eq=fed_fixed), lambda x, e, m, h: pos(m + e)),
        'money = deposits only':
            (lambda x: dict(eq=fed_fixed, floor=row(M=1)), lambda x, e, m, h: pos(x[I['M']] + e)),
        'cash-free; bank equity also fixed':
            (lambda x: dict(eq=fed_fixed + [row(EB=1)]), lambda x, e, m, h: pos(m + x[I['EB']] + e)),
        'Treasury R1/R2 (e fixed)':
            (lambda x: dict(eq=fed_fixed), lambda x, e, m, h: pos(m + e)),
        'Treasury R3 (e fixed; T - B can only rise; B only falls)':
            (lambda x: dict(eq=fed_fixed, ge=[WT], le=[B]),
             lambda x, e, m, h: max(0.0, m + e + pos(x[I['T']] - B @ x))),
        'Treasury R4 (e, T - B fixed; B only falls)':
            (lambda x: dict(eq=fed_fixed + [WT], le=[B]),
             lambda x, e, m, h: pos(B @ x - x[I['T']]) + pos(x[I['LB']] + x[I['LF']] - h)),
        'Treasury R5 (e, B and T fixed)':
            (lambda x: dict(eq=fed_fixed + [B, row(T=1)]),
             lambda x, e, m, h: B @ x + pos(x[I['LB']] + x[I['LF']] - h)),
    }
    print(f'{instances} random openings per model')
    for name, (cons, formula) in cases.items():
        bad = 0
        for _ in range(instances):
            x0 = opening(rng)
            e = x0[I['EF']] + x0[I['QF']] - x0[I['XF']]
            m = MONEY @ x0; h = x0[I['BH']] + x0[I['EB']]
            if name.startswith('cash-free'):   # cash-free special cases
                x0[I['CH']] = 0; x0[I['CB']] = 0; x0[I['XF']] = 0; x0[I['QF']] = 0; x0[I['U']] = 0; x0[I['LF']] = 0
                x0[I['EF']] = FED @ x0 + x0[I['EF']]; x0[I['EB']] = BANK @ x0 + x0[I['EB']]
                if x0[I['EB']] < 0: continue
                e = x0[I['EF']]; m = MONEY @ x0; h = x0[I['BH']] + x0[I['EB']]
            s = static(x0, **cons(x0))
            bad += abs(s - formula(x0, e, m, h)) > 1e-6
        print(f'  {name:55s} static != closed form: {bad}')


if __name__ == '__main__':
    main(*(int(a) for a in sys.argv[1:]))
