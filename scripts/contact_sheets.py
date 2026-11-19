"""Contact sheets of the chosen plots that have not been looked at yet (for spotting figures that are not plots).
usage (from the mosaic folder): python3 -I scripts/contact_sheets.py OUTDIR
Already looked at = keys in checked.txt (one per line). Writes OUTDIR/sheet_NN.png (12 x 10 plots of 128 px, each with
a running number) and OUTDIR/new_keys.txt (number key). After looking: add bad ones to exclude.txt, the rest to
checked.txt, and run the mosaic again with --reassign; repeat until no new plot appears."""
import sys, os, json
from PIL import Image, ImageDraw
SCR = os.path.dirname(os.path.abspath(__file__)); HERE = os.path.dirname(SCR)   # scripts/ and the mosaic folder
W = f'{HERE}/work'; SRC = f'{HERE}/cms_sources'
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
seen = {l.strip() for l in open(f'{HERE}/checked.txt') if l.strip()} if os.path.exists(f'{HERE}/checked.txt') else set()
tiles = json.load(open(f'{HERE}/assignment_40.json'))['tiles']
new = sorted({t['key'] for t in tiles} - seen)
open(f'{out}/new_keys.txt', 'w').write(''.join(f'{i} {k}\n' for i, k in enumerate(new)))
C, R, S = 12, 10, 128
for s in range(0, len(new), C * R):
    sh = Image.new('RGB', (C * S, R * S), 'white'); d = ImageDraw.Draw(sh)
    for n, k in enumerate(new[s:s + C * R]):
        src = next(f for f in (f'{W}/hi/{k}.png', f'{W}/cand/{k}.png', f'{HERE}/extra_cand/{k}.png') if os.path.exists(f))
        im = Image.open(src).convert('RGB'); im.thumbnail((S - 6, S - 6), Image.LANCZOS)
        x, y = (n % C) * S, (n // C) * S; sh.paste(im, (x + 3, y + 3)); d.rectangle([x, y, x + 26, y + 11], fill='black'); d.text((x + 2, y), str(s + n), fill='yellow')
    sh.save(f'{out}/sheet_{s // (C * R):02d}.png')
print(len(tiles), 'tiles,', len(new), 'not looked at before,', (len(new) + C * R - 1) // (C * R), 'sheets')
