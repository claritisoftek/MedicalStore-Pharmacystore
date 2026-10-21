"""Company branding is portable database data; software identity is a bundled asset."""
from pathlib import Path
from io import BytesIO
import base64, warnings
from PIL import Image, ImageOps

MAX_FILE=5*1024*1024
MAX_PIXELS=12_000_000

def normalize_logo(raw):
    if not raw or len(raw)>MAX_FILE: raise ValueError('Choose a PNG or JPEG logo smaller than 5 MB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in ('PNG','JPEG'): raise ValueError('Only PNG and JPEG logos are supported')
                if source.width*source.height>MAX_PIXELS: raise ValueError('Logo dimensions are too large')
                image=ImageOps.exif_transpose(source).convert('RGBA')
                image.thumbnail((512,512),Image.Resampling.LANCZOS)
                out=BytesIO(); image.save(out,format='PNG',optimize=True)
                return out.getvalue()
    except (Image.DecompressionBombError,Image.DecompressionBombWarning): raise ValueError('Logo dimensions are too large')
    except (OSError,SyntaxError) as e: raise ValueError('Cannot read this image; choose a valid PNG or JPEG') from e

def logo_bytes(store):
    encoded=store.get_setting('logo_png')
    if not encoded: return None
    try: return normalize_logo(base64.b64decode(encoded,validate=True))
    except (ValueError,TypeError): return None

def save_profile(store,values,logo=None):
    store.authorize(True)
    allowed={'name','address','phone','email','tagline','footer'}
    cleaned={key:str(value).strip() for key,value in values.items() if key in allowed}
    if not cleaned.get('name'): raise ValueError('Company name is required')
    if any(len(value)>500 for value in cleaned.values()): raise ValueError('Profile fields must be 500 characters or fewer')
    if logo is not None: cleaned['logo_png']=base64.b64encode(normalize_logo(logo)).decode() if logo else ''
    store.settings(cleaned)
