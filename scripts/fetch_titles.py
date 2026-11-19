"""Titles of all papers in cms_sources/ from the public arXiv API (for the hover text in the PDF).
usage (from the mosaic folder): python3 -I scripts/fetch_titles.py
Asks http://export.arxiv.org/api/query?id_list=... in batches of 100 ids, 3 s pause between batches (arXiv's rule).
Paper id = folder name; old-style folders hep-ex_0012003 -> hep-ex/0012003. Writes titles.json {folder: title}."""
import os, re, json, time, html, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the mosaic folder
ids = sorted(d for d in os.listdir(f'{HERE}/cms_sources') if re.match(r'^(\d{4}\.\d{4,5}|[a-z-]+_\d{7})$', d))
out = f'{HERE}/titles.json'; T = json.load(open(out)) if os.path.exists(out) else {}
todo = [d for d in ids if d not in T]
for s in range(0, len(todo), 100):
    b = todo[s:s + 100]; url = 'https://export.arxiv.org/api/query?max_results=100&id_list=' + ','.join(x.replace('_', '/') for x in b)
    x = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'python-urllib'}), timeout=60).read().decode()
    for e in re.findall(r'<entry>(.*?)</entry>', x, re.S):
        i = re.search(r'<id>https?://arxiv.org/abs/(.*?)</id>', e).group(1); i = re.sub(r'v\d+$', '', i).replace('/', '_')
        T[i] = ' '.join(html.unescape(re.search(r'<title>(.*?)</title>', e, re.S).group(1)).split())
    json.dump(T, open(out, 'w'), indent=0, ensure_ascii=False); print(len(T), 'titles'); time.sleep(3)
print('missing:', [d for d in ids if d not in T])
