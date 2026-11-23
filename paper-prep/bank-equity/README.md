# Transaction engine used by the Fed-valuation sensitivity

`payout_model.py` executes the funded sequences of the broad-debt model, and
`replay.py` replays them independently, without importing any model code.
`broad-debt-model/fed-valuation/` uses both. The engine can also pay out bank
equity to named holders; the paper uses only two settings: banks keep their
equity (the headline), and banks pay it all to the domestic sector (Table 2,
column 9).
