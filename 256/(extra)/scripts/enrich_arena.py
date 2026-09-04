#!/usr/bin/env python3
"""
enrich_arena.py — give the 66 Are.na images real names.

Each Are.na block came in with a junk filename for a title ("tumblr_ab12…jpg").
This replaces that with a plain description of what the picture shows, keeps the
old filename in `original_filename`, adds an `aka` list of alternative names
(drawn from the order→chaos vocabulary so search finds them), sets a sensible
subject folder, and gives an opening spectrum placement (Keyaa can re-drag any
card in one click).

Also clears a handful of weak auto-sourced concept images back to "needs an
image" so they can be re-sourced by hand.

    python3 enrich_arena.py
"""

import json, os

MF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "collection.json")
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# id -> (title, folder, spectrum, [aka...])
ARENA = {
 "arena-1254341":  ("Painted wire grid warping over a tiled wall", "Abstract & image-grids", "pressure",
    ["bent wire mesh", "a grid being pulled out of shape", "distorted grid over tile"]),
 "arena-1254367":  ("Mass group portrait — hundreds of faces in a grid", "People & gatherings", "inhabited",
    ["a crowd treated as hundreds of individual cells", "students posing for a class photograph", "rows of people"]),
 "arena-1887985":  ("Typology grid of disposable film cameras", "Abstract & image-grids", "order",
    ["camera typology collections", "photo archives arranged as thumbnails", "contact sheet"]),
 "arena-2197625":  ("Tennis crowd in tiered seating (Wimbledon)", "Sports & recreation", "inhabited",
    ["Wimbledon spectators filling tiered seats", "stadium crowds", "bleachers with scattered spectators"]),
 "arena-4005902":  ("Honeycomb with a patch of dark cells", "Nature, farming & landscape", "inhabited",
    ["honeycomb with a few dark or empty cells", "a honeycomb with damaged cells", "hexagonal grid"]),
 "arena-4161089":  ("Dancer on a ledge against a gridded concert-hall wall", "People & gatherings", "pressure",
    ["a person exceeding the boundaries of their box", "a gridded facade", "figure against a grid"]),
 "arena-4423603":  ("Cross-stitch floral pattern on a graph-paper grid", "Abstract & image-grids", "order",
    ["a floral textile built over square modules", "cross-stitch chart", "needlepoint pattern on graph paper"]),
 "arena-4444075":  ("Grid of collected eyes, one cell broken", "Abstract & image-grids", "inhabited",
    ["eyes collected and recombined into a grid", "facial features placed in mismatched cells", "a perfect matrix with one symbol missing"]),
 "arena-5202985":  ("Aerial-collage animation ('Someday', Páraic Mc Gloughlin)", "Abstract & image-grids", "pressure",
    ["a landscape cut apart and recombined into tiles", "aerial city blocks", "video collage"]),
 "arena-6108639":  ("Hand reaching through a chain-link fence", "Streets & public space", "pressure",
    ["a hand reaching through a chain-link fence", "bent chain-link fencing", "grid under pressure"]),
 "arena-6149628":  ("Typology grid of old keys on a dark ground", "Abstract & image-grids", "order",
    ["rows of keys organized by type", "key typology", "collection arranged as a grid"]),
 "arena-6512365":  ("Nine-cell grid of pixelated body fragments", "Abstract & image-grids", "pressure",
    ["bodies folded inside individual boxes", "a portrait breaking into pixel blocks", "facial features in mismatched cells"]),
 "arena-13064669": ("QR code", "Abstract & image-grids", "order",
    ["QR codes", "barcode", "a black-and-white matrix", "data grid"]),
 "arena-13075470": ("Sol LeWitt modular cube grid in a gallery corner", "Abstract & image-grids", "pressure",
    ["a Sol LeWitt-like corner grid becoming three-dimensional", "a grid folding into three dimensions", "modular cubes"]),
 "arena-14957945": ("Nested rectangular frames receding into depth (Taufenbach & Pourtout)", "Abstract & image-grids", "pressure",
    ["nested squares with changing colors", "a grid folding into three dimensions", "concentric frames"]),
 "arena-15610283": ("Grid of sky tiles with swifts crossing the divisions", "Nature, farming & landscape", "inhabited",
    ["birds crossing the divisions of a photo grid", "clouds split across photographic contact sheets", "gradient sky tiles"]),
 "arena-23557368": ("Gego — wire grid drawing collapsing at one corner", "Abstract & image-grids", "pressure",
    ["a grid cut open in one corner", "a wire grid being pulled out of shape", "a grid folding into three dimensions"]),
 "arena-30038245": ("Scattered photo thumbnails drifting on black", "Abstract & image-grids", "pressure",
    ["photographs organized into cells of different sizes", "screens scattered across a dark installation", "a grid disappearing into darkness"]),
 "arena-38135349": ("Landscape shredded and recombined into tiles", "Nature, farming & landscape", "pressure",
    ["a landscape cut apart and recombined into tiles", "an aerial settlement that resembles an overwhelming maze", "collage of photographic rectangles"]),
 "arena-38548882": ("Colour-dot matrix over a close-up of an eye", "Abstract & image-grids", "inhabited",
    ["a colored-dot matrix shifting between circles and squares", "a repeated-symbol chart with changing colors", "dots over a face"]),
 "arena-40003667": ("Red flowers seen through ribbed gridded glass", "Nature, farming & landscape", "inhabited",
    ["flowers seen through gridded glass", "reflections breaking a glass grid", "image fractured by glass tiles"]),
 "arena-41612615": ("Wool patchwork quilt with scattered orange squares", "Abstract & image-grids", "inhabited",
    ["a quilt with irregular patches", "a woven textile with bright blocks breaking a neutral field", "a patchwork textile using mismatched fabrics"]),
 "arena-41707931": ("Portion of a beetle's eye — compound-eye cells", "Nature, farming & landscape", "order",
    ["beetle compound eyes", "honeycomb cells", "a hexagonal grid", "microscope plate"]),
 "arena-41726187": ("Tumbling-blocks signature quilt (Adeline Harris Spears, 1863)", "Abstract & image-grids", "inhabited",
    ["a signature quilt made from repeated cubes", "tumbling blocks", "an isometric cube grid"]),
 "arena-41775954": ("Transit-symbol construction drawing on a spec grid (NJ Transit)", "Abstract & image-grids", "order",
    ["transit-design specification sheets", "registration and measurement sheets", "a logo on a construction grid"]),
 "arena-41792036": ("Hand-painted watercolour swatch chart", "Abstract & image-grids", "order",
    ["watercolour swatch charts", "paint-swatch walls", "Pantone charts", "colour-checker cards"]),
 "arena-41792038": ("Apartment windows lit differently at night, figures inside", "Streets & public space", "inhabited",
    ["windows lit differently across an apartment building", "people visible through separate apartment windows", "apartment windows with people inside"]),
 "arena-41792057": ("Grid of cyanotype flower tiles", "Abstract & image-grids", "order",
    ["a floral textile built over square modules", "botanical photogram grid", "blueprint flowers", "tile samples"]),
 "arena-41792060": ("Grid of gold panels stamped with fragmented letters", "Abstract & image-grids", "pressure",
    ["letters scattered across an underlying grid", "typography escaping its columns", "a perfect matrix with one symbol missing"]),
 "arena-41807324": ("Loose grid of letterpress specimen cards", "Abstract & image-grids", "pressure",
    ["typeface specimen charts", "letters scattered across an underlying grid", "specimen slips pinned to a wall"]),
 "arena-41807893": ("Grid of sixteen cloud photographs", "Nature, farming & landscape", "inhabited",
    ["clouds split across photographic contact sheets", "a landscape cut apart into tiles", "contact sheet of skies"]),
 "arena-41807905": ("Contact sheet of a coastline at dusk", "Nature, farming & landscape", "inhabited",
    ["a landscape cut apart and recombined into tiles", "photographs organized into cells", "seascape studies in a grid"]),
 "arena-41807910": ("Wall of small sky paintings on ledges", "Abstract & image-grids", "inhabited",
    ["a wall of television screens showing different footage", "clouds split across a grid", "panel grid of skies"]),
 "arena-41854274": ("Aerial patchwork of terraced fields with one tree", "Nature, farming & landscape", "pressure",
    ["agricultural plots with irregular boundaries", "crop fields seen from above", "any rigid grid with one living thing refusing to follow it"]),
 "arena-41854279": ("Warehouse window grid with mismatched broken panes", "Industrial & technical", "pressure",
    ["broken windows across a regular facade", "missing tiles in a tiled wall", "mismatched replacement tiles"]),
 "arena-41854282": ("Apartment tower at night, every window different", "Streets & public space", "inhabited",
    ["windows lit differently across an apartment building", "apartment windows with irregular lights", "a gridded facade at night"]),
 "arena-44141683": ("One figure posed in each box of a stacked grid", "People & gatherings", "pressure",
    ["bodies folded inside individual boxes", "a person exceeding the boundaries of their box", "figures in cubes"]),
 "arena-44141738": ("Restaurant order ticket — ruled grid filled by hand", "Food & kitchens", "pressure",
    ["restaurant order tickets", "spreadsheet cells containing inconsistent amounts of text", "a ruled form filled in by hand"]),
 "arena-44141769": ("Portrait built from a quadtree of subdividing squares", "Abstract & image-grids", "pressure",
    ["a portrait breaking into pixel blocks", "a face reconstructed through square fragments", "an adaptive grid portrait"]),
 "arena-44436468": ("Blueprint grid of cassette tapes, brick-laid", "Abstract & image-grids", "inhabited",
    ["cassette tapes organized in rows", "cassette tapes arranged like bricks but varying in size", "a Tetris board with gaps"]),
 "arena-44436469": ("Wall of hundreds of sunset photographs", "Abstract & image-grids", "inhabited",
    ["sunsets through windows", "photographs organized into cells of different sizes", "a wall of screens showing different footage"]),
 "arena-44751831": ("Halftone dot field with a band of angled white bars", "Abstract & image-grids", "pressure",
    ["a black-and-white grid invaded by diagonal stripes", "a dot matrix", "rectangles rotated inside a square field"]),
 "arena-45035720": ("Colour-palette grid over a lotus photo", "Abstract & image-grids", "inhabited",
    ["a color chart stained by use", "blocks of color placed inside photographic imagery", "paint-swatch displays"]),
 "arena-45035740": ("Birthday-colour calendar grid (one swatch per date)", "Abstract & image-grids", "order",
    ["calendar pages", "Pantone charts", "a colour chart", "spreadsheet cells"]),
 "arena-45123567": ("Grid of scuffed black-and-white geometric panels", "Abstract & image-grids", "pressure",
    ["squares scattered over an invisible grid", "rectangles rotated inside a square field", "a repeated-symbol chart"]),
 "arena-45123570": ("Stacked toilet-paper rolls forming a loose grid of holes", "Industrial & technical", "pressure",
    ["a pile of toilet-paper rolls forming a loose grid", "rows of rough circles", "warehouse pallets of rolls"]),
 "arena-45333995": ("Vasarely — scattered paper squares over a field (1940)", "Abstract & image-grids", "pressure",
    ["squares scattered over an invisible grid", "rectangles rotated inside a square field", "a black-and-white grid invaded"]),
 "arena-45333999": ("Chryssa — brushed grid over ruled 'window' cells ('City')", "Abstract & image-grids", "pressure",
    ["a grid overwritten by handwriting", "newspaper columns crossed by hand-drawn lines", "typography escaping its columns"]),
 "arena-45334000": ("Woven-textile study in blocks on graph paper (Bauhaus)", "Abstract & image-grids", "order",
    ["a woven textile with bright blocks breaking a neutral field", "a weaving draft on graph paper", "textile colour study"]),
 "arena-45334004": ("Joe Tilson — grid of eyes with cells painted over ('A–Z Box')", "Abstract & image-grids", "inhabited",
    ["eyes collected and recombined into a grid", "facial features placed in mismatched cells", "a repeated-symbol chart with changing colors"]),
 "arena-45428965": ("Girard fabric design — colour-cycling clover grid (Herman Miller '625')", "Abstract & image-grids", "order",
    ["a colored-dot matrix shifting between circles and squares", "repeated squares distorted into an optical pattern", "a fabric swatch"]),
 "arena-45781862": ("Woven paper strips with coloured dots at the crossings", "Abstract & image-grids", "order",
    ["strips woven across one another", "a woven mat with interrupted colors", "basket weave"]),
 "arena-45906951": ("Cross-stitched heat-map / diffraction pattern", "Abstract & image-grids", "inhabited",
    ["pixelated heat maps with irregular concentrations", "a repeated-symbol chart with changing colors", "an embroidered data grid"]),
 "arena-46076090": ("Grid of Albers 'Homage to the Square' panels", "Abstract & image-grids", "inhabited",
    ["nested squares with changing colors", "a colored-dot matrix", "repeated squares"]),
 "arena-46443789": ("Endless isometric grid of office cubicles", "Schools & offices", "inhabited",
    ["office cubicles", "a crowd treated as hundreds of individual cells", "an aerial settlement that resembles a maze"]),
 "arena-46443794": ("Grid of rust-stained paper panels", "Abstract & image-grids", "inhabited",
    ["a color chart stained by use", "a grid obscured by fog", "stained modular panels"]),
 "arena-46443795": ("Storm landscape in painted tiles with radiating gold rays", "Abstract & image-grids", "pressure",
    ["light passing through perforated screens", "a landscape cut apart and recombined into tiles", "a grid interrupted by a circle"]),
 "arena-46443805": ("Grid of folded black packets on a pegboard frame", "Abstract & image-grids", "pressure",
    ["a regular structure invaded by soft materials", "tool pegboards", "a grid folding into three dimensions"]),
 "arena-47056437": ("Vasarely — dot-in-square op-art grid (rainbow field)", "Abstract & image-grids", "inhabited",
    ["a colored-dot matrix shifting between circles and squares", "repeated squares distorted into an optical pattern", "op art dot grid"]),
 "arena-47056444": ("Improvised patchwork quilt with yarn ties", "Abstract & image-grids", "inhabited",
    ["a patchwork textile using mismatched fabrics", "a quilt with irregular patches", "a signature quilt"]),
 "arena-47056445": ("Painted grid columns filled to wavy heights (a drawn wave)", "Abstract & image-grids", "pressure",
    ["a grid with one row slipping sideways", "a repeated-symbol chart", "columns of varying height"]),
 "arena-47728564": ("Forks interlocking tines-to-tines into a grid", "Food & kitchens", "inhabited",
    ["forks interlocking into a distorted grid", "cutlery organizers", "an interlocked metal grid"]),
 "arena-48107668": ("Glowing tiles scattering across dark pavement", "Abstract & image-grids", "pressure",
    ["glowing squares spreading across dark pavement", "blocks clustering unevenly", "a Tetris board with gaps"]),
 "arena-48107671": ("Wall of small mirrors each catching a fragment of the street", "Abstract & image-grids", "pressure",
    ["reflections breaking a glass-building grid", "a person moving behind translucent windows", "a crowd seen through fencing"]),
 "arena-48107672": ("Improvised strip quilt forming a symmetrical figure", "Abstract & image-grids", "inhabited",
    ["a geometric quilt that almost forms a face", "a patchwork textile using mismatched fabrics", "strips woven across one another"]),
 "arena-48226790": ("Portrait shattered into a brick grid of photo fragments", "Abstract & image-grids", "pressure",
    ["a portrait breaking into pixel blocks", "a face reconstructed through square fragments", "a glitch portrait grid"]),
}

# weak auto-sourced concept images to send back to "needs an image"
CLEAR = ["concept-007", "concept-013", "concept-029", "concept-037", "concept-229"]


def main():
    doc = json.load(open(MF, encoding="utf-8"))
    by_id = {it["id"]: it for it in doc["items"]}

    named = 0
    for _id, (title, folder, spectrum, aka) in ARENA.items():
        it = by_id.get(_id)
        if not it:
            continue
        if it.get("title") and "original_filename" not in it:
            it["original_filename"] = it["title"]
        it["title"] = title
        it["category"] = folder
        it["aka"] = aka
        it["spectrum"] = spectrum
        named += 1

    cleared = 0
    for _id in CLEAR:
        it = by_id.get(_id)
        if not it:
            continue
        f = it.get("file")
        if f and f.startswith("images/"):
            p = os.path.join(os.path.dirname(MF), "..", f)
            if os.path.exists(p):
                os.remove(p)
        it["file"] = None
        it["status"] = "needed"
        it["source_url"] = None
        it["source_label"] = None
        it.pop("image_credit", None)
        it["color"] = None
        note = (it.get("notes") or "")
        if "via Wikimedia Commons" in note or "Wikimedia Commons)" in note:
            it["notes"] = ""
        cleared += 1

    # refresh counts
    items = doc["items"]
    coll = sum(1 for i in items if i.get("status") == "collected")
    doc["meta"].update(total=len(items), collected=coll, needed=len(items) - coll)

    tmp = MF + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MF)
    print(f"named {named} Are.na images; cleared {cleared} weak concept images")
    print(f"collected now {coll}/{len(items)}")


if __name__ == "__main__":
    main()
