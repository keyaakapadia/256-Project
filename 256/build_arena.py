#!/usr/bin/env python3
"""
build_arena.py — rebuild the collection from Are.na only.

Sources, in order:
  1. "Grids IRL: Order to Chaos"  (199 blocks) — the spectrum spine.
     Split by position: first third = Order, middle = Inhabited, last = Under pressure.
  2. "256"                        (80 blocks) — reference / designy grids, land Unsorted.

Every image is downloaded into images/.  De-duped by file content.
`source_url` is the block's external source when Are.na has one, otherwise the
Are.na block permalink.  Names come from a real block title when present, else
left blank for a visual naming pass.

    python3 build_arena.py
"""
import hashlib, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(ROOT, "images")
DATA = os.path.join(ROOT, "data")
MF = os.path.join(DATA, "collection.json")
UA = {"User-Agent": "256-thesis-cms/1.0 (kapak530@newschool.edu)"}

CHANNELS = [
    ("grids-irl-order-to-chaos", "grid", "spine"),
    ("two-five-six-zp015cq1v2k", "ref", "unsorted"),
]
CATS = ["Streets & public space", "Transportation", "Schools & offices", "Stores & commerce",
        "Food & kitchens", "Home & objects", "People & gatherings", "Sports & recreation",
        "Nature, farming & landscape", "Industrial & technical", "Abstract & image-grids"]
KW = {
 "Transportation": "car parking garage runway subway train rail bike bicycle taxi bus airport marina boat traffic tollbooth freight container dock",
 "Streets & public space": "street sidewalk crosswalk facade balcony fence scaffold fire escape building manhole cobble brick pavement",
 "Schools & offices": "desk locker classroom library cubicle office ceiling blind filing keyboard calendar spreadsheet lecture",
 "Stores & commerce": "supermarket shelf shop store aisle retail vending price label product refrigerator pharmacy magazine record",
 "Food & kitchens": "egg carton tray oven muffin cookie bread sushi bento kitchen fridge freezer spice bottle wine cafeteria restaurant",
 "Home & objects": "tile floor quilt blanket window screen blind shelf hook rug mat tatami photo frame switch outlet radiator vent",
 "People & gatherings": "people crowd audience choir orchestra graduation seat pew stadium bleacher class dancers marching queue protest",
 "Sports & recreation": "court tennis basketball soccer football pool lane track bowling gym weight treadmill chess scrabble bingo stadium",
 "Nature, farming & landscape": "field crop vineyard orchard paddy garden greenhouse hedge hay honeycomb spiderweb leaf pinecone bark salt beach cemetery",
 "Industrial & technical": "solar substation server circuit led factory conveyor pallet pipe pegboard rebar cinder drain elevator mailbox blister film",
}


def guess_cat(text):
    t = (text or "").lower()
    best, bs = "Abstract & image-grids", 0
    for c, kws in KW.items():
        s = sum(1 for k in kws.split() if k in t)
        if s > bs:
            bs, best = s, c
    return best


def real_title(b):
    for key in ("title", "generated_title"):
        v = (b.get(key) or "").strip()
        if v and not re.match(r"^(original_|tumblr_|image\.?|screenshot|screen[- ]shot|untitled|giphy|IMG[_-]|DSC|\d+[_-]|https?[:/])", v, re.I) \
           and not re.match(r"^[a-f0-9]{16,}$", v):
            return re.sub(r"\.(jpe?g|png|gif|webp)$", "", v, flags=re.I).strip()
    src = (b.get("source") or {}).get("title") or ""
    if src and not src.startswith("original_") and len(src) > 3:
        return src.strip()
    return None


def ext_source(b):
    u = (b.get("source") or {}).get("url") or ""
    if u and "cloudfront.net" not in u and "arena_images" not in u:
        return u
    return f"https://www.are.na/block/{b['id']}"


def dl(url, dest):
    r = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(r, timeout=120) as f:
        b = f.read()
    open(dest, "wb").write(b)
    return b


def slug(s, taken):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:58].strip("-") or "block"
    out, n = s, 2
    while out in taken:
        out = f"{s}-{n}"; n += 1
    taken.add(out)
    return out


def fetch_channel(slug_):
    out, page = [], 1
    while True:
        u = f"https://api.are.na/v2/channels/{slug_}/contents?per=100&page={page}"
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40))
        cs = d.get("contents") or []
        out += cs
        if len(cs) < 100:
            break
        page += 1; time.sleep(0.4)
    return out


def main():
    os.makedirs(IMG, exist_ok=True)
    prev = json.load(open(MF, encoding="utf-8")) if os.path.exists(MF) else {}

    items, seen_hash, taken = [], {}, set()
    for slug_, prefix, mode in CHANNELS:
        blocks = [b for b in fetch_channel(slug_) if b.get("class") == "Image"]
        print(f"{slug_}: {len(blocks)} image blocks")
        N = len(blocks)
        for pos, b in enumerate(blocks):
            img = (b.get("image") or {}).get("original", {}) or {}
            url = img.get("url") or (b.get("source") or {}).get("url")
            if not url:
                continue
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower() or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                ext = ".jpg"
            try:
                blob = dl(url, os.path.join(IMG, f".tmp{ext}"))
            except Exception as e:
                print("  ! dl", b["id"], e); continue
            h = hashlib.md5(blob).hexdigest()
            if h in seen_hash:
                os.remove(os.path.join(IMG, f".tmp{ext}"))
                continue
            title = real_title(b)
            name = slug(title or f"{prefix}-{pos+1:03d}", taken)
            os.replace(os.path.join(IMG, f".tmp{ext}"), os.path.join(IMG, name + ext))
            seen_hash[h] = name

            if mode == "spine":
                spec = "order" if pos < N/3 else ("inhabited" if pos < 2*N/3 else "pressure")
                rank = pos + 1
            else:
                spec, rank = None, None
            it = {
                "id": f"arena-{b['id']}",
                "title": title or "",
                "needs_name": title is None,
                "spectrum": spec,
                "spectrum_rank": rank,
                "category": guess_cat(" ".join(filter(None, [title, b.get("description")]))),
                "on_arena_board": True,
                "arena_channel": slug_,
                "source": "arena",
                "status": "collected",
                "file": "images/" + name + ext,
                "source_url": ext_source(b),
                "source_label": _host(ext_source(b)),
                "arena_block_url": f"https://www.are.na/block/{b['id']}",
                "arena_image_url": url,
                "archive_links": [],
                "color": None,
                "notes": (b.get("description") or "").strip(),
            }
            items.append(it)
            if (pos + 1) % 20 == 0:
                print(f"   {pos+1}/{N}")
            time.sleep(0.15)

    collected = len(items)
    doc = {
        "meta": {
            "title": "256 — grids from order to chaos (Are.na build)",
            "channels": [c[0] for c in CHANNELS],
            "built": time.strftime("%Y-%m-%d %H:%M"),
            "total": collected, "collected": collected, "needed": 0,
            "categories": CATS,
            "spectrum_labels": (prev.get("meta") or {}).get("spectrum_labels", {
                "order": "1 - Order (clear, controlled grids)",
                "inhabited": "2 - Inhabited (the grid gains variation)",
                "pressure": "3 - Under pressure (order and chaos together)",
            }),
        },
        "items": items,
    }
    tmp = MF + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MF)
    named = sum(1 for i in items if not i["needs_name"])
    print(f"\ncollection.json: {collected} images  ({named} named, {collected-named} need a name)")
    print("images on disk:", len([f for f in os.listdir(IMG) if not f.startswith('.')]))


def _host(u):
    try:
        n = urllib.parse.urlparse(u).netloc
        return "Are.na" if "are.na" in n else n[4:] if n.startswith("www.") else n
    except Exception:
        return "Are.na"


if __name__ == "__main__":
    main()
