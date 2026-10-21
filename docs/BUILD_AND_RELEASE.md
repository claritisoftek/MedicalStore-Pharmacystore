# Build and release process

## Current handover status
The initial source was verified on Linux/Python 3.12. The repository now builds on Windows and publishes only after automated domain, executable and installed-package smoke checks pass. The release assets contain Windows build evidence. Physical printer tests and interactive customer Windows 10/11 acceptance remain separate checks.

## Builder requirements
- Windows 10/11 x64 or a Windows x64 CI runner.
- Python 3.12 x64 from a distribution with Tk/SQLite, and the Python Launcher `py`.
- Inno Setup 6 with `ISCC.exe` at the standard Program Files (x86) path.
- Internet on the builder to install pinned Python dependencies and toolchains. The resulting customer application needs none of those downloads at runtime.
- A4/thermal devices and drivers for final physical acceptance. A CI runner may have no installed printers; enumeration must still succeed.

## Local build
1. Extract the source to a path you control. Open PowerShell there.
2. Run `powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1`.
3. The script switches to the project root, creates `.venv`, installs requirements, runs `unittest`, collects notices, calls PyInstaller, runs the frozen package self-test and calls Inno Setup.
4. Any failed command stops the build. Investigate and fix it; do not bypass frozen smoke checks.
5. Expected outputs after success:
   - `dist/PharmacyDesktop/PharmacyDesktop.exe` and its complete `_internal` dependencies. This executable alone is not a portable distribution; keep its whole directory.
   - `build/frozen-smoke.json` with `ok: true` and desktop/dependency checks.
   - `release/PharmacyDesktop-0.2.0-Windows-x64-Setup.exe`.
   - `release/SHA256SUMS.txt` after package-release.ps1.
6. Install on a clean Windows test computer with no Python, PHP, MySQL, Excel or internet. Follow ACCEPTANCE_CHECKLIST.md.
7. Test both x64 Windows 10 and Windows 11, under a normal (non-admin) Windows user. Windows ARM and 32-bit x86 are not targeted by this build.

## GitHub Actions release process
1. This project is published at https://github.com/claritisoftek/MedicalStore-Pharmacystore under its existing GPL-3.0 licence.
2. A push to main or manual workflow dispatch runs `.github/workflows/build-windows.yml` on Windows Server 2022.
3. The workflow runs the builder, silently installs the resulting installer, runs the installed executable self-test and uninstalls it.
4. It assembles portable, source and documentation archives, records dependency/runtime provenance and computes SHA256SUMS.txt.
5. Push builds and manual runs with `publish_release` unchecked only validate and retain packages as workflow artifacts. To publish a new version, first change all version/tag references to an unused release version, then use Actions → Build and release Windows installer → Run workflow on main and check `publish_release`. Only after all checks pass does publication create the release targeting the exact build commit. Existing releases are never overwritten automatically.
6. Physical printer and clean Windows 10/11 acceptance remain required. CI does not send printer jobs.
7. Build evidence is also retained as an Actions artifact even if later publication fails.

## Dependency bundling
PyInstaller `--onedir --windowed` includes the Python interpreter, Tcl/Tk and imported extensions. `--collect-all reportlab` and `--collect-all openpyxl` gather library data and modules. pywin32 printer dependencies are referenced in normal imports for analysis. Notices are collected from installed distributions into `THIRD_PARTY_NOTICES`; Python's license is copied where available. Inspect the generated notices before commercial distribution and complete missing Tcl/Tk/transitive notices from the exact builder distribution where necessary.

No customer environment variables, PHP service, MySQL service or web browser are required by the packaged source design. Windows itself and correctly installed printer drivers remain prerequisites.

## Signing and release integrity
No code-signing certificate is supplied. If you have one, sign the executable before installer compilation and sign the installer afterward using your normal Windows signing process. Keep credentials outside source control. Recompute SHA256 after signing.

Record release tag/commit, Python patch version, `python -m pip freeze`, tool/compiler versions, build logs, smoke output, acceptance sign-off and final installer hash. Retain the exact installer given to each customer.

## Upgrade rules
Keep AppId stable. Data stays outside the install directory and must not be overwritten by installer files. Before future schema changes, implement tested, versioned migrations with a pre-migration backup. Never ship a new version with ad-hoc schema changes or reset a customer's live database.

## v0.2.0 design release gate
The ui/modern-dispensary branch runs Windows builds and screenshot checks without publishing a release. Review native screenshots against docs/design/selected-reference.jpg, update design-qa.md, then fast-forward main to the verified change. Main builds the packages again; manual publication requires `publish_release` checked and `final result: passed`. Assets, logs, screenshots, interaction results and exact commit provenance are retained.

## Repeating tests after a release
Use Run workflow on the current main branch with `publish_release` unchecked. This repeats domain, frozen-app, native UI, installer and uninstall checks without attempting to recreate the existing release. A rerun of an older failed run still uses that run's original commit; select a fresh main run to test current fixes. This separation was added after v0.2.0 so routine verification cannot fail merely because its release tag already exists.
