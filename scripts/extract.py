"""Figures and captions of every paper: reads the LaTeX source in each folder of cms_sources/, writes work/figs.json.
usage (from the mosaic folder): python3 -I scripts/extract.py [SRC OUT]   (defaults: cms_sources work/figs.json)"""
import os, re, json, sys, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the mosaic folder
SRC, OUT = sys.argv[1:3] if len(sys.argv) > 2 else (f'{HERE}/cms_sources', f'{HERE}/work/figs.json')

def braced(s, i):
    # s[i] == '{' ; return content and end index
    depth = 0
    for j in range(i, len(s)):
        if s[j] == '{': depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0: return s[i+1:j], j+1
    return s[i+1:], len(s)

def expand(path, d, seen=0):
    try: t = open(path, errors='ignore').read()
    except: return ''
    t = re.sub(r'(?<!\\)%.*', '', t)
    if seen > 4: return t
    def rep(m):
        name = m.group(1)
        for c in (name, name + '.tex'):
            p = os.path.join(d, c)
            if os.path.isfile(p): return expand(p, d, seen+1)
        return ''
    return re.sub(r'\\(?:input|include)\{([^}]+)\}', rep, t)

POS = [(r'upper limit|exclusion|excluded|95\\?% CL|95\\%', 3), (r'observed', 2), (r'measured|measurement', 2),
       (r'unfolded|differential cross section|cross section', 2), (r'compar\w* (with|to) .*(prediction|theor|calcul)', 2),
       (r'likelihood scan|confidence|contour|signal strength|coupling', 2), (r'summary|combin', 1.5),
       (r'result', 1.5), (r'data', 0.5), (r'extracted|fitted value', 1)]
NEG = [(r'feynman|diagram', -5), (r'schematic|illustration|layout|architecture|sketch', -5),
       (r'efficienc', -2), (r'control region|validation region|sideband', -2), (r'pre-?fit', -2),
       (r'simulat', -1), (r'systematic uncertaint', -1.5), (r'trigger', -1.5), (r'correlation matri', -2),
       (r'event display', -4), (r'acceptance', -1)]

res = {}
for d in sorted(os.listdir(SRC)):
    pd = os.path.join(SRC, d)
    if not os.path.isdir(pd): continue
    mains = [f for f in glob.glob(pd + '/*.tex') if '\\begin{document}' in open(f, errors='ignore').read()]
    if not mains: res[d] = {'error': 'no main tex'}; continue
    # several complete documents (e.g. an author list): prefer the one with figures, then *_temp.tex, then the largest
    def rank(f):
        t = open(f, errors='ignore').read()
        return ('\\begin{figure' not in t and '\\includegraphics' not in t, '_temp' not in f, -len(t), f)
    main = sorted(mains, key=rank)[0]
    t = expand(main, pd)
    title = ''
    m = re.search(r'\\title(?:\[[^\]]*\])?\{', t)
    if m: title = braced(t, m.end()-1)[0]
    app = len(t)
    for pat in (r'\\appendix', r'\\begin\{acknowledgments\}', r'\\bibliography\{', r'\\section\*?\{Summary'):
        mm = re.search(pat, t)
        if mm and pat != r'\\section\*?\{Summary': app = min(app, mm.start())
    summ = re.search(r'\\section\*?\{(Summary|Conclusion)', t)
    figs = []
    for m in re.finditer(r'\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}', t, re.S):
        body = m.group(1)
        files = re.findall(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}', body)
        cm = re.search(r'\\caption(?:\[[^\]]*\])?\{', body)
        cap = braced(body, cm.end()-1)[0] if cm else ''
        cap = re.sub(r'\s+', ' ', cap).strip()
        if not files: continue
        figs.append({'files': files, 'caption': cap, 'appendix': m.start() > app})
    n = len(figs)
    for k, f in enumerate(figs):
        c = f['caption'].lower(); s = 0
        for p, w in POS + NEG:
            if re.search(p, c): s += w
        s += 2.0 * (k / max(n-1, 1))       # later figures more likely results
        if f['appendix']: s -= 4
        f['score'] = round(s, 2); f['idx'] = k + 1
    res[d] = {'main': os.path.basename(main), 'title': re.sub(r'\s+', ' ', title), 'figs': figs}
json.dump(res, open(OUT, 'w'), indent=1)
