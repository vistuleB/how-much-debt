# The appendix: what each protection does

Checks behind the appendix of *How much debt does money need?* They need
Python 3.11 or later with `numpy` and `scipy` (see the root README). Unlike the rest of the
repository, run the commands in the table from this folder
(`cd paper-prep/static-vs-operational`).

## The result

The least debt can be read two ways. **Static:** the least debt over balance
sheets that balance, keep every holding non-negative, keep each protected
quantity at its opening value and keep money at or above its opening level.
**Operational:** the least debt reachable from the opening by a given menu of
transactions, with every intermediate balance sheet valid. Anything a menu
reaches is statically admissible, so the operational minimum is never below
the static one. The appendix's table gives the static minimum for each set
of protections and the transactions that reach it; `proofs.md` proves both.

## Commands

| Command | Checks |
|---|---|
| `python3 -I toy.py 300 7` | In a small model (one or two household groups, a bank, a central bank, a Treasury), for each row of the appendix's table: the static minimum by linear programme, the closed form, and the least debt reachable by the row's transactions. Without transfers between groups, pooling the groups' net positions is not reached (the "operational above static" count); with them it is. Protecting money alone is not reachable, since no transaction lowers central-bank equity. |
| `python3 -I paths.py 500 13` | Executes the explicit transaction histories of `proofs.md` on random openings, checking every intermediate balance sheet, and compares each end state with the static minimum. |
| `python3 -I landscape_s9_s15.py 2000 1` | In models with currency, central-bank advances and Treasury regimes R1–R5, each proved least debt equals the static minimum. |
| `python3 -I landscape_s20.py 1500 3` | The same for the bank-positions model (bank nondeposit funding, other claims, locked positions). |
| `python3 -I landscape_s22_f2.py 600 4` | The same for the three-operation menu under central-bank regimes F2 and F3. The F2 run is repeated without a one-way bound, to show the bound is needed: there it disagrees, by design. |
| `python3 -I gov_as_group.py 200 5` | An extra check, not used by the paper: the Treasury and central bank consolidated into one government sector. |

Together the three `landscape` runs compare 24,700 random openings (excluding
the deliberate counterexample) with no disagreement.

The check on US data, that the static reading reproduces the executed minima
on all 252 completed balance sheets of the earlier, narrower measure, is
`python3 -I paper-prep/broad-debt/feasibility.py`, run from the repository
root; it needs only the standard library.

## Notation

The scripts use short names: `EB`, `EF` are the paper's V_B, V_F (bank and
central-bank equity); `T` and `R` are R_T and R_B (the Treasury's account and
bank reserves); `WT` is V_T. `proofs.md` uses the paper's notation.
