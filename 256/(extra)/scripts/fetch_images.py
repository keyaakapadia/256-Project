#!/usr/bin/env python3
"""
fetch_images.py — source a *good* image for every 256 item.

Searches Openverse (Flickr / museum Creative-Commons photography — the same
"realm" as the Are.na picks) first, falls back to Wikimedia Commons, scores the
candidates for grid-ish / well-shot / high-res, downloads the winner into
images/ under a **name that describes the picture** (not a number), and records
the original page + licence + author.

    python3 fetch_images.py                      # fill items with no image
    python3 fetch_images.py --replace-weak       # ALSO redo the plain Commons
                                                 #   documentary shots from the
                                                 #   first pass
    python3 fetch_images.py --limit 30

Safe to stop / re-run. Only touches items it sources itself.
"""

import argparse, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
MF   = os.path.join(ROOT, "data", "collection.json")
IMG  = os.path.join(ROOT, "images")
LOG  = os.path.join(ROOT, "data", "fetch_images.log")
UA   = "256-thesis-cms/1.0 (student project; kapak530@newschool.edu)"
OV   = "https://api.openverse.org/v1/images/"
WC   = "https://commons.wikimedia.org/w/api.php"
EXT  = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

GOOD = ("pattern", "grid", "aerial", "rows", "repetition", "repeating", "texture",
        "geometry", "geometric", "typology", "abstract", "symmetry", "array",
        "from above", "lines", "stack", "stacked", "tiled", "facade")
BAD  = ("logo", "clipart", "clip art", "icon", "diagram", "vector", "map of",
        "coat of arms", "flag of", "chart of", "screenshot")

STOP = set("a an the of in on at and or with without before after into from to "
           "seen being over under across around each every some several".split())


def log(m):
    line = time.strftime("%H:%M:%S ") + m
    print(line, flush=True)
    open(LOG, "a", encoding="utf-8").write(line + "\n")


def load(): return json.load(open(MF, encoding="utf-8"))


def save(doc):
    items = doc["items"]
    c = sum(1 for i in items if i.get("status") == "collected")
    doc["meta"].update(total=len(items), collected=c, needed=len(items) - c)
    tmp = MF + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MF)


def slug(s, taken):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    s = re.sub(r"-+", "-", s)[:60].strip("-") or "image"
    base, n = s, 2
    while s in taken:
        s = f"{base}-{n}"; n += 1
    taken.add(s)
    return s


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def strip_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def score(title, tags, w, h, provider):
    t = (title + " " + " ".join(tags)).lower()
    s = 0
    if w >= 1600: s += 3
    elif w >= 1000: s += 1
    if w and h and 0.5 <= w / h <= 2.0: s += 1
    if provider in ("flickr", "smithsonian", "metmuseum", "rawpixel", "brooklynmuseum",
                    "clevelandmuseum", "statensmuseum", "sciencemuseum", "nypl"): s += 1
    if any(g in t for g in GOOD): s += 3
    if any(b in t for b in BAD): s -= 6
    return s


def openverse(query):
    q = urllib.parse.urlencode({
        "q": query, "page_size": "18", "category": "photograph",
        "license": "cc0,pdm,by,by-sa,by-nc,by-nc-sa", "mature": "false",
    })
    try:
        data = http_json(OV + "?" + q)
    except Exception as e:
        log(f"  ! openverse {e}"); return []
    out = []
    for r in data.get("results", []):
        url = r.get("url")
        if not url: continue
        w, h = r.get("width") or 0, r.get("height") or 0
        tags = [t.get("name", "") for t in (r.get("tags") or [])]
        lic = ((r.get("license") or "") + " " + (r.get("license_version") or "")).strip().upper() or "CC"
        out.append({
            "dl": url, "w": w, "h": h,
            "score": score(r.get("title") or "", tags, w, h, r.get("provider") or ""),
            "page": r.get("foreign_landing_url") or url,
            "label": "Openverse · " + (r.get("source") or r.get("provider") or "cc"),
            "license": lic,
            "artist": (r.get("creator") or "")[:120],
            "title": strip_html(r.get("title") or "") or query,
        })
    return out


def commons(query):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": "6", "gsrlimit": "12",
        "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": "1600",
    })
    try:
        data = http_json(WC + "?" + q)
    except Exception as e:
        log(f"  ! commons {e}"); return []
    out = []
    for p in (data.get("query") or {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in EXT: continue
        w, h = ii.get("width") or 0, ii.get("height") or 0
        if w < 700: continue
        em = ii.get("extmetadata", {})
        cats = strip_html(em.get("Categories", {}).get("value"))
        out.append({
            "dl": ii.get("thumburl") or ii.get("url"), "w": w, "h": h,
            "score": score(p.get("title", ""), [cats], w, h, "commons"),
            "page": ii.get("descriptionurl") or p.get("title"),
            "label": "Wikimedia Commons",
            "license": strip_html(em.get("LicenseShortName", {}).get("value")) or "see Commons",
            "artist": strip_html(em.get("Artist", {}).get("value"))[:120],
            "title": (p.get("title", "") or query).replace("File:", ""),
        })
    return out


def queries(it):
    t = re.sub(r"[^\w\s-]", " ", (it.get("title") or "")).strip()
    words = [w for w in t.split() if w.lower() not in STOP]
    yield t
    aka = it.get("aka") or []
    for a in aka[:2]:
        if not any(x in a for x in ("&", "Streets", "Home", "People", "Nature",
                                    "Industrial", "Schools", "Stores", "Sports",
                                    "Food", "Transportation", "Abstract")):
            yield a
    if len(words) > 2:
        yield " ".join(words[-3:])


def pick(it):
    best = None
    for i, q in enumerate(queries(it)):
        cands = openverse(q)
        if i == 0:
            cands += commons(q)
        cands = [c for c in cands if c["w"] >= 640]
        cands.sort(key=lambda c: c["score"], reverse=True)
        if cands and cands[0]["score"] >= (3 if i == 0 else 1):
            return cands[0]
        if cands and (best is None or cands[0]["score"] > best["score"]):
            best = cands[0]
        time.sleep(0.4)
    return best


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        clen = int(r.headers.get("Content-Length") or 0)
        if clen > 14_000_000:
            raise ValueError("too big")
        blob = r.read()
    if len(blob) < 2500:
        raise ValueError("too small")
    open(dest, "wb").write(blob)
    return len(blob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--replace-weak", action="store_true")
    ap.add_argument("--sleep", type=float, default=1.1)
    a = ap.parse_args()
    os.makedirs(IMG, exist_ok=True)

    doc = load()
    items = doc["items"]
    taken = set()
    for it in items:
        if it.get("file"):
            taken.add(os.path.splitext(os.path.basename(it["file"]))[0])

    def wants(it):
        if it.get("source") == "arena":
            return False
        if it.get("status") != "collected":
            return True
        if a.replace_weak:
            cr = it.get("image_credit") or {}
            return cr.get("source") == "Wikimedia Commons"
        return False

    todo = [it for it in items if wants(it)]
    if a.limit:
        todo = todo[:a.limit]
    log(f"=== run: {len(todo)} item(s); replace_weak={a.replace_weak} ===")

    got = miss = 0
    for n, it in enumerate(todo, 1):
        tag = f"[{n}/{len(todo)}] {it['title'][:50]}"
        try:
            hit = pick(it)
        except Exception as e:
            log(f"{tag}  ! {e}"); miss += 1; continue
        if not hit:
            log(f"{tag}  — no match"); miss += 1; continue

        old = it.get("file")
        ext = EXT.get("", None)
        ext = os.path.splitext(urllib.parse.urlparse(hit["dl"]).path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        name = slug(it["title"], taken)
        dest = os.path.join(IMG, name + ext)
        try:
            size = download(hit["dl"], dest)
        except Exception as e:
            log(f"{tag}  ! dl {e}"); taken.discard(name); miss += 1; continue

        if old and old != "images/" + name + ext:
            op = os.path.join(ROOT, old)
            if os.path.exists(op) and os.path.basename(op).startswith(("concept-", "arena-")):
                try: os.remove(op)
                except OSError: pass
        it["file"] = "images/" + name + ext
        it["status"] = "collected"
        it["source_url"] = hit["page"]
        it["source_label"] = hit["label"]
        it["image_credit"] = {"source": hit["label"], "page": hit["page"],
                              "license": hit["license"], "artist": hit["artist"]}
        it["color"] = None
        cred = f'{hit["title"]} — {hit["license"]}'
        if hit["artist"]:
            cred += f', {hit["artist"]}'
        if not (it.get("notes") or "").strip() or "via Wikimedia Commons" in (it.get("notes") or ""):
            it["notes"] = cred
        got += 1
        log(f'{tag}  ✓ [{hit["score"]}] {hit["license"]} {size // 1024}KB  {name}{ext}')
        if n % 8 == 0:
            save(doc)
        time.sleep(a.sleep)

    save(doc)
    log(f"=== done: +{got}, {miss} unmatched. {doc['meta']['collected']}/{doc['meta']['total']} collected ===")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("interrupted — saved."); sys.exit(1)
