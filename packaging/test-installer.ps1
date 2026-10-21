$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$installer = (Resolve-Path 'release\PharmacyDesktop-0.2.0-Windows-x64-Setup.exe').Path
$smokeRoot = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { $env:TEMP }
$installPath = Join-Path $smokeRoot 'PharmacyDesktop-Installer-Smoke'
if (Test-Path $installPath) { throw "Use a fresh installer smoke directory: $installPath" }
$process = Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', ('/DIR="' + $installPath + '"')) -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Installer failed: $($process.ExitCode)" }
$exe = Join-Path $installPath 'PharmacyDesktop.exe'
if (-not (Test-Path $exe)) { throw 'Installed executable missing' }
$report = Join-Path (Get-Location) 'build\installed-smoke.json'
$process = Start-Process -FilePath $exe -ArgumentList @('--self-test', ('"' + $report + '"')) -Wait -PassThru
if ($process.ExitCode -ne 0 -or -not (Test-Path $report)) { throw 'Installed application smoke check failed' }
if (-not ((Get-Content $report -Raw | ConvertFrom-Json).ok)) { throw 'Installed smoke report failed' }
$process = Start-Process -FilePath (Join-Path $installPath 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Uninstaller failed' }
if (Test-Path $exe) { throw 'Executable remains after uninstall' }
Write-Host 'Installer, installed application and uninstaller smoke checks passed.'
