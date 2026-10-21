# Pharmacy Desktop v0.1.0 — Windows x64

Offline, English-language pharmacy counter software using PKR and a local database.

## Downloads
- **Windows-x64-Setup.exe**: customer installer; includes Python/Tk, SQLite and application dependencies. Customer does not need Python, PHP, MySQL, Excel or internet access for normal use.
- **Windows-x64-Portable.zip**: extract the whole folder and launch PharmacyDesktop.exe; do not move the exe out of its dependency folder. Data still lives under the current Windows user's LOCALAPPDATA.
- **Source.zip**: matching source code, tests and Windows packaging scripts.
- **Documentation.zip**: customer guide, database/technology guide, change log, maintenance/LAN plan, build/release process, Excel opening-stock template and acceptance checklist.
- **SHA256SUMS.txt**: hashes for release files.
- **frozen-smoke.json / installed-smoke.json / build-provenance.json**: automated Windows build evidence.

## Features
Medicine catalogue/categories, barcode lookup and scanning, batch/expiry/low-stock visibility, supplier purchases, multi-item counter sales, discounts, customer credit, supplier/customer balances and payments, expenses, reports, Excel opening inventory import, backup/restore, PDF export and Windows printer integration.

## First run
Install on Windows 10/11 x64 under the account used at the payment counter. Create the Admin username/password at first launch; no default credentials and no demonstration business records. Set business text and thermal/A4 printer names under Administration. Install the correct printer drivers and choose actual A4/58/80 mm paper forms in Windows Printing Preferences.

## Verification and limits
Release publication is gated on automated domain tests on Windows, frozen executable smoke checks, silent installation, installed application smoke checks and uninstallation on the Windows 2022 CI runner. Those checks exercise Admin/Cashier screen initialization, a sample purchase/sale, PDF generation, Excel and Windows printer module loading using disposable data. They do not send print jobs.

Physical thermal/A4 printers, barcode scanner hardware, interactive workflows on Windows 10/11, upgrade/data preservation and customer acceptance still need checking on the delivery machine. The installer is unsigned; Windows may show a publisher/SmartScreen warning.

Single workstation release: LAN server mode is future work. Whole sale units only. Excel imports new opening inventory/batches, not historical transactions or opening party balances. Same-day whole-sale cancellation only; partial/historical returns, purchase correction and stock disposal/adjustment are not implemented. No tax/FBR integration. See README and documentation before live operation.

## Licence
The repository's existing GPL-3.0 licence is retained. Corresponding application source is included with this release. Third-party dependencies retain their respective licences/notices in the application bundle.
