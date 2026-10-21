$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
Copy-Item docs\USER_GUIDE.md release\USER_GUIDE.md
Copy-Item docs\RELEASE_NOTES.md release\RELEASE_NOTES.md
Copy-Item build\frozen-smoke.json release\frozen-smoke.json
Copy-Item build\installed-smoke.json release\installed-smoke.json
Copy-Item build\build-provenance.json release\build-provenance.json
Copy-Item LICENSE dist\PharmacyDesktop\LICENSE
Copy-Item docs dist\PharmacyDesktop\docs -Recurse -Force
Compress-Archive -Path dist\PharmacyDesktop -DestinationPath release\PharmacyDesktop-0.1.0-Windows-x64-Portable.zip -Force
git archive --format=zip --prefix=PharmacyDesktop-0.1.0/ --output=release/PharmacyDesktop-0.1.0-Source.zip HEAD
if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed' }
Compress-Archive -Path docs,templates,LICENSE,README.md -DestinationPath release\PharmacyDesktop-0.1.0-Documentation.zip -Force
& $python -c "from pathlib import Path; import hashlib; r=Path('release'); files=sorted(p for p in r.iterdir() if p.is_file() and p.name not in ('SHA256SUMS.txt','SHA256.txt')); (r/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files),encoding='utf-8')"
if ($LASTEXITCODE -ne 0) { throw 'Checksum generation failed' }
Remove-Item release\SHA256.txt -ErrorAction SilentlyContinue
