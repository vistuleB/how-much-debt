"""Conditional instrument-split openings; preserves all inherited US artifacts.

Issuer completion: retain existing placement of bank-issued securities in nonbank
bank-funding accounts. Thus institutional CP/corporate holdings are nonbank debt.
This is a completion, not observed who-to-whom data. Signed L.223 net positions
are outside the selected L.208/L.214 instrument perimeter, not zero gross debt.
"""
import hashlib,json,sys
from pathlib import Path
from inventory import build as inventory
from corrected_model import G,H,certificate,debt,reduce,validate,loans,issued
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'fed-balance-sheet-audit/z1-bank-positions'
SOURCE=BASE/'row-split/check.json'
def opening(case,inv,foreign_issuers="nonbank"):
 if foreign_issuers not in ["nonbank","bank"]:raise ValueError("foreign issuer policy")
 v={x['name']:x['value'] for group in ('balances','holdings','positions') for x in case['state'][group]}
 row={r['series']:r['value'] for r in inv['contributions']}
 agency=next(c for c in inv['checks'] if c['id']==case['id'])['agency_issuer_layer']
 for g in G:
  v['s_'+g]=inv['federal_loans']['foreign' if g=='r' else 'domestic_residual']
  v['j_t'+g]=0
 for h in H:
  for g in G:v['a_'+h+g]=v['z_'+h+g]=0
 # Old bilateral source completion allocates known foreign interbank claims
 # and net direct investment to j_br; bank domestic securities stay in j_bd.
 v['z_bd']=agency['Banks']+sum(row[c] for c in ['FL703069175.Q','LM703062005.Q','LM703063005.Q'])
 # A published -$1m repo asset in 2024 is a signed contra-position.
 # Gross it onto the existing locked Fed liability account, preserving equity.
 contra=max(0,-row['FL712051005.Q'])
 v['j_fd']+=contra;v['xf']+=contra;v['ql']+=contra
 v['z_fd']=agency['Fed'];v['a_fd']=row['FL713068005.Q']
 v['z_fr']=row['FL713011525.Q']
 for h in G:
  for g in G:v['z_'+h+g]=v['j_'+h+g]
 if foreign_issuers=='bank':v['z_dr']=0
 # Government agency holdings already carry the inherited representation's
 # face normalization in the shared real-world record (billions -> millions).
 v['z_td']=v['j_td']=sum(round(x['value']*1000) for x in case['shared_positions'] if x['holder']=='Treasury' and x['instrument']['type']=='AgencyBond')
 v['z_tr']=v['j_tr']=next(x['value'] for x in inv['treasury_held_securities'] if x['series']=='FL313063005.Q')
 validate(v);return v

def build(source_path=SOURCE):
 raw=Path(source_path).read_bytes();inv=inventory(cases_path=source_path);byyear={y['year']:y for y in inv['years']};records=[]
 for case in json.loads(raw)['scenarios']:
  for foreign_issuers in ["nonbank","bank"]:
   v=opening(case,byyear[case["year"]],foreign_issuers)
   for pooled in [False,True]:
    for repayable in [False,True]:
     c=certificate(v,pooled,repayable);r=reduce(v,pooled,repayable)
     if abs(debt(r.v)-c['lower_bound'])>1e-3:raise ValueError((case['id'],pooled,repayable,debt(r.v),c))
     corrections=[]
     repo=next(x['value'] for x in byyear[case['year']]['contributions'] if x['series']=='FL712051005.Q')
     if repo<0:corrections.append(dict(source='FL712051005.Q',amount=-repo,changes=['j_fd +amount','xf +amount','ql +amount'],reason='Gross signed negative repo asset into existing locked Fed liabilities; equity unchanged'))
     records.append(dict(nonbank_foreign_security_issuers=foreign_issuers,corrections=corrections,id=case['id'],year=case['year'],representation=case['representation'],pooled=pooled,securities_repayable=repayable,opening=v,endpoint=r.v,stream=r.steps,certificate=c,signed_debt_receipt_gap={g:loans(v,g)+v['s_'+g]+issued(v,g)-c['receipts'][g] for g in G},opening_debt=debt(v),kernel=debt(r.v)))
 return dict(format_version=1,status='conditional corrected experiment; not a source-identified full-debt estimate',source_sha256=hashlib.sha256(raw).hexdigest(),archive_sha256=inv['archive_sha256'],unit='USD millions',issuer_completion='inherited_nonbank_bank_security_funding',federal_borrower_completion='domestic_except_observed_FL263169203',intercompany_policy='outside_L208_L214_instrument_perimeter_signed_L223_retained_in_excluded_inventory',foreign_reserve_security_completion='foreign_nonbank_sovereign',nonbank_foreign_security_issuer_cases=['nonbank','bank'],records=records)
def render(d):
 # The shared renderer also publishes the isolated annual extensions.
 # Derive the period from this report rather than naming the root dataset.
 spans=[]
 for year in sorted({r['year'] for r in d['records']}):
  if spans and spans[-1][1]+1==year:spans[-1][1]=year
  else:spans.append([year,year])
 labels=[str(a) if a==b else f'{a}–{b}' for a,b in spans]
 period=', '.join(labels[:-1])+' and '+labels[-1] if len(labels)>1 else labels[0]
 lines=['# Instrument-split broad-debt experiment','',f'Audited 20 November 2026. Conditional on the named issuer completion and selected instrument perimeter. The selected agency-look-through, nonbank-issuer, repayable-securities figures supply Table 2 for {period}; other rows show the alternative profiles. USD trillions. Repayable/not repayable are different permissions, not estimated contractual rights.','', '| Year | Representation | Securities | Nonbank-held foreign issuers | Opening D | Separate kernel | Pooled kernel |','|---|---|---|---|---:|---:|---:|']
 for year in sorted({r['year'] for r in d['records']}):
  for rep in ['agency_lookthrough','security_outside_D']:
   rows=[r for r in d['records'] if r['year']==year and r['representation']==rep]
   if not rows:continue
   for foreign_issuers in ["nonbank","bank"]:
    for repay in [True,False]:
     def rng(xs):return f'{min(xs)/1e6:.3f}–{max(xs)/1e6:.3f}'
     rs=[r for r in rows if r['securities_repayable']==repay and r['nonbank_foreign_security_issuers']==foreign_issuers]
     lines.append(f"| {year} | {rep} | {'repayable' if repay else 'not repayable'} | {foreign_issuers} | {rng([r['opening_debt'] for r in rs])} | {rng([r['kernel'] for r in rs if not r['pooled']])} | {rng([r['kernel'] for r in rs if r['pooled']])} |")
 lines+=['',f"{len(d['records'])} executed configurations; {sum(len(r['stream']) for r in d['records'])} funded atomic steps. All endpoints attain their receipt/collection certificate.",'','Issuer completion, scope, proof and remaining modelling choices: see `broad-debt-model/CORRECTED.md`.','']
 return '\n'.join(lines)
if __name__=='__main__':
 d=build();base=Path(__file__).parent
 for name,text in [('corrected-results.json',json.dumps(d,separators=(',',':'),sort_keys=True)+'\n'),('corrected-results.md',render(d))]:
  p=base/name
  if '--check' in sys.argv:
   if p.read_text()!=text:raise ValueError('stale '+name)
  else:p.write_text(text)
 print(f"{len(d['records'])} instrument-split profiles reach their certificates by funded witnesses")
