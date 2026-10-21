# Branding and v0.2.0 upgrade process

## Admin logo/profile workflow
Open Company profile at the top right or in Administration. Select Replace logo, choose PNG/JPEG under 5 MB, review the preview, edit business fields and Save company profile. Cancel does not commit the draft. Remove then Save clears the uploaded logo and restores the generic leafy company mark.

Logo validation rejects corrupt files, unsupported formats and oversized dimensions. Logos are normalized to PNG within 512 × 512 with input metadata removed. The normalized PNG is stored as base64 in the existing settings table, together with profile text in a single transaction. No dependence on the original upload path remains. Cashiers cannot change this identity.

The header updates immediately while retaining the current cart. Current identity appears on newly generated and reprinted PDF/native documents; old exported PDFs are immutable files. The software capsule icon stays fixed so each pharmacy can change its own company logo independently.

## Backup and recovery
Ordinary database snapshots include the company logo and text. A restored snapshot restores its stored identity; a legacy snapshot without a logo falls back to the generic mark. No separate logo folder needs copying. Retain separate-drive backups as described in USER_GUIDE.md.

## Upgrade from 0.1.0
1. Create a fresh database backup and verify its location.
2. Close all application windows. Use the same Windows account as the live counter.
3. Run the new 0.2.0 Setup.exe. Keep the normal installation directory.
4. Launch and sign in with the existing account. Verify medicine counts, recent invoice totals and party balances.
5. Configure company profile/logo and check A4/thermal printer selection and actual paper forms.
6. Print a sample receipt/report and create a new backup after acceptance.

AppId, data path and schema version 1 remain unchanged. The installer updates binaries/assets/docs and never deploys or deletes a business database. There is no demo stock or default Admin password. Restoring an old snapshot replaces all business records and accounts, so use the deliberate restore workflow only when intended.

## Developer change points
- Palette/native styles: pharmacy/theme.py.
- Navigation/cart/profile controls: pharmacy/app.py.
- Logo validation/storage: pharmacy/branding.py.
- Branded PDF/GDI output: pharmacy/printing.py.
- Header text for documents: pharmacy/reports.py.
- Bundled capsule icon: assets/pharmacy-icon.png/.ico; update both, PyInstaller --icon and Inno Setup SetupIconFile together.
- Smoke/visual checks: pharmacy/selftest.py and packaging/capture_ui.py.
- Schema remains version 1; future structural changes still need explicit migrations.
