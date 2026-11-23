"""Netting on a network of claims with known or unknown amounts.

A *network* is a list of parties and a list of claims. Each claim is
(holder, issuer, is_debt, capacity), where capacity is a number or the name of
an unknown. Unknowns have bounds and may be tied by linear constraints (the
published totals). A *netting* cancels an amount x_e of each claim, between 0
and its capacity, so that no party's net position changes; claims a party
holds on itself cancel freely. Pairwise netting only cancels claims between
two parties against each other; multilateral netting may cancel around any
chain.

Two problems, over all values of the unknowns that satisfy the constraints:

  most_favourable   the most debt netting can cancel (one linear programme);
  least_favourable  the smallest debt amount netting is sure to cancel: the unknowns are
                    chosen to hurt netting, then netting does its best.

The second is min over unknowns of max over x. The inner maximum equals, by
linear-programming duality, min over potentials pi and slacks y >= 0 with
y_e >= w_e - (A' pi)_e of sum_e capacity_e * y_e, where A is the conservation
matrix (one row per party, or per pair of parties for pairwise netting) and
w_e is 1 for debt and 0 otherwise. A is totally unimodular, so integral pi is
optimal; y_e is then a small integer, written in binary, and each product
capacity_e * bit is linearised exactly. One mixed-integer programme.

Needs numpy and scipy.
"""
from itertools import combinations

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp


class Network:
    def __init__(self, parties):
        self.parties = list(parties)
        self.claims = []          # (holder, issuer, is_debt, capacity: float or str)
        self.unknowns = {}        # name -> (lo, hi)
        self.constraints = []     # (coeffs: {name: c}, lo, hi), constant terms folded into lo/hi

    def claim(self, holder, issuer, debt, capacity):
        assert holder in self.parties and issuer in self.parties, (holder, issuer)
        if isinstance(capacity, str):
            assert capacity in self.unknowns, capacity
        elif capacity <= 0:
            return
        self.claims.append((holder, issuer, bool(debt), capacity))

    def unknown(self, name, lo, hi):
        assert name not in self.unknowns and lo <= hi + 1e-9, (name, lo, hi)
        self.unknowns[name] = (lo, max(lo, hi))

    def constrain(self, coeffs, lo, hi):
        self.constraints.append((dict(coeffs), lo, hi))

    # ---- shared pieces -------------------------------------------------
    def _rows(self, pairwise):
        """Conservation matrix: party balances, or pair balances."""
        if pairwise:
            keys = list(combinations(sorted(self.parties), 2))
            idx = {k: i for i, k in enumerate(keys)}
            A = np.zeros((len(keys), len(self.claims)))
            for j, (h, i, _, _) in enumerate(self.claims):
                if h != i:
                    A[idx[tuple(sorted((h, i)))], j] = 1 if h < i else -1
            return A
        A = np.zeros((len(self.parties), len(self.claims)))
        for j, (h, i, _, _) in enumerate(self.claims):
            if h != i:
                A[self.parties.index(h), j] += 1
                A[self.parties.index(i), j] -= 1
        return A

    def _ub(self, c):
        return c if not isinstance(c, str) else self.unknowns[c][1]

    def debt_total_range(self):
        return sum(self._ub(c) for _, _, d, c in self.claims if d)

    # ---- problem 1 -----------------------------------------------------
    def most_favourable(self, pairwise=False):
        """Max debt cancelled over unknowns and cancellations. Returns (value, unknowns)."""
        U = list(self.unknowns); nu, nc = len(U), len(self.claims)
        n = nu + nc
        c = np.zeros(n)
        for j, cl in enumerate(self.claims):
            c[nu + j] = -1.0 if cl[2] else 0.0
        A_eq = np.hstack([np.zeros((0, nu)), np.zeros((0, nc))])
        rows = self._rows(pairwise)
        A_eq = np.hstack([np.zeros((rows.shape[0], nu)), rows]); b_eq = np.zeros(rows.shape[0])
        A_ub, b_ub = [], []
        for j, (_, _, _, cap) in enumerate(self.claims):          # x_e <= capacity
            r = np.zeros(n); r[nu + j] = 1
            if isinstance(cap, str):
                r[U.index(cap)] = -1; A_ub.append(r); b_ub.append(0.0)
            else:
                A_ub.append(r); b_ub.append(cap)
        for coeffs, lo, hi in self.constraints:
            r = np.zeros(n)
            for k, v in coeffs.items():
                r[U.index(k)] = v
            if hi is not None:
                A_ub.append(r); b_ub.append(hi)
            if lo is not None:
                A_ub.append(-r); b_ub.append(-lo)
        bounds = [self.unknowns[u] for u in U] + [(0, None)] * nc
        res = linprog(c, A_ub=np.array(A_ub) if A_ub else None, b_ub=b_ub or None,
                      A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
        assert res.status == 0, res.message
        return -res.fun, dict(zip(U, res.x[:nu]))

    # ---- problem 2 -----------------------------------------------------
    def least_favourable(self, pairwise=False, K=None):
        """Min over unknowns of the max debt cancelled.

        Returns (value, allocation, witnessed, attained): attained is the debt
        netting can cancel under the returned allocation, computed exactly with
        a linear programme. It is always a certified figure: the constraints
        allow that allocation, and under it netting cancels exactly this much.

        K bounds the potentials. The default, the number of parties, is always
        enough. A smaller K is faster and gives a value no larger than the exact
        one; the allocation it returns is then checked with most_favourable on
        the fixed allocation (witnessed=True when they agree), which proves that
        the published totals allow an allocation under which netting cancels
        no more than this value."""
        U = list(self.unknowns); nu, nc = len(U), len(self.claims)
        A = self._rows(pairwise); m = A.shape[0]
        if K is None:
            K = len(self.parties) if not pairwise else 1       # potential range, always enough
        L = 2 * K + 2                                          # slack values 0..L-1
        # variables: unknowns u (nu) | potentials pi (m) | one-hot delta (nc*L) | split capacity c (nc*L)
        o_pi, o_d = nu, nu + m
        o_c = o_d + nc * L
        n = o_c + nc * L
        cost = np.zeros(n); lo = np.zeros(n); hi = np.zeros(n); integ = np.zeros(n)
        for k, u in enumerate(U):
            lo[k], hi[k] = self.unknowns[u]
        lo[o_pi:o_d] = -K; hi[o_pi:o_d] = K; integ[o_pi:o_d] = 1
        hi[o_d:o_c] = 1; integ[o_d:o_c] = 1
        rows, rlo, rhi = [], [], []
        def add(r, a, b):
            rows.append(r); rlo.append(a); rhi.append(b)
        for j, (_, _, debt, cap) in enumerate(self.claims):
            Ub = self._ub(cap)
            d = [o_d + j * L + k for k in range(L)]; c = [o_c + j * L + k for k in range(L)]
            r = np.zeros(n); r[d] = 1; add(r, 1, 1)                              # one slack value
            r = np.zeros(n); r[d] = np.arange(L); r[o_pi:o_d] = A[:, j]          # y_e >= w_e - (A' pi)_e
            add(r, 1.0 if debt else 0.0, np.inf)
            r = np.zeros(n); r[c] = 1                                            # capacity split over values
            if isinstance(cap, str):
                r[U.index(cap)] = -1; add(r, 0, 0)
            else:
                add(r, cap, cap)
            for k in range(L):
                hi[c[k]] = Ub; cost[c[k]] = k
                r = np.zeros(n); r[c[k]] = 1; r[d[k]] = -Ub; add(r, -np.inf, 0)  # c_k <= U delta_k
        for coeffs, a, b in self.constraints:
            r = np.zeros(n)
            for k, v in coeffs.items():
                r[U.index(k)] = v
            add(r, -np.inf if a is None else a, np.inf if b is None else b)
        res = milp(cost, constraints=LinearConstraint(np.array(rows), rlo, rhi),
                   integrality=integ, bounds=Bounds(lo, hi), options=dict(mip_rel_gap=1e-9))
        assert res.status == 0, res.message
        alloc = {k: min(max(v, self.unknowns[k][0]), self.unknowns[k][1]) for k, v in zip(U, res.x[:nu])}   # solver noise
        attained = self.cancelled_given(alloc, pairwise)
        return res.fun, alloc, abs(attained - res.fun) < 1e-6 * max(1.0, abs(res.fun)), attained

    def cancelled_given(self, alloc, pairwise=False):
        """Max debt cancelled with every unknown fixed at alloc (a linear programme)."""
        F = Network(self.parties)
        for k, v in alloc.items():
            v = min(max(v, self.unknowns[k][0]), self.unknowns[k][1])
            F.unknown(k, max(0.0, v), max(0.0, v))
        F.claims = list(self.claims)
        return F.most_favourable(pairwise)[0]


def self_test():
    """Small networks with known answers for both problems."""
    out = []
    # 1. three-party loop, all known: 8 cancelled (two debt arcs of a 4-cycle... see values)
    N = Network('dbr'); N.claim('b', 'd', 1, 10); N.claim('d', 'r', 1, 7); N.claim('r', 'b', 0, 4)
    out.append(('loop, multilateral', N.most_favourable()[0], 8)); out.append(('loop, least', N.least_favourable()[0], 8))
    out.append(('loop, pairwise', N.most_favourable(pairwise=True)[0], 0))
    # 2. a pair
    N = Network('dr'); N.claim('d', 'r', 1, 3); N.claim('r', 'd', 1, 5)
    out.append(('pair', N.most_favourable(pairwise=True)[0], 6)); out.append(('pair, least', N.least_favourable(pairwise=True)[0], 6))
    # 3. the allocation decides whether a loop exists: g owes 10 to x, holder of x is b or q (unknown split);
    #    q owes g 10 (known); b owes nothing to g. Debt to q can cancel against q's debt to g.
    N = Network(['g', 'q', 'b']); N.unknown('to_b', 0, 10); N.unknown('to_q', 0, 10)
    N.constrain({'to_b': 1, 'to_q': 1}, 10, 10)
    N.claim('b', 'g', 1, 'to_b'); N.claim('q', 'g', 1, 'to_q'); N.claim('g', 'q', 1, 10)
    out.append(('allocation, most', N.most_favourable()[0], 20))     # all held by q: pair cancels 10+10
    out.append(('allocation, least', N.least_favourable()[0], 0))    # all held by b: nothing cancels
    # 4. a self-claim cancels freely; least favourable makes it as small as allowed
    N = Network(['g', 'b']); N.unknown('self', 2, 6); N.claim('g', 'g', 1, 'self')
    out.append(('self, most', N.most_favourable()[0], 6)); out.append(('self, least', N.least_favourable()[0], 2))
    for name, got, want in out:
        assert abs(got - want) < 1e-6, (name, got, want)
    print(f'self-test: {len(out)} cases, all correct')


if __name__ == '__main__':
    self_test()
