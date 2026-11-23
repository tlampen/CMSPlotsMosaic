"""Vector-graphics PDF of the mosaic (optional; not made by the default build).

usage (from the mosaic folder): python3 -I scripts/make_vector_pdf.py [--out CMSPlotsMosaic_vector.pdf] [--dpi 150]
Reads assignment_40.json, titles.json, textbox.json (written by CMSPlotsMosaic.py when it draws the hi-res image)
and the plots' source files; writes one square page of 40 x 40 cm, laid out exactly like CMSPlotsMosaic_hires.png:
  * plots with a PDF source: the source's first page, embedded as a form XObject (vector, fonts as in the source),
    clipped to its ink box and scaled into its cell by the same rule as the PNG (tile_thumbs.cell_size, unrounded)
  * EPS / PS sources: converted to PDF with Ghostscript (pdfwrite, -dEPSCrop; a plain PS file with a %%BoundingBox
    gets that box as its page), then as above
  * bitmap sources (png, jpg): the full-size image, cropped to its ink, embedded losslessly
  * ink box: the first page rendered with pdftoppm at --dpi (media box, page rotation applied, as in the pipeline),
    bounding box of pixels differing from white by more than 20 of 255; cached in work/vector_cache/
  * black frame of the forced pair, text box (line, text in embedded DejaVu fonts, QR code as vector squares, CMS logo
    as the original 1024 px image), all at the positions recorded in textbox.json
  * links and hover titles of every cell and the QR-code link, as in CMSPlotsMosaic.pdf (make_pdf.add_links)
No plot content is changed: plots are only placed, scaled and clipped."""
import os, sys, io, json, argparse, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageChops, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import pikepdf
from pikepdf import Name, Array
Image.MAX_IMAGE_PIXELS = None
SCR = os.path.dirname(os.path.abspath(__file__)); HERE = os.path.dirname(SCR)   # scripts/ and the mosaic folder
W = f'{HERE}/work'; SRC = f'{HERE}/cms_sources'; VC = f'{W}/vector_cache'
sys.path.insert(0, SCR)
from tile_thumbs import AMIN, AMAX
from make_pdf import add_links
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=f'{HERE}/CMSPlotsMosaic_vector.pdf')
ap.add_argument('--dpi', type=int, default=150, help='resolution of the renders used to find the ink box of each plot')
A = ap.parse_args()
os.makedirs(VC, exist_ok=True)

j = json.load(open(f'{HERE}/assignment_40.json')); N = j['params']['n']; tiles = j['tiles']
titles = json.load(open(f'{HERE}/titles.json')); tb = json.load(open(f'{HERE}/textbox.json'))
SIZE, U, G, FW = tb['size'], tb['u'], tb['gap'], tb['frame']     # hi-res picture: pixels, cell, gap, frame width
S = 40 / 2.54 * 72; F = S / SIZE                                   # page side in points; points per hi-res pixel
INDEX = {f"{c['paper']}__{c['fig']}__{c['panel']}": c['path'] for c in json.load(open(f'{W}/cands.json'))}
INDEX.update({f"{c['paper']}__{c['fig']}__{c['panel']}": c['path'] for c in json.load(open(f'{HERE}/extra_cands.json'))})
VECTOR = ('.pdf',); PS = ('.eps', '.ps', '.epsi')

def ink_bbox(im):
    return ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda v: 255 if v > 20 else 0).getbbox()

def prepare(key):
    """source description of one plot: {'kind': 'pdf', 'pdf': path, 'box': ink box in points of the rendered page}
    or {'kind': 'image', 'png': path of the ink-cropped bitmap}; cached as work/vector_cache/KEY.json"""
    cj = f'{VC}/{key}.json'
    if os.path.exists(cj): return json.load(open(cj))
    p = os.path.join(SRC, INDEX[key]); ext = os.path.splitext(p)[1].lower()
    if ext in VECTOR or ext in PS:
        if ext in PS:                                              # eps / ps -> pdf, still vector
            pdf = f'{VC}/{key}.pdf'
            subprocess.run(['gs', '-q', '-dSAFER', '-dNOPAUSE', '-dBATCH', '-dEPSCrop', '-sDEVICE=pdfwrite', f'-sOutputFile={pdf}', p],
                           capture_output=True, timeout=120, check=True)
            head = open(p, 'rb').read(4000).decode('latin1').splitlines()
            bbl = [l.split(':')[1].split() for l in head if l.startswith('%%BoundingBox:') and 'atend' not in l]
            if 'EPSF' not in head[0] and bbl:                      # plain PS with a bounding box: gs ignores -dEPSCrop, so
                with pikepdf.open(pdf, allow_overwriting_input=True) as d:   # crop the page to the box (as ImageMagick does)
                    d.pages[0].MediaBox = Array([float(v) for v in bbl[0]]); d.save(pdf)
        else: pdf = p
        with tempfile.TemporaryDirectory(dir=VC) as td:
            subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-singlefile', '-r', str(A.dpi), '-png', pdf, f'{td}/r'], capture_output=True, timeout=300, check=True)
            im = Image.open(f'{td}/r.png').convert('RGB'); bb = ink_bbox(im) or (0, 0, im.width, im.height)
        k = 72 / A.dpi; d = {'kind': 'pdf', 'pdf': os.path.relpath(pdf, HERE), 'box': [v * k for v in bb]}
    else:                                                          # bitmap: full size, cropped to its ink
        im = Image.open(p); im = im.convert('RGBA') if im.mode in ('RGBA', 'LA', 'P') else im.convert('RGB')
        if im.mode == 'RGBA': bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg.convert('RGB')
        bb = ink_bbox(im); im = im.crop(bb) if bb else im
        out = f'{VC}/{key}.png'; im.save(out); d = {'kind': 'image', 'png': os.path.relpath(out, HERE)}
    json.dump(d, open(cj, 'w')); return d

with ThreadPoolExecutor(8) as ex: SRCS = list(ex.map(lambda t: prepare(t['key']), tiles))

def place(t, aspect):
    """rectangle of a plot in page points (x, y from the bottom left, w, h): the PNG's rule, without rounding"""
    sd = U - G - (2 * FW if t.get('forced') else 0); o = (U - sd) / 2
    e = aspect / AMAX if aspect > AMAX else aspect / AMIN if aspect < AMIN else 1.0
    w, h = (sd, sd / e) if e >= 1 else (sd * e, sd)
    px, py = t['c'] * U + o + (sd - w) / 2, t['r'] * U + o + (sd - h) / 2
    return px * F, S - (py + h) * F, w * F, h * F

# ---- page with everything that is not a PDF plot (reportlab), then the PDF plots as form XObjects (pikepdf)
buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(S, S), pageCompression=1)
c.setTitle(f'CMS physics in {len(tiles)} plots'); c.setAuthor('Plots: CMS Collaboration')
c.setSubject('Mosaic of the CMS logo (vector graphics); click a plot to open its paper on arXiv, hover to see its title')
for t, s in zip(tiles, SRCS):
    if s['kind'] == 'image':
        im = Image.open(f"{HERE}/{s['png']}"); x, y, w, h = place(t, im.width / im.height)
        c.drawImage(ImageReader(im), x, y, w, h)
ft = [t for t in tiles if t.get('forced')]
def frame(x0, y0, x1, y1, th):                                   # PIL outline of width th inside [x0, x1) x [y0, y1), pixels
    c.setLineWidth(th * F); c.setStrokeColorRGB(0, 0, 0); c.setLineJoin(0)
    c.rect((x0 + th / 2) * F, S - (y1 - th / 2) * F, (x1 - x0 - th) * F, (y1 - y0 - th) * F, stroke=1, fill=0)
if ft: frame(min(t['c'] for t in ft) * U, min(t['r'] for t in ft) * U, (max(t['c'] for t in ft) + 1) * U, (max(t['r'] for t in ft) + 1) * U, FW)
frame(*tb['border'])
for name in {t_[2] for t_ in tb['text']}: pdfmetrics.registerFont(TTFont(name[:-4], f'{HERE}/fonts/{name}'))
for x, y, name, size, fill, text in tb['text']:                   # PIL draws from the ascender line; PDF from the baseline
    asc = ImageFont.truetype(f'{HERE}/fonts/{name}', size).getmetrics()[0]
    c.setFont(name[:-4], size * F); c.setFillColorRGB(*(v / 255 for v in fill)); c.drawString(x * F, S - (y + asc) * F, text)
q = tb['qr']; k = q['module']; path = c.beginPath()                # QR code: one filled path of runs of dark modules
for r, row in enumerate(q['rows']):
    cc = 0
    while cc < len(row):
        if row[cc] == '1':
            e = cc
            while e < len(row) and row[e] == '1': e += 1
            path.rect((q['x'] + cc * k) * F, S - (q['y'] + (r + 1) * k) * F, (e - cc) * k * F, k * F); cc = e
        else: cc += 1
c.setFillColorRGB(0, 0, 0); c.drawPath(path, stroke=0, fill=1)
lg = Image.open(f'{HERE}/CMSlogo.png').convert('RGBA'); bg = Image.new('RGBA', lg.size, 'white'); bg.alpha_composite(lg)
lx, ly, ls = tb['logo']; c.drawImage(ImageReader(bg.convert('RGB')), lx * F, S - (ly + ls) * F, ls * F, ls * F)
c.showPage(); c.save(); buf.seek(0)

pdf = pikepdf.open(buf); page = pdf.pages[0]; xo = page.Resources.get('/XObject') or pikepdf.Dictionary()
ops, srcdocs, nvec = [], [], 0
for n, (t, s) in enumerate(zip(tiles, SRCS)):
    if s['kind'] != 'pdf': continue
    src = pikepdf.open(io.BytesIO(open(f"{HERE}/{s['pdf']}", 'rb').read())); srcdocs.append(src)   # kept open until saved
    sp = src.pages[0]; mb = [float(v) for v in sp.mediabox]; X0, X1 = sorted(mb[0::2]); Y0, Y1 = sorted(mb[1::2])
    rot = int(sp.obj.get('/Rotate', 0)) % 360
    form = sp.as_form_xobject(False); form.BBox = Array([X0, Y0, X1, Y1])
    # page space (x, y) -> rendered page (right, down) in points, as pdftoppm shows the media box with /Rotate applied:
    # right = a1 x + b1 y + c1, down = a2 x + b2 y + c2
    a1, b1, c1, a2, b2, c2 = {0: (1, 0, -X0, 0, -1, Y1), 90: (0, 1, -Y0, 1, 0, -X0),
                              180: (-1, 0, X1, 0, 1, -Y0), 270: (0, -1, Y1, -1, 0, X1)}[rot]
    bx0, by0, bx1, by1 = s['box']; x, y, w, h = place(t, (bx1 - bx0) / (by1 - by0))
    sx, sy = w / (bx1 - bx0), h / (by1 - by0)
    m = (sx * a1, -sy * a2, sx * b1, -sy * b2, x + sx * (c1 - bx0), y + h - sy * (c2 - by0))
    nm = f'/P{n}'; xo[Name(nm)] = pdf.copy_foreign(form); nvec += 1
    ops.append(f'q {x:.4f} {y:.4f} {w:.4f} {h:.4f} re W n ' + ' '.join(f'{v:.6f}' for v in m) + f' cm {nm} Do Q')
page.Resources.XObject = xo
page.contents_add(pikepdf.Stream(pdf, ('\n'.join(ops) + '\n').encode()), prepend=True)
add_links(pdf, page, S, N, tiles, titles, tb)
pdf.save(A.out, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
print('wrote', A.out, os.path.getsize(A.out) // 1024, 'KB;', nvec, 'plots as vector graphics,', len(tiles) - nvec, 'as bitmaps;',
      sum(1 for t in tiles if t['key'].split('__')[0] not in titles), 'without title')
