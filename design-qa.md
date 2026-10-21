# Warm Dispensary design QA — v0.2.0

final result: passed

## Source and rendered evidence
- Source visual truth: `docs/design/selected-reference.jpg`, high-quality export of the third displayed Image Gen concept explicitly selected by the customer. Original source was 1487 × 1058; reference normalized to 1440 × 1024 for comparison.
- Native Windows implementation: `docs/design/windows-counter.png` (1440 × 1024 client/image pixels), `windows-compact.png` (1080 × 680), `windows-company-profile.png` (700 × 800).
- Full comparison input viewed together: `docs/design/visual-comparison.jpg`, source on left, Windows implementation on right, both normalized to 1440 × 1024. Focused payment comparison was also viewed at readable density (`build/windows-verified/payment-comparison.jpg`).
- Supporting Windows captures: Stock, Purchases, Reports, Administration, branded header, Cashier empty state and sign-in, retained in the workflow evidence and UI-Screenshots release archive.
- Verified Windows build: commit `352fade105956a799ce5e75add1d396552e6ae74`, workflow run `39631644115`. Domain, native interaction/screenshot, frozen app, installation, installed app and uninstall checks all passed.
- Scope: native Python/Tk Windows desktop software, not a web prototype. Native client screenshots and callback/interaction checks replace web browser/console checks for this user-requested desktop application. No browser-rendered preview or site publication is claimed.
- Density: screenshot bounds use native client coordinates and match PNG dimensions 1:1; no OS title bar included. Reference normalization aligns the intended viewport. Final capture helper additionally records screen size, Tk scaling and actual font metadata in render-info.json for release evidence.
- State: signed-in Admin, six illustrative medicines, two-line cash sale totalling PKR 365.00, 21 October 2026. The compact screenshot is taken after an exercised checkout, so its remaining stock reflects that test sale. Production first-run data remain empty.

## Comparison history and fixes
1. First local capture: [P1] unsupported Linux fallback produced a fixed bitmap font; [P2] expanding workspace hid the footer. Selected an available sans-serif family/font path and reserved the footer before expanding the workspace. Native Windows rendering now uses Segoe UI with readable heading/body hierarchy.
2. Second pass: [P2] medicine icons collided with text; [P2] Add actions lacked the green affordance; [P2] company identity was too far left. Increased tree icon-column spacing, added real Tabler-icon buttons and centered company identity. Windows counter evidence confirms the corrections.
3. Compact layout: [P0] payment controls consumed the cart editing region. Condensed the customer/payment layout and cart rows, while preserving independent cart scrolling and bottom-reserved payment controls.
4. First Windows preview: the compact cart was only 69px high. Added compact payment-button styles below 800px window height, retained an 80px minimum editable-cart assertion, and reran Windows checks. `windows-compact.png` shows a complete editable line and visible payment actions; the minimum-height check passes.
5. Profile: pinned Save/Cancel outside scrollable profile content, so smaller windows cannot hide submission controls. `windows-company-profile.png` confirms logo preview/replacement/removal and all profile fields.
6. Added wheel scrolling through cart child controls and reduced generic/purchase table requested heights so other native pages remain usable in smaller windows. Reviewed Windows Stock/Purchases/Administration captures with no hidden primary actions.

## Required fidelity surfaces
- **Fonts/typography:** Segoe UI on Windows, bold forest display headings, readable 14–15px body/counter text, distinct totals and consistent captions. Native compact density is intentional; no fixed-font fallback or clipped display copy remains in Windows evidence.
- **Spacing/layout:** horizontal navigation, approximately 62/38 stock/cart split, persistent editable cart, centered company mark, reserved footer, bottom payment actions and independent scrolling. Native fields are a little denser than the concept so the same application also fits a common smaller counter display.
- **Colors/tokens:** ivory #FBFAF6, forest #24573E, sage #E4EBDE, muted text and restrained #A24D36 stock alerts. No decorative KPI dashboard, nested cards or unrequested feature panels were introduced.
- **Images/icons:** original generated medicine capsule icon and leafy default company mark; crisp rasterized Tabler controls with licence. Company logo is replaceable independently of software icon. No handmade replacement icon shapes or text-glyph icons are used.
- **Copy/content:** English/PKR, same hero task and invoice arithmetic. Alphabetical catalogue order and omission of manufacturer sublabels reflect the existing data model. Actual backup status is used instead of inventing a backup timestamp from the concept.

## Interaction evidence
Windows capture checks exercised visible Add button, barcode scan, quantity change, cart wheel scrolling, PKR 500 received against PKR 365 giving PKR 135 change, checkout creating one invoice and clearing cart, logo picker/profile save retaining the current cart, minimum-window controls, Cashier navigation and sign-in. Frozen/installed checks exercised bundled medicine icon, company-profile rendering, Excel and logo-bearing PDF generation. 30 domain/branding regression tests passed.

## Findings
No actionable P0/P1/P2 findings remain for the selected native design adaptation. Full and focused comparisons and compact/profile/other-page captures were reviewed after fixes.

## Follow-up polish / residual acceptance
- [P3] Native controls and square medicine icon differ slightly from the concept's soft radii; the palette, hierarchy and workflows are preserved.
- [P3] Manufacturer/brand sublabels would require a future catalogue-field/import change; no fabricated brand data were added.
- Physical printer/scanner operation, customer Windows 10/11 checks at 125/150% DPI and real-world upgrade acceptance remain device-specific tests. These are not claimed by screenshot/CI checks.

## Implementation checklist
- [x] Selected direction implemented and source/actual Windows screenshots compared together.
- [x] Earlier P0/P1/P2 layout issues fixed and recaptured.
- [x] Company logo/profile editing, database portability and branded document output implemented.
- [x] Existing schema, accounts/data location and installer identity retained.
- [x] Native Windows build, UI and installer tests pass; matching documentation and evidence packaged.
