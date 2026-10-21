"""Optional maintainer tool: rasterize the bundled Tabler icon subset, not a runtime dependency.
Usage: python packaging/prepare_icons.py /path/to/tabler-icons
Install CairoSVG==2.9.1 in the asset preparation environment first.
"""
from pathlib import Path
import sys,shutil
import cairosvg
source=Path(sys.argv[1]); target=Path(__file__).resolve().parent.parent/'assets/icons'; target.mkdir(parents=True,exist_ok=True)
names=['pill','search','user','building-store','credit-card','trash','database','photo','plus','minus','logout']
for name in names:
    svg=(source/'icons/outline'/(name+'.svg')).read_text()
    for suffix,color in [('', '#24573E')]+([('-white','#FFFFFF')] if name in ('credit-card','plus') else []):
        cairosvg.svg2png(bytestring=svg.replace('currentColor',color).encode(),write_to=str(target/(name+suffix+'.png')),output_width=48,output_height=48)
shutil.copyfile(source/'LICENSE',target/'LICENSE-Tabler.txt')
