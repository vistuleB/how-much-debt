"""Apply the current isolated broad-debt experiment, not a new source completion."""
import hashlib,json,sys
from pathlib import Path
STAGE=Path(__file__).resolve().parent
sys.path.insert(0,str(STAGE.parents[2]/'broad-debt-model'))
import corrected_build,corrected_check,inventory

def main():
 source=STAGE/'row-split/check.json';d=corrected_build.build(source)
 out=STAGE/'broad-debt';out.mkdir(exist_ok=True)
 for name,text in [('results.json',json.dumps(d,separators=(',',':'),sort_keys=True)+'\n'),('results.md',corrected_build.render(d))]:
  p=out/name
  if '--check' in sys.argv:
   if p.read_text()!=text:raise ValueError('stale '+str(p))
  else:p.write_text(text)
 summary=corrected_check.check(json.loads((out/'results.json').read_text()),source)
 text=json.dumps(summary,indent=2,sort_keys=True)+'\n'
 if '--check' in sys.argv:assert (out/'verification.json').read_text()==text
 else:(out/'verification.json').write_text(text)
 print(json.dumps(summary))
if __name__=='__main__':main()
