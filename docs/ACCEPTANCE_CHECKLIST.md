# Release acceptance checklist

Release: 0.2.0 | Tester: __________ | Windows version: __________ | Build hash: __________

The source handover has NOT passed the Windows/device checks below. Complete on Windows 10 and Windows 11 x64 before customer delivery. Use disposable data.

## Build and clean installation
- [ ] Build script completes; all tests pass; frozen-smoke.json says ok true.
- [ ] Installer launches under a normal Windows user and creates shortcuts.
- [ ] Start application with internet disconnected on a PC without Python/PHP/MySQL/Excel.
- [ ] Initial business data are empty; create Admin; confirm password minimum/mismatch checks.
- [ ] No default credentials or demonstration medicines are present.
- [ ] Closing and relaunching retains credentials/data; a second app instance is rejected.
- [ ] Uninstall/reinstall preserves data; upgrade with unchanged AppId preserves it.

## Company identity
- [ ] Admin can replace/remove logo and save company name/tagline/contact details.
- [ ] Cancel does not save a draft; saving a profile retains the current cart.
- [ ] Logo is present in PDFs/printouts and survives backup/restore.
- [ ] Capsule app, executable, installer and desktop shortcut icons display correctly.

## Catalogue, import, purchase and stock
- [ ] Create a medicine and preserve barcode leading zeros.
- [ ] Generate template; import at least two medicines and two batches of one SKU.
- [ ] Preview before Confirm import makes no database changes.
- [ ] Invalid date/quantity/formula/header/duplicate barcode errors leave no partial data.
- [ ] Existing SKU and duplicate exact workbook import are rejected.
- [ ] Receive multi-item supplier purchase, partially pay and verify supplier balance.
- [ ] Expired receiving rejected; expired batch cannot be sold; near expiry and low stock visible.
- [ ] Quantities/prices/costs all refer to the same agreed sale unit.

## Counter and financial controls
- [ ] Real scanner in keyboard+Enter mode adds the correct medicine repeatedly.
- [ ] Search/select, quantity change, remove and clear cart work.
- [ ] Sale covering two batches allocates earliest expiry first.
- [ ] Insufficient stock rejects entire invoice without changing quantities.
- [ ] Walk-in full payment and named-customer credit behave correctly.
- [ ] Discount, subtotal, paid, due and cash change handled correctly by operator.
- [ ] Customer receipts and supplier payments reduce the correct outstanding balances.
- [ ] Overpayments are rejected; expense updates financial report.
- [ ] Reconcile sales, COGS, profit and recorded cash movement to a manual test case.
- [ ] Same-day eligible void restores quantities exactly once; old-date void rejected.
- [ ] Cashier cannot access Admin purchasing/users/reports/backups through UI; own password change works.

## Actual printers (record make/model/driver)
Thermal 58 mm: __________ | Thermal 80 mm: __________ | A4: __________
- [ ] Driver preferences select actual roll width/A4; Windows test pages succeed.
- [ ] Print short and long customer receipts, long medicine names and multiple batches on 58 mm.
- [ ] Repeat on 80 mm; text is readable and not clipped.
- [ ] A4 vendor bill and multi-page management report paginate without losing lines.
- [ ] Selecting printer routes to correct hardware; printer settings persist.
- [ ] Printer offline/paper-out failure does not re-record the sale; reprint works.
- [ ] PDF exports of A4/58/80 open with correct dimensions and legible text.

## Recovery and customer handover
- [ ] Backup to separate drive and restore into a disposable profile/PC.
- [ ] Restored quantities/invoices/balances match snapshot; restored credentials work.
- [ ] Pre-restore safety snapshot exists; invalid backup does not overwrite current records.
- [ ] Business name/contact/footer and both printer choices are set for customer.
- [ ] Customer receives tested installer, hash, user guide, backup instructions and own Admin credentials.
- [ ] Explain one-workstation scope and current unsupported returns/adjustment workflows.
- [ ] Archive matching source, build provenance, notices, test evidence and acceptance sign-off.

Approved for delivery by: __________ Date: __________
