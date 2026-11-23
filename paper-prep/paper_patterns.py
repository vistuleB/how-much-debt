"""Executable checks of the paper's quantified pattern claims; stdlib only.
Run from repository root: python3 -I paper-prep/paper_patterns.py
No file is written. The CLI targets W17; --w16 retains the historical
checks. evaluate()/main() remain W16 compatibility APIs for stored sweeps.
"""
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('paper_profiles',P/'paper_profiles.py')
profiles=importlib.util.module_from_spec(s);s.loader.exec_module(profiles)
EPS=1e-8


def evaluate(data=None):
 d=data or profiles.Data();out=[]
 def exact(name,actual,expected):
  out.append(dict(claim=name,passed=actual==expected,actual=actual,expected=expected))
 def truth(name,value,detail=None):
  out.append(dict(claim=name,passed=bool(value),actual=detail if detail is not None else bool(value),expected=True))
 def rounded(name,value,expected,digits):
  out.append(dict(claim=name,passed=f'{value:.{digits}f}'==expected,actual=value,expected=expected,rounding=digits))
 rows=[r for r in d.records if r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank' and r['securities_repayable'] and not r['pooled']]
 exact('source years',d.years,list(range(2001,2026)))
 pairs=[(r,d.get(r['year'],case=profiles.completion(r),payout=False,pooled=True)) for r in rows]
 eq=sorted({r['year'] for r,k in pairs if abs(k['kernel']/profiles.T-d.metrics(r['year'],case=profiles.completion(r))['tnd'])<EPS})
 expected=list(range(2010,2014))+list(range(2018,2026))
 exact('bank equity kept: pooled equality years',eq,expected)
 truth('bank equity kept: equality in every completion of those years',all(abs(k['kernel']/profiles.T-d.metrics(r['year'],case=profiles.completion(r))['tnd'])<EPS for r,k in pairs if r['year'] in expected))
 lead=[(r['year'],k['kernel']/profiles.T-d.metrics(r['year'],case=profiles.completion(r))['tnd']) for r,k in pairs]
 exact('bank equity kept: later money-binding years',[y for y in d.years if 2010<=y and any(yy==y and v>EPS for yy,v in lead)],list(range(2014,2018)))
 rounded('bank equity kept: maximum 2014–2017 lead',max(v for y,v in lead if 2014<=y<=2017),'0.5',1)
 m=[d.metrics(r['year'],case=profiles.completion(r)) for r in rows]
 truth('with payouts: pooled equals Treasury in every year/completion 2008–2025',all(abs(d.metrics(r['year'],case=profiles.completion(r))['pooled_lead'])<EPS for r in rows if r['year']>=2008))
 early=[d.metrics(r['year'],case=profiles.completion(r))['pooled_lead'] for r in rows if r['year']<2008]
 truth('with payouts: positive pooled lead in every completion 2001–2007',min(early)>0)
 rounded('with payouts: early pooled lead minimum',min(early),'0.4',1)
 rounded('with payouts: early pooled lead maximum',max(early),'0.6',1)
 for label,key in [('pairwise','netting_kept_ratio'),('multilateral A','multilateral_a_kept_ratio'),
                   ('multilateral B','multilateral_b_kept_ratio'),('most generous C','multilateral_kept_ratio')]:
  ratios=[x[key] for x in m]
  truth('US '+label+' / equity-kept kernel in [1.15,1.45), every year/completion',
        all(1.15<=v<1.45 for v in ratios),dict(minimum=min(ratios),maximum=max(ratios),records=len(ratios)))
 truth('US netting ordering C <= B <= A <= pairwise, every year/completion',
       all(x['multilateral']<=x['multilateral_b']+EPS and x['multilateral_b']<=x['multilateral_a']+EPS
           and x['multilateral_a']<=x['netting']+EPS for x in m))
 negative=sorted({r['year'] for r in rows if r['opening']['ef']<0})
 exact('central bank negative-equity years',negative,[2011]+list(range(2021,2026)))
 truth('central bank sign pattern in every completion',all((r['opening']['ef']<0)==(r['year'] in negative) for r in rows))
 rep_deltas=[];issuer_debt=[];issuer_frozen=[];issuer_ratios=[];bank_leads=[];bank_keep_leads=[]
 same_rep=[];same_issuer=[]
 for r in rows:
  y=r['year'];case=profiles.completion(r)
  base=d.metrics(y,case=case);alt=d.metrics(y,'agency_lookthrough','bank',case=case)
  same_issuer.extend([alt['kernel']-base['kernel'],alt['kept_kernel']-base['kept_kernel']])
  issuer_debt.append(base['debt']-alt['debt']);issuer_frozen.append(base['not_repayable']-alt['not_repayable'])
  issuer_ratios.append(alt['netting_kept_ratio']);bank_leads.append((y,alt['pooled_lead']))
  bank_keep=d.get(y,issuer='bank',payout=False,pooled=True,case=case)
  bank_keep_leads.append((y,bank_keep['kernel']/profiles.T-alt['tnd']))
  for payout in (True,False):
   for pool in (True,False):
    a=d.get(y,payout=payout,pooled=pool,case=case)
    b=d.get(y,'security_outside_D',payout=payout,pooled=pool,case=case)
    same_rep.append(b['kernel']-a['kernel'])
    a=d.get(y,payout=payout,pooled=pool,repayable=False,case=case)
    b=d.get(y,'security_outside_D',payout=payout,pooled=pool,repayable=False,case=case)
    rep_deltas.append((b['kernel']-a['kernel'])/profiles.T)
 truth('agency representation: repayable separate/pooled kernels unchanged, both payout policies',max(map(abs,same_rep))<.001)
 truth('agency representation: not-repayable kernel never lower',min(rep_deltas)>=-EPS)
 rounded('agency representation: maximum not-repayable increase',max(rep_deltas),'10.4',1)
 truth('foreign-bank issuers: separate columns 4 and 9 unchanged',max(map(abs,same_issuer))<EPS)
 truth('foreign-bank issuers: debt and not-repayable kernel never higher',min(issuer_debt)>=-EPS and min(issuer_frozen)>=-EPS)
 rounded('foreign-bank issuers: maximum debt reduction',max(issuer_debt),'3.8',1)
 rounded('foreign-bank issuers: maximum not-repayable reduction',max(issuer_frozen),'3.8',1)
 rounded('foreign-bank issuers: netting / equity-kept kernel minimum',min(issuer_ratios),'1.3',1)
 rounded('foreign-bank issuers: netting / equity-kept kernel maximum',max(issuer_ratios),'1.5',1)
 rounded('foreign-bank issuers: pooled lead 2001',max(v for y,v in bank_leads if y==2001),'0.05',2)
 truth('foreign-bank issuers: pooled equality in every completion from 2002',all(abs(v)<EPS for y,v in bank_leads if y>=2002))
 truth('foreign-bank issuers: equity-kept lead gone in 2014–2017',all(abs(v)<EPS for y,v in bank_keep_leads if 2014<=y<=2017))
 head=[d.metrics(y) for y in d.years]
 truth('household remainder has surplus with payouts every year',all(x['hh_rest_paid']<0 for x in head))
 exact('household remainder deficit years without payouts',[y for y,x in zip(d.years,head) if x['hh_rest_kept']>EPS],[2015,2017])
 truth('household remainder surplus in all other years without payouts',all(x['hh_rest_kept']<0 for y,x in zip(d.years,head) if y not in (2015,2017)))
 truth('Treasury share greater than half in every year/completion from 2009',all(d.metrics(r['year'],case=profiles.completion(r))['treasury_share_pct']>50 for r in rows if r['year']>=2009))
 truth('domestic term positive in every year/completion',all(x['dom']>0 for x in m))
 rounded('domestic term minimum over all years/completions',min(x['dom'] for x in m),'3.6',1)
 rounded('domestic term maximum over all years/completions',max(x['dom'] for x in m),'8.7',1)
 truth('foreign term zero in every year/completion',all(abs(x['foreign_term'])<EPS for x in m))
 for group in ('Bottom50','Next40','Next9'):
  truth('household '+group+' deficit in every year',all(x['hh_gap_'+group]>0 for x in head))
 for group in ('RemainingTop1','TopPt1'):
  truth('household '+group+' surplus in every year',all(x['hh_gap_'+group]<0 for x in head))
 return out


def main():
 checks=evaluate()
 for c in checks:print(('OK' if c['passed'] else 'MISMATCH')+' | PATTERN | '+json.dumps(c,sort_keys=True))
 failed=sum(not c['passed'] for c in checks)
 print(f'PATTERN SUMMARY | {len(checks)} claims | {failed} mismatches')
 return int(bool(failed))


evaluate_w16=evaluate
main_w16=main


def main_w17():
 return profiles.load('current_patterns_w17','paper-prep/paper_patterns_w17.py').main()


if __name__=='__main__':raise SystemExit(main_w16() if '--w16' in sys.argv else main_w17())
