"""Save a low-resolution PNG copy of a big grid image, under a size limit (default 1 MB).
usage: make_lowres.py BIG.png LOWRES.png [max_bytes]"""
import sys, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
src, dst = sys.argv[1:3]; limit = int(sys.argv[3]) if len(sys.argv) > 3 else 1_000_000
im = Image.open(src).convert('RGB')
for w in (2400, 2200, 2000, 1800, 1600, 1400, 1200):
    sm = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    for name, img in (('rgb', sm), ('256 colours', sm.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE))):
        img.save(dst, optimize=True)
        if os.path.getsize(dst) <= limit:
            print(f'{dst} {sm.size} {name} {os.path.getsize(dst) // 1024} KB'); sys.exit()
sys.exit(f'could not get {dst} under {limit} bytes')
