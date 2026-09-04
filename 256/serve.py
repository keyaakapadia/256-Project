#!/usr/bin/env python3
"""
serve.py  ---  the 256 CMS server  (Python standard library only)

    python3 serve.py            # then open http://localhost:8256

Serves the static CMS and gives it a tiny JSON API so edits you make in the
browser (re-sorting the spectrum, moving folders, tagging colour, notes,
pasting an image URL, uploading a file) are written straight back into
data/collection.json and images/.
"""

import base64, json, os, re, threading, urllib.parse, urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT       = os.path.dirname(os.path.abspath(__file__))
COLLECTION = os.path.join(ROOT, "data", "collection.json")
IMAGES     = os.path.join(ROOT, "images")
PORT       = int(os.environ.get("PORT", "8256"))
LOCK       = threading.Lock()
EXT_OK     = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".tiff")


def load():
    with open(COLLECTION, encoding="utf-8") as fh:
        return json.load(fh)


def save(doc):
    items = doc["items"]
    collected = sum(1 for i in items if i.get("status") == "collected")
    doc["meta"]["total"]     = len(items)
    doc["meta"]["collected"] = collected
    doc["meta"]["needed"]    = len(items) - collected
    tmp = COLLECTION + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, COLLECTION)


def find(items, _id):
    for it in items:
        if it["id"] == _id:
            return it
    return None


def slug_ext(url, fallback=".jpg"):
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    return ext if ext in EXT_OK else fallback


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):  # quieter console
        pass

    def end_headers(self):      # never cache — always serve the latest edit
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    # ---- helpers -------------------------------------------------------
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(n) or b"{}")

    # ---- routes ------------------------------------------------------
    def do_GET(self):
        if self.path.split("?")[0] == "/api/collection":
            with LOCK:
                return self._json(load())
        return super().do_GET()

    def do_DELETE(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _id = (q.get("id") or [""])[0]
        with LOCK:
            doc = load()
            it = find(doc["items"], _id)
            if not it:
                return self._json({"error": "not found"}, 404)
            doc["items"] = [x for x in doc["items"] if x["id"] != _id]
            if it.get("file") and it["file"].startswith("images/") and it.get("source") == "upload":
                fp = os.path.join(ROOT, it["file"])
                if os.path.exists(fp):
                    os.remove(fp)
            save(doc)
            return self._json({"ok": True})

    def do_POST(self):
        route = self.path.split("?")[0]
        try:
            data = self._body()
        except Exception as e:
            return self._json({"error": "bad json: %s" % e}, 400)

        with LOCK:
            doc = load()
            items = doc["items"]

            # -- partial merge of one item ----------------------------
            if route == "/api/item":
                it = find(items, data.get("id", ""))
                if not it:
                    return self._json({"error": "not found"}, 404)
                for k, v in data.items():
                    if k == "id":
                        continue
                    it[k] = v
                it["user_edited"] = True
                save(doc)
                return self._json({"ok": True, "item": it})

            # -- create a brand new entry ----------------------------
            if route == "/api/new":
                import time
                nid = "upload-%d" % int(time.time() * 1000)
                it = {
                    "id": nid,
                    "title": data.get("title") or "Untitled",
                    "spectrum": data.get("spectrum"),
                    "spectrum_rank": None,
                    "category": data.get("category") or "Home & objects",
                    "on_arena_board": False,
                    "source": "upload",
                    "status": "needed",
                    "file": None,
                    "source_url": data.get("source_url") or None,
                    "source_label": _label(data.get("source_url")),
                    "arena_block_url": None,
                    "archive_links": [],
                    "color": None,
                    "notes": data.get("notes") or "",
                    "user_edited": True,
                }
                items.append(it)
                save(doc)
                return self._json({"ok": True, "item": it})

            # -- download an image from a URL into images/ -----------
            if route == "/api/fetch-image":
                it = find(items, data.get("id", ""))
                if not it:
                    return self._json({"error": "not found"}, 404)
                url = (data.get("url") or "").strip()
                if not url:
                    return self._json({"error": "no url"}, 400)
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "256-cms/1.0"})
                    with urllib.request.urlopen(req, timeout=90) as r:
                        blob = r.read()
                        ctype = r.headers.get("Content-Type", "")
                except Exception as e:
                    return self._json({"error": "download failed: %s" % e}, 502)
                ext = slug_ext(url)
                if ext == ".jpg" and "png" in ctype:
                    ext = ".png"
                if ext == ".jpg" and "webp" in ctype:
                    ext = ".webp"
                fname = "%s%s" % (re.sub(r"[^A-Za-z0-9_-]", "_", it["id"]), ext)
                with open(os.path.join(IMAGES, fname), "wb") as fh:
                    fh.write(blob)
                it["file"] = "images/" + fname
                it["status"] = "collected"
                if not it.get("source_url"):
                    it["source_url"] = url
                    it["source_label"] = _label(url)
                it["user_edited"] = True
                save(doc)
                return self._json({"ok": True, "item": it})

            # -- accept a file uploaded from the browser ------------
            if route == "/api/upload":
                it = find(items, data.get("id", ""))
                if not it:
                    return self._json({"error": "not found"}, 404)
                raw = data.get("dataUrl", "")
                m = re.match(r"data:([^;]+);base64,(.*)$", raw, re.S)
                if not m:
                    return self._json({"error": "bad dataUrl"}, 400)
                mime, b64 = m.group(1), m.group(2)
                ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                       "image/webp": ".webp", "image/avif": ".avif"}.get(mime, ".jpg")
                fname = "%s%s" % (re.sub(r"[^A-Za-z0-9_-]", "_", it["id"]), ext)
                with open(os.path.join(IMAGES, fname), "wb") as fh:
                    fh.write(base64.b64decode(b64))
                it["file"] = "images/" + fname
                it["status"] = "collected"
                it["user_edited"] = True
                save(doc)
                return self._json({"ok": True, "item": it})

        return self._json({"error": "unknown route"}, 404)


def _label(url):
    if not url:
        return None
    try:
        net = urllib.parse.urlparse(url).netloc
        return net[4:] if net.startswith("www.") else net
    except Exception:
        return None


if __name__ == "__main__":
    os.makedirs(IMAGES, exist_ok=True)
    if not os.path.exists(COLLECTION):
        raise SystemExit("data/collection.json missing --- run:  python3 build.py")
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("\n  256 CMS  ->  http://localhost:%d\n  (Ctrl+C to stop)\n" % PORT)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")
