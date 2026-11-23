"""Source-instrument crosswalk for the paper’s Table 1; no source/model mutation.
Run: python3 -I broad-debt-model/equity_kept_instruments.py [--check]
The 137-row source disposition catalogue is exhaustive for L.109/110/106;
additional source controls used for nonbank/physical positions follow below.
Old catalogue assignments are retained as provenance, not treated as current rules.
"""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'fed-balance-sheet-audit/z1-bank-positions'

# coordinate; paper table row or balance-sheet operation; applies to source contribution,
# not an instruction to add parent controls to their children.
MAP={
 'B':('bb,bf,d_b,r_b','1'), 'B_B':('bb','1'), 'B_F':('bf','1'),
 'B / Treasury perimeter':('B allocation/perimeter control','1; control'),
 'B / other government issuer':('B allocation/perimeter control','1; control'),
 'C_B':('cb','11: fixed vault cash'), 'C_H':('d_ch,r_ch','11'),
 'M':('d_m,r_m','10'), 'M / Q_B_res':('d_m,r_m / qbr government deposits','10 / 11'),
 'J_B':('j_bd / j_br, split into a,z or excluded remainder','3 / 5'),
 'J_B / internal elimination':('j_bd / j_br or consolidated elimination','3 / 5 / elimination'),
 'J_F':('j_fd / j_fr, split into a,z or excluded remainder','2 / 3 / 5'),
 'L_B':('l_bd,l_br','2; parent/child loan controls are not additive'),
 'L_B / J_B':('l_bg underlying MBS / z_bg issuer debt','2 / 3; representation dependent'),
 'L_F / J_F':('l_fg underlying MBS / z_fg issuer debt','2 / 3; representation dependent'),
 'N_B':('nb','9'), 'N_B / internal elimination':('nb after consolidation','9'),
 'N_B / X_B_res':('nb excluding Fed capital stock / xbr capital stock','9 / 11'),
 'N_F':('nf, included in xf','fixed existing Fed non-debt; no disposal row'),
 'Q_B_H':('d_qbh,r_qbh','6'),
 'Q_B_H / internal elimination':('d_qbh,r_qbh after consolidation','6'),
 'Q_B_res':('qbr','11'), 'Q_B_res counterpart':('qbr: government deposit liability','11'),
 'Q_H':('d_qh,r_qh','7'), 'Q_H / Q_G':('d_qh,r_qh / qg official Treasury component','7 / treasury_claim into t'),
 'Q_lock':('ql','11'), 'R':('r','settlement reserves: changes with Fed purchases/repayment'),
 'R / X_B_res / internal elimination':('r / excluded foreign interbank j_br / eliminated internal claims','settlement / 5 / elimination'),
 'T':('t','Treasury account: changes on collection/redemption'),
 'T / C_H currency bridge':('t / currency valuation/population bridge','account / 11'),
 'T / Q_B_res counterpart':('t or qbr; actual private-bank deposits locked','account / 11'),
 'U':('u','11'), 'U / Q_B_res / internal elimination':('u / foreign funding qbh / consolidation','11 / 6 / elimination'),
 'X_B_res':('xbr','11'), 'X_F_res':('xf - nf - j_fd - j_fr','11'),
 'X_F_res / J_F':('j_fd / j_fr in current source_interpretation.py','5 (old catalogue ambiguity resolved by executable mapping)'),
 'X_F_res / reconciliation':('locked xf residual, ql or qbr signed grossing','11; signed bridge'),
 'X_F_res counterpart':('locked Fed asset; Treasury counterpart not independently added','11; counterpart control'),
 'bank_debt_security_funding':('d_qbh,r_qbh','6; parent funding control'),
 'bank_misc_funding':('qbr','11; parent control'),
 'equity_bridge':('eb','8; market share liability controls are not eb'),
 'fed_equity_bridge':('ef / bank-held Fed stock xbr','fixed ef / 11; equity bridge'),
 'fed_agency_securities':('l_fg / z_fg plus representation controls','2 / 3'),
 'fed_deposits_and_currency':('t,d_qh,r_qh,d_ch,r_ch','7 / account / 11; parent control'),
 'fed_interbank_assets':('u and float bridge','11; parent control'),
 'fed_misc_assets':('nb/nf/j/locked children as explicitly mapped','parent control, not an extra asset'),
 'fed_valuation_bridge':('valuation input to bf / agency / ef','valuation control, not an extra asset'),
 'currency_issuer_bridge':('currency reconciliation control','11; not independently additive'),
 'Treasury_unrepresented_assets':('outside completed Treasury perimeter','no Table 1 row'),
 'Treasury_unrepresented_liabilities':('outside completed Treasury perimeter','no Table 1 row'),
}
for key in ('bank_financial_assets','bank_financial_liabilities','bank_liabilities_and_equity',
            'bank_securities','fed_financial_assets','fed_financial_liabilities',
            'fed_liabilities_and_equity','fed_securities'):
 MAP[key]=('institutional control total','control; not an additional position')
OVERRIDE={
 'FL403197033.Q':('j_bd - a_bd - z_bd','5: excluded FHLB deposit claim, still sold'),
 'FL702050005.Q':('excluded j_bd remainder','5: federal funds/repo asset, still sold'),
 'LM763092305.Q':('signed contribution inside aggregate excluded j_br','5: intercompany debt excluded from D; not a nonnegative standalone loan'),
 'FL763040005.Q':('excluded j_bd remainder','5: bank-held life-insurance reserves, still sold'),
 'FL713091103.Q':('excluded j_fr remainder','5: central-bank swap claim, still sold/held as excluded; issuer label is inherited completion'),
 'FL712051005.Q':('excluded j_fd remainder; negative observation grossed to ql','5 / 11: Fed repo asset; not extinguished'),
 'FL713011525.Q':('z_fr','3: Fed-held foreign securities completed as nonbank sovereign'),
 'FL713068005.Q':('a_fd','2: selected additional nonbank loans'),
 'FL713068813.Q':('a_fd component','2'), 'FL713068665.Q':('a_fd component','2'),
 'FL713068863.Q':('a_fd component','2'), 'FL713068505.Q':('a_fd component','2'),
 'FL313061703.Q':('z_td','4: Treasury-held agency issuer claim; common face normalization'),
 'FL313063005.Q':('z_tr','4: Treasury-held corporate/foreign security'),
 'FL314023005.Q':('s_d,s_r','4: restored federal loan control'),
 'FL313069005.Q':('s_d,s_r component','4'), 'FL313065005.Q':('s_d,s_r component','4'),
 'FL313066220.Q':('s_d student-loan component','4'),
 'FL713069603.Q':('no separate added leaf; securities/agency residual control','control only; not an extra loan'),
}


def render():
 rows=json.loads((BASE/'series-mapping.json').read_text())['entries']
 lines=['# Paper instrument-to-operation crosswalk','',
 'Generated by `python3 -I broad-debt-model/equity_kept_instruments.py`.',
 'Rows refer to the paper’s Table 1, numbered from Treasury bonds (1) to fixed positions (11).',
 'Scope: source controls and constituent instruments, not 137 additive stocks. Parent controls, memo overlaps, consolidation and valuation are labelled; no control is added twice.',
 '', '| Table | Source series | Source label | Current coordinate / treatment | Table 1 row |',
 '|---|---|---|---|---|']
 for row in rows:
  assignment=row['assignment']
  coordinate,table=OVERRIDE.get(row['series'],MAP[assignment])
  lines.append('| '+ ' | '.join(str(x).replace('|','/') for x in (row['table'],row['series'],row['label'],coordinate,table))+' |')
 lines+=['',f'{len(rows)} source rows dispositioned. The original assignment catalogue remains unchanged.',
 '', '## Sources beyond the three institutional tables', '',
 '| Source / instrument | Coordinate / Table 1 row |', '|---|---|',
 '| L.209 FL893169175: commercial paper | selected nonbank z after subtracting bank issuance and institutional holdings / 3 |',
 '| L.212 FL893062005: municipal debt | selected z / 3 |',
 '| L.213 FL893063005: corporate and foreign bonds | selected z, net of bank issuance/institutional holdings; foreign bank-issuer sensitivity leaves z_dr=0 / 3 or excluded j / 5 |',
 '| L.214 FL894123005: all loans | l_hg after exclusions for federal-held, direct-Fed and bank-funding loans; those restored as s_g/a_fd where appropriate / 2,4 |',
 '| L.125/L.126 FL403065195, FL403065495, FL413065005: agency mortgage pools | underlying l_hg in look-through; security and borrower layer retained separately otherwise / 2,3 |',
 '| L.216 FL263169203: foreign federal-loan borrowers | s_r; remaining federal loans s_d / 4 |',
 '| L.203 FL763123005; L.204 FL313030003: government bank deposits | subtract from nonbank deposits; qbr locked / 11 |',
 '| S.62.a LM702010095: bank nonfinancial assets | nb / 9, sold to Fed |',
 '| S.61.a LM712010095: Fed nonfinancial assets | nf (included in xf), existing balance fixed; increases when bank nb acquired |',
 '| L.109 FL713164003: Fed capital stock | subtracted from bank miscellaneous equity and kept in xbr / 11 |',
 '', '## Source/code authority', '',
 '`source_interpretation.py` constructs the holdings; `adapters/bank_positions.gleam` and `adapters/row_split.gleam` project them. `corrected_build.py` marks a/z subinventories; `corrected_model.py` defines the transaction whitelist. The new equity-kept copy differs only in prohibiting payout and omitting its receipts. This crosswalk changes none of those sources or assignments.',
 '', 'The inherited j debtor labels are completion labels, not source-identified issuers: excluded interbank and swap claims still occur there. Row 5 should not imply that every excluded claim is legally owed by a nonbank. The selected debt perimeter excludes them even though conversion permission is retained.',
 '', 'Household pensions, insurance and shares are omitted/locked in the household-slicing experiment. This does not lock bank-owned insurance reserves in excluded j or bank-owned shares/fund holdings in nb. Stock ownership and institutional holder must be specified.']
 return '\n'.join(lines)+'\n'


if __name__=='__main__':
 path=Path(__file__).with_name('equity-kept-instruments.md');text=render()
 if '--check' in sys.argv:
  if path.read_text()!=text:raise SystemExit('stale '+str(path))
 else:path.write_text(text)
 print('137 institutional source rows and 10 additional source groups mapped')
