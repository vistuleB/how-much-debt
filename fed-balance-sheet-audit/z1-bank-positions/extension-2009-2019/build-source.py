#!/usr/bin/env python3
"""Model-independent source interpretation for the shared Gleam ledger pipeline.

No model-coordinate or kernel fields are emitted. Python handles the archived
CSV container and explicit source interpretation policies. Gleam marshals this
JSON into DataPacket, runs the shared historian, completes shared ledger.State
anchors, and performs the model-specific projection.
"""
import itertools
import json
import sys
import hashlib
from source_profile import ROOT, interpret_positions, ExtensionSource
from pathlib import Path
STAGE=Path(__file__).resolve().parent

def write_output(path,text):
    if '--check' in sys.argv:
        if path.read_text()!=text:raise ValueError('stale '+str(path))
    else:path.write_text(text)



OUT=STAGE/'source'
YEARS=list(range(2009,2020))


def refresh_source_bridges(src):
    """Source-only controls/policies; no model completion or diagnostic code."""
    OUT.mkdir(exist_ok=True)
    mapping=json.loads((ROOT/'series-mapping.json').read_text())['entries']
    bridges=[]
    for year in YEARS:
        values={e['table']+':'+e['series']:src.value(e['table'],year,e['series'][:-2]) for e in mapping}
        v=lambda t,c:src.value(t,year,c)
        bank_n=v('s62a','LM702010095')
        bank_net=v('l110','FL704090005')+bank_n-v('l110','FL704190005')
        fed_net=v('l109','FL714090005')+v('s61a','LM712010095')-v('l109','FL714190005')
        assert bank_net-v('l110','FL703181105')==v('s62a','FL702090095')
        assert fed_net-v('l109','FL713164005')==v('s61a','FL712090095')
        reserves=sum(v('l202',c) for c in ['FL763013005','FL753013003','FL743013003','FL473013005'])
        assert reserves==v('l109','FL713113003')
        bridges.append(dict(year=year,source_values=values,bank_net_assets=bank_net,
            fed_signed_source_net_assets=fed_net,bank_nonfinancial=bank_n,
            bank_nonfinancial_status='observed',
            bank_IMA_check_status='independent published-component check',
            bank_IMA_bridge_error=0,fed_IMA_bridge_error=0,reserve_subsector_bridge_error=0))
    policy=dict(format_version=1,base_policy='calibration-policy.json',
        base_policy_sha256=hashlib.sha256((ROOT/'calibration-policy.json').read_bytes()).hexdigest(),
        years=YEARS,reference_bridge='Source net-assets Fed equity, as in 2008; no extrapolation of the 2020 valuation remainder or its equity/asset correction family.',
        signed_misc='When negative: either remove the signed contra-liability against E_F (headline), or gross it into existing locked X_F_res. Both keep liabilities nonnegative; neither invents an eligible asset. They give identical E_F-X_F and kernel/potential diagnostics. The net observation does not identify the underlying gross split.',
        missing_data='All required 2009–2019 observations are present; no interpolation, carry-forward or missing-stock derivation used.',
        limits='Same conditional eligibility, price, perimeter and pooling assumptions as the baseline. Annual endpoints and funded instantaneous reductions, not an identified intervening transaction history.')
    write_output(OUT/'extension-policy.json',json.dumps(policy,indent=2)+'\n')
    source_hash=hashlib.sha256((ROOT/'raw/z1-20260319-csv.zip').read_bytes()).hexdigest()
    write_output(OUT/'source-bridges.json',json.dumps(dict(format_version=1,units='USD millions',source_sha256=source_hash,status='source-only bridges; all nonfinancial components observed',model_states_emitted=0,benchmarks=bridges,derivations=src.derivations),indent=2)+'\n')


def main():
    src=ExtensionSource()
    refresh_source_bridges(src)
    cases=[]
    for year in YEARS:
        feds=['source_net_assets']
        signed=src.value('l109',year,'FL713193005')
        signed_policies=['economic_equity','locked_contra_asset'] if signed<0 else ['economic_equity']
        for bank,fed,allocation,policy in itertools.product(['holder_correction','issuer_correction'],feds,
                ['minimum','observed_us_mix','maximum'],signed_policies):
            real=interpret_positions(src,year,bank,fed,allocation,policy)
            identifier=f'{year}/{bank}/{fed}/{allocation}'
            if policy!='economic_equity':identifier+='/'+policy
            notes=[json.dumps(record,sort_keys=True) for record in real['corrections']+real['valuation_projections']]
            notes+=['Nonbank non-debt baseline is selected as zero; unlisted holdings are selected as zero within this conditional perimeter. Not observed global absence.',
                    'Source legal agency financing claims are retained separately from underlying loans; no model look-through has occurred.']
            cases.append(dict(id=identifier,year=year,policy=policy,notes=notes,positions=real['real_holdings']))
    mapping=json.loads((ROOT/'series-mapping.json').read_text())['entries']
    for year in YEARS:
        for entry in mapping:src.value(entry['table'],year,entry['series'][:-2])
        for table,code in [('s61a','FL712090095'),('s62a','FL702090095'),('s61a','LM712010095'),('s62a','LM702010095')]:src.value(table,year,code)
    labels={}
    for table in src.tables:
        for line in src.z.read('data_dictionary/'+table+'.txt').decode().splitlines():
            code,label,*_=line.split('\t');labels[(table,code)]=label.strip()
    observations=[]
    for key,value in src.used.items():
        table,rest=key.split(':',1);date,series=rest.rsplit(':',1)
        observations.append(dict(year=int(date[:4]),date=date,table=table,series=series,
            label=labels[(table,series)],raw=str(value)))
    for key,derivation in src.derivations.items():
        table,rest=key.split(':',1);date,series=rest.rsplit(':',1)
        observations.append(dict(year=int(date[:4]),date=date,table=table,series=series,
            label=labels[(table,series)],raw=derivation['raw']))
    observations.sort(key=lambda r:(r['year'],r['table'],r['series']))
    path=STAGE/'real-world'
    path.mkdir(exist_ok=True)
    output=dict(format_version=1,source_sha256=hashlib.sha256((ROOT/'raw/z1-20260319-csv.zip').read_bytes()).hexdigest(),
        units='USD millions',population='Z.1 private depository institutions; monetary authority; federal government; remaining actors pooled as Nonbank',
        valuation='Original controls retained in observations; explicit common Treasury/agency price projections and reconciliation choices in cases',
        observations=observations,cases=cases)
    write_output(path/'input.json',json.dumps(output,indent=2)+'\n')
    write_output(path/'source-derivations.json',json.dumps(src.derivations,indent=2)+'\n')
    print(f'{len(observations)} raw measurements; {len(cases)} shared-ledger completion policies; no model states emitted.')


if __name__=='__main__':main()
