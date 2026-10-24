# Pharmacy Web 1.1 — production improvements, 24 October 2026

This release implements the twelve agreed counter, stock, customer, account, reporting and accessibility improvements. Windows Desktop remains a separate application and is not changed by this web release.

## Responsibilities and access

| Role | Access |
| --- | --- |
| Operator / Cashier | Counter sales, own sales/receipts, customer creation and correction. No supplier, cost, report, team or backup access. |
| Manager | Counter and all sales, stock, imports, batch costs, purchases, customers/suppliers, payments, expenses and reports. No team, profile, audit or backup access. |
| IT | Company profile/logo, team management, audit history and database backup downloads. Cannot transact, view operational stock/sales/reports or restore backups. Backups contain all business data and hashes, so IT is a privileged trusted role. Cannot create, modify or grant Admin access. |
| Admin | All functions including restore. Only Admin may grant/manage Admin access. Last active Admin cannot be demoted or deactivated. |

Roles are enforced on server routes and reloaded from the database on every request. Updating an account revokes all its sessions. New accounts require a chosen password; existing passwords are never displayed or changed through Manage account. Account and party changes are audited. Cashier is the retained database role name for Operator. Existing accounts keep their roles.

## Data migration and recovery

`web/db.js` migrates schema version 1 to 2 under a MySQL advisory lock. Columns are additive: products receive brand, prescription status and variant; parties receive active/archive status; the account role enum receives Manager and IT. Existing products get blank brand/variant and NULL prescription status, shown as not recorded. Existing customers/suppliers remain active. No stock, sale, payment or history is removed or fabricated.

A private JSON safety snapshot is stored in `web_backups` before upgrading a populated version 1 database. It is downloadable by Admin/IT from Administration. Migration is repeatable, including after an interrupted additive DDL step. InnoDB DDL commits independently, so do not deploy old application code as a database downgrade. The old schema version is updated only after all additions succeed. Version 2 backups include the new fields. Version 1 web backups remain restorable by Admin: missing fields become blank/unknown and parties active; normal validation, safety snapshot, password and session invalidation still apply. Never restore a backup on production solely to test it.

## Operator changes

1. Walk-in checkout explains missing cash and offers Exact cash; paid cash sales never need a named customer. Named customers may carry unpaid credit balances. It does not infer cash payment from an empty/zero field.
2. Search accepts name/SKU/barcode/brand/variant. Up/Down selects a result; Tab reaches its quantity; Enter adds the chosen number. Enter on an exact SKU/barcode adds one unit; repeated scans increase quantity. Focus returns to search after adding. F2 focuses search, F5 attempts valid checkout. Existing cart quantity inputs support keyboard editing.
3. Names wrap in tables/cart and result widths reserve room for stock, price and Add. Phone stock rows become labelled cards.
4. Manual create/edit and new imports require brand/manufacturer and explicit prescription Yes/No. Variant is optional (strength, dosage form or pack). Existing metadata is never guessed. Stock's Missing product details filter identifies legacy records for review. Prescription status is catalogue information; this change does not implement prescription document storage or a clinical authorization workflow.
5. Customer/supplier Edit changes contact details only. Archive removes a record from new-transaction selections; balances, past documents and payments remain available. Restore makes it selectable again. There is no irreversible deletion.
6–7. Roles and team lifecycle follow the table above, including confirmation, auditing and session revocation.
8. Stock search, category, low-stock, expired and expiring-within-90-days filters, 25-item pages and per-product Batches details. Expired stock remains blocked from sale.
9. Discount above subtotal, negative amounts and amounts with more than two decimals prevent checkout. Impossible negative totals/change are not rendered. Uncertain network outcomes keep the same frozen checkout payload and retry key; the operator sees a safe plain-language retry message. Confirmed validation errors allow correction.
10. Report results carry their generated date range and PKT label. Editing dates immediately clears results/print links; reversed dates show an error. Out-of-order successful requests cannot overwrite newer results.
11. All native dialogs use their visible heading as the accessible name. Native Escape and focus restoration are retained.
12. History shows readable Pakistan time with original values retained in expandable details. Audit rows show usernames and meaningful references; business users can navigate reference links when permitted.

## Excel template

Download the new template from Stock before new imports. Required header order:

`sku, name, barcode, category, price, reorder, batch, expiry, quantity, cost, brand, prescription, variant`

Prescription accepts Yes/No (also true/false or 1/0). Brand must be nonblank. Variant may be blank. Existing SKU metadata must match exactly, including the new fields. Old ten-column workbooks now show an explicit required-columns validation error; existing imported records are preserved. Update existing product details first before importing additional batches against them. Duplicate-file and atomic rollback protections remain in force.

## Implementation and validation

Technology remains Express, vanilla browser JS/CSS, mysql2/InnoDB, ExcelJS with namespace normalization, and Playwright. New helpers are in `web/public/app.js`; shared input validation and customer/account writes are in `web/service.js`; permissions/routes in `web-server.js`; migrations in `web/db.js`. No new runtime dependencies.

Local checks cover database migration/idempotency, metadata, archive/restore, vendor payments, independent Cashier/Manager/IT sessions, last Admin protection, session invalidation, transactions, FEFO, duplicate prevention, restore and startup. Browser checks cover search quantity keyboard flow, cash/discount validation, stale reports, accessible dialogs, stock search/batches, required form fields and desktop/mobile layout. CI runs against MySQL 8.4 with Node 22 and Chromium before production promotion. Physical printer/scanner hardware and a complete screen-reader assessment remain customer acceptance checks.

## Verified release evidence

Runtime commit: `8b1a6aef0451553921654132933cf53e77de4448`.

GitHub Actions run [40098623145](https://github.com/claritisoftek/MedicalStore-Pharmacystore/actions/runs/40098623145), job `120885998042`: all steps succeeded on Node 22 / MySQL 8.4, including 21 Node/database/startup checks, clean production dependency audit, and the expanded Chromium workflow. The workflow exercised a long medicine name, 2-unit keyboard entry, exact cash, excessive discount rejection, invalid report dates, labelled prescription selector, named dialogs and focus return, stock batch details/search, role options, interrupted successful checkout retry, receipt access, and 390px phone stock layout. No page script errors occurred. The artifact `12561952392` retains four reviewed screenshots plus the test log. SHA256: `69d7bee17d4c7f84e0afb2fade7527364e912cf0eca056f67216148b15c6169b`.

The initial browser run caught an ambiguous prescription-selector accessible name. Explicit labels were added and the full workflow passed on the runtime commit above. Desktop and phone-stock screenshots were visually reviewed before promotion. These fixtures use a disposable test database; they do not represent customer transactions. Final promotion includes documentation-only additions over the verified runtime commit.
