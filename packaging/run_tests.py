"""Capture tests without PowerShell native stderr conversion changing exit semantics."""
import subprocess,sys
from pathlib import Path
result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
Path('build').mkdir(exist_ok=True)
Path('build/test-results.txt').write_text(result.stdout,encoding='utf-8')
print(result.stdout)
sys.exit(result.returncode)
