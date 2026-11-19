"""16x16 thumbnails of every physics-plot candidate AS IT IS DRAWN IN ITS SQUARE CELL, for the mosaic "CMS physics in 1530 plots".

Pool = work/cands.json (panels that passed the HARD caption filter and the BLACK list) PLUS extra_cands.json (plots of
the papers outside the 1521-paper selection, see extra_candidates.py) whose measurements in work/candcolours.json /
extra_colours.json pass the photo / legend checks (aspect 0.4-3, ink > 3%, white inside > 5%).
A paper with no plot passing the aspect limit gets its plots with aspect up to 3.5 (one paper: 2005.14219).
How a plot is put into the square cell (same rule in CMSPlotsMosaic.py):
  * width/height between AMIN and AMAX: drawn as an exact square (shape change at most 17 %)
  * wider or taller: stretched only up to that limit, then centred in the cell with white above/below (or beside)
For each: crop the 60 dpi render to its ink, draw it that way on a white 64x64 square, shrink to 16x16 (BOX filter).
Output: scripts/tile_thumbs.npz
        (keys, T uint8 (N,16,16,3), aspect, fill = share of the cell the plot covers, soft, main, amin, amax)
usage (from the mosaic folder): python3 -I scripts/tile_thumbs.py"""
import os, json, numpy as np
from PIL import Image, ImageChops
from concurrent.futures import ThreadPoolExecutor
SCR = os.path.dirname(os.path.abspath(__file__)); HERE = os.path.dirname(SCR)   # scripts/ and the mosaic folder
W = f'{HERE}/work'; SRC = f'{HERE}/cms_sources'
S, B, AMIN, AMAX = 16, 64, 0.85, 1.18
cands = json.load(open(f'{W}/cands.json')) + json.load(open(f'{HERE}/extra_cands.json'))
cc = json.load(open(f'{W}/candcolours.json')); cc.update(json.load(open(f'{HERE}/extra_colours.json')))
def png(k): return f'{W}/cand/{k}.png' if os.path.exists(f'{W}/cand/{k}.png') else f'{HERE}/extra_cand/{k}.png'
def ok(m, amax): return m and 0.4 < m['aspect'] < amax and m['ink'] > 0.03 and m['white_in'] > 0.05
key = lambda c: f"{c['paper']}__{c['fig']}__{c['panel']}"
have = {c['paper'] for c in cands if ok(cc.get(key(c)), 3.0)}
keep = [(key(c), c.get('soft', False), c['main']) for c in cands
        if ok(cc.get(key(c)), 3.0 if c['paper'] in have else 3.5) and os.path.exists(png(key(c)))]

def crop_ink(im):
    bb = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda v: 255 if v > 20 else 0).getbbox()
    return im.crop(bb) if bb else im

def cell_size(a, side):
    """(w, h) of a plot with aspect a (width/height) inside a square cell of `side` px"""
    e = a / AMAX if a > AMAX else a / AMIN if a < AMIN else 1.0          # aspect left after the allowed stretch
    return (side, max(1, round(side / e))) if e >= 1 else (max(1, round(side * e)), side)

def feat(item):
    k = item[0]
    try:
        im = crop_ink(Image.open(png(k)).convert('RGB')); a = im.width / im.height
        w, h = cell_size(a, B); sq = Image.new('RGB', (B, B), 'white'); sq.paste(im.resize((w, h), Image.BOX), ((B - w) // 2, (B - h) // 2))
        return k, np.asarray(sq.resize((S, S), Image.BOX), np.uint8), a, w * h / B / B
    except Exception: return None
if __name__ == '__main__':
    with ThreadPoolExecutor(8) as ex: res = [r for r in ex.map(feat, keep) if r]
    meta = {k: (s, m) for k, s, m in keep}
    np.savez_compressed(f'{HERE}/tile_thumbs.npz', keys=np.array([r[0] for r in res]), T=np.array([r[1] for r in res], np.uint8),
                        aspect=np.array([r[2] for r in res], np.float32), fill=np.array([r[3] for r in res], np.float32),
                        soft=np.array([meta[r[0]][0] for r in res]), main=np.array([meta[r[0]][1] for r in res]), amin=AMIN, amax=AMAX)
    print(len(res), 'physics tiles from', len({r[0].split('__')[0] for r in res}), 'papers;', sum(r[3] > 0.999 for r in res), 'fill their cell')
