# Customer operation guide

This guide describes the application after a Windows installer has been built and accepted. The source handover does not itself contain Setup.exe.

## Installation and first run
1. Install the correct A4 and thermal printer drivers in Windows; print a Windows test page on each.
2. Run the supplied tested `PharmacyDesktop-0.1.0-Windows-x64-Setup.exe`. Install under the same Windows account the counter staff will use. The app does not require administrator privileges for a per-user install.
3. Open Pharmacy Desktop from the desktop shortcut.
4. On the first run create a unique Admin username and password of at least 10 characters. Record these securely. No preconfigured password exists.
5. Open Administration → Business / printing settings and set business name, address, phone, receipt footer, roll width and both printer names. Interface language is English and amounts are PKR.
6. Open Windows Printing Preferences for each printer. Set A4 on the report printer and the correct 58/80 mm roll/form on the thermal printer. Run receipt and A4 test prints.
7. Create a Cashier account under Administration → New user. Staff can change their own passwords from the top bar. Keep Admin credentials with the business owner.

## Initial medicine data using Excel
1. Stock → Excel template saves an empty `.xlsx` file. Open in Excel or another compatible spreadsheet editor.
2. Keep the exact header row, order and worksheet as supplied:
   `sku, name, barcode, category, selling_price, reorder_level, batch, expiry, opening_quantity, unit_cost`.
3. Format SKU, barcode and batch columns as Text **before entering data**, preserving leading zeros.
4. Enter one row per batch. Selling price and unit cost are PKR per same whole sale unit. For example, if selling strips, enter quantities/prices/costs per strip throughout.
5. Use `YYYY-MM-DD` for expiry. Where the package gives month/year only, confirm the last valid day from the supplier/manufacturer before entering it; the app needs a precise date.
6. Enter a positive whole opening quantity, nonnegative reorder level, unit cost and selling price, maximum two decimal places. No formulas, macros, negative quantities or expired opening stock.
7. Multiple rows for the same SKU must have identical medicine name/barcode/category/price/reorder and distinct batch/expiry combinations.
8. Save as `.xlsx`, then Stock → Import opening stock. Review the preview. No changes happen before Confirm import.
9. If a row is invalid, correct the workbook and retry. Applying an invalid/colliding workbook does not partially update inventory. Do not reimport renamed/reformatted copies to try to add more stock: existing SKUs are rejected. Later inventory comes through Purchases.
10. Add medicines with no opening stock manually through Stock → Add medicine. Add suppliers and customers from their respective tabs. Historical transactions and opening party balances are not imported by this version.

## Receiving a vendor bill
1. Create the supplier and medicine catalogue entries first.
2. Purchases → Add batch to vendor bill. Choose a medicine, batch, expiry, quantity and unit cost. Repeat for every line.
3. Remove a mistaken staged batch before saving.
4. Save vendor bill. Select supplier, enter the vendor invoice/reference and amount paid now.
5. Check the total before saving; purchases cannot be edited in this release.
6. Print the A4 purchase record or export PDF. Outstanding supplier amount is tracked automatically.

## Counter sale and receipts
1. Use a barcode scanner configured as a USB keyboard with Enter suffix, or type a SKU/barcode and press Enter. Alternatively search by name, select a row, and Add selected.
2. Repeated scans increase quantity. Select a cart line to change quantity/remove it. Clear cart abandons the unsaved cart.
3. Checkout. Choose a named customer for credit; leave blank for walk-in. Enter any discount and the amount applied to the invoice.
4. For a cash sale apply exactly the invoice net amount; calculate cash change at the counter before confirming. The program records payment applied, not tender and change.
5. Complete the sale; stock is allocated from the earliest expiring available batches. Expired or insufficient stock blocks the whole sale.
6. In the receipt preview choose the thermal printer and 58/80 mm size, then Print. Export PDF is available. The sale is already saved even if printing fails; use Sales → Reprint receipt to avoid recording it twice.
7. Check Sales for recent invoices. Cashier list shows only that cashier's last 2,000 invoices; Admin sees the last 2,000 overall. This limit is a screen limit, not data deletion or report truncation.
8. Admin may void an eligible same-day entire sale and restore its stock. The operator handles the cash refund. Earlier-date and partially returned sales need a future returns module; do not enter negative sales.

## Balances, expenses and reporting
- Customers/Suppliers show outstanding balances. Admin → Record balance payment records a customer receipt or a supplier payment. Enter only actual money received/paid; overpayment is rejected.
- Statement shows invoice totals, payments at invoice, subsequent payments and outstanding amount. Print on A4.
- Expenses → Add expense records a category, note and paid PKR amount.
- Reports accepts inclusive from/to dates. Sales/expenses/cash figures cover that period; inventory and party balances are current at generation time. The report explicitly labels that distinction.
- Stock highlights LOW/OUT when sellable units are at/below reorder. Batch details mark expired and near-expiry (within 90 days). Expired stock remains physically recorded until a future adjustment/disposal workflow is added.

## Backup and restore
1. At closing time, Admin → Create backup. Choose a **new** filename on a separate drive, e.g. `pharmacy-2026-10-21.sqlite3`.
2. Keep several dated backups. A backup on the same disk alone does not protect against disk failure. Close exported files appropriately and protect them like business records.
3. Periodically test restore on a separate test Windows profile/PC, not the live counter. Confirm products, recent invoices and balances.
4. To recover: Admin → Restore backup. This replaces all records and accounts with the selected snapshot. The app checks validity and first saves a `before-restore-...sqlite3` safety copy in the data folder.
5. You are signed out. Log in with the Admin username/password stored in that backup.
6. Transactions recorded after the backup are absent after recovery and need controlled re-entry from receipts.

## Upgrades, removal and support
- Back up before upgrades. Close the program, install the approved upgrade under the same Windows user, and verify records.
- Uninstall removes installed software but deliberately keeps the data folder. Reinstall under that same Windows profile reuses its data.
- Do not share the live SQLite database through a network drive. This release is one workstation; planned LAN support needs a server implementation.
- If printing fails, check Windows test page, printer name, driver form size, spooler and paper roll. Do not re-record the sale.
- For a support error provide the exact message and relevant invoice ID; the local data folder contains `error.log` for unexpected callback errors. Avoid sending full customer databases unless necessary and authorized.
- Forgotten Admin passwords have no built-in reset bypass. Use an existing second Admin to retain access or arrange a controlled developer recovery; keep a known-good backup and credentials.
