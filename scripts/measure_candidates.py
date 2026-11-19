"""Measure every 60 dpi render in work/cand/: aspect, ink and white_in, written to work/candcolours.json.
usage (from the mosaic folder): python3 -I scripts/measure_candidates.py
Keys already in work/candcolours.json are kept (delete the file to measure everything again).
  crop     to the bounding box of non-white pixels (difference from white > 20 of 255)
  aspect   width / height of the crop
  white_in share of the crop's pixels (after scaling it to fit 232x192, LANCZOS) with Lab L > 95 and chroma < 5
  ink      share of the pixels of a white 240x200 canvas, with the scaled crop pasted in its centre, that have L < 90"""
import os, json, numpy as np
from PIL import Image, ImageChops
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = f'{HERE}/work'
def lab(rgb):
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T / [0.95047, 1, 1.08883]
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def measure(png):
    try: im = Image.open(png).convert('RGB')
    except Exception: return None
    bb = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda v: 255 if v > 20 else 0).getbbox()
    if not bb: return None
    im = im.crop(bb); w, h = im.size; k = min(232 / w, 192 / h)
    im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    Li = lab(np.asarray(im, float) / 255).reshape(-1, 3)
    cell = Image.new('RGB', (240, 200), 'white'); cell.paste(im, ((240 - im.width) // 2, (200 - im.height) // 2))
    L = lab(np.asarray(cell, float) / 255).reshape(-1, 3)
    return {'ink': float((L[:, 0] < 90).mean()), 'aspect': w / h, 'white_in': float(((Li[:, 0] > 95) & (np.hypot(Li[:, 1], Li[:, 2]) < 5)).mean())}
if __name__ == '__main__':
    out = f'{W}/candcolours.json'; cc = json.load(open(out)) if os.path.exists(out) else {}
    keys = [f[:-4] for f in sorted(os.listdir(f'{W}/cand')) if f.endswith('.png') and f[:-4] not in cc]
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(lambda k: measure(f'{W}/cand/{k}.png'), keys))
    cc.update({k: m for k, m in zip(keys, res) if m}); json.dump(cc, open(out, 'w'))
    print(len(cc), 'measured in all,', len(keys), 'new')
