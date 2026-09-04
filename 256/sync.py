#!/usr/bin/env python3
"""
sync.py — pull anything newly added to the Are.na channels into the collection.

Checks the two named channels plus the supplemental grid channels, downloads
any image block that isn't already here (matched by Are.na block id *and* by
file content), appends it as an Unplaced item, and re-bakes data/collection.js.

    python3 sync.py            # one pass
    python3 sync.py --quiet    # only print when something changed

Run it on a schedule to keep the archive current. Pinterest can't be synced
automatically (login wall) — pull those in by hand with the console snippet.
"""
import argparse, hashlib, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG  = os.path.join(ROOT, "images")
MF   = os.path.join(ROOT, "data", "collection.json")
LOG  = os.path.join(ROOT, "data", "sync.log")
BAKE = os.path.join(ROOT, "bake.py")
UA   = {"User-Agent": "256-thesis-cms/1.0 (kapak530@newschool.edu)"}

# only YOUR two channels — new blocks you add there land here automatically.
# (the supplemental public channels were one-time top-ups, not watched.)
CHANNELS = [
    "grids-irl-order-to-chaos",
    "two-five-six-zp015cq1v2k",
]
CATS = ["Streets & public space", "Transportation", "Schools & offices", "Stores & commerce",
        "Food & kitchens", "Home & objects", "People & gatherings", "Sports & recreation",
        "Nature, farming & landscape", "Industrial & technical",
        "Op-art & moiré", "Pattern & texture", "Type & lettering", "Animation",
        "Abstract & image-grids"]


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M ") + msg
    print(line, flush=True)
    try:
        open(LOG, "a", encoding="utf-8").write(line + "\n")
    except OSError:
        pass


def fetch_channel(slug):
    out, page = [], 1
    while True:
        u = f"https://api.are.na/v2/channels/{slug}/contents?per=100&page={page}"
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40))
        except Exception as e:
            log(f"  ! {slug} p{page}: {e}"); break
        cs = d.get("contents") or []
        out += cs
        if len(cs) < 100:
            break
        page += 1; time.sleep(0.3)
    return out


def real_title(b):
    for k in ("title", "generated_title"):
        v = (b.get(k) or "").strip()
        if v and not re.match(r"^(original_|tumblr_|image\.?$|screenshot|screen[- ]shot|untitled|giphy|IMG[_-]|DSC|\d+[_.-]|https?[:/]|[a-f0-9]{16,}$)", v, re.I):
            return re.sub(r"\.(jpe?g|png|gif|webp|gifv)$", "", v, flags=re.I).strip()
    return ""


def ext_source(b):
    u = (b.get("source") or {}).get("url") or ""
    bad = ("cloudfront.net", "arena_images", "arena-images-temp", "media.tumblr.com")
    return u if (u and not any(x in u for x in bad)) else f"https://www.are.na/block/{b['id']}"


def host(u):
    try:
        n = urllib.parse.urlparse(u).netloc
        return "Are.na" if "are.na" in n else (n[4:] if n.startswith("www.") else n)
    except Exception:
        return "Are.na"


def slug(s, taken):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:58].strip("-") or "grid"
    out, n = s, 2
    while out in taken:
        out = f"{s}-{n}"; n += 1
    taken.add(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    doc = json.load(open(MF, encoding="utf-8"))
    items = doc["items"]
    # remember every block we've seen, so a block you delete/cull never comes back
    seen_path = os.path.join(ROOT, "data", "sync_seen.json")
    try:
        seen = set(json.load(open(seen_path)))
    except Exception:
        seen = set()
    have = {it["id"] for it in items} | seen
    taken = {os.path.splitext(os.path.basename(it["file"]))[0] for it in items if it.get("file")}
    hashes = set()
    for it in items:
        p = os.path.join(ROOT, it["file"]) if it.get("file") else None
        if p and os.path.exists(p):
            try:
                hashes.add(hashlib.md5(open(p, "rb").read()).hexdigest())
            except OSError:
                pass

    added = 0
    for ch in CHANNELS:
        for b in fetch_channel(ch):
            if b.get("class") != "Image":
                continue
            bid = f"arena-{b['id']}"
            seen.add(bid)
            if bid in have:
                continue
            url = (b.get("image") or {}).get("original", {}).get("url") or (b.get("source") or {}).get("url")
            if not url:
                continue
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            try:
                blob = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            except Exception:
                continue
            if len(blob) < 2500:
                continue
            h = hashlib.md5(blob).hexdigest()
            if h in hashes:
                have.add(bid)
                continue
            hashes.add(h)
            title = real_title(b)
            name = slug(title or f"grid-new-{b['id']}", taken)
            open(os.path.join(IMG, name + ext), "wb").write(blob)
            src = ext_source(b)
            items.append({
                "id": bid, "title": title, "needs_name": not title,
                "spectrum": None, "spectrum_rank": None,
                "category": "Animation" if ext == ".gif" else "Abstract & image-grids",
                "on_arena_board": True, "arena_channel": ch, "source": "arena",
                "status": "collected", "file": "images/" + name + ext,
                "source_url": src, "source_label": host(src),
                "arena_block_url": f"https://www.are.na/block/{b['id']}",
                "arena_image_url": url, "archive_links": [], "color": None,
                "notes": (b.get("description") or "").strip(),
            })
            have.add(bid)
            added += 1
            log(f"  + {name}{ext}  ({ch})")
            time.sleep(0.15)

    json.dump(sorted(seen), open(seen_path, "w"))
    if added:
        c = len(items)
        doc["meta"]["categories"] = CATS
        doc["meta"].update(total=c, collected=c, needed=0)
        tmp = MF + ".tmp"
        json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        os.replace(tmp, MF)
        os.system(f'{sys.executable} "{BAKE}" >/dev/null 2>&1')
        log(f"synced: +{added} new  ->  {c} items total")
    elif not a.quiet:
        log("synced: nothing new")


if __name__ == "__main__":
    main()
