# Asset provenance

Application capsule icon and default leafy company mark are original generated branding assets for this release, based on the user-selected Warm Dispensary concept. Company logo is replaceable by Admin. UI icons are unmodified Tabler outline artwork rasterized to green/white PNGs at build preparation; MIT license retained at assets/icons/LICENSE-Tabler.txt. CairoSVG is used only to prepare these bundled raster assets and is not required by the customer runtime.

Tabler source: https://github.com/tabler/tabler-icons
Reviewed icon source commit: a4ce1404bc6d24d3c365afe7b258d6bf6f48d62d

## Future asset preparation
Bundled runtime PNG artwork is optimized to 256 × 256 (rendered at smaller UI sizes); Windows ICO carries 16–256 px variants. To regenerate standard controls, clone the recorded Tabler source revision, install CairoSVG==2.9.1 in a developer environment, and run `python packaging/prepare_icons.py /path/to/tabler-icons`. This optional preparation tool is never run at customer startup or during ordinary Windows builds.

For a replacement original medicine application icon, run `python packaging/prepare_app_icon.py /path/to/original-square-icon.png`, review 16/32/48 px output and rebuild both executable and installer. Use Image Gen or supplied original brand artwork for image creation; the conversion script only resizes/encodes it. Default leafy company artwork is in assets/company-default.png; customers normally replace it through Admin → Company profile, without source edits.
