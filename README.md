# Pharmacy Desktop — 0.2.0

Independent offline pharmacy desktop implementation, prepared for Windows 10/11 x64.
[Build status](https://github.com/claritisoftek/MedicalStore-Pharmacystore/actions/workflows/build-windows.yml) | [Download installer and full release](https://github.com/claritisoftek/MedicalStore-Pharmacystore/releases)

Release publication is gated on automated Windows domain tests, frozen application and installed application checks, installation and uninstallation on Windows Server 2022. Evidence is attached to the release. Physical printer/scanner checks and interactive Windows 10/11 acceptance remain necessary on the delivery machine.

## Modern desktop release

The customer-selected Warm Dispensary design uses warm ivory and forest green, horizontal navigation, a persistent cart, live cash/change calculation and a medicine application/installer icon. **Admin → Company profile** can replace/remove the company logo and edit name, tagline, address, phone, email and receipt footer without reinstalling. PNG/JPEG logos are stored in the database, backed up/restored, and included on PDFs/native printouts.

## Included behavior
- Empty business database; create the first Admin at initial launch, no default password.
- Admin and Cashier roles; password changes; account creation; audit trail.
- Medicine catalogue, categories, barcode lookup/scanning, batch inventory, expiry and low-stock indications.
- Multi-item vendor purchases and purchase bills; multi-item counter sales, discounts, cash/credit allocation, customer receipts.
- Customer receivables, supplier payables, subsequent balance payments, statements, expenses.
- Date-range financial reports with cost of goods, operating result and recorded cash movement.
- Validated .xlsx opening inventory import with preview, atomic apply and duplicate-file rejection.
- Manual SQLite snapshot backups and validated full restore with automatic pre-restore backup.
- A4/58mm/80mm PDF export; Windows native printing to installed printer drivers.
- Generic English UI and PKR; pharmacy name, logo, tagline, address, phone, email, footer and printer choices are editable.

## Current limits that affect delivery
- Single local workstation only. LAN mode is a documented future extension, not an enabled feature.
- Windows packaging and dependency loading are tested by release automation; physical printing and customer Windows 10/11 acceptance require device-specific checks.
- Only whole sale units; price/cost must refer to the same unit (e.g. strip or tablet). No pack conversion.
- Excel import covers new opening inventory and batches, not transaction history, party balances, suppliers or customers. Enter customers/suppliers using the application. Preserve a copy of the original workbook.
- Same-day whole-sale cancellation only; no partial/historical returns, credit notes, purchase amendments, stock adjustments or refunds ledger.
- No GST/FBR integration, insurance billing, prescription processing or controlled-medicine register.
- Native print uses the printer driver's configured page size. Set thermal roll size and A4 in Windows Printing Preferences; PDF size selection alone does not change printer hardware defaults.
- No digital signing certificate included; Windows SmartScreen may display an unsigned-app warning.

## Run source (developer machine)
Python 3.12 with Tk support:
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```
On Linux use `.venv/bin/python`; native Windows printing is unavailable there.

## Build the customer installer on Windows
Install Python 3.12 x64 and Inno Setup 6 **on the developer/build computer only**, then open PowerShell in this directory:
```
powershell -ExecutionPolicy Bypass -File packaging\build-windows.ps1
```
The script installs pinned dependencies, runs tests, creates a bundled executable directory, runs its smoke test, and builds `release/PharmacyDesktop-0.2.0-Windows-x64-Setup.exe`.
The customer does not need Python, PHP, MySQL, Excel, a browser or an internet connection for the compiled application. Windows printer drivers are required for physical printing.

Pushes to main and manual workflow dispatch build and publish the Windows release. Release assets include the installer, portable app, matching source, documentation, checksums and evidence. The workflow does not overwrite existing v0.2.0 assets; bump version references before subsequent releases.

## Documentation index
- [Customer operation and backup guide](docs/USER_GUIDE.md)
- [Architecture, dependencies and database](docs/TECHNICAL_GUIDE.md)
- [Build and release process](docs/BUILD_AND_RELEASE.md)
- [Changes and implementation decisions](docs/CHANGELOG.md)
- [Repository assessment and provenance](docs/UPSTREAM_REVIEW.md)
- [Customer acceptance checks](docs/ACCEPTANCE_CHECKLIST.md)
- [Verification evidence](docs/TEST_RESULTS.md)
- [Future maintenance and LAN plan](docs/MAINTENANCE.md)

All customer records are under `%LOCALAPPDATA%\PharmacyDesktop\` for the Windows profile running the program, separate from installed files. Uninstalling preserves that directory.

## Licence

The repository's existing [GNU GPL v3](LICENSE) is preserved. Matching application source is published with the release. Third-party libraries retain their own licences.

## Upgrade from v0.1.0

Create a backup, close the app and run the v0.2.0 installer under the same Windows account. AppId, install path, data folder and schema version remain unchanged; existing accounts and records are retained. No demonstration business data are installed. See [design QA](design-qa.md) and [branding/upgrade guide](docs/BRANDING_AND_UPGRADE.md).
