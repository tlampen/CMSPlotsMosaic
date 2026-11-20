"""Candidate plots of the papers that are in cms_sources/ but not in the 1521-paper selection of the logo-grid
pipeline (work/selection.txt), for the all-papers mosaic.

Two kinds of papers:
  * with figures in work/figs.json (cut only because the selection is "the newest 1521"): their figures, minus
    those whose caption matches the HARD filter of scripts/candidates.py (drawings, diagrams, photos ...)
  * where scripts/extract.py found no figure (old LaTeX with \\epsfig/\\psfig, or figures in included files):
    every image file of the paper folder (pdf, eps, ps, epsi, png, jpg), no caption; non-plots are removed by eye
    afterwards (exclude.txt)
Each candidate is rendered to extra_cand/KEY.png (pdf: pdftoppm 60 dpi; other: ImageMagick convert, at most 600 px),
and measured like scripts/measure_candidates.py does (aspect, ink, white_in).
Output: extra_cands.json (same fields as work/cands.json), extra_colours.json, extra_cand/*.png
usage (from the mosaic folder): python3 -I scripts/extra_candidates.py"""
import os, re, json, subprocess, numpy as np
from PIL import Image, ImageChops
SCR = os.path.dirname(os.path.abspath(__file__)); HERE = os.path.dirname(SCR)   # scripts/ and the mosaic folder
W = f'{HERE}/work'; SRC = f'{HERE}/cms_sources'
src = open(f'{SCR}/candidates.py').read()
exec(src[src.index('HARD = '):src.index('# panels (paper__figure__panel)')])          # HARD and SOFT caption filters
r = json.load(open(f'{W}/figs.json')); sel = {l.split()[0] for l in open(f'{W}/selection.txt')}
EXT = ('.pdf', '.eps', '.ps', '.epsi', '.png', '.jpg', '.jpeg')
SKIP = re.compile(r'logo|PoS|orcid|cc-by|by\.pdf', re.I)                              # journal logos etc.
def resolve(d, fn):
    for c in [fn] + [fn + e for e in EXT]:
        if os.path.isfile(os.path.join(SRC, d, c)): return os.path.join(d, c)
    base = os.path.basename(fn)
    for root, _, files in os.walk(os.path.join(SRC, d)):
        for c in [base] + [base + e for e in EXT]:
            if c in files: return os.path.relpath(os.path.join(root, c), SRC)
    return None
os.makedirs(f'{HERE}/extra_cand', exist_ok=True)
out = []
for d in sorted(k for k, v in r.items() if 'error' not in v and k not in sel):
    if r[d]['figs']:
        seen = set()
        for f in r[d]['figs']:
            if HARD.search(f['caption']): continue
            for k, fn in enumerate(f['files']):
                p = resolve(d, fn)
                if p and p not in seen:
                    seen.add(p); out.append({'paper': d, 'fig': f['idx'], 'panel': k, 'path': p, 'appendix': f['appendix'], 'main': False,
                                             'soft': bool(SOFT.search(f['caption'])), 'cap': f['caption'][:200]})
    else:
        files = sorted(os.path.relpath(os.path.join(root, f), SRC) for root, _, fs in os.walk(os.path.join(SRC, d), followlinks=True)
                       for f in fs if f.lower().endswith(EXT) and not SKIP.search(f))
        for i, p in enumerate(files, 1):
            out.append({'paper': d, 'fig': i, 'panel': 0, 'path': p, 'appendix': False, 'main': False, 'soft': False, 'cap': ''})
def lab(rgb):
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T / [0.95047, 1, 1.08883]
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
def measure(png):                                  # as measure() in scripts/measure_candidates.py
    im = Image.open(png).convert('RGB')
    bb = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda v: 255 if v > 20 else 0).getbbox()
    if not bb: return None
    im = im.crop(bb); w, h = im.size; k = min(232 / w, 192 / h)
    im = im.resize((max(1, int(w * k)), max(1, int(h * k))), Image.LANCZOS)
    Li = lab(np.asarray(im, float) / 255).reshape(-1, 3)
    cell = Image.new('RGB', (240, 200), 'white'); cell.paste(im, ((240 - im.width) // 2, (200 - im.height) // 2))
    L = lab(np.asarray(cell, float) / 255).reshape(-1, 3)
    return {'ink': float((L[:, 0] < 90).mean()), 'aspect': w / h, 'white_in': float(((Li[:, 0] > 95) & (np.hypot(Li[:, 1], Li[:, 2]) < 5)).mean())}
col, good = {}, []
for c in out:
    key = f"{c['paper']}__{c['fig']}__{c['panel']}"; o = f'{HERE}/extra_cand/{key}'; p = os.path.join(SRC, c['path'])
    if not os.path.exists(o + '.png'):
        if p.endswith('.pdf'): subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-singlefile', '-r', '60', '-png', p, o], capture_output=True, timeout=120)
        else: subprocess.run(['convert', p + '[0]', '-background', 'white', '-flatten', '-resize', '600x600>', o + '.png'], capture_output=True, timeout=120)
    if os.path.exists(o + '.png'):
        m = measure(o + '.png')
        if m: col[key] = m; good.append(c)
json.dump(good, open(f'{HERE}/extra_cands.json', 'w'), indent=0); json.dump(col, open(f'{HERE}/extra_colours.json', 'w'), indent=0)
from collections import Counter
print(len(good), 'extra candidates rendered:', dict(Counter(c['paper'] for c in good)))
print('papers in cms_sources with no usable image:', sorted(k for k, v in r.items() if 'error' not in v and k not in sel and k not in {c['paper'] for c in good}))
