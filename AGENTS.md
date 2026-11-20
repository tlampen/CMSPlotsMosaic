# AGENTS.md — CMSPlotsMosaic

Instructions for AI coding agents working in this folder. It holds the mosaic "CMS physics in 1534 plots": the CMS
logo drawn as a 40×40 grid of plots taken from CMS papers, with a text box and a clickable PDF.
The full method is in `README.md` — read it before changing anything.

## What is here
| Path | What |
|---|---|
| `scripts/CMSPlotsMosaic.py` | matching (which plot goes where) and drawing, including the text box, logo and QR code |
| `scripts/extract.py`, `select_papers.py`, `candidates.py` | first steps: figures and captions of every paper, paper selection, caption filters |
| `scripts/render_candidates.py`, `measure_candidates.py` | 60 dpi renders of the candidate plots, and their measurements |
| `scripts/extra_candidates.py` | candidate plots of the papers outside the 1525-paper selection |
| `scripts/tile_thumbs.py` | builds the plot pool and its 16×16 thumbnails (`tile_thumbs.npz`); also holds `cell_size`, the rule for fitting a plot into a cell |
| `scripts/contact_sheets.py` | sheets of newly chosen plots for the check by eye |
| `scripts/make_small.py`, `fetch_titles.py`, `make_pdf.py` | small copy of an image; paper titles from arXiv (`titles.json`); the PDF with links and hover titles |
| `work/` | intermediate results and render caches (1.6 GB); can be rebuilt |
| `cms_sources` | symbolic link to the paper sources: one folder per paper (arXiv id). **Read-only; the only thing outside this folder.** |
| `CMSlogo.png`, `main_picks.txt`, `fonts/` | inputs: the logo, hand-made main-result picks, the text box fonts. Do not change. |
| `exclude.txt` | figures removed by eye (key  # reason) |
| `checked.txt` | plots already looked at and accepted |
| `assignment_40.json` | the result: row, column and plot of every cell, plus all settings |
| `textbox.json` | position of the QR code, written when the picture is drawn |
| `CMSPlotsMosaic*.png`, `.pdf` | the outputs |

The folder is self-contained: every script finds the folder from its own location and reads nothing outside it
except through the `cms_sources` link.

## Commands
Run in this folder, and always start Python with `-I`:
```bash
python3 -I scripts/CMSPlotsMosaic.py --tile_px 48 --out CMSPlotsMosaic.png
python3 -I scripts/CMSPlotsMosaic.py --tile_px 160 --out CMSPlotsMosaic_hires.png
python3 -I scripts/make_small.py CMSPlotsMosaic_hires.png CMSPlotsMosaic_small.png
python3 -I scripts/make_pdf.py
```
The full build order, from the paper sources on, is in `README.md`.
- Without `--reassign` the mosaic script only redraws from `assignment_40.json` (about a minute). This is enough for
  changes to the text box, frame, gaps or image size.
- Add `--reassign` only when the choice or placement of plots is meant to change (pool, weights, grid, blank
  rectangle). It takes a few minutes and may bring in plots that have not been checked — then do the check by eye.
- Draw the hi-res image last: it writes `textbox.json`, which `make_pdf.py` reads. Rebuild the PDF after every redraw.
- `python3 -I scripts/contact_sheets.py DIR` writes the sheets of unchecked plots to `DIR`.
- Scratch files go to `$TMPDIR`, not into this folder.
- Only `fetch_titles.py` needs the network (`export.arxiv.org`); it sends public arXiv ids and nothing else.

## Rules for this picture
1. **Keep `README.md` current and stand-alone.** After any change, update it:
   sizes and sha256 of the outputs, commands, method, settings, numbers, checks, known limits. It must be enough to
   rewrite the scripts from it, and must not refer to other variants or earlier versions.
2. **Never change a plot's content.** No recolouring or tinting; the picture comes only from which plot goes where.
   Scaling is allowed; nearly square plots (width/height 0.85–1.18) are drawn as exact squares, others are centred in
   their cell on white.
3. **Physics plots only.** No Feynman diagrams, sketches, detector drawings, photos, event displays, tables, stand-alone
   legends, or plots of other experiments. The caption filters catch most; the rest is found by eye.
4. **Look at every newly chosen plot.** After `--reassign`, run `contact_sheets.py`, view the sheets, add bad figures
   to `exclude.txt` (with a reason) and the others to `checked.txt`, recompute, and repeat until no unchecked plot is
   chosen.
5. **Fixed properties** (change only if the user asks): 40×40 grid; white background; no plot twice; exactly one plot
   from every paper that has a usable plot; the one exception is arXiv:1207.7235, whose two Higgs discovery plots
   (four-lepton and diphoton mass) sit side by side in a black frame; text box in the top right corner (11×6 cells, 11 wide and 6 high,
   one row of plots above and one column to the right).
   The numbers must add up: cells outside the blank rectangle = papers + 1. If the pool or the rectangle changes,
   the script stops with a message; do not fix this with duplicates.
6. **Text box wording is the user's.** Do not reword it or add credits without being asked. The date comes from
   `--date` and the QR address from `--url`.

## Conventions
- Plot key: `PAPER__FIGURE__PANEL` (figure from 1, panel from 0), e.g. `1207.7235__4__0`; an entry `PAPER__FIGURE` in
  `exclude.txt` removes all panels of that figure. Old-style arXiv ids use `_` in folder names
  (`hep-ex_0012003` = `hep-ex/0012003`).
- Rows and columns are counted from the top left: from 0 in scripts and JSON, from 1 in `README.md` and in messages.
- The target is the logo as it is (square corners; `--corner` stays 0).
- Report measured numbers (colour distance and brightness correlation against the logo; the letters and tracks checks
  the script prints) rather than impressions, and say what was not verified — for example the QR code has not been
  test-scanned and the PDF hover text has not been tried in a viewer.

## Do not
- Do not edit or delete the inputs (`cms_sources`, `CMSlogo.png`, `main_picks.txt`, `fonts/`), or anything outside this folder.
- Do not delete folders or caches without asking.
- Do not send paper lists or other project details to outside services, apart from the arXiv title lookup above.

## Software
python 3.12 with numpy, scipy, Pillow, qrcode, reportlab, pikepdf; `pdftoppm` (poppler); ImageMagick `convert` with
Ghostscript for eps/ps files.
