"""Read-only profile calculations shared by pattern checks and sensitivities.

Amounts are USD trillions in the returned metrics. No solver or writer runs.
Source rows/keys stay unchanged; a profile is a choice among stored runs.
"""
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
T=1e6
FILES=['fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json',
       'broad-debt-model/corrected-results.json',
       'fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json']


def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def key(r):return (r['id'],r['pooled'],r['securities_repayable'],r['nonbank_foreign_security_issuers'])


def completion(r):
 return r['id'].replace('/agency_lookthrough','').replace('/security_outside_D','')


class Data:
 def __init__(self):
  self.records=[r for f in FILES for r in json.loads((ROOT/f).read_text())['records']]
  kept=json.loads((ROOT/'broad-debt-model/equity-kept-results.json').read_text())
  self.kept=[r for f in kept['families'] for r in f['report']['records']]
  self.index={True:{key(r):r for r in self.records},False:{key(r):r for r in self.kept}}
  self.ids={(completion(r),r['representation']):r['id'] for r in self.records}
  self.years=sorted({r['year'] for r in self.records})
  self.heads={}
  for r in self.records:
   if r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank' and r['securities_repayable'] and not r['pooled']:
    self.heads.setdefault(r['year'],completion(r))
  self.series=load('profile_series','paper-prep/broad-debt/series.py')
  self.multi=load('profile_multi','paper-prep/broad-debt/netting_multilateral.py')
  self.sc=load('profile_households','paper-prep/sector-slicing/slice_checks.py')
  self.H,self.X=self.sc.b101h(),self.sc.dfa();self.student=self.sc.student()
  self.household_net=json.loads((ROOT/'paper-prep/netting-splits/households-results.json').read_text())
  self._metrics={}

 def get(self,year,representation='agency_lookthrough',issuer='nonbank',payout=True,pooled=False,repayable=True,case=None):
  ident=self.ids[(case or self.heads[year],representation)]
  return self.index[payout][(ident,pooled,repayable,issuer)]

 def metrics(self,year,representation='agency_lookthrough',issuer='nonbank',payout=True,case=None):
  cache=(year,representation,issuer,payout,case or self.heads[year])
  if cache in self._metrics:return self._metrics[cache]
  opts=dict(representation=representation,issuer=issuer,payout=payout,case=case)
  r=self.get(year,**opts);v=r['opening'];cert=r['certificate']
  frozen=self.get(year,repayable=False,**opts)
  pool=self.get(year,pooled=True,**opts)
  keep=self.get(year,representation,issuer,False,case=case)
  pay=self.get(year,representation,issuer,True,case=case)
  bonds=sum(v[k] for k in ('bb','bf','d_b','r_b'))/T
  resources=sum(v[k] for k in ('t','qg','s_d','s_r','j_td','j_tr'))/T
  debt=r['opening_debt']/T;k=r['kernel']/T
  gd,gr=(r['signed_debt_receipt_gap'][g]/T for g in 'dr')
  money=(v['d_m']+v['d_ch'])/T
  P=sum(v[k] for k in ('d_m','r_m','d_ch','r_ch'))/T
  cl=lambda h,g:sum(v[p+h+g] for p in ('l_','a_'))
  cancelled=sum(cl(g,g) for g in 'dr')+2*min(cl('d','r'),cl('r','d'))
  cancelled+=2*sum(min(v['s_'+g]+v['a_t'+g],v[g+'_b']) for g in 'dr')
  cancelled+=sum(min(cl('b',g),v[g+'_qbh'])+min(cl('f',g),v[g+'_qh']) for g in 'dr')
  m=dict(debt=debt,kernel=k,netting=self.series.netting_only(v,r['opening_debt'])/T,
   tnd=max(0,bonds-resources),dom=max(0,gd),gap_d=gd,gap_r=gr,foreign_term=max(0,gr),
   pooled=pool['kernel']/T,not_repayable=frozen['kernel']/T,
   kept_kernel=keep['kernel']/T,payout_kernel=pay['kernel']/T,
   eb=v['eb']/T,ef=v['ef']/T,money_d=money,money=P,net_d=money-gd,
   within_sector=sum(v.get(p+g+g,0) for p in ('l_','a_','z_') for g in 'dr')/T,
   netting_not_repayable=debt-cancelled/T,
   multilateral=self.multi.netting(v,r['opening_debt'],'C')/T)
  m['multilateral_a']=self.multi.netting(v,r['opening_debt'],'A')/T
  m['multilateral_b']=self.multi.netting(v,r['opening_debt'],'B')/T
  m.update(retired=debt-k,retirement_pct=100*(1-k/debt),netting_retirement_pct=100*(1-m['netting']/debt),
   not_repayable_retired=debt-m['not_repayable'],not_repayable_retirement_pct=100*(1-m['not_repayable']/debt),
   debt_ratio=debt/k,netting_ratio=m['netting']/k,treasury_share_pct=100*m['tnd']/k,
   not_repayable_netting_ratio=m['netting_not_repayable']/m['not_repayable'],
   netting_kept_ratio=m['netting']/m['kept_kernel'],retirement_kept_pct=100*(1-m['kept_kernel']/debt),
   netting_to_kept_gap=m['netting']-m['kept_kernel'],fed_threshold=m['ef']-(k-P),pooled_lead=m['pooled']-m['tnd'])
  m.update(multilateral_a_kept_ratio=m['multilateral_a']/m['kept_kernel'],
   multilateral_b_kept_ratio=m['multilateral_b']/m['kept_kernel'],
   multilateral_kept_ratio=m['multilateral']/m['kept_kernel'])
  ratios=[m[x] for x in ('netting_kept_ratio','multilateral_a_kept_ratio','multilateral_b_kept_ratio','multilateral_kept_ratio')]
  m.update(any_netting_ratio_min=min(ratios),any_netting_ratio_max=max(ratios))
  cols=('Loans (Liabilities)','Debt securities','Loans (Assets)')
  scales={col:sum(self.H[year][c] for c in codes)/T/sum(self.X[(f'{year}:Q4',g)][col] for g in self.sc.GROUPS)
          for col,codes in self.sc.VINTAGE if col in cols}
  gaps=lambda factors:[sum(sign*self.X[(f'{year}:Q4',g)][col]*factors[col] for col,sign in zip(cols,(1,-1,-1))) for g in self.sc.GROUPS]
  gs,raw=gaps(scales),gaps(dict.fromkeys(cols,1))
  split=lambda xs:m['tnd']+sum(max(0,x) for x in xs)+max(0,gd-sum(xs))+max(0,gr)
  one,five=split([sum(gs)]),split(gs);rest=gd-sum(gs)
  # The household totals are held fixed under source-profile sensitivities;
  # these are arithmetic sensitivities, not fresh household holder completions.
  kept_rest=rest+(m['eb'] if payout else 0)
  paid_rest=rest-(0 if payout else m['eb'])
  five_kept=five+max(0,kept_rest)-max(0,rest)
  m.update(hh_one=one,hh_five=five,hh_kept=five_kept,hh_rest=rest,hh_rest_kept=kept_rest,
   hh_rest_paid=paid_rest,hh_effect=max(0,kept_rest)-max(0,paid_rest),
   hh_separation_pct=100*(one/k-1),wealth_extra_pct=100*(five/one-1),
   hh_share_pct=100*one/debt,hh_five_share_pct=100*five/debt,base_share_pct=100*k/debt,
   vintage_effect=abs(five-split(raw)))
  for g,value in zip(self.sc.GROUPS,gs):m['hh_gap_'+g]=value
  cc=sum(self.X[(f'{year}:Q4',g)]['Consumer credit'] for g in self.sc.GROUPS)
  parts={g:dict(c=sum(self.X[(f'{year}:Q4',g)][col]*scales[col] for col in cols[1:]),
    o=self.X[(f'{year}:Q4',g)][cols[0]]*scales[cols[0]],
    s=self.student[year]*self.X[(f'{year}:Q4',g)]['Consumer credit']/cc) for g in self.sc.GROUPS}
  parts['rest']={k:cert[field]['d']/T-sum(v[k] for v in parts.values()) for k,field in [('c','receipts'),('o','repayable'),('s','treasury_receivables')]}
  parts['row']={k:cert[field]['r']/T for k,field in [('c','receipts'),('o','repayable'),('s','treasury_receivables')]}
  result=debt-self.sc.sequence(parts,(bonds,resources),cert['prepared_reserve_cap']/T,False)
  m['collection_increment']=result-five
  if representation=='agency_lookthrough' and issuer=='nonbank' and (case is None or case==self.heads[year]):
   n=self.household_net[str(year)]
   m.update(hh_netting=n['pairwise_most'],hh_netting_ratio=n['pairwise_most']/five,
            hh_netting_kept_ratio=n['pairwise_most']/five_kept)
  self._metrics[cache]=m
  return m
