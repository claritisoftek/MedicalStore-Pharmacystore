# Pharmacy Desktop v0.2.0 — Warm Dispensary

Modern offline Windows pharmacy software using PKR and English.

## New in this release
- User-selected warm ivory/forest-green design, horizontal navigation and clearer screen headings.
- Medicine catalogue search with visible Add controls and a persistent cart.
- Inline quantity editing, discounts, payment received and live change calculation; F2 Search, F3 Add, F5 Complete sale.
- Original capsule medicine icon for the application, desktop shortcut and installer.
- Admin-editable Company profile: replace/remove PNG or JPEG logo, company name, tagline, address, phone, email and receipt footer.
- Company logo is stored in the database and included in backups/restores, PDF output and native printer output. Changing business identity does not replace the software capsule icon.
- Existing v0.1.0 database, accounts and business records are retained. No schema reset or sample records are shipped.

## Downloads
Setup.exe includes all application dependencies; Python, PHP, MySQL, Microsoft Excel and internet are not required for normal customer use. Install the correct Windows printer drivers separately.
Portable.zip contains the complete runnable directory. Source.zip contains matching code/tests/build scripts. Documentation.zip includes customer/developer guides, design QA, change records and the Excel opening inventory template. Checksums and build evidence are attached.

## Updating from v0.1.0
Create a database backup, close the app, and run the new installer under the same Windows account. The installer keeps the same AppId and data folder. Do not delete your data directory or create a new Windows profile to upgrade.

## Company logo changes
Admin → Company profile → Replace logo → Save company profile. PNG/JPEG up to 5 MB; images are normalized to a portable PNG of maximum 512 × 512. Remove restores the generic company mark. Current company identity is used for newly generated and reprinted documents.

## Verification and limits
Windows release pipeline runs domain tests, native UI interaction checks, icon/logo loading, frozen executable smoke, installation/installed-app smoke and uninstallation on Windows Server 2022. Native screenshots and the design-QA report document visual verification. Physical thermal/A4 printer tests, actual scanner hardware and customer Windows 10/11 acceptance at 125/150% DPI remain device-specific checks. Installer is unsigned.

Single workstation only; LAN server mode remains future work. Whole sale units only. Excel imports new opening inventory/batches, not transaction history or opening party balances. Same-day whole-sale cancellation only; no partial/historical returns, purchase correction, disposal/adjustment or FBR integration. Live cash tender/change is UI guidance; stored invoice payment is the applied amount and receipt reprints use that stored amount.

## Licence
Existing GPL-3.0 retained. Application source is included. Dependency and Tabler icon notices retain their original licences.
