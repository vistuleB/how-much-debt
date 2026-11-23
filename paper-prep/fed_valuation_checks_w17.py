"""Read-only W17 checks of selected and full-family Fed-cost sensitivity.

No builders/model imports. Source amounts are USD millions. Bank equity is
kept; agency look-through and nonbank foreign-security issuers are selected.
"""
import gzip
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='broad-debt-model/fed-valuation/results.json.gz'
YEARS=tuple(range(2021,2026));T=1e6


def read():
    doc=json.loads(gzip.decompress((ROOT/SOURCE).read_bytes()))
    if doc['format_version']!=1 or doc['unit']!='USD millions':
        raise ValueError('Fed valuation format/units')
    return doc['records']


def selected(records):
    # Explicitly the economic-equity completion (no locked_contra_asset suffix).
    # The headline defaults use the minimum bank-MBS completion. At this
    # sensitivity the observed_us_mix alternative has identical EF and kernels.
    result={}
    for r in records:
        if (r['representation']!='agency_lookthrough' or r['issuer']!='nonbank'
                or r['policy']!='kept' or r['year'] not in YEARS):continue
        expected=f"{r['year']}/holder_correction/equity_correction/minimum/agency_lookthrough"
        if r['id']!=expected:continue
        key=(r['year'],r['pooled'])
        if key in result:raise ValueError('Duplicate selected Fed valuation case')
        result[key]=r
    if set(result)!={(y,p) for y in YEARS for p in (False,True)}:
        raise ValueError('Incomplete selected Fed valuation coverage')
    return result


def cost_equity_family_2025(records):
    """All headline-representation completions, not only the chosen headline."""
    family={}
    for r in records:
        if (r['year']!=2025 or r['representation']!='agency_lookthrough'
                or r['issuer']!='nonbank' or r['policy']!='kept' or r['pooled']):continue
        if r['id'] in family:raise ValueError('Duplicate Fed-cost equity completion')
        family[r['id']]=r
    baseline=json.loads((ROOT/'broad-debt-model/equity-kept-results.json').read_text())
    expected={r['id'] for f in baseline['families'] for r in f['report']['records']
              if r['id'].startswith('2025/') and r['representation']=='agency_lookthrough'
              and r['nonbank_foreign_security_issuers']=='nonbank'
              and r['securities_repayable'] and not r['pooled']}
    if set(family)!=expected or len(family)!=24:
        raise ValueError('Incomplete 2025 Fed-cost equity completion family')
    return list(family.values())


def numbers(records=None):
    rows=read() if records is None else records
    s=selected(rows);family=cost_equity_family_2025(rows)
    separate=[s[y,False] for y in YEARS];last=s[2025,False]
    return [
        ('2025 equity and separate kernel increase','0.53',last['ef_change']/T),
        ('2021–2025 separate kernel increase minimum','0.06',min(r['kernel_change'] for r in separate)/T),
        ('2021–2025 separate kernel increase maximum','0.58',max(r['kernel_change'] for r in separate)/T),
        ('2025 amortized-cost equity across completions minimum','-0.18',min(r['opening']['ef'] for r in family)/T),
        ('2025 amortized-cost equity across completions maximum','0.06',max(r['opening']['ef'] for r in family)/T)]


def patterns(records=None):
    rows=read() if records is None else records;s=selected(rows);out=[]
    def add(claim,passed,actual):
        out.append(dict(claim='W17 Fed valuation '+claim,passed=bool(passed),actual=actual,expected=True,scope='W17 Fed-cost experiment; selection stated in claim'))
    values=list(s.values());separate=[s[y,False] for y in YEARS];pooled=[s[y,True] for y in YEARS]
    add('reported deltas match endpoints',all(r['kernel']-r['baseline_kernel']==r['kernel_change'] and r['opening']['ef']-r['baseline_ef']==r['ef_change'] for r in rows),len(rows))
    add('equity rises in 2025',s[2025,False]['opening']['ef']>s[2025,False]['baseline_ef'],[s[2025,False]['baseline_ef']/T,s[2025,False]['opening']['ef']/T])
    add('separate kernel rises in every year 2021–2025',all(r['kernel_change']>0 for r in separate),{str(r['year']):r['kernel_change']/T for r in separate})
    add('separate changes equal equity changes in every stored completion',all(r['kernel_change']==r['ef_change'] for r in rows if not r['pooled']),sum(not r['pooled'] for r in rows))
    add('pooled kernel unchanged in every year/completion 2021–2025',all(r['kernel_change']==0 and r['kernel']==r['baseline_kernel'] for r in rows if r['pooled']),sum(r['pooled'] for r in rows))
    # These are holder reallocations, not changes to opening selected debt.
    base=json.loads((ROOT/'broad-debt-model/equity-kept-results.json').read_text())
    expected={(r['id'],r['nonbank_foreign_security_issuers'],policy,r['pooled'])
              for f in base['families'] for r in f['report']['records']
              if r['securities_repayable'] and int(r['id'][:4]) in YEARS
              for policy in ('kept','domestic')}
    actual=[(r['id'],r['issuer'],r['policy'],r['pooled']) for r in rows]
    add('complete unique all-policy valuation family',len(actual)==len(set(actual))==len(expected)==1728 and set(actual)==expected,len(actual))
    index={(r['id'],r['pooled']):r for f in base['families'] for r in f['report']['records'] if r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank' and r['securities_repayable']}
    unchanged=True
    for r in values:
        old=index[r['id'],r['pooled']]
        unchanged &= r['opening']['eb']==old['opening']['eb']
        unchanged &= r['baseline_ef']==old['opening']['ef'] and r['baseline_kernel']==old['kernel']
        unchanged &= all(r['opening'][k]==old['opening'][k] for k in ('d_m','r_m','d_ch','r_ch','r_b'))
    add('bank equity, money and foreign Treasury holdings retained',unchanged,len(values))
    # Check the source report's observed-US-mix presentation as well as the
    # paper's default minimum completion; do not silently combine their rows.
    alternatives=[r for r in rows if r['representation']=='agency_lookthrough' and r['issuer']=='nonbank' and r['policy']=='kept' and r['year']>=2022 and r['id']==f"{r['year']}/holder_correction/equity_correction/observed_us_mix/agency_lookthrough"]
    add('observed-US-mix has the same quoted figures',len(alternatives)==8 and all(all(r[k]==s[r['year'],r['pooled']][k] for k in ('baseline_ef','ef_change','baseline_kernel','kernel','kernel_change')) and r['opening']['ef']==s[r['year'],r['pooled']]['opening']['ef'] for r in alternatives),len(alternatives))
    family=cost_equity_family_2025(rows)
    interval=[min(r['opening']['ef'] for r in family)/T,max(r['opening']['ef'] for r in family)/T]
    add('2025 cost-equity completion range crosses zero',interval[0]<0<interval[1],dict(completions=len(family),range=interval))
    return out
