# Technical guide

## Technology and rationale
| Component | Version/choice | Purpose |
|---|---|---|
| Python | Build with 3.12 x64 | Desktop runtime, standard SQLite and Tk bindings |
| Tk/ttk | Python distribution's Tcl/Tk | Native desktop forms/tables without browser server |
| SQLite | Bundled Python sqlite3 runtime version | Local transactional database; WAL, FK enforcement, synchronous FULL |
| openpyxl | 3.1.5 | Read/write .xlsx without Microsoft Excel |
| ReportLab | 4.4.9 | Offline PDF reports and receipts |
| pywin32 | 311, Windows only | Enumerate printers and GDI printing |
| PyInstaller | 6.22.3 | Bundle Python, Tcl/Tk, libraries into standalone app directory |
| Inno Setup | 6 on builder | Per-user Windows installation and uninstall |
| unittest | Python standard library | Transaction, financial and import regression tests |

The listed application/library versions are pinned in requirements files. The build resolves transitive dependencies from the index; a fully hash-locked wheelhouse is not included. Archive the successful builder environment and build provenance for production reproducibility. Inno Setup and Python patch versions are not locked by this source package.

## Module map
- `run.py`: normal launch or packaged `--self-test REPORT_PATH`.
- `pharmacy/core.py`: schema, local paths, validation, authentication, authorization, purchases, batch allocation, sales, voids, balances, expenses, settings, snapshots/restore.
- `pharmacy/app.py`: Tk UI, dialogs, counter cart, purchase cart, lists, previews, data entry, printer selection.
- `pharmacy/excel.py`: XLSX template, strict validation/preview, atomic opening-stock apply.
- `pharmacy/reports.py`: receipt, purchase bill and date-range report text generation.
- `pharmacy/printing.py`: ReportLab PDF and Windows printer DC output.
- `pharmacy/selftest.py`: frozen-package startup/role/dependency smoke check in a disposable directory.
- `tests/test_workflows.py`: domain regression tests.
- `packaging/`: build script, installer configuration and notice collection.

## Storage and ownership
Application binaries: `%LOCALAPPDATA%\Programs\PharmacyDesktop`.
Business data per Windows user: `%LOCALAPPDATA%\PharmacyDesktop\pharmacy.sqlite3`.
Additional files: SQLite WAL/SHM as needed, workstation lock, error log, pre-restore snapshots. Manually selected backups/PDFs/workbooks go to the chosen destination.

Do not put the live database on OneDrive/network shares/removable media. A future LAN host must own the database and expose business operations. Different Windows accounts currently get independent databases. Uninstall preserves business data; upgrades must retain the same application ID and path.

## Database, schema version 1
| Table | Main fields and relationship | Meaning |
|---|---|---|
| meta | version | Migration version (exactly 1 for this release) |
| users | id, username UNIQUE, password, role, active | Salted PBKDF2 credentials, Admin/Cashier |
| settings | key PK, value | Business text, thermal roll and preferred printers |
| products | id, sku UNIQUE, name, barcode UNIQUE nullable, category, price, reorder, active | Medicine and whole sale unit |
| parties | id, kind, name, phone, address | Customer or supplier |
| purchases | id, created, supplier_id→parties, reference, total, paid | Vendor invoice header |
| batches | id, product_id→products, purchase_id→purchases nullable, batch, expiry, quantity, cost, original_quantity | Current batch stock; null purchase means opening import |
| sales | id, created, user_id→users, customer_id→parties nullable, subtotal, discount, total, paid, status | Posted or Void invoice |
| sale_lines | id, sale_id→sales, batch_id→batches, quantity, price, cost | Immutable allocation and price/cost snapshots |
| payments | id, created, party_id→parties, amount, note | Customer receipt or supplier payment; direction inferred from party kind |
| expenses | id, created, category, note, amount | Immediate paid business expense |
| audit | id, created, user_id, action, detail | Append-oriented application audit; not tamper proof |
| imports | id, digest UNIQUE, created, rows | Opening workbook SHA256 and batch count |

No physical deletion operations are exposed. Indices cover batches by product/expiry and sales by created time. Amounts are integer paisa; UI converts decimal strings once, rejects negative/nonfinite/overprecision values, and formats amounts for display. Quantities are positive integers on inputs; batch balance cannot go below zero. Dates are ISO YYYY-MM-DD and local workstation timestamps. Maintain the Windows time/timezone accurately.

## Transaction processes
1. Purchase validates supplier, bill reference and all batches. `BEGIN IMMEDIATE` inserts header and all batch rows, then audit. Any failure rolls back all records.
2. Sale merges duplicate scans, holds SQLite write lock, selects nonexpired stock ordered by expiry then batch ID, validates full availability, calculates totals/discount/payment, inserts header/allocations and deducts quantities in one transaction.
3. Each allocation stores cost and selling price at sale time so later catalogue price changes cannot alter historical profit.
4. Named customer sales permit partial payment. Walk-in sales require payment applied equal to net invoice total. Cash tender/change is handled by the operator; only amount applied is stored.
5. Party balances = posted invoice amounts minus invoice-paid values minus subsequent payments. Payment cannot exceed remaining balance. Supplier balance direction is payable; customer direction is receivable.
6. Same-day sale cancellation restores original batches and marks invoice Void; already-void and previous-day invoices are rejected. Cancellation of a credit sale is rejected when later payments make its unpaid amount greater than outstanding customer balance. Physical cash refund is manual. No historical return ledger exists.
7. Expenses are paid entries; management operating result = net posted sales − allocated costs − expenses. This is not a statutory/tax financial statement.
8. Import reads workbook into validated immutable preview data; creates only new products/batches. A transaction rolls back all rows if any existing SKU/barcode collides. Exact repeated files are rejected by digest.
9. Backup uses SQLite's online backup API, not raw file copying while WAL is active.
10. Restore opens source read-only, checks integrity/version/foreign keys/column layouts/active admin, makes a safety snapshot, restores through backup API and forces fresh login. Restore is exclusive in the desktop process.

## Authentication and roles
Passwords use a random 16-byte salt with PBKDF2-HMAC-SHA256, 600,000 iterations, constant-time digest comparison and 10-character minimum. First run creates the Admin; no default account. Cashiers may sell, add customers and view stock/their sales. Admins manage purchasing/catalogue/expenses/reports/users/backup/settings. Store write methods enforce permissions regardless of UI tab visibility. Five failed attempts temporarily disable the sign-in button for 30 seconds; this is a UI throttle, not a persistent lockout.

The database itself is not encrypted. Windows file permissions protect local records; application logins are not a defense against a Windows user who can copy or edit the database. Backup files contain all records and password hashes. Printer spoolers and exported PDFs may contain customer information.

## Printing
Windows integration enumerates installed printers, creates a printer DC, uses a fixed-width font, wraps to printable width and paginates to the driver's current printable height. Application paper choice affects font/PDF sizing; native hardware paper/form selection remains the driver's configured preference. No silent default PDF-viewer dependency exists. PDF generation is wholly local; ordinary report text uses ReportLab's built-in font (English only).
