"""Generate/recheck equity-kept funded streams from unchanged stored openings.

From repository root: python3 -I broad-debt-model/equity_kept_build.py [--check]
No source interpretation or opening is regenerated. New outputs only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
P=Path(__file__).resolve().parent
ROOT=P.parent
sys.path.insert(0,str(P))
import equity_kept_model as model
import equity_kept_check as replay

INPUTS=[
 ('broad-debt-model/corrected-results.json','fed-balance-sheet-audit/z1-bank-positions/row-split/check.json'),
 ('fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json','fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/row-split/check.json'),
 ('fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json','fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/row-split/check.json')]


def build():
 spec=importlib.util.spec_from_file_location('reference_kept',ROOT/'paper-prep/broad-debt/bank_equity_kept.py')
 reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
 families=[];unaffected=0;frozen=0;differences=[];pooled={}
 for baseline_path,source_path in INPUTS:
  raw=(ROOT/baseline_path).read_bytes();old=json.loads(raw);records=[]
  for rec in old['records']:
   v=rec['opening'];pool=rec['pooled'];repay=rec['securities_repayable']
   result=model.reduce(v,pool,repay);cert=model.certificate(v,pool,repay)
   actual=model.debt(result.v);expected=reference.certificate(v,pool,repay,False)
   if abs(actual-expected)>.001:raise ValueError(('reference certificate',rec['id'],pool,repay,actual,expected))
   if abs(actual-cert['lower_bound'])>.001:raise ValueError('attainment')
   if result.v['eb']!=v['eb']:raise ValueError('equity')
   row=dict(rec,endpoint=result.v,stream=result.steps,certificate=cert,kernel=actual,
            signed_debt_receipt_gap={g:model.loans(v,g)+v['s_'+g]+model.issued(v,g)-cert['receipts'][g] for g in model.G})
   records.append(row)
   same=abs(actual-rec['kernel'])<=.001
   unaffected+=same
   if not repay:
    frozen+=1
    if not same:differences.append(dict(id=rec['id'],pooled=pool,issuer=rec['nonbank_foreign_security_issuers'],delta=actual-rec['kernel']))
   if pool and repay and rec['representation']=='agency_lookthrough' and rec['nonbank_foreign_security_issuers']=='nonbank':
    year=rec['year'];treasury_floor=max(0,-model.treasury(v))
    pooled.setdefault(year,[]).append(abs(actual-treasury_floor)<=.001)
  report={k:v for k,v in old.items() if k!='records'}
  report['records']=records
  families.append(dict(baseline_path=baseline_path,source_path=source_path,
                       baseline_sha256=hashlib.sha256(raw).hexdigest(),report=report))
 document=dict(format_version=1,policy='bank_equity_kept',unit='USD millions',families=families)
 verification=replay.check_all(document)
 verification.update(auditor_formula_differences=0,payout_no_effect_configurations=unaffected,
  securities_not_repayable_configurations=frozen,securities_not_repayable_differences=differences,
  headline_pooled_equals_treasury={str(y):all(xs) for y,xs in sorted(pooled.items())},
  first_permanent_headline_treasury_year=next(y for y in sorted(pooled) if all(all(pooled[z]) for z in pooled if z>=y)))
 return document,verification


if __name__=='__main__':
 document,verification=build()
 for name,data in [('equity-kept-results.json',document),('equity-kept-verification.json',verification)]:
  text=json.dumps(data,sort_keys=True,separators=(',',':'))+'\n';path=P/name
  if '--check' in sys.argv:
   if path.read_text()!=text:raise ValueError('stale '+name)
  else:path.write_text(text)
 print(json.dumps(verification,sort_keys=True))
