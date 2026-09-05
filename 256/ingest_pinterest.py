#!/usr/bin/env python3
"""
ingest_pinterest.py — add pins pulled via the browser-console snippet.

Feed it the JSON array the console produced: [{url, alt, pin}, ...]

    python3 ingest_pinterest.py pins.json

Downloads each image into images/, names it from the alt text, guesses a
folder from the alt text, records the pin as source_url, lands it Unplaced,
de-dupes by file content, and re-bakes data/collection.js.
"""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, "images")
MF = os.path.join(ROOT, "data", "collection.json")
BAKE = os.path.join(ROOT, "bake.py")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

KW = {
 "Streets & public space": "manhole sidewalk street facade fence netting scaffold construction debris net brick pavement",
 "Industrial & technical": "netting debris safety dust control construction site",
 "People & gatherings": "people crowd circle standing walking faces person",
 "Nature, farming & landscape": "field garden tree leaf farm",
 "Home & objects": "tile floor quilt textile fabric",
}


def clean_alt(a):
    a = re.sub(r"^\s*This (may contain|contains an image of)[:\s]*", "", a or "", flags=re.I)
    a = a.strip(" .")
    return a


def guess_cat(alt):
    t = alt.lower()
    best, bs = "Abstract & image-grids", 0
    for c, kw in KW.items():
        s = sum(1 for k in kw.split() if k in t)
        if s > bs:
            bs, best = s, c
    return best


def slug(s, taken):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:58].strip("-") or "pin"
    out, n = s, 2
    while out in taken:
        out = f"{s}-{n}"; n += 1
    taken.add(out)
    return out


def main():
    if len(sys.argv) < 2:
        print("usage: python3 ingest_pinterest.py pins.json"); sys.exit(1)
    pins = json.load(open(sys.argv[1], encoding="utf-8"))

    doc = json.load(open(MF, encoding="utf-8"))
    items = doc["items"]
    taken = {os.path.splitext(os.path.basename(it["file"]))[0] for it in items if it.get("file")}
    hashes = set()
    for it in items:
        p = os.path.join(ROOT, it["file"]) if it.get("file") else None
        if p and os.path.exists(p):
            try:
                hashes.add(hashlib.md5(open(p, "rb").read()).hexdigest())
            except OSError:
                pass
    have_pin = {it.get("source_url") for it in items if it.get("source") == "pinterest"}

    added = skipped = 0
    for p in pins:
        url, alt, pin = p.get("url"), clean_alt(p.get("alt")), p.get("pin")
        if not url or pin in have_pin:
            skipped += 1; continue
        try:
            blob = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception as e:
            print("  ! download failed", url, e); skipped += 1; continue
        if len(blob) < 2000:
            skipped += 1; continue
        h = hashlib.md5(blob).hexdigest()
        if h in hashes:
            skipped += 1; continue
        hashes.add(h)
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".jpg"
        if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            ext = ".jpg"
        title = alt[:70] if alt else "Pinterest reference"
        name = slug(title, taken)
        open(os.path.join(IMG, name + ext), "wb").write(blob)
        items.append({
            "id": "pin-" + hashlib.md5(pin.encode()).hexdigest()[:10],
            "title": title,
            "spectrum": None, "spectrum_rank": None,
            "category": guess_cat(alt),
            "on_arena_board": False, "source": "pinterest",
            "status": "collected", "file": "images/" + name + ext,
            "source_url": pin, "source_label": "Pinterest",
            "archive_links": [], "color": None, "notes": "",
        })
        added += 1
        print(f"  + {name}{ext}")
        time.sleep(0.1)

    if added:
        c = len(items)
        doc["meta"].update(total=c, collected=c, needed=0)
        tmp = MF + ".tmp"
        json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        os.replace(tmp, MF)
        os.system(f'{sys.executable} "{BAKE}" >/dev/null 2>&1')
    print(f"\nadded {added}, skipped {skipped} (dupe/failed). total now {len(items)}.")


if __name__ == "__main__":
    main()
