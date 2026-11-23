"""Continuous 2001–2025 views, assembled from stored old/new results only."""
import hashlib,json,sys
from pathlib import Path
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;REPO=STAGE.parents[2]

def build():
 MID=BASE/'extension-2009-2019'
 paths=[BASE/'row-split/check.json',MID/'row-split/check.json',STAGE/'row-split/check.json',BASE/'row-split/restrictive-check.json',MID/'row-split/restrictive-check.json',STAGE/'row-split/restrictive-check.json',REPO/'broad-debt-model/corrected-results.json',MID/'broad-debt/results.json',STAGE/'broad-debt/results.json']
 paths.append(STAGE/'real-world/partial-2000.json')
 data=[json.loads(p.read_text()) for p in paths]
 states=sum([x['scenarios'] for x in data[:3]],[]);restrictive=sum([x['records'] for x in data[3:6]],[]);broad=sum([x['records'] for x in data[6:9]],[])
 assert len({s['id'] for s in states})==len(states)==480
 assert sorted({s['year'] for s in states})==list(range(2001,2026))
 out=[]
 for year in range(2001,2026):
  fed='source_net_assets' if year<2020 else 'equity_correction'
  head=f'{year}/holder_correction/{fed}/observed_us_mix/agency_lookthrough'
  state=next(s for s in states if s['id']==head)
  v={a['name']:a['value'] for group in ['balances','holdings','positions'] for a in state['state'][group]}
  m=v['d_m']+v['r_m'];currency=v['d_ch']+v['r_ch']
  observed=[r for r in restrictive if r['year']==year and r['borrower']=='observed']
  chosen=[]
  for menu in ['three','five']:
   for central in ['F2','F3']:
    r=next(r for r in observed if r['id']==head and r['menu']==menu and r['central_bank']==central and r['foreign_share']==0)
    family=[x for x in observed if x['representation']=='agency_lookthrough' and x['menu']==menu and x['central_bank']==central and x['foreign_share']==0]
    chosen.append(dict(menu=menu,central_bank=central,bonds=r['bonds'],separate=r['kernel'],pooled=r['pooled_kernel'],separate_range=[min(x['kernel'] for x in family),max(x['kernel'] for x in family)],pooled_range=[min(x['pooled_kernel'] for x in family),max(x['pooled_kernel'] for x in family)],pooled_at_opening_bond_stock=sum(abs(x['pooled_kernel']-x['bonds'])<1e-6 for x in family),completions=len(family)))
  bs=next(r for r in broad if r['id']==head and not r['pooled'] and r['securities_repayable'] and r['nonbank_foreign_security_issuers']=='nonbank')
  bp=next(r for r in broad if r['id']==head and r['pooled'] and r['securities_repayable'] and r['nonbank_foreign_security_issuers']=='nonbank')
  out.append(dict(year=year,id=head,fed_equity_profile=fed,states=sum(s['year']==year for s in states),deposits=m,currency=currency,nonbank_money=m+currency,narrow_debt=sum(v[k] for k in ['bb','bf','d_b','r_b'])+sum(v['l_'+h+g] for h in 'bfdr' for g in 'dr'),restrictive=chosen,broad=dict(debt=bs['opening_debt'],separate=bs['kernel'],pooled=bp['kernel'],domestic_gap=bs['signed_debt_receipt_gap']['d'],treasury_bonds_after_redemption=bs['opening']['bb']+bs['opening']['bf']+bs['opening']['d_b']+bs['opening']['r_b']-bs['certificate']['redemption_cap'])))
 partial=data[9];assert partial['year']==2000 and partial['units']=='USD billions'
 pm=next(x['value'] for x in partial['known_positions'] if x['holder']=='Nonbank' and x['instrument']['type']=='Deposit')*1000
 ch=next(x['value'] for x in partial['known_positions'] if x['holder']=='Nonbank' and x['instrument']['type']=='Currency')*1000
 return dict(partial_years=[dict(year=2000,status='not_completed',deposits=pm,currency=ch,nonbank_money=pm+ch)],format_version=1,vintage='2026-03-19',status='conditional year-end snapshots; not a completed intervening history; broad results audited 20 November 2026',input_sha256={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},years=out)
def render(d):
 lines=['# US year-end series, 2001–2025','','Generated from the isolated backfill and unchanged existing outputs. USD trillions. All years use the March 19, 2026 Z.1 archive. The 2001–2019 Fed profile is labelled source net assets; 2020–2025 retains the equity-correction headline. Both headline derivations use source net assets with the inherited price adjustments; the later correction families are not backfilled or compared as matched completion families.','', 'Conditional endpoint reductions, not observed transaction histories. Headline agency look-through, observed-US mix, holder correction and domestic payouts. Completion ranges and both agency representations remain in the machine-readable/full result files.','', 'Year 2000 is retained as partial source/historian evidence only; no completed opening or kernel is reported for it. See `source-coverage.json` and `real-world/partial-2000.json`.','', '## Existing narrow debt: three-operation menu, settling Fed F2','', '| Year | Deposits M | Currency C_H | Nonbank money | Debt B+L | Bonds B | Separate K | Pooled K | Pooled loans left | At opening bond stock: completions |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
 for y in d['partial_years']:
  lines.append(f"| {y['year']} (partial) | {y['deposits']/1e6:.3f} | {y['currency']/1e6:.3f} | {y['nonbank_money']/1e6:.3f} | — | — | — | — | — | not completed |")
 for y in d['years']:
  r=next(r for r in y['restrictive'] if r['menu']=='three' and r['central_bank']=='F2')
  nums=[y['deposits'],y['currency'],y['nonbank_money'],y['narrow_debt'],r['bonds'],r['separate'],r['pooled'],r['pooled']-r['bonds']]
  lines.append(f"| {y['year']} | "+' | '.join(f'{x/1e6:.3f}' for x in nums)+f" | {r['pooled_at_opening_bond_stock']}/{r['completions']} |")
 lines+=['','## Existing narrow debt: five-operation menu, domestic payouts','', '| Year | F2 separate | F2 pooled | F3 separate | F3 pooled |','|---|---:|---:|---:|---:|']
 for y in d['years']:
  f2=next(r for r in y['restrictive'] if r['menu']=='five' and r['central_bank']=='F2');f3=next(r for r in y['restrictive'] if r['menu']=='five' and r['central_bank']=='F3')
  lines.append(f"| {y['year']} | "+' | '.join(f'{v/1e6:.3f}' for v in [f2['separate'],f2['pooled'],f3['separate'],f3['pooled']])+' |')
 lines+=['','## Conditional instrument-split broad debt: F1 conversions and R4 redemption','', 'Different experiment from the tables above. Repayable securities, inherited issuer placement and nonbank-held foreign bonds assigned nonbank issuers. See `broad-debt/results.md` for both repayment and foreign-issuer profiles; the proof/source qualifications in `broad-debt-model/CORRECTED.md` carry over.','', '| Year | Broad D | Separate K | Pooled K | Treasury floor | Domestic receipt gap |','|---|---:|---:|---:|---:|---:|']
 for y in d['years']:
  b=y['broad'];lines.append(f"| {y['year']} | "+' | '.join(f"{b[k]/1e6:.3f}" for k in ['debt','separate','pooled','treasury_bonds_after_redemption','domestic_gap'])+' |')
 lines+=['','## When does the bond floor bind?','', '“Money versus government debt” is not a menu-independent dichotomy. In the narrow restrictive experiments, bonds are frozen, so K=B precisely when no selected loans remain. This does not assert K equals nonbank money otherwise.','']
 for menu in ['three','five']:
  rows=[(y['year'],next(r for r in y['restrictive'] if r['menu']==menu and r['central_bank']=='F2')) for y in d['years']]
  hit=[year for year,r in rows if abs(r['pooled']-r['bonds'])<1e-6]
  notafter=[year for year,r in rows if hit and year>min(hit) and abs(r['pooled']-r['bonds'])>=1e-6]
  lines.append(f"- Headline {menu}-operation pooled F2: bond floor binds in {', '.join(map(str,hit))}; later departures after the first equality: {', '.join(map(str,notafter)) or 'none'}. All-completion counts above prevent treating the headline as universal.")
 lines+=['','The broad table allows redemption and changes what counts as debt, so its Treasury floor is a different quantity. Its domestic gap must not be substituted into a narrower model or household slicing without matching the instrument and permission definitions.','']
 return '\n'.join(lines)
if __name__=='__main__':
 d=build()
 for name,text in [('annual-series.json',json.dumps(d,indent=2,sort_keys=True)+'\n'),('annual-series.md',render(d))]:
  p=STAGE/name
  if '--check' in sys.argv:
   if p.read_text()!=text:raise ValueError('stale '+name)
  else:p.write_text(text)
 print('Published 25 consecutive completed year-end snapshots, 480 underlying projections')
