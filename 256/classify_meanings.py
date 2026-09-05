#!/usr/bin/env python3
"""
classify_meanings.py — a fourth lens: not what a grid shows, but what it's
*for*. Assigns every item a primary `meaning` (and a `meaning2` when a
second reading is nearly as strong — a fence separates AND controls; a
street guides AND organizes).

    python3 classify_meanings.py

Order runs Organize -> Contain -> Separate -> Guide -> Measure -> Control ->
Repeat -> Play -> Break: roughly least to most disordered, so the Meaning
view can be read start to finish like the Spectrum view.
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.abspath(__file__))
MF = os.path.join(ROOT, "data", "collection.json")
BAKE = os.path.join(ROOT, "bake.py")

MEANINGS = ["organize", "contain", "separate", "guide", "measure",
            "control", "repeat", "play", "break"]

# strong phrase signals, checked first — most specific wins by score
PHRASE = {
 "organize": ["calendar","spreadsheet","shelf","shelves","shelving","filing","index","floor plan",
              "floor-plan","dashboard","wayfinding","listings","price label","product grid",
              "storage","pigeonhole","locker","folder","archive box","contents list","catalogue",
              "inventory","organiz"],
 "contain": ["window","windowpane","cage","pixel","box","boxes","blister","fridge","refrigerator",
             "freezer","mailbox","safety-deposit","cubby","carton","crate","bottle","jar","vending",
             "compartment","cell block","enclosure","packaging","bag","tray"],
 "separate": ["fence","fencing","palisade","chain-link","chain link","border","barrier","tile",
              "tiled","scaffold","sheeting","partition","divider","wall","gap","netting","railing",
              "hedge","curtain"],
 "guide": ["street","road","crosswalk","sidewalk","pavement","map","wayfinding","game board",
           "chessboard","chess","scrabble","bingo","board game","runway","track","lane","route",
           "path","transit","subway map","floor plan","staircase"],
 "measure": ["graph paper","ruler","chart","calibration","colour-checker","color-checker",
             "dither","dithering","registration","paper-size","scale","spectrometer","test chart",
             "colour chart","color chart","measurement","diagram","axonometric","blueprint",
             "specimen","typeface","weight list"],
 "control": ["surveillance","cctv","camera monitor","urban planning","aerial of","institutional",
             "identical cell","uniform","checkpoint","security","control room","command",
             "monitor wall","server rack","vr headset","panopticon","grid of screens","listings grid"],
 "repeat": ["textile","fabric","weave","woven","quilt","pattern","tessellation","facade","tiling",
            "mosaic","mass production","assembly line","conveyor","module","modular","repeated",
            "repetition","brick","cobblestone","honeycomb","stack of","rows of"],
 "play": ["game","toy","kinetic","colour-cycling","color-cycling","playful","arcade","typography",
          "experimental type","letters tumbling","letters rotated","'human'","'studio'","confetti",
          "vasarely","bridget riley","op-art","op art","optical","kusama","dot matrix","polka",
          "starburst","rainbow","glitch","psychedelic","dazzle"],
 "break": ["distort","warp","warped","bulging","broken","shatter","shattered","fragment","collapse",
           "collapsing","glitch","tumbling","escape","overlap","irregular","cracked","torn","ripped",
           "disrupted","folding into three dimensions","cut open","one row slipping","interference",
           "moiré","moire"],
}

CAT_FALLBACK = {
 "Streets & public space": "guide", "Transportation": "guide",
 "Schools & offices": "organize", "Stores & commerce": "organize",
 "Food & kitchens": "contain", "Home & objects": "repeat",
 "People & gatherings": "control", "Sports & recreation": "play",
 "Nature, farming & landscape": "repeat", "Industrial & technical": "control",
 "Op-art & moiré": "break", "Pattern & texture": "repeat",
 "Type & lettering": "play", "Animation": "play",
 "Abstract & image-grids": "play",
}
SPEC_FALLBACK = {"order": "organize", "inhabited": "contain", "pressure": "break"}


def score(text, phrases):
    return sum(1 for p in phrases if p in text)


def classify(it):
    text = " ".join(filter(None, [it.get("title"), it.get("notes"),
                                   " ".join(it.get("aka") or [])])).lower()
    scores = {m: score(text, ph) for m, ph in PHRASE.items()}
    ranked = sorted(MEANINGS, key=lambda m: (-scores[m], MEANINGS.index(m)))
    top, second = ranked[0], ranked[1]
    if scores[top] == 0:
        top = CAT_FALLBACK.get(it.get("category")) or SPEC_FALLBACK.get(it.get("spectrum")) or "play"
        return top, None
    m2 = second if scores[second] >= max(1, scores[top] - 1) and scores[second] > 0 else None
    return top, m2


def main():
    doc = json.load(open(MF, encoding="utf-8"))
    for it in doc["items"]:
        m1, m2 = classify(it)
        it["meaning"] = m1
        if m2:
            it["meaning2"] = m2
        else:
            it.pop("meaning2", None)
    tmp = MF + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MF)
    os.system(f'python3 "{BAKE}" >/dev/null 2>&1')
    c = collections.Counter(it["meaning"] for it in doc["items"])
    print("classified", len(doc["items"]), "items")
    for m in MEANINGS:
        print(f"  {m:10} {c.get(m, 0)}")


if __name__ == "__main__":
    main()
