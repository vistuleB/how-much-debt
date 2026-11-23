"""Fed-only cost sensitivity for the current instrument-split model; new outputs.

python3 -I broad-debt-model/fed-valuation/build.py [--check]
"""
import gzip
import hashlib
import json
from fractions import Fraction
from pathlib import Path
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];BASE=ROOT/'fed-balance-sheet-audit/z1-bank-positions'
sys.path.insert(0,str(ROOT/'paper-prep/bank-equity'))
import payout_model as model
import replay
INPUTS=['broad-debt-model/corrected-results.json','broad-debt-model/equity-kept-results.json',
        'fed-balance-sheet-audit/z1-bank-positions/row-split/check.json',
        'fed-balance-sheet-audit/z1-bank-positions/row-split/input.json',
        'fed-balance-sheet-audit/z1-bank-positions/valuation-sensitivity/check.json',
        'fed-balance-sheet-audit/z1-bank-positions/valuation-sensitivity/input.json']


def changed_opening(rec,case,narrow,shared,partition):
    v=dict(rec['opening']);old=case['merged'];new=narrow['state'];look=rec['representation']=='agency_lookthrough'
    def delta(section,name):return new[section][name]-old[section][name]
    v['bf']+=delta('balances','b_f');v['d_b']+=delta('balances','b_h')
    v['ef']+=delta('balances','e_f');v['xf']+=delta('balances','x_f');v['nf']+=delta('holdings','n_f')
    v['j_fd']+=delta('holdings','j_f');v['z_fd']+=delta('holdings','j_f')
    v['l_fd']+=delta('balances','l_f')
    def holding(kind):return sum(round(x['value']*1000) for x in shared['positions'] if x['holder']=='Nonbank' and x['instrument']['type']==kind)
    public_agency=holding('AgencyBond')+holding('AgencyMortgageSecurity');public_mbs=holding('AgencyMortgageSecurity')
    foreign_mbs=round(Fraction(partition['foreign_agency']*public_mbs,public_agency))
    shift=foreign_mbs-partition['foreign_mbs'] if look else 0
    v['l_rd']+=shift
    v['l_dd']+=delta('holdings','l_h')-shift
    v['j_rd']-=shift;v['z_rd']-=shift
    v['j_dd']+=delta('holdings','j_h')+shift;v['z_dd']+=delta('holdings','j_h')+shift
    model.base.validate(v)
    if v['r_b']!=rec['opening']['r_b']:raise ValueError('foreign Treasury amount changed')
    if v['eb']!=rec['opening']['eb']:raise ValueError('bank equity changed')
    if model.base.bonds(v)!=model.base.bonds(rec['opening']):raise ValueError('Treasury face changed')
    if model.base.debt(v)!=rec['opening_debt']:raise ValueError('selected opening debt changed')
    return v,foreign_mbs


def build():
    raw={p:(ROOT/p).read_bytes() for p in INPUTS};data={p:json.loads(v) for p,v in raw.items()}
    prior={r['id']:r for r in data[INPUTS[2]]['scenarios']}
    part={r['id']:r['partition'] for r in data[INPUTS[3]]['partitions']}
    narrow={r['id'].replace('/fed_amortized_cost',''):r for r in data[INPUTS[4]]['projections']}
    shared={r['id'].replace('/fed_amortized_cost',''):r for r in data[INPUTS[5]]['cases']}
    key=lambda r:(r['id'],r['pooled'],r['securities_repayable'],r['nonbank_foreign_security_issuers'])
    kept={key(r):r for f in data[INPUTS[1]]['families'] for r in f['report']['records']}
    rows=[];steps=0
    for rec in data[INPUTS[0]]['records']:
        if rec['year'] not in range(2021,2026) or not rec['securities_repayable']:continue
        ident=rec['id'];prefix=ident.replace('/agency_lookthrough','').replace('/security_outside_D','')
        opening,foreign_mbs=changed_opening(rec,prior[ident],narrow[ident],shared[prefix],part[prefix])
        for policy in ('kept','domestic'):
            shares=dict(d=float(policy=='domestic'),r=0.,treasury=0.,central_bank=0.,retained=float(policy=='kept'))
            r=model.reduce(opening,shares,rec['pooled'],True);k=model.base.debt(r.v)
            replay.replay(opening,shares,rec['pooled'],True,r.steps,r.v,k);steps+=len(r.steps)
            baseline=rec if policy=='domestic' else kept[key(rec)]
            rows.append(dict(id=ident,year=rec['year'],representation=rec['representation'],
                             issuer=rec['nonbank_foreign_security_issuers'],policy=policy,pooled=rec['pooled'],
                             opening=opening,endpoint=r.v,stream=r.steps,kernel=k,
                             baseline_kernel=baseline['kernel'],baseline_ef=rec['opening']['ef'],
                             ef_change=opening['ef']-rec['opening']['ef'],kernel_change=k-baseline['kernel'],
                             foreign_mbs=foreign_mbs))
    report=dict(format_version=1,unit='USD millions',scope='Existing Fed-only amortized-cost rule; instrument-split nonbank debt; securities repayable; separate dated openings, not transactions between valuations.',
                source_sha256={p:hashlib.sha256(v).hexdigest() for p,v in raw.items()},records=rows)
    verification=dict(records=len(rows),steps=steps,years=sorted({r['year'] for r in rows}),all_attained=True,
                      opening_debt_unchanged=True,bank_equity_unchanged=True)
    return report,verification


if __name__=='__main__':
    report,verification=build();encoded=(json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode()
    outputs={'results.json.gz':gzip.compress(encoded,mtime=0),'verification.json':(json.dumps(verification,sort_keys=True,indent=2)+'\n').encode()}
    for name,data in outputs.items():
        p=HERE/name
        if '--check' in sys.argv:
            # Compare content, not gzip framing: the gzip header's OS byte differs between Python versions.
            stored=p.read_bytes()
            assert (gzip.decompress(stored)==encoded if name.endswith('.gz') else stored==data),'stale '+name
        else:p.write_bytes(data)
    print(json.dumps(verification,sort_keys=True))
