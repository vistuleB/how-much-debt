#!/usr/bin/env python3
"""Standard-library check of restrictive formulas and stored funded witnesses.
No project imports; implements the six admitted vector families independently.
This implementation check does not replace an independent mathematical review.
"""
import argparse, copy, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
TOL=1e-6

def flat(s):
    pairs=[(e['name'],e['value']) for group in ['balances','holdings','positions'] for e in s[group]]
    assert len(dict(pairs))==len(pairs),'duplicate coordinate'
    return dict(pairs)
def near(a,b):return abs(a-b)<TOL
def money(s,g):return s[g+'_m']+s[g+'_ch']
def owned(s,g):return sum(s['l_'+g+b] for b in 'dr')
def owed(s,g):return sum(s['l_'+h+g] for h in 'bfdr')
def bonds(s):return sum(s[k] for k in ['bb','bf','d_b','r_b'])
def debt(s):return bonds(s)+sum(owed(s,g) for g in 'dr')
def net(s,g):
    other='r' if g=='d' else 'd'
    return money(s,g)+sum(s[g+'_'+f] for f in ['b','n','qh','qbh'])+owned(s,g)+sum(s['j_'+g+i] for i in 'drt')+s['shares_'+other]-owed(s,g)-sum(s['j_'+h+g] for h in 'bfdr')-s['shares_'+g]
def valid(s):
    assert all(isinstance(v,(int,float)) and math.isfinite(v) and (k=='ef' or v>=-TOL) for k,v in s.items()),'sign/finite'
    jb=sum(s['j_b'+i] for i in 'drt');jf=sum(s['j_f'+i] for i in 'drt')
    assert near(s['bb']+s['l_bd']+s['l_br']+s['r']+s['cb']+s['nb']+s['xbr']+jb,s['d_m']+s['r_m']+s['u']+s['eb']+s['d_qbh']+s['r_qbh']+s['qbr']),'bank sheet'
    assert near(s['bf']+s['l_fd']+s['l_fr']+s['u']+s['xf'],sum(s[k] for k in ['r','t','cb','d_ch','r_ch','d_qh','r_qh','qg','ql','ef'])),'Fed sheet'
    assert s['xf']+TOL>=s['nf']+jf,'Fed inventory'
def capacities(s,menu,share):
    return {g:s[g+'_b']+owned(s,g)+(s[g+'_qbh']+s['eb']*(share if g=='r' else 1-share) if menu=='five' else 0) for g in 'dr'}
def formula(s,menu,central,share,pooled=False):
    c=capacities(s,menu,share)
    if pooled:
        c={'p':sum(c.values())};l={'p':sum(owed(s,g) for g in 'dr')};f={'p':s['l_fd']+s['l_fr']}
    else:l={g:owed(s,g) for g in 'dr'};f={g:s['l_f'+g] for g in 'dr'}
    # Two lower certificates: group money budgets and bank-debt+reserve cap.
    resource_bound=sum(max(0,l[g]-c[g]) for g in c)
    frozen=sum(f.values())+sum(max(0,l[g]-f[g]-c[g]) for g in c)
    return bonds(s)+(frozen if central=='F3' else max(resource_bound,frozen-s['r']))
def check_row(record,parent):
    v=flat(parent['state'])
    # Named counterfactual changes borrower, not holder/principal or any sheet.
    if record['borrower']=='whole_foreign':amount=v['l_rd']
    elif record['borrower']=='direct_foreign':amount=record['_direct_amount'];assert amount>=0
    else:assert record['borrower']=='observed';amount=0
    v['l_rd']-=amount;v['l_rr']+=amount;s=v
    valid(s);opening=copy.deepcopy(s)
    k=formula(s,record['menu'],record['central_bank'],record['foreign_share'])
    assert near(k,record['kernel']),'reported kernel'
    changed={'bb','d_m','r_m','d_b','r_b','l_bd','l_br','l_dd','l_dr','l_rd','l_rr'}
    if record['menu']=='five':changed|={'eb','d_qbh','r_qbh'}
    if record['central_bank']!='F3':changed|={'r','l_fd','l_fr'}
    for move in record['moves']:
        a=move['amount'];assert math.isfinite(a) and a>=0,'move amount'
        x=move['action'].split('/');delta={}
        if x[0]=='nonbank' and x[1]=='BondToBank':g=x[2];delta={g+'_b':-a,'bb':a,g+'_m':a}
        elif x[0]=='nonbank-loan' and x[1]=='LoanToBank':g,b=x[2];delta={'l_'+g+b:-a,'l_b'+b:a,g+'_m':a}
        elif x[0]=='loan' and x[1]=='RepayBank':g=x[2];delta={'l_b'+g:-a,g+'_m':-a}
        elif x[0]=='loan' and x[1]=='RepayFed':
            assert record['central_bank']!='F3','Fed loan repayment not permitted'
            g=x[2];delta={'l_f'+g:-a,g+'_m':-a,'r':-a}
        elif x[0]=='nonbank' and x[1]=='FundingRepaid':
            assert record['menu']=='five','funding repayment not permitted';g=x[2];delta={g+'_qbh':-a,g+'_m':a}
        elif x[0]=='wage':
            assert record['menu']=='five','equity payout not permitted';share=move['foreign_share'];assert share==record['foreign_share'];delta={'eb':-a,'d_m':a*(1-share),'r_m':a*share}
        else:raise AssertionError('move outside whitelist: '+move['action'])
        for key,value in delta.items():s[key]+=value
        valid(s)
        assert all(near(s[key],opening[key]) for key in s if key not in changed),'fixed coordinate'
        for g in 'dr':
            assert money(s,g)+TOL>=money(opening,g),'group money floor'
            weight=record['foreign_share'] if g=='r' else 1-record['foreign_share']
            assert near(net(s,g)+weight*s['eb'],net(opening,g)+weight*opening['eb']),'attributed group net position'
            if record['menu']=='three':assert near(net(s,g),net(opening,g)),'group net position'
    assert near(debt(s),k),'attainment'
    assert near(record['bonds'],bonds(s)) and near(record['fed_loans'],s['l_fd']+s['l_fr']),'surviving debt composition'
    assert near(record['other_loans'],debt(s)-bonds(s)-s['l_fd']-s['l_fr']),'other surviving loans'
    # Independent replay on the pooled original state (borrower reassignment merges out).
    p=copy.deepcopy(parent['merged']);start=p['balances']['m']+p['balances']['c_h'];b=p['balances'];h=p['holdings'];pos=p['positions']
    opening_net=start+b['b_h']-b['l_b']-b['l_f']+pos['q_b_h']+b['e_b']
    for move in record['pooled_moves']:
        a=move['amount'];assert a>=0 and math.isfinite(a)
        kind=move['action']
        if kind=='BankBuysNonbankBond':b['b_h']-=a;b['b_b']+=a;b['m']+=a
        elif kind=='BankBuysNonbankLoan':h['l_h']-=a;b['l_b']+=a;b['m']+=a
        elif kind=='BankRepaysNonbankFunding':assert record['menu']=='five';pos['q_b_h']-=a;b['m']+=a
        elif kind=='Wage':assert record['menu']=='five';b['e_b']-=a;b['m']+=a
        elif kind=='Repay':b['l_b']-=a;b['m']-=a
        elif kind=='RepayFedLoan':assert record['central_bank']!='F3';b['l_f']-=a;b['r']-=a;b['m']-=a
        else:raise AssertionError('pooled move outside whitelist')
        assert b['m']+b['c_h']+TOL>=start,'pooled floor'
        assert near(b['m']+b['c_h']+b['b_h']-b['l_b']-b['l_f']+pos['q_b_h']+b['e_b'],opening_net),'pooled net position'
        assert all(v>=-TOL for key,v in b.items() if key!='e_f') and all(v>=-TOL for v in h.values()) and all(v>=-TOL for v in pos.values()),'pooled funding'
        assert near(b['b_b']+b['l_b']+b['r']+b['c_b']+b['n_b']+pos['j_b']+pos['x_b_res'],b['m']+b['u']+b['e_b']+pos['q_b_h']+pos['q_b_res']),'pooled bank sheet'
        assert near(b['b_f']+b['l_f']+b['u']+b['x_f'],b['r']+b['t']+b['c_b']+b['c_h']+b['q_f']+b['e_f']),'pooled Fed sheet'
    pk=formula(opening,record['menu'],record['central_bank'],record['foreign_share'],True)
    assert near(pk,record['pooled_kernel']),'pooled formula'
    assert near(pk,b['b_h']+b['b_b']+b['b_f']+b['l_b']+b['l_f']+h['l_h']),'pooled attained'
    return len(record['moves'])+len(record['pooled_moves'])
# Existing F1/R3/E3 witness vectors, independently executed here.
def apply_general(v,m,p,border):
    a=m['amount'];assert math.isfinite(a) and a>=0,'invalid move amount'
    parts=m['action'].split('/');kind=parts[0];rule=parts[1] if len(parts)>1 else ''
    d={}
    def add(k,x):d[k]=d.get(k,0)+x
    if kind=='shared':
        table={
          'BankNonDebtToFed':{'nb':-a,'nf':a,'xf':a,'r':a},
          'TreasuryClaimSettled':{'qg':-a,'t':a},'VaultToReserves':{'cb':-a,'r':a},
          'BankBondToFed':{'bb':-a,'bf':a,'r':a},'RedeemFed':{'bf':-a,'t':-a},'Advance':{'u':a,'r':a}}
        assert rule in table,'unsupported/forbidden shared witness move'
        assert rule!='Advance' or not p['fixed'],'fixed advances'
        assert rule!='RedeemFed' or p['regime']!=5,'Treasury redemption not permitted'
        d=table[rule]
    elif kind=='nonbank':
        g=parts[2];assert g in 'dr'
        if rule=='FundingRepaid':d={g+'_qbh':-a,g+'_m':a}
        elif rule=='FedClaimSettled':
            assert g!='r' or not p['locked'],'locked foreign Fed claim'
            d={g+'_qh':-a,'r':a,g+'_m':a}
        elif rule=='DepositCash':d={g+'_ch':-a,'cb':a,g+'_m':a}
        elif rule=='BondToBank':d={g+'_b':-a,'bb':a,g+'_m':a}
        elif rule=='Spend':
            assert p['regime'] in [1,2],'spending forbidden'
            d={'t':-a,'r':a,g+'_m':a}
        elif rule=='Tax':
            assert p['regime'] in [1,2,3] and (g=='d' or p['foreign_tax']),'tax forbidden'
            d={'t':a,'r':-a,g+'_m':-a}
        else:raise AssertionError('unsupported nonbank witness rule')
    elif kind=='loan':
        g=parts[2]
        if rule=='BankLoanToFed':d={'l_b'+g:-a,'l_f'+g:a,'r':a}
        elif rule=='RepayFed':d={'l_f'+g:-a,g+'_m':-a,'r':-a}
        else:raise AssertionError('unsupported loan witness rule')
    elif kind=='nonbank-loan':
        assert rule=='LoanToBank'
        h,b=parts[2];d={'l_'+h+b:-a,'l_b'+b:a,h+'_m':a}
    elif kind=='j':
        assert p['j']=='E1','J conversion not permitted'
        g,i=parts[2]
        if rule=='BankJToFed':d={'j_b'+i:-a,'j_f'+i:a,'xf':a,'r':a}
        elif rule=='NonbankJToFed':d={'j_'+g+i:-a,'j_f'+i:a,'xf':a,'r':a,g+'_m':a}
        else:raise AssertionError('unsupported J witness rule')
    elif kind=='wage':
        assert m['foreign_share']==0,'unexpected payout policy'
        d={'eb':-a,'d_m':a}
    elif kind=='issue-equity':
        assert border.startswith('X3/') or border=='X4','equity forbidden'
        g=rule;other='r' if g=='d' else 'd';d={'shares_'+g:a,g+'_m':a,other+'_m':-a}
    elif kind=='transfer':
        assert border=='X4','transfer forbidden'
        g=rule;other='r' if g=='d' else 'd';d={g+'_m':-a,other+'_m':a}
    else:raise AssertionError('unknown witness action '+m['action'])
    for k,x in d.items():v[k]+=x
    valid(v)


def verify(path,source):
    report=json.loads(path.read_text());raw=source.read_bytes();parents=json.loads(raw)
    assert report['format_version']==2
    assert report['source_sha256']==hashlib.sha256(raw).hexdigest(),'parent hash'
    states={x['id']:x for x in parents['scenarios']};seen=set();steps=0;results={}
    source_input=json.loads((source.parent/'input.json').read_text())
    direct={p['id']:p['partition']['foreign_owned_loans'] for p in source_input['partitions']}
    for r in report['records']:
        key=(r['id'],r['borrower'],r['menu'],r['central_bank'],r['foreign_share'])
        assert key not in seen,'duplicate configuration';seen.add(key)
        r['_direct_amount']=direct[r['id'].replace('/'+r['representation'],'')]
        try:steps+=check_row(r,states[r['id']])
        except (AssertionError,KeyError,ValueError) as e:raise AssertionError(str(key)+': '+str(e)) from None
        results[key]=r['kernel']
    expected={(sid,borrower,menu,central,share) for sid in states for borrower in ['observed','direct_foreign','whole_foreign'] for menu in ['three','five'] for central in ['F1','F2','F3'] for share in ([0] if menu=='three' else [0,1])}
    assert seen==expected,'configuration coverage'
    for (sid,borrower,menu,central,share),value in results.items():
        assert near(value,results[sid,borrower,menu,('F2' if central=='F1' else central),share]),'menu F1=F2'
        if central=='F2':assert value<=results[sid,borrower,menu,'F3',share]+TOL,'Fed ordering'
        if menu=='five':assert value<=results[sid,borrower,'three',central,0]+TOL,'menu ordering'
    counter_seen=set()
    for c in report['counterfactuals']:
        key=(c['id'],c['borrower']);assert key not in counter_seen;counter_seen.add(key)
        parent=states[c['id']];v=flat(parent['state'])
        amount=0 if c['borrower']=='observed' else v['l_rd'] if c['borrower']=='whole_foreign' else direct[c['id'].replace('/'+parent['representation'],'')]
        v['l_rd']-=amount;v['l_rr']+=amount;opening=copy.deepcopy(v)
        h={g:v[g+'_b']+owned(v,g)+v[g+'_qbh']+v[g+'_qh']+(v['eb'] if g=='d' else 0) for g in 'dr'}
        b=bonds(v);total=debt(v);ld=owed(v,'d');lr=owed(v,'r');red=min(v['t']+v['qg'],b);sink=b-red
        sigma=max(0,v['xbr']-v['qbr']+sum(v['j_b'+i] for i in 'drt')-v['u']-money(v,'d')-money(v,'r'))
        expected=max(0,total-red-h['d']-h['r']+sigma,total-red-h['d']-lr,total-red-h['r']-ld-sink)
        assert near(expected,c['kernel']),'counterfactual formula'
        for move in c['moves']:
            apply_general(v,move,dict(fixed=True,j='E3',regime=3,foreign_tax=False,locked=False),'X1')
            for g in 'dr':
                assert money(v,g)+TOL>=money(opening,g),'counterfactual money floor'
                assert v[g+'_n']+TOL>=opening[g+'_n'],'counterfactual non-debt floor'
            steps+=1
        assert v==flat(c['endpoint']) and near(debt(v),c['kernel']),'counterfactual attainment'
    assert len(counter_seen)==len(states)*3,'counterfactual coverage'
    return dict(states=len(states),configurations=len(seen),counterfactuals=len(counter_seen),replayed_steps=steps,problems=0)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path,default=ROOT/'row-split/restrictive-check.json');parser.add_argument('--source',type=Path,default=ROOT/'row-split/check.json');a=parser.parse_args()
    try:print(json.dumps(verify(a.report,a.source)));return 0
    except (AssertionError,KeyError,ValueError,TypeError) as e:print(json.dumps(dict(problems=1,detail=str(e))));return 1
if __name__=='__main__':raise SystemExit(main())
