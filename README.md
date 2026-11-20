# CMSPlotsMosaic
Tools to create a mosaic poster mimicking the CMS logo from the plots in CMS publications

**What it is:** the CMS logo (`CMSlogo.png`) drawn as a 40×40 grid of same-size square cells on a white background.
Every cell holds a different plot taken from a CMS paper; no plot is recoloured or tinted — the picture comes only
from which plot is put where.

- 1534 plots from 1533 papers: one plot per paper, except arXiv:1207.7235 (observation of the Higgs boson), which
  gives two plots (four-lepton mass and diphoton mass), side by side inside a black frame at row 36, columns 13–14
  (rows and columns counted from the top left, from 1).
- A blank rectangle of 11×6 cells (11 columns, 6 rows) in the top right corner (rows 2–7, columns 29–39; one row of plots above it, one
  column to its right) holds a text box with a line around it, the CMS logo and a QR code.
- The cells of the letters "CMS" and of the red particle tracks count more in the matching.
- A PDF version: clicking a plot opens its paper on arXiv; hovering shows the paper's title.

Why 1534 cells: 40×40 = 1600 cells, 1533 papers, and the Higgs discovery paper gives two plots, so 1534 cells are
needed; 1600 − 1534 = 66 = 11 × 6, the blank rectangle. (The only other rectangles, 6 wide × 11 high or 1 × 66 / 2 × 33 / 3 × 22,
do not suit a text box.)

Built 2026-11-20 by Claude Code (model Opus 5.5), with the scripts written earlier by Claude Code (model Fable 5.2).

| File | What | Size | sha256 |
|---|---|---|---|
| `CMSPlotsMosaic_hires.png` | 6400×6400 (160 px per cell) | 32810 KB | `bab2cc6f440154d0…` |
| `CMSPlotsMosaic.png` | 1920×1920 (48 px per cell) | 4531 KB | `ab9fedf82ae9eb5d…` |
| `CMSPlotsMosaic_small.png` | 1400×1400, 256 colours, under 1 MB | 899 KB | `76b2e284dec5866c…` |
| `CMSPlotsMosaic.pdf` | clickable PDF with hover titles, one page 40×40 cm | 20572 KB | `aa156532c86fbd55…` |
| `assignment_40.json` | row, column, plot of every cell; all settings | 73 KB | `0bcdb5e8ba453793…` |
| `tile_thumbs.npz` | 16×16 thumbnails of the 31,184 pool plots | 9034 KB | `7e8599de4fba05f2…` |
| `titles.json` | paper titles from the arXiv API | 205 KB | `89355daff2b13b2a…` |

Everything needed is inside this folder:
- `scripts/` — all scripts: `extract.py`, `select_papers.py`, `candidates.py`, `render_candidates.py`,
  `measure_candidates.py`, `extra_candidates.py`, `tile_thumbs.py`, `CMSPlotsMosaic.py`, `contact_sheets.py`,
  `make_small.py`, `fetch_titles.py`, `make_pdf.py`. Each finds the folder from its own location.
- `work/` — intermediate results: `figs.json`, `selection.txt`, `cands.json`, `candcolours.json`, `cand/` (60 dpi
  renders), `render_cache/`, and optionally `hi/` (130 dpi renders, see step 4; not present for this build). All can be rebuilt.
- data: `main_picks.txt`, `exclude.txt` (179 figures removed by eye), `checked.txt` (5295 plots looked at),
  `extra_cands.json`, `extra_colours.json`, `extra_cand/`, `textbox.json` (position of the QR code), `fonts/`.

## Getting the papers (`fetch_CMSPapers_inspire.py` → `cms_papers.json`, `cms_sources/`, `cms_pdfs/` )
This step comes before everything below: it makes the list of CMS papers and downloads their sources to directory cms_sources. 
- The script asks INSPIRE (`https://inspirehep.net/api/literature`) for the published CMS papers in hep-ex: query
  `report_numbers.value:CMS-* and arxiv_eprints.categories:hep-ex and tc published`, newest first, 250 per page,
  fields titles, abstracts, arXiv ids, DOIs and report numbers.
- `cms_papers.json` — the result: a list with one INSPIRE record per paper (`id` and `metadata`), newest first
  (1539 papers on 2026-11-19, 6.5 MB). It is the script's own record of what is already known; the mosaic scripts do
  not read it — they work from the folders in `cms_sources`.
- By default only papers not yet in `cms_papers.json` are fetched (fetching stops at the first page with nothing new)
  and are put at the front of the list; `--full` fetches all papers again.
- `--download pdf|src|both` downloads the files of the newly found papers from arXiv: PDFs to `cms_pdfs/ID.pdf`,
  LaTeX sources to `cms_sources/ID/` (the archive is unpacked and then deleted). Without the option the script asks
  when new papers are found. `--all-missing` also fills in files missing for papers already in the list.
  In file and folder names `/` in old-style ids becomes `_`. There are 4 seconds between arXiv downloads; failures
  are listed in `cms_download_failed.txt`. Papers with no LaTeX source on arXiv (PDF only) get no source folder.
- Run in this folder (the paths are relative to where it is run); needs the network and the python package `requests`:
```bash
python3 fetch_CMSPapers_inspire.py --download src                 # new papers and their sources
python3 fetch_CMSPapers_inspire.py --download src --all-missing   # also sources missing for known papers
```
The mosaic needs only the sources (`src`), not the PDFs. After new papers arrive, the build below has to be run
again from step 1, and the grid and blank rectangle may need to change (cells outside the rectangle = papers + 1).

## Inputs
- `cms_sources` — a folder with the paper sources created by the fetch script : one folder per paper (1534 folders), named
  by arXiv id (`1207.7235`; old style `hep-ex_0012003`), holding the paper's LaTeX source and figure files as
  downloaded from arXiv.
- `CMSlogo.png` — 1024×1024 RGBA; square, 8 px black outline, light-blue / yellow / green areas, red particle
  tracks, navy letters "CMS", white top right part.
- `main_picks.txt` — hand-made list of main-result panels of 145 papers (lines `id figure panel`), used in step 2.
- `fonts/DejaVuSans.ttf`, `fonts/DejaVuSans-Bold.ttf` — fonts of the text box.
- Key of a plot everywhere: `PAPER__FIGURE__PANEL` (figure number from 1, panel from 0), e.g. `1207.7235__4__0`.

## Build commands (run in this folder)
```bash
python3 -I scripts/extract.py                # step 1  -> work/figs.json
python3 -I scripts/select_papers.py          # step 2  -> work/selection.txt
python3 -I scripts/candidates.py             # step 3  -> work/cands.json
python3 -I scripts/render_candidates.py      # step 4  -> work/cand/*.png (about an hour if none exist)
python3 -I scripts/measure_candidates.py     # step 4  -> work/candcolours.json
python3 -I scripts/extra_candidates.py       # step 5
python3 -I scripts/tile_thumbs.py            # step 6, about 3 min
python3 -I scripts/CMSPlotsMosaic.py --reassign --tile_px 160 --out CMSPlotsMosaic_hires.png   # steps 7-12, about 3 min
python3 -I scripts/contact_sheets.py SOMEDIR # step 13; repeat the line above until nothing new
python3 -I scripts/CMSPlotsMosaic.py --tile_px 48 --out CMSPlotsMosaic.png
python3 -I scripts/CMSPlotsMosaic.py --tile_px 160 --out CMSPlotsMosaic_hires.png   # last, so textbox.json fits the hi-res image
python3 -I scripts/make_small.py CMSPlotsMosaic_hires.png CMSPlotsMosaic_small.png
python3 -I scripts/fetch_titles.py           # step 14 (needs network: export.arxiv.org)
python3 -I scripts/make_pdf.py               # step 15
```
Without `--reassign` the mosaic script reuses `assignment_40.json` and only draws. Drawing needs only steps 1–3 (`work/cands.json`) and the 60 dpi renders of the 1534 chosen plots (in `work/cand/`, or `extra_cand/` for the papers of step 5), made with the commands of step 4; it does not need `candcolours.json` or `tile_thumbs.npz` (`tile_thumbs.py` builds the pool only when run as a script, so `cell_size` can be imported). Steps 1–3 must see exactly the 1534 paper folders of this build: newer folders in `cms_sources` change the 1525-paper selection, so pass a folder of links to the 1534 folders as `extract.py SRC work/figs.json` and `candidates.py work SRC`. All settings are the script's
defaults and are stored in `assignment_40.json` → `params`. The improvement step uses numpy's `default_rng(1)`.
Built on 2026-11-20 by running every step in this folder from the paper sources. Running the assignment a second time
(`--reassign`) reproduces `assignment_40.json` exactly. The other steps were run once.

# Part 1 — which plots can be used (the pool)

## 1. Figures and captions of every paper (`scripts/extract.py` → `work/figs.json`)
For each folder: the main LaTeX file is the `*.tex` in the folder's top level that contains `\begin{document}`; if
several, prefer one with figures, then one with `_temp` in its name, then the longest. Comments (`%…`) are removed and
`\input{}` / `\include{}` are expanded (up to 5 levels). Every `\begin{figure}…\end{figure}` (also `figure*`) gives
one figure: the list of its `\includegraphics` file names (= its panels, in order) and its `\caption` text
(brace-matched, white space collapsed). Figures without `\includegraphics` are skipped. A figure is marked
"appendix" if it comes after `\appendix`, `\begin{acknowledgments}` or `\bibliography{`. Each figure also gets a
"main result" score from caption words (limits, measurements, comparisons with theory count up; diagrams, efficiencies,
control regions count down; later figures get up to +2; appendix −4); the score is only used to name a paper's
main-result figure, which matters here only for the fallback in step 3.

## 2. Paper selection (`scripts/select_papers.py` → `work/selection.txt`)
The 1525 newest papers (by arXiv number) among those where step 1 found at least one figure. For each, its main-result
panel: from the hand-made list `main_picks.txt` (lines `id figure panel`), otherwise the figure with the
highest score, panel 0 (marked `auto`). The remaining papers of `cms_sources/` are added in step 5.

## 3. Caption filter (`scripts/candidates.py` → `work/cands.json`)
Every panel of every figure of the selected papers is a candidate, unless
- its caption matches **HARD** (not a plot of a physics quantity; case-insensitive regular expression):

  `feynman|diagram|schematic|sketch|layout|architecture|flowchart|flow chart|event display|photograph|\bphoto|picture|workflow|cross-sectional view|network structure|structural representation|service setup|firmware|location relative|tracker map|pictorial|binning scheme|displays? of|scheme of|conceptual design|event topology|simplified model for`

  (exception: a hand-picked main-result panel is kept even then);
- or it is in the script's list `BLACK` (67 figures or panels found by eye in earlier work: photos, drawings, Feynman
  diagrams, sketches, a legend);
- or its file cannot be found (name as given, or with `.pdf` / `.png` / `.jpg` added, or by base name anywhere below
  the paper folder), or the same file was already taken for this paper.

If nothing of a paper survives, its main-result panel is used. A candidate is marked **soft** (border case: kept, but
with a penalty in the matching) if its caption matches **SOFT**:

  `illustrat|definition of|visuali[sz]ation|structure of the|confusion matri|correlation matri|migration matri|response matri|covariance matri|\bloss\b|training|learning rate|runtime|\bepoch|roc curve|rejection rate versus|impacts? of (the )?nuisance|pulls?\b|overview of|representation of|example of the correction procedure|binning|fraction of the total signal|signal composition|correlations between|sources of uncertaint|\bz score|false positive|true positive|correlation factors|correlation coefficient|probability matri|signal regions defined|sources of systematic|\bimpacts?\b|nuisance parameter|time taken|production modes|benchmark .*models|categori[sz]ation|custom function|transfer function|eigenvalue|eigenvector|breakdown|impact of (the )?systematic|correlations? of the|sigmoid|event yields|yields in (each|the)|discriminant|\bscores?\b|classifier|\bdnn\b|\bbdt\b|\bpnn\b|\bnn output|output node|\bauc\b|systematic uncertainties related|breakdown of (the )?systematic|relative (systematic )?uncertaint(y|ies) (as|in)`

Stored per candidate: paper, figure, panel, file path, appendix flag, main flag, soft flag, caption (200 characters).
Result: 31,217 panels from 1525 papers.

## 4. Rendering and measuring the candidates (`scripts/render_candidates.py`, `scripts/measure_candidates.py`)
Each candidate is rendered to `work/cand/KEY.png`: PDF files with `pdftoppm -f 1 -l 1 -singlefile -r 60 -png`,
other files with ImageMagick `convert FILE[0] -background white -flatten -resize 600x600\>`. Each render is measured
(results in `work/candcolours.json`): crop to the bounding box of
non-white pixels (difference from white > 20 of 255); **aspect** = width/height of the crop; scale the crop to fit
232×192 (LANCZOS) and convert to CIE Lab (sRGB, D65); **white_in** = share of its pixels with L > 95 and chroma < 5;
paste it centred on a white 240×200 canvas; **ink** = share of canvas pixels with L < 90.
Optional sharper renders `work/hi/KEY.png` (`pdftoppm -f 1 -l 1 -singlefile -r 130 -png`; no script here makes them,
and this build has none) are used for drawing when present. Without them the drawing step renders what it
needs itself (step 11), with the same result up to resampling.

## 5. Papers outside the selection (`extra_candidates.py` → `extra_cands.json`, `extra_colours.json`, `extra_cand/`)
For the 9 folders not in `selection.txt`:
- if step 1 found figures (2 papers, the oldest: `hep-ex_0012003`, `hep-ph_9806366`): all panels whose caption does not
  match HARD (file lookup as in step 3, also trying `.eps`, `.ps`, `.epsi`, `.jpeg`); soft flag from SOFT;
- if step 1 found none (old `\epsfig` LaTeX, or figures in sub-files; 6 papers): every image file below the folder
  (`.pdf .eps .ps .epsi .png .jpg .jpeg`; names matching `logo|PoS|orcid|cc-by|by.pdf` skipped), sorted by path,
  numbered as figures 1, 2, … with panel 0, no caption;
- `2003.07868` has no image file and so no plot: **it is the only paper not in the mosaic**.

Rendered as in step 4 (into `extra_cand/`) and measured the same way. 296 candidates from 8 papers; all were looked at
and the non-plots put into `exclude.txt`.

## 6. Pool and thumbnails (`tile_thumbs.py` → `tile_thumbs.npz`)
Pool = candidates of steps 3 and 5 with 0.4 < aspect < 3.0, ink > 0.03 (drops near-empty panels and legend strips) and
white_in > 0.05 (drops photos). For a paper with no plot inside the aspect limits the upper limit is 3.5 (one paper,
`2005.14219`, whose plots are about 3:1). Result: 31,184 plots from 1533 papers.

How a plot is put into a square cell of side s (function `cell_size`, used for the thumbnails and for drawing): with
a = aspect, AMIN = 0.85, AMAX = 1.18: if AMIN ≤ a ≤ AMAX the plot is drawn as an exact s×s square (shape change at most
17 %); if a > AMAX it is drawn s wide and s·AMAX/a high; if a < AMIN it is drawn s high and s·a/AMIN wide; centred on
white. **fill** = drawn area / s².

Thumbnail: the 60 dpi render is cropped to its ink, drawn this way on a white 64×64 square (BOX filter), and shrunk
to 16×16 RGB (BOX). Stored: keys, thumbnails `T`, aspect, fill, soft, main.

## 7. Final pool rules (start of `scripts/CMSPlotsMosaic.py`)
- Remove every plot listed in `exclude.txt` (an entry `PAPER__FIGURE` removes all its panels).
- Use only plots with fill = 1 (nearly square); papers that have no such plot keep all their plots (259 papers).
- The paper of the forced pair (`--force 1207.7235__3__0,1207.7235__4__0`) keeps only those two plots; the second one
  is treated as a paper of its own, so that "one plot per paper" gives exactly the two.
- Result: 22,170 plots, 1534 "papers" (1533 real ones).

# Part 2 — which plot goes where

## 8. Target (`CMSPlotsMosaic.py`)
`CMSlogo.png` composited on white, reduced (BOX) to 640×640 = 16×16 patches per cell and converted to CIE Lab; no
lightness or colour remapping. (The script has an option `--corner R` that rounds the target's corners with radius R
cells; it is off, R = 0.)
Cells: all 40×40 except the blank rectangle (`--blank 1,28,6,11` = first row, first column, rows, columns, from 0).

Cell classes, measured on the 640×640 target:
- **edge cell**: rms over the cell's patches of the Lab distance to the cell mean (a*, b* ×2 in the squares) > 12
  (`--edge_thr`) — 656 cells;
- **letter cell**: more than 4 % navy pixels (R < 70, G < 70, B > 90), only in the left 80 % of the picture (leaves out
  the small vertical text) — 105 cells;
- **track cell**: more than 3 % red pixels (R > 200, G < 100, B < 70) — 238 cells.

## 9. Cost of plot j in cell i
Plot thumbnails and target cells are averaged to k×k patches for k = 16, 8, 4, 2, 1 (Lab). With
d_k = mean over the k×k patches of [ΔL² + 2·Δa² + 2·Δb²] (`--w_ab 2`):

    tile(i,j) = W_i · Σ_k s_k · d_k  +  400·soft_j  +  1500·(1 − fill_j)

- scale weights s_16…s_1: flat cells 0 / 0.15 / 0.25 / 0.30 / 0.30 (`--scales`); edge cells 0.20 / 0.25 / 0.25 / 0.15 /
  0.15 (`--scales_edge`) — on a border the position of the border inside the cell counts more;
- cell weight W_i = 1 + 4·letter + 3·track (`--w_letter`, `--w_track`);
- `--soft_pen 400`, `--fill_pen 1500`.

**Blurred-picture term** (what the eye sees from a distance; lets neighbours compensate each other): on the 2×2 patch
grid (2 pixels per cell, 80×80 for the picture) with residual r = √w·(plot − target) per Lab channel
(w = 1, 2, 2), zero in the blank rectangle:

    blur = (1/4) · Σ_channels ‖ G ∗ r ‖²,   G = Gaussian, σ = 0.75 cell (`--sigma`), weight `--w_blur 1`

computed as (1/4)·Σ r·(G∗G∗r); G∗G is a Gaussian of σ√2, kernel cut at 3σ√2.

## 10. Assignment
1. **Forced pair:** D0(i,j) = tile(i,j) + blur energy of plot j alone in cell i. Over all horizontally adjacent cell
   pairs and both orders, take the placement with the smallest D0 sum for the two forced plots. Those two cells accept
   nothing else and the two plots go nowhere else (other costs set to 10⁹); the cells are frozen.
2. **Optimal assignment:** matrix best(i,p) = min over the plots j of paper p of D0(i,j), 1534×1534; Hungarian
   algorithm (`scipy.optimize.linear_sum_assignment`). Each cell then takes its paper's best plot for that cell.
3. **Improvement** (up to 12 sweeps over the cells in random order, `default_rng(1)`; stops when fewer than 0.2 % of
   the cells change in a sweep). For cell i with plot j₀ the change of the total cost (tile + blur with the current
   neighbours) is computed exactly: for a change d of the cell's 2×2 residual, Δblur = (1/4)·[2·⟨d, G∗G∗r⟩ + dᵀK d] with
   K the 4×4 block of G∗G. Moves: (A) another plot of the same paper; (C) swap the plots of cell i and another cell —
   the 12 most promising partners (`--partners`) are evaluated exactly (move in i, then move in the partner with the
   updated residual). The better of A and C is made if it lowers the cost.

Result here: tile term 5474.5 → 5483.1, blur term 975.5 → 946.8 per cell (total 6450.0 → 6429.9).
The script asserts that every paper appears exactly once and no plot twice.

Settings tried for the letter / track weights (40×40, thumbnail preview; "letters" = brightness correlation with the
logo in the box around the letters, "tracks" = correlation of redness R − (G+B)/2 over the track cells, both at
4 px per cell): weights 2 / 0 → letters 0.637, tracks 0.529; **4 / 3 (chosen) → 0.635, 0.577**; 8 / 6 → 0.625, 0.582
(tried with `--corner 4` on the 1530-plot pool; this build, without it, gives 0.638 and 0.576).
With one plot per paper the choice is limited, so the gains are small.

# Part 3 — drawing

## 11. Tiles
White canvas of 40·u pixels (u = `--tile_px`). Gap between cells 4 % of u (`--gap`); plot side s = u − gap. Source
image of a plot: the 60 dpi render, or the 130 dpi one if the first is smaller than 90 % of the needed size; if still
too small and the source is a PDF, it is rendered at the needed resolution (130–400 dpi, cached in
`work/render_cache/`); bitmaps are used at full size (eps/ps at 300 dpi). Cropped to its ink, resized (LANCZOS)
by the rule of step 6, pasted centred in the cell.
The forced pair: its plots are made smaller by 2×10 % of u and a black frame 10 % of u wide (`--frame`) is drawn
around the two cells, inside them.

## 12. Text box (in the blank rectangle; all sizes relative to u; fonts DejaVu Sans)
- A solid black line around the box: a rectangle inset 0.14 u from the edge of the blank area, 0.05 u thick.
- Margins 0.55 u left/right, 0.5 u top/bottom. Title, bold 0.66 u, colour (20,20,20): "CMS physics in 1534 plots".
- Two paragraphs, 0.29 u, colour (40,40,40), line step 1.32 × font size, word-wrapped to the box width:
  "The CMS logo, made of plots from 1533 papers of the CMS Collaboration: one plot from every paper except for the
  2012 observation of the Higgs boson, for which two plots are shown (four-lepton and diphoton mass, black frame)."
  and "Each plot is shown as published."
- QR code, bottom right: address `https://home.cern/science/experiments/cms/` (`--url`), python `qrcode` with error
  correction M, no built-in border, black on white, module size = the largest whole number of pixels giving a code of
  at most 1.9 u.
- The CMS logo (`CMSlogo.png` on white, LANCZOS) at the same size as the QR code, to its left, 0.35 u apart.
- Credit line, bottom left beside the logo (wrapped to the width left of it minus 0.4 u), 0.21 u, colour (90,90,90): "Plots: CMS Collaboration, from the arXiv
  sources of the papers. Arrangement computed with Claude (Fable 5.2), 20 November 2026. More about CMS:
  home.cern/science/experiments/cms" (date from `--date`).
- The numbers 1534 and 1533 are taken from the assignment. The position of the QR code is written to `textbox.json`.

"Shown as published" refers to colours and content; plots are scaled, and nearly square ones are drawn as exact squares.

## 13. Check by eye (`contact_sheets.py`)
Sheets of 12×10 numbered thumbnails (128 px) of all chosen plots not yet in `checked.txt`. Figures that are not plots
of a physics quantity (drawings, photos, Feynman diagrams, event displays, tables, legends, plots of other experiments)
go into `exclude.txt`, the others into `checked.txt`; then the mosaic is recomputed. Repeat until no unchecked plot is
chosen. For this build all 1534 plots are in `checked.txt` (the last round: 13 new plots, none excluded).
193 of the plots have soft captions; 259 cells are not filled by their plot.

## 14. Titles (`fetch_titles.py` → `titles.json`)
arXiv API `https://export.arxiv.org/api/query?max_results=100&id_list=…`, 100 ids per request, 3 s pause; id = folder
name with `_` → `/`. Title = `<title>` of each `<entry>`, HTML-unescaped, white space collapsed. All 1534 folders got one.

## 15. PDF (`make_pdf.py`)
One page of 40×40 cm; the hi-res PNG as JPEG (quality 88, no chroma subsampling) with reportlab. Then with pikepdf,
for each cell (whole cell): a link annotation to `https://arxiv.org/abs/ID` with "TITLE (arXiv:ID)" as `/Contents`,
and on top an invisible push-button form field with the same URI action and the same text as tooltip (`/TU`) — the
hover text in Acrobat, Chrome and Firefox. Plus a link on the QR code. Checked by reading the PDF back: 1534 links and
1534 buttons, each on the cell of its paper with that paper's title (0 mismatches). Not tested by hand in a viewer.

## Result
Whole image shrunk to 64 px wide against the logo shrunk the same way: mean RGB distance 84.5, brightness (mean of R, G, B)
correlation 0.58 (the text box is part of the image but not of the logo).

## Known limits
- 259 cells are not filled by their plot (papers with no nearly square plot); square-drawn plots change shape by up to 17 %.
- Plots are mostly white, so the light-blue area is uneven and the letters are only moderately clear.
- The QR code was made by a standard library but not test-scanned.
- The under-1 MB copy has 256 colours; its small text is hard to read.

## Software
Not in the folder (must be installed): python 3.12.3, numpy 1.26.4, scipy 1.11.4, Pillow 10.2.0, qrcode, reportlab,
pikepdf; pdftoppm (poppler),
ImageMagick `convert` (with Ghostscript for eps/ps).
