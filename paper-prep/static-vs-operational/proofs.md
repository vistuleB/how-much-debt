# Proofs: static minima and their attainment

Companion to `README.md`. Proves the closed forms of
the nested cases and of the government-as-a-group results, and gives for
each an explicit history that attains it. `paths.py` executes every history
on random openings and checks each step.

## Setting

The cash-free toy model of `toy.py`. Public groups g; one consolidated bank; a
central bank (CB); a Treasury. For group g: deposits m_g, claims held h_g
(bonds plus loans on any group), loans owed o_g, net position
V_g = m_g + h_g − o_g. Bank: claims C_B (loans, bonds), reserves R_B; deposits
M = Σ m_g, equity V_B. Central bank: claims C_F (bonds, loans); reserves R_B,
Treasury account R_T, equity V_F. Treasury: account R_T, bonds B outstanding,
net position V_T = R_T − B. Public claims in total: H = Σ h_g. Debt
D = B + L = H + C_B + C_F.

**Admissible state:** both balance sheets hold (C_B + R_B = M + V_B,
C_F = R_B + R_T + V_F); every holding, R_B, R_T and V_B is non-negative; V_F has
either sign. **Policy:** fixed quantities are conditions on the end state;
each group's money (or total money, in the pooled cases) is a floor at every
step. [x]₊ = max(x, 0).

## Two lemmas

**Lemma 1 (identity).** In every admissible state,
D = M + R_T + V_B + V_F + H.

*Proof.* D = H + C_B + C_F; substitute C_B = M + V_B − R_B and
C_F = R_B + R_T + V_F. ∎

**Lemma 2 (group bound).** In every admissible state with m_g ≥ m_g⁰,
o_g ≥ [m_g⁰ − V_g]₊, and m_g + h_g ≥ max(m_g⁰, V_g).

*Proof.* o_g = m_g + h_g − V_g ≥ m_g⁰ − V_g, and o_g ≥ 0. Likewise
m_g + h_g = V_g + o_g ≥ V_g, and m_g + h_g ≥ m_g ≥ m_g⁰. ∎

Sector net positions sum to zero: Σ V_g + V_B + V_F + V_T = 0.

## A. Static minima

Superscript 0 denotes opening values; V = Σ V_g, M⁰ = Σ m_g⁰.

| Case | Fixed at the end | Least D |
|---|---|---|
| 1 | M ≥ M⁰ | 0 |
| 2 | M ≥ M⁰, V_F | [M⁰ + V_F]₊ |
| 3 | M ≥ M⁰, V_F, V_B | [M⁰ + V_F + V_B]₊ |
| 4 | M ≥ M⁰, V_F, V_B, V | [M⁰ − V]₊ + [−V_T]₊ |
| 5 | each m_g ≥ m_g⁰, V_F, V_B, each V_g | Σ_g [m_g⁰ − V_g]₊ + [−V_T]₊ |

In cases 4 and 5, V_T is fixed by the sum rule, so −V_T = B⁰ − R_T⁰ is the
Treasury's net debt.

*Lower bounds.* By Lemma 1, with H, R_T, V_B ≥ 0 and M ≥ M⁰: D ≥ M⁰ + V_F in
case 2 and D ≥ M⁰ + V_F + V_B in case 3; D ≥ 0 always. In case 5, Lemma 2
gives M + H ≥ Σ max(m_g⁰, V_g), and R_T = V_T + B ≥ V_T with R_T ≥ 0 gives
R_T ≥ [V_T]₊; so D ≥ Σ max(m_g⁰, V_g) + [V_T]₊ + V_B + V_F. Using the sum rule
this equals Σ [m_g⁰ − V_g]₊ + [−V_T]₊. Case 4 is case 5 with one pooled
group (Lemma 2 applied to the sum).

*Attainment by an admissible end state.* Case 1: m = M⁰, R_B = M⁰, V_F = −M⁰,
everything else zero. Cases 2–3 (V_B = 0 in case 2): H = 0, R_T = 0; if the
bound is positive take M = M⁰ and R_B = max(0, −V_F), which lies in
[0, M⁰ + V_B] because the bound is non-negative; if it is zero take
M = −V_F − V_B ≥ M⁰ and R_B = −V_F. The bank and the central bank then hold
claims C_B = M + V_B − R_B ≥ 0 and C_F = R_B + R_T + V_F ≥ 0, any mix of bonds and
loans. Case 5: h_g = 0, m_g = max(m_g⁰, V_g), o_g = [m_g⁰ − V_g]₊,
R_T = [V_T]₊, B = [−V_T]₊; split the claims between bank and central bank
with any R_B in [max(0, −R_T − V_F), M + V_B], an interval that is non-empty
because its endpoints differ by D ≥ 0. Every value matches the bound. ∎

The case-5 minimum reads: **the least debt is the Treasury's net debt plus
the amount by which each household group's money exceeds its net position.** This is the paper's Proposition 1 in this
setting, and the case-5 history below is its Proposition 2. Bank and
central-bank equity drop out once all net positions are fixed.

## B. Attainment by transactions

All histories begin with the same block, made of transactions in every menu
used below:

**Block P (everything to the central bank).** (a) The central bank buys all
bonds and loans the bank holds. (b) The bank buys all bonds and loans the
public holds, crediting the sellers. (c) The central bank buys those from
the bank.

*After P:* every claim is held by the central bank; the bank holds only
reserves, so R_B = M + V_B; each group has m_g = m_g⁰ + c_g, where c_g = h_g⁰
is its sale receipt. During P, money only rises and every purchase is
bounded by the seller's holding; no fixed quantity moves (purchases swap a
claim for money or reserves).

**Invariant after P.** Every later step is a Treasury redemption of a
central-bank bond with the Treasury account, a repayment of a central-bank
loan, a tax, a spending payment or a transfer. None gives the bank a claim,
so R_B = M + V_B ≥ 0 at every later step. The central bank's claims stay
non-negative because each redemption or repayment is bounded by what it
holds, and R_T stays non-negative because redemptions and spending are bounded
by R_T.

**Case 5.** After P: (d) the Treasury redeems min(R_T, B) of central-bank
bonds; (e) each group repays min(L_g, c_g) of its loans, all central-bank
held. Group g's money falls by at most c_g, so its floor holds; it ends at
m_g⁰ + [c_g − L_g]₊ = max(m_g⁰, V_g) with o_g = [L_g − c_g]₊ =
[m_g⁰ − V_g]₊, and R_T, B end at [V_T]₊, [−V_T]₊. No step moves V_F, V_B or
any V_g. The end state is the optimum of A.

**Case 4.** As case 5, with total repayment min(L, c) shared among
borrowers and transfers between groups placed before each repayment so the
borrower has the money. Transfers leave total money and total V unchanged.

**Case 3.** After P and (d): repay central-bank loans out of money above the
floor (with transfers); tax any money still above the floor; redeem bonds
with the proceeds; spend what remains in the Treasury account to the public
and have it repay central-bank loans with it. Money never falls below M⁰
(repayments and taxes use only the excess; spending precedes the repayment
it funds). The end state has H = 0 and either M = M⁰ and R_T = 0, giving
D = M⁰ + V_B + V_F, or no bonds and no loans left, giving D = 0.

**Case 2.** First the bank pays out all its equity to the public (money
rises), then the case-3 history with V_B = 0.

In every case the end state reaches the lower bound of A, so
operational and static minima coincide for these menus. ∎

**Case 1 (not attainable).** No transaction in the project changes V_F
(there is no cancellation, forgiveness or write-off). Every reachable state
therefore satisfies the case-2 constraints, and the case-2 history attains
their minimum: the operational minimum in case 1 is [M⁰ + V_F]₊, above the
static 0 whenever M⁰ + V_F > 0.

**One pass suffices.** Block P makes reserves equal deposits plus bank
equity for the rest of the history, so reserves never limit a tax or a
repayment. The alternating rounds found by the time-expanded programme in
`toy.py` were not needed; they appear only if the central bank does not buy
from the bank.

## C. The government as a group

Consolidate the Treasury and the central bank into G, with deposit −R_B,
term debt B_out (bonds held outside the central bank) and net position
V_G = V_T + V_F. Objective D_c = L + B_out. Fixed at the end: V_B, each V_g
with its floor at every step, and V_G.

(a) **Overdraft unlimited:** least D_c = Σ_g [m_g⁰ − V_g]₊.

(b) **Overdraft may not grow (R_B ≤ R_B⁰ at the end):** least
D_c = Σ_g [m_g⁰ − V_g]₊ + [−R_B⁰ − V_G]₊.

*Lower bounds.* Lemma 2 bounds each o_g. B_out ≥ 0 gives (a). For (b), G's
balance sheet gives B_out = (central-bank loans) − R_B − V_G ≥ −R_B⁰ − V_G.

*Attainment.* (a) Block P, then each group repays min(L_g, c_g) to the
central bank: B_out = 0 and o_g = [m_g⁰ − V_g]₊. (b) Continue: the central
bank sells loans to the bank, then bonds, until R_B = R_B⁰ (each sale lowers
reserves one for one). Selling loans leaves D_c unchanged; the bonds sold
amount to [−R_B⁰ − V_G]₊, because after the repayments R_B = M + V_B and
M + V_B − Σ o_g = −V_G. The central bank holds enough bonds:
the condition reduces to R_T⁰ + V_F⁰ + R_B⁰ ≥ 0, which is the central bank's
opening claims, non-negative. ∎

So with a floor on its deposit the government follows the household rule;
without one, its term debt can always be turned into overdraft.

## Checks

`python3 paths.py 500 13` executes each history above on 500 random
openings: no invalid step, no fixed quantity moved, and every end state at
the linear-programme minimum. The closed forms also match the linear
programmes in `toy.py` and `gov_as_group.py`.

## Scope

Cash-free; one bank; no non-deposit bank funding, non-debt assets or
revaluation; amounts divisible; transactions at recorded values. The
three-operation menu with the Treasury and central bank fixed is a
different menu, proved separately; `landscape_s22_f2.py` checks its closed
forms against static programmes.
