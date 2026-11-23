# Bank equity kept: funded kernel reductions

23 November 2026. Isolated copies of the corrected executor and independent
checker; existing corrected modules and numerical results are unchanged.

```sh
python3 -I broad-debt-model/equity_kept_build.py
python3 -I broad-debt-model/equity_kept_build.py --check
python3 -I broad-debt-model/equity_kept_check.py --self-test
python3 -I broad-debt-model/equity_kept_instruments.py --check
python3 -I paper-prep/paper_numbers.py
```

Standard library only; run from repository root. Build writes only the two
new `equity-kept-*.json` outputs; `--check` rebuilds in memory and compares bytes.
No source-input refresh or inventory writer runs.

The opening files are the existing corrected results for 2001–2007,
2008/2020–2025 and 2009–2019. All 480 completed balance sheets are used, with
both foreign-security issuer completions, both money groupings and both
security repayment permissions: 3,840 streams. Both agency representations
are included. Amounts are USD millions, as in the parent executor.

`equity_kept_model.py` copies `corrected_model.py`, removes the payout receipt
from its certificate and the payout step from its construction, rejects payout
transactions (including zero-amount ones), and enforces unchanged bank and Fed
equity after each move. All other moves and invariants are reproduced explicitly.
Its `net` retains the parent's bank-equity addend; since equity is now constant,
checking that expression also checks the ordinary nonbank net position.

`equity_kept_check.py` is an independent copy of `corrected_check.py`, importing
no project module. It reconstructs openings from the pinned source archive and
row-split reports, derives its own resource certificate, rejects payouts, checks
both balance sheets, Treasury and nonbank net positions, money floors, equity
and capacities after every step, and requires all expected configurations.
Pooled transfers preserve the total nonbank net position and money floor, as in
the parent grouping policy; separate runs protect each group individually.

The builder additionally compares every reached endpoint with the independent reference
`bank_equity_kept.py`. All 3,840 values agree within the original executor's
0.001 USD million tolerance ($1,000); no numerical discrepancy was found.
Independent replay checks 103,944 atomic steps; nine corrupted reports are
rejected by the self-test.

The output is `equity-kept-results.json`, with separately identified source
families, SHA-256 fingerprints of the original corrected reports and their
source/archive fingerprints. `equity-kept-verification.json` records the
comparison and replay counts and annual pooled Treasury-floor equalities.

## Results and qualification

- 2,616 configurations are unchanged by forbidding the payout.
- All 1,920 not-repayable configurations are among those unchanged cases.
- Headline 2025 separate kernel with equity kept: 37.468091 trillion versus
  34.206770 with the payout (3.261321 trillion difference).
- First pooled equality with Treasury net debt: **2010**. Equality holds in
  2010–2013, fails again in 2014–2017, and holds throughout 2018–2025. A permanent
  switch from 2010 is not supported by these outputs.

The source-to-operation crosswalk is `equity-kept-instruments.md`. It identifies
controls and overlapping memo rows as such; 137 source rows are not 137 additive
positions.
