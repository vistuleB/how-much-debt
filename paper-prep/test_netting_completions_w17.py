"""Regression checks for security eligibility and completion-envelope scope."""
import importlib.util,json,subprocess,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('netting_completion_checks',P/'netting_completions_w17.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Netting(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=m.build()
 def test_all_years_and_completions(self):
  self.assertEqual([r['year'] for r in self.d['years']],list(range(2001,2026)))
  self.assertEqual(sum(r['completions'] for r in self.d['years']),240)
  self.assertTrue(all(r['passed'] for r in m.patterns(self.d)))
 def test_upper_selector_is_not_the_favourable_endpoint(self):
  rows=json.loads(subprocess.check_output([sys.executable,'-I',str(P/'broad-debt/bank_equity_kept.py'),'--json']))
  for r in self.d['years']:
   x=next(x for x in rows if x['year']==r['year'])
   self.assertAlmostEqual(x['netting_not_repayable'],r['netting'][1],places=6)
  self.assertGreater(self.d['years'][-1]['netting'][1]-self.d['years'][-1]['netting'][0],.28)
 def test_nonrepayable_security_cannot_be_cancelled(self):
  o={k:0 for k in ('s_d','s_r','a_td','a_tr','z_td','z_tr','d_b','r_b','d_qbh','r_qbh','d_qh','r_qh')}
  o['z_dd']=10
  self.assertEqual(m.netting(o,10),10)
  self.assertEqual(m.netting(o,10,True),0)
if __name__=='__main__':unittest.main()
