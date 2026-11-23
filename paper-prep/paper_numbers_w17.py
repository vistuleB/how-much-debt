"""Read-only numerical checks for W17; W16 remains in paper_numbers.py.main().

Run from repository root: python3 -I paper-prep/paper_numbers_w17.py
Standard library only; reads stored results and pinned source archives. Never
imports a writer or runs an inventory builder. Printed paper values are literal
expectations below, so this command also works without the manuscript. External
and historical test-run counts are labelled, not presented as recomputed data.
A mismatch exits 1. This is a transcription/rounding check, not a source audit. The source/table mapping review is equity-kept-instruments.md.
"""
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if Path.cwd().resolve() != ROOT:
    raise SystemExit('Run from repository root')
T = 1e6
FAILURES = []
COUNT = 0


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(context, printed, exact, source, digits=None, significant=None):
    global COUNT
    COUNT += 1
    rendered = str(int(exact)) if digits is None else f'{exact:.{digits}f}'
    if significant is not None:
        rendered = format(float(format(exact, f'.{significant}g')), 'g')
    ok = rendered == printed
    print(f"{'OK' if ok else 'MISMATCH'} | {context} | paper={printed} | "
          f'exact={exact:.12g} | rounded={rendered} | {source}')
    if not ok:
        FAILURES.append(context)


def command_json(path):
    return json.loads(subprocess.check_output([sys.executable, '-I', '-B', path, '--json']))


PAPER = ROOT / "codex-auditor/W17/paper.md"
TABLE = [['2001', '27.22', '10.35', '8.30', '3.84', '4.45', '3.3', '14.31', '7.46'], ['2002', '29.38', '11.15', '9.11', '4.12', '4.99', '3.2', '15.58', '8.17'], ['2003', '32.16', '12.12', '9.90', '4.54', '5.36', '3.2', '17.15', '8.83'], ['2004', '36.16', '13.47', '11.24', '4.94', '6.30', '3.2', '19.46', '9.95'], ['2005', '39.13', '14.91', '12.60', '5.28', '7.33', '3.1', '20.65', '11.03'], ['2006', '42.94', '16.41', '14.09', '5.47', '8.61', '3.0', '22.40', '12.28'], ['2007', '46.77', '17.64', '15.19', '5.72', '9.47', '3.1', '24.10', '13.12'], ['2008', '47.27', '19.52', '15.92', '6.59', '9.33', '3.0', '23.54', '13.58'], ['2009', '47.63', '20.64', '16.97', '8.00', '8.97', '2.8', '25.34', '14.93'], ['2010', '48.16', '21.54', '17.31', '9.37', '7.94', '2.8', '26.14', '15.43'], ['2011', '49.61', '22.41', '18.26', '10.71', '7.55', '2.7', '27.67', '16.43'], ['2012', '51.78', '23.77', '19.31', '11.83', '7.48', '2.7', '29.60', '17.52'], ['2013', '52.78', '25.00', '20.84', '12.35', '8.49', '2.5', '29.56', '18.87'], ['2014', '55.17', '26.27', '22.02', '13.05', '8.97', '2.5', '31.16', '20.04'], ['2015', '56.08', '27.92', '23.02', '13.56', '9.46', '2.4', '31.16', '21.01'], ['2016', '58.23', '29.73', '24.04', '14.24', '9.80', '2.4', '32.32', '21.90'], ['2017', '61.02', '30.92', '25.27', '14.76', '10.51', '2.4', '33.98', '22.97'], ['2018', '63.22', '33.18', '26.01', '15.90', '10.11', '2.4', '34.56', '23.78'], ['2019', '67.17', '34.73', '27.06', '16.98', '10.08', '2.5', '37.31', '24.88'], ['2020', '75.17', '41.19', '30.82', '19.99', '10.84', '2.4', '41.91', '28.45'], ['2021', '80.13', '42.69', '34.20', '22.81', '11.39', '2.3', '45.20', '31.48'], ['2022', '81.33', '43.93', '33.94', '24.15', '9.80', '2.4', '44.08', '31.10'], ['2023', '85.93', '48.34', '35.26', '26.53', '8.73', '2.4', '47.76', '32.35'], ['2024', '89.86', '50.86', '36.04', '28.61', '7.42', '2.5', '50.59', '33.03'], ['2025', '96.07', '54.00', '37.47', '30.61', '6.86', '2.6', '54.62', '34.21']]


def main():
    series = load('paper_series', 'paper-prep/broad-debt/series.py')
    rows = command_json('paper-prep/broad-debt/series.py')
    by_year = {x['year']: x for x in rows}
    kept_rows=command_json('paper-prep/broad-debt/bank_equity_kept.py')
    kept={x['year']:x for x in kept_rows}
    stored=json.loads(Path('broad-debt-model/equity-kept-results.json').read_text())
    records=[r for family in stored['families'] for r in family['report']['records']]
    selected = [r for r in records if r['representation'] == 'agency_lookthrough'
                and r['nonbank_foreign_security_issuers'] == 'nonbank'
                and r['securities_repayable'] and not r['pooled']]
    heads = {}
    for r in selected:
        heads.setdefault(int(r['id'][:4]), r)
    # W17's headline uses the independently executed equity-kept records.
    for x in rows:
        y=x['year'];r=heads[y]
        x.update(least=kept[y]['separate'],pooled=kept[y]['pooled'],
                 gap_d=r['signed_debt_receipt_gap']['d']/T,gap_r=r['signed_debt_receipt_gap']['r']/T,
                 dom=max(0,r['signed_debt_receipt_gap']['d']/T))
    src = 'bank_equity_kept.py --json; equity-kept-results.json'
    table=TABLE
    if PAPER.exists():
        import re
        table=[[x.strip() for x in line.strip().strip('|').split('|')] for line in PAPER.read_text().splitlines() if re.match(r'^\| 20\d\d \|',line)]
        if len(table)!=25:raise ValueError('W17 Table 2 coverage')
    else:print('MANUSCRIPT | using stored W17 expectations; local draft absent')
    for row in table:
        y = int(row[0]); x = by_year[y]
        vals = [x['debt'], x['netting'], x['least'], x['tnd'], x['dom'],
                x['debt']/x['least'], x['frozen'], kept[y]['least_with_payout']]
        for col, printed, exact in zip(('debt','netting','kernel','Treasury','domestic','ratio','not repayable','domestic payout'), row[1:], vals):
            check(f'4.2 Table 2 {y} {col}', printed, exact, src, 1 if col == 'ratio' else 2)
    a, b = by_year[2021], by_year[2025]
    o1, o5 = heads[2021]['opening'], heads[2025]['opening']
    money = lambda o: o['d_m'] + o['d_ch']
    # Bank equity is kept; V_d excludes any hypothetical equity payout.
    vd = lambda o, r: money(o) - r['signed_debt_receipt_gap']['d']
    for name, printed, value in [
        ('Treasury net debt increase','7.8',b['tnd']-a['tnd']),
        ('domestic net position increase (bank equity kept)','5.3',(vd(o5,heads[2025])-vd(o1,heads[2021]))/T),
        ('domestic money increase','0.8',(money(o5)-money(o1))/T),
        ('domestic term 2021','11.4',a['dom']),('domestic term 2025','6.9',b['dom']),
        ('kernel increase','3.3',b['least']-a['least']),
        ('2025 debt retired','58.6',b['debt']-b['least']),
        ('2025 debt retired, securities not repayable','41.4',b['debt']-b['frozen']),
        ('2025 netting','54.0',b['netting']),('2025 kernel','37.5',b['least']),
        ('2025 Treasury','30.6',b['tnd']),('2025 debt','96.1',b['debt']),
        ('domestic term minimum','4.5',min(x['dom'] for x in rows)),
        ('domestic term maximum','11.4',max(x['dom'] for x in rows)),
        ('2025 gap netting to kept kernel','16.5',b['netting']-kept[2025]['separate']),
        ('2025 kernel with equity kept','37.5',kept[2025]['separate'])]:
        check('1 / 4.2 '+name, printed, value, src, 1)
    for name,values,expectations in [
        ('2014–2017 pooled above Treasury',[x['pooled']-x['tnd'] for x in rows if 2014<=x['year']<=2017],('0.1','0.5')),
        ('column 9 domestic payout netting ratio',[x['netting_ratio_with_payout'] for x in kept_rows],('1.3','1.6'))]:
        for bound,printed,value in zip(('min','max'),expectations,(min(values),max(values))):
            check('1 / 4.2 '+name+' '+bound,printed,value,'kept and domestic reference policy series',1)
    o = o5
    intra = sum(o.get(p+g+g,0) for p in ('l_','a_','z_') for g in 'dr')/T
    check('4.2 netting within sectors 2025','26.0',intra,'series.py netting_only: sum l_gg+a_gg+z_gg',1)
    for name, vals, expected in [
        ('retirement %', [100*(x['debt']-x['least'])/x['debt'] for x in rows],('57','70')),
        ('netting retirement %',[100*(x['debt']-x['netting'])/x['debt'] for x in rows],('43','63')),
        ('not repayable retirement %',[100*(x['debt']-x['frozen'])/x['debt'] for x in rows],('43','50')),
        ('netting / kernel',[x['netting']/x['least'] for x in rows],('1.2','1.4')),
        ('2001–2009 pooled above Treasury',[x['pooled']-x['tnd'] for x in rows if x['year']<2010],('1.2','2.4')),
        ('2001–2008 Treasury share %',[100*x['tnd']/x['least'] for x in rows if x['year']<=2008],('38','46'))]:
        for bound, printed, value in zip(('min','max'),expected,(min(vals),max(vals))):
            check('1 / 4.2 '+name+' '+bound,printed,value,src,1 if '.' in printed else 0)
    check('1 / 4.2 2025 Treasury share %','82',100*b['tnd']/b['least'],src,0)
    narrow_paths = [Path(f).parent.parent/'row-split/check.json' for f in series.FILES if 'extension' in f]
    narrow_paths += [Path('fed-balance-sheet-audit/z1-bank-positions/row-split/check.json')]
    states = [s for p in narrow_paths for s in json.loads(p.read_text())['scenarios']]
    check('4.1 completed balance sheets','480',len(states),'three row-split/check.json scenario lists')
    check('4.1 look-through sheets','240',sum(s['representation']=='agency_lookthrough' for s in states),'three row-split/check.json scenario lists')
    reps = sorted({s['representation'] for s in states})
    counts = [sum(s['year']==y and s['representation']==r for s in states) for y in by_year for r in reps]
    check('4.1 fewest completions/year in each representation','6',min(counts),'three row-split/check.json')
    check('4.1 most completions/year in each representation','24',max(counts),'three row-split/check.json')
    ef = [r['opening']['ef']/T for r in selected if int(r['id'][:4])==2025]
    check('2.3 Fed equity magnitude minimum','0.47',-max(ef),'stored selected opening.ef',2)
    check('2.3 Fed equity magnitude maximum','0.72',-min(ef),'stored selected opening.ef',2)
    # Linear extrapolation of the current separate kernel's gap to money.
    # This is a scale calculation, not a valid state with only EF changed:
    # another balance-sheet coordinate must compensate any equity change.
    P = sum(o[k] for k in ('d_m','r_m','d_ch','r_ch'))/T
    threshold = o['ef']/T - (b['least'] - P)
    check('2.3 about minus $14T Fed-equity threshold','-14',threshold,'opening.ef - (separate kernel - nonbank money); counterfactual with fixed other offsets',0)
    print(f'QUALIFICATION | 2.3 linear extrapolation threshold={threshold:.6f} trillion; not a proved comparative static with completion rules held fixed')
    print('EXTERNAL | 2.3 deferred asset | paper=243.5 USD billions | '
          'Federal Reserve Bank of New York (2026), Open Market Operations during 2025; '
          'https://www.newyorkfed.org/markets/annual_reports | not recomputed from Z.1')
    # Read source observations, without importing the writing inventory builder.
    archive=Path('fed-balance-sheet-audit/z1-bank-positions/raw/z1-20260319-csv.zip')
    with zipfile.ZipFile(archive) as z:
        federal=list(csv.reader(io.StringIO(z.read('csv/l106.csv').decode())))
        direct_rows=list(csv.reader(io.StringIO(z.read('csv/l223.csv').decode())))
    def observation(rows, code):
        k=rows[0].index(code)
        return float(next(x[k] for x in rows[1:] if x[0]=='2025:Q4'))
    for name,printed,code in [('student','1.58','FL313066220.Q'),('all federal loans','2.40','FL314023005.Q')]:
        check('4.1 '+name,printed,observation(federal,code)/T,'March archive csv/l106.csv '+code+' 2025:Q4',2)
    check('4.1 direct-investment intercompany debt, USD billions','-4.4',
          observation(direct_rows,'LM763092305.Q')/1000,
          'March archive csv/l223.csv LM763092305.Q 2025:Q4',1)
    # Household replication uses precisely slice_checks.py's item-by-item rescale.
    sc=load('paper_slice_checks','paper-prep/sector-slicing/slice_checks.py')
    H,X=sc.b101h(),sc.dfa()
    student=sc.student(); collection_increments=[]
    household=[]; raw=[]
    for x in rows:
        y=x['year']; cols=('Loans (Liabilities)','Debt securities','Loans (Assets)')
        scales={col:sum(H[y][c] for c in codes)/T/sum(X[(f'{y}:Q4',g)][col] for g in sc.GROUPS)
                for col,codes in sc.VINTAGE if col in cols}
        def gaps(scale):
            return [sum(sign*X[(f'{y}:Q4',g)][col]*scale[col] for col,sign in zip(cols,(1,-1,-1))) for g in sc.GROUPS]
        def split(gs):
            return x['tnd']+sum(max(0,g) for g in gs)+max(0,x['gap_d']-sum(gs))+max(0,x['gap_r'])
        gs=gaps(scales); unscaled=gaps(dict.fromkeys(cols,1))
        rest=x['gap_d']-sum(gs)
        delta=max(0,rest)-max(0,rest-heads[y]['opening']['eb']/T)
        household.append(dict(year=y,gaps=gs,one=split([sum(gs)]),five=split(gs),five_kept=split(gs),kept_delta=delta,base=x['least'],debt=x['debt']))
        raw.append(split(unscaled))
        r=heads[y]; cert=r['certificate']; op=r['opening']
        cc=sum(X[(f'{y}:Q4',g)]['Consumer credit'] for g in sc.GROUPS)
        parts={g:dict(c=sum(X[(f'{y}:Q4',g)][col]*scales[col] for col in cols[1:]),
                      o=X[(f'{y}:Q4',g)][cols[0]]*scales[cols[0]],
                      s=student[y]*X[(f'{y}:Q4',g)]['Consumer credit']/cc) for g in sc.GROUPS}
        parts['rest']={k:cert[field]['d']/T-sum(v[k] for v in parts.values())
                       for k,field in [('c','receipts'),('o','repayable'),('s','treasury_receivables')]}
        parts['row']={k:cert[field]['r']/T for k,field in [('c','receipts'),('o','repayable'),('s','treasury_receivables')]}
        bonds=sum(op[k] for k in ('bb','bf','d_b','r_b'))/T
        resources=sum(op[k] for k in ('t','qg','s_d','s_r','j_td','j_tr'))/T
        result=r['opening_debt']/T-sc.sequence(parts,(bonds,resources),cert['prepared_reserve_cap']/T,False)
        collection_increments.append(result-split(gs))
    for name, vals, expected in [
        ('household separation %',[100*(x['one']/x['base']-1) for x in household],('0','19')),
        ('wealth division additional %',[100*(x['five']/x['one']-1) for x in household],('1','10'))]:
        for end,printed,value in zip(('min','max'),expected,(min(vals),max(vals))):
            check('5 / 6 '+name+' '+end,printed,value,'slice_checks.py March rescaling algorithm (recomputed here)',0)
    h=household[-1]
    for label,printed,gap in zip(('bottom 50','next 40','next 9'),('5.9','7.4','1.4'),h['gaps']):
        check('5 2025 '+label+' gap',printed,gap,'slice_checks.py March rescaling',1)
    for label,printed,value in [('pooled household share','46',100*h['one']/h['debt']),('five wealth groups share','47',100*h['five']/h['debt']),('two sector share','39',100*h['base']/h['debt'])]:
        check('5 2025 '+label,printed,value,'March-rescaled DFA / stored opening debt',0)
    check('5 maximum vintage effect','0.26',max(abs(x['five']-a) for x,a in zip(household,raw)),'March-rescaled versus unscaled DFA',2)
    net=json.loads(Path('paper-prep/netting-splits/households-results.json').read_text())
    ratios=[(x['year'],net[str(x['year'])]['pairwise_most']/x['five']) for x in household]
    y,ratio=min(ratios,key=lambda p:p[1])
    check('5 favourable pairwise / split lower ratio','1.17',ratio,'households-results.json pairwise_most / split_min',2)
    check('5 year of lowest ratio','2022',y,'households-results.json')
    check('5 favourable pairwise 2025','55.6',net['2025']['pairwise_most'],'households-results.json',1)
    check('5 split minimum 2025','45.3',net['2025']['split_min'],'households-results.json',1)
    multi=load('paper_multi','paper-prep/broad-debt/netting_multilateral.py')
    check('4.2 multilateral 2025','52.2',multi.netting(o,heads[2025]['opening_debt'],'C')/T,'netting_multilateral.py most generous claim set C',1)
    frozen_net=[]
    for year in sorted(heads):
        rec=heads[year]; op=rec['opening']
        g=lambda k:op.get(k,0)
        cl=lambda h,s:g('l_'+h+s)+g('a_'+h+s)
        cancelled=sum(cl(h,h) for h in 'dr')+2*min(cl('d','r'),cl('r','d'))
        cancelled+=2*sum(min(g('s_'+h)+g('a_t'+h),g(h+'_b')) for h in 'dr')
        cancelled+=sum(min(cl('b',h),g(h+'_qbh'))+min(cl('f',h),g(h+'_qh')) for h in 'dr')
        value=rec['opening_debt']/T-cancelled/T
        frozen_net.append(value/by_year[year]['frozen'])
        if year==2025:
            check('4.2 netting securities not cancellable','74.4',value,'netting_frozen.py first completion, independently verified as the favourable minimum',1)
    check('4.2 not repayable netting ratio minimum','1.3',min(frozen_net),'netting_frozen.py',1)
    check('4.2 not repayable netting ratio maximum','1.4',max(frozen_net),'netting_frozen.py',1)
    check('5 collection-only Treasury proportional increment','0.8',max(collection_increments),'slice_checks.py sequence, March-rescaled items and consumer-credit proportions',1)
    foreign=[r for r in records if int(r['id'][:4])==2025 and r['representation']=='security_outside_D' and r['nonbank_foreign_security_issuers']=='nonbank']
    check('Table 2 caption agency-as-security debt 2025','106.5',foreign[0]['opening_debt']/T,'stored security_outside_D opening_debt',1)
    import ast
    base=Path('paper-prep/static-vs-operational')
    tree=ast.parse((base/'landscape_s9_s15.py').read_text())
    cases=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign)
               and any(isinstance(t,ast.Name) and t.id=='cases' for t in n.targets))
    tree20=ast.parse((base/'landscape_s20.py').read_text())
    regimes=next(n.iter for n in ast.walk(tree20) if isinstance(n,ast.For)
                 and isinstance(n.target,ast.Name) and n.target.id=='regime')
    tree22=ast.parse((base/'landscape_s22_f2.py').read_text())
    profiles=next(n.iter for n in ast.walk(tree22) if isinstance(n,ast.For)
                  and isinstance(n.target,ast.Tuple))
    n22=sum(one_way for profile,one_way in ast.literal_eval(profiles))
    trials=2000*len(cases.keys)+1500*len(ast.literal_eval(regimes))+600*n22
    check('Appendix configured random-opening comparisons','24700',trials,
          'README landscape commands: 2000 x 8 + 1500 x 5 + 600 x 2; AST counts, excludes deliberate counterexample')
    print('HISTORICAL RUN RECORD | No LP outcomes recertified by the count check; '
          'rerun the three documented landscape commands for their no-disagreement result')
    source_kept='python3 -I paper-prep/broad-debt/bank_equity_kept.py --json; equity-kept-results.json executed/replayed counterpart'
    for label,values,printed,digits in [
        ('abstract kept-equity netting ratio minimum',[x['netting_ratio'] for x in kept_rows],'1.2',1),
        ('abstract kept-equity netting ratio maximum',[x['netting_ratio'] for x in kept_rows],'1.4',1),
        ('introduction kept-equity retirement % minimum',[100*(1-x['separate']/x['debt']) for x in kept_rows],'57',0),
        ('introduction kept-equity retirement % maximum',[100*(1-x['separate']/x['debt']) for x in kept_rows],'70',0)]:
        value=(min if 'minimum' in label else max)(values)
        check('paper '+label,printed,value,source_kept,digits)
    check('5 greatest household kept-equity increment','0.14',max(x['kept_delta'] for x in household),'March-rescaled household rest gap with opening bank equity removed from receipts',2)
    affected=[x['year'] for x in household if x['kept_delta']>1e-9]
    check('5 count of years with household equity effect','2',len(affected),'March-rescaled household rest gap')
    for printed,y in zip(('2015','2017'),affected):
        check('5 year with household equity effect',printed,y,'March-rescaled household rest gap')
    print('DETAIL | household equity increments='+repr({x['year']:x['kept_delta'] for x in household if x['kept_delta']>1e-9}))
    check('5 favourable pairwise / kept split ratio','1.17',min(net[str(x['year'])]['pairwise_most']/x['five_kept'] for x in household),'stored household netting / March-rescaled kept-equity split',2)
    executed=json.loads(Path('broad-debt-model/equity-kept-results.json').read_text())
    checked=0
    kept_formula=load('paper_kept','paper-prep/broad-debt/bank_equity_kept.py')
    for family in executed['families']:
        for rec in family['report']['records']:
            exact=kept_formula.certificate(rec['opening'],rec['pooled'],rec['securities_repayable'],False)
            if abs(exact-rec['kernel'])>0.001:
                FAILURES.append('equity-kept executed certificate '+rec['id'])
            checked+=1
    print(f'EXECUTED COMPARISON | {checked} equity-kept endpoints compared with independent paper formula')
    check('Appendix earlier narrow openings' ,'252',len(json.loads(Path('fed-balance-sheet-audit/z1-bank-positions/row-split/check.json').read_text())['scenarios']),'row-split/check.json')
    profile_module=load('paper_profiles','paper-prep/paper_profiles.py')
    profile_data=profile_module.Data()
    all_netting=[profile_data.metrics(r['year'],case=profile_module.completion(r)) for r in selected]
    for label,value,printed in [
        ('abstract all netting / equity-kept kernel minimum',min(x['any_netting_ratio_min'] for x in all_netting),'1.2'),
        ('abstract all netting / equity-kept kernel maximum',max(x['any_netting_ratio_max'] for x in all_netting),'1.4'),
        ('4.2 multilateral / equity-kept kernel minimum',min(x['multilateral_kept_ratio'] for x in all_netting),'1.2'),
        ('4.2 multilateral / equity-kept kernel maximum',max(x['multilateral_kept_ratio'] for x in all_netting),'1.4')]:
        check(label,printed,value,'maximum-circulation netting A/B/C and pairwise; all selected completions',1)
    fed=load('w17_fed_valuation','paper-prep/fed_valuation_checks_w17.py')
    for label,printed,value in fed.numbers():
        family='across completions' in label
        check(('2.3' if family else '4.1')+' Fed valuation '+label,printed,value,
              fed.SOURCE+('; all 24 kept-equity completions' if family else '; selected kept-equity completion'),2)
    nc=load('w17_netting_completions','paper-prep/netting_completions_w17.py')
    for label,printed,value in nc.numbers():
        check('1 / 4.2 '+label,printed,value,'all 240 agency-look-through/nonbank-issuer completions; securities not cancellable',0)
    patterns=load('paper_patterns_w17','paper-prep/paper_patterns_w17.py').evaluate(profile_data)
    for result in patterns:
        print(('OK' if result['passed'] else 'MISMATCH')+' | PATTERN | '+json.dumps(result,sort_keys=True))
        if not result['passed']:
            FAILURES.append('pattern: '+result['claim'])
    print(f'PATTERN SUMMARY | {len(patterns)} claims | {sum(not r["passed"] for r in patterns)} mismatches')
    print(f'SUMMARY | {COUNT} comparisons | {len(FAILURES)} mismatches')
    return int(bool(FAILURES))


if __name__ == '__main__':
    raise SystemExit(main())
