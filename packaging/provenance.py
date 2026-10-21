import json,platform,sqlite3,subprocess,sys,os
from pathlib import Path
from datetime import datetime,timezone
result={'built_at':datetime.now(timezone.utc).isoformat(),'commit':os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'runner':platform.platform(),'python':sys.version,'sqlite':sqlite3.sqlite_version,'dependencies':subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True).splitlines(),'run_url':f"https://github.com/{os.environ.get('GITHUB_REPOSITORY','')}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"}
Path('build/build-provenance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
