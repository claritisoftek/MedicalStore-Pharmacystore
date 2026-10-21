# Upstream assessment and provenance

Reviewed 2026-10-21.
Source requested: https://github.com/MusheAbdulHakim/Pharmacy-management-system
Reviewed commit: `0f6455ed171ff21f447bb776fb093d76fdefc055`.
Read repository metadata, README, composer.json, package.json, migrations/models list and SaleController.

## Findings
The source is a Laravel 8 web application, with PHP, Composer, npm build tooling and a MySQL-oriented setup. The README's installation procedure is a development web-server procedure, not a packaged Windows desktop installer. It lists catalogue, purchases, sales, suppliers, users/roles, reporting and backups.

composer.json declares MIT for the Laravel project, and the README describes the Laravel framework as MIT. No standalone LICENSE file was found at the reviewed root. The README separately credits the commercial Doccure ThemeForest template. Framework licensing does not establish redistribution rights for that theme. This is a provenance observation, not a legal determination.

The inspected SaleController records individual sales against purchase quantity, rather than the transactional multi-line invoice and batch allocation required here. Reusing it would require further accounting, expiry and consistency work.

## Decision and implementation boundary
This deliverable is an **independent replacement implementation**, informed by the requested feature list. It is not a converted Laravel fork and does not claim compatibility with the upstream database. No upstream PHP, template, image, theme, SQL seed data, credentials or screenshots are distributed in the source package. This avoids silently redistributing the theme or shipping demonstration credentials/data.

The original source remains separately cloned in the working environment for assessment only. It is not included in the customer handover archive. Existing Laravel databases require a separately designed migration into the documented Excel template; they cannot be opened directly by this application.

## Traceable mapping
| Original concept | Desktop implementation |
|---|---|
| Laravel controllers/models | `pharmacy/core.py` Store operations and SQLite schema |
| Blade/Doccure UI | Original Tk/ttk desktop UI in `pharmacy/app.py` |
| MySQL | Embedded SQLite local file |
| Roles/permissions packages | Admin/Cashier checks at write/report operation boundary |
| Stock from purchase rows | Explicit batches, immutable sale allocations and stored cost snapshots |
| Browser export/print | Local PDF generation and Windows GDI printer drawing |
| Web deployment | PyInstaller application directory plus Inno Setup installer recipe |

If the business specifically requires retaining the original Laravel screens or source, treat that as a separate implementation path, verify theme redistribution rights and package a supported PHP runtime/web host/database instead. Those components are not part of this package.
