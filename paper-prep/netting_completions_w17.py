"""Read-only completion ranges for netting without early security cancellation.

Uses every agency-look-through/nonbank-issuer completion, sectors separate,
securities not repayable. USD millions in source; reported amounts USD trillions.
Never selects a completion by its order when computing an extremum.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];T=1e6
FILES=('fed-balance-sheet-audit/z1-bank-positions/extension-2000-2007/broad-debt/results.json',
       'broad-debt-model/corrected-results.json',
       'fed-balance-sheet-audit/z1-bank-positions/extension-2009-2019/broad-debt/results.json')

def netting(o,debt,securities=False):
    loan=lambda h,g:o.get('l_'+h+g,0)+o.get('a_'+h+g,0)+(o.get('z_'+h+g,0) if securities else 0)
    cancelled=sum(loan(g,g) for g in 'dr')+2*min(loan('d','r'),loan('r','d'))
    cancelled+=2*sum(min(o['s_'+g]+o['a_t'+g]+(o['z_t'+g] if securities else 0),o[g+'_b']) for g in 'dr')
    cancelled+=sum(min(loan(h,g),o[g+('_qbh' if h=='b' else '_qh')]) for h in 'bf' for g in 'dr')
    return debt-cancelled

def build():
    records=[r for f in FILES for r in json.loads((ROOT/f).read_text())['records']
             if r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank'
             and not r['pooled'] and not r['securities_repayable']]
    kept_path='broad-debt-model/equity-kept-results.json'
    kept={r['id']:r for f in json.loads((ROOT/kept_path).read_text())['families'] for r in f['report']['records']
          if r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank'
          and not r['pooled'] and not r['securities_repayable']}
    if len(records)!=len({r['id'] for r in records}) or {r['id'] for r in records}!=set(kept):raise ValueError('Completion coverage')
    years=[]
    for year in range(2001,2026):
        rs=[r for r in records if int(r['id'][:4])==year]
        if not rs:raise ValueError('Missing year')
        if len({r['opening_debt'] for r in rs})!=1 or len({r['kernel'] for r in rs})!=1:raise ValueError('Unexpected debt/kernel completion spread')
        for r in rs:
            if abs(r['kernel']-kept[r['id']]['kernel'])>.001:raise ValueError('Kept/payout nonrepayable kernel disagreement')
        repayable_nets={netting(r['opening'],r['opening_debt'],True) for r in rs}
        if len(repayable_nets)!=1:raise ValueError('Repayable netting completion spread')
        points=[dict(id=r['id'],netting=netting(r['opening'],r['opening_debt'])/T,
                     ratio=netting(r['opening'],r['opening_debt'])/r['kernel'],
                     retirement_pct=100*(1-netting(r['opening'],r['opening_debt'])/r['opening_debt'])) for r in rs]
        def extrema(field):return [min(p[field] for p in points),max(p[field] for p in points)]
        lo,hi=extrema('netting')
        years.append(dict(year=year,completions=len(rs),repayable_netting=next(iter(repayable_nets))/T,debt=rs[0]['opening_debt']/T,kernel=rs[0]['kernel']/T,
                          netting=extrema('netting'),ratio=extrema('ratio'),retirement_pct=extrema('retirement_pct'),
                          minimum_ids=[p['id'] for p in points if p['netting']==lo],maximum_ids=[p['id'] for p in points if p['netting']==hi],
                          first_completion=points[0],first_is_minimum=points[0]['netting']==lo))
    return dict(scope='All stored source completions; agency look-through, nonbank foreign issuers, separate sectors, debt securities not cancellable. Kept and payout kernels coincide here.',
                unit='USD trillions for levels; percent for retirement',
                source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in (*FILES,kept_path)},years=years)

def numbers(data=None):
    d=data or build();years=d['years']
    return [('nonrepayable netting retirement % minimum','20',min(r['retirement_pct'][0] for r in years)),
            ('nonrepayable netting retirement % maximum','31',max(r['retirement_pct'][1] for r in years))]

def patterns(data=None):
    d=data or build();ys=d['years'];ratio=[min(r['ratio'][0] for r in ys),max(r['ratio'][1] for r in ys)]
    claims=[('all first completions are favourable netting endpoints',all(r['first_is_minimum'] for r in ys),len(ys)),
            ('nonrepayable netting ratio rounds to 1.3–1.4 over all completions',[f'{x:.1f}' for x in ratio]==['1.3','1.4'],ratio),
            ('2025 74.4 is favourable, not completion invariant',ys[-1]['year']==2025 and f"{ys[-1]['netting'][0]:.1f}"=='74.4' and ys[-1]['netting'][1]-ys[-1]['netting'][0]>.1,ys[-1]['netting'])]
    return [dict(claim='W17 completion netting '+name,passed=bool(ok),actual=value,expected=True,scope='all 240 named nonrepayable-security completions') for name,ok,value in claims]


def render(d):
    out=['# Non-repayable-security netting across completions','',d['scope'],'',
         '| Year | Completions | Netting minimum | Netting maximum | Kernel | Netting/kernel | Debt retired % | First is minimum? |',
         '|---|---:|---:|---:|---:|---|---|---|']
    for r in d['years']:
        out.append(f"| {r['year']} | {r['completions']} | {r['netting'][0]:.6f} | {r['netting'][1]:.6f} | {r['kernel']:.6f} | {r['ratio'][0]:.6f}–{r['ratio'][1]:.6f} | {r['retirement_pct'][0]:.6f}–{r['retirement_pct'][1]:.6f} | {'yes' if r['first_is_minimum'] else 'no'} |")
    return '\n'.join(out)+'\n'

if __name__=='__main__':
    d=build()
    for name,text in [('netting-completions-w17.json',json.dumps(d,sort_keys=True,indent=2)+'\n'),('netting-completions-w17.md',render(d))]:
        p=Path(__file__).resolve().parent/name
        if '--check' in sys.argv:
            if p.read_text()!=text:raise SystemExit('stale '+name)
        else:p.write_text(text)
    print(len(d['years']),'years;',sum(r['completions'] for r in d['years']),'completions')
