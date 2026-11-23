# Isolated backfill profile copied from source_interpretation.py at 13a3f2d.
# Changes: source root and supported years only initially; year-specific fixes
# are recorded here and in README.md. Existing US artifacts stay unchanged.
#!/usr/bin/env python3
"""Z.1 source interpretation, independent of every model.

Retains legal instruments and ownership in the shared real-world vocabulary.
Explicit valuation/reconciliation choices construct conditional endpoint holdings;
missing observations remain in the raw measurement record. No model coordinates,
kernels or conversion permissions are produced by this module.
"""
from fractions import Fraction
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'raw/z1-20260319-csv.zip'

class Source:
    def __init__(self, archive=ARCHIVE):
        expected=json.loads((ROOT/'source-manifest.json').read_text())['sha256']
        if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != expected:
            raise ValueError('Fixed-vintage archive hash changed')
        self.z = zipfile.ZipFile(archive)
        self.tables = {}
        self.used = {}

    def value(self, table, year, code):
        if table not in self.tables:
            self.tables[table] = {r['date']: r for r in csv.DictReader(io.StringIO(
                self.z.read('csv/' + table + '.csv').decode('utf-8-sig')))}
        code += '.A' if table.startswith('s') else '.Q'
        stamp = str(year) if table.startswith('s') else f'{year}:Q4'
        raw = self.tables[table][stamp][code]
        if raw == 'ND':
            raise ValueError((table, stamp, code, 'missing'))
        val = int(raw)
        self.used[f'{table}:{stamp}:{code}'] = val
        return val


class ExtensionSource(Source):
    def __init__(self):
        super().__init__()
        self.derivations={}

    def value(self, table, year, code):
        try:
            return super().value(table,year,code)
        except ValueError as error:
            if error.args != (('s62a','2025','LM702010095.A','missing'),):
                raise
            # The IMA identity is independently checked on 2008 and 2020 by
            # build.py. Here the total and the other three terms are observed.
            terms={
                'IMA_net_worth': self.value('s62a',year,'FL702090095'),
                'equity_instruments': self.value('l110',year,'FL703181105'),
                'financial_assets': self.value('l110',year,'FL704090005'),
                'financial_liabilities': self.value('l110',year,'FL704190005'),
            }
            amount=terms['IMA_net_worth']+terms['equity_instruments']-terms['financial_assets']+terms['financial_liabilities']
            assert amount>=0
            self.derivations['s62a:2025:LM702010095.A']=dict(
                raw='ND',value=amount,units='USD millions',terms=terms,
                formula='IMA net worth + equity instruments - financial assets + financial liabilities',
                status='Derived from published accounting controls, not a directly observed component or carry-forward')
            return amount


def interpret_positions(src, year, bank_correction, fed_correction, allocation,
             signed_misc_policy="economic_equity", fed_valuation="common"):
    allowed_fed=['equity_correction','asset_correction'] if year >= 2020 else ['source_net_assets']
    if signed_misc_policy not in ["economic_equity", "locked_contra_asset"]:
        raise ValueError("Unknown signed miscellaneous-position policy")
    if fed_valuation not in ['common', 'fed_amortized_cost'] or (fed_valuation != 'common' and year < 2021):
        raise ValueError('Unknown or unavailable Fed valuation policy')
    if year not in range(2000,2008) or bank_correction not in ['holder_correction','issuer_correction'] or fed_correction not in allowed_fed or allocation not in ['minimum','observed_us_mix','maximum']:
        raise ValueError('Unknown benchmark or calibration policy')
    v = lambda t, c: src.value(t, year, c)
    corrections = []
    projections = []
    def correct(position, amount, reason):
        if amount:
            corrections.append(dict(position=position, delta=amount, units='USD millions', reason=reason))

    # Source holder values are not repayment principal. Use one explicit common
    # face-normalization factor for each Treasury/agency universe, then round.
    treasury_face = v('l210', 'FL313161105')
    treasury_market = v('l210', 'FL893061105')
    tp = Fraction(treasury_face, treasury_market)
    b_b = round(v('l110', 'LM703061105') * tp)
    b_f = round(v('l109', 'LM713061103') * tp)
    bonds = treasury_face + v('l210', 'FL313169205')
    b_h = bonds-b_b-b_f
    def project(position, amount, reason):
        if amount:
            projections.append(dict(position=position, delta=amount, units='USD millions', reason=reason))
    project('B_B', b_b-v('l110', 'LM703061105'), 'Common Treasury market-to-face projection; uniform price across holders, not observed holder-specific face value.')
    project('B_F', b_f-v('l109', 'LM713061103'), 'Same Treasury face-normalization policy.')

    agency_face = v('l211', 'FL893161705')
    agency_market = v('l211', 'FL893061705')
    ap = Fraction(agency_face, agency_market)
    bank_agency = round(v('l110', 'LM703061705')*ap)
    fed_agency = round(v('l109', 'LM713061705')*ap)
    fed_agency_factor = ap
    if fed_valuation == 'fed_amortized_cost':
        # The Treasury/agency amortized-cost components sum to the memo total.
        # Amortized cost is a sensitivity, not observed holder-specific par.
        target = v('l109', 'FL714022065')
        assert target > 0
        b_f = v('l109', 'FL713061163')
        fed_agency = v('l109', 'FL713061765')
        assert b_f + fed_agency == target
        fed_agency_factor = Fraction(fed_agency, v('l109', 'LM713061705'))
        b_h = bonds-b_b-b_f
        project('B_F', b_f-round(v('l109','LM713061103')*tp), 'Fed-only amortized-cost sensitivity: published Treasury component; nonbank residual absorbs reallocation, aggregate Treasury face fixed.')
        assert b_h >= 0
    gov_agency = round(v('l211', 'FL313061703')*ap)
    project('bank_agency_total', bank_agency-v('l110','LM703061705'), 'Common agency market-to-face projection; no holder-specific price inferred.')
    project('fed_agency_total', fed_agency-v('l109','LM713061705'), 'Same common agency normalization.' if fed_valuation == 'common' else 'Fed-only amortized-cost sensitivity; published agency component and proportional agency MBS split, not observed holder-specific par.')
    us_agency = round(v('l111', 'LM763061705')*ap)
    us_mbs_market = sum(v('l111', c) for c in ['LM763061805','LM763061503','LM763061603','LM763061403'])
    assert us_mbs_market+v('l111','LM763061795') == v('l111','LM763061705')
    us_mbs = round(us_mbs_market*ap)
    unsplit = bank_agency-us_agency
    share = dict(minimum=Fraction(0), observed_us_mix=Fraction(us_mbs_market,v('l111','LM763061705')), maximum=Fraction(1))[allocation]
    bank_mbs = us_mbs+round(unsplit*share)
    fed_mbs = round(v('l109','LM713061903')*fed_agency_factor)
    pool_principal = v('l126','FL413065005')+v('l125','FL403065195')+v('l125','FL403065495')
    assert 0 <= bank_mbs <= bank_agency and 0 <= fed_mbs <= fed_agency
    assert bank_mbs+fed_mbs <= pool_principal <= agency_face
    # Government agency holdings are conservatively assigned to issuer debt in
    # this completion; the source does not give its exact MBS split here.
    agency_direct = agency_face-pool_principal
    assert bank_agency-bank_mbs+fed_agency-fed_mbs+gov_agency <= agency_direct

    internal_a = sum(v('l202', c) for c in ['FL754112205','FL754012205','FL474012205','FL743020005'])
    internal_l = sum(v('l202', c) for c in ['FL764112205','FL754112205'])
    discrepancy = internal_a-internal_l
    assert discrepancy == -v('l202','FL904010005')
    if bank_correction == 'holder_correction':
        correct('source.internal_bank_assets', -discrepancy, 'Trust published issuer-side internal liabilities; correct holder aggregate and asset total before eliminating matched claims.')
        corrected_internal = internal_l
    else:
        correct('source.internal_bank_liabilities', discrepancy, 'Trust published holder-side internal assets; correct issuer aggregate and liability total before eliminating matched claims.')
        corrected_internal = internal_a
    correct('source.bank_net_assets', -discrepancy, 'Both internal-claim correction routes reduce measured net assets equally; after consolidation their state coordinates coincide.')

    r = v('l109','FL713113003')
    u = v('l109','FL713068705')
    float_ = v('l109','FL713022003')
    # Both signs are published historically; keep positive float as an asset.
    foreign_assets = v('l110','FL704010005')-internal_a-r
    foreign_funding = v('l110','FL704110005')-internal_l-u-float_
    assert min(foreign_assets, foreign_funding) >= 0
    gov_check = v('l203','FL763123005')
    gov_time = v('l204','FL313030003')
    m = v('l110','FL703127005')+v('l110','FL703130005')-gov_check-gov_time
    core_loans = v('l110','FL704023005')
    fed_stock = v('l109','FL713164003')
    assert fed_stock <= v('l110','FL703094905')
    n_b = -fed_stock+sum(v('l110',c) for c in ['LM703064105','LM763092100','FL703094905','LM703064205'])+v('s62a','LM702010095')
    qb_h = foreign_funding+sum(v('l110',c) for c in ['FL702150005','FL704122005','FL703169005','LM753192305'])
    qb_res = gov_check+gov_time+v('l110','FL763178000')+v('l110','FL703190005')
    xb_res = v('l110','FL703090005')-float_+fed_stock
    jb = foreign_assets+sum(v('l110',c) for c in ['FL403197033','FL702050005','FL703069175','LM703062005','LM703063005','LM763092305','FL763040005'])
    cb, ch = v('l110','FL703025005'), v('l109','FL713125005')

    # Loan book: published loan instruments, excluding Treasury nonmarketable
    # securities, bank funding, Treasury-owned loans and direct Fed facilities.
    # Agency look-through redistributes underlying principal; it does not add it.
    loans = v('l214','FL894123005')-v('l106','FL314123005')-v('l110','FL703169005')-v('l106','FL314023005')-v('l109','FL713068005')
    agency_h = agency_face-bank_agency-fed_agency-gov_agency
    sec_jh = v('l209','FL893169175')+v('l212','FL893062005')+v('l213','FL893063005')-v('l110','FL703069175')-v('l110','LM703062005')-v('l110','LM703063005')-v('l110','FL704122005')-v('l106','FL313063005')-v('l109','FL713011525')
    assert sec_jh >= 0
    # Preserve legal claims and underlying loans separately. Looking through
    # agency financing is an adapter policy, not a source interpretation.
    jb += bank_agency
    jf_agency = fed_agency
    lh = loans-core_loans
    assert min(lh,sec_jh,jb) >= 0

    # Gross signed float/net-IMF positions onto existing opposite-sheet classes.
    # Each is an observed signed item, not a new balancing position.
    imf = v('l109','FL713011405')
    assert imf <= 0
    signed_misc = v('l109','FL713193005')
    contra = max(0, -signed_misc)
    q_lock = max(0, signed_misc)-min(0,float_)-imf
    q_h = sum(v('l109',c) for c in ['FL713124005','FL713129005','FL713122605','FL712151003'])
    t = v('l109','FL713123005')
    nf = v('s61a','LM712010095')+v('l109','FL713064103')
    jf = jf_agency+sum(v('l109',c) for c in ['FL713011515','FL713091103','FL712051005','FL713011525','FL713068005'])
    locked = max(0,float_)+sum(v('l109',c) for c in ['FL713012003','FL713011203','FL713014003','FL713093005'])
    if float_>0:
        project('Fed.locked_float_asset',float_,'Retain observed positive clearing float in existing locked Fed assets; negative float remains a liability. No balancing plug or zero substitution.')
    # Published rounded leaf totals exceed the financial-asset control by $1m.
    leaves = sum(v('l109',c) for c in ['FL714010005','FL713012003','FL713011405','FL712051005','LM714022005','FL713068005','FL713064103','FL713090005'])
    rounding = v('l109','FL714090005')-leaves
    assert abs(rounding) <= 1
    locked += rounding
    correct('Fed.unidentified_misc_assets', rounding, 'Published leaf/control rounding; preserve financial-asset control exactly.')
    xf = nf+jf+locked
    bank_val = b_b-v('l110','LM703061105')+bank_agency-v('l110','LM703061705')
    fed_val = b_f-v('l109','LM713061103')+fed_agency-v('l109','LM713061705')
    eb = v('l110','FL704090005')+v('s62a','LM702010095')-v('l110','FL704190005')-discrepancy+bank_val
    source_ef = v('l109','FL714090005')+v('s61a','LM712010095')-v('l109','FL714190005')+fed_val
    remainder = None
    if year >= 2020:
        premium = v('l109','LM714022005')-v('l109','FL714022065')
        reference_ef = v('l109','FL713164005')+v('s61a','LM712010095')+premium+fed_val
        remainder = source_ef-reference_ef
        # Pinned-vintage guard: the bridge above computes this remainder from
        # independent source totals; this assertion does not assign a plug.
        if year == 2020:
            assert remainder == -9796
        if fed_correction == 'equity_correction':
            ef = source_ef
            correct('E_F_reference', remainder, 'Allocate remaining book/source valuation bridge to economic equity; source assets retained.')
        else:
            ef = reference_ef
            locked -= remainder
            xf -= remainder
            correct('Fed.unidentified_misc_assets', -remainder, 'Alternative explicit upstream correction to the existing asset series; reference equity retained. This is a scenario, not an observed asset.')
    else:
        assert fed_correction == 'source_net_assets'
        ef = source_ef
    # A negative net liability cannot enter the nonnegative model liability class.
    # Two explicit representations preserve the signed source sheet: remove it
    # against economic equity, or gross it to a locked contra-asset. Neither is
    # an observed gross split or a purchasable asset. Both give the same E_F-X_F.
    if contra:
        if signed_misc_policy == 'economic_equity':
            ef -= contra
            project('E_F', -contra, 'Remove negative net miscellaneous liability from the liability sheet against economic equity; no new asset or transaction.')
        else:
            locked += contra
            xf += contra
            project('X_F_res', contra, 'Gross negative net miscellaneous liability into existing locked contra-assets; not an independently observed asset and not eligible for conversion.')
    assert locked >= 0
    def holding(holder, kind, value, **kwargs):
        return dict(holder=holder,instrument=dict(type=kind,**kwargs),value=value)
    # This is the shared real-world vocabulary, not model coordinates. Unknown
    # residual assets are not asserted to be physical or non-debt. Fed capital
    # stock is a non-debt ownership interest, separately nontransferable.
    holdings = [
        holding('Nonbank','Deposit',m), holding('Banks','Reserves',r),
        holding('Treasury','TreasuryAccount',t),
        holding('Nonbank','Currency',ch), holding('Banks','Currency',cb),
        holding('Nonbank','TreasuryBond',b_h), holding('Banks','TreasuryBond',b_b),
        holding('Fed','TreasuryBond',b_f), holding('Banks','PrivateLoan',core_loans),
        holding('Nonbank','PrivateLoan',lh-pool_principal),
        holding('Agencies','PrivateLoan',pool_principal),
        holding('Treasury','PrivateLoan',v('l106','FL314023005')),
        holding('Fed','FedAdvance',u),
        holding('Banks','AgencyMortgageSecurity',bank_mbs),
        holding('Fed','AgencyMortgageSecurity',fed_mbs),
        holding('Nonbank','AgencyMortgageSecurity',pool_principal-bank_mbs-fed_mbs),
        holding('Banks','AgencyBond',bank_agency-bank_mbs),
        holding('Fed','AgencyBond',fed_agency-fed_mbs),
        holding('Treasury','AgencyBond',gov_agency),
        holding('Nonbank','AgencyBond',agency_direct-(bank_agency-bank_mbs)-(fed_agency-fed_mbs)-gov_agency),
        holding('Banks','PhysicalAsset',v('s62a','LM702010095'),name='nonfinancial_assets'),
        holding('Banks','NonDebtAsset',v('l110','LM703064105'),name='corporate_equity'),
        holding('Banks','NonDebtAsset',v('l110','LM763092100'),name='direct_investment_equity'),
        holding('Banks','NonDebtAsset',v('l110','FL703094905')-fed_stock,name='miscellaneous_equity'),
        holding('Banks','NonDebtAsset',v('l110','LM703064205'),name='investment_fund_shares'),
        holding('Banks','NonDebtAsset',fed_stock,name='central_bank_capital_stock'),
        holding('Banks','UnclassifiedAsset',xb_res-fed_stock,name='miscellaneous_bank_assets'),
        holding('Fed','PhysicalAsset',v('s61a','LM712010095'),name='nonfinancial_assets'),
        holding('Fed','NonDebtAsset',v('l109','FL713064103'),name='corporate_equity'),
        holding('Fed','UnclassifiedAsset',locked,name='monetary_and_unidentified_assets'),
        holding('Banks','OtherClaim',jb-bank_agency,name='external_financial_claims',debtor='Nonbank'),
        holding('Fed','OtherClaim',jf-fed_agency,name='external_financial_claims',debtor='Nonbank'),
        holding('Nonbank','OtherClaim',sec_jh,name='other_securities',debtor='Nonbank'),
        holding('Nonbank','OtherClaim',qb_h,name='external_bank_funding',debtor='Banks'),
        holding('Treasury','Deposit',gov_check+gov_time),
        holding('Nonbank','OtherClaim',qb_res-gov_check-gov_time,name='other_bank_liabilities',debtor='Banks'),
        holding('Nonbank','OtherClaim',q_h,name='deposits_and_reverse_repos',debtor='Fed'),
        holding('Nonbank','OtherClaim',q_lock,name='other_central_bank_liabilities',debtor='Fed'),
    ]
    assert all(h['value'] >= 0 for h in holdings)
    assert real_equity(holdings,'Banks') == eb
    assert real_equity(holdings,'Fed') == ef
    core_asset_cap = v('l110','FL704090005')+v('s62a','LM702010095')-v('l110','LM703061105')-core_loans-r-cb-float_
    result = dict(year=year,bank_correction=bank_correction,fed_correction=fed_correction,
                  mbs_allocation=allocation,real_holdings=holdings,
                  corrections=corrections,valuation_projections=projections,
                bridges=dict(treasury_face_factor=str(tp),agency_face_factor=str(ap),bank_agency_face=bank_agency,
                             bank_observed_us_mbs_market=us_mbs_market,bank_us_mbs_face=us_mbs,
                             bank_unsplit_agency_face=unsplit,bank_mbs_face=bank_mbs,fed_mbs_face=fed_mbs,
                             underlying_securitized_mortgage_principal=pool_principal,loan_total=loans,
                             internal_matched_elimination=corrected_internal,internal_discrepancy=discrepancy,
                             bank_valuation_projection=bank_val,fed_valuation_projection=fed_val,
                             fed_remainder=remainder,fed_locked_assets=locked,
                             signed_misc_liabilities=signed_misc,negative_misc_contra=contra,
                             signed_misc_policy=signed_misc_policy,
                             sigma_conservative_other_asset_cap=core_asset_cap,
                             sigma_threshold=m+ch+u))

    if year in [2008,2020]:
        for key in ["signed_misc_liabilities", "negative_misc_contra", "signed_misc_policy"]:
            del result["bridges"][key]
    return result


def real_equity(holdings, actor):
    debtors={'Deposit':'Banks','FedAdvance':'Banks','Reserves':'Fed',
             'TreasuryAccount':'Fed','Currency':'Fed','TreasuryBond':'Treasury',
             'PrivateLoan':'Nonbank','AgencyBond':'Agencies','AgencyMortgageSecurity':'Agencies'}
    return sum(h['value']*((h['holder']==actor)-(h['instrument'].get('debtor',debtors.get(h['instrument']['type']))==actor)) for h in holdings)
