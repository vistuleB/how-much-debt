"""Run the existing independent ROW-SPLIT checker on isolated backfill paths."""
import importlib.util,json,sys
from pathlib import Path
STAGE=Path(__file__).resolve().parent
BASE=STAGE.parent
spec=importlib.util.spec_from_file_location('independent_row',BASE/'check-row-split.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
summary=checker.verify(json.loads((STAGE/'row-split/check.json').read_text()),json.loads((STAGE/'real-world/check.json').read_text()),STAGE/'row-split/input.json',BASE/'raw/z1-20260319-csv.zip',STAGE/'real-world/input.json')
text=json.dumps(summary,indent=2,sort_keys=True)+'\n'
if '--check' in sys.argv:
    if (STAGE/'verification.json').read_text()!=text:raise ValueError('stale verification.json')
else:(STAGE/'verification.json').write_text(text)
print(json.dumps(summary))
