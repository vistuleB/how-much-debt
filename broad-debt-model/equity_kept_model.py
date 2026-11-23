"""Bank-equity-kept experiment, copied from corrected_model.py on 2026-11-23.

Same moves and invariants except payouts are prohibited. Existing modules and
outputs are unchanged. Bank equity is fixed at every intermediate state.

J remains the financial-asset book. Its nonnegative a (additional loan) and
z (security) subinventories identify selected nonbank debt. The remainder is
excluded from D but keeps the old acquisition permissions. t holds Treasury
securities, separate from s_g federal loans. No interest or new issuance.
"""
from math import isfinite
from model import validate as institutional_sheets, bonds, loans, TOL
G=('d','r');H=('b','f','d','r','t')
COORDINATES=set('bb bf cb eb ef nb nf qbr qg ql r t u xbr xf shares_d shares_r'.split())
COORDINATES.update(g+'_'+k for g in G for k in ['m','ch','b','n','qbh','qh'])
COORDINATES.update('l_'+h+g for h in 'bfdr' for g in G)
COORDINATES.update('j_'+h+g for h in 'bfdr' for g in 'drt')
COORDINATES.update('j_t'+g for g in G)
COORDINATES.update('s_'+g for g in G)
COORDINATES.update(a+'_'+h+g for a in ['a','z'] for h in H for g in G)
def owned(v,h):return sum(v['j_'+h+g] for g in G)
def selected(v,h,g):return v['a_'+h+g]+v['z_'+h+g]
def issued(v,g):return sum(selected(v,h,g) for h in H)
def debt(v):return bonds(v)+sum(loans(v,g)+v['s_'+g]+issued(v,g) for g in G)
def treasury(v):return v['t']+v['qg']+sum(v['s_'+g] for g in G)+owned(v,'t')-bonds(v)
def net(v,g):
 return v[g+'_m']+v[g+'_ch']+v[g+'_b']+v[g+'_qh']+v[g+'_qbh']+owned(v,g)+sum(v['l_'+g+b] for b in G)-loans(v,g)-v['s_'+g]-issued(v,g)+(v['eb'] if g=='d' else 0)
def validate(v):
 if set(v)!=COORDINATES or any(type(x) not in [int,float] for x in v.values()):raise ValueError('state coordinates or number type')
 institutional_sheets(v)
 if any(v['j_'+h+'t']!=0 for h in 'bfdr') or v.get('shares_d',0)!=0 or v.get('shares_r',0)!=0:raise ValueError('outside successor experiment profile')
 for h in H:
  for g in G:
   if selected(v,h,g)>v['j_'+h+g]+TOL:raise ValueError('selected debt exceeds financial inventory')
def certificate(v,pooled=False,securities_repayable=True):
 validate(v)
 if type(pooled) is not bool or type(securities_repayable) is not bool:raise ValueError('policy')
 receipts={g:v[g+'_b']+v[g+'_qh']+v[g+'_qbh']+owned(v,g)+sum(v['l_'+g+b] for b in G) for g in G}
 due={g:loans(v,g)+v['s_'+g]+sum(v['a_'+h+g]+(v['z_'+h+g] if securities_repayable else 0) for h in H) for g in G}
 to_treasury={g:v['s_'+g]+v['a_t'+g]+(v['z_t'+g] if securities_repayable else 0) for g in G}
 if pooled:
  q=min(sum(receipts.values()),sum(due.values()));collect=min(sum(to_treasury.values()),q)
 else:
  quotas={g:min(receipts[g],due[g]) for g in G};q=sum(quotas.values());collect=sum(min(quotas[g],to_treasury[g]) for g in G)
 reserve_cap=v['r']+v['nb']+v['bb']+sum(v[g+'_b']+v[g+'_qh'] for g in G)+sum(v['l_'+h+g] for h in 'bdr' for g in G)+sum(owned(v,h) for h in 'bdr')
 q=min(q,reserve_cap);collect=min(collect,q)
 redeemed=min(bonds(v),v['t']+v['qg']+collect)
 return dict(receipts=receipts,repayable=due,treasury_receivables=to_treasury,repayment_cap=q,prepared_reserve_cap=reserve_cap,treasury_collection_cap=collect,redemption_cap=redeemed,lower_bound=debt(v)-q-redeemed)
class Run:
 def __init__(self,v,pooled=False,securities_repayable=True):
  validate(v)
  if type(pooled) is not bool or type(securities_repayable) is not bool:raise ValueError('policy')
  self.v=dict(v);self.opening=dict(v);self.pooled=pooled;self.repayable=securities_repayable;self.steps=[]
 def spare(self,g):return max(0,self.v[g+'_m']-self.opening[g+'_m'])
 def move(self,kind,a,g=None,h=None,asset=None):
  if isinstance(a,bool) or not isinstance(a,(int,float)) or not isfinite(a) or a<0:raise ValueError('amount')
  if g is not None and g not in G:raise ValueError('group')
  if h is not None and h not in {'b','f','d','r','t'}:raise ValueError('holder')
  if asset is not None and asset not in ['a','z','excluded']:raise ValueError('instrument')
  simple={'buy_bond','funding','fed_claim','loan_to_fed','repay_loan','repay_treasury_loan'}
  global_rules={'payout','bank_nondebt_to_fed','bond_to_fed','treasury_claim','redeem'}
  if kind not in simple|global_rules|{'buy_loan','claim_to_fed','repay_claim','transfer'}:raise ValueError('unknown transaction')
  if kind in simple and ((g is None or g not in G) or h is not None or asset is not None):raise ValueError('parameters')
  if kind in global_rules and (g is not None or h is not None or asset is not None):raise ValueError('parameters')
  if kind=='buy_loan' and ((g is None or g not in G) or (h is None or h not in G) or asset is not None):raise ValueError('loan parameters')
  if kind=='claim_to_fed' and ((g is None or g not in G) or (h is None or h not in {'b','d','r'}) or asset not in ['a','z','excluded']):raise ValueError('claim parameters')
  if kind=='repay_claim' and ((g is None or g not in G) or (h is None or h not in {'f','t'}) or asset not in ['a','z'] or asset=='z' and not self.repayable):raise ValueError('repayment permission')
  if kind=='transfer' and (not self.pooled or (g is None or g not in G) or (h is None or h not in G) or g==h or asset is not None):raise ValueError('transfer parameters')
  if kind=='payout':raise ValueError('bank equity kept: payout prohibited')
  if a==0:return
  rules={
   'buy_bond':{f'{g}_b':-1,'bb':1,f'{g}_m':1},
   'buy_loan':{f'l_{h}{g}':-1,f'l_b{g}':1,f'{h}_m':1},
   'funding':{f'{g}_qbh':-1,f'{g}_m':1},
   'fed_claim':{f'{g}_qh':-1,'r':1,f'{g}_m':1},
   'bank_nondebt_to_fed':{'nb':-1,'nf':1,'xf':1,'r':1},
   'payout':{'eb':-1,'d_m':1},'bond_to_fed':{'bb':-1,'bf':1,'r':1},
   'loan_to_fed':{f'l_b{g}':-1,f'l_f{g}':1,'r':1},
   'treasury_claim':{'qg':-1,'t':1},
   'repay_loan':{f'l_f{g}':-1,f'{g}_m':-1,'r':-1},
   'repay_treasury_loan':{f's_{g}':-1,f'{g}_m':-1,'r':-1,'t':1},
   'redeem':{'bf':-1,'t':-1},
   'transfer':{f'{g}_m':-1,f'{h}_m':1},
  }
  if kind=='claim_to_fed':
   if h not in {'b','d','r'}:raise ValueError('seller')
   key=f'j_{h}{g}'
   cap=self.v[key]-selected(self.v,h,g) if asset=='excluded' else self.v[f'{asset}_{h}{g}'] if asset in ['a','z'] else -1
   if a>cap+TOL:raise ValueError('claim inventory')
   changes={key:-1,f'j_f{g}':1,'xf':1,'r':1}
   if h in G:changes[f'{h}_m']=1
   if asset!='excluded':changes.update({f'{asset}_{h}{g}':-1,f'{asset}_f{g}':1})
  elif kind=='repay_claim':
   if h not in {'f','t'} or asset not in ['a','z'] or (asset=='z' and not self.repayable):raise ValueError('repayment permission')
   changes={f'j_{h}{g}':-1,f'{asset}_{h}{g}':-1,f'{g}_m':-1,'r':-1}
   changes['xf' if h=='f' else 't']=-1 if h=='f' else 1
  else:
   if kind not in rules:raise ValueError('unknown transaction')
   if kind=='buy_loan' and h not in G:raise ValueError('loan seller')
   if kind=='transfer' and (not self.pooled or h not in G or h==g):raise ValueError('transfer permission')
   changes=rules[kind]
  w=dict(self.v)
  for k,c in changes.items():w[k]+=c*a
  validate(w)
  if w['eb']!=self.opening['eb'] or w['ef']!=self.opening['ef']:raise ValueError('institutional equity changed')
  diffs=[w[x+'_m']-self.opening[x+'_m'] for x in G]
  if (sum(diffs)<-TOL if self.pooled else min(diffs)<-TOL):raise ValueError('money floor')
  if abs(treasury(w)-treasury(self.v))>TOL:raise ValueError('Treasury net position')
  nd=[net(w,x)-net(self.v,x) for x in G]
  if (abs(sum(nd))>TOL if kind=='transfer' else max(map(abs,nd))>TOL):raise ValueError('nonbank net position')
  self.v=w;self.steps.append(dict(kind=kind,amount=a,g=g,h=h,asset=asset))
def reduce(v,pooled=False,securities_repayable=True):
 r=Run(v,pooled,securities_repayable)
 for g in G:
  for kind,key in [('buy_bond',g+'_b'),('funding',g+'_qbh'),('fed_claim',g+'_qh')]:r.move(kind,r.v[key],g)
  for borrower in G:r.move('buy_loan',r.v['l_'+g+borrower],borrower,g)
 r.move('bank_nondebt_to_fed',r.v['nb']);r.move('bond_to_fed',r.v['bb'])
 for g in G:r.move('loan_to_fed',r.v['l_b'+g],g)
 for h in 'bdr':
  for g in G:
   for asset in ['a','z','excluded']:
    amount=r.v[f'{asset}_{h}{g}'] if asset!='excluded' else max(0,r.v['j_'+h+g]-selected(r.v,h,g))
    r.move('claim_to_fed',amount,g,h,asset)
 r.move('treasury_claim',r.v['qg'])
 def treasury_due(g):return r.v['s_'+g]+r.v['a_t'+g]+(r.v['z_t'+g] if securities_repayable else 0)
 def due(g):return treasury_due(g)+r.v['l_f'+g]+r.v['a_f'+g]+(r.v['z_f'+g] if securities_repayable else 0)
 def repay(g,treasury_only=False):
  r.move('repay_treasury_loan',min(r.v['s_'+g],r.spare(g),max(0,r.v['r'])),g)
  for asset in ['a']+(['z'] if securities_repayable else []):r.move('repay_claim',min(r.v[asset+'_t'+g],r.spare(g),max(0,r.v['r'])),g,'t',asset)
  if not treasury_only:
   r.move('repay_loan',min(r.v['l_f'+g],r.spare(g),max(0,r.v['r'])),g)
   for asset in ['a']+(['z'] if securities_repayable else []):r.move('repay_claim',min(r.v[asset+'_f'+g],r.spare(g),max(0,r.v['r'])),g,'f',asset)
 # Under pooling, pay Treasury claims across BOTH groups before other claims.
 for g in G:repay(g,True)
 if pooled:
  for g,h in [('r','d'),('d','r')]:r.move('transfer',min(r.spare(g),treasury_due(h)),g,h);repay(h,True)
 for g in G:repay(g)
 if pooled:
  for g,h in [('r','d'),('d','r')]:r.move('transfer',min(r.spare(g),due(h)),g,h);repay(h)
 r.move('redeem',min(r.v['t'],r.v['bf']))
 return r
