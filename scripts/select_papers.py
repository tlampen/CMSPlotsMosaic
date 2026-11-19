"""Choose which papers go into the grid and each paper's main-result figure.

usage (from the mosaic folder): python3 -I scripts/select_papers.py [WORK N PICKS]   (defaults: work 1521 main_picks.txt)
  WORK   work directory (must contain figs.json from extract.py)
  N      number of papers (the newest N by arXiv number)
  PICKS  file with hand-made main-result picks, lines "arxiv_id figure panel"
Papers without a hand-made pick get the highest-scoring figure from extract.py
(marked 'auto'; such picks must still pass the physics-variable filter).
Writes WORK/selection.txt."""
import json, sys, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the mosaic folder
W, N, PICKS = (sys.argv[1], int(sys.argv[2]), sys.argv[3]) if len(sys.argv) > 3 else (f'{HERE}/work', 1521, f'{HERE}/main_picks.txt')   # defaults
r = json.load(open(f'{W}/figs.json'))
picks = {l.split()[0]: l.split() for l in open(PICKS) if l.strip()}
def age(d):
    """sort key by submission date: new-style 2202.05856 and old-style hep-ex_0012003 (YYMMNNN)"""
    num = d.split('_')[-1]
    yymm, rest = (num[:4], num[5:]) if '.' in num else (num[:4], num[4:])
    yy = int(yymm[:2]); year = 1900 + yy if yy >= 91 else 2000 + yy
    return (year, int(yymm[2:]), int(rest), d)
papers = sorted((d for d, v in r.items() if 'figs' in v and v['figs']), key=age)
if len(papers) < N:
    sys.exit(f'only {len(papers)} papers with figures in the sources, {N} requested')
chosen, auto = sorted(papers[-N:]), []
with open(f'{W}/selection.txt', 'w') as f:
    for d in chosen:
        if d in picks:
            f.write(' '.join(picks[d]) + '\n')
        else:
            best = max(r[d]['figs'], key=lambda x: x['score'])
            f.write(f"{d} {best['idx']} 0 auto\n"); auto.append(d)
print(f'{N} papers, {chosen[0]} .. {chosen[-1]}; automatic main-result pick for {len(auto)}')
if auto: print(f"  they are marked 'auto' in {W}/selection.txt; copy corrected lines to {PICKS} to fix them")
