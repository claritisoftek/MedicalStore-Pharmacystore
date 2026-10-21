# Maintenance and future changes

## Change process
1. Keep this package in a business-owned Git repository; commit the original handover as the baseline. Current repository: https://github.com/claritisoftek/MedicalStore-Pharmacystore.
2. Open a change record describing the user-visible trigger, intended behavior, affected financial/stock records and compatibility.
3. Back up a disposable test database and preserve the prior release.
4. Change the smallest appropriate module using TECHNICAL_GUIDE.md's module map. Keep GUI code free of direct business writes; add operations to Store or a replacement service.
5. For financial or inventory changes add meaningful regression coverage. Re-run unit tests and the frozen Windows smoke check.
6. Update schema migration code/version where required, documentation, CHANGELOG, application version, installer version and release filename consistently.
7. Build on Windows, run acceptance on a clean machine and relevant actual printers, then record the new release hash and customer's installed version.

## Common modifications
| Request | Files/process |
|---|---|
| Business text/printer names | Administration settings; no source changes needed |
| Business logo | Admin → Company profile, Replace logo/Remove and Save; code in branding.py, app.py and printing.py |
| New field on a medicine | Schema migration, Store validation, product dialog, import template/validation, stock display, reports and tests |
| New report | Add authorized report builder in reports.py, UI entry and date/financial reconciliation tests |
| Pack/tablet conversion | Design canonical base unit plus purchase/sale conversion and rounding rules before changing quantities |
| Taxes | Define legal/tax requirements and line/header tax snapshots, receipt fields, accounting/reconciliation and rounding tests |
| Returns | Add separate dated return headers/lines, original allocation links, stock condition decisions, cash/credit reversals and audit; never edit historical invoices silently |
| Stock loss/expiry disposal | Add reasoned quantity movements with approval, timestamp, cost and auditable stock reconciliation |
| Import existing customer/supplier balances | Design migration/opening-ledger entries and matching keys; current inventory template cannot carry these |
| Admin account reset/disable | Add a controlled account-management UI, prevent disabling the last active Admin, audit resets and force password change |

## LAN expansion design — not implemented
Do not turn the SQLite file path into `\\server\share\pharmacy.sqlite3`. SQLite WAL and filesystem locking are not a multi-PC deployment architecture.

1. Keep one host responsible for transactions; expose authenticated APIs for product lookup, purchases, checkout, payments, reports and backups.
2. Desktop clients use a service adapter instead of directly opening the database. Keep Store transaction semantics and permission checks at the host boundary.
3. Evaluate PostgreSQL for server deployment. SQLite can remain host-local for a small workload if access is serialized through the host process, but this needs measured concurrency testing.
4. Add TLS/trusted local certificate setup, host authentication, durable sessions, firewall rules, host discovery/static address and a Windows service lifecycle.
5. Add idempotency keys to checkout/payment APIs so client retries cannot duplicate invoices or payments.
6. Test concurrent sales of the last stock unit, network interruption after commit, host restart, simultaneous payments, login revocation and coherent backups.
7. Each counter owns its own printer selection and prints the committed receipt returned by the host. Failure to print must not repeat the transaction.
8. Disable offline writes while disconnected unless a separate synchronization/conflict protocol is designed. This release has no cross-computer sync.

## Database migration policy
Version 1 currently checks the exact schema version; it is not a generic migration framework. Future changes must include sequential migrations, explicit transaction boundaries where SQLite permits, compatibility checks and restore tests against older backup files. Test upgrade on a copy of actual shaped data and validate balances, line costs and batch quantities afterward.

## Known design limits and hardening work
- Whole units only; no partial/historical returns, stock correction/disposal or purchase reversal.
- No party edit, user reset/deactivation UI or persistent lockout policy yet.
- Audit is application-generated and can be edited by someone with raw database access.
- Backups and database are unencrypted; add encryption only with a key/recovery plan and independent tests.
- Reports are management summaries, not a general ledger/statutory reporting system.
- Vendor reference is required but not unique; operator must avoid recording the same vendor bill twice.
- Financial dates come from local Windows clock; no date lock/accounting close exists.
- Current native printer code respects driver defaults; driver-specific thermal cut/ESC-POS features are not implemented.
- The domain tests run here; Tk screens, Windows dependencies, installer and physical devices require the documented Windows checks.
