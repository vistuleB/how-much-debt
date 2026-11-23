"""Isolated ownership-aware payouts using the unchanged broad-debt transaction menu.

Ownership claims are a separate subledger. Existing opening coordinates and
model files are never rewritten. Parent pass-through is a named permission.
"""
import importlib.util
from pathlib import Path
import sys
from math import isfinite

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'broad-debt-model'))
import corrected_model as base
G=base.G
EPS=.001


def validate_shares(shares):
    if not isinstance(shares,dict) or set(shares)!={'d','r','treasury','central_bank','retained'} or any(type(x) not in (int,float) or not isfinite(x) or x<0 for x in shares.values()) or abs(sum(shares.values())-1)>1e-10:
        raise ValueError('ownership weights')


def certificate(v, shares, pooled=False, repayable=True):
    validate_shares(shares)
    c=base.certificate(v,pooled,repayable)
    receipts={g:c['receipts'][g]-(v['eb'] if g=='d' else 0)+v['eb']*shares[g] for g in G}
    quotas={g:min(receipts[g],c['repayable'][g]) for g in G}
    q=min(sum(receipts.values()),sum(c['repayable'].values())) if pooled else sum(quotas.values())
    hc=min(sum(c['treasury_receivables'].values()),q) if pooled else sum(min(quotas[g],c['treasury_receivables'][g]) for g in G)
    reserve=c['prepared_reserve_cap']-v['eb']*(shares['treasury']+shares['central_bank'])
    if reserve < -EPS: raise ValueError('payout cannot be funded from prepared reserves')
    q=min(q,max(0,reserve));hc=min(hc,q)
    redemption=min(base.bonds(v),v['t']+v['qg']+v['eb']*shares['treasury']+hc)
    return dict(receipts=receipts,repayable=c['repayable'],treasury_receivables=c['treasury_receivables'],
                repayment_cap=q,prepared_reserve_cap=reserve,treasury_collection_cap=hc,redemption_cap=redemption,
                lower_bound=base.debt(v)-q-redemption)


class Run(base.Run):
    def __init__(self,v,pooled,repayable,shares):
        super().__init__(v,pooled,repayable)
        validate_shares(shares)
        self.shares=shares;self.entitlements={g:v['eb']*shares[g] for g in shares}
        self.claims=dict(self.entitlements)
    def move(self,kind,*args,**kwargs):
        if kind=='payout':raise ValueError('use the ownership-aware payout, not the legacy domestic payout')
        return super().move(kind,*args,**kwargs)
    def payout(self):
        for target in ('d','r','treasury','central_bank'):
            amount=self.claims[target]
            if amount==0:continue
            before=dict(self.v);w=dict(before)
            w['eb']-=amount
            if target in G:w[target+'_m']+=amount
            elif target=='treasury':w['r']-=amount;w['t']+=amount
            else:w['r']-=amount;w['ef']+=amount
            base.validate(w)
            # Payout extinguishes precisely that holder's bank-equity claim.
            if target in G:
                old=base.net(before,target)-(before['eb'] if target=='d' else 0)+self.claims[target]
                new=base.net(w,target)-(w['eb'] if target=='d' else 0)
                if abs(new-old)>EPS:raise ValueError('owner net position')
            elif target=='treasury':
                if abs(base.treasury(w)-base.treasury(before)-amount)>EPS:raise ValueError('Treasury claim settlement')
            elif abs(w['ef']-before['ef']-amount)>EPS:raise ValueError('Fed claim settlement')
            self.v=w;self.claims[target]=0.
            self.steps.append(dict(kind='ownership_payout',amount=amount,target=target))
        if abs(self.v['eb']-self.entitlements['retained'])>EPS:raise ValueError('retained equity')


def reduce(v, shares, pooled=False, repayable=True):
    r=Run(v,pooled,repayable,shares)
    for g in G:
        for kind,key in [('buy_bond',g+'_b'),('funding',g+'_qbh'),('fed_claim',g+'_qh')]:r.move(kind,r.v[key],g)
        for borrower in G:r.move('buy_loan',r.v['l_'+g+borrower],borrower,g)
    r.move('bank_nondebt_to_fed',r.v['nb']);r.move('bond_to_fed',r.v['bb'])
    for g in G:r.move('loan_to_fed',r.v['l_b'+g],g)
    for h in 'bdr':
        for g in G:
            for asset in ('a','z','excluded'):
                amount=r.v[f'{asset}_{h}{g}'] if asset!='excluded' else max(0,r.v['j_'+h+g]-base.selected(r.v,h,g))
                r.move('claim_to_fed',amount,g,h,asset)
    r.payout()
    r.move('treasury_claim',r.v['qg'])
    def treasury_due(g):return r.v['s_'+g]+r.v['a_t'+g]+(r.v['z_t'+g] if repayable else 0)
    def due(g):return treasury_due(g)+r.v['l_f'+g]+r.v['a_f'+g]+(r.v['z_f'+g] if repayable else 0)
    def repay(g,treasury_only=False):
        r.move('repay_treasury_loan',min(r.v['s_'+g],r.spare(g),max(0,r.v['r'])),g)
        for a in ['a']+(['z'] if repayable else []):r.move('repay_claim',min(r.v[a+'_t'+g],r.spare(g),max(0,r.v['r'])),g,'t',a)
        if not treasury_only:
            r.move('repay_loan',min(r.v['l_f'+g],r.spare(g),max(0,r.v['r'])),g)
            for a in ['a']+(['z'] if repayable else []):r.move('repay_claim',min(r.v[a+'_f'+g],r.spare(g),max(0,r.v['r'])),g,'f',a)
    for g in G:repay(g,True)
    if pooled:
        for g,h in [('r','d'),('d','r')]:r.move('transfer',min(r.spare(g),treasury_due(h)),g,h);repay(h,True)
    for g in G:repay(g)
    if pooled:
        for g,h in [('r','d'),('d','r')]:r.move('transfer',min(r.spare(g),due(h)),g,h);repay(h)
    r.move('redeem',min(r.v['t'],r.v['bf']))
    if abs(base.debt(r.v)-certificate(v,shares,pooled,repayable)['lower_bound'])>EPS:raise ValueError('certificate not attained')
    return r
