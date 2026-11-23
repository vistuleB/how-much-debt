"""Reconstruct every legacy J source contribution, without assigning mixed debtors.

No executor inputs are changed here. Additive rows and signed subtractions are
kept distinct from nonadditive controls. All values are USD millions.
"""
import csv,hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'fed-balance-sheet-audit/z1-bank-positions'
ARCHIVE=BASE/'raw/z1-20260319-csv.zip'
# owner, table, series, disposition, rationale; agency has representation-dependent
# principal and is reconciled as a separate residual against legacy coordinates.
TERMS=[
 ('Banks','l110','FL403197033','exclude','FHLB deposits: deposit instrument, not securities or loans.'),
 ('Banks','l110','FL702050005','exclude','Federal funds and repos; bank liabilities or excluded repo instrument.'),
 ('Banks','l110','FL703069175','mixed_issuer','Commercial paper: eligible instrument, bank issuer share must be removed.'),
 ('Banks','l110','LM703062005','include','Municipal securities: nonbank government issuers.'),
 ('Banks','l110','LM703063005','mixed_issuer','Corporate/foreign bonds: split bank versus nonbank issuers.'),
 ('Banks','l110','LM763092305','mixed_issuer','Direct-investment intercompany debt: identify debtor sector and instrument.'),
 ('Banks','l110','FL763040005','exclude','Life-insurance reserves: not loan or debt-security instrument.'),
 ('Fed','l109','FL713011515','exclude','Foreign currency/deposits: not loan or debt-security instrument.'),
 ('Fed','l109','FL713091103','exclude','Central-bank swap counterparties, not nonbank debtors.'),
 ('Fed','l109','FL712051005','exclude','Repo/official-reserve claims; excluded repo, mixed remainder requires detail.'),
 ('Fed','l109','FL713011525','mixed_issuer','Foreign securities: identify bank/nonbank issuer shares.'),
 ('Fed','l109','FL713068005','include','Loans to households, brokers/dealers, finance companies and other financial business; four published nonbank borrower components close exactly.'),
 ('Nonbank','l209','FL893169175','include_net_of_bank_issuance','Total commercial paper less bank-issued securities through the existing netting expression.'),
 ('Nonbank','l212','FL893062005','include','Municipal securities control contribution.'),
 ('Nonbank','l213','FL893063005','include_net_of_bank_issuance','Corporate/foreign bonds control contribution; existing expression subtracts bank debt issuance.'),
]
SUBTRACTIONS=[('l110','FL703069175'),('l110','LM703062005'),('l110','LM703063005'),('l110','FL704122005'),('l106','FL313063005'),('l109','FL713011525')]

def build(cases_path=None):
 raw=ARCHIVE.read_bytes();expected=json.loads((BASE/'source-manifest.json').read_text())['sha256']
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('archive hash')
 z=zipfile.ZipFile(io.BytesIO(raw));tables={}
 def v(t,c,y):
  if t not in tables:tables[t]={r['date']:r for r in csv.DictReader(io.StringIO(z.read('csv/'+t+'.csv').decode('utf-8-sig')))}
  return int(tables[t][f'{y}:Q4'][c+'.Q'])
 mapping={}
 for name in z.namelist():
  if name.startswith('data_dictionary/') and name.endswith('.txt'):
   for line in z.read(name).decode('utf-8-sig').splitlines():
    fields=line.split('\t')
    if len(fields)>1:mapping[(Path(name).stem,fields[0].split('.')[0])]=fields[1]
 cases=json.loads((Path(cases_path) if cases_path is not None else BASE/'row-split/check.json').read_text())['scenarios'];years=sorted({c['year'] for c in cases});result=[]
 for y in years:
  rows=[dict(holder=h,table=t,series=c+'.Q',label=mapping.get((t,c),c),disposition=d,reason=r,value=v(t,c,y)) for h,t,c,d,r in TERMS]
  interbank=v('l110','FL704010005',y)-sum(v('l202',c,y) for c in ['FL754112205','FL754012205','FL474012205','FL743020005'])-v('l109','FL713113003',y)
  rows.append(dict(holder='Banks',table='derived',series='external_interbank_assets',label='Interbank assets after matched internal claims and Fed reserves',disposition='exclude',reason='Debtors are banks/Fed, not nonbanks.',value=interbank))
  nonbank_total=sum(v(t,c,y) for h,t,c,_,_ in TERMS if h=='Nonbank')-sum(v(t,c,y) for t,c in SUBTRACTIONS)
  checks=[]
  for case in cases:
   if case['year']!=y:continue
   s={x['name']:x['value'] for g in ('balances','holdings','positions') for x in case['state'][g]}
   bank=sum(s['j_b'+i] for i in 'drt');fed=sum(s['j_f'+i] for i in 'drt');nonbank=sum(s['j_'+h+i] for h in 'dr' for i in 'drt')
   bn=sum(r['value'] for r in rows if r['holder']=='Banks');fn=sum(r['value'] for r in rows if r['holder']=='Fed')
   # Agency remainder is the retained issuer layer; look-through principal
   # already in L must never be re-added.
   remainder=dict(Banks=bank-bn,Fed=fed-fn,Nonbank=nonbank-nonbank_total)
   if min(remainder.values()) < -1e-3:raise ValueError((case['id'],'negative agency residual',remainder))
   checks.append(dict(id=case['id'],legacy_J=dict(Banks=bank,Fed=fed,Nonbank=nonbank),agency_issuer_layer=remainder))
  fed_components=[dict(series=c+'.Q',label=mapping[('l109',c)],value=v('l109',c,y)) for c in ['FL713068813','FL713068665','FL713068863','FL713068505']]
  if sum(x['value'] for x in fed_components)!=v('l109','FL713068005',y):raise ValueError('Fed loan borrower control')
  federal_components=[dict(series=c+'.Q',label=mapping[('l106',c)],value=v('l106',c,y)) for c in ['FL313069005','FL313065005','FL313066220']]
  if sum(x['value'] for x in federal_components)!=v('l106','FL314023005',y):raise ValueError('Federal loan instrument control')
  treasury_securities=[dict(series=c+'.Q',label=mapping[('l106',c)],value=v('l106',c,y)) for c in ['FL313061703','FL313063005']]
  if sum(x['value'] for x in treasury_securities)!=v('l106','FL314022005',y):raise ValueError('Treasury securities control')
  federal=v('l106','FL314023005',y);student=v('l106','FL313066220',y);foreign=v('l216','FL263169203',y)
  result.append(dict(year=y,contributions=rows,nonbank_signed_subtractions=[dict(table=t,series=c+'.Q',value=-v(t,c,y),label=mapping.get((t,c),c)) for t,c in SUBTRACTIONS],nonbank_nonagency=nonbank_total,checks=checks,treasury_held_securities=treasury_securities,fed_nonbank_loan_components=fed_components,federal_loan_components=federal_components,federal_loans=dict(total=federal,student=student,foreign=foreign,domestic_residual=federal-foreign,nonstudent_residual=federal-student)))
 return dict(format_version=1,archive_sha256=expected,status='complete additive inventory; mixed issuer splits unresolved; no new minima certified',years=result)

def render(d):
 lines=['# Legacy J inventory and broad-debt classification','','Generated by `inventory.py`. USD trillions in the table; exact USD millions in JSON.','',
 'Every source contribution is retained, including signed nonbank netting terms. Mixed issuer rows are not classified by their old J debtor label. The old adapter assigned residuals to domestic nonbank as a completion; that does not establish that the debtor is a nonbank.','',
 '| Holder | Source | 2025 | Disposition | Reason |','|---|---|---:|---|---|']
 y=next(x for x in d['years'] if x['year']==2025)
 for r in y['contributions']:lines.append(f"| {r['holder']} | `{r['series']}` | {r['value']/1e6:.6f} | {r['disposition']} | {r['reason']} |")
 lines += ['', '## Netting and agency layer','', 'The direct-investment contribution is a signed net series (negative $4.414 billion in 2025). It cannot be installed as a nonnegative gross loan asset without a separate grossing/offset policy. Keeping its signed amount visible is not an assertion of negative debt.', '',
 'The nonbank securities expression subtracts bank securities **issued**, not bank-held securities alone. It then subtracts selected institutional holdings. This supports a nonbank aggregate, but does not identify which institutional holders own the excluded bank-issued portion. A new bilateral allocation must satisfy both issuer totals and holder capacities. Do not subtract bank issuance a second time from nonbank claims while also removing it from institutional holdings.', '',
 'For every one of the 252 states, the JSON records the residual agency issuer layer after reconstructing non-agency J. These residuals are nonnegative. Agency principal already looked through into L is not counted again. Separate representation choices remain separate experiments.', '',
 '## Federal loans','', '| Year | Total | Student | Observed foreign borrowers | Nonstudent residual |','|---|---:|---:|---:|---:|']
 for x in d['years']:
  f=x['federal_loans'];lines.append(f"| {x['year']} | {f['total']/1e6:.6f} | {f['student']/1e6:.6f} | {f['foreign']/1e6:.6f} | {f['nonstudent_residual']/1e6:.6f} |")
 lines += ['', 'The selected total in `source_interpretation.py` explicitly subtracts federal-held loans; `build-row-split.py` subtracts observed federal loans from foreign liabilities too. Thus S restores an excluded selected liability, not a duplicate of L. Domestic residual allocation remains a completion, pending program/borrower checks.', '',
 '## Additional Treasury holdings required by the adopted rule','', 'Treasury also holds agency/GSE and corporate/foreign securities outside legacy J. Their instrument control closes exactly in all seven years and is recorded in JSON. A holder-independent definition cannot omit these while counting the same nonbank-issued security elsewhere. Agency holdings must follow the chosen look-through/consolidation representation; corporate/foreign issuer composition needs review. These are not yet added to the prototype or its formula.', '', '## Next implementation boundary','',
 'Keep excluded funding claims in their existing institutional balance sheets and under their existing permissions. Split eligible loans/securities from excluded claims before constructing the successor model state. The blanket-J prototype is not that adapter. Required next evidence: bank/nonbank issuer allocation of corporate bonds and CP; direct-investment counterparties; foreign-security issuers. Fed n.e.c. loans ARE resolved: the four published domestic nonbank borrower components close exactly in all seven years. Federal loans also close to other loans, mortgages and student loans. This inventory alone does not certify experiment results.','']
 return '\n'.join(lines)
if __name__=='__main__':
 d=build();out=Path(__file__).parent
 for name,text in [('claim-inventory.json',json.dumps(d,indent=2,sort_keys=True)+'\n'),('claim-inventory.md',render(d))]:
  p=out/name
  if '--check' in sys.argv:
   if p.read_text()!=text:raise ValueError('stale '+name)
  else:p.write_text(text)
 print('7 source years; all 252 legacy J inventories reconstructed')
