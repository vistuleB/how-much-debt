#!/usr/bin/env python3
"""Independent formula checker for BANK-POSITIONS benchmark states.

Reads only (1) stored model states and (2) reported diagnostics. It imports no
repository code and trusts no reported kernel: every value is recomputed from
the state coordinates using the independently implemented model formulas, then compared.

Formulas: Lemma 20.3 (identity and parameters), Theorem 20.4 and
Proposition 20.5 (convertible J, "E1/E2"), Theorem 20.9 (not-convertible J, "E3").
Lemma 20.3 decomposes debt as money + convertible claims + Treasury resources
+ a signed offset, with a penalty when additional advances are unavailable.
Theorem 20.4 gives attained kernels for the five Treasury regimes; Proposition
20.5 gives endpoint money-minus-debt maxima and the J-inclusive adjustment.
Theorem 20.9 replaces the claim buffer and offset when J cannot be converted.
Vector order everywhere: funding (fixed, additional) x statistic (narrow,
J-inclusive) x regime (R1..R5) = 20 entries.

Usage:
  python3 -I independent_formula_check.py STATES.json [STATES2.json ...] --diagnostics check.json

STATES files: either a list of records or an object with a "scenarios" list.
Each record has "id" and "state" = {"balances", "holdings", "positions"} in
integer USD millions, as in completed-benchmarks.json.
--diagnostics: the shared route's check.json ("projections" list with
"convertible" and "not_convertible" blocks). Exit status 1 on any discrepancy.
"""
import json
import sys

FUNDING = ("fixed", "additional")
STATISTIC = ("narrow", "J-inclusive")


def pos(x):
    return x if x > 0 else 0


def flatten(state):
    v = {}
    for group in ("balances", "holdings", "positions"):
        for k, x in state[group].items():
            if k in v:
                raise ValueError("duplicate coordinate " + k)
            v[k] = x
    return v


def structural_errors(v):
    """Balance sheets, sign conditions and the Lemma 20.3 identity.

    The identity is D = m + h + W + e: debt equals money, convertible
    claims, Treasury resources and a signed balance-sheet offset.
    """
    errs = []
    for k, x in v.items():
        if not isinstance(x, int):
            errs.append(k + " is not an integer")
        elif k != "e_f" and x < 0:
            errs.append(k + " is negative")
    x_b = v["n_b"] + v["j_b"] + v["x_b_res"]
    q_b = v["q_b_h"] + v["q_b_res"]
    if v["q_f"] != v["q_h"] + v["q_g"] + v["q_f_lock"]:
        errs.append("Q_F != Q_H + Q_G + Q_lock")
    if v["x_f"] < v["n_f"] + v["j_f"]:
        errs.append("X_F smaller than N_F + J_F (negative locked Fed residual)")
    bank = v["m"] + v["e_b"] + v["u"] + q_b - (v["b_b"] + v["l_b"] + v["r"] + v["c_b"] + x_b)
    fed = v["b_f"] + v["l_f"] + v["u"] + v["x_f"] - (v["r"] + v["t"] + v["c_h"] + v["c_b"] + v["q_f"] + v["e_f"])
    if bank:
        errs.append("bank sheet off by %d" % bank)
    if fed:
        errs.append("Fed sheet off by %d" % fed)
    return errs


def diagnostics(v, not_convertible):
    """Return dict of 20-vectors and scalars for one J policy."""
    bonds = v["b_h"] + v["b_b"] + v["b_f"]
    loans = v["l_h"] + v["l_b"] + v["l_f"]
    debt = bonds + loans
    m = v["m"] + v["c_h"]
    w = v["t"] + v["q_g"]
    x_b = v["n_b"] + v["j_b"] + v["x_b_res"]
    h = v["b_h"] + v["l_h"] + v["e_b"] + v["j_h"] + v["q_h"] + v["q_b_h"]
    e = v["e_f"] + v["q_f_lock"] + v["q_b_res"] - v["x_f"] - x_b - v["j_h"]
    z = v["x_b_res"] - v["q_b_res"]
    if debt != m + h + w + e:
        raise ValueError("identity D = m + h + W + e fails")
    if not_convertible:  # Theorem 20.9, (20.9)
        # Non-convertible J leaves the buffer and enters the locked offset.
        e, h, z = e + v["j_h"], h - v["j_h"], z + v["j_b"]
    j_tot = v["j_h"] + v["j_b"] + v["j_f"]
    kernels, potentials, penalties = [], [], []
    for funding in FUNDING:
        sigma = pos(z - v["u"] - m) if funding == "fixed" else 0
        k = [pos(m + e + sigma), pos(m + e + sigma),
             pos(m + e + sigma + pos(w - bonds)),
             pos(bonds - w) + pos(loans - h + sigma),
             bonds + pos(loans - h + sigma)]
        psi = [-e, -e, -e - pos(w - bonds), -e - pos(w - bonds), -e - w]
        for statistic in STATISTIC:
            add = j_tot if statistic == "J-inclusive" else 0
            kernels += [x + add for x in k]
            potentials += [x - add for x in psi]
            penalties.append(sigma)
    return {"kernels": kernels, "potentials": potentials, "penalties": penalties,
            "debt": debt, "nonbank_money": m}


def load_states(paths):
    states = {}
    for p in paths:
        data = json.load(open(p))
        records = data.get("scenarios", data.get("projections")) if isinstance(data, dict) else data
        for r in records:
            if r["id"] in states:
                raise ValueError("duplicate state id " + r["id"])
            states[r["id"]] = flatten(r["state"])
    return states


def main(argv):
    if "--diagnostics" not in argv:
        sys.exit(__doc__)
    i = argv.index("--diagnostics")
    state_paths, diag_path = argv[1:i], argv[i + 1]
    states = load_states(state_paths)
    projections = json.load(open(diag_path))["projections"]
    problems, compared = [], 0
    reported_ids = set()
    for p in projections:
        sid = p["id"]
        if sid in reported_ids:
            problems.append(sid + ": duplicate reported projection")
        reported_ids.add(sid)
        if sid not in states:
            problems.append(sid + ": no stored state")
            continue
        v = states[sid]
        errs = structural_errors(v)
        if errs:  # formulas presuppose balanced sheets; report and skip
            problems += [sid + ": " + e for e in errs]
            continue
        for block, not_convertible in (("convertible", False), ("not_convertible", True)):
            mine = diagnostics(v, not_convertible)
            for key, value in mine.items():
                compared += 1
                if p[block][key] != value:
                    problems.append("%s %s %s: reported %s, recomputed %s" % (sid, block, key, p[block][key], value))
    for sid in sorted(set(states) - reported_ids):
        problems.append(sid + ": state with no reported diagnostics")
    summary = {"states": len(states), "projections": len(projections),
               "fields_compared": compared, "problems": len(problems)}
    print(json.dumps(summary))
    for line in problems[:50]:
        print(line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
