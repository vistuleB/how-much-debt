"""Regression checks for sign, binding-year, issuer and sweep coverage failures.
Run: python3 -I paper-prep/test_paper_patterns.py
"""
import contextlib
import copy
import importlib.util
import io
from pathlib import Path
import unittest
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('patterns',P/'paper_patterns.py')
patterns=importlib.util.module_from_spec(s);s.loader.exec_module(patterns)


class Patterns(unittest.TestCase):
 def test_current_sources(self):
  self.assertTrue(all(c['passed'] for c in patterns.evaluate()))

 def test_one_completed_opening_cannot_hide_a_binding_error(self):
  d=patterns.profiles.Data();r=d.get(2010,payout=False,pooled=True)
  k=patterns.profiles.key(r);d.index[False][k]=dict(r,kernel=r['kernel']+1000)
  bad=[c['claim'] for c in patterns.evaluate(d) if not c['passed']]
  self.assertIn('bank equity kept: equality in every completion of those years',bad)

 def test_wrong_equity_sign_is_detected(self):
  d=patterns.profiles.Data()
  for r in d.records:
   if r['year']==2011 and r['representation']=='agency_lookthrough' and r['nonbank_foreign_security_issuers']=='nonbank':
    r['opening']=dict(r['opening'],ef=1)
  self.assertFalse(next(c['passed'] for c in patterns.evaluate(d) if c['claim']=='central bank negative-equity years'))

 def test_issuer_effect_is_not_silently_assumed_zero(self):
  d=patterns.profiles.Data();r=d.get(2025,issuer='bank')
  k=patterns.profiles.key(r);d.index[True][k]=dict(r,kernel=r['kernel']+1000)
  self.assertFalse(next(c['passed'] for c in patterns.evaluate(d) if c['claim']=='foreign-bank issuers: separate columns 4 and 9 unchanged'))

 def test_netting_rounding_interval_rejects_both_outside_edges(self):
  claim='US most generous C / equity-kept kernel in [1.15,1.45), every year/completion'
  for invalid in (1.149999,1.45):
   with self.subTest(ratio=invalid):
    d=patterns.profiles.Data()
    d.metrics(2025)['multilateral_kept_ratio']=invalid
    self.assertFalse(next(c['passed'] for c in patterns.evaluate(d) if c['claim']==claim))

 def test_paper_command_propagates_pattern_failure(self):
  m=patterns.profiles.load('numbers_pattern_test','paper-prep/paper_numbers.py')
  original=m.load
  class Bad:
   @staticmethod
   def evaluate(data=None):return [dict(claim='injected pattern failure',passed=False,actual=False,expected=True)]
  m.load=lambda name,path:Bad if path=='paper-prep/paper_patterns.py' else original(name,path)
  with contextlib.redirect_stdout(io.StringIO()):status=m.main()
  self.assertEqual(status,1)
  self.assertIn('pattern: injected pattern failure',m.FAILURES)


if __name__=='__main__':unittest.main()
