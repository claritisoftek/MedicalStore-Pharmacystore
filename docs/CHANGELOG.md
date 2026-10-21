# Changes and decision log

## 0.1.0 — 2026-10-21 — development source handover

### Scope confirmed
Windows 10/11 installer with dependencies; primary single counter; future LAN expansion; medicines/batches/expiry, purchases/suppliers, POS/receipts, customer balances, expenses, reports, barcode scanning, empty database, Excel import, backup/restore, A4 and thermal printing, English, PKR and generic branding. Maintenance/process/technology documentation mandatory.

### Assessment and architecture decision
Reviewed upstream commit `0f6455ed171ff21f447bb776fb093d76fdefc055`. Chose an independent Python/Tk/SQLite implementation rather than bundling the Laravel 8/MySQL/third-party theme stack. No upstream application assets are copied into this handover. Detailed reasoning and mapping: UPSTREAM_REVIEW.md.

### Implemented
- Local schema with FK/check constraints, WAL and explicit transactional writes.
- Blank initial business database and first-run Admin creation.
- Salted PBKDF2 passwords, Admin/Cashier roles, password change and audit entries.
- Catalogue/category/price/reorder/barcode data, batch quantities and expiry visibility.
- Vendor purchase headers and batches; supplier outstanding balances.
- Counter cart, barcode Enter lookup, quantities, discounts, named-customer credit and walk-in full-payment requirement.
- Earliest-expiry batch allocation with expired/insufficient-stock rejection, price/cost snapshots.
- Same-day whole-sale cancellation and duplicate-void rejection.
- Customer/supplier payments, balance statements, paid expenses and management summaries.
- Strict XLSX opening inventory template, row validation, preview, consistent multi-batch products, transactional apply and digest tracking.
- SQLite backup API snapshots; restore schema/integrity checks, pre-restore snapshot and reauthentication.
- Offline PDF layout sizes A4/58mm/80mm and Windows GDI printing implementation.
- Per-user installer recipe, pinned application/build dependencies, Windows build script, frozen-package smoke check and GitHub Actions build workflow.
- Full developer/customer/build/acceptance/process documentation.

### Corrections during implementation
- Password change form now masks both old/new passwords.
- Cashier can access own password change from the top bar.
- Frozen smoke test checks the actual nine Admin tabs and four Cashier tabs.
- Historical sale cancellation is blocked because the initial model has no dated returns/refund ledger.

### Verification and outstanding release gates
Automated tests passed on Linux; see TEST_RESULTS.md for exact count and scope. Source compilation succeeded. Windows Setup.exe, frozen Windows smoke, interactive GUI operation, upgrade/uninstall and actual printer compatibility are not verified in this environment. LAN service and broader migration/returns features are future work.


### Repository publication and Windows release automation
Published to the customer-selected `claritisoftek/MedicalStore-Pharmacystore` repository, preserving its existing GPL-3.0 licence. Added main-branch Windows builds, frozen and installed executable smoke checks, silent installer/uninstaller verification, source/portable/documentation packaging, dependency provenance, checksums and gated GitHub Release creation. Windows outcomes are recorded in release evidence rather than inferred from Linux tests. Physical printer verification remains pending on customer hardware.
