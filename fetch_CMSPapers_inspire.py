"""Fetch published CMS hep-ex papers from INSPIRE into cms_papers.json,
and optionally download their arXiv PDFs and/or LaTeX sources.

By default only papers not already in cms_papers.json are fetched: results are
requested newest-first and fetching stops at the first page that contains no
new papers. New papers are prepended to the existing list.

Options:
  --full                 re-fetch all papers instead of only new ones
  --download pdf|src|both     (if omitted and new papers are found, you are asked)
                         download files for the newly fetched papers
  --all-missing          with --download: also fill in files missing for any
                         paper already in cms_papers.json

Examples:
  python3 fetch_CMSPapers_inspire.py
  python3 fetch_CMSPapers_inspire.py --download both
  python3 fetch_CMSPapers_inspire.py --download pdf --all-missing
"""
import argparse, json, os, sys, tarfile, time
import requests

JSON_FILE = "cms_papers.json"
URL = "https://inspirehep.net/api/literature"

# ── Download configuration (from fetch_cms_full.py) ─────────────────────────
PDF_DIR      = "cms_pdfs"         # directory for PDFs
SRC_DIR      = "cms_sources"      # directory for source archives
EXTRACT_SRC  = True               # if True, extract .tar.gz and delete archive
DELAY        = 4.0                # seconds between arXiv downloads
TIMEOUT      = 120                # seconds before a download times out
FAILED_LOG   = "cms_download_failed.txt"
# ─────────────────────────────────────────────────────────────────────────────


def fetch_new_papers(existing):
    """Return (new_papers, error) from INSPIRE, skipping papers in `existing`."""
    known_ids = {p["id"] for p in existing}
    new_papers = []
    params = {
        "q": "report_numbers.value:CMS-* and arxiv_eprints.categories:hep-ex and tc published",
        "sort": "mostrecent",
        "size": 250,
        "page": 1,
        "fields": "titles,abstracts,arxiv_eprints,dois,report_numbers"
    }
    fetched = 0

    while True:
        print(f"Fetching page {params['page']}...")
        try:
            r = requests.get(URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Error: {e}")
            return new_papers, True

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", 0)

        if params["page"] == 1:
            print(f"Total papers on INSPIRE: {total}")

        if not hits:
            break

        fetched += len(hits)
        page_new = [p for p in hits if p["id"] not in known_ids]
        new_papers.extend(page_new)
        known_ids.update(p["id"] for p in page_new)
        print(f"  → {len(page_new)} new on this page, {len(new_papers)} new in total")

        # Results are newest-first, so a page with nothing new means we're caught up.
        if existing and not page_new:
            break
        if fetched >= total:
            break

        params["page"] += 1
        time.sleep(1)

    return new_papers, False


def paper_info(p):
    md = p.get("metadata", {})
    titles = md.get("titles") or []
    eprints = md.get("arxiv_eprints") or []
    title = titles[0].get("title", "(no title)") if titles else "(no title)"
    arxiv_id = eprints[0].get("value", "") if eprints else ""
    return title, arxiv_id


def safe_id(arxiv_id):
    return arxiv_id.replace("/", "_")


def needs_pdf(arxiv_id):
    return not os.path.exists(os.path.join(PDF_DIR, f"{safe_id(arxiv_id)}.pdf"))


def needs_src(arxiv_id):
    sid = safe_id(arxiv_id)
    # Already extracted → directory exists; not extracted → tar.gz exists
    return not os.path.exists(os.path.join(SRC_DIR, f"{sid}.tar.gz")) and \
           not os.path.exists(os.path.join(SRC_DIR, sid))


def download_pdf(arxiv_id):
    r = requests.get(f"https://arxiv.org/pdf/{arxiv_id}", timeout=TIMEOUT)
    r.raise_for_status()
    with open(os.path.join(PDF_DIR, f"{safe_id(arxiv_id)}.pdf"), "wb") as f:
        f.write(r.content)


def download_source(arxiv_id):
    """Download the LaTeX source archive from arXiv and (optionally) extract it
    into a per-paper subdirectory of SRC_DIR. Returns (success, message)."""
    r = requests.get(f"https://arxiv.org/src/{arxiv_id}", timeout=TIMEOUT)
    r.raise_for_status()

    # arXiv sometimes returns a bare PDF/PS if no LaTeX source exists
    content_type = r.headers.get("Content-Type", "")
    if "pdf" in content_type or "postscript" in content_type:
        return False, "no LaTeX source (PDF/PS only)"

    sid = safe_id(arxiv_id)
    tar_path = os.path.join(SRC_DIR, f"{sid}.tar.gz")
    with open(tar_path, "wb") as f:
        f.write(r.content)

    if EXTRACT_SRC:
        extract_dir = os.path.join(SRC_DIR, sid)
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with tarfile.open(tar_path) as tar:
                # "data" filter blocks absolute paths / path traversal in archives
                tar.extractall(path=extract_dir, filter="data")
            os.remove(tar_path)
        except Exception as e:
            return False, f"extraction failed: {e}"

    return True, "ok"


def download_files(papers, want_pdf, want_src):
    if want_pdf:
        os.makedirs(PDF_DIR, exist_ok=True)
    if want_src:
        os.makedirs(SRC_DIR, exist_ok=True)

    pending = []
    for p in papers:
        title, arxiv_id = paper_info(p)
        if not arxiv_id:
            continue
        if (want_pdf and needs_pdf(arxiv_id)) or (want_src and needs_src(arxiv_id)):
            pending.append((title, arxiv_id))

    if not pending:
        print("Nothing to download — all files already present.")
        return

    per_paper = int(want_pdf) + int(want_src)
    print(f"\nDownloading for {len(pending)} papers "
          f"(~{len(pending) * per_paper * DELAY / 60:.0f} min at {DELAY}s per download)")

    ok, failed = 0, []
    for i, (title, arxiv_id) in enumerate(pending, 1):
        label = title[:65]
        print(f"[{i}/{len(pending)}]")

        if want_pdf and needs_pdf(arxiv_id):
            try:
                download_pdf(arxiv_id)
                print(f"  ✓ PDF  {arxiv_id}  {label}")
                ok += 1
            except Exception as e:
                print(f"  ✗ PDF  {arxiv_id}  FAILED: {e}")
                failed.append((arxiv_id, "pdf", str(e)))
            time.sleep(DELAY)

        if want_src and needs_src(arxiv_id):
            try:
                success, msg = download_source(arxiv_id)
                if success:
                    print(f"  ✓ SRC  {arxiv_id}  {label}")
                    ok += 1
                else:
                    print(f"  ⚠ SRC  {arxiv_id}  skipped ({msg})")
            except Exception as e:
                print(f"  ✗ SRC  {arxiv_id}  FAILED: {e}")
                failed.append((arxiv_id, "src", str(e)))
            time.sleep(DELAY)

    print(f"\nDownloads done.  {ok} successful,  {len(failed)} failed.")
    if failed:
        with open(FAILED_LOG, "w") as f:
            for row in failed:
                f.write("\t".join(row) + "\n")
        print(f"Failures logged to: {FAILED_LOG}")
    if want_pdf:
        print(f"PDFs in:    {PDF_DIR}/")
    if want_src:
        print(f"Sources in: {SRC_DIR}/")


def ask_download(n_new):
    """Ask what to download for the new papers. Returns 'pdf', 'src', 'both'
    or None. Never asks when stdin is not a terminal (e.g. cron)."""
    if not sys.stdin.isatty():
        print("Not running interactively; skipping downloads "
              "(use --download to download unattended).")
        return None
    print(f"\nDownload files for the {n_new} new paper(s)?")
    print("  1) PDFs only")
    print("  2) Source files only (LaTeX + original plots)")
    print("  3) Both PDFs and source files")
    print("  4) Skip")
    choices = {"1": "pdf", "2": "src", "3": "both", "4": None, "": None}
    while True:
        try:
            choice = input("Enter 1, 2, 3 or 4 [4]: ").strip()
        except EOFError:
            return None
        if choice in choices:
            return choices[choice]
        print("Invalid choice.")


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true",
                        help="re-fetch all papers instead of only new ones")
    parser.add_argument("--download", choices=["pdf", "src", "both"],
                        help="download arXiv PDFs, LaTeX sources, or both")
    parser.add_argument("--all-missing", action="store_true",
                        help="with --download: fill in missing files for all papers, "
                             "not just newly fetched ones")
    args = parser.parse_args()
    if args.all_missing and not args.download:
        parser.error("--all-missing requires --download")

    existing = []
    if not args.full and os.path.exists(JSON_FILE):
        with open(JSON_FILE) as f:
            existing = json.load(f)
    print(f"Existing papers in {JSON_FILE}: {len(existing)}")

    new_papers, error = fetch_new_papers(existing)
    print(f"\nDone! {len(new_papers)} new papers fetched.")

    all_papers = new_papers + existing
    if new_papers:
        for p in new_papers:
            print(f"  + {p['id']}: {paper_info(p)[0]}")
        tmp = JSON_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(all_papers, f, indent=2)
        os.replace(tmp, JSON_FILE)
        print(f"Saved {len(all_papers)} papers to {JSON_FILE}")
    else:
        print(f"No changes; {JSON_FILE} left as is.")

    download = args.download
    if not download and new_papers:
        download = ask_download(len(new_papers))

    if download:
        want_pdf = download in ("pdf", "both")
        want_src = download in ("src", "both")
        targets = all_papers if args.all_missing else new_papers
        download_files(targets, want_pdf, want_src)

    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
