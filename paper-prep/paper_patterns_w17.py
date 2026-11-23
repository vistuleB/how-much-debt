"""W17 headline and wording checks; legacy W16 evaluation remains unchanged."""
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];PAPER=ROOT/'codex-auditor/W17/paper.md';EPS=1e-8


def load(name,path):
    s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def evaluate(data=None):
    legacy=load('w17_legacy_patterns','paper-prep/paper_patterns.py');d=data or legacy.profiles.Data()
    replaced={'Treasury share greater than half in every year/completion from 2009','domestic term minimum over all years/completions','domestic term maximum over all years/completions'}
    out=[dict(c,scope='retained W16 support/named-policy check') for c in legacy.evaluate(d) if c['claim'] not in replaced]
    def truth(name,value,detail=None):out.append(dict(claim=name,passed=bool(value),actual=detail if detail is not None else bool(value),expected=True,scope='W17'))
    def exact(name,value,expected):out.append(dict(claim=name,passed=value==expected,actual=value,expected=expected,scope='W17'))
    rows=[r for r in d.records if r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank' and r['securities_repayable'] and not r['pooled']]
    metrics=[d.metrics(r['year'],payout=False,case=legacy.profiles.completion(r)) for r in rows]
    truth('W17 Treasury share exceeds half in every completion from 2010',all(x['treasury_share_pct']>50 for r,x in zip(rows,metrics) if r['year']>=2010))
    exact('W17 domestic term rounded range',[f'{min(x["dom"] for x in metrics):.1f}',f'{max(x["dom"] for x in metrics):.1f}'],['4.5','11.4'])
    truth('W17 domestic term positive in every year/completion',all(x['dom']>0 for x in metrics))
    truth('W17 foreign term zero in every year/completion',all(abs(x['foreign_term'])<EPS for x in metrics))
    exact('W17 kept pooled money-binding years',sorted({r['year'] for r,x in zip(rows,metrics) if x['pooled_lead']>EPS}),list(range(2001,2010))+list(range(2014,2018)))
    head={y:d.metrics(y,payout=False) for y in d.years}
    hh={y:x['hh_one']-x['kernel'] for y,x in head.items()};wealth={y:x['hh_five']-x['hh_one'] for y,x in head.items()}
    exact('W17 household line larger years',[y for y in d.years if hh[y]>wealth[y]+EPS],list(range(2001,2007))+list(range(2021,2026)))
    exact('W17 wealth line larger years',[y for y in d.years if wealth[y]>hh[y]+EPS],list(range(2007,2021)))
    for issuer in ('nonbank','bank'):
        truth('W17 pooled money leads before 2009, issuer '+issuer,all(d.metrics(y,issuer=issuer,payout=False)['pooled_lead']>EPS for y in range(2001,2009)))
    for y in d.years:
        ks=[x['kernel'] for r,x in zip(rows,metrics) if r['year']==y]
        truth(f'W17 kept kernel equal across completions {y}',max(ks)-min(ks)<EPS)
    out.extend(load('w17_fed_patterns','paper-prep/fed_valuation_checks_w17.py').patterns())
    out.extend(load('w17_netting_completion_patterns','paper-prep/netting_completions_w17.py').patterns())
    if PAPER.exists():
        text=PAPER.read_text()
        fragments={
          'W17 headline keeps both equities':'with bank and central-bank equity also maintained',
          'W17 table keeps equity in headline':'Kernel, banks pay out equity',
          'W17 early repayment permission named':'if nonbank securities can be repaid before maturity',
          'W17 household Treasury permission disclosed':'the split kernel lets the Treasury sell its loans',
          'W17 household remainder exceptions disclosed':'every year except 2015 and 2017',
          'W17 wealth/household ranking stated':'Neither line dominates.',
          'W17 numerical valuation convention disclosed':'the central bank included, although its own books value its securities at amortized cost',
          'W17 threshold scale wording':'minus $14 trillion',
          'W17 Fed cost equity range disclosed':'at amortized cost it would lie between −$0.18 trillion and +$0.06 trillion',
          'W17 nonrepayable netting retirement range stated':'netting offsetting claims retires 43% to 63% in the first case and 20% to 31% in the second',
          'W17 Fed cost sensitivity disclosed':"would raise its equity, and with it the kernel with the sectors separate, by $0.06–0.58 trillion in 2021–2025 ($0.53 trillion in 2025; Section 2.3), and leave the pooled kernel unchanged"}
        for name,fragment in fragments.items():truth(name,fragment in text,dict(fragment=fragment,present=fragment in text))
    return out


def main():
    if not PAPER.exists():print('SKIP | Manuscript wording gates: local W17 draft absent; data-pattern checks still run.')
    checks=evaluate()
    for c in checks:print(('OK' if c['passed'] else 'MISMATCH')+' | PATTERN | '+json.dumps(c,sort_keys=True))
    failed=sum(not c['passed'] for c in checks);print(f'PATTERN SUMMARY | {len(checks)} claims | {failed} mismatches');return int(bool(failed))


if __name__=='__main__':raise SystemExit(main())
