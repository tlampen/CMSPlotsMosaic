"""Render every candidate plot of work/cands.json at 60 dpi into work/cand/KEY.png (existing files are kept).
usage (from the mosaic folder): python3 -I scripts/render_candidates.py
PDF files: pdftoppm -f 1 -l 1 -singlefile -r 60 -png; other files: ImageMagick convert FILE[0] -background white
-flatten -resize 600x600> . Runs 8 at a time; a file that takes more than 60 s is skipped."""
import os, json, subprocess
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = f'{HERE}/work'; SRC = f'{HERE}/cms_sources'
os.makedirs(f'{W}/cand', exist_ok=True)
def render(c):
    o = f"{W}/cand/{c['paper']}__{c['fig']}__{c['panel']}"; p = os.path.join(SRC, c['path'])
    if os.path.exists(o + '.png'): return 0
    try:
        if p.endswith('.pdf'): subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-singlefile', '-r', '60', '-png', p, o], capture_output=True, timeout=60)
        else: subprocess.run(['convert', p + '[0]', '-background', 'white', '-flatten', '-resize', '600x600>', o + '.png'], capture_output=True, timeout=60)
    except subprocess.TimeoutExpired: pass
    return 1
cands = json.load(open(f'{W}/cands.json'))
with ThreadPoolExecutor(8) as ex: n = sum(ex.map(render, cands))
print(len(cands), 'candidates,', n, 'rendered now,', sum(not os.path.exists(f"{W}/cand/{c['paper']}__{c['fig']}__{c['panel']}.png") for c in cands), 'without a render')
