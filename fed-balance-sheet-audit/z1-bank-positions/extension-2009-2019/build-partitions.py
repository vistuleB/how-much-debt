#!/usr/bin/env python3
"""Retain ROW observations and declared ownership completions; no model states.

The one shared Z.1 Document/historian remains authoritative. Sector attribution
is additional completion evidence for the finer adapter, not a second ledger.
"""
import copy
from fractions import Fraction
import hashlib
import json
import sys
from source_profile import ROOT, ExtensionSource
from pathlib import Path
STAGE=Path(__file__).resolve().parent

def write_output(path,text):
    if '--check' in sys.argv:
        if path.read_text()!=text:raise ValueError('stale '+str(path))
    else:path.write_text(text)


OUT=STAGE/'row-split'


def main():
    shared=json.loads((STAGE/'real-world/input.json').read_text())
    src=ExtensionSource()
    assert shared['source_sha256']==hashlib.sha256((ROOT/'raw/z1-20260319-csv.zip').read_bytes()).hexdigest()
    partitions=[]
    notes=[
      'D/R ownership is source-completion metadata used to populate DomesticNonbank/RestOfWorld and explicit loan borrowers in the one shared ledger.State. The model adapter reads the resulting state only, not numeric ownership parameters.',
      'Foreign checkable deposits exclude the separately recorded Fed foreign deposit liability; currency remains separate from deposits.',
      'The ROW agency-MBS split is not observed. Select the same underlying/financing share as all nonbank agency holdings, rounded to whole millions. No issuer guarantee is counted a second time.',
      'Foreign depository-institution loan liabilities are assigned to the selected bank population. Remaining foreign loan liabilities after known Treasury loans are nonbank-held; Fed mortgage holdings are domestic. L.216 identifies direct foreign-owned loan assets as US nonfinancial-business loans plus US broker-dealer cash accounts; their borrowers are domestic, not an unobserved foreign alternative. Some other holder assignments remain completion assumptions.',
      'Foreign-held nonbank J includes observed CP/municipals/corporate bonds and agency issuer claims. Unidentified foreign holdings of selected-bank corporate bonds are assigned to domestic holders; this is an ownership completion, not an observed bilateral matrix.',
      'Foreign eligible Fed claims include foreign deposits plus L.109 FL712151115, identified as the foreign official repo pool by the March 2026 Z.1 footnote and H.4.1. The 2025 quarter-end amount matches H.4.1 exactly. RRP operations are not reassigned abroad. The old zero-pool assignment is retained only as a named historical allocation sensitivity, not the source-supported headline. The total repo marginal bound does not identify any additional bilateral placement.',
      'Foreign bank funding includes observed foreign interbank liabilities and foreign-office intercompany debt. Remaining bank funding is assigned domestic.',
      'Issuer labels on J have no repayment permission and do not change its kernel. Identifiable foreign interbank/Fed reserve claims and foreign bonds receive R labels; unresolved issuer holdings are assigned D. The nonbank net-assets diagnostic is within this selected perimeter, not national net worth.',
    ]
    def holding(case,holder,kind,name=None):
        return sum(v['value'] for v in case['positions'] if v['holder']==holder and v['instrument']['type']==kind and (name is None or v['instrument'].get('name')==name))
    for case in shared['cases']:
        year=case['year'];v=lambda t,c:src.value(t,year,c)
        tp=Fraction(v('l210','FL313161105'),v('l210','FL893061105'))
        ap=Fraction(v('l211','FL893161705'),v('l211','FL893061705'))
        foreign_agency=round(v('l133','LM263061705')*ap)
        nonbank_agency=holding(case,'Nonbank','AgencyBond')+holding(case,'Nonbank','AgencyMortgageSecurity')
        nonbank_mbs=holding(case,'Nonbank','AgencyMortgageSecurity')
        foreign_mbs=round(Fraction(foreign_agency*nonbank_mbs,nonbank_agency))
        assert 0<=foreign_mbs<=min(foreign_agency,nonbank_mbs)
        internal_l=sum(v('l202',c) for c in ['FL764112205','FL754112205'])
        internal_a=sum(v('l202',c) for c in ['FL754112205','FL754012205','FL474012205','FL743020005'])
        ff=v('l110','FL704110005')-internal_l-v('l109','FL713068705')-v('l109','FL713022003')
        foreign_total=v('l133','FL264123005')-v('l216','FL263169203')
        foreign_bank=v('l215','FL263168005')
        row={
          'deposits':v('l203','FL263027003')+v('l204','FL263030005')-v('l109','FL713122605'),
          'currency':v('l203','FL263025003'),
          'treasuries':round(v('l133','LM263061105')*tp),
          'fed_claims':v('l109','FL713122605')+v('l109','FL712151115'),
          'bank_funding':ff+v('l110','LM753192305'),
          'foreign_bank_loans':foreign_bank,
          'foreign_nonbank_loans':foreign_total-foreign_bank,
          'foreign_owned_loans':v('l133','FL263069005'),
          'foreign_agency':foreign_agency,'foreign_mbs':foreign_mbs,
          'foreign_securities':sum(v('l133',c) for c in ['LM263069103','LM263062003','LM263063005']),
          'domestic_foreign_bonds':v('l133','LM263163005')-v('l106','FL313063005')-v('l109','FL713011525'),
          'bank_foreign_j':v('l110','FL704010005')-internal_a-v('l109','FL713113003')+v('l110','LM763092305'),
          'fed_foreign_j':sum(v('l109',c) for c in ['FL713091103','FL713011525','FL713011515']),
          'treasury_foreign_loans':v('l216','FL263169203'),
        }
        assert row['foreign_owned_loans']==v('l216','FL263069500')+v('l216','FL263067005')
        assert min(row.values())>=0,(year,row)
        partitions.append(dict(id=case['id'],partition=row,foreign_repo_max=min(v('l109','FL712151003'),v('l207','FL262051005'))))
    # Preserve original raw observations and add only previously absent source
    # cells. Derived nonbank allocations remain choices in the partition list.
    doc=copy.deepcopy(shared)
    keys={(x['table'],x['date'],x['series']) for x in doc['observations']}
    labels={}
    for t in src.tables:
        for line in src.z.read('data_dictionary/'+t+'.txt').decode().splitlines():
            c,label,*_=line.split('\t');labels[t,c]=label.strip()
    for key,value in src.used.items():
        t,rest=key.split(':',1);date,c=rest.rsplit(':',1)
        if (t,date,c) not in keys:
            doc['observations'].append(dict(year=int(date[:4]),date=date,table=t,series=c,label=labels[t,c],raw=str(value)))
    doc['observations'].sort(key=lambda x:(x['year'],x['table'],x['series']))
    output=dict(format_version=2,shared_input_sha256=hashlib.sha256((STAGE/'real-world/input.json').read_bytes()).hexdigest(),shared_source_input=doc,notes=notes,partitions=partitions)
    OUT.mkdir(exist_ok=True)
    write_output(OUT/'input.json',json.dumps(output,indent=2)+'\n')
    print(f'{len(partitions)} ownership completions; {len(doc["observations"])} retained source cells; no model state or kernel emitted')


if __name__=='__main__':main()
