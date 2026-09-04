#!/usr/bin/env python3
"""
add_more_grids.py — top the Are.na build up to a target count with more
grid blocks pulled from public Are.na channels in the same vein.

    python3 add_more_grids.py --target 300

De-dupes by file content against what's already in images/.  New items land
Unsorted (no spectrum) for you to place; folder is auto-guessed; colour is
read on load.  Source = the block's external link when Are.na has one, else
the Are.na block permalink.
"""
import argparse, hashlib, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, "images")
MF = os.path.join(ROOT, "data", "collection.json")
PULL = os.path.join(ROOT, "data", "arena_pull")
UA = {"User-Agent": "256-thesis-cms/1.0 (kapak530@newschool.edu)"}

# public channels — op-art, generative pattern, animated grids (well-labelled ones)
CHANNELS = [
    "op-art-m_f8v8_zgb4",
    "i-can-t-believe-it-s-not-gif",
    "patterns-w61q_k86gr0",
]
CATS = ["Streets & public space", "Transportation", "Schools & offices", "Stores & commerce",
        "Food & kitchens", "Home & objects", "People & gatherings", "Sports & recreation",
        "Nature, farming & landscape", "Industrial & technical", "Abstract & image-grids"]
KW = {
 "Transportation": "car parking garage runway subway train rail bike taxi bus airport marina traffic container",
 "Streets & public space": "street sidewalk crosswalk facade balcony fence scaffold building brick pavement plaza housing aerial rooftop city block",
 "Schools & offices": "desk locker classroom library cubicle office ceiling calendar spreadsheet lecture floor-plan plan",
 "Stores & commerce": "supermarket shelf shop store aisle retail vending product packaging",
 "Food & kitchens": "egg carton tray oven cookie bread sushi kitchen fridge bottle restaurant",
 "Home & objects": "tile floor quilt blanket window screen blind shelf rug textile flower lattice cutout",
 "People & gatherings": "people crowd audience choir orchestra stadium bleacher dancers queue protest portrait faces",
 "Sports & recreation": "court tennis basketball soccer pool bowling gym chess scrabble bingo",
 "Nature, farming & landscape": "field crop vineyard orchard garden greenhouse honeycomb spiderweb leaf beach cemetery landscape",
 "Industrial & technical": "solar server circuit led factory conveyor pallet pipe pegboard rebar mailbox film cassette",
}


def guess_cat(t):
    t = (t or "").lower(); best, bs = "Abstract & image-grids", 0
    for c, kw in KW.items():
        s = sum(1 for k in kw.split() if k in t)
        if s > bs: bs, best = s, c
    return best


def real_title(b):
    for key in ("title", "generated_title"):
        v = (b.get(key) or "").strip()
        if v and not re.match(r"^(original_|tumblr_|image\.?$|screenshot|screen[- ]shot|untitled|giphy|IMG[_-]|DSC|\d+[_.-]|https?[:/]|[a-f0-9]{16,}$)", v, re.I):
            return re.sub(r"\.(jpe?g|png|gif|webp|gifv)$", "", v, flags=re.I).strip()
    return None


def ext_source(b):
    u = (b.get("source") or {}).get("url") or ""
    bad = ("cloudfront.net", "arena_images", "arena-images-temp", "media.tumblr.com")
    if u and not any(x in u for x in bad):
        return u
    return f"https://www.are.na/block/{b['id']}"


def host(u):
    try:
        n = urllib.parse.urlparse(u).netloc
        return "Are.na" if "are.na" in n else (n[4:] if n.startswith("www.") else n)
    except Exception:
        return "Are.na"


def dl(url):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=120) as f:
        return f.read()


def fetch_channel(slug):
    out, page = [], 1
    while True:
        u = f"https://api.are.na/v2/channels/{slug}/contents?per=100&page={page}"
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40))
        except Exception as e:
            print("  ! channel", slug, e); break
        cs = d.get("contents") or []
        out += cs
        if len(cs) < 100:
            break
        page += 1; time.sleep(0.3)
    return out


def slug_name(s, taken):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:58].strip("-") or "grid"
    out, n = s, 2
    while out in taken:
        out = f"{s}-{n}"; n += 1
    taken.add(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=300)
    a = ap.parse_args()
    os.makedirs(PULL, exist_ok=True)

    doc = json.load(open(MF, encoding="utf-8"))
    items = doc["items"]
    have_ids = {it["id"] for it in items}

    # hash every image already in the collection
    hashes = set()
    for it in items:
        p = os.path.join(ROOT, it["file"]) if it.get("file") else None
        if p and os.path.exists(p):
            hashes.add(hashlib.md5(open(p, "rb").read()).hexdigest())
    taken = {os.path.splitext(os.path.basename(it["file"]))[0] for it in items if it.get("file")}

    need = a.target - len(items)
    print(f"have {len(items)}, target {a.target} -> need {need} more")
    if need <= 0:
        return

    added = 0
    for slug in CHANNELS:
        if added >= need:
            break
        blocks = fetch_channel(slug)
        json.dump(blocks, open(os.path.join(PULL, slug + ".json"), "w"), indent=1)
        imgs = [b for b in blocks if b.get("class") == "Image"]
        print(f"{slug}: {len(imgs)} image blocks")
        for b in imgs:
            if added >= need:
                break
            bid = f"arena-{b['id']}"
            if bid in have_ids:
                continue
            url = (b.get("image") or {}).get("original", {}).get("url") or (b.get("source") or {}).get("url")
            if not url:
                continue
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            try:
                blob = dl(url)
            except Exception:
                continue
            if len(blob) < 2500:
                continue
            h = hashlib.md5(blob).hexdigest()
            if h in hashes:
                continue
            hashes.add(h)
            title = real_title(b)
            name = slug_name(title or f"grid-extra-{b['id']}", taken)
            open(os.path.join(IMG, name + ext), "wb").write(blob)
            src = ext_source(b)
            items.append({
                "id": bid,
                "title": title or "",
                "needs_name": title is None,
                "spectrum": None, "spectrum_rank": None,
                "category": guess_cat(" ".join(filter(None, [title, b.get("description")]))),
                "on_arena_board": True,
                "arena_channel": slug,
                "source": "arena",
                "status": "collected",
                "file": "images/" + name + ext,
                "source_url": src,
                "source_label": host(src),
                "arena_block_url": f"https://www.are.na/block/{b['id']}",
                "arena_image_url": url,
                "archive_links": [],
                "color": None,
                "notes": (b.get("description") or "").strip(),
            })
            have_ids.add(bid)
            added += 1
            if added % 15 == 0:
                _save(doc); print(f"  +{added}")
            time.sleep(0.15)

    _save(doc)
    named = sum(1 for i in items if not i.get("needs_name"))
    print(f"\nadded {added}. total {len(items)}  ({named} named, {len(items)-named} need a name)")


def _save(doc):
    items = doc["items"]
    c = sum(1 for i in items if i.get("status") == "collected")
    doc["meta"].update(total=len(items), collected=c, needed=len(items) - c)
    tmp = MF + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MF)


if __name__ == "__main__":
    main()
