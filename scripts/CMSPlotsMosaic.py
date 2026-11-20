"""Physics tile mosaic of the CMS logo: 40x40 grid of same-size square cells on white, every cell a different plot from
a CMS paper, one plot per paper, a text box in the top right corner. No plot is recoloured or tinted.

usage (from the mosaic folder):
  python3 -I scripts/CMSPlotsMosaic.py [--tile_px 160] [--out FILE.png] [--reassign] ...

Steps (see README.md for the full description):
  pool     plots of tile_thumbs.npz (tile_thumbs.py) minus exclude.txt; only nearly square plots, except for papers
           that have none; the paper of --force keeps only the two forced plots
  target   CMSlogo.png on white, 16x16 patches per cell, CIE Lab
  cost     per cell and plot: squared Lab distance on 16x16 ... 1x1 patch grids (finer weights on cells crossed by a
           logo border), times a cell weight (letters "CMS" and particle tracks count more),
           plus penalties (border-case caption, plot not filling its cell); plus a blurred-picture term
  assign   the forced pair first (best two adjacent cells), then the Hungarian algorithm cells x papers,
           then local improvement (another plot of the same paper, or swap two cells)
  draw     plots resized into their cells, black frame around the forced pair, text box with a line around it, the CMS logo and a QR code
The assignment is saved (assignment_N.json) and reused, so other resolutions place the same plots."""
import sys, os, json, argparse, subprocess
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
from scipy.optimize import linear_sum_assignment
Image.MAX_IMAGE_PIXELS = None

SCR = os.path.dirname(os.path.abspath(__file__)); HERE = os.path.dirname(SCR)   # scripts/ and the mosaic folder
W = f'{HERE}/work'; SRC = f'{HERE}/cms_sources'
ap = argparse.ArgumentParser()
ap.add_argument('--n', type=int, default=40, help='tiles per side'); ap.add_argument('--tile_px', type=int, default=160)
ap.add_argument('--gap', type=float, default=0.04, help='white gap between tiles, fraction of a cell')
ap.add_argument('--blank', default='1,28,6,11', help='blank text rectangle: first row, first column, rows, columns (counted from 0)')
ap.add_argument('--out', default=None); ap.add_argument('--assign', default=None); ap.add_argument('--preview', default=None)
ap.add_argument('--w_ab', type=float, default=2.0); ap.add_argument('--chroma_scale', type=float, default=1.0)
ap.add_argument('--lmap', type=float, default=0.0, help='1 = logo lightness fully quantile-matched to the plots, 0 = logo lightness as it is')
ap.add_argument('--scales', default='0,0.15,0.25,0.30,0.30', help='weights of the 16x16, 8x8, 4x4, 2x2, 1x1 patch grids in flat cells')
ap.add_argument('--scales_edge', default='0.20,0.25,0.25,0.15,0.15', help='the same for edge cells (a logo border crosses the cell)')
ap.add_argument('--edge_thr', type=float, default=12.0, help='edge cell = spread (rms Lab distance from the cell mean) of the logo inside the cell above this')
ap.add_argument('--w_letter', type=float, default=4.0, help='extra cost weight of cells containing part of the navy CMS letters')
ap.add_argument('--partners', type=int, default=12, help='swap partners evaluated exactly per cell in the improvement step')
ap.add_argument('--w_track', type=float, default=3.0, help='extra cost weight of cells containing part of a red particle track')
ap.add_argument('--corner', type=float, default=0.0, help='radius of rounded corners of the target, in cells (0 = square, as the logo is)')
ap.add_argument('--w_corner', type=float, default=2.0, help='extra cost weight of the cells that the rounded corners pass through or cut off')
ap.add_argument('--date', default='20 November 2026', help='date printed in the text box')
ap.add_argument('--url', default='https://home.cern/science/experiments/cms/', help='address of the QR code in the text box')
ap.add_argument('--w_blur', type=float, default=1.0, help='weight of the blurred-picture term (0 = tiles matched independently)')
ap.add_argument('--sigma', type=float, default=0.75, help='blur radius (Gaussian sigma) in tiles')
ap.add_argument('--soft_pen', type=float, default=400.0); ap.add_argument('--fill_pen', type=float, default=1500.0, help='penalty x share of the cell a plot leaves empty'); ap.add_argument('--sweeps', type=int, default=12)
ap.add_argument('--force', default='1207.7235__3__0,1207.7235__4__0', help='two plots of one paper, placed side by side in a black frame; the only plots of that paper')
ap.add_argument('--frame', type=float, default=0.10, help='width of the black frame around the forced plot, fraction of a cell')
ap.add_argument('--reassign', action='store_true'); ap.add_argument('--no_draw', action='store_true')
A = ap.parse_args()
BR, BC, BH, BW = (int(v) for v in A.blank.split(','))          # blank rectangle
N = A.n; ASSIGN = A.assign or f'{HERE}/assignment_{N}.json'

def lab(rgb):
    rgb = rgb / 255; c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T / [0.95047, 1, 1.08883]
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

lg = Image.open(f'{HERE}/CMSlogo.png').convert('RGBA'); bgw = Image.new('RGBA', lg.size, 'white'); bgw.alpha_composite(lg)
logo = bgw.convert('RGB'); logo0 = logo                          # logo0: the unchanged logo, also shown in the text box
# rounded corners: outside a rounded square of radius --corner cells the target is white; the logo's black outline
# (8 px of 1024) follows the arc
yy, xx = np.mgrid[0:logo.height, 0:logo.width]; rp = A.corner / A.n * logo.width
ddx = np.maximum(np.maximum(rp - xx, xx - (logo.width - 1 - rp)), 0); ddy = np.maximum(np.maximum(rp - yy, yy - (logo.height - 1 - rp)), 0)
dist = np.hypot(ddx, ddy); incorner = (ddx > 0) & (ddy > 0)
if A.corner > 0:
    la = np.asarray(logo).copy(); la[incorner & (dist > rp - 8)] = 0; la[incorner & (dist > rp)] = 255; logo = Image.fromarray(la)

def pool(a, k):                                  # (..., 8k', 8k', 3)-style block mean: a = (M, 16,16,3) -> (M,k,k,3)
    f = a.shape[1] // k; return a.reshape(a.shape[0], k, f, k, f, 3).mean((2, 4))

# ------------------------------------------------------------------ assignment (computed once, then reused)
if A.reassign or not os.path.exists(ASSIGN):
    rng = np.random.default_rng(1)
    z = np.load(f'{HERE}/tile_thumbs.npz'); keys, fill, soft = z['keys'], z['fill'], z['soft']
    excl = [l.split('#')[0].strip() for l in open(f'{HERE}/exclude.txt') if l.split('#')[0].strip()]
    bad = np.array([any(k == e or k.startswith(e + '__') for e in excl) for k in keys])
    pap0 = np.array([k.split('__')[0] for k in keys]); square = (fill > 0.999) & ~bad
    use = square | (~bad & ~np.isin(pap0, np.unique(pap0[square])))        # other shapes only for papers with no square plot
    forced = A.force.split(','); assert len(forced) == 2
    use &= (pap0 != forced[0].split('__')[0]); use |= np.isin(keys, forced)             # that paper: only the two forced plots
    print(f'papers with plots: {len(set(pap0))}; usable after the exclusion lists: {len(set(pap0[~bad]))}; of these {len(set(pap0[use & ~square]))} have no nearly square plot')
    keys, soft, T16 = keys[use], soft[use], z['T'][use].astype(np.float64); NT = len(keys)
    fillu = fill[use]
    papers = np.array([k.split('__')[0] for k in keys], dtype=object); papers[keys == forced[1]] += '#2'   # second forced plot: its own slot
    up, pid = np.unique(papers.astype(str), return_inverse=True)
    print(f'pool: {NT} plots from {len(up)} papers'); 
    cells = [(r, c) for r in range(N) for c in range(N) if not (BR <= r < BR + BH and BC <= c < BC + BW)]; NC = len(cells)
    assert NC == len(up), f'{NC} cells but {len(up)} plots needed (papers + 1): change --blank'
    cr = np.array([r for r, _ in cells]); ccol = np.array([c for _, c in cells])
    # plot colours in Lab on 16x16, 8x8, 4x4, 2x2, 1x1 grids
    KS = (16, 8, 4, 2, 1); X = {k: lab(pool(T16, k)) for k in KS}
    # target: logo on white, 16 patches per cell (lightness remapping / chroma scaling only if asked for)
    rgb = np.asarray(logo.resize((16 * N, 16 * N), Image.BOX), float); tg = lab(rgb); qs = np.linspace(0, 100, 201)
    tg2 = tg.reshape(2 * N, 8, 2 * N, 8, 3).mean((1, 3))
    Lx, Ly = np.percentile(tg2[..., 0], qs), np.percentile(X[2][..., 0], qs)
    tg[..., 0] = (1 - A.lmap) * tg[..., 0] + A.lmap * np.interp(tg[..., 0], Lx, Ly); tg[..., 1:] *= A.chroma_scale
    percell = lambda a: a.reshape(N, 16, N, 16, -1).transpose(0, 2, 1, 3, 4)[cr, ccol]         # (NC,16,16,ch)
    tcell = percell(tg); TG = {k: tcell.reshape(NC, k, 16 // k, k, 16 // k, 3).mean((2, 4)) for k in KS}
    wv = np.sqrt(np.array([1.0, A.w_ab, A.w_ab]))
    # edge cells (a logo border crosses the cell) and letter cells (part of the navy CMS letters inside)
    spread = np.sqrt((((tcell - tcell.mean((1, 2), keepdims=True)) * wv) ** 2).sum(-1).mean((1, 2))); edge = spread > A.edge_thr
    navy = (rgb[..., 0] < 70) & (rgb[..., 1] < 70) & (rgb[..., 2] > 90)
    navy[:, int(16 * N * 0.80):] = False                                                     # not the small vertical text
    letter = percell(navy[..., None].astype(float)).mean((1, 2, 3)) > 0.04
    red = (rgb[..., 0] > 200) & (rgb[..., 1] < 100) & (rgb[..., 2] < 70)
    track = percell(red[..., None].astype(float)).mean((1, 2, 3)) > 0.03
    cm = np.asarray(Image.fromarray(((incorner & (dist > rp - 8)) * 255).astype(np.uint8)).resize((16 * N, 16 * N), Image.BOX), float) / 255
    corner = (percell(cm[..., None]).mean((1, 2, 3)) > 0.01) & (A.corner > 0)
    cellw = 1 + A.w_letter * letter + A.w_track * track + A.w_corner * corner
    WS = np.where(edge[:, None], np.array([float(v) for v in A.scales_edge.split(',')]), np.array([float(v) for v in A.scales.split(',')]))
    print(f'{int(edge.sum())} edge cells, {int(letter.sum())} letter cells, {int(track.sum())} track cells, {int(corner.sum())} corner cells of {NC}')
    # per-tile cost D[cell, plot] = cell weight x sum over grids of weight x mean squared weighted Lab distance
    D = np.zeros((NC, NT))
    for n, k in enumerate(KS):
        if not WS[:, n].any(): continue
        Fp = (X[k] * wv).reshape(NT, -1) / k; Ft = (TG[k] * wv).reshape(NC, -1) / k
        D += (cellw * WS[:, n])[:, None] * ((Ft ** 2).sum(1)[:, None] - 2 * Ft @ Fp.T + (Fp ** 2).sum(1)[None])
    D += A.soft_pen * soft[None] + A.fill_pen * (1 - fillu)[None]
    # blurred-picture term, on the 2x2 grid (2 pixels per tile): w_blur/4 * || G * (mosaic - target) ||^2
    sg = A.sigma * 2; R = int(np.ceil(3 * sg * np.sqrt(2)))
    ax = np.arange(-R, R + 1); g1 = np.exp(-ax ** 2 / (4 * sg * sg)); g1 /= g1.sum(); G2 = np.outer(g1, g1)   # G convolved with G
    off = [(0, 0), (0, 1), (1, 0), (1, 1)]
    K = np.array([[G2[R + a[0] - b[0], R + a[1] - b[1]] for b in off] for a in off])                        # 4x4
    x2 = (X[2] * wv).reshape(NT, 4, 3); t2 = (TG[2] * wv).reshape(NC, 4, 3); wb = A.w_blur / 4
    def selfblur(i):                              # blur energy of each plot alone in cell i
        d = x2 - t2[i]; return wb * np.einsum('nac,ab,nbc->n', d, K, d)
    D0 = D + np.array([selfblur(i) for i in range(NC)]) if A.w_blur else D.copy()
    # 1) optimal assignment: every paper once (the second forced plot counts as a paper of its own)
    # forced pair: the two horizontally adjacent cells (either order) where the two plots fit best
    fj = [int(np.nonzero(keys == k)[0][0]) for k in forced]; ci_ = {rc: i for i, rc in enumerate(cells)}
    _, r_, c_, a_ = min((D0[ci_[r, c + a], fj[0]] + D0[ci_[r, c + 1 - a], fj[1]], r, c, a)
                        for r in range(N) for c in range(N - 1) for a in (0, 1) if (r, c) in ci_ and (r, c + 1) in ci_)
    fc = [ci_[r_, c_ + a_], ci_[r_, c_ + 1 - a_]]; frozen = np.zeros(NC, bool); frozen[fc] = True
    for i, j in zip(fc, fj):
        keep = (D[i, j], D0[i, j]); D[i, :] = 1e9; D0[i, :] = 1e9; D[:, j] = 1e9; D0[:, j] = 1e9; D[i, j], D0[i, j] = keep
    print(f'forced pair at row {r_ + 1}, columns {c_ + 1}-{c_ + 2} (counted from 1)')
    order = np.argsort(pid, kind='stable'); start = np.searchsorted(pid[order], np.arange(len(up)))
    best = np.minimum.reduceat(D0[:, order], start, axis=1)                          # (NC, papers): best plot of each paper per cell
    rows, cols = linear_sum_assignment(best); cellpaper = np.empty(NC, int); cellpaper[rows] = cols
    cur = np.empty(NC, int)
    for i in range(NC):
        pj = np.nonzero(pid == cellpaper[i])[0]; cur[i] = pj[D0[i, pj].argmin()]
    assert list(cur[fc]) == fj
    # 2) neighbour-aware improvement
    def total(cur):
        res = np.zeros((2 * N, 2 * N, 3))
        for i in range(NC): res[2 * cr[i]:2 * cr[i] + 2, 2 * ccol[i]:2 * ccol[i] + 2] = (x2[cur[i]] - t2[i]).reshape(2, 2, 3)
        from scipy.ndimage import convolve
        e = sum((convolve(res[..., ch], G2, mode='constant') * res[..., ch]).sum() for ch in range(3))
        return D[np.arange(NC), cur].sum(), wb * e, res
    d_, b_, res = total(cur); print(f'after assignment: tile term {d_ / NC:.1f}  blur term {b_ / NC:.1f}  total {(d_ + b_) / NC:.1f}')
    if A.w_blur:
        resp = np.zeros((2 * N + 2 * R, 2 * N + 2 * R, 3)); resp[R:-R, R:-R] = res
        def grad(i):                              # (G2 * residual) at the 4 pixels of cell i -> (4,3)
            r0, c0 = 2 * cr[i], 2 * ccol[i]
            return np.array([(resp[r0 + a:r0 + a + 2 * R + 1, c0 + b:c0 + b + 2 * R + 1] * G2[..., None]).sum((0, 1)) for a, b in off])
        def put(i, j):
            resp[R + 2 * cr[i]:R + 2 * cr[i] + 2, R + 2 * ccol[i]:R + 2 * ccol[i] + 2] = (x2[j] - t2[i]).reshape(2, 2, 3)
        def dcell(i, j):                          # exact change of the total cost when cell i gets plot j (current residual)
            d1 = x2[j] - x2[cur[i]]
            return D[i, j] - D[i, cur[i]] + wb * (2 * (d1 * grad(i)).sum() + np.einsum('ac,ab,bc->', d1, K, d1))
        # moves, for cell i with plot j0 of paper p:  (A) another plot of p   (C) swap the plots of cell i and another cell
        for sweep in range(A.sweeps):
            nrep = nswap = 0; gain = 0.0
            for i in rng.permutation(NC):
                if frozen[i]: continue
                j0 = cur[i]; p = pid[j0]; g = grad(i); d = x2 - x2[j0]                      # change of the residual, (NT,4,3)
                delta = D[i] - D[i, j0] + wb * (2 * (d * g).sum((1, 2)) + np.einsum('nac,ab,nbc->n', d, K, d))
                ok = pid == p                                                               # A
                dl = np.where(ok, delta, np.inf); dl[j0] = np.inf; j = int(dl.argmin())
                best_swap = (0.0, -1)                                                       # C: best few partners, evaluated exactly
                dc = delta[cur].copy(); dc[frozen | (cur == j0)] = np.inf
                for i1 in np.argsort(dc)[:A.partners]:
                    if not np.isfinite(dc[i1]): continue
                    j1 = cur[i1]
                    da = dc[i1]; put(i, j1); cur[i] = j1; db = dcell(i1, j0); cur[i] = j0; put(i, j0)
                    if da + db < best_swap[0]: best_swap = (da + db, int(i1))
                if dl[j] < min(best_swap[0], -1e-9):
                    cur[i] = j; put(i, j); nrep += 1; gain += dl[j]
                elif best_swap[0] < -1e-9:
                    i1 = best_swap[1]; j1 = cur[i1]; cur[i], cur[i1] = j1, j0; put(i, j1); put(i1, j0); nswap += 1; gain += best_swap[0]
            print(f'  sweep {sweep + 1}: {nrep} replaced, {nswap} swapped, gain {gain / NC:.2f} per tile')
            if nrep + nswap < NC * 0.002: break
        d_, b_, res = total(cur); print(f'after improvement: tile term {d_ / NC:.1f}  blur term {b_ / NC:.1f}  total {(d_ + b_) / NC:.1f}')
    assert len(set(cur)) == NC == len(up) and (np.bincount(pid[cur], minlength=len(up)) == 1).all()   # every paper once, no plot twice
    out = [{'r': int(r), 'c': int(c), 'key': str(keys[cur[i]]), **({'forced': True} if frozen[i] else {})} for i, (r, c) in enumerate(cells)]
    json.dump({'params': {k: v for k, v in vars(A).items() if k in ('n', 'blank', 'w_ab', 'chroma_scale', 'lmap', 'scales', 'scales_edge', 'edge_thr', 'w_letter', 'partners', 'w_track', 'corner', 'w_corner', 'w_blur', 'sigma', 'soft_pen', 'fill_pen', 'sweeps', 'force')},
               'cost_per_tile': {'tile': d_ / NC, 'blur': b_ / NC}, 'tiles': out}, open(ASSIGN, 'w'), indent=0)
    print(f'assignment: {NC} tiles, {len({t["key"].split("__")[0] for t in out})} papers, {len(set(cur))} different plots, '
          f'{int(soft[cur].sum())} border-case captions; {int((fillu[cur] < 0.999).sum())} cells are not filled by their plot')
    if A.preview:                                 # quick look: the mosaic made of the 16x16 thumbnails
        pv = np.full((16 * N, 16 * N, 3), 255, np.uint8); T8 = z['T'][use]
        for i, (r, c) in enumerate(cells): pv[16 * r:16 * r + 16, 16 * c:16 * c + 16] = T8[cur[i]]
        Image.fromarray(pv).save(A.preview)
        sm = np.asarray(Image.fromarray(pv).resize((64, 64), Image.BOX), float); lo = np.asarray(logo.resize((64, 64), Image.BOX), float)
        # letters check: brightness correlation at 4 px per cell inside the box around the letter cells
        lc = np.nonzero(letter)[0]; r0, r1, c0, c1 = cr[lc].min(), cr[lc].max() + 1, ccol[lc].min(), ccol[lc].max() + 1
        pa = np.asarray(Image.fromarray(pv).resize((4 * N, 4 * N), Image.BOX), float).mean(2)[4 * r0:4 * r1, 4 * c0:4 * c1]
        la = np.asarray(logo.resize((4 * N, 4 * N), Image.BOX), float).mean(2)[4 * r0:4 * r1, 4 * c0:4 * c1]
        print(f'letters check (rows {r0 + 1}-{r1}, columns {c0 + 1}-{c1}, 4 px per cell): brightness correlation {np.corrcoef(pa.ravel(), la.ravel())[0, 1]:.3f}')
        f4 = lambda im: np.asarray(im.resize((4 * N, 4 * N), Image.BOX), float); P4, L4 = f4(Image.fromarray(pv)), f4(logo)
        redness = lambda a: a[..., 0] - (a[..., 1] + a[..., 2]) / 2; tm = np.repeat(np.repeat(np.isin(np.arange(N * N), [r * N + c for (r, c), t_ in zip(cells, track) if t_]).reshape(N, N), 4, 0), 4, 1)
        print(f'tracks check (track cells, 4 px per cell): redness correlation {np.corrcoef(redness(P4)[tm], redness(L4)[tm])[0, 1]:.3f}')
        print(f'preview check (64 px wide): distance {np.sqrt(((sm - lo) ** 2).sum(2)).mean():.1f}, brightness correlation {np.corrcoef(sm.mean(2).ravel(), lo.mean(2).ravel())[0, 1]:.2f}')
tiles = json.load(open(ASSIGN))['tiles']
if A.no_draw: sys.exit()

# ------------------------------------------------------------------ draw
u = A.tile_px; g = max(1, round(A.gap * u)); side = u - g; SIZE = N * u
INDEX = {f"{c['paper']}__{c['fig']}__{c['panel']}": c['path'] for c in json.load(open(f'{W}/cands.json'))}   # key -> source file
INDEX.update({f"{c['paper']}__{c['fig']}__{c['panel']}": c['path'] for c in json.load(open(f'{HERE}/extra_cands.json'))})
CACHE = f'{W}/render_cache'; os.makedirs(CACHE, exist_ok=True)

def crop_ink(im):
    bb = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda v: 255 if v > 20 else 0).getbbox()
    return im.crop(bb) if bb else im

def render(key, need):
    """the plot image, cropped to its ink, at least about `need` px on its longer side when the source allows"""
    best = None
    for src in (f'{W}/cand/{key}.png', f'{HERE}/extra_cand/{key}.png', f'{W}/hi/{key}.png'):   # 60 dpi (pipeline / extra papers), 130 dpi renders
        if os.path.exists(src):
            best = crop_ink(Image.open(src).convert('RGB'))
            if max(best.size) >= 0.9 * need: return best
    p = os.path.join(SRC, INDEX[key]); have = max(best.size) if best else 0
    if p.endswith('.pdf'):                                           # vector source: render at the resolution needed
        c60 = f'{W}/cand/{key}.png' if os.path.exists(f'{W}/cand/{key}.png') else f'{HERE}/extra_cand/{key}.png'
        base = max(crop_ink(Image.open(c60).convert('RGB')).size)   # size at 60 dpi
        dpi = int(min(400, max(130, np.ceil(60 * need / base * 1.05 / 10) * 10)))
        out = f'{CACHE}/{key}_{dpi}.png'
        if not os.path.exists(out): subprocess.run(['pdftoppm', '-f', '1', '-l', '1', '-singlefile', '-r', str(dpi), '-png', p, out[:-4]], capture_output=True)
    else:                                                            # bitmap source: use it at full size
        out = f'{CACHE}/{key}_full.png'
        if not os.path.exists(out): subprocess.run(['convert'] + (['-density', '300'] if p.lower().endswith(('.eps', '.ps', '.epsi')) else []) + [p + '[0]', '-background', 'white', '-flatten', out], capture_output=True)
    if os.path.exists(out):
        im = crop_ink(Image.open(out).convert('RGB'))
        if max(im.size) > have: best = im
    return best

sys.path.insert(0, SCR); from tile_thumbs import cell_size       # same rule as used for the thumbnails

fw = max(2, round(A.frame * u))                                   # frame width

def card(t):
    sd = side - 2 * fw if t.get('forced') else side; o = (u - sd) // 2          # forced plots are a bit smaller: room for the frame
    im = render(t['key'], sd); a = im.width / im.height; w, h = cell_size(a, sd)
    return (im.resize((w, h), Image.LANCZOS), (t['c'] * u + o + (sd - w) // 2, t['r'] * u + o + (sd - h) // 2),
            max(im.size) / max(w, h), a / (w / h))

from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(8) as ex: cards = list(ex.map(card, tiles))
canvas = Image.new('RGB', (SIZE, SIZE), 'white')
for cd, xy, _, _ in cards: canvas.paste(cd, xy)
ft = [t for t in tiles if t.get('forced')]
if ft:                                                            # black frame around the forced pair (drawn inside its two cells)
    x0, y0 = min(t['c'] for t in ft) * u, min(t['r'] for t in ft) * u; x1, y1 = (max(t['c'] for t in ft) + 1) * u, (max(t['r'] for t in ft) + 1) * u
    ImageDraw.Draw(canvas).rectangle([x0, y0, x1 - 1, y1 - 1], outline='black', width=fw)
low = sum(1 for _, _, q, _ in cards if q < 0.8); asp = np.array([a for _, _, _, a in cards]); nfull = sum(1 for cd, _, _, _ in cards if cd.size[0] == cd.size[1])
# ---- text box in the blank rectangle: line around it, title, text, credit line, CMS logo, QR code
npap = len({t['key'].split('__')[0] for t in tiles}); FB = f'{HERE}/fonts/DejaVuSans-Bold.ttf'; FR = f'{HERE}/fonts/DejaVuSans.ttf'
TITLE = f'CMS physics in {len(tiles)} plots'
BODY = [f'The CMS logo, made of plots from {npap} papers of the CMS Collaboration: one plot from every paper except for the 2012 '
        'observation of the Higgs boson, for which two plots are shown (four-lepton and diphoton mass, black frame).',
        'Each plot is shown as published.']
FOOT = f'Plots: CMS Collaboration, from the arXiv sources of the papers. Arrangement computed with Claude (Fable 5.2), {A.date}. More about CMS: ' + A.url.split('//')[1].rstrip('/')
dr = ImageDraw.Draw(canvas); X0, Y0, X1, Y1 = BC * u, BR * u, (BC + BW) * u, (BR + BH) * u
ins, th = round(0.14 * u), max(2, round(0.05 * u))                                   # solid line around the text box: inset, thickness
dr.rectangle([X0 + ins, Y0 + ins, X1 - ins - 1, Y1 - ins - 1], outline='black', width=th)
mx = round(0.55 * u); x0, y0 = X0 + mx, Y0 + round(0.5 * u); wid = BW * u - 2 * mx
def wrap(text, font, width):
    lines, cur_ = [], ''
    for w_ in text.split():
        t_ = (cur_ + ' ' + w_).strip()
        if dr.textlength(t_, font=font) <= width: cur_ = t_
        else: lines.append(cur_); cur_ = w_
    return lines + [cur_]
f1 = ImageFont.truetype(FB, round(0.66 * u)); f2 = ImageFont.truetype(FR, round(0.29 * u)); f3 = ImageFont.truetype(FR, round(0.21 * u))
while dr.textlength(TITLE, font=f1) > wid: f1 = ImageFont.truetype(FB, f1.size - 1)
y = y0; dr.text((x0, y), TITLE, fill=(20, 20, 20), font=f1); y += round(1.3 * f1.size)
for para in BODY:
    for ln in wrap(para, f2, wid): dr.text((x0, y), ln, fill=(40, 40, 40), font=f2); y += round(1.32 * f2.size)
    y += round(0.45 * f2.size)
import qrcode                                                    # QR code, bottom right of the text box
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0); qr.add_data(A.url); qr.make(fit=True)
qm = np.array(qr.get_matrix(), bool); k = max(1, int(1.9 * u) // len(qm)); qs = k * len(qm)
qx, qy = X1 - mx - qs, Y1 - round(0.5 * u) - qs
canvas.paste(Image.fromarray(np.where(np.kron(qm, np.ones((k, k), bool)), 0, 255).astype(np.uint8)).convert('RGB'), (qx, qy))
lgx = qx - round(0.35 * u) - qs                                   # the CMS logo, same size, left of the QR code
canvas.paste(logo0.resize((qs, qs), Image.LANCZOS), (lgx, qy))
fl = wrap(FOOT, f3, lgx - x0 - round(0.4 * u)); yb = Y1 - round(0.5 * u) - round(1.3 * f3.size) * len(fl)
assert y <= min(yb, qy - round(0.1 * u)), 'text does not fit the blank rectangle'
for ln in fl: dr.text((x0, yb), ln, fill=(90, 90, 90), font=f3); yb += round(1.3 * f3.size)
QRBOX = [qx / SIZE, qy / SIZE, (qx + qs) / SIZE, (qy + qs) / SIZE]   # as fractions of the picture, for the PDF link
out = A.out or f'{HERE}/CMSPlotsMosaic_{SIZE}.png'
canvas.save(out, optimize=True); json.dump({'qr_box': QRBOX, 'url': A.url}, open(f'{HERE}/textbox.json', 'w'))
print('wrote', out, canvas.size, os.path.getsize(out) // 1024, 'KB;', low, f'plots enlarged by more than 25% from their best source; {len(cards) - nfull} plots do not fill their cell; shape change: largest {100 * np.abs(np.log(asp)).max():.0f}% (log), mean {100 * np.abs(np.log(asp)).mean():.1f}%')
