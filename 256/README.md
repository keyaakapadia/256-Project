# 256 — a working archive of grids, order → chaos

A small content-management system for the 256 Part 1 collection. It holds every
image in one folder, keeps each image tied to its **original source link**, and
lets you re-sort the whole set three different ways without touching a
spreadsheet.

```
256/
├── index.html · style.css · app.js   the CMS (browser)
├── serve.py                          tiny local server + save API  (stdlib only)
├── build.py                          (re)builds the manifest from concepts.txt + Are.na
├── fetch_images.py                   sources a good image per item (Openverse → Commons)
├── enrich_titles.py                  adds `aka` alt-names to the concept items
├── enrich_arena.py                   names the 66 Are.na images + first spectrum pass
├── rename_files.py                   renames image files to describe the picture
├── fonts/                            Neue Montreal (bundled; used via @font-face)
├── data/
│   ├── concepts.txt                  your 400-item "order → chaos" list (edit freely)
│   ├── arena_raw.json                cached dump of the Are.na channel
│   └── collection.json               THE MANIFEST — every item, generated + your edits
└── images/                           every image, named for what it shows
                                        (e.g. gego-wire-grid-collapsing.jpg)
```

## Look

One typeface — **Neue Montreal** (bundled in `fonts/`, no web request) — on a
warm paper ground, one blue doing all the talking, square corners, hairline
rules, labels in a small tracked uppercase "system" voice. Same visual language
as the Thesis Journal. Light only. Colour is the 9-swatch **Saphinka palette**
(`--c0`…`--c8` in `style.css`).

## Naming & search

Every item carries its own title plus an **`aka`** list — the same subject
worded the way your second list (the subject-folder taxonomy) puts it, plus a
few plain synonyms. Search matches all of it, so "Empty parking spaces" also
turns up under *parking lot*, *cars*, *bays*. The drawer shows the alternatives
under the title. The 66 Are.na images were given plain descriptive titles (old
filenames kept in `original_filename`) and a starting spectrum placement.


## Two builds

The live collection (`data/collection.json` + `images/`) is now built **only from Are.na**:
`build_arena.py` pulls every image block from *Grids IRL: Order to Chaos* (the spectrum
spine, split into Order / Inhabited / Under-pressure by its channel position) and *256*
(reference grids), de-dupes by file content, names each from its block title where there is
one, and records the block's external source when Are.na has one — otherwise the Are.na
block permalink.

The earlier archive-sourced build is kept, not shown:
- `images(extra)/` — the ~450 Openverse / Wikimedia Commons images
- `data/collection(extra).json` — its manifest

To switch back: swap those two `(extra)` names with `images/` and `data/collection.json`.

## Run it

```bash
cd "Senior Year/Thesis/256"
python3 serve.py
```

Open **http://localhost:8256**. No install, no Node, no dependencies — it uses
only the Python standard library.

To rebuild the manifest after editing `concepts.txt`, or to re-pull the channel:

```bash
python3 build.py            # refresh, download any missing Are.na images
python3 build.py --refetch  # re-download the Are.na channel JSON first
```

`build.py` is **merge-safe**: anything you change in the CMS (spectrum re-sorts,
folder moves, colour tags, notes, images you add) is keyed by `id` and survives
every rebuild.

## What's already in it

| | count | notes |
|---|---|---|
| **Images collected** | 66 | every image on your [Are.na channel](https://www.are.na/keyaa-kapadia/two-five-six-zp015cq1v2k), downloaded into `images/`, each carrying its original `source_url` (and its Are.na block link) |
| **Concepts to source** | 400 | your numbered list, each a "specimen slip" card with a subject folder and five archive search links ready to click |
| **Total items** | 466 | |

### Sourcing the rest

`fetch_images.py` searches **Openverse** (Flickr / museum Creative-Commons
photography — the same realm as the Are.na picks) first, falls back to
**Wikimedia Commons**, scores the candidates for grid-ish / well-shot /
high-resolution, and downloads the winner into `images/` under a name that
describes the picture. It records the original page as `source_url` plus the
licence + author in an `image_credit` field.

```bash
python3 fetch_images.py                 # fill items that have no image
python3 fetch_images.py --replace-weak  # also redo the plain documentary
                                        #   shots from the first pass
python3 fetch_images.py --limit 30
```

Safe to stop / re-run (collected items skipped; manifest written every few
items). Matches are **automatic and uneven** — for everyday subjects the CC
pools just don't hold Sol-LeWitt-grade grid pictures. Treat these as a working
scaffold: open a card and **paste a URL** to drop in a better frame (it
downloads and re-records the source). Items with no match keep their five
hand-search links (**NYPL, Library of Congress, Wikimedia Commons, Flickr CC,
Unsplash**).

## The three organisations

1. **Spectrum — order → chaos.** One line, three stages: **1 Order** (the grid
   stated plainly) · **2 Inhabited** (the same grid, lived in) · **3 Under
   pressure** (order and chaos at once). Concept items follow their place in
   `concepts.txt`; the 66 Are.na images got a first placement from
   `enrich_arena.py` — re-drag any card in its editor.
2. **Folders — by subject.** Ten subject folders from your second list, plus
   *Abstract & image-grids* for the textile / collage / photo-grid references.
   Auto-assigned by keyword; fix any card in one click via its editor.
3. **Colour — by swatch.** The CMS reads each collected image on a canvas, pulls
   an average + a 5-swatch palette, and drops it into whichever of the nine
   **Saphinka** swatches it sits closest to — Olives Before Dinner, Blended
   Strawberries, Fresh Cut Wood, Day Old Snow, Jarred Deep Sea, Sky To A Bird,
   Horsing Around, Sunsets Through Windows, Ocean Wave Break. Override per item
   in the editor.

## Editing a card

Click any card. The drawer lets you set spectrum, folder and colour bucket, write
a note ("why this one / how it reads / where shot"), open the original source and
the archive links, and add an image by **pasting a URL** (downloaded server-side
into `images/`) or **uploading a file**. `+ new item` adds something that isn't
on either list.

## Files you'll hand in / present from

- `images/` — every image, filename = what it shows
- `data/collection.json` — the full catalogue: title + `aka`, source URL, source
  label, image credit + licence, spectrum, folder, colour palette, notes — for
  all 466 items
