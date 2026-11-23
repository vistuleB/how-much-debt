"""Source/coverage/isolation checks; formula and replay checks run separately."""
import hashlib,importlib.util,json,unittest
from pathlib import Path
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent
class BackfillTests(unittest.TestCase):
 def test_no_legacy_artifact_changed(self):
  manifest=json.loads((STAGE/'baseline-inputs.json').read_text())
  for name,sha in manifest['unchanged_baseline'].items():self.assertEqual(hashlib.sha256((BASE/name).read_bytes()).hexdigest(),sha,name)
 def test_profile_only_changes_root_and_year_guard(self):
  original=(BASE/'source_interpretation.py').read_text()
  expected=original.replace('ROOT=Path(__file__).resolve().parent','ROOT=Path(__file__).resolve().parents[1]').replace('year not in [2008,2020,2021,2022,2023,2024,2025]','year not in range(2009,2020)')
  expected=expected.rstrip()+'\n'
  actual=(STAGE/'source_profile.py').read_text()
  self.assertTrue(actual.endswith(expected))
  self.assertEqual(len(actual)-len(expected),actual.index(original.splitlines()[0]))
 def test_all_years_without_missing_stock_fills(self):
  d=json.loads((STAGE/'real-world/input.json').read_text())
  self.assertEqual(sorted({x['year'] for x in d['cases']}),list(range(2009,2020)))
  self.assertEqual(len(d['cases']),72)
  self.assertEqual(len({x['id'] for x in d['cases']}),72)
  self.assertFalse(any(x['raw']=='ND' for x in d['observations']))
  self.assertEqual(json.loads((STAGE/'real-world/source-derivations.json').read_text()),{})
  for y in range(2009,2020):
   rows=[x for x in d['cases'] if x['year']==y]
   self.assertEqual(len(rows),12 if y==2009 else 6)
   self.assertTrue(all('/source_net_assets/' in x['id'] for x in rows))
 def test_observed_ima_and_reserve_controls(self):
  d=json.loads((STAGE/'source/source-bridges.json').read_text())
  self.assertEqual(len(d['benchmarks']),11)
  for x in d['benchmarks']:
   self.assertEqual(x['bank_nonfinancial_status'],'observed')
   for k in ['bank_IMA_bridge_error','fed_IMA_bridge_error','reserve_subsector_bridge_error']:self.assertEqual(x[k],0)
 def test_existing_and_new_ids_disjoint(self):
  new=json.loads((STAGE/'row-split/check.json').read_text())['scenarios'];old=json.loads((BASE/'row-split/check.json').read_text())['scenarios']
  self.assertEqual(len(new),144);self.assertEqual(len({x['id'] for x in new}),144)
  self.assertFalse({x['id'] for x in new}&{x['id'] for x in old})
  for y in range(2009,2020):self.assertEqual({s['representation'] for s in new if s['year']==y},{'agency_lookthrough','security_outside_D'})
 def test_continuous_published_series(self):
  d=json.loads((STAGE/'annual-series.json').read_text())
  self.assertEqual([y['year'] for y in d['years']],list(range(2008,2026)))
  self.assertEqual(sum(y['states'] for y in d['years']),396)
  for y in d['years']:
   self.assertEqual(y['deposits']+y['currency'],y['nonbank_money'])
   self.assertEqual(len(y['restrictive']),4)
 def test_backend_record(self):
  d=json.loads((STAGE/'backend-parity.json').read_text())
  self.assertEqual(d['backends'],['erlang','javascript'])
  for name,sha in d['sha256'].items():self.assertEqual(hashlib.sha256((STAGE/name).read_bytes()).hexdigest(),sha)
 def test_broad_coverage(self):
  d=json.loads((STAGE/'broad-debt/results.json').read_text())
  self.assertEqual(len(d['records']),1152)
  ids={(r['id'],r['pooled'],r['securities_repayable'],r['nonbank_foreign_security_issuers']) for r in d['records']}
  self.assertEqual(len(ids),1152)
if __name__=='__main__':unittest.main()
