"""Collect installed distribution notices into bundled output, preserving relative paths."""
from importlib import metadata
from pathlib import Path
import sys, shutil
out=Path('build/THIRD_PARTY_NOTICES'); out.mkdir(parents=True,exist_ok=True)
for dist in metadata.distributions():
    name=dist.metadata.get('Name','unknown')
    for file in dist.files or []:
        if any(word in file.name.lower() for word in ('license','copying','notice')):
            source=Path(dist.locate_file(file))
            if source.is_file():
                dest=out/name/str(file).replace('../','')
                dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,dest)
license=Path(sys.base_prefix)/'LICENSE.txt'
if license.exists(): shutil.copyfile(license,out/'Python-LICENSE.txt')
(out/'README.txt').write_text('Third party notices collected from the build environment. This includes runtime and build tool notices. Application code is an independent implementation; see docs/UPSTREAM_REVIEW.md.',encoding='utf-8')
