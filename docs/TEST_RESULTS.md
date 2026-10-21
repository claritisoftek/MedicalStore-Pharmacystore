# Verification evidence — 2026-10-21

## Executed in this environment
- Platform: Linux x86_64, glibc 2.39; Python 3.12.14; SQLite 3.53.1.
- Libraries: openpyxl 3.1.5 and ReportLab 4.4.9.
- `python -m compileall -q pharmacy run.py tests`: passed.
- `python -m unittest discover -s tests -v`: **22 tests passed in 5.111 seconds** on the final tested source.
- Full output: `test-results-2026-10-21.txt`.

## Automated coverage
1. Empty initial business database (no users/stock/transactions).
2. Exact currency conversion and invalid/negative/nonfinite/overprecision rejection.
3. Purchase, discounted credit sale, customer/supplier balances, subsequent payments, expense, profit and cash reconciliation.
4. Entire sale rollback if a later cart item has insufficient stock.
5. Earliest-expiry batch allocation across duplicate cart entries.
6. Expired stock sale prevention.
7. Expired purchase and excessive-discount rejection without stock loss.
8. Walk-in credit/overpayment rejection.
9. Supplier overpayment rejection.
10. Same-day cancellation reverses stock/credit exactly once.
11. Cancellation after customer settlement is rejected.
12. Previous-date cancellation is rejected without changing stock.
13. Cashier may sell; restricted catalogue/backup/report/expense/purchase/settings operations rejected.
14. Password change invalidates old password; failed login clears session.
15. Snapshot restore recovers inventory, creates safety backup and forces reauthentication.
16. Invalid backup leaves current records intact.
17. Valid multi-batch Excel preview/apply and exact-file duplicate rejection.
18. Invalid Excel row rejects workbook before changes.
19. Existing barcode collision rolls back entire import.
20. Formula cells rejected.
21. A4/58mm/80mm PDFs generated successfully.
22. Purchase reference required and failed purchase leaves no header.

## Not executed / not claimed
- Interactive Tk screens (this environment has no X display server).
- Windows-specific pywin32 printer enumeration, GDI printing and driver layout.
- PyInstaller Windows executable and frozen GUI/dependency smoke test.
- Inno Setup installer compilation, offline installation, Windows 10/11 behavior, uninstall/upgrade.
- Physical 58/80 mm and A4 hardware tests, scanner hardware and long-print pagination.
- LAN operation (not implemented).

The Windows workflow and acceptance checklist are supplied to close those release gates. Passing the domain tests does not establish a customer-ready Windows installer.
