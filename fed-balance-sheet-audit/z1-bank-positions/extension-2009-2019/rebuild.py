"""Explicit isolated build; --verify alone never refreshes generated artifacts."""
import argparse,json,subprocess,sys
from pathlib import Path
STAGE=Path(__file__).resolve().parent;BASE=STAGE.parent;REPO=STAGE.parents[2]
def run(args,cwd=REPO):
 print('+ '+' '.join(map(str,args)),flush=True)
 subprocess.run(list(map(str,args)),cwd=cwd,check=True)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
 if not (a.build or a.verify):p.print_help();return
 py=sys.executable
 if a.build:
  for script in ['build-source.py','build-partitions.py']:run([py,STAGE/script])
  run([py,STAGE/'verify-backends.py','--build-and-compare'])
  run([py,STAGE/'build-broad.py']);run([py,STAGE/'publish.py'])
 if a.verify:
  for script in ['build-source.py','build-partitions.py','verify-backends.py']:run([py,STAGE/script,'--check'])
  run([py,STAGE/'check.py','--check'])
  run([py,BASE/'independent_formula_check.py',STAGE/'real-world/check.json','--diagnostics',STAGE/'real-world/check.json'])
  run([py,BASE/'check-restrictive.py','--report',STAGE/'row-split/restrictive-check.json','--source',STAGE/'row-split/check.json'])
  for script in ['build-broad.py','publish.py']:run([py,STAGE/script,'--check'])
  run([py,'-m','unittest','discover','-s',STAGE,'-p','test_*.py'])
if __name__=='__main__':main()
