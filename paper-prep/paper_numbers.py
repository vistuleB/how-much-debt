"""Read-only verification of the paper’s data-derived numbers.

Run from repository root: python3 -I paper-prep/paper_numbers.py
The CLI targets W17. --w16 retains the historical checks; main()/TABLE
remain the W16 compatibility API used by the versioned sensitivity outputs.
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


TABLE = [['2001', '27.22', '10.35', '7.46', '3.84', '3.62', '3.6', '14.31', '8.30'], ['2002', '29.38', '11.15', '8.17', '4.12', '4.05', '3.6', '15.58', '9.11'], ['2003', '32.16', '12.12', '8.83', '4.54', '4.29', '3.6', '17.15', '9.90'], ['2004', '36.16', '13.47', '9.95', '4.94', '5.01', '3.6', '19.46', '11.24'], ['2005', '39.13', '14.91', '11.03', '5.28', '5.76', '3.5', '20.65', '12.60'], ['2006', '42.94', '16.41', '12.28', '5.47', '6.81', '3.5', '22.40', '14.09'], ['2007', '46.77', '17.64', '13.12', '5.72', '7.40', '3.6', '24.10', '15.19'], ['2008', '47.27', '19.52', '13.58', '6.59', '6.98', '3.5', '23.54', '15.92'], ['2009', '47.63', '20.64', '14.93', '8.00', '6.92', '3.2', '25.34', '16.97'], ['2010', '48.16', '21.54', '15.43', '9.37', '6.07', '3.1', '26.14', '17.31'], ['2011', '49.61', '22.41', '16.43', '10.71', '5.72', '3.0', '27.67', '18.26'], ['2012', '51.78', '23.77', '17.52', '11.83', '5.69', '3.0', '29.60', '19.31'], ['2013', '52.78', '25.00', '18.87', '12.35', '6.52', '2.8', '29.56', '20.84'], ['2014', '55.17', '26.27', '20.04', '13.05', '6.99', '2.8', '31.16', '22.02'], ['2015', '56.08', '27.92', '21.01', '13.56', '7.46', '2.7', '31.16', '23.02'], ['2016', '58.23', '29.73', '21.90', '14.24', '7.66', '2.7', '32.32', '24.04'], ['2017', '61.02', '30.92', '22.97', '14.76', '8.21', '2.7', '33.98', '25.27'], ['2018', '63.22', '33.18', '23.78', '15.90', '7.88', '2.7', '34.56', '26.01'], ['2019', '67.17', '34.73', '24.88', '16.98', '7.90', '2.7', '37.31', '27.06'], ['2020', '75.17', '41.19', '28.45', '19.99', '8.47', '2.6', '41.91', '30.82'], ['2021', '80.13', '42.69', '31.48', '22.81', '8.66', '2.5', '45.20', '34.20'], ['2022', '81.33', '43.93', '31.10', '24.15', '6.95', '2.6', '44.08', '33.94'], ['2023', '85.93', '48.34', '32.35', '26.53', '5.82', '2.7', '47.76', '35.26'], ['2024', '89.86', '50.86', '33.03', '28.61', '4.42', '2.7', '50.59', '36.04'], ['2025', '96.07', '54.00', '34.21', '30.61', '3.60', '2.8', '54.62', '37.47']]


def main():
    series = load('paper_series', 'paper-prep/broad-debt/series.py')
    rows = command_json('paper-prep/broad-debt/series.py')
    by_year = {x['year']: x for x in rows}
    kept_rows=command_json('paper-prep/broad-debt/bank_equity_kept.py')
    kept={x['year']:x for x in kept_rows}
    records = list(series.records())
    selected = [r for r in records if r['representation'] == 'agency_lookthrough'
                and r['nonbank_foreign_security_issuers'] == 'nonbank'
                and r['securities_repayable'] and not r['pooled']]
    heads = {}
    for r in selected:
        heads.setdefault(int(r['id'][:4]), r)
    src = 'python3 -I paper-prep/broad-debt/series.py --json'
    for row in TABLE:
        y = int(row[0]); x = by_year[y]
        vals = [x['debt'], x['netting'], x['least'], x['tnd'], x['dom'],
                x['debt']/x['least'], x['frozen'], kept[y]['separate']]
        for col, printed, exact in zip(('debt','netting','kernel','Treasury','domestic','ratio','not repayable','equity kept'), row[1:], vals):
            check(f'4.2 Table 2 {y} {col}', printed, exact, src, 1 if col == 'ratio' else 2)
    a, b = by_year[2021], by_year[2025]
    o1, o5 = heads[2021]['opening'], heads[2025]['opening']
    money = lambda o: o['d_m'] + o['d_ch']
    # With domestic payouts, the paper's effective V_d includes opening bank equity.
    vd = lambda o, r: money(o) - r['signed_debt_receipt_gap']['d']
    for name, printed, value in [
        ('Treasury net debt increase','7.8',b['tnd']-a['tnd']),
        ('domestic net position increase (including bank payout)','5.8',(vd(o5,heads[2025])-vd(o1,heads[2021]))/T),
        ('domestic money increase','0.8',(money(o5)-money(o1))/T),
        ('domestic term 2021','8.7',a['dom']),('domestic term 2025','3.6',b['dom']),
        ('kernel increase','2.7',b['least']-a['least']),
        ('2025 debt retired','61.9',b['debt']-b['least']),
        ('2025 debt retired, securities not repayable','41.4',b['debt']-b['frozen']),
        ('2025 netting','54.0',b['netting']),('2025 kernel','34.2',b['least']),
        ('2025 Treasury','30.6',b['tnd']),('2025 debt','96.1',b['debt']),
        ('domestic term minimum','3.6',min(x['dom'] for x in rows)),
        ('domestic term maximum','8.7',max(x['dom'] for x in rows)),
        ('2025 gap netting to kept kernel','16.5',b['netting']-kept[2025]['separate']),
        ('2025 kernel with equity kept','37.5',kept[2025]['separate'])]:
        check('1 / 4.2 '+name, printed, value, src, 1)
    o = o5
    intra = sum(o.get(p+g+g,0) for p in ('l_','a_','z_') for g in 'dr')/T
    check('4.2 netting within sectors 2025','26.0',intra,'series.py netting_only: sum l_gg+a_gg+z_gg',1)
    for name, vals, expected in [
        ('retirement %', [100*(x['debt']-x['least'])/x['debt'] for x in rows],('61','73')),
        ('netting retirement %',[100*(x['debt']-x['netting'])/x['debt'] for x in rows],('43','63')),
        ('not repayable retirement %',[100*(x['debt']-x['frozen'])/x['debt'] for x in rows],('43','50')),
        ('netting / kernel',[x['netting']/x['least'] for x in rows],('1.3','1.6')),
        ('2001–2007 pooled above Treasury',[x['pooled']-x['tnd'] for x in rows if x['year']<2008],('0.4','0.6')),
        ('2001–2008 Treasury share %',[100*x['tnd']/x['least'] for x in rows if x['year']<=2008],('44','52'))]:
        for bound, printed, value in zip(('min','max'),expected,(min(vals),max(vals))):
            check('1 / 4.2 '+name+' '+bound,printed,value,src,1 if '.' in printed else 0)
    check('1 / 4.2 2025 Treasury share %','89',100*b['tnd']/b['least'],src,0)
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
    check('2.3 about minus $11T Fed-equity threshold','-11',threshold,'opening.ef - (separate kernel - nonbank money); counterfactual with fixed other offsets',0)
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
        delta=max(0,rest+heads[y]['opening']['eb']/T)-max(0,rest)
        household.append(dict(year=y,gaps=gs,one=split([sum(gs)]),five=split(gs),five_kept=split(gs)+delta,kept_delta=delta,base=x['least'],debt=x['debt']))
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
        ('household separation %',[100*(x['one']/x['base']-1) for x in household],('9','34')),
        ('wealth division additional %',[100*(x['five']/x['one']-1) for x in household],('1','10'))]:
        for end,printed,value in zip(('min','max'),expected,(min(vals),max(vals))):
            check('5 / 6 '+name+' '+end,printed,value,'slice_checks.py March rescaling algorithm (recomputed here)',0)
    h=household[-1]
    for label,printed,gap in zip(('bottom 50','next 40','next 9'),('5.9','7.4','1.4'),h['gaps']):
        check('5 2025 '+label+' gap',printed,gap,'slice_checks.py March rescaling',1)
    for label,printed,value in [('pooled household share','46',100*h['one']/h['debt']),('five wealth groups share','47',100*h['five']/h['debt']),('two sector share','36',100*h['base']/h['debt'])]:
        check('5 2025 '+label,printed,value,'March-rescaled DFA / stored opening debt',0)
    check('5 maximum vintage effect','0.26',max(abs(x['five']-a) for x,a in zip(household,raw)),'March-rescaled versus unscaled DFA',2)
    net=json.loads(Path('paper-prep/netting-splits/households-results.json').read_text())
    ratios=[(int(y),v['pairwise_most']/v['split_min']) for y,v in net.items()]
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
            check('4.2 netting securities not cancellable','74.4',value,'netting_frozen.py cancellation expression',1)
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
    patterns=load('paper_patterns','paper-prep/paper_patterns.py').evaluate(profile_data)
    for result in patterns:
        print(('OK' if result['passed'] else 'MISMATCH')+' | PATTERN | '+json.dumps(result,sort_keys=True))
        if not result['passed']:
            FAILURES.append('pattern: '+result['claim'])
    print(f'PATTERN SUMMARY | {len(patterns)} claims | {sum(not r["passed"] for r in patterns)} mismatches')
    print(f'SUMMARY | {COUNT} comparisons | {len(FAILURES)} mismatches')
    return int(bool(FAILURES))


# Preserve the historical compatibility API and all literal W16 expectations.
main_w16 = main


def main_w17():
    return load('current_paper_numbers_w17','paper-prep/paper_numbers_w17.py').main()


if __name__ == '__main__':
    raise SystemExit(main_w16() if '--w16' in sys.argv else main_w17())
