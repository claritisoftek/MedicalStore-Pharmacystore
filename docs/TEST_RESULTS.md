# Verification — v0.2.0

## Local executed checks
- Python source compilation: passed.
- 30 automated tests: 22 accounting/stock/import/backup tests plus eight branding tests.
- New tests cover logo replacement/removal, invalid-file rollback, JPEG normalization/resizing, logo backup/restore under schema version 1, Cashier authorization, logo-bearing PDF at A4/58/80 mm, text-only updates preserving the logo and legacy/malformed-logo fallback.
- Native Tk interaction capture on a temporary X display: barcode scan, cart quantity adjustment, PKR 500 tender against PKR 365 total gives PKR 135 change, checkout commits one invoice, cart clears after commit, minimum viewport reserves visible cart/payment controls, company profile, Cashier navigation and sign-in.
- Native source smoke check: Admin/Cashier pages, bundled medicine icon/default logo, profile dialog, PDF/Excel module loading: passed.

## Windows release evidence
The Windows build runs the same tests and native interaction capture, frozen executable smoke, installer compilation, installed executable smoke and uninstallation. Logs/provenance/smoke results and native screenshots are retained as Actions artifacts. Published release evidence applies to the exact source commit listed in build-provenance.json. Publication requires design-qa.md to say final result: passed.

## Remaining physical checks
Actual printer driver image output/thermal roll handling, actual barcode scanner hardware, customer Windows 10/11 interactive acceptance and 125/150% DPI remain device-specific checks. No network/LAN support is claimed. The installer is unsigned.

The prior test-results-2026-10-21.txt file records the historical 0.1.0 22-test Linux baseline; current Windows build/test output is retained separately.
