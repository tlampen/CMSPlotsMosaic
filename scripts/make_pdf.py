"""Clickable PDF of the mosaic: clicking a plot opens its paper on arXiv; hovering shows the paper's title.

usage (from the mosaic folder): python3 -I scripts/make_pdf.py [quality=88]
Reads CMSPlotsMosaic_hires.png, assignment_40.json, titles.json (fetch_titles.py) and textbox.json
(written by CMSPlotsMosaic.py); writes CMSPlotsMosaic.pdf:
  * one square page of 40 x 40 cm with the picture as a JPEG (reportlab)
  * for every cell, covering the whole cell (added with pikepdf):
      - a link annotation to https://arxiv.org/abs/ID with the title as its /Contents
      - on top of it an invisible push-button field with the same web action and the title as its tooltip (/TU);
        this is what Acrobat, Chrome and Firefox show when the mouse rests on a plot
    ID = the paper's folder name in cms_sources/; old-style folders hep-ex_0012003 -> hep-ex/0012003
  * a link on the QR code to its address"""
import os, sys, json, io
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pikepdf
from pikepdf import Dictionary, Name, Array, String
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); Q = int(sys.argv[1]) if len(sys.argv) > 1 else 88
j = json.load(open(f'{HERE}/assignment_40.json')); N = j['params']['n']; tiles = j['tiles']
titles = json.load(open(f'{HERE}/titles.json')); tb = json.load(open(f'{HERE}/textbox.json'))
buf = io.BytesIO(); Image.open(f'{HERE}/CMSPlotsMosaic_hires.png').convert('RGB').save(buf, 'JPEG', quality=Q, subsampling=0); buf.seek(0)
S = 40 / 2.54 * 72; u = S / N                                   # page side and cell size in points
out = f'{HERE}/CMSPlotsMosaic.pdf'; tmp = io.BytesIO()
c = canvas.Canvas(tmp, pagesize=(S, S)); c.setTitle(f'CMS physics in {len(tiles)} plots'); c.setAuthor('Plots: CMS Collaboration')
c.setSubject('Mosaic of the CMS logo; click a plot to open its paper on arXiv, hover to see its title')
c.drawImage(ImageReader(buf), 0, 0, S, S); c.save(); tmp.seek(0)
pdf = pikepdf.open(tmp); page = pdf.pages[0]; annots, fields = [], []
def uri(url): return Dictionary(S=Name.URI, URI=String(url))
def link(rect, url, text):
    return pdf.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=Array(rect), Border=Array([0, 0, 0]), A=uri(url), Contents=String(text)))
for n, t in enumerate(tiles):
    folder = t['key'].split('__')[0]; aid = folder.replace('_', '/'); url = f'https://arxiv.org/abs/{aid}'
    text = f"{titles.get(folder, '')} (arXiv:{aid})".strip()
    x, y = t['c'] * u, S - (t['r'] + 1) * u; rect = [round(v, 2) for v in (x, y, x + u, y + u)]   # PDF origin is bottom left
    annots.append(link(rect, url, text))
    w = pdf.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Widget, FT=Name.Btn, Ff=65536, T=String(f'plot{n}'), TU=String(text),
                                     Rect=Array(rect), F=0, P=page.obj, A=uri(url), MK=Dictionary(), Border=Array([0, 0, 0])))
    annots.append(w); fields.append(w)
q = tb['qr_box']; annots.append(link([round(v, 2) for v in (q[0] * S, S - q[3] * S, q[2] * S, S - q[1] * S)], tb['url'], tb['url']))
page.Annots = Array(annots); pdf.Root.AcroForm = Dictionary(Fields=Array(fields))
pdf.save(out); print('wrote', out, os.path.getsize(out) // 1024, 'KB,', len(tiles), 'plots with link and hover text;', sum(1 for t in tiles if t['key'].split('__')[0] not in titles), 'without title')
