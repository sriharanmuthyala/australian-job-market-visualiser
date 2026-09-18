#!/usr/bin/env python3
"""
Add median weekly earnings and a short description to each occupation in data.json
by reading the Jobs and Skills Australia occupation profiles.

    python enrich_profiles.py data.json

The descriptions are what score_llm.py reads, so run this before scoring.
Be polite: the default is one request per second, and results are cached in
.cache/ so re-runs are cheap.

JSA renders these pages with Drupal and the markup shifts between releases.
Everything below is best-effort: if a field can't be found it stays null and
the viewer just shows "—" for that layer.
"""

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request

BASE = "https://www.jobsandskills.gov.au"
SEARCH = BASE + "/data/occupation-and-industry-profiles/occupations-osca"
UA = "ausjobs-treemap/1.0 (personal research tool)"
CACHE = ".cache"


def get(url, pause=1.0):
    os.makedirs(CACHE, exist_ok=True)
    key = os.path.join(CACHE, re.sub(r"\W+", "_", url)[-180:] + ".html")
    if os.path.exists(key):
        return open(key, encoding="utf-8").read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")
    open(key, "w", encoding="utf-8").write(html)
    time.sleep(pause)
    return html


def strip_tags(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;?", " ", s)
    s = re.sub(r"&amp;", "&", s)
    return re.sub(r"\s+", " ", s).strip()


def find_profile_url(name, code):
    """Search the profile index for this occupation and return its page URL."""
    q = SEARCH + "?" + urllib.parse.urlencode({"search_api_fulltext": name})
    html = get(q)
    hrefs = re.findall(r'href="(/data/occupation-and-industry-profiles/[^"]+)"', html)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    for h in hrefs:
        if slug[:24] in h:
            return BASE + h
    return BASE + hrefs[0] if hrefs else None


def parse_profile(html):
    text = strip_tags(html)
    out = {}
    m = re.search(r"median weekly earnings[^$]{0,80}\$([\d,]+)", text, re.I)
    if m:
        out["pay_weekly"] = int(m.group(1).replace(",", ""))
    m = re.search(r"(?:employed|employment)\D{0,40}([\d,]{4,})", text, re.I)
    if m:
        out["emp_profile"] = int(m.group(1).replace(",", ""))
    # The description sits after the occupation title, before the stats blocks.
    m = re.search(r"(?:Description|What they do)\s*(.{80,1200}?)(?:Employed|Median|Skill level)", text, re.I)
    if m:
        out["description"] = m.group(1).strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", default="data.json", nargs="?")
    ap.add_argument("--pause", type=float, default=1.0)
    ap.add_argument("--limit", type=int, default=0, help="stop after N occupations (for testing)")
    args = ap.parse_args()

    doc = json.load(open(args.data))
    rows = doc["occupations"]
    if args.limit:
        rows = rows[: args.limit]

    for i, d in enumerate(rows, 1):
        if d.get("pay_weekly") and d.get("description"):
            continue
        try:
            url = find_profile_url(d["name"], d["code"])
            if not url:
                print(f"  {i:>3}/{len(rows)} {d['name']}: no profile found")
                continue
            info = parse_profile(get(url, args.pause))
            d["url"] = url
            for k in ("pay_weekly", "description"):
                if info.get(k):
                    d[k] = info[k]
            print(f"  {i:>3}/{len(rows)} {d['name']}: "
                  f"pay={d.get('pay_weekly')} desc={'yes' if d.get('description') else 'no'}")
        except Exception as e:
            print(f"  {i:>3}/{len(rows)} {d['name']}: {e}")

    json.dump(doc, open(args.data, "w"), indent=1)
    got = sum(1 for d in doc["occupations"] if d.get("pay_weekly"))
    print(f"\nupdated {args.data}: median pay on {got}/{len(doc['occupations'])} occupations")


if __name__ == "__main__":
    main()
