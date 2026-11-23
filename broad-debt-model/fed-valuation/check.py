"""Independent source-to-opening and funded-vector check; imports no builder/model."""
import csv
from fractions import Fraction as F
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'paper-prep/bank-equity'))
import replay


def main():
    report=json.load(gzip.open(HERE/'results.json.gz','rt'))
    for name,h in report['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,('source hash',name)
    raw=json.loads((ROOT/'broad-debt-model/corrected-results.json').read_text())
    key=lambda r:(r['id'],r.get('issuer',r.get('nonbank_foreign_security_issuers')),r['pooled'])
    base={key(r):r for r in raw['records'] if 2021<=r['year']<=2025 and r['securities_repayable']}
    archive=ROOT/'fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip'
    source_manifest=json.loads((archive.parent.parent/'source-manifest.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==source_manifest['sha256']
    tables={}
    z=zipfile.ZipFile(archive)
    def read(t,c,y):
        if t not in tables:tables[t]={r['date']:r for r in csv.DictReader(io.StringIO(z.read('csv/'+t+'.csv').decode()))}
        return int(tables[t][f'{y}:Q4'][c+'.Q'])
    seen=set();steps=0
    for r in report['records']:
        k=key(r);identity=k+(r['policy'],);assert identity not in seen,'duplicate';seen.add(identity)
        old=base[k]['opening'];y=r['year'];v=lambda t,c:read(t,c,y);look=r['representation']=='agency_lookthrough'
        ap=F(v('l211','FL893161705'),v('l211','FL893061705'))
        fa=v('l109','FL713061765');bf=v('l109','FL713061163');assert fa+bf==v('l109','FL714022065')
        original_fa=round(ap*v('l109','LM713061705'))
        cost_mbs=round(F(fa*v('l109','LM713061903'),v('l109','LM713061705')))
        bank_agency=round(ap*v('l110','LM703061705'));us_agency=round(ap*v('l111','LM763061705'))
        us_mbs=sum(v('l111',c) for c in ('LM763061805','LM763061503','LM763061603','LM763061403'))
        allocation=r['id'].split('/')[3]
        share={'minimum':F(0),'maximum':F(1),'observed_us_mix':F(us_mbs,v('l111','LM763061705'))}[allocation]
        bank_mbs=round(ap*us_mbs)+round((bank_agency-us_agency)*share)
        pool=v('l126','FL413065005')+v('l125','FL403065195')+v('l125','FL403065495')
        nb_mbs=pool-bank_mbs-cost_mbs
        nb_agency=v('l211','FL893161705')-bank_agency-fa-round(ap*v('l211','FL313061703'))
        foreign=round(ap*v('l133','LM263061705'))
        foreign_mbs=round(F(foreign*nb_mbs,nb_agency))
        assert r['foreign_mbs']==foreign_mbs
        df=bf-old['bf'];dl=(cost_mbs-old['l_fd']) if look else 0
        dj=fa-original_fa-dl
        shift=foreign_mbs-(old['l_rd']-v('l133','FL263069005')) if look else 0
        expected=dict(old)
        for name,delta in dict(bf=df,d_b=-df,ef=df+fa-original_fa,xf=dj,j_fd=dj,z_fd=dj,
                               l_fd=dl,l_rd=shift,l_dd=-dl-shift,j_rd=-shift,z_rd=-shift,
                               j_dd=-dj+shift,z_dd=-dj+shift).items():expected[name]+=delta
        assert expected==r['opening'],('source projection',identity)
        assert replay.debt(expected)==replay.debt(old),'opening debt changed'
        shares=dict(d=float(r['policy']=='domestic'),r=0.,treasury=0.,central_bank=0.,retained=float(r['policy']=='kept'))
        assert r['policy'] in ('kept','domestic')
        steps+=replay.replay(expected,shares,r['pooled'],True,r['stream'],r['endpoint'],r['kernel'])
    assert seen=={k+(p,) for k in base for p in ('kept','domestic')},'configuration coverage'
    print(f'{len(seen)} raw-source projections and funded streams verified; {steps} steps; full policy coverage.')


if __name__=='__main__':main()
