"""Broad-debt prototype. USD millions; inherited opening coordinates remain fixed.

The J inventory is deliberately called 'selected claims', not 'securities': its
source composition includes funding claims and requires classification review.
"""
from math import isfinite

GROUPS = 'dr'
TOL = 1e-3

def owned(v, h): return sum(v['j_'+h+i] for i in 'drt')
def issued(v, i): return sum(v['j_'+h+i] for h in 'bfdr')
def bonds(v): return v['bb']+v['bf']+v['d_b']+v['r_b']
def loans(v, g): return sum(v['l_'+h+g] for h in 'bfdr')
def debt(v): return bonds(v)+sum(loans(v,g)+issued(v,g)+v['s_'+g] for g in GROUPS)+issued(v,'t')
def treasury(v): return v['t']+v['qg']+v['s_d']+v['s_r']-bonds(v)
def net(v,g):
    return v[g+'_m']+v[g+'_ch']+v[g+'_b']+v[g+'_qh']+v[g+'_qbh']+owned(v,g)+sum(v['l_'+g+b] for b in GROUPS)-loans(v,g)-issued(v,g)-v['s_'+g]

def validate(v):
    if any(not isfinite(x) or (k!='ef' and x < -TOL) for k,x in v.items()): raise ValueError('nonfinite or negative position')
    bank=v['bb']+sum(v[k] for k in ['l_bd','l_br','r','cb','nb','xbr'])+owned(v,'b')-sum(v[k] for k in ['d_m','r_m','u','eb','d_qbh','r_qbh','qbr'])
    fed=sum(v[k] for k in ['bf','l_fd','l_fr','u','xf'])-sum(v[k] for k in ['r','t','cb','d_ch','r_ch','d_qh','r_qh','qg','ql','ef'])
    if abs(bank)>TOL or abs(fed)>TOL or v['xf']+TOL<v['nf']+owned(v,'f'): raise ValueError('balance sheet or inventory')

class Run:
    def __init__(self,v,pooled=False,securities_repayable=True):
        validate(v); self.v=dict(v); self.opening=dict(v); self.pooled=pooled
        self.repayable=securities_repayable; self.steps=[]
    def move(self,kind,a,g=None,h=None):
        if not isfinite(a) or a<0: raise ValueError('amount')
        if a==0:return
        if g is not None and g not in GROUPS: raise ValueError('group')
        if h is not None and h not in GROUPS: raise ValueError('group')
        rules={
          'buy_bond':{f'{g}_b':-1,'bb':1,f'{g}_m':1},
          'buy_loan':{f'l_{g}{h}':-1,f'l_b{h}':1,f'{g}_m':1},
          'funding':{f'{g}_qbh':-1,f'{g}_m':1},
          'fed_claim':{f'{g}_qh':-1,'r':1,f'{g}_m':1},
          'payout':{'eb':-1,'d_m':1},
          'bond_to_fed':{'bb':-1,'bf':1,'r':1},
          'loan_to_fed':{f'l_b{g}':-1,f'l_f{g}':1,'r':1},
          'nonbank_claim_to_fed':{f'j_{g}{h}':-1,f'j_f{h}':1,'xf':1,'r':1,f'{g}_m':1},
          'bank_claim_to_fed':{f'j_b{g}':-1,f'j_f{g}':1,'xf':1,'r':1},
          'treasury_claim':{'qg':-1,'t':1},
          'repay_loan':{f'l_f{g}':-1,f'{g}_m':-1,'r':-1},
          'treasury_buys_bank_loan':{f'l_b{g}':-1,f's_{g}':1,'t':-1,'r':1},
          'repay_treasury':{f's_{g}':-1,f'{g}_m':-1,'r':-1,'t':1},
          'repay_claim':{f'j_f{g}':-1,'xf':-1,f'{g}_m':-1,'r':-1},
          'redeem':{'bf':-1,'t':-1},
          'transfer':{f'{g}_m':-1,f'{h}_m':1},
        }
        if kind not in rules or (kind=='transfer' and (not self.pooled or g==h)) or (kind=='repay_claim' and not self.repayable): raise ValueError('permission')
        w=dict(self.v)
        for k,c in rules[kind].items(): w[k]+=c*a
        validate(w)
        diffs=[w[x+'_m']-self.opening[x+'_m'] for x in GROUPS]
        if (sum(diffs)<-TOL if self.pooled else min(diffs)<-TOL):raise ValueError('money floor')
        if abs(treasury(w)-treasury(self.opening))>TOL:raise ValueError('Treasury net position')
        # Payouts convert bank equity into domestic deposits; attribute initial equity.
        for x in GROUPS:
            before=net(self.v,x)+(self.v['eb'] if x=='d' else 0)
            after=net(w,x)+(w['eb'] if x=='d' else 0)
            if kind!='transfer' and abs(after-before)>TOL:raise ValueError('nonbank net position')
        self.v=w;self.steps.append(dict(kind=kind,amount=a,g=g,h=h))
    def spare(self,g):return max(0,self.v[g+'_m']-self.opening[g+'_m'])

def reduce(v,pooled=False,securities_repayable=True):
    r=Run(v,pooled,securities_repayable)
    for g in GROUPS:
        for kind,key in [('buy_bond',g+'_b'),('funding',g+'_qbh'),('fed_claim',g+'_qh')]:r.move(kind,r.v[key],g)
        for h in GROUPS:
            r.move('buy_loan',r.v['l_'+g+h],g,h)
            if securities_repayable:r.move('nonbank_claim_to_fed',r.v['j_'+g+h],g,h)
    r.move('payout',r.v['eb']);r.move('bond_to_fed',r.v['bb'])
    for g in GROUPS:
        r.move('loan_to_fed',r.v['l_b'+g],g)
        if securities_repayable:r.move('bank_claim_to_fed',r.v['j_b'+g],g)
    r.move('treasury_claim',r.v['qg'])
    def repay(g):
        for kind,key in [('repay_treasury','s_'+g),('repay_loan','l_f'+g)]+([('repay_claim','j_f'+g)] if securities_repayable else []):r.move(kind,min(r.v[key],r.spare(g)),g)
    for g in 'rd':repay(g)
    if pooled:
        for g,h in [('r','d'),('d','r')]:
            due=r.v['s_'+h]+r.v['l_f'+h]+(r.v['j_f'+h] if securities_repayable else 0)
            r.move('transfer',min(r.spare(g),due),g,h);repay(h)
    r.move('redeem',min(r.v['t'],r.v['bf']))
    return r
