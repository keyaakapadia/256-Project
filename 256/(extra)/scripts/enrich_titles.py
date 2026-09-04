#!/usr/bin/env python3
"""
enrich_titles.py  —  give every item an `aka` list of alternative names so
the CMS search finds it however you phrase it.

Each concept item keeps its own title, and gains:
  - matching phrases from the SUBJECT-TAXONOMY list (your second naming of the
    same 256 subjects), by shared significant words
  - that taxonomy section's label as a keyword
  - a few plain synonyms for the common "grid" nouns

Run after the images are in.  Idempotent — rebuilds `aka` from scratch each
time, touches nothing else.

    python3 enrich_titles.py
"""

import json, os, re

MF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "collection.json")

# ---- the subject taxonomy: your second naming of the same subjects ----------
TAXONOMY = {
"Streets & public space": """
Parking lot spaces | Rows of parked cars | Parking-garage columns | Crosswalk stripes |
Sidewalk paving slabs | Brick sidewalks | Cobblestone streets | Road-lane markings |
Highway tollbooths | Traffic cones arranged in rows | Bike racks | Public benches in rows |
Street trees planted evenly | Tree guards | Storm-drain covers | Manhole-cover patterns |
Construction barriers | Scaffolding | Chain-link fences | Metal security fences |
Subway entrance railings | Bus-stop shelters | Newsstands | Outdoor market stalls |
Food-truck lineups | Shipping containers | Construction-site rebar | Building facades |
Fire escapes | Apartment balconies
""",
"Transportation": """
Airplane seats | Train seats | Subway seats | Bus seats | School-bus seats |
Airport departure boards | Train-station timetable boards | Subway-platform tiles |
Railway tracks and sleepers | Train-carriage windows | Airport security lanes |
Baggage-claim belts | Airport luggage carts | Rental bicycles in docks |
E-scooters parked together | Taxi queues | Bus queues | Boarding gates | Ferry seating |
Marina boat slips | Rows of bicycles | Motorcycle parking | Car-dealership lots |
Airport runways | Highway interchanges | Traffic seen from above |
Bus-depot parking bays | Train yards | Shipping-port container stacks |
Traffic lights aligned along a street
""",
"Schools & offices": """
Classroom desks | Lecture-hall seats | Library tables | Library bookshelves |
Rows of lockers | School cubbies | Computer-lab stations | Office cubicles |
Conference-room chairs | Co-working desks | Filing cabinets | Mailroom pigeonholes |
Office ceiling panels | Fluorescent ceiling lights | Window blinds | Bulletin-board pins |
Calendar pages | Spreadsheet cells on a screen | Keyboard keys | Numerical keypads |
Desk-organizer compartments | Stacks of notebooks | Post-it notes on a wall |
Name tags arranged for an event | Employee ID cards on a rack | Printer-paper trays |
Storage boxes in an archive | Museum collection drawers | Blueprint filing systems |
Architectural plans
""",
"Stores & commerce": """
Supermarket aisles | Grocery shelves | Canned goods | Cereal boxes |
Bottled drinks in refrigerators | Egg cartons | Produce crates | Fruit stacked at a market |
Bakery display trays | Chocolate-box compartments | Pharmacy shelves | Clothing racks |
Folded shirts | Shoe-store displays | Sunglasses displays | Jewelry display cases |
Lipstick displays | Nail-polish shelves | Hardware-store drawers | Paint-swatch displays |
Tile-store samples | Fabric-sample books | Vinyl records in bins | Bookstore shelves |
Magazine racks | Vending-machine compartments | Laundromat machines |
Shopping carts nested together | Warehouse pallets | Self-checkout stations
""",
"Food & kitchens": """
Ice-cube trays | Oven racks | Stove grates | Cooling racks | Baking trays | Muffin tins |
Waffle patterns | Chocolate bars | Crackers arranged in packaging | Sushi trays |
Bento boxes | Dumplings lined up | Cookies on a baking sheet | Cupcakes in a display |
Eggs in cartons | Bread loaves on racks | Restaurant tables | Cafe chairs | Cafeteria trays |
Place settings at a banquet | Wine bottles in racks | Spice jars | Kitchen tiles |
Dish-drying racks | Cutlery organizers | Refrigerator shelves | Freezer compartments |
Pantry shelves | Restaurant order tickets | Food-delivery bags lined up
""",
"Home & objects": """
Bathroom tiles | Shower tiles | Mosaic floors | Wooden floorboards | Parquet flooring |
Rugs with geometric patterns | Woven mats | Tatami mats | Yoga mats laid out for a class |
Bed frames | Quilts | Checkered blankets | Windowpanes | Window screens | Venetian blinds |
Bookshelves | Shoe racks | Coat hooks | Laundry baskets | Storage cubbies |
Closet compartments | Photo walls | Framed pictures arranged together | Light switches |
Electrical outlet panels | Radiator slats | Air-conditioning vents | Speaker grilles |
Remote-control buttons | Board-game boards
""",
"People & gatherings": """
Rows of people sitting in a theater | Students seated in class | People at graduation |
An orchestra seated onstage | Choir members on risers | Marching bands |
Military formations | Parade participants | Protesters holding signs |
People waiting in airport lines | Grocery-store checkout lines | Festival entrance queues |
People seated at long tables | Conference audiences | Church pews filled with people |
Stadium crowds | Bleacher seating | Group exercise classes | Yoga classes | Spin classes |
Dancers in formation | Ballet-barre classes | Swimmers in separate lanes |
Runners at a starting line | Cyclists in a peloton | Workers at assembly stations |
Chefs working along a kitchen line | Barbershop chairs occupied in a row |
Students posing for a class photograph | Apartment windows with people inside
""",
"Sports & recreation": """
Tennis-court markings | Basketball-court markings | Volleyball-court markings |
Badminton courts | Pickleball courts | Soccer-field mowing patterns |
Football-field yard lines | Baseball-field seating | Running-track lanes |
Swimming-pool lanes | Diving blocks | Golf driving-range bays | Batting cages |
Bowling lanes | Bowling-ball racks | Gym lockers | Weight racks | Treadmills lined up |
Exercise bikes lined up | Climbing-wall holds | Stadium seats | Stadium roof structures |
Scoreboards | Chessboards | Checkers boards | Scrabble boards | Bingo cards |
Foosball-player formations | Ping-pong practice tables | Arcade-machine rows
""",
"Nature, farming & landscape": """
Crop fields seen from above | Vineyard rows | Orchard trees | Rice paddies | Tea plantations |
Vegetable-garden plots | Community-garden beds | Greenhouse frames | Plant nursery trays |
Seedling grids | Flower beds | Hedge mazes | Irrigation channels |
Hay bales arranged in fields | Timber stacked at a farm | Fishing nets | Honeycomb |
Spiderwebs | Leaf veins | Pinecone scales | Sunflower-seed patterns | Corn kernels |
Tree bark with rectangular cracks | Cracked earth | Salt flats |
Rock formations with repeated fractures | Rows of beach umbrellas | Beach chairs |
Campsite plots | Cemetery plots and headstones
""",
"Industrial & technical": """
Solar-panel fields | Electrical substations | Power-line towers | Server racks |
Circuit boards | Computer ventilation grilles | LED-light panels |
Security-camera monitor walls | Factory assembly lines | Conveyor belts |
Warehouse shelving | Stacked pallets | Factory pipes | Metal storage cages |
Tool pegboards | Nuts and bolts in organizer trays | Construction bricks stacked on pallets |
Cinder-block walls | Rebar cages | Drainage grates | Elevator-button panels |
Apartment intercom buttons | Mailboxes in an apartment lobby | Safety-deposit boxes |
Server-room floor tiles | Cemetery urn compartments | Contact sheets of photographs |
Film strips | Pharmacy pill blister packs | Rows of phone-app icons on a screen
""",
}

# plain synonyms for the recurring "grid" nouns
SYN = {
 "parking": ["cars", "lot", "bays", "stalls", "spaces"],
 "car": ["cars", "vehicles", "automobiles", "dealership"],
 "crosswalk": ["zebra crossing", "pedestrian crossing", "road markings"],
 "lane": ["lanes", "markings", "road"],
 "facade": ["facades", "building exterior", "elevation"],
 "facades": ["facade", "building exterior", "elevation"],
 "balcony": ["balconies"], "balconies": ["balcony"],
 "fence": ["fencing", "mesh", "chain link", "railings"],
 "fences": ["fencing", "mesh", "chain link", "railings"],
 "shelf": ["shelves", "shelving", "racks", "aisles"],
 "shelves": ["shelving", "racks", "aisles"],
 "shelving": ["shelves", "racks", "aisles"],
 "seat": ["seats", "seating", "chairs", "rows"],
 "seats": ["seating", "chairs", "rows", "audience"],
 "chair": ["chairs", "seats", "seating"],
 "tile": ["tiles", "tiling", "mosaic", "grout"],
 "tiles": ["tiling", "mosaic", "grout"],
 "window": ["windows", "panes", "glazing", "windowpanes"],
 "windows": ["panes", "glazing", "windowpanes", "facade"],
 "locker": ["lockers", "cubby", "cubbies"],
 "lockers": ["cubbies", "cubby"],
 "pallet": ["pallets", "crates", "stacks"],
 "pallets": ["crates", "stacks"],
 "container": ["containers", "shipping", "cargo"],
 "containers": ["shipping", "cargo", "port"],
 "column": ["columns", "pillars", "posts"],
 "columns": ["pillars", "posts"],
 "brick": ["bricks", "brickwork", "masonry"],
 "cubicle": ["cubicles", "office desks", "workstations"],
 "cubicles": ["office desks", "workstations"],
 "desk": ["desks", "tables", "workstations"],
 "desks": ["tables", "workstations"],
 "bookshelf": ["bookshelves", "shelves", "stacks"],
 "bookshelves": ["shelves", "stacks", "library"],
 "crowd": ["crowds", "audience", "spectators", "people"],
 "crowds": ["audience", "spectators", "people"],
 "pew": ["pews", "church seating", "benches"],
 "pews": ["church seating", "benches"],
 "field": ["fields", "aerial", "farmland", "plots"],
 "fields": ["aerial", "farmland", "plots"],
 "solar": ["solar panels", "photovoltaic array"],
 "server": ["servers", "server rack", "data center"],
 "runway": ["runways", "airfield", "tarmac"],
 "track": ["tracks", "rails", "sleepers"],
 "tracks": ["rails", "sleepers", "railway"],
 "grave": ["graves", "headstones", "cemetery"],
 "headstone": ["headstones", "gravestones", "cemetery"],
 "headstones": ["gravestones", "cemetery"],
 "honeycomb": ["hexagons", "beehive", "comb"],
 "grid": ["matrix", "lattice", "array"],
}

STOP = set("a an the of in on at and or with without before after into from to "
           "seen being over under across around perfectly one each every some "
           "several through outside inside their his her its clear controlled "
           "rows row lined arranged aligned different variation gains".split())


def toks(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    out = []
    for w in s.split():
        if w in STOP or len(w) < 3:
            continue
        w = re.sub(r"(ies)$", "y", w)
        w = re.sub(r"(sses)$", "ss", w)
        w = re.sub(r"s$", "", w) if len(w) > 4 else w
        out.append(w)
    return set(out)


TAX = [(sec, phrase.strip(), toks(phrase)) for sec, block in TAXONOMY.items()
       for phrase in re.split(r"\s*\|\s*", block.strip()) if phrase.strip()]


def aka_for(title):
    tt = toks(title)
    if not tt:
        return []
    hits = []
    for sec, phrase, pt in TAX:
        ov = tt & pt
        if len(ov) >= 2 or (len(ov) == 1 and len(pt) <= 2):
            hits.append((len(ov), sec, phrase))
    hits.sort(reverse=True)
    aka, secs = [], []
    for _, sec, phrase in hits[:4]:
        if phrase.lower() != title.lower():
            aka.append(phrase)
        if sec not in secs:
            secs.append(sec)
    syn = []
    for w in tt:
        syn += SYN.get(w, [])
    # de-dup, keep order, cap
    seen, final = set(), []
    for x in aka + secs[:1] + syn:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            final.append(x)
    return final[:6]


def main():
    doc = json.load(open(MF, encoding="utf-8"))
    n = 0
    for it in doc["items"]:
        if it.get("source") == "arena":
            continue
        a = aka_for(it.get("title", ""))
        if a:
            it["aka"] = a
            n += 1
        elif "aka" in it:
            del it["aka"]
    tmp = MF + ".tmp"
    json.dump(doc, open(tmp, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    os.replace(tmp, MF)
    print(f"added alternative names (`aka`) to {n} items")
    # a couple of samples
    for it in doc["items"]:
        if it.get("aka") and it["id"] in ("concept-001", "concept-004", "concept-030", "concept-120"):
            print(f'  {it["title"]!r}  ->  {it["aka"]}')


if __name__ == "__main__":
    main()
