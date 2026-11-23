# The instrument-split model: specification

The model behind `corrected_build.py`, `corrected_check.py` and
`corrected-results.json`, which give the paper's Table 2 for 2008 and 2020–2025 and, through
the annual extensions, for the other years. It refines an earlier model in which
all other financial claims (the J book) sat outside debt.

## What changed

The old J book remains as an asset inventory. Within each holder/borrower cell:

- `a_hg` identifies additional selected nonbank loans already carried in J;
- `z_hg` identifies selected nonbank debt securities;
- `j_hg - a_hg - z_hg` is excluded from selected debt, but retains the old
  financial-acquisition permissions.

Federal loans are `s_d, s_r`. Treasury-held securities are `j_td, j_tr` with
corresponding `z_td, z_tr`. Debt includes these independently of holder:

\[
D=B+\sum_g L_g+\sum_g s_g+\sum_{h,g}(a_{hg}+z_{hg}).
\]

Treasury net position is T + q_G + S + J_T − B. Repayment of a Treasury-held
claim reduces the borrower's deposits and reserves, reduces that claim and
raises T. Moving a bank-held loan onto the Treasury's books changes its holder,
not D. The test suite checks that accounting reclassification; acquisition is
not an extra permission in the reduction menu.

The four configurations are separate versus pooled nonbank money floors, crossed
with securities repayable versus securities not repayable. **Securities that
are not repayable can still be sold**; their issuers cannot extinguish them.
Loans, including the Fed's nonbank n.e.c. loans, remain repayable in both profiles.

## Exact operation menu

F1 financial conversions, fixed advances, domestic bank payout, repayment of
nonbank funding of banks, and R4 Treasury redemption. Banks can purchase nonbank-held
bonds/loans, then transfer them to the Fed. Nonbank- and bank-held financial J holdings can
be acquired by the Fed. Eligible bank non-debt holdings N_B can also be acquired
by the Fed, as in the earlier bank-positions model; nonbank non-debt assets are
protected. Existing nonbank claims on the Fed and Treasury claims on the Fed can
settle. Borrowers repay Fed-held loans and eligible selected claims, or pay the
Treasury on its loans/securities. Securities repayment is subject to the chosen
profile. Pooled profiles additionally allow money transfers between the nonbank sectors.

No new lending, issuance, Treasury spending, taxes, asset revaluation or free
cross-border equity injection. Locked holdings remain locked. This is one named
experiment, not an implementation of all R/F/X menus or timed contracts.

## Receipt, collection and reserve certificate

For each nonbank sector g define from the opening:

- c_g: proceeds of selling its bonds, loans and J holdings, plus repayment of
  its bank funding, settlement of its Fed claims and its bank-equity payout;
- o_g: all its **repayable** selected obligations (excluding securities that are not repayable);
- s*_g: the repayable part owed specifically to the Treasury.

For separate floors let q_g=min(c_g,o_g), Q_0=Σq_g and
H_0=Σmin(s*_g,q_g). For pooled floors let Q_0=min(Σc_g,Σo_g) and
H_0=min(Σs*_g,Q_0).

Let ρ be the reserves available after the complete preparation:

\[
\rho=R+N_B+B_B+\sum_g B_g+\sum_g q_{Hg}
 +\sum_{h\in\{B,D,R\},g}L_{hg}
 +\sum_{h\in\{B,D,R\},g}J_{hg}.
\]

Here q_Hg are nonbank claims on the Fed, not bank funding. Currency is fixed and
cannot be turned into extra payment liquidity in this experiment. Set

\[
Q=\min(Q_0,\rho),\qquad H=\min(H_0,Q),\qquad
Z=\min(B,T+q_G+H).
\]

The minimum selected debt for this operation menu is

\[
\boxed{K=D-Q-Z.}
\]

This is deliberately written as debt removed, with **funded Treasury collections**.
It avoids assuming all Treasury assets can be collected irrespective of borrowers.
All quantities are nonnegative; the construction proves K is nonnegative.

### Lower bound

Nonbank receipts are bounded by c_g: the menu cannot create or replenish the
saleable assets, bank equity or bank/Fed obligations being collected. Each such
stock can supply money at most once net. Separate floors therefore cap total
repayment by Σmin(c_g,o_g); pooling gives the corresponding aggregate cap.
Reserves can increase only from the preparation stocks listed in ρ and fall by
one unit for every payment of selected nonbank debt. Thus repayment is at most Q.

Treasury collections are at most H_0 by the same group budgets, and cannot exceed
total repayment Q. Without taxes, issuance or spending, Treasury redemption is
therefore at most min(B,T+q_G+H). Selected nonbank-debt repayment and Treasury
redemption are the only debt-reducing operations, establishing D′≥D−Q−Z.

### Funded attainment

Buy all nonbank-held bonds/loans and transferable nonbank-held J, settle nonbank claims on
banks and the Fed and distribute bank equity. Move eligible bank non-debt assets and all
bank-held bonds/loans/J to the Fed. This preparation never decreases nonbank
money or reserves, leaves both institutional equities consistent, and realizes
all receipts c_g and reserves ρ. Settle q_G into T.

Pay Treasury-held obligations **across both groups first**, to the maximum H,
then other repayable obligations until total repayment Q. Under separate floors,
the group capacities q_g permit these allocations: prioritize min(s*_g,q_g),
then use each remaining quota for other obligations. If the common reserve cap
binds, stop at Q; choosing Treasury payments first realizes min(H_0,Q).
Under pooling, transfers allocate the combined receipts first to Treasury debts,
then the remaining obligations. No payment exceeds current receipts, inventory
or reserves. Treasury collects H, then redeems Z bonds held by the Fed. This
last operation uses T and does not consume bank reserves. Endpoint debt is K.

The net-position checks refer to the selected accounting scope; they are not full household net worth including locked pensions or physical assets.

The argument applies to the stated menu,
not automatically to broader permissions, protected instruments or contract flags.

### Why an earlier, simpler formula fails

Take B_F=5, E_F=5, Treasury loans to D of 10, and every other position zero.
Both institutional sheets balance. Nobody has sale proceeds, so no repayment or
redemption is possible: minimum D is 15. The earlier expression
[B−T−q_G−S]_+ + Σ[obligations−receipts]_+ gives 10. It implicitly spends loan
collections that never occur. Such a formula can still match the empirical
openings without being a general theorem.

## Source decisions and remaining empirical qualifications

1. **Bank-issued securities.** The inherited completion places bank debt-security
   funding in nonbank bank-funding accounts. This leaves institutional CP and
   corporate-bond holdings allocated to nonbank issuers. We retain that explicit
   completion, rather than claim it is observed. Shifting bank-issued holdings
   into banks would require a matching change to nonbank funding and nonbank
   securities; independently subtracting bank issuance twice is wrong.
2. **Fed foreign securities.** Classified as foreign nonbank sovereign debt.
   The New York Fed's 2025 SOMA report describes foreign-currency outright
   investments in Dutch, French, German and Japanese government securities.
   Extending that sovereign classification to all retained dates is recorded as
   a completion, not inferred from a generic foreign-bond label alone.
   Nonbank-held foreign bonds receive two separate issuer completions: all
   nonbank versus all bank issuers. Their financial holdings and acquisition
   rights stay unchanged; only selected debt/repayment eligibility changes.
   Both are endpoints of a classification sensitivity, not two observed
   economies. In the repayable profiles their attained minima coincide for
   every retained opening; opening debt and the minima with
   securities not repayable differ.
3. **Direct-investment intercompany debt.** The main run selects the debt-security
   and loan instruments of L.208/L.214; the separately published L.223 signed net
   series is retained in excluded inventory. This does **not** establish that
   gross intercompany lending is zero or that all economically describable debt
   has been captured. Including that instrument would need gross data,
   not max(0, net); the net series is −$4.414B in 2025.
4. **Federal loans.** All domestic except observed FL263169203 foreign borrowers;
   the three asset components (other loans, mortgages, student credit) close
   exactly to total federal loans. Their residual borrower allocation remains
   conditional. Fed n.e.c. loans have four observed domestic nonbank borrower
   components; they are loans and are repayable even when securities are not.
5. **Treasury-held securities.** Add the normalized agency issuer layer already
   retained in the shared source record, plus corporate/foreign securities.
   The latter use the inherited foreign-issuer assignment. No second copy of
   underlying agency mortgage principal is introduced. Both agency representations
   remain distinct, including the legal security layer when retained.
6. **2024 signed repo.** The raw Fed repo asset is −$1M. Gross that signed
   contra-position into the existing locked Fed liability: J_F, X_F and Q_lock
   each rise by $1M. Equity and selected debt are unchanged. Every affected record
   names this source adjustment; it is not an unexplained balancing plug.

The range across inherited completions is zero for each year/representation/
repayment/floor/foreign-issuer profile in this run. That does not bound the issuer-completion
and perimeter choices above, nor establish historical identification.

The key `security_outside_D` names a source representation inherited from the
earlier model: in this model its retained nonbank securities **are inside D**.
The key is kept for traceability; it does not define the debt perimeter.

## Verification

`corrected_build.py` generates complete openings, transaction streams, endpoints,
certificates and source-adjustment records. `corrected_check.py` imports no
project code: it reconstructs source assignments from the pinned archive,
recomputes certificates independently, and replays every atomic vector while
checking balances, inventory, selected net positions, money floors and endpoint debt.
Eight deliberate corruptions are rejected.

Source interpretation note: the $1.368T/$4.285T/$16.855T 2025 CP/municipal/
corporate figures in the inventory are additive **control contributions before
signed subtractions**, not the final amounts held by the nonbank sectors. The JSON keeps
those netting terms explicitly.

```sh
python3 broad-debt-model/corrected_build.py --check
python3 -I broad-debt-model/corrected_check.py --self-test
```

Sources: the pinned March 19, 2026 Z.1 archive and dictionaries, especially
L.109/L.110/L.106/L.202/L.208/L.214/L.216/L.223; the source positions shared with the earlier model;
[New York Fed SOMA report 2025](https://www.newyorkfed.org/medialibrary/media/markets/omo/omo2025-pdf.pdf);
[Financial Accounts instrument descriptions](https://www.federalreserve.gov/releases/z1/preview/html/table_desc_instruments.htm).
