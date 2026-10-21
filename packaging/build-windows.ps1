# Run from any folder on a Windows 10/11 x64 build machine.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows x64 required' }
python -c "import sys; assert sys.version_info[:2] == (3,12), 'Use Python 3.12 x64'"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 required' }
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 x64 on the build machine' }
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
New-Item -ItemType Directory -Force build | Out-Null
& $python packaging/run_tests.py
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $python packaging/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'Notice collection failed' }
& $python -m PyInstaller --noconfirm --clean --windowed --onedir --name PharmacyDesktop --collect-all reportlab --collect-all openpyxl --add-data 'build/THIRD_PARTY_NOTICES;THIRD_PARTY_NOTICES' run.py
if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
$report = Join-Path (Get-Location) 'build\frozen-smoke.json'
Remove-Item $report -ErrorAction SilentlyContinue
$process = Start-Process -FilePath 'dist\PharmacyDesktop\PharmacyDesktop.exe' -ArgumentList @('--self-test', ('"' + $report + '"')) -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Frozen executable smoke test failed' }
if (-not ((Get-Content $report -Raw | ConvertFrom-Json).ok)) { throw 'Frozen smoke report failed' }
$compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (-not (Test-Path $compiler)) { throw 'Install Inno Setup 6 on build machine, then rerun' }
& $compiler packaging/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
& $python packaging/provenance.py
if ($LASTEXITCODE -ne 0) { throw 'Build provenance collection failed' }
Write-Host 'Installer created in release. Complete docs/ACCEPTANCE_CHECKLIST.md before customer delivery.'
