# Pharmacy Web verification

Final result: passed for the repository implementation.

## Exact tested implementation
- Commit: `ee2247222cccbbd938d807604eded43a72f8a473`.
- [Passing GitHub web workflow](https://github.com/claritisoftek/MedicalStore-Pharmacystore/actions/runs/39658564626).
- Node.js 22 on Ubuntu, MySQL 8.4 service, Chromium through Playwright.
- 16 Node/domain/API checks passed (including nested integration scenarios); no skipped database checks. Local MariaDB 10.11 tests also passed.
- Production dependency audit: zero reported vulnerabilities at verification time. Pinned lockfile includes patched Sharp/rate limiter and an ExcelJS uuid override; workbook generation/import tests cover that override's integration.

## Executed checks
- Private first-Admin setup, login cookies, exact-origin and CSRF enforcement.
- Empty initial business database, catalogue and customer/supplier creation, multi-batch purchasing.
- Earliest-expiry-first allocation, stock rollback, concurrent sales cannot oversell, retry keys return one invoice, stale displayed price rejection.
- Credit sale, collection limits, subsequent payments, expense, same-day cancellation restrictions and financial reports.
- Logo normalization, disguised SVG rejection, escaped receipt content, A4/thermal document routes.
- Atomic Excel opening stock import, preview, formula rejection and duplicate workbook protection.
- Cashier cannot invoke Admin APIs or download backups and sees only role-appropriate records.
- Invalid restore rolls back, inconsistent financial totals are rejected, valid restore keeps safety snapshot and invalidates all sessions.
- Browser login, real logo file upload/profile save, Add, quantity/cart display, PKR 100 tender / PKR 10 sale gives PKR 90 change.
- Browser simulates a successful server checkout followed by an interrupted HTML error response. Retrying creates exactly one invoice.
- Receipt window, vendor-bill form, report generation, company profile, mobile touch actions/current-sale shortcut and logout.
- Desktop 1440 × 1000 and mobile 390px screenshots reviewed. No horizontal page overflow or browser JavaScript errors in the tested flow.

## Screenshots reviewed
These contain only disposable test data. Production first-run database remains empty.

[Desktop counter](design/web-counter.png) · [Mobile counter](design/web-mobile.png) · [Company profile](design/web-company-profile.png)

The first visual pass showed Add controls offscreen on small devices. Catalogue rows now become mobile cards with visible Add buttons; a Review sale shortcut reaches the cart. The revised captures show controls and totals without clipping. The selected ivory/forest design, medicine icon and replaceable company mark are preserved. No actionable blocking visual findings remain in reviewed screens.

## Corrections during verification
MySQL requires cross-column payment constraints at table level; corrected and rerun successfully. The browser harness needed an explicit repository-root working directory. Its output folder now preserves Node logs. These were resolved before main promotion.

## Deployment and physical acceptance
Passing CI verifies code, transactions and browser behavior against disposable databases. It does not deploy a Hostinger account or validate that account's credentials, DNS or HTTPS configuration. Follow [Hostinger guide](HOSTINGER_WEB.md), then verify the actual production URL/health/login/database persistence and the customer's physical thermal/A4 printers and scanner. Browser printing requires the local print dialog. Windows device/DPI acceptance remains separate. Hosted MySQL and offline desktop SQLite do not synchronize automatically.
