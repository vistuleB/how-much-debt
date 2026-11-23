# Glossary

The code and stored data use their own short names. This file maps them to
the terms of the paper, *How much debt does money need?* Each code term means
one thing; where the paper uses a different word for the same thing, both are
given.

## Paper terms and code terms

| Paper | Code and data | Notes |
|---|---|---|
| transaction-based debt kernel, or kernel, D_min | `kernel` (`kernels` for a list); `least` in the output of `series.py` and the scripts that use it, `split_min` for the household split | The least debt that ordinary transactions reach with the paper's protections (its Sections 1 and 2). The appendix's "least debt" with weaker protections is not always reached by transactions, so it is not called a kernel. |
| debt, D | `debt`, `opening_debt` | Treasury bonds plus every loan and debt security owed by the nonbank sectors. |
| nonbank sectors | `nonbank`; actor `DomesticNonbank`, `RestOfWorld` | Two sectors in the US runs: domestic (`d`) and rest of the world (`r`). |
| money of a sector | `m` (deposits) and `ch` (currency), e.g. `d_m`, `d_ch`; `nonbank_money` in totals | |
| net position of a sector, V_g | `net(v, g)` | Financial claims less financial debts. |
| bank equity, V_B | `eb` | Financial net position of the consolidated bank. |
| central-bank equity, V_F | `ef` | May be negative. |
| what a sector owes, o_g | `due` | In `certificate()`: the part it may repay (without nonbank securities when they are not repayable). |
| claims a sector can sell or collect, h_g | `receipts` | In `certificate()`. In `corrected_model.py` the domestic sector's receipts include the bank's equity payout (Table 2, column 9); in `equity_kept_model.py` and `bank_equity_kept.py`, the headline, they do not. |
| the value of Proposition 1 | `certificate` | The computed bound for one balance sheet and one set of permissions. |
| a sequence of transactions that reaches it (Proposition 2) | `witness`; in the corrected model the list `steps` (also `stream`) | Every stored witness is replayed by the checkers. |
| one transaction | `move` | Its type is its `kind` or `action`. |
| securities not repayable early | `securities_repayable = False`; "frozen repayment" | Applies to nonbank debt securities only; Treasury bonds can still be redeemed. |
| sectors pooled / separate | `pooled`, `separate` | |
| look-through representation | `agency_lookthrough` | Agency mortgage-backed securities replaced by the underlying mortgages. The alternative, `security_outside_D`, keeps them as securities outside debt. |
| completed balance sheet | one record of a stored run; its variant is named by its completion labels | 6 to 24 per year. |
| locked positions | `locked` | Positions that stay where they are. |
| shares (equity held as an instrument) | `shares_d`, `shares_r` | Not to be confused with `eb`, `ef`. |

## Output fields of the paper's scripts

USD trillions in the `--json` output of `series.py` and `bank_equity_kept.py`.

| Field | Meaning |
|---|---|
| `debt` | Debt, D (Table 2, column 2). |
| `netting` | Debt left by pairwise netting (column 3). |
| `separate` | The kernel, banks keep their equity, sectors protected separately (`bank_equity_kept.py`; column 4). |
| `tnd` | The Treasury's net debt, [−V_T]₊ (column 5). |
| `least` | In `series.py`: the kernel when banks pay out their equity to the domestic sector (column 9). |
| `least_with_payout` | The same in `bank_equity_kept.py`, which reproduces it. |
| `payout` | Bank equity, V_B: the amount the payout version pays to the domestic sector. |
| `pooled` | The kernel with the two sectors protected as one. |
| `frozen`, `separate_not_repayable` | The kernel when nonbank securities cannot be repaid early (column 8). `least_not_repayable_with_payout` and `pooled_not_repayable` are the payout and pooled versions. |
| `netting_not_repayable` | What netting leaves when it may not cancel nonbank securities. |
| `netting_ratio`, `netting_ratio_with_payout`, `netting_ratio_not_repayable` | What netting leaves divided by the matching kernel. |
| `gap_d`, `gap_r` | What the domestic sector (`d`) and the rest of the world (`r`) owe, less the claims they can sell or collect, with the payout included in the domestic sector's receipts. Positive means the sector owes more than it can raise. Stored in each run as `signed_debt_receipt_gap`. |
| `dom` | [`gap_d`]₊, the domestic term of Proposition 1 in the payout version. Column 6 is the same term with banks keeping their equity: column 4 minus column 5. |
| `n_sheets`, `spread_*` | The number of completed balance sheets in the year, and the spread of each figure across them (zero for the kernel). |

## Letters

Holders and issuers are single letters: `b` bank, `f` central bank (the
Federal Reserve), `t` Treasury, `d` domestic nonbank sector, `r` rest of the
world. A two-letter suffix is holder then borrower: `l_bd` is a loan held by
the bank and owed by the domestic sector.

## Coordinates of the broad-debt model

Amounts are in USD millions.

| Name | Meaning |
|---|---|
| `bb`, `bf` | Treasury bonds held by the bank, by the central bank |
| `d_b`, `r_b` | Treasury bonds held by a nonbank sector |
| `r` | reserves of the bank at the central bank (the paper's R_B) |
| `t` | the Treasury's account at the central bank (the paper's R_T) |
| `cb` | vault cash |
| `u` | central-bank advances to the bank |
| `l_hg` | loan held by `h`, owed by `g` |
| `s_g` | federal loans owed by sector `g` (mainly student loans) |
| `a_hg`, `z_hg` | additional loans and debt securities held by `h`, owed by `g`; with `l_hg` and `s_g` they make up the nonbank debt in D |
| `j_hg` | the financial-asset book: other claims held by `h` on `g`; only its `a` and `z` parts count as debt |
| `g_qbh` | sector `g`'s nondeposit claims on the bank (bank funding) |
| `g_qh` | sector `g`'s claims on the central bank other than currency (deposits, reverse repurchase agreements) |
| `g_n` | inherited non-debt holdings, kept fixed |
| `qg` | the Treasury's other claim on the central bank |
| `nb`, `nf` | non-debt assets of the bank, of the central bank |
| `xf` | central-bank assets outside bonds, loans and advances |
| `ql`, `xbr`, `qbr` | locked central-bank claims, locked bank assets, locked bank funding |

## Labels in the stored runs

| Label | Meaning |
|---|---|
| `representation` | `agency_lookthrough` or `security_outside_D`, see above |
| `nonbank_foreign_security_issuers` | whether the issuers of foreign debt securities are treated as `nonbank` (as in the paper) or `bank` |
| `fed_equity_profile` | how central-bank equity is measured: `source_net_assets` (as published) or `equity_correction` |
| `treasury_bonds_after_redemption` | opening bonds less those the Treasury can redeem |
| `pooled_at_opening_bond_stock` | number of cases in which the pooled kernel equals the opening bond stock |

## The earlier experiments (independent checks only)

The checkers in `fed-balance-sheet-audit/z1-bank-positions/` also verify an
earlier, narrower family of experiments, kept because they test the same
stored balance sheets from another side. They use these labels:

| Label | Meaning |
|---|---|
| `J` | other claims, treated as a block |
| E1, E2, E3 | experiments on `J`: E1 and E2 let it be sold to the central bank, E3 does not (`not_convertible`) |
| menu `three`, `five` | permitted transaction types; `five` adds repayment of bank funding and payout of bank equity |
| F1, F2, F3 | central-bank regimes, each allowing fewer central-bank transactions than the last, so the kernel can only rise from F1 to F3; under F3 the central bank's loans cannot be repaid |
| R1–R5 | Treasury regimes (what the Treasury may do with its account) |
| X1–X4 | cross-border regimes (what may be traded between the two sectors) |
| `foreign_share` | share of a bank-equity payout going to the rest of the world |
| `borrower` | counterfactual moving loans held by the rest of the world from domestic to foreign borrowers: none (`observed`), the direct part (`direct_foreign`) or all (`whole_foreign`) |

These experiments do not produce the paper's figures.
