"""Coverage, signed-float source bridge and deliberately incomplete 2000 state."""
import hashlib,importlib.util,json,unittest
from pathlib import Path
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent
spec=importlib.util.spec_from_file_location('early_source',STAGE/'source_profile.py');profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
class Tests(unittest.TestCase):
 def test_previous_artifacts_unchanged(self):
  for name,sha in json.loads((STAGE/'baseline-inputs.json').read_text())['unchanged_baseline'].items():self.assertEqual(hashlib.sha256((BASE/name).read_bytes()).hexdigest(),sha,name)
 def test_no_invented_completion_for_2000(self):
  d=json.loads((STAGE/'real-world/input.json').read_text())
  self.assertEqual(len(d['cases']),42);self.assertEqual({x['year'] for x in d['cases']},set(range(2001,2008)))
  unknown=[x for x in d['observations'] if x['raw']=='ND']
  self.assertEqual([(x['year'],x['series']) for x in unknown],[(2000,'FL703139105.Q')])
  self.assertFalse(any(x['year']==2000 and x['table'] in ['s61a','s62a'] for x in d['observations']))
  self.assertEqual(json.loads((STAGE/'real-world/source-derivations.json').read_text()),{})
 def test_absence_is_not_published_nd(self):
  cov=json.loads((STAGE/'source-coverage.json').read_text());y=cov['years'][0]
  self.assertEqual(y['year'],2000);self.assertFalse(y['completed'])
  self.assertEqual(sum(r['reason']=='published_ND' for r in y['missing']),1)
  self.assertEqual(sum(r['reason']=='period_absent' and r['raw'] is None for r in y['missing']),4)
  self.assertTrue(all(not x['missing'] for x in cov['years'][1:]))
  self.assertEqual(cov['financial_sector_nonfinancial_assets_2000']['value'],1019061)
 def test_partial_historian_preserves_core_only(self):
  d=json.loads((STAGE/'real-world/partial-2000.json').read_text())
  self.assertEqual((d['year'],d['units'],len(d['known_positions'])),(2000,'USD billions',8))
  self.assertEqual(d['measurement_constraints'],139)
  self.assertFalse(any(p['instrument']['type']=='PhysicalAsset' for p in d['known_positions']))
  values={(p['holder'],p['instrument']['type']):p['value'] for p in d['known_positions']}
  self.assertEqual(values['Nonbank','Deposit'],4896.231);self.assertEqual(values['Nonbank','Currency'],517.66)
 def test_both_float_signs_close_the_source_sheet(self):
  for y in range(2001,2008):
   s=profile.ExtensionSource();r=profile.interpret_positions(s,y,'holder_correction','source_net_assets','observed_us_mix');v=lambda t,c:s.value(t,y,c)
   amount=v('l109','FL713022003');entries=[x for x in r['valuation_projections'] if x['position']=='Fed.locked_float_asset']
   self.assertEqual(len(entries),int(amount>0))
   if amount>0:self.assertEqual(entries[0]['delta'],amount)
   expected=v('l109','FL714090005')+v('s61a','LM712010095')-v('l109','FL714190005')+r['bridges']['fed_valuation_projection']-max(0,-v('l109','FL713193005'))
   self.assertEqual(profile.real_equity(r['real_holdings'],'Fed'),expected)
  with self.assertRaises(KeyError):profile.interpret_positions(profile.ExtensionSource(),2000,'holder_correction','source_net_assets','observed_us_mix')
 def test_complete_projections_and_broad_profiles(self):
  rows=json.loads((STAGE/'row-split/check.json').read_text())['scenarios']
  self.assertEqual(len(rows),84);self.assertEqual(len({r['id'] for r in rows}),84)
  self.assertEqual({r['year'] for r in rows},set(range(2001,2008)))
  rows=json.loads((STAGE/'broad-debt/results.json').read_text())['records'];self.assertEqual(len(rows),672)
 def test_no_blind_stock_flow_backcast(self):
  probes=json.loads((STAGE/'source-coverage.json').read_text())['stock_flow_backcast_diagnostic']
  fed,bank=probes
  self.assertEqual(fed['control_error'],0);self.assertLessEqual(fed['max_observed_absolute_error'],1)
  self.assertEqual(bank['control_error'],6258);self.assertEqual(bank['max_observed_absolute_error'],13522)
  self.assertFalse(any(p['applied'] for p in probes))
 def test_backend_parity_and_series(self):
  d=json.loads((STAGE/'backend-parity.json').read_text());self.assertEqual(len(d['sha256']),4)
  for name,sha in d['sha256'].items():self.assertEqual(hashlib.sha256((STAGE/name).read_bytes()).hexdigest(),sha)
  d=json.loads((STAGE/'annual-series.json').read_text());self.assertEqual([y['year'] for y in d['years']],list(range(2001,2026)))
  self.assertEqual(sum(y['states'] for y in d['years']),480)
  self.assertEqual(d['partial_years'][0]['status'],'not_completed');self.assertNotIn('kernel',d['partial_years'][0])
if __name__=='__main__':unittest.main()
