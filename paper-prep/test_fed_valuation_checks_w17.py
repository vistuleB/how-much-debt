"""Regression checks for failure propagation of the new Fed-valuation claims."""
import copy
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('fed_checks',ROOT/'paper-prep/fed_valuation_checks_w17.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class FedChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=m.read()
 def test_stored_claims(self):
  self.assertTrue(all(r['passed'] for r in m.patterns(self.rows)))
  self.assertTrue(all(f'{exact:.2f}'==printed for _,printed,exact in m.numbers(self.rows)))
 def test_missing_selected_case_is_rejected(self):
  selected=m.selected(self.rows);target=selected[2025,True]
  with self.assertRaises(ValueError):m.selected([r for r in self.rows if r is not target])
 def test_pooled_change_is_not_hidden_by_consistent_delta(self):
  bad=copy.deepcopy(self.rows);r=m.selected(bad)[2025,True]
  r['kernel']+=1;r['kernel_change']+=1
  found=[x for x in m.patterns(bad) if not x['passed']]
  self.assertTrue(any('pooled kernel unchanged' in r['claim'] for r in found))
 def test_range_requires_the_nonheadline_upper_completion(self):
  family=m.cost_equity_family_2025(self.rows)
  upper=max(family,key=lambda r:r['opening']['ef'])
  self.assertEqual(upper['opening']['ef'],60488)
  self.assertNotEqual(upper['id'],m.selected(self.rows)[2025,False]['id'])
  with self.assertRaises(ValueError):m.numbers([r for r in self.rows if r is not upper])
 def test_nonheadline_earlier_case_cannot_be_omitted(self):
  target=next(r for r in self.rows if r['year']==2022 and r['issuer']=='bank')
  bad=[r for r in self.rows if r is not target]
  self.assertTrue(any('complete unique' in x['claim'] and not x['passed'] for x in m.patterns(bad)))
 def test_nonheadline_separate_delta_is_checked(self):
  bad=copy.deepcopy(self.rows)
  r=next(r for r in bad if r['year']==2022 and r['issuer']=='bank' and not r['pooled'])
  r['kernel']+=1;r['kernel_change']+=1
  self.assertTrue(any('separate changes equal' in x['claim'] and not x['passed'] for x in m.patterns(bad)))
 def test_source_unit_mistake_changes_printed_equity(self):
  bad=copy.deepcopy(self.rows);r=m.selected(bad)[2025,False];r['ef_change']*=1000
  self.assertTrue(any(f'{value:.2f}'!=printed for _,printed,value in m.numbers(bad)))
if __name__=='__main__':unittest.main()
