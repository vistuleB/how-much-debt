"""Independent bank-equity-kept source/vector replay. Copy of corrected_check.py
with payouts prohibited and fixed bank/Fed equity verified at every step.
Imports no project modules. Run: python3 -I broad-debt-model/equity_kept_check.py
Supports --self-test.
"""
import copy,csv,hashlib,io,itertools,json,math,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=Path(__file__).parent
SOURCE=ROOT/'fed-balance-sheet-audit/z1-bank-positions/row-split/check.json'
ZIP=ROOT/'fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip'
EPS=.001

def check(report,source_path=SOURCE):
 raw=Path(source_path).read_bytes();archive=ZIP.read_bytes()
 assert report['source_sha256']==hashlib.sha256(raw).hexdigest(),'source fingerprint'
 assert report['archive_sha256']==hashlib.sha256(archive).hexdigest(),'archive fingerprint'
 assert report['issuer_completion']=='inherited_nonbank_bank_security_funding'
 assert report['federal_borrower_completion']=='domestic_except_observed_FL263169203'
 assert report['foreign_reserve_security_completion']=='foreign_nonbank_sovereign'
 assert report['intercompany_policy']=='outside_L208_L214_instrument_perimeter_signed_L223_retained_in_excluded_inventory'
 assert report['unit']=='USD millions'
 cases={c['id']:c for c in json.loads(raw)['scenarios']};seen=set();steps=0
 z=zipfile.ZipFile(io.BytesIO(archive));tables={}
 def source(t,c,y):
  if t not in tables:tables[t]={r['date']:r for r in csv.DictReader(io.StringIO(z.read('csv/'+t+'.csv').decode('utf-8-sig')))}
  return int(tables[t][f'{y}:Q4'][c+'.Q'])
 def close(a,b):assert abs(a-b)<=EPS,(a,b)
 def own(v,h):return v['j_'+h+'d']+v['j_'+h+'r']
 def B(v):return sum(v[k] for k in ['bb','bf','d_b','r_b'])
 def L(v,g):return sum(v['l_'+h+g] for h in 'bfdr')
 def K(v,g):return sum(v[a+'_'+h+g] for a in ['a','z'] for h in 'bfdrt')
 def D(v):return B(v)+sum(L(v,g)+K(v,g)+v['s_'+g] for g in 'dr')
 def T(v):return v['t']+v['qg']+v['s_d']+v['s_r']+own(v,'t')-B(v)
 def N(v,g):return sum(v[g+'_'+k] for k in ['m','ch','b','qh','qbh'])+own(v,g)+sum(v['l_'+g+b] for b in 'dr')-L(v,g)-K(v,g)-v['s_'+g]+(v['eb'] if g=='d' else 0)
 def valid(v):
  assert all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and (k=='ef' or x>=-EPS) for k,x in v.items()),'position sign/type'
  close(v['bb']+sum(v[k] for k in ['l_bd','l_br','r','cb','nb','xbr'])+own(v,'b'),sum(v[k] for k in ['d_m','r_m','u','eb','d_qbh','r_qbh','qbr']))
  close(sum(v[k] for k in ['bf','l_fd','l_fr','u','xf']),sum(v[k] for k in ['r','t','cb','d_ch','r_ch','d_qh','r_qh','qg','ql','ef']))
  assert v['xf']+EPS>=v['nf']+own(v,'f'),'Fed inventory'
  for h in 'bfdrt':
   for g in 'dr':assert v['a_'+h+g]+v['z_'+h+g]<=v['j_'+h+g]+EPS,'selected inventory'
 for rec in report['records']:
  ident=(rec['id'],rec['pooled'],rec['securities_repayable'],rec['nonbank_foreign_security_issuers']);assert ident not in seen,'duplicate';seen.add(ident)
  assert type(rec['pooled']) is bool and type(rec['securities_repayable']) is bool
  case=cases[rec['id']];year=case['year'];assert rec['year']==year and rec['representation']==case['representation']
  src=lambda t,c:source(t,c,year)
  expected={a['name']:a['value'] for group in ['balances','holdings','positions'] for a in case['state'][group]}
  old=dict(expected)
  for g in 'dr':expected['s_'+g]=src('l216','FL263169203') if g=='r' else src('l106','FL314023005')-src('l216','FL263169203');expected['j_t'+g]=0
  for h,g in itertools.product('bfdrt','dr'):
   expected['a_'+h+g]=expected['z_'+h+g]=0
  excluded_bank=src('l110','FL403197033')+src('l110','FL702050005')+src('l110','FL763040005')
  # All old foreign bank J is interbank/net direct investment under the
  # explicitly inherited placement; domestic remainder is selected securities.
  expected['z_bd']=old['j_bd']-excluded_bank
  for h,g in itertools.product('dr','dr'):expected['z_'+h+g]=expected['j_'+h+g]
  assert rec['nonbank_foreign_security_issuers'] in ['nonbank','bank']
  if rec['nonbank_foreign_security_issuers']=='bank':expected['z_dr']=0
  expected['z_fr']=src('l109','FL713011525');expected['a_fd']=src('l109','FL713068005')
  repo=src('l109','FL712051005');contra=max(0,-repo)
  expected_corrections=[] if not contra else [dict(source='FL712051005.Q',amount=contra,changes=['j_fd +amount','xf +amount','ql +amount'],reason='Gross signed negative repo asset into existing locked Fed liabilities; equity unchanged')]
  assert rec['corrections']==expected_corrections
  for key in ['j_fd','xf','ql']:expected[key]+=contra
  expected['z_fd']=expected['j_fd']-expected['a_fd']-max(0,repo)
  expected['z_td']=expected['j_td']=sum(round(p['value']*1000) for p in case['shared_positions'] if p['holder']=='Treasury' and p['instrument']['type']=='AgencyBond')
  expected['z_tr']=expected['j_tr']=src('l106','FL313063005')
  assert expected==rec['opening'],('projection',rec['id'])
  v=dict(expected);valid(v);pooled=rec['pooled'];repay=rec['securities_repayable']
  # Independently derive resource ceilings rather than read the certificate.
  cash={g:sum(v[g+'_'+k] for k in ['b','qh','qbh'])+own(v,g)+v['l_'+g+'d']+v['l_'+g+'r'] for g in 'dr'}
  due={g:L(v,g)+v['s_'+g]+sum(v['a_'+h+g]+(v['z_'+h+g] if repay else 0) for h in 'bfdrt') for g in 'dr'}
  st={g:v['s_'+g]+v['a_t'+g]+(v['z_t'+g] if repay else 0) for g in 'dr'}
  q=min(sum(cash.values()),sum(due.values())) if pooled else sum(min(cash[g],due[g]) for g in 'dr')
  hc=min(sum(st.values()),q) if pooled else sum(min(st[g],cash[g],due[g]) for g in 'dr')
  reserves=v['r']+v['nb']+v['bb']+sum(v[g+'_b']+v[g+'_qh'] for g in 'dr')+sum(v['l_'+h+g]+v['j_'+h+g] for h in 'bdr' for g in 'dr')
  q=min(q,reserves);hc=min(hc,q);red=min(B(v),v['t']+v['qg']+hc);floor=D(v)-q-red
  stored=rec['certificate'];assert stored['receipts']==cash and stored['repayable']==due and stored['treasury_receivables']==st
  for k,x in [('repayment_cap',q),('prepared_reserve_cap',reserves),('treasury_collection_cap',hc),('redemption_cap',red),('lower_bound',floor)]:close(stored[k],x)
  assert rec['signed_debt_receipt_gap']=={g:L(v,g)+v['s_'+g]+K(v,g)-cash[g] for g in 'dr'}
  close(rec['opening_debt'],D(v))
  for tx in rec['stream']:
   name,a,g,h,asset=(tx[k] for k in ['kind','amount','g','h','asset'])
   assert type(a) in [int,float] and math.isfinite(a) and a>=0
   assert g is None or g in 'dr';assert h is None or h in 'bfdrt'
   delta={}
   def add(key,x):delta[key]=delta.get(key,0)+x
   if name=='buy_bond':add(g+'_b',-1);add('bb',1);add(g+'_m',1)
   elif name=='buy_loan':
    assert h in 'dr';add('l_'+h+g,-1);add('l_b'+g,1);add(h+'_m',1)
   elif name=='funding':add(g+'_qbh',-1);add(g+'_m',1)
   elif name=='fed_claim':add(g+'_qh',-1);add('r',1);add(g+'_m',1)
   elif name=='bank_nondebt_to_fed':add('nb',-1);add('nf',1);add('xf',1);add('r',1)
   elif name=='payout':raise AssertionError('payout prohibited')
   elif name=='bond_to_fed':add('bb',-1);add('bf',1);add('r',1)
   elif name=='loan_to_fed':add('l_b'+g,-1);add('l_f'+g,1);add('r',1)
   elif name=='treasury_claim':add('qg',-1);add('t',1)
   elif name=='claim_to_fed':
    assert h in 'bdr' and asset in ['a','z','excluded']
    cap=v['j_'+h+g]-v['a_'+h+g]-v['z_'+h+g] if asset=='excluded' else v[asset+'_'+h+g]
    assert a<=cap+EPS
    add('j_'+h+g,-1);add('j_f'+g,1);add('xf',1);add('r',1)
    if h in 'dr':add(h+'_m',1)
    if asset!='excluded':add(asset+'_'+h+g,-1);add(asset+'_f'+g,1)
   elif name in ['repay_loan','repay_treasury_loan']:
    add(('l_f' if name=='repay_loan' else 's_')+g,-1);add(g+'_m',-1);add('r',-1)
    if name=='repay_treasury_loan':add('t',1)
   elif name=='repay_claim':
    assert h in 'ft' and (asset=='a' or asset=='z' and repay)
    add('j_'+h+g,-1);add(asset+'_'+h+g,-1);add(g+'_m',-1);add('r',-1);add('xf' if h=='f' else 't',-1 if h=='f' else 1)
   elif name=='transfer':
    assert pooled and h in 'dr' and h!=g;add(g+'_m',-1);add(h+'_m',1)
   elif name=='redeem':add('bf',-1);add('t',-1)
   else:raise AssertionError('unlisted transaction')
   before=[N(v,x) for x in 'dr'];tn=T(v)
   for k,sign in delta.items():v[k]+=sign*a
   valid(v);close(T(v),tn)
   close(v['eb'],expected['eb']);close(v['ef'],expected['ef'])
   if name=='transfer':close(N(v,'d')+N(v,'r'),sum(before))
   else:
    for x,n in zip('dr',before):close(N(v,x),n)
   changes=[v[x+'_m']-expected[x+'_m'] for x in 'dr']
   assert (sum(changes) if pooled else min(changes))>=-EPS,'floor'
   steps+=1
  assert v==rec['endpoint'],'endpoint'
  close(D(v),rec['kernel']);close(D(v),floor)
 assert seen==set(itertools.product(cases,[False,True],[False,True],['nonbank','bank'])),'missing configuration'
 return dict(records=len(seen),replayed_steps=steps,problems=0)


def check_all(document):
 assert document['policy']=='bank_equity_kept'
 seen=set();totals=dict(records=0,replayed_steps=0,problems=0)
 for family in document['families']:
  path=family['baseline_path'];assert path not in seen;seen.add(path)
  baseline=ROOT/path
  assert hashlib.sha256(baseline.read_bytes()).hexdigest()==family['baseline_sha256'],'baseline fingerprint'
  result=check(family['report'],ROOT/family['source_path'])
  for k in totals:totals[k]+=result[k]
 assert seen=={'broad-debt-model/corrected-results.json',
  'fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json',
  'fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json'},'families'
 return totals


if __name__=='__main__':
 document=json.loads((P/'equity-kept-results.json').read_text())
 print(json.dumps(check_all(document),sort_keys=True))
 if '--self-test' in sys.argv:
  mutations=[
   ('kernel',lambda d:d['families'][0]['report']['records'][0].update(kernel=-1)),
   ('bank equity',lambda d:d['families'][0]['report']['records'][0]['endpoint'].update(eb=0)),
   ('payout',lambda d:d['families'][0]['report']['records'][0]['stream'].insert(0,dict(kind='payout',amount=1,g=None,h=None,asset=None))),
   ('missing family',lambda d:d['families'].pop()),
   ('missing record',lambda d:d['families'][0]['report']['records'].pop()),
   ('duplicate record',lambda d:d['families'][0]['report']['records'].__setitem__(1,d['families'][0]['report']['records'][0])),
   ('opening coordinate',lambda d:d['families'][0]['report']['records'][0]['opening'].update(d_m=0)),
   ('step amount',lambda d:d['families'][0]['report']['records'][0]['stream'][0].update(amount=-1)),
   ('baseline fingerprint',lambda d:d['families'][0].update(baseline_sha256='bad'))]
  for name,mutate in mutations:
   bad=copy.deepcopy(document);mutate(bad)
   try:check_all(bad)
   except (AssertionError,ValueError,KeyError):continue
   raise AssertionError('corruption escaped: '+name)
  print(f'{len(mutations)} corruptions rejected')
