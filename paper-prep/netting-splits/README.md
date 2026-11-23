# Netting under the household split

Section 5 of the paper compares netting with the debt kernel when households
are split into five wealth groups (Distributional Financial Accounts). The
accounts give each group's totals but not who holds whose claims, so netting
depends on an unknown *allocation* of claims; the kernel does not (it needs
only each group's money and net position). This folder computes netting over
every allocation consistent with the published totals. Needs NumPy and SciPy
(see the root README; SciPy 1.13 gave wrong results). Run from the repository
root.

| Command | Gives |
|---|---|
| `python3 -I paper-prep/netting-splits/netting_lp.py` | Self-test of the solver on small networks with known answers |
| `python3 -I paper-prep/netting-splits/two_sector.py` | Check: the solver on the two-sector network of Table 2 reproduces `netting_multilateral.py` and the pairwise netting of `series.py` on all 240 balance sheets. Seconds |
| `python3 -I paper-prep/netting-splits/best_case.py` | For every year, the debt netting leaves under the allocation most favourable to netting, pairwise and multilateral, with judgement calls J4 and J8 kept and dropped, and its ratio to the split kernel (the figure in Section 5). Seconds. With `--json` it prints the same results as JSON; `best-case-results.json` is that output, stored |
| `python3 -I paper-prep/netting-splits/run_households.py <year> --check` | Both ends for one year, the allocation most and least favourable to netting, compared with the stored `households-results.json` without changing it. The least favourable end is a mixed-integer programme: from under a minute to half an hour per year, about two and a half hours for all 25 |

`run_households.py` without `--check` writes its results into
`households-results.json`; `--resume` skips the years already there. Run one
process at a time: the solver already uses several threads, and parallel runs
can take many times longer. The least favourable end can differ between SciPy
versions in the fourth decimal (USD trillions), within the tolerance of
`--check`; the most favourable end, which the paper uses, does not. The solver
may print its own progress lines.

## Files

- `netting_lp.py`: the solver. A network of claims with known or unknown
  amounts, unknowns tied by linear constraints; the most debt netting can
  cancel under the most favourable allocation (a linear programme), and under
  the least favourable one (a mixed-integer programme, obtained from the dual
  of the inner problem). The least favourable figure is always *certified*:
  the allocation found is checked with a linear programme, so the published
  totals allow an allocation under which netting leaves at least that much.
- `two_sector.py`: the two-sector network of the paper's Table 2, all amounts
  known; run as a command, it checks that it reproduces `paper-prep/broad-debt/netting_multilateral.py` and the
  pairwise netting of `series.py` on all 240 balance sheets.
- `households.py`: the household split, with every judgement call labelled.
- `best_case.py`, `run_households.py`: the runs above.

## Judgement calls (households.py)

- **J1** Groups may hold claims on other groups and on themselves (household
  mortgages held by households, and agency mortgage-backed securities, which
  the look-through representation turns into claims on the mortgage
  borrowers). A group's claims on itself cancel.
- **J2** Only debt securities and loans held count as a group's claims, as in
  the kernel's narrow bracket; deposits and currency never cancel; fund
  shares, pensions, insurance, equities and businesses stay locked.
- **J3** Bank bonds held by households are nondeposit claims on banks; with
  foreign bonds they are at most each group's corporate and foreign bonds, and
  in total at most households' (B.101.h).
- **J4** Households hold no claims on the central bank other than currency.
- **J5** The Treasury's claims on households are at least the federal student
  loans (L.222), each group's at most its consumer credit.
- **J6** Households' Treasury securities total B.101.h's figure, each group's
  at most its government and municipal securities.
- **J7** Household debt held by banks and the central bank lies between the
  bounds of `paper-prep/sector-slicing/netting_range.py`.
- **J8** For the wider claim sets, non-debt claims of or on the domestic sector
  belong to the rest of the sector, not to households.
- **J9** DFA sub-items are rescaled to the March 2026 Z.1 with their parent
  column's factor.

Results, both ends (`households-results.json`): pairwise netting leaves 1.17 to
1.30 times the split kernel under the most favourable allocation, and 1.52
to 1.77 times under the least favourable one. For 2001–2004, 2006 and 2008–2013
the least favourable figure is a certified lower bound (`exact_worst_case` is
false): an allocation the totals allow leaves at least that much.

A call that loosens the constraints can only help netting at the most
favourable end. J1 loosens; J4 and J8 tighten, so `best_case.py` also reports
the run without them: pairwise netting's best case is unchanged in every year,
multilateral netting's falls by at most $0.34 trillion, and the lowest ratios
to the split kernel stay 1.17 (pairwise, 2022) and 1.07 (multilateral,
2010).

## Checks

`best_case.py` and `run_households.py` check every year and exit with status 1
if a check fails: multilateral netting never leaves more than pairwise; a wider
claim set or dropped judgement call never leaves more; netting never leaves less
than the split kernel; for `run_households.py` also that the most favourable
end is below the least favourable one and that the hand bounds of
`netting_range.py` bracket the exact pairwise values.
