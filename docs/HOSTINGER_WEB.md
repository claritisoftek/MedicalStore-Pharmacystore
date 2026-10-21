# Pharmacy Web — Hostinger deployment and operation

## What changed
The repository now includes an independent browser application in addition to the existing Python/Tk Windows application. The root `package.json` identifies **Express** to Hostinger, installs pinned dependencies using `package-lock.json`, and starts `server.js`. The web UI uses the selected Warm Dispensary palette and existing licensed/generated application assets. The desktop source, installer workflow and SQLite files are not replaced.

Web technology: Node.js 22 or 24, Express 5, MySQL/MariaDB InnoDB through mysql2, browser HTML/CSS/JavaScript, ExcelJS for .xlsx and Sharp for safe logo normalization. No Python or build-time database connection is needed for the web build. `npm run build` validates JavaScript; this is a running Express backend, not a static export.

## Deploy from your GitHub repository
1. In Hostinger choose **Node.js Web App**, reconnect this repository, branch **main**, root directory **/**, framework **Express**, Node **22** (or 24).
2. Install command: `npm ci`. Build command: `npm run build`. Start command: `npm start`. Entry file if requested: `server.js`. Do not select static hosting or point the application root to `web/public`: that would omit authentication and the database API.
3. Create a **new dedicated empty MySQL database and database user** in hPanel → Databases → Management. Do not select another customer's or an existing application's database. Copy the full names including Hostinger's account prefix.
4. Add the following environment variables in the Node.js application settings. Keep real passwords and tokens outside GitHub:

| Name | Value |
| --- | --- |
| `NODE_ENV` | `production` |
| `APP_URL` | Your exact HTTPS website origin, e.g. `https://pharmacy.example.com` (no path) |
| `DB_HOST` | `127.0.0.1` for Hostinger's local MySQL service |
| `DB_PORT` | `3306` |
| `DB_USER` | Full database username from hPanel |
| `DB_PASSWORD` | That database user's password |
| `DB_NAME` | Full dedicated database name from hPanel |
| `SETUP_TOKEN` | A private random value of at least 32 characters; use a password manager to generate it |
| `TZ` | `Asia/Karachi` |

Hostinger provides `PORT`; the server uses it. `.env.example` is documentation only. Never upload a real `.env` to GitHub. `APP_URL` must exactly match the origin used in your browser; a wrong domain or HTTP/HTTPS mismatch blocks form submissions intentionally. Keep HTTPS enabled.

5. Deploy/restart. Startup creates the web tables without inserting business records. `/health` returns `{ "ok": true }` only when MySQL is reachable. The build can succeed even if database variables are missing; check **runtime logs** for connection errors.
6. Visit your site. Create the first Admin with your private `SETUP_TOKEN`, username and a password of at least 10 characters. There is no default administrator/password. Once configured, the public setup endpoint cannot create another first Admin.
7. Confirm login, an empty catalogue, company profile save and a backup download. On a disposable test database, test purchase → sale → receipt before entering real records. Document the deployed URL and source commit for the customer.

This change prepares the repository for hosting. It does not create a Hostinger website/database, configure DNS, or enter credentials in your account automatically.

Official Hostinger references:
- https://www.hostinger.com/support/how-to-deploy-a-nodejs-website-in-hostinger/
- https://www.hostinger.com/support/connecting-a-hostinger-mysql-database-to-a-node-js-application/
- https://www.hostinger.com/support/how-to-add-environment-variables-during-node-js-application-deployment/

## Daily operation
- **Stock:** create medicines and unit sale prices, or download the opening-inventory template. All quantities are whole sale units; use the same tablet/strip/unit basis for purchase and sale prices.
- **Suppliers / Purchases:** create supplier, add multiple dated batches to a vendor bill, enter the paid amount, save and print the A4 bill. Saving updates inventory and payables atomically.
- **Counter:** type a medicine or scan an exact barcode/SKU and press Enter; Add, edit quantities, select a customer when granting credit, enter discount and cash received. Complete sale uses current server prices and earliest unexpired batches. Excess tender is change; only applied payment is stored. F2 focuses search and F5 submits. Sales provides receipt reprints.
- **Customers / Suppliers:** record subsequent collections/vendor payments and print statements. Payments cannot exceed the outstanding balance. Admin manages payments; Cashier can add customers and sell.
- **Sales:** last 200 records; Cashier sees their own sales. Admin can cancel an entire posted same-day sale if subsequent payments do not prevent cancellation. No partial/historical returns workflow is claimed.
- **Expenses / Reports:** record expenses and run date-range revenue, cost of goods, operating-result and cash-movement reports. Figures use PKR paisa integers; Pakistan calendar dates are used server-side.
- **Administration:** change company logo/name/contact/footer, create Admin/Cashier users, download/restore backups and review recent audit activity. Changing one's password signs out all of that user's sessions. Sessions expire after eight hours and persist in MySQL across server restarts.

## Printer behavior
Receipts support 58 mm, 80 mm and A4 browser layouts. Vendor bills, statements and reports use A4. Use **Print / Save PDF** and choose the matching paper size in the browser and installed printer driver. Browser security requires the user's print dialog; silent Windows native printing is a desktop-only feature. No remote host can directly control a customer's USB printer. Actual thermal roll margins/height, A4 output and barcode scanner hardware require device acceptance checks.

## Excel opening inventory
Use the web template, not a renamed desktop workbook. Columns in order: `sku, name, barcode, category, price, reorder, batch, expiry, quantity, cost`. Prices/costs are PKR decimal strings/numbers with at most two decimals, dates `YYYY-MM-DD`, quantities/reorder whole numbers. Upload `.xlsx` up to 5 MB / 5,000 data rows, validate/preview, then explicitly Apply. Formula cells and expired stock are rejected. Identical workbook bytes cannot be applied twice; importing changed files again can add new batches, so operators must check contents carefully. Existing SKUs must match catalogue fields. Imports do not load transaction history or opening party balances.

## Backups, restore and redeployment
Business data, logos, sessions and audit records are in MySQL, outside the source checkout. Keep the same database variables during redeployment; never drop/reset the production database to update code.

Admin downloads a versioned **web JSON backup**, including account password hashes and all business tables. Store it securely off-host. Browser restore currently accepts files up to 12 MB; for larger databases use managed MySQL backups/exports and a developer-supervised restore. Do not expose backup files in public folders. Use a valid backup and the current Admin password to restore; the operation validates schema columns and database relationships and applies in a single transaction. It records a safety snapshot in `web_backups` before replacing data. If restore fails, current records remain. Successful restore signs out everyone; sign in with accounts from the backup. Administration lists safety snapshots for download. Safety snapshots are in the same MySQL database, so also maintain independent Hostinger/off-host database backups.

The Windows SQLite database and web MySQL database are **separate**. They do not synchronize automatically, and their backups are not interchangeable. Opening stock can be transferred through the documented web Excel template; transaction-history migration requires a separate validated migration.

## Security and maintenance
- No registration for additional users; only Admin creates users. First setup is guarded by a private hosting token.
- Passwords use salted PBKDF2-SHA256 (600,000 rounds), compatible in algorithm with the desktop but separate accounts/storage.
- Random session tokens are stored as SHA-256 digests in MySQL. HttpOnly, SameSite=Strict and production Secure cookies; CSRF token + exact-origin validation on changes; sign-in rate limiting; Helmet CSP and security headers.
- Server enforces roles; hiding UI controls alone does not grant/restrict access. No SQL credentials or password hashes are returned by normal state endpoints.
- All mutations take a shared InnoDB transaction lock; stock checks, FEFO allocation and ledger updates are atomic across processes. Checkout keys make identical retried submissions return the same invoice, protecting against a lost response/double click.
- Browser templates escape business text. Logos are size/pixel-limited, decoded, resized and re-encoded as PNG; external logo URLs/SVG uploads are not accepted.
- Run one application instance for in-memory login rate-limit consistency; sessions and accounting transactions themselves are database-backed. Add a shared rate-limit store before scaling to multiple independent instances.
- Keep pinned dependencies and lockfile; run `npm ci`, `npm run build`, `npm test`, `npm audit`. Run full tests with a dedicated MySQL database name ending `_test` and `RUN_DB_TESTS=1`. Tests erase that test database's application tables, never run against production.
- Database schema version is `web_meta.version=1`; future changes need explicit tested migrations. Existing installations are never auto-reset.
- `web/service.js`: business transaction logic. `web/db.js`: schema and connection boundary. `server.js`: authentication, routes and deployment entry. `web/public/`: responsive UI/print controls. `web/printing.js`: escaped documents. `web/test/`: Node tests. `web/browser/`: browser acceptance checks. `.github/workflows/test-web.yml`: MySQL integration and browser CI.

## Scope and acceptance limits
Hosted app requires internet; offline Windows operation remains available in the desktop release. Multi-user browser access shares one pharmacy database (not separate tenants). There is no offline sync, pack conversion, tax/FBR integration, prescription register, partial returns or purchase amendments. Prices are generic PKR amounts. List views show the latest 200 sales, vendor bills and expenses, latest 100 audit events; date-range reports include all matching database records. Physical printers, production Hostinger runtime, clean Windows devices and customer acceptance must be verified after deployment; a GitHub CI result does not claim those checks.
