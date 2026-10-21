"""Convert a supplied/generated original app icon into runtime PNG and Windows ICO.
Usage: python packaging/prepare_app_icon.py /path/to/original-icon.png
"""
from pathlib import Path
import sys
from PIL import Image
root=Path(__file__).resolve().parent.parent/'assets';root.mkdir(exist_ok=True)
with Image.open(sys.argv[1]) as source:
    icon=source.convert('RGBA');icon.thumbnail((256,256),Image.Resampling.LANCZOS)
    if icon.width!=icon.height: raise ValueError('Supply a square icon')
    icon.save(root/'pharmacy-icon.png',optimize=True)
    icon.save(root/'pharmacy-icon.ico',sizes=[(n,n) for n in (16,24,32,48,64,128,256) if n<=icon.width])
