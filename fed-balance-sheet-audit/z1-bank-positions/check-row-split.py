#!/usr/bin/env python3
"""Independent standard-library structural, formula and funded-witness audit.

Imports no project code. Uses cut certificates (not the Gleam max-flow code),
reconstructs transaction vectors, and compares merged states to the existing
shared-route report. Source observations are reread from the pinned archive.
"""
import argparse
import copy
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parent
BORDERS=['X1','X2','X3/0','X3/1T','X3/2.5T','X3/5T','X3/10T','X3/infinity','X4']
CAPS=[0,0,0,1000000,2500000,5000000,10000000,math.inf,math.inf]


def flat(record):
    out={}
    for section in ['balances','holdings','positions']:
        for entry in record[section]:
            assert entry['name'] not in out,'duplicate coordinate '+entry['name']
            out[entry['name']]=entry['value']
    return out


def owned(v,holder):return sum(v['j_'+holder+i] for i in 'drt')
def loans(v,g):return sum(v['l_'+h+g] for h in 'bfdr')
def loan_assets(v,g):return sum(v['l_'+g+b] for b in 'dr')
def money(v,g):return v[g+'_m']+v[g+'_ch']
def bonds(v):return v['bb']+v['bf']+v['d_b']+v['r_b']
def debt(v):return bonds(v)+loans(v,'d')+loans(v,'r')
def jtotal(v):return sum(owned(v,h) for h in 'bfdr')
def close(a,b):return abs(a-b)<1e-6


def structural(v):
    expected=set('r t bb bf cb u nb xf nf qg ql eb ef xbr qbr shares_d shares_r'.split())
    expected|={g+'_'+f for g in 'dr' for f in ['m','ch','b','n','qh','qbh']}
    expected|={'l_'+h+g for h in 'bfdr' for g in 'dr'}
    expected|={'j_'+h+i for h in 'bfdr' for i in 'drt'}
    assert v.keys()==expected,'coordinate coverage'
    assert all(type(x) in [int,float] and math.isfinite(x) and (k=='ef' or x>=0) for k,x in v.items()),'invalid amount/sign'
    assert close(v['d_m']+v['r_m']+v['u']+v['eb']+v['d_qbh']+v['r_qbh']+v['qbr'],v['bb']+v['l_bd']+v['l_br']+v['r']+v['cb']+v['nb']+v['xbr']+owned(v,'b')),'bank sheet'
    assert close(v['bf']+v['l_fd']+v['l_fr']+v['u']+v['xf'],sum(v[k] for k in ['r','t','cb','d_ch','r_ch','d_qh','r_qh','qg','ql','ef'])),'Fed sheet'
    assert v['xf']>=v['nf']+owned(v,'f'),'Fed eligible inventory exceeds assets'


def merged(v):
    return dict(balances=dict(m=v['d_m']+v['r_m'],r=v['r'],t=v['t'],b_h=v['d_b']+v['r_b'],b_b=v['bb'],b_f=v['bf'],l_b=v['l_bd']+v['l_br'],l_f=v['l_fd']+v['l_fr'],c_h=v['d_ch']+v['r_ch'],c_b=v['cb'],u=v['u'],n_b=v['nb'],x_f=v['xf'],q_f=v['d_qh']+v['r_qh']+v['qg']+v['ql'],e_b=v['eb'],e_f=v['ef']),
        holdings=dict(n_h=v['d_n']+v['r_n'],n_f=v['nf'],j_h=owned(v,'d')+owned(v,'r'),j_f=owned(v,'f'),q_h=v['d_qh']+v['r_qh'],q_g=v['qg'],l_h=loan_assets(v,'d')+loan_assets(v,'r')),
        positions=dict(j_b=owned(v,'b'),x_b_res=v['xbr'],q_b_h=v['d_qbh']+v['r_qbh'],q_b_res=v['qbr'],q_f_lock=v['ql']))


def shared_state_check(s,v,baseline_snapshot,raw):
    amounts={};aggregate={}
    actor=lambda a:'Nonbank' if a in ['DomesticNonbank','RestOfWorld'] else a
    def add(d,h,i,value):
        key=(h,json.dumps(i,sort_keys=True));d[key]=d.get(key,0)+value
    for p in s['shared_positions']:
        assert p['holder']!='Nonbank','aggregate Nonbank copied alongside subgroups'
        i=p['instrument'];scaled=p['value']*1000
        assert close(scaled,round(scaled)),'off-grid shared source'
        value=round(scaled)
        assert value>=0,'negative shared stock'
        key=(p['holder'],json.dumps(i,sort_keys=True))
        assert key not in amounts,'duplicate shared account'
        amounts[key]=value
        collapsed=copy.deepcopy(i)
        if i['type']=='PrivateLoanTo':
            assert i['borrower'] in ['DomesticNonbank','RestOfWorld'],'invalid refined borrower'
            collapsed={'type':'PrivateLoan'}
        elif i['type']=='OtherClaim':collapsed['debtor']=actor(i['debtor'])
        add(aggregate,actor(p['holder']),collapsed,value)
    expected={}
    for p in baseline_snapshot['positions']:add(expected,p['holder'],p['instrument'],round(p['value']*1000))
    assert {k:x for k,x in aggregate.items() if x}=={k:x for k,x in expected.items() if x},'shared-state aggregation'
    def value(holder,kind,**extra):return amounts.get((holder,json.dumps(dict(type=kind,**extra),sort_keys=True)),0)
    year=s['year'];read=lambda table,code:int(raw[(table,f'{year}:Q4',code+'.Q')])
    foreign_m=read('l203','FL263027003')+read('l204','FL263030005')-read('l109','FL713122605')
    assert value('RestOfWorld','Deposit')==foreign_m,'foreign deposit source'
    assert value('RestOfWorld','Currency')==read('l203','FL263025003'),'foreign currency source'
    foreign_claims=read('l109','FL713122605')+read('l109','FL712151115')
    assert value('RestOfWorld','OtherClaim',name='deposits_and_reverse_repos',debtor='Fed')==foreign_claims,'foreign official pool ownership'
    assert v['r_qh']==foreign_claims,'foreign Fed claim projection'
    assert read('l133','FL263069005')==read('l216','FL263069500')+read('l216','FL263067005'),'named domestic borrowers of foreign-held loans'
    assert value('Treasury','PrivateLoanTo',borrower='RestOfWorld')==read('l216','FL263169203'),'Treasury foreign loan source'
    for group,holder in [('d','DomesticNonbank'),('r','RestOfWorld')]:
        for field,kind in [('m','Deposit'),('ch','Currency'),('b','TreasuryBond')]:
            assert v[group+'_'+field]==value(holder,kind),'subgroup projection '+group+'_'+field
    assert v['l_br']==value('Banks','PrivateLoanTo',borrower='RestOfWorld'),'foreign bank borrower'
    assert v['l_dr']==value('DomesticNonbank','PrivateLoanTo',borrower='RestOfWorld'),'cross-border loan borrower'
    look=s['representation']=='agency_lookthrough'
    assert v['l_rd']==value('RestOfWorld','PrivateLoanTo',borrower='DomesticNonbank')+(value('RestOfWorld','AgencyMortgageSecurity') if look else 0),'foreign loan owner'
    assert v['j_rd']==value('RestOfWorld','OtherClaim',name='other_securities',debtor='DomesticNonbank')+value('RestOfWorld','AgencyBond')+(0 if look else value('RestOfWorld','AgencyMortgageSecurity')),'foreign J ownership'
    assert v['j_dr']==value('DomesticNonbank','OtherClaim',name='other_securities',debtor='RestOfWorld'),'foreign J issuer'
    for h,g in [('Banks','b'),('Fed','f')]:
        assert v['j_'+g+'r']==value(h,'OtherClaim',name='external_financial_claims',debtor='RestOfWorld'),'institution J issuer'


def parameters(key):
    parts=key.split('/')
    return dict(j=parts[0],fixed=parts[1]=='fixed',regime=int(parts[2][1:]),foreign_tax='foreign-taxable' in parts,locked='foreign-claims-locked' in parts)


def formula(v,key,cap):
    p=parameters(key);reg=p['regime'];conv=p['j']=='E1'
    h={g:v[g+'_b']+v[g+'_qbh']+loan_assets(v,g)+(owned(v,g) if conv else 0)+(v[g+'_qh'] if g=='d' or not p['locked'] else 0)+(v['eb'] if g=='d' else 0) for g in 'dr'}
    w=v['t']+v['qg'];b=bonds(v);ld=loans(v,'d');lr=loans(v,'r');d=b+ld+lr
    z=v['xbr']-v['qbr']+(0 if conv else owned(v,'b'))
    sigma=max(0,z-v['u']-money(v,'d')-money(v,'r')) if p['fixed'] else 0
    red=min(w,b) if reg in [3,4] else 0
    spend=w if reg in [1,2] else 0
    sink=b if reg in [1,2] else (b-red if reg==3 else 0)
    # Independent dual form: mandatory debt, global funding, two group cuts.
    mandatory=d-red-(ld+lr+sink)
    pool=max(mandatory,d-red-h['d']-h['r']-spend+sigma)
    cd=d-red-h['d']-lr-(sink if p['foreign_tax'] else 0)-spend
    cr=d-red-h['r']-ld-sink-spend
    incoming_d=math.inf if reg in [1,2] and p['foreign_tax'] else cap
    incoming_r=math.inf if reg in [1,2] else cap
    k=max(pool,cd-incoming_d,cr-incoming_r)
    psi=money(v,'d')+money(v,'r')+h['d']+h['r']+spend+red-d
    return k,psi,sigma


def apply_witness(v,m,p,border):
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
    structural(v)


def verify(report,baseline,source_input,archive,shared_input):
    assert report['border_order']==BORDERS,'border coverage'
    digest=lambda b:hashlib.sha256(b).hexdigest()
    assert report['input_sha256']==digest(source_input.read_bytes()),'ROW input hash'
    inp=json.loads(source_input.read_text());doc=inp['shared_source_input']
    raw={(x['table'],x['date'],x['series']):x['raw'] for x in doc['observations']}
    assert inp['shared_input_sha256']==digest(shared_input.read_bytes()),'shared input hash'
    assert report['source_sha256']==doc['source_sha256']==digest(archive.read_bytes()),'archive hash'
    with zipfile.ZipFile(archive) as z:
        tables={}
        for x in doc['observations']:
            t=x['table']
            if t not in tables:tables[t]={r['date']:r for r in csv.DictReader(io.StringIO(z.read('csv/'+t+'.csv').decode('utf-8-sig')))}
            assert tables[t][x['date']][x['series']]==x['raw'],x
    refs={x['id']:x for x in baseline['projections']}
    snapshots={x['id']:x for x in baseline['snapshots']}
    states={x['id']:x for x in report['scenarios']}
    assert len(states)==len(report['scenarios']) and states.keys()==refs.keys(),'scenario coverage'
    series_count=0;witness_steps=0
    expected_keys={f'{j}/{f}/R{r}' for j in ['E1','E3'] for f in ['fixed','additional'] for r in range(1,6)}
    expected_keys|={f'{j}/fixed/R3/{v}' for j in ['E1','E3'] for v in ['foreign-taxable','foreign-claims-locked']}
    for sid,s in states.items():
        try:
            v=flat(s['state']);structural(v)
            choice_id=sid.replace('/'+s['representation'],'')
            shared_state_check(s,v,snapshots[choice_id],raw)
            assert merged(v)==s['merged']==refs[sid]['state'],'merged coordinate mismatch'
            assert {x['key'] for x in s['results']}==expected_keys and len(s['results'])==len(expected_keys),'policy coverage'
            for data in s['results']:
                assert all(len(data[k])==len(CAPS) for k in ['kernels','debts','bonds','loans_d','loans_r','money_d','money_r','shares_d','shares_r','steps']),'border vector coverage'
                for idx,cap in enumerate(CAPS):
                    k,psi,sigma=formula(v,data['key'],cap)
                    assert close(k,data['kernels'][idx]) and close(k,data['debts'][idx]),data['key']+': kernel/debt'
                    assert close(psi,data['psi']) and close(sigma,data['sigma']),data['key']+': potential/funding'
                    assert close(k,data['bonds'][idx]+data['loans_d'][idx]+data['loans_r'][idx]),'debt composition'
                    assert data['money_d'][idx]>=money(v,'d') and data['money_r'][idx]>=money(v,'r'),'endpoint money floor'
                    assert close(data['money_d'][idx]+data['money_r'][idx]-k,psi),'attained potential'
                    assert data['shares_d'][idx]<=cap and data['shares_r'][idx]<=cap,'equity capacity'
                    series_count+=1
                assert data['kernels']==sorted(data['kernels'],reverse=True),'capacity monotonicity'
                assert data['kernels'][0]==data['kernels'][1]==data['kernels'][2],'X1/X2/zero capacity'
                p=parameters(data['key'])
                block='convertible' if p['j']=='E1' else 'not_convertible'
                offset=0 if p['fixed'] else 10
                old_k=refs[sid][block]['kernels'][offset+p['regime']-1]
                if not p['locked']:assert close(data['kernels'][-1],old_k),'predecessor consistency'
                else:assert data['kernels'][-1]>=old_k,'locked-claim ordering'
        except (AssertionError,KeyError,ValueError) as exc:raise AssertionError(sid+': '+str(exc)) from None
    for w in report['witnesses']:
        sid=w['id']
        try:
            opening=flat(states[sid]['state']);v=copy.deepcopy(opening);p=parameters(w['key']);idx=BORDERS.index(w['border']);cap=CAPS[idx]
            for move in w['moves']:
                apply_witness(v,move,p,w['border'])
                for g in 'dr':
                    assert money(v,g)>=money(opening,g),'intermediate money floor '+g
                    assert v[g+'_n']>=opening[g+'_n'],'intermediate N floor '+g
                    assert v['shares_'+g]-opening['shares_'+g]<=cap,'cumulative equity capacity '+g
                witness_steps+=1
            assert v==flat(w['endpoint']),'stored endpoint mismatch'
            assert close(debt(v),formula(opening,w['key'],cap)[0]),'witness not attaining'
        except (AssertionError,KeyError,ValueError) as exc:raise AssertionError(sid+' '+w['key']+' '+w['border']+': '+str(exc)) from None
    return dict(states=len(states),kernel_configurations_checked=series_count,stored_witnesses=len(report['witnesses']),independently_replayed_steps=witness_steps,raw_observations=len(doc['observations']),problems=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'row-split/check.json')
    parser.add_argument('--baseline',type=Path,default=ROOT/'real-world/check.json')
    args=parser.parse_args()
    try:
        summary=verify(json.loads(args.report.read_text()),json.loads(args.baseline.read_text()),ROOT/'row-split/input.json',ROOT/'raw/z1-20260319-csv.zip',ROOT/'real-world/input.json')
        print(json.dumps(summary));return 0
    except (AssertionError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps(dict(problems=1,detail=str(exc))));return 1


if __name__=='__main__':raise SystemExit(main())
