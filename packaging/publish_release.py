"""Publish new release without allowing PowerShell to reinterpret expected gh stderr."""
from pathlib import Path
import os, subprocess, sys
repo=os.environ['GITHUB_REPOSITORY']; commit=os.environ['GITHUB_SHA']; tag='v0.1.0'
probe=subprocess.run(['gh','release','view',tag,'--repo',repo],capture_output=True,text=True)
if probe.returncode==0:
    raise SystemExit('v0.1.0 already exists. Bump the version; published assets are never overwritten automatically.')
if 'release not found' not in (probe.stdout+probe.stderr).lower():
    raise SystemExit('Unable to verify release absence: '+probe.stderr.strip())
assets=[str(p.resolve()) for p in sorted(Path('release').iterdir()) if p.is_file()]
if not assets or not any(p.endswith('-Setup.exe') for p in assets): raise SystemExit('Installer assets missing')
result=subprocess.run(['gh','release','create',tag,*assets,'--repo',repo,'--target',commit,'--title','Pharmacy Desktop v0.1.0 — Windows x64','--notes-file','docs/RELEASE_NOTES.md','--latest'])
sys.exit(result.returncode)
