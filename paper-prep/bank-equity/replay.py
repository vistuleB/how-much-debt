"""Independent payout/vector and household-resource replay. Imports no model code."""
import math

EPS=.002
G='dr'
H='bfdrt'


def close(a,b,label):
    if abs(a-b)>EPS:raise ValueError((label,a,b))


def owned(v,h):return sum(v['j_'+h+g] for g in G)
def bonds(v):return sum(v[k] for k in ('bb','bf','d_b','r_b'))
def loans(v,g):return sum(v['l_'+h+g] for h in 'bfdr')
def securities(v,g):return sum(v['z_'+h+g] for h in H)
def debt(v):return bonds(v)+sum(loans(v,g)+v['s_'+g]+sum(v[a+'_'+h+g] for a in ('a','z') for h in H) for g in G)
def treasury(v):return v['t']+v['qg']+v['s_d']+v['s_r']+owned(v,'t')-bonds(v)
def net(v,g):return sum(v[g+'_'+k] for k in ('m','ch','b','qh','qbh'))+owned(v,g)+sum(v['l_'+g+h] for h in G)-loans(v,g)-v['s_'+g]-sum(v[a+'_'+h+g] for a in ('a','z') for h in H)


def valid(v):
    if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not math.isfinite(x) or (k!='ef' and x < -EPS) for k,x in v.items()):raise ValueError('invalid coordinate')
    close(v['bb']+sum(v[k] for k in ('l_bd','l_br','r','cb','nb','xbr'))+owned(v,'b'),sum(v[k] for k in ('d_m','r_m','u','eb','d_qbh','r_qbh','qbr')),'bank sheet')
    close(sum(v[k] for k in ('bf','l_fd','l_fr','u','xf')),sum(v[k] for k in ('r','t','cb','d_ch','r_ch','d_qh','r_qh','qg','ql','ef')),'central bank sheet')
    if v['xf']+EPS<v['nf']+owned(v,'f'):raise ValueError('Fed inventory')
    for h in H:
        for g in G:
            if v['a_'+h+g]+v['z_'+h+g]>v['j_'+h+g]+EPS:raise ValueError('selected inventory')


def formula(v,shares,pooled,repayable):
    sale={g:sum(v[g+'_'+k] for k in ('b','qh','qbh'))+owned(v,g)+sum(v['l_'+g+h] for h in G)+shares[g]*v['eb'] for g in G}
    due={g:loans(v,g)+v['s_'+g]+sum(v['a_'+h+g]+(v['z_'+h+g] if repayable else 0) for h in H) for g in G}
    tc={g:v['s_'+g]+v['a_t'+g]+(v['z_t'+g] if repayable else 0) for g in G}
    cap=v['r']+v['nb']+v['bb']+sum(v[g+'_b']+v[g+'_qh'] for g in G)+sum(v['l_'+h+g]+v['j_'+h+g] for h in 'bdr' for g in G)-v['eb']*(shares['treasury']+shares['central_bank'])
    q=min(cap,min(sum(sale.values()),sum(due.values())) if pooled else sum(min(sale[g],due[g]) for g in G))
    collected=min(q,sum(tc.values()) if pooled else sum(min(tc[g],sale[g],due[g]) for g in G))
    return debt(v)-q-min(bonds(v),v['t']+v['qg']+shares['treasury']*v['eb']+collected)


def replay(v,shares,pooled,repayable,stream,endpoint,kernel):
    v=dict(v);opening=dict(v)
    if set(shares)!={'d','r','treasury','central_bank','retained'} or any(type(x) not in (int,float) or not math.isfinite(x) or x<0 for x in shares.values()) or abs(sum(shares.values())-1)>1e-10:raise ValueError('weights')
    claims={k:v['eb']*s for k,s in shares.items()};paid=set();valid(v)
    original={g:net(v,g)+claims[g] for g in G};tn=treasury(v)+claims['treasury'];fn=v['ef']+claims['central_bank']
    for step in stream:
        kind=step['kind'];a=step['amount'];g=step.get('g');h=step.get('h');asset=step.get('asset')
        expected={'kind','amount','target'} if kind=='ownership_payout' else {'kind','amount','g','h','asset'}
        if set(step)!=expected:raise ValueError('transaction fields')
        if not isinstance(a,(int,float)) or isinstance(a,bool) or not math.isfinite(a) or a<=0:raise ValueError('transaction amount')
        if kind=='ownership_payout':
            target=step.get('target')
            if target not in ('d','r','treasury','central_bank') or target in paid:raise ValueError('payout recipient/repetition')
            close(a,claims[target],'entitlement');paid.add(target);claims[target]=0
            delta={'eb':-a}
            if target in G:delta[target+'_m']=a
            else:
                delta['r']=-a;delta['t' if target=='treasury' else 'ef']=a
        else:
            # Shapes are checked independently instead of trusting supplied deltas.
            simple={'buy_bond','funding','fed_claim','loan_to_fed','repay_loan','repay_treasury_loan'}
            if kind in simple and (g not in G or h is not None or asset is not None):raise ValueError('simple parameters')
            rules={
              'buy_bond':{f'{g}_b':-1,'bb':1,f'{g}_m':1},
              'buy_loan':{f'l_{h}{g}':-1,f'l_b{g}':1,f'{h}_m':1},
              'funding':{f'{g}_qbh':-1,f'{g}_m':1},
              'fed_claim':{f'{g}_qh':-1,'r':1,f'{g}_m':1},
              'bank_nondebt_to_fed':{'nb':-1,'nf':1,'xf':1,'r':1},
              'bond_to_fed':{'bb':-1,'bf':1,'r':1},
              'loan_to_fed':{f'l_b{g}':-1,f'l_f{g}':1,'r':1},
              'treasury_claim':{'qg':-1,'t':1},
              'repay_loan':{f'l_f{g}':-1,f'{g}_m':-1,'r':-1},
              'repay_treasury_loan':{f's_{g}':-1,f'{g}_m':-1,'r':-1,'t':1},
              'redeem':{'bf':-1,'t':-1},
              'transfer':{f'{g}_m':-1,f'{h}_m':1}}
            if kind=='transfer' and (not pooled or g not in G or h not in G or g==h):raise ValueError('transfer permission')
            if kind=='buy_loan' and (g not in G or h not in G or asset is not None):raise ValueError('seller')
            if kind in ('claim_to_fed','repay_claim'):
                if g not in G:raise ValueError('borrower')
                if kind=='claim_to_fed':
                    if h not in 'bdr' or asset not in ('a','z','excluded'):raise ValueError('claim sale')
                    available=v['j_'+h+g]-v['a_'+h+g]-v['z_'+h+g] if asset=='excluded' else v[asset+'_'+h+g]
                    if a>available+EPS:raise ValueError('claim source')
                    rules[kind]={f'j_{h}{g}':-1,f'j_f{g}':1,'xf':1,'r':1}
                    if h in G:rules[kind][h+'_m']=1
                    if asset!='excluded':rules[kind].update({f'{asset}_{h}{g}':-1,f'{asset}_f{g}':1})
                else:
                    if h not in ('f','t') or asset not in ('a','z') or (asset=='z' and not repayable):raise ValueError('claim repayment')
                    rules[kind]={f'j_{h}{g}':-1,f'{asset}_{h}{g}':-1,f'{g}_m':-1,'r':-1,('xf' if h=='f' else 't'):(-1 if h=='f' else 1)}
            if kind not in rules:raise ValueError('unknown transaction')
            delta={k:c*a for k,c in rules[kind].items()}
        for k,d in delta.items():v[k]+=d
        valid(v)
        differences=[v[g+'_m']-opening[g+'_m'] for g in G]
        if (sum(differences) if pooled else min(differences)) < -EPS:raise ValueError('money floor')
        if pooled:close(sum(net(v,g)+claims[g] for g in G),sum(original.values()),'pooled wealth')
        else:
            for g in G:close(net(v,g)+claims[g],original[g],'protected wealth')
        close(treasury(v)+claims['treasury'],tn,'Treasury wealth')
        close(v['ef']+claims['central_bank'],fn,'Fed wealth')
        close(sum(claims.values()),v['eb'],'equity claims')
    if any(abs(v[k]-endpoint[k])>EPS for k in v):raise ValueError('endpoint')
    close(debt(v),kernel,'endpoint debt');close(formula(opening,shares,pooled,repayable),kernel,'independent formula')
    for target in ('d','r','treasury','central_bank'):close(claims[target],0,'unpaid entitlement')
    return len(stream)


def household_replay(parts,B,W,rho,payout,stream,kernel,D,treasury_sells):
    money={g:0. for g in parts};owed={g:p['o'] for g,p in parts.items()};held={g:p['s'] for g,p in parts.items()}
    cash=W-sum(held.values());repaid=0.;remaining=B;claims=dict(payout);seen_sales=set()
    assets={g:p['c'] for g,p in parts.items()}
    wealth={g:assets[g]-owed[g]+claims[g] for g in parts}
    treasury_wealth=W-B+claims['treasury']
    for step in stream:
        if set(step)!={'kind','group','amount'}:raise ValueError('household transaction fields')
        kind,g,a=step['kind'],step.get('group'),step['amount']
        if type(a) not in (int,float) or not math.isfinite(a) or a<0:raise ValueError('household amount')
        if kind=='sell_receipts':
            if g in seen_sales:raise ValueError('duplicate receipts')
            close(a,parts[g]['c'],'sale receipts');seen_sales.add(g);money[g]+=a;assets[g]-=a
        elif kind=='payout':
            close(a,claims[g],'household entitlement');claims[g]=0
            if g in parts:money[g]+=a
            elif g=='treasury':cash+=a;rho-=a
            elif g=='central_bank':rho-=a
            else:raise ValueError('recipient')
        elif kind=='repay_treasury':
            if a>held[g]+EPS:raise ValueError('Treasury inventory')
            held[g]-=a;owed[g]-=a;money[g]-=a;rho-=a;cash+=a;repaid+=a
        elif kind=='repay_other':
            if a>owed[g]-held[g]+EPS:raise ValueError('debt inventory')
            owed[g]-=a;money[g]-=a;rho-=a;repaid+=a
        elif kind=='sell_treasury_claims':
            if not treasury_sells:raise ValueError('Treasury sale permission')
            close(a,sum(held.values()),'Treasury sale');cash+=a;held=dict.fromkeys(held,0.)
        elif kind=='redeem':cash-=a;remaining-=a;repaid+=a
        else:raise ValueError('household kind')
        if min(money.values()) < -EPS or rho < -EPS or cash < -EPS or remaining < -EPS or min(owed.values()) < -EPS:raise ValueError('household funding')
        for group in parts:close(money[group]+assets[group]-owed[group]+claims[group],wealth[group],'household protected net position')
        close(cash+sum(held.values())-remaining+claims['treasury'],treasury_wealth,'household Treasury net position')
    close(D-repaid,kernel,'household endpoint')
    if any(claims.values()):raise ValueError('unpaid household entitlement')
    if treasury_sells:
        floor=max(0,B-W-payout['treasury'])
        independent=floor+sum(max(0,p['o']-p['c']-payout[g]) for g,p in parts.items())
        close(independent,kernel,'household formula')
    return len(stream)
