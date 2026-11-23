"""Explicit backend regeneration/parity check, or read-only recorded-hash check."""
import argparse,hashlib,json,subprocess
from pathlib import Path
STAGE=Path(__file__).resolve().parent;REPO=STAGE.parents[2]
PATHS=['real-world/check.json','row-split/check.json','row-split/restrictive-check.json']
def hashes():return {p:hashlib.sha256((STAGE/p).read_bytes()).hexdigest() for p in PATHS}
def main():
 p=argparse.ArgumentParser(description=__doc__);m=p.add_mutually_exclusive_group(required=True);m.add_argument('--build-and-compare',action='store_true');m.add_argument('--check',action='store_true');a=p.parse_args()
 if a.check:
  d=json.loads((STAGE/'backend-parity.json').read_text());assert d['sha256']==hashes(),'stale backend parity record'
 else:
  observed={}
  for backend in ['erlang','javascript']:
   for module in ['us_backfill_check','us_backfill_restrictive_check']:
    subprocess.run(['gleam','run','--target',backend,'-m',module],cwd=REPO/'historical-model',check=True)
   observed[backend]=hashes()
  assert observed['erlang']==observed['javascript'],'backend output drift'
  d=dict(format_version=1,status='byte-identical Erlang/JavaScript output after canonical shared-account ordering',backends=['erlang','javascript'],sha256=observed['erlang'])
  (STAGE/'backend-parity.json').write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
 print('Three canonical reports match the recorded Erlang/JavaScript hashes')
if __name__=='__main__':main()
