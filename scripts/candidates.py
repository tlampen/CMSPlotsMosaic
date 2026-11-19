"""List every figure panel of the selected papers, dropping figures that do not show a physics variable."""
import json, re, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the mosaic folder
S, SRC = sys.argv[1:3] if len(sys.argv) > 2 else (f'{HERE}/work', f'{HERE}/cms_sources')   # usage: python3 -I scripts/candidates.py [WORK SRC]
r = json.load(open(f'{S}/figs.json'))
papers = [l.split()[0] for l in open(f'{S}/selection.txt')]
main = {l.split()[0]: (int(l.split()[1]), int(l.split()[2])) for l in open(f'{S}/selection.txt')}
AUTO = {l.split()[0] for l in open(f'{S}/selection.txt') if l.split()[3:] == ['auto']}
# HARD: not a plot of a physics variable at all (drawings, photos, displays) -> always dropped
HARD = re.compile(r'feynman|diagram|schematic|sketch|layout|architecture|flowchart|flow chart|event display|photograph|'
                  r'\bphoto|picture|workflow|cross-sectional view|network structure|structural representation|'
                  r'service setup|firmware|location relative|tracker map|pictorial|binning scheme|displays? of|scheme of|conceptual design|event topology|simplified model for', re.I)
# SOFT: border cases (ML outputs, matrices, ROC curves, impacts, yields, binning, uncertainty breakdowns ...)
# -> kept, with a small penalty in colour3.py so they win only when they match the logo colours clearly better
SOFT = re.compile(r'illustrat|definition of|visuali[sz]ation|structure of the|'
                 r'confusion matri|correlation matri|migration matri|response matri|covariance matri|'
                 r'\bloss\b|training|learning rate|runtime|\bepoch|roc curve|rejection rate versus|'
                 r'impacts? of (the )?nuisance|pulls?\b|overview of|representation of|example of the correction procedure|'
                 r'binning|fraction of the total signal|signal composition|correlations between|sources of uncertaint|\bz score|false positive|true positive|correlation factors|correlation coefficient|probability matri|signal regions defined|sources of systematic|\bimpacts?\b|nuisance parameter|time taken|production modes|benchmark .*models|categori[sz]ation|custom function|transfer function|eigenvalue|eigenvector|breakdown|impact of (the )?systematic|correlations? of the|sigmoid|event yields|yields in (each|the)|discriminant|\bscores?\b|classifier|\bdnn\b|\bbdt\b|\bpnn\b|\bnn output|output node|\bauc\b|systematic uncertainties related|breakdown of (the )?systematic|relative (systematic )?uncertaint(y|ies) (as|in)',
                 re.I)
# panels (paper__figure__panel) or whole figures (paper__figure) to leave out
BLACK = {'2504.08507__5__0',                                   # legend only
         '2406.08712__1', '2206.09997__1', '2404.02992__1', '2309.16003__1',  # photo / production diagrams
         '2406.08712__11', '2302.02970__1', '2506.17195__4',                  # photos
         '2404.16082__1', '2604.13320__1', '2401.08777__3',
         '2406.08712__2', '2406.08712__4', '2406.08712__5', '2406.08712__6', '2406.08712__8', '2406.08712__9',  # no captions: photos/sketches
         '2411.19749__2',                                      # detector sketch
         '2402.08486__1', '2210.02489__3', '2204.12313__3', '2402.18658__3', '2407.10717__7',   # drawings with soft-only captions
         '2307.15761__2', '2509.13512__2', '2509.13512__19', '2304.07174__6', '2206.09466__17',
         # drawings found in the 39x39 grid (Feynman diagrams, sketches, photo, slide, text page)
         '1801.03957__1', '1502.04785__1', '1104.3168__1', '1909.12285__2', '1708.02510__1', '1209.2344__1',
         '2102.08816__1', '1601.06431__1', '0805.4769__2', '2401.08777__2', '1901.04040__3', '2105.01683__2',
         '1707.03325__1', '2012.03876__5', '1204.3774__4', '2002.11449__3', '1303.4571__1__1', '1707.00350__2',
         '0805.3816__3', '2011.03422__1', '2006.10165__15', '2008.04422__3', '2111.13948__2', '1012.5945__3',
         '1502.04785__2', '1801.03957__2', '2002.11449__1', '2002.11449__4', '2002.11449__5', '2002.11449__11',
         '2012.03876__2', '2012.03876__3', '2012.03876__7', '2012.03876__10', '2105.01683__1', '2105.01683__6', '2105.01683__7',
         '2011.01185__26', '1511.06084__2'}                                    # detector geometry, pixel layout                   # selection trees, region/binning schemes
def resolve(d, fn):
    """file for an \\includegraphics name: as given, with an extension, or (for \\graphicspath) anywhere below the paper dir"""
    for c in (fn, fn + '.pdf', fn + '.png', fn + '.jpg'):
        if os.path.isfile(os.path.join(SRC, d, c)): return os.path.join(d, c)
    base = os.path.basename(fn)
    for root, _, files in os.walk(os.path.join(SRC, d)):
        for c in (base, base + '.pdf', base + '.png', base + '.jpg'):
            if c in files: return os.path.relpath(os.path.join(root, c), SRC)
    return None

out, stats = [], {}
for d in papers:
    figs = r[d]['figs']; n0 = 0
    seen = set()
    for f in figs:
        hard = bool(HARD.search(f['caption'])); soft = bool(SOFT.search(f['caption']))
        for k, fn in enumerate(f['files']):
            p = resolve(d, fn)
            if not p or p in seen: continue
            if hard and ((f['idx'], k) != main[d] or d in AUTO): continue
            if f"{d}__{f['idx']}__{k}" in BLACK or f"{d}__{f['idx']}" in BLACK: continue
            seen.add(p)
            out.append({'paper': d, 'fig': f['idx'], 'panel': k, 'path': p, 'appendix': f['appendix'],
                        'main': (f['idx'], k) == main[d], 'soft': soft, 'cap': f['caption'][:200]})
            n0 += 1
    if n0 == 0:                               # nothing passed the filter: fall back to the main-result panel
        f = figs[main[d][0] - 1]; fn = f['files'][main[d][1]]
        p = resolve(d, fn)
        if p:
            out.append({'paper': d, 'fig': f['idx'], 'panel': main[d][1], 'path': p,
                        'appendix': f['appendix'], 'main': True, 'soft': False, 'cap': f['caption'][:200]}); n0 = 1
    stats[d] = n0
json.dump(out, open(f'{S}/cands.json', 'w'), indent=0)
v = sorted(stats.values())
print('candidates', len(out), 'papers', len(stats), 'min/median/max per paper', v[0], v[len(v)//2], v[-1])
