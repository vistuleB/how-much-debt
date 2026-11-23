"""Retain availability evidence, distinguishing published ND from absent periods."""
import csv,hashlib,io,json,sys,zipfile
from pathlib import Path
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent
raw=(BASE/'raw/z1-20260319-csv.zip').read_bytes();z=zipfile.ZipFile(io.BytesIO(raw));tables={}
specs=[(e['table'],e['series'],e['label']) for e in json.loads((BASE/'series-mapping.json').read_text())['entries']]
for t,c in [('s61a','FL712090095'),('s62a','FL702090095'),('s61a','LM712010095'),('s62a','LM702010095')]:
 d={r.split('\t')[0]:r.split('\t')[1] for r in z.read('data_dictionary/'+t+'.txt').decode().splitlines()};specs.append((t,c+'.A',d[c+'.A']))
doc_path=STAGE/'row-split/input.json'
if doc_path.exists():
 seen={(t,c) for t,c,_ in specs}
 for o in json.loads(doc_path.read_text())['shared_source_input']['observations']:
  if (o['table'],o['series']) not in seen:
   specs.append((o['table'],o['series'],o['label']));seen.add((o['table'],o['series']))
specs.sort()
years=[]
for y in range(2000,2008):
 missing=[]
 for t,c,label in specs:
  if t not in tables:tables[t]={r['date']:r for r in csv.DictReader(io.StringIO(z.read('csv/'+t+'.csv').decode('utf-8-sig')))}
  date=str(y) if t.startswith('s') else f'{y}:Q4'
  value=tables[t].get(date,{}).get(c)
  if value is None or value=='ND':missing.append(dict(table=t,series=c,label=label,raw=value,reason='published_ND' if value=='ND' else 'period_absent',binding=c!='FL703139105.Q'))
 years.append(dict(year=y,source_cells=len(specs),missing=missing,completed=y>=2001,clearing_float=int(tables['l109'][f'{y}:Q4']['FL713022003.Q'])))
sector={r['date']:r for r in csv.DictReader(io.StringIO(z.read('csv/s6a.csv').decode('utf-8-sig')))}
d=dict(financial_sector_nonfinancial_assets_2000=dict(table='s6a',series='LM795013865.A',value=int(sector['2000']['LM795013865.A']),units='USD millions',status='Whole financial sector, not an observed bank/Fed split; no completion assigned'),format_version=1,source_sha256=hashlib.sha256(raw).hexdigest(),years=years)
# Diagnostic only: a closing stock minus next-year capital formation,
# revaluation and other-volume changes is not assumed to identify an opening.
probes=[]
for table,prefix,flow,financial in [('s61a','71','FU715015085','l109'),('s62a','70','FU705015085','l110')]:
 ts=tables[table];r=ts['2001'];code='LM'+prefix+'2010095.A'
 candidate=int(r[code])-int(r[flow+'.A'])-int(r['FR'+prefix+'2010095.A'])-int(r['FV'+prefix+'2010095.A'])
 nw=int(r['FL'+prefix+'2090095.A'])-int(r['FC'+prefix+'2090095.A'])
 r0=tables[financial]['2000:Q4'];fa='FL714090005.Q' if prefix=='71' else 'FL704090005.Q';li='FL714190005.Q' if prefix=='71' else 'FL704190005.Q';eq='FL713164005.Q' if prefix=='71' else 'FL703181105.Q'
 nw_control=int(r0[fa])+candidate-int(r0[li])-int(r0[eq])
 errors=[]
 for year in range(2002,2025):
  row=ts[str(year)];back=int(row[code])-int(row[flow+'.A'])-int(row['FR'+prefix+'2010095.A'])-int(row['FV'+prefix+'2010095.A'])
  errors.append(dict(year=year,error=back-int(ts[str(year-1)][code])))
 probes.append(dict(table=table,candidate_nonfinancial_assets_2000=candidate,terms_2001={k:int(r[k]) for k in [code,flow+'.A','FR'+prefix+'2010095.A','FV'+prefix+'2010095.A']},networth_backcast=nw,networth_from_2000_financial_sheet=nw_control,control_error=nw_control-nw,observed_year_errors=errors,max_observed_absolute_error=max(abs(e['error']) for e in errors),applied=False))
d['stock_flow_backcast_diagnostic']=probes
text=json.dumps(d,indent=2,sort_keys=True)+'\n';p=STAGE/'source-coverage.json'
if '--check' in sys.argv:assert p.read_text()==text,'stale source coverage'
else:p.write_text(text)
print('2000 has one nonbinding ND and four absent IMA cells; 2001–2007 source controls available')
