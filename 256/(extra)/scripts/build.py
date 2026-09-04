#!/usr/bin/env python3
"""
build.py  ---  256 collection builder / importer

What it does
------------
1. Parses data/concepts.txt  -> the 400-item "order -> chaos" spine
   (spectrum band + rank come from the numbered position, exactly as Keyaa wrote it)
2. Reads   data/arena_raw.json -> the 66 images saved on the Are.na channel
   downloads each one into images/  and records its ORIGINAL source link
3. Keyword-maps every item into one of 10 theme folders
4. Writes  data/collection.json  --- the single manifest the CMS reads

It is MERGE-SAFE. Run it as many times as you want. Anything you change inside
the CMS (spectrum re-sorts, folder moves, colour tags, notes, uploaded images)
is keyed by id and preserved on the next build.

Usage
-----
    python3 build.py                # build / refresh, download missing arena images
    python3 build.py --refetch      # re-pull the channel JSON from are.na first
    python3 build.py --no-download  # rebuild manifest only, skip image downloads
"""

import json, os, re, sys, time, urllib.request, urllib.parse

ROOT   = os.path.dirname(os.path.abspath(__file__))
DATA   = os.path.join(ROOT, "data")
IMAGES = os.path.join(ROOT, "images")
CONCEPTS_TXT = os.path.join(DATA, "concepts.txt")
ARENA_RAW    = os.path.join(DATA, "arena_raw.json")
COLLECTION   = os.path.join(DATA, "collection.json")

ARENA_SLUG = "two-five-six-zp015cq1v2k"
ARENA_API  = "https://api.are.na/v2/channels/%s/contents?per=100&direction=desc" % ARENA_SLUG

# --------------------------------------------------------------------------
# 1. THEME TAXONOMY  --  the 10 folders, from Keyaa's second list
# --------------------------------------------------------------------------
CATEGORIES = [
    "Streets & public space",
    "Transportation",
    "Schools & offices",
    "Stores & commerce",
    "Food & kitchens",
    "Home & objects",
    "People & gatherings",
    "Sports & recreation",
    "Nature, farming & landscape",
    "Industrial & technical",
    "Abstract & image-grids",
]

# phrase -> category. Comma-separated phrases; first category with a hit wins,
# tested in this order. Phrases are matched as substrings (hyphens = spaces).
KEYWORD_MAP = [
    ("Abstract & image-grids",
     "quilt, textile, patchwork, woven, weave, basket weave, collage, mosaic, "
     "pixel, pixelated, portrait, a face, facial features, eyes collected, "
     "optical pattern, sol lewitt, lewitt, dot matrix, dot-matrix, heat map, "
     "heat-map, tetris, recombined, typography, letters scattered, handwriting, "
     "expressive marks, distorted into, rotated inside, square field, "
     "invisible grid, nested squares, obscured by fog, into darkness, "
     "three dimensions, colored-dot, colored dot, strips woven, symbol missing, "
     "repeated-symbol, contact sheet, photo grid, recombined into tiles, "
     "landscape cut apart, bodies folded, individual boxes, individual cells, "
     "grid folding, grid cut open, grid with one, grid interrupted, "
     "grid reflected, grid obscured, grid disappearing, film strip, film frame, "
     "contact sheet, typeface specimen, transit-design, transit design, "
     "registration and measurement, specification sheet, camera typology, "
     "typology, color chart, colour chart, color-checker, colour-checker, "
     "color checker, cassette tape, rows of keys, keys organized, wire sculpture, "
     "fabric stretched, structure invaded, invaded by soft, hand-drawn, "
     "hand drawn, diagonal stripe, perfectly repeated, loose grid, "
     "blocks clustering, glowing squares, blocks of color, newspaper column, "
     "measurement lines, overwritten by, almost forms a face"),
    ("Transportation",
     "parking, garage, dealership, car, cars, runway, tollbooth, toll, marina, "
     "boat, ferry, railway, rail track, sleeper, train, subway, carriage, bus, "
     "bike, bicycle, scooter, motorcycle, taxi, boarding gate, baggage, luggage, "
     "suitcase, airport, airplane, aircraft, shipping container, container, "
     "shipping, port container, depot, highway lane, commuter, peloton, cyclist, "
     "traffic"),
    ("Sports & recreation",
     "tennis, basketball, volleyball, soccer, football, baseball, swimmer, "
     "swimming, pool lane, runner, running, track lane, bowling, climbing hold, "
     "climbing wall, chess, scrabble, bingo, foosball, stadium, bleacher, "
     "spin bike, spin-bike, spectator, wimbledon, golf, gym, barre, ballet, "
     "yard line"),
    ("Food & kitchens",
     "kitchen, oven, stove, cooling rack, baking, muffin tin, ice-cube, ice cube, "
     "chocolate, bento, sushi, dumpling, cookie, cupcake, bread, bakery, loaf, "
     "wine rack, spice, cutlery, dish-drying, dish drying, fridge, refrigerator, "
     "freezer, pantry, produce, fruit, market crate, egg, milk carton, yogurt, "
     "yoghurt, cafeteria, banquet, restaurant, place setting, place-setting, "
     "food-delivery, food delivery, grocery product, tea plantation"),
    ("Stores & commerce",
     "supermarket, grocery, shelf, shelves, canned goods, cereal, bottled drink, "
     "vending, pharmacy, pill, blister, clothing, clothes, shirt, shoe, "
     "sunglasses, jewelry, jewellery, lipstick, nail-polish, nail polish, "
     "hardware, paint-swatch, paint swatch, pantone, swatch, tile sample, "
     "tile-sample, fabric swatch, vinyl record, bookstore, magazine, laundromat, "
     "shopping cart, shopping-cart, price label, sale sticker, pallet, warehouse, "
     "checkout, retail rack, product display, display case, shopping basket, "
     "crates piled, crate, market crate"),
    ("Schools & offices",
     "classroom, desk, lecture, library, bookshelf, book, locker, cubby, cubbie, "
     "computer-lab, computer lab, cubicle, conference, co-working, filing "
     "cabinet, mailroom, pigeonhole, ceiling panel, fluorescent, blind, "
     "bulletin, planning wall, calendar, spreadsheet, keyboard, keypad, "
     "organizer, notebook, post-it, name tag, id card, printer, archive, "
     "museum-storage, museum storage, blueprint, floor plan, floor-plan"),
    ("People & gatherings",
     "people, person, crowd, audience, graduation, orchestra, choir, marching, "
     "military, parade, protest, protester, dancer, formation, congregation, "
     "pew, queue, waiting, seated, student, class photograph, worker, chef, "
     "barbershop, passengers, bodies, body, group exercise"),
    ("Nature, farming & landscape",
     "crop, field, vineyard, orchard, rice paddy, tea, plantation, garden, "
     "greenhouse, nursery, seedling, flower bed, hedge, maze, irrigation, hay "
     "bale, timber, fishing net, honeycomb, spiderweb, spider web, leaf, vein, "
     "pinecone, sunflower, corn kernel, bark, cracked earth, salt flat, rock "
     "formation, beach umbrella, beach chair, campsite, cemetery, headstone, "
     "plant, ivy, weed, bird, cloud, landscape, settlement, agricultural, "
     "footprints, rice padd, compound eye, seedling, crop row"),
    ("Industrial & technical",
     "solar panel, electrical substation, power-line, power line, server rack, "
     "circuit board, ventilation, vent, grille, led screen, led panel, "
     "surveillance, monitor, factory, assembly line, conveyor, pipe, cable, "
     "rebar, cinder block, cinder-block, cinderblock, drainage grate, elevator "
     "button, intercom, mailbox, safety-deposit, safety deposit, qr code, "
     "barcode, app icon, browser tab, desktop, glitch, scaffolding, "
     "construction, pegboard, perforated, screens scattered, dark installation, "
     "installation, television screen, wall of television"),
    ("Home & objects",
     "bathroom, shower, floorboard, parquet, rug, tatami, yoga mat, bed frame, "
     "blanket, windowpane, venetian, shoe rack, coat hook, coats hanging, "
     "closet, photo wall, family photograph, framed picture, light "
     "switch, outlet, radiator, air conditioner, air-conditioning, air "
     "conditioning, speaker grille, remote, board game, board-game, curtain, "
     "satellite dish, tile, tiled, graph paper, toilet-paper, toilet paper, "
     "modular shelving, ice-cube tray"),
    ("Streets & public space",
     "sidewalk, paving, slab, brick, cobblestone, crosswalk, road-lane, road "
     "lane, street map, city block, chain-link, chainlink, chain link, fence, "
     "mesh, wire grid, wire mesh, railing, newsstand, market stall, food-truck, "
     "food truck, facade, fire escape, glass-block, glass block, "
     "curtain-wall, curtain wall, glass office, glass partition, building, "
     "manhole, storm drain, storm-drain, bench, street "
     "tree, tree guard, traffic cone, barrier, hotel window, window, balcony, "
     "apartment, boarded, tiled station, poster, flyer, demolition"),
]

def categorise(text):
    t = " " + text.lower().replace("-", " ") + " "
    for cat, phrases in KEYWORD_MAP:
        for ph in phrases.split(","):
            k = ph.strip().replace("-", " ")
            if k and k in t:
                return cat
    return "Home & objects"   # rare fallback

# --------------------------------------------------------------------------
# 2. ARCHIVE SEARCH LINKS  --  where a *legit* source image can be found
# --------------------------------------------------------------------------
def archive_links(title):
    q = urllib.parse.quote_plus(re.sub(r"[^a-zA-Z0-9 ]", "", title).strip())
    return [
        {"label": "NYPL Digital Collections",
         "url": "https://digitalcollections.nypl.org/search/index?keywords=" + q},
        {"label": "Library of Congress (photos)",
         "url": "https://www.loc.gov/photos/?q=" + q + "&fa=access-restricted:false"},
        {"label": "Wikimedia Commons",
         "url": "https://commons.wikimedia.org/w/index.php?search=" + q +
                "&title=Special:MediaSearch&type=image"},
        {"label": "Flickr (Creative Commons)",
         "url": "https://www.flickr.com/search/?text=" + q +
                "&license=2%2C3%2C4%2C5%2C6%2C9"},
        {"label": "Unsplash",
         "url": "https://unsplash.com/s/photos/" + q.replace("+", "-")},
    ]

# --------------------------------------------------------------------------
# 3. PARSE THE 400-ITEM SPINE
# --------------------------------------------------------------------------
SPECTRUM_LABEL = {
    "order":     "1 - Order (clear, controlled grids)",
    "inhabited": "2 - Inhabited (the grid gains variation)",
    "pressure":  "3 - Under pressure (order and chaos together)",
}

def parse_concepts():
    items, band = [], "order"
    with open(CONCEPTS_TXT, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re.match(r"#\s*SPECTRUM:\s*(\w+)", line)
            if m:
                band = m.group(1).strip()
                continue
            m = re.match(r"^(\d+)\.\s+(.*?)\s*$", line)
            if not m:
                continue
            rank = int(m.group(1))
            text = m.group(2)
            arena_star = text.endswith("★")
            text = text.rstrip("★ ").strip()
            items.append({
                "id": "concept-%03d" % rank,
                "title": text,
                "spectrum": band,
                "spectrum_rank": rank,
                "category": categorise(text),
                "on_arena_board": arena_star,
                "source": "concept-list",
                "status": "needed",
                "file": None,
                "source_url": None,
                "source_label": None,
                "arena_block_url": None,
                "archive_links": archive_links(text),
                "color": None,
                "notes": "",
            })
    return items

# --------------------------------------------------------------------------
# 4. ARENA CHANNEL -> entries (+ image download)
# --------------------------------------------------------------------------
def load_arena_raw(refetch):
    if refetch or not os.path.exists(ARENA_RAW):
        print("  fetching channel JSON from are.na ...")
        req = urllib.request.Request(ARENA_API, headers={"User-Agent": "256-cms/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
        with open(ARENA_RAW, "wb") as fh:
            fh.write(raw)
    return json.load(open(ARENA_RAW, encoding="utf-8"))

def clean_ext(url):
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".bmp") else ".jpg"

def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "256-cms/1.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    with open(dest, "wb") as fh:
        fh.write(data)
    return len(data)

def parse_arena(raw, do_download):
    blocks = raw.get("contents", raw if isinstance(raw, list) else [])
    entries = []
    for b in blocks:
        if b.get("class") != "Image":
            continue
        bid  = b.get("id")
        img  = (b.get("image") or {})
        orig = (img.get("original") or {}).get("url") or (img.get("display") or {}).get("url")
        if not orig:
            continue
        src  = (b.get("source") or {})
        src_url = src.get("url")
        # best available "original source": explicit source, else provider page, else the arena CDN file
        provider = (src.get("provider") or {}).get("name")
        raw_title = (b.get("title") or "").strip()
        title = re.sub(r"\s+", " ", raw_title)[:120] or ("Are.na block %s" % bid)

        ext  = clean_ext(orig.split("?")[0])
        fname = "arena-%s%s" % (bid, ext)
        fpath = os.path.join(IMAGES, fname)

        if do_download and not os.path.exists(fpath):
            try:
                n = download(orig, fpath)
                print("    downloaded %-22s %6.0f kB" % (fname, n / 1024))
                time.sleep(0.25)
            except Exception as e:
                print("    !! failed %s : %s" % (fname, e))
                fpath = None

        entries.append({
            "id": "arena-%s" % bid,
            "title": title,
            "spectrum": None,          # <-- you sort these in class; that's the assignment
            "spectrum_rank": None,
            "category": categorise(title) if raw_title else None,
            "on_arena_board": True,
            "source": "arena",
            "status": "collected" if (fpath and os.path.exists(fpath)) else "needed",
            "file": ("images/" + fname) if (fpath and os.path.exists(fpath)) else None,
            "source_url": src_url or orig,
            "source_label": provider or (urllib.parse.urlparse(src_url).netloc if src_url else "are.na CDN"),
            "arena_block_url": "https://www.are.na/block/%s" % bid,
            "arena_image_url": orig,
            "archive_links": [],
            "color": None,
            "notes": "",
        })
    return entries

# --------------------------------------------------------------------------
# 5. MERGE  --  keep everything the CMS changed
# --------------------------------------------------------------------------
KEEP_IF_SET = ("spectrum", "spectrum_rank", "category", "status", "color",
               "notes", "file", "source_url", "source_label")

def merge(fresh, old_by_id):
    out = []
    for item in fresh:
        prev = old_by_id.get(item["id"])
        if prev:
            for k in KEEP_IF_SET:
                if prev.get(k) not in (None, "", []):
                    item[k] = prev[k]
            if prev.get("user_edited"):
                item["user_edited"] = True
        out.append(item)
    # keep purely user-added rows (images uploaded through the CMS)
    fresh_ids = {i["id"] for i in out}
    for pid, prev in old_by_id.items():
        if pid not in fresh_ids and prev.get("source") == "upload":
            out.append(prev)
    return out

# --------------------------------------------------------------------------
def main():
    refetch     = "--refetch" in sys.argv
    do_download = "--no-download" not in sys.argv

    old_by_id = {}
    if os.path.exists(COLLECTION):
        try:
            for it in json.load(open(COLLECTION, encoding="utf-8"))["items"]:
                old_by_id[it["id"]] = it
        except Exception as e:
            print("  (could not read existing collection.json: %s)" % e)

    print("[1/3] parsing 400-item spine ...")
    concepts = parse_concepts()
    print("      %d concepts" % len(concepts))

    print("[2/3] importing Are.na channel ...")
    arena = parse_arena(load_arena_raw(refetch), do_download)
    print("      %d image blocks" % len(arena))

    print("[3/3] merging + writing manifest ...")
    items = merge(concepts + arena, old_by_id)

    # stable order: spectrum spine first (by rank), then arena (unsorted) at the end
    order = {"order": 0, "inhabited": 1, "pressure": 2, None: 9}
    items.sort(key=lambda x: (order.get(x["spectrum"], 9), x["spectrum_rank"] or 9999, x["id"]))

    collected = sum(1 for i in items if i["status"] == "collected")
    payload = {
        "meta": {
            "title": "256 --- grids from order to chaos",
            "channel": "https://www.are.na/keyaa-kapadia/two-five-six-zp015cq1v2k",
            "built": time.strftime("%Y-%m-%d %H:%M"),
            "total": len(items),
            "collected": collected,
            "needed": len(items) - collected,
            "categories": CATEGORIES,
            "spectrum_labels": SPECTRUM_LABEL,
        },
        "items": items,
    }
    with open(COLLECTION, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print("\n  wrote data/collection.json")
    print("  %d items total  |  %d collected  |  %d still needed"
          % (len(items), collected, len(items) - collected))
    from collections import Counter
    print("  by folder:")
    for cat, n in Counter(i["category"] for i in items if i["category"]).most_common():
        print("     %-32s %3d" % (cat, n))

if __name__ == "__main__":
    main()
