# How much debt does money need? Replication files

Code and data behind the US figures in John Paul Steinberger, *How much debt
does money need?* (2026). The paper's central quantity is the
*transaction-based debt kernel* (`kernel` in the code): the least debt that
ordinary transactions can reach while no sector's money or net financial
position falls, under the protections the paper states.

Release v1.0.0 is archived at Zenodo: https://doi.org/10.5281/zenodo.24482763

## Running the code

Python 3.11 or later. Most commands use the standard library only; the
appendix checks, the independent netting check and the household-split
netting also need NumPy and SciPy 1.17 or later (SciPy 1.17 needs Python 3.11
or later, SciPy 1.18 needs 3.12), and Figure 1 also needs Matplotlib. Tested with Python 3.11, NumPy 2.4 and SciPy
1.17, and with Python 3.14, NumPy 2.5 and SciPy 1.18; SciPy 1.13 gave wrong
results in the household-split solver. A virtual environment is the
simplest way to get them:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Run every command from this folder, the repository root, unless its row says
otherwise. Paths in the documentation are likewise from the repository root,
unless they name a file in the same folder. Most commands use `python3 -I` (isolated mode), so that nothing
outside the repository, such as `PYTHONPATH` or packages installed with
`pip install --user`, can change the result; install NumPy and SciPy in a
virtual environment, as above, rather than with `--user`.
Two commands are exceptions and run without `-I`:
`broad-debt-model/corrected_build.py`, which imports its neighbour
`corrected_model.py`, and the Figure 1 script, which imports the
household-split code in `paper-prep/netting-splits/`.

Every command takes seconds, except the household-split netting at the
allocation least favourable to netting (`run_households.py`, about two and a
half hours for all 25 years on one process). Its results are stored, and
`best_case.py` gives the figure the paper uses in seconds.

`python3 -I paper-prep/paper_numbers.py` checks every number in the paper
against the stored results, in seconds; `paper-numbers.md` says where each
comes from.

The checks were written against the final manuscript, labelled W17 in the
code (`paper_numbers_w17.py`, `paper_patterns_w17.py`); the numbers they
expect are stored in the code, so the manuscript itself is not needed. The
option `--w16` reruns the checks of the preceding draft, whose headline let
banks pay out their equity; it is kept for the record and does not match the
published paper.

## The paper's numbers

| Command | Gives |
|---|---|
| `python3 -I paper-prep/broad-debt/bank_equity_kept.py` | Table 2, columns 4, 6 and 7: the transaction-based debt kernel with banks keeping their equity, as in the paper's headline figures, separate and pooled, and netting compared with it (`--json` for machine-readable output) |
| `python3 -I paper-prep/broad-debt/series.py` | Table 2, the other columns: debt, netting, the Treasury's net debt, the kernel with securities not repayable, and the kernel when banks also pay out their equity to the domestic sector (column 9), 2001–2025, with the spread across completed balance sheets (`--json`) |
| `python3 -I paper-prep/broad-debt/netting.py` | What netting alone leaves, in 2008 and 2020–2025 (`series.py` gives every year) |
| `python3 -I paper-prep/broad-debt/netting_frozen.py` | Netting when securities cannot be retired early, against the matching kernel |
| `python3 -I paper-prep/netting_completions_w17.py` | The same, over every completed balance sheet of each year: what netting leaves when securities cannot be retired early varies slightly with the completion, unlike the kernel |
| `python3 -I paper-prep/broad-debt/netting_multilateral.py` | What any netting can leave, including clearing around chains of three or more parties |
| `python3 -I paper-prep/broad-debt/netting_multilateral.py --self-test` | The netting solver on small networks with known answers |
| `python3 -I paper-prep/broad-debt/netting_multilateral_check.py` | Independent check of the multilateral netting with a linear-programme solver (needs `numpy` and `scipy`) |
| `python3 -I paper-prep/sector-slicing/slice_corrected.py` | The kernel with households split into five wealth groups |
| `python3 -I paper-prep/sector-slicing/slice_checks.py` | Checks on that split: vintage, containment, an explicit sequence that attains it |
| `python3 -I paper-prep/sector-slicing/netting_range.py` | What netting leaves under the household split (a range) |
| `python3 paper-prep/figures/make_figure1.py figure1.pdf` | Figure 1, as `figure1.pdf` and `figure1.png` (needs `numpy`, `scipy` and `matplotlib`; uses the TeX Gyre Pagella font if installed, otherwise the default font) |

These read the stored completed balance sheets and executed runs:

- `fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json` (2001–2007)
- `broad-debt-model/corrected-results.json` (2008, 2020–2025)
- `fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json` (2009–2019)

The completed balance sheets behind these runs are stored in each folder's
`row-split/check.json`, with the narrower earlier experiments in
`row-split/restrictive-check.json` (about 70 MB together). They are stored so
that every result can be checked without rebuilding: `check-row-split.py` and
`check-restrictive.py` in `fed-balance-sheet-audit/z1-bank-positions/` check
them, and `rebuild.py --verify` in each extension folder re-verifies them (see
"Independent checks"). Rebuilding them from the raw data (`rebuild.py --build`)
also needs the project's balance-sheet completion model, written in Gleam,
which is not part of this package.

The sensitivity in Section 4.1 that values the Federal Reserve's securities at
amortized cost is stored in `broad-debt-model/fed-valuation/results.json.gz`
(1,728 executed and independently replayed runs, 2021–2025);
`paper_numbers.py` reads it. The transaction engine these runs use, and its
independent replayer, are in `paper-prep/bank-equity/` (see its README). `python3 -I broad-debt-model/fed-valuation/build.py --check`
rebuilds it and compares, and `python3 -I broad-debt-model/fed-valuation/check.py`
re-checks it independently from the raw Z.1 archive.

The household-split netting stores its results in
`paper-prep/netting-splits/best-case-results.json` (the allocation most
favourable to netting) and `paper-prep/netting-splits/households-results.json`
(both ends).

## Independent checks

| Command | Checks |
|---|---|
| `python3 broad-debt-model/corrected_build.py --check` | Every stored run reaches its kernel with a funded witness |
| `python3 -I broad-debt-model/corrected_check.py --self-test` | Replays every step of every sequence, and rejects deliberately corrupted copies |
| `python3 -I broad-debt-model/equity_kept_build.py --check` and `python3 -I broad-debt-model/equity_kept_check.py --self-test` | The same for the runs in which banks keep their equity: 3,840 executed sequences, stored in `broad-debt-model/equity-kept-results.json`; `EQUITY-KEPT.md` explains them |
| `cd fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007 && python3 -I rebuild.py --verify` | Re-verifies the stored 2001–2007 balance sheets and runs |
| `cd fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019 && python3 -I rebuild.py --verify` | Re-verifies the stored 2009–2019 balance sheets and runs |

The code's short names (the coordinate letters, the labels in the stored
runs) are explained in `GLOSSARY.md`.

## Netting under the household split

`paper-prep/netting-splits/` computes how much debt netting leaves when
households are split into five wealth groups, over every allocation of claims
consistent with the published totals (Section 5). Its README lists the
commands and the judgement calls. It needs `numpy` and `scipy`.

## The appendix

`paper-prep/static-vs-operational/` holds the proofs and checks behind the
appendix ("What each protection does"); its README lists the commands. The
check on US data is `python3 -I paper-prep/broad-debt/feasibility.py`: the
static reading reproduces the executed minima on all 252 completed balance
sheets of the earlier, narrower measure.

## Sources

All from the Board of Governors of the Federal Reserve System, included
unchanged. `SOURCES.json` gives, for each file, the release, the URL, the
download date, the size and the SHA-256; `python3 -I check_sources.py`
checks that every file is present and unchanged.

- *Financial Accounts of the United States* (Z.1), March 19, 2026 release:
  `fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip`, with
  the printed release (`z1-20260319.pdf`) and the H.4.1 release of January 2,
  2026 (`h41-20260102.pdf`), each cited for one classification in
  `fed-balance-sheet-audit/z1-bank-positions/source-manifest.json`.
- Z.1, September 11, 2026 release, table S.14.b and its data dictionary:
  `paper-prep/sector-slicing/raw/z1-20260911-S14_b.csv` and `.txt`, extracted
  unchanged from the release's ZIP.
- *Distributional Financial Accounts*, September 18, 2026 release (data
  through 2026Q2): `paper-prep/sector-slicing/raw/dfa.zip`.

Unless otherwise indicated, information on the Board's website is in the
public domain and may be copied and distributed without permission; the Board
asks to be cited as the source.

## Licence

Code: MIT. Documentation and the project's stored data: CC BY 4.0. The raw
statistical releases keep their own terms. See `LICENSE` for the scope, and
`CITATION.cff` for how to cite.
