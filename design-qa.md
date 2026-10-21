# Warm Dispensary design QA — v0.2.0

Source visual truth: `docs/design/selected-reference.jpg`, the third displayed concept selected by the customer.
Source dimensions: 1487 × 1058. Reference normalized to 1440 × 1024 for comparison.
Native application scope: existing Python/Tk Windows desktop software, not a web prototype. Native screenshot and interaction verification is used; browser/console checks do not apply to this user-requested desktop application.

Implementation screenshots currently available: `build/screenshots-v5/counter-1440.png`, `counter-1080.png`, `company-profile.png`, `sign-in.png`, `cashier-empty.png`.
Viewport: 1440 × 1024 and minimum 1080 × 680 client pixels. Linux fallback uses available Nimbus Sans L core font; Windows target uses Segoe UI. State: signed-in Admin, illustrative six-medicine inventory, two-line cash sale PKR 365.00, local data, no invented backup record. Customer production database remains empty on first run.

## Comparison history
1. First native capture: [P1] runtime fallback to fixed bitmap font erased typography hierarchy; [P2] footer clipped by pack order. Fixed by selecting an available font family/font path and reserving footer before the expanding workspace.
2. Second pass: [P2] medicine symbol collided with row text; [P2] row Add control lacked the selected design's green action affordance; [P2] company identity sat too far left. Fixed column spacing, actual library-icon Add buttons, and centered company identity.
3. Minimum viewport pass: [P0] payment section consumed cart height, hiding item editing. Compacted payment fields/customer selector and changed cart rows to a two-line editable layout. Added minimum visible-cart-height assertion to screenshot tests.
4. Company profile: made content scrollable with pinned Save/Cancel controls so small screens cannot hide submission controls.

## Required fidelity surfaces
- Typography: warm forest display headings, clear bold totals, readable body sizes; Windows Segoe UI still requires rendered confirmation.
- Layout/rhythm: horizontal navigation, approximately 62/38 stock/cart split, persistent cart, bottom anchored payment controls, centered company identity, independent scrolling.
- Tokens: ivory #FBFAF6, forest #24573E, sage #E4EBDE, restrained #A24D36 low-stock alerts, no decorative dashboard cards.
- Images/icons: original generated capsule application icon and leafy default company mark; standard Tabler outline icons, bundled raster assets with MIT notice. User logo replaces company mark independently of fixed software icon.
- Copy/content: English, PKR, same hero task and sample invoice arithmetic; alphabetical catalogue order is intentional. Reference manufacturer/brand sublabels are not invented because existing database has no manufacturer field.

## Current findings / release gate
Local interaction tests pass; Windows screenshots and final comparison are pending. No final release may publish until the final Windows evidence is reviewed and this report is marked passed.

final result: blocked
