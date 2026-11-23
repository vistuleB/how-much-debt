# Every number in the paper

```sh
python3 -I paper-prep/paper_numbers.py
```

This one command checks every number in *How much debt does money need?* that
comes from the data: 287 comparisons, in seconds. It needs only the standard
library. Run it from the repository root. It reads only stored results and the
raw Federal Reserve archives, and writes nothing. It also checks 84 patterns
in the data that the paper's text relies on, such as the years in which each
side binds. With the manuscript present, it would also check eleven wording points
against its text; the manuscript is not part of this package, so these are
skipped, and the first output line says so (`MANUSCRIPT | using stored W17
expectations; local draft absent`). W17 is the code's label for the final
manuscript.

Each comparison is one output line of the form:

```
OK | <where in the paper> | paper=<printed value> | exact=<value> | rounded=<value as the paper rounds it> | <source>
```

Other lines are labelled by their first word: `PATTERN` (one pattern check,
with its details as JSON), `EXTERNAL` (a number taken from outside the data),
`QUALIFICATION`, `DETAIL`, `EXECUTED COMPARISON` and `HISTORICAL RUN RECORD`
(notes on how a number was computed). The output ends with `PATTERN SUMMARY`
and `SUMMARY`, the numbers of checks and of mismatches. The exit status is 1
if any printed value differs from the exact value rounded as the paper rounds
it.

## Where the numbers come from

| Numbers in the paper | Source |
|---|---|
| Table 2, columns 2, 3, 5 and 8; netting and securities-not-repayable figures | `paper-prep/broad-debt/series.py --json` |
| Table 2, column 9 (banks pay out their equity) | `bank_equity_kept.py --json` (`least_with_payout`, which reproduces the stored payout kernel) |
| Table 2, columns 4, 6 and 7 (banks keep their equity); retirement percentages, ratios, the Treasury's share, which side binds, and the 2021–2025 changes in the introduction and Section 4 | `paper-prep/broad-debt/bank_equity_kept.py --json` |
| Netting with securities not cancellable ($74.4–74.7 trillion in 2025, depending on the completion) | `paper-prep/netting_completions_w17.py`, over all 240 look-through completions (`netting-completions-w17.md` gives each year's range). `paper-prep/broad-debt/netting_frozen.py` prints the first completion, the low end in every year; `bank_equity_kept.py` reports the high end |
| Debt retired by netting when securities are not cancellable (20–31%) | `paper-prep/netting_completions_w17.py`, over all completions |
| Netting around chains of three or more parties ($52.2 trillion in 2025, the most generous claim set) | `paper-prep/broad-debt/netting_multilateral.py` |
| Netting within sectors | `series.py` |
| Fed amortized-cost sensitivity: 2025 equity, 2021–2025 kernel-change range and pooled invariance | `broad-debt-model/fed-valuation/results.json.gz` |
| Central-bank equity in 2025 | the stored completed balance sheets (`opening.ef`) |
| Federal loans; intercompany direct-investment debt | the March 2026 Z.1 archive, tables L.106 and L.223 (series named in the output) |
| Numbers of completed balance sheets | the three `row-split/check.json` files |
| Household split: percentages, the bottom-99% gaps, vintage effect | the DFA household items rescaled item by item to the March Z.1, as described in the paper and implemented in `paper-prep/sector-slicing/slice_checks.py` |
| Household split: netting compared with the kernel | `paper-prep/netting-splits/households-results.json` |
| Appendix counts | the documented trial parameters of the three `landscape` commands; `row-split/check.json` for the 252 earlier balance sheets |

`paper-prep/sector-slicing/slice_corrected.py` prints the household figures
*without* the rescaling to March, so they differ slightly from the paper's
(the paper's figures are rescaled to March; see `slice_checks.py`).

## An external observation and a scale calculation

- **The Fed's deferred asset, $243.5 billion at the end of 2025.** This is
  external: Federal Reserve Bank of New York (2026), *Open Market Operations
  during 2025*. The command prints its source; it does not recompute it.
- **Central-bank equity of about minus $14 trillion**, the equity that would
  bring the debt kernel below money in 2025. This is a scale calculation:
  equity now, less the gap between the kernel (banks keeping their equity)
  and money: −14.13. It is computed from the stored opening and kernel; it is
  not a balance sheet that has been completed and solved.

The appendix's count of 24,700 random openings is recomputed from the trial
parameters. The results of those trials come from rerunning the three
`landscape` commands in `paper-prep/static-vs-operational/`.
