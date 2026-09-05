/* 256 — working archive : client ------------------------------------ */
"use strict";

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const state = { doc: null, items: [], view: "spectrum", q: "",
                fCollected: false, fArena: false, fNeeded: true,
                colorQueue: [], colorBusy: false };

const SPECTRUM_ORDER = ["order", "inhabited", "pressure"];
const SPECTRUM_META = {
  order:     ["Order", ""],
  inhabited: ["Bending", ""],
  pressure:  ["Under pressure", ""],
  unsorted:  ["Unplaced", ""],
};

/* Meaning: the same grid read by what it's for, not what it shows.
   Ordered roughly least -> most disordered, so it reads like a second
   spectrum. Each meaning also nudges how its own row of cards sits. */
const MEANING_ORDER = ["organize", "contain", "separate", "guide", "measure",
                       "control", "repeat", "play", "break"];
const MEANING_META = {
  organize: ["Organize", ""], contain: ["Contain", ""], separate: ["Separate", ""],
  guide:    ["Guide", ""],    measure: ["Measure", ""], control:  ["Control", ""],
  repeat:   ["Repeat", ""],   play:    ["Play", ""],    break:    ["Break", ""],
};
/* Colour view: no names, no buckets — every image placed on one continuous
   run, ordered by its own average colour. */
function rgb2hsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  const l = (mx + mn) / 2;
  const s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  let h = 0;
  if (d !== 0) {
    if (mx === r) h = ((g - b) / d) % 6;
    else if (mx === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60; if (h < 0) h += 360;
  }
  return { h, s, l };
}
/* sort key from the average colour: near-neutrals first (dark→light), then
   chromatic. The hue wheel is rotated so the seam falls in the greens —
   reds sit next to oranges, not split across the two ends of the run. */
const HUE_SEAM = 140;   // start the run here (green); reds/oranges land together, mid-run
function colourSortKey(it) {
  const c = it.color;
  if (!c || !Array.isArray(c.avg)) return [2, 0, 0];
  const { h, s, l } = rgb2hsl(c.avg[0], c.avg[1], c.avg[2]);
  if (s < 0.14) return [0, 0, l];
  return [1, (h - HUE_SEAM + 360) % 360, l];
}

/* ---------- data ---------------------------------------------------- */
async function loadCollection() {
  try {
    const r = await fetch("api/collection", { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    state.doc = await r.json();
  } catch (e) {
    // no server (opened straight from the file system) — use the baked copy
    if (!window.__COLLECTION) throw e;
    state.doc = window.__COLLECTION;
    state.readonly = true;
    document.body.classList.add("readonly");
  }
  state.items = state.doc.items;
  $("#c-total").textContent = state.doc.meta.total;
  const chans = state.doc.meta.channels || [];
  $("#arena-link").href = state.doc.meta.channel
    || (chans[0] ? "https://www.are.na/keyaa-kapadia-lw6jnd8ydco/grids-irl-order-to-chaos" : "#");
  render();
}

async function patchItem(id, fields) {
  if (state.readonly) { toast("read-only — run  python3 serve.py  to edit"); return {}; }
  const r = await fetch("api/item", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, ...fields }),
  });
  const j = await r.json();
  if (j.item) {
    const i = state.items.findIndex(x => x.id === id);
    if (i >= 0) state.items[i] = j.item;
  }
  return j;
}

/* ---------- filtering + grouping ---------------------------------- */
function visible() {
  const q = state.q.trim().toLowerCase();
  return state.items.filter(it => {
    if (q) {
      const hay = [it.title, ...(it.aka || []), it.source_label, it.source_url, it.notes, it.category]
        .filter(Boolean).join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function bySpectrumThenRank(a, b) {
  const oa = SPECTRUM_ORDER.indexOf(a.spectrum), ob = SPECTRUM_ORDER.indexOf(b.spectrum);
  if (oa !== ob) return (oa < 0 ? 9 : oa) - (ob < 0 ? 9 : ob);
  return (a.spectrum_rank ?? 9999) - (b.spectrum_rank ?? 9999);
}

const byOrder = (a, b) => (a.order_index ?? 9999) - (b.order_index ?? 9999) || bySpectrumThenRank(a, b);

function groupsForView(items) {
  if (state.view === "spectrum") {
    const g = { unsorted: [], order: [], inhabited: [], pressure: [] };
    items.forEach(it => (g[it.spectrum] || g.unsorted).push(it));
    const out = [];
    if (g.unsorted.length) out.push(mkGroup("unsorted", SPECTRUM_META.unsorted, g.unsorted.sort(byOrder)));
    SPECTRUM_ORDER.forEach(k => out.push(mkGroup(k, SPECTRUM_META[k], g[k].sort(byOrder))));
    return out;
  }
  if (state.view === "folders") {
    // every folder runs in the same order → chaos sequence
    const cats = state.doc.meta.categories;
    const map = new Map(cats.map(c => [c, []]));
    items.forEach(it => { if (!map.has(it.category)) map.set(it.category, []); map.get(it.category).push(it); });
    return [...map]
      .filter(([, arr]) => arr.length)
      .map(([c, arr]) => mkGroup(c, [c, `${arr.length} image${arr.length === 1 ? "" : "s"}`], arr.sort(byOrder)));
  }
  if (state.view === "meaning") {
    const map = Object.fromEntries(MEANING_ORDER.map(m => [m, []]));
    items.forEach(it => (map[it.meaning] || map.play).push(it));
    return MEANING_ORDER
      .filter(m => map[m].length)
      .map(m => mkGroup(m, MEANING_META[m], map[m].sort(byOrder)));
  }
  // colour — one continuous run, ordered by each image's own average colour
  const sorted = [...items].sort((a, b) => {
    const ka = colourSortKey(a), kb = colourSortKey(b);
    return ka[0] - kb[0] || ka[1] - kb[1] || ka[2] - kb[2];
  });
  return [mkGroup("colour", ["", ""], sorted)];
}
function mkGroup(key, [name, desc], items, swatch) { return { key, name, desc, items, swatch }; }

/* ---------- render ---------------------------------------------- */
function render() {
  const stage = $("#stage");
  stage.innerHTML = "";
  const groups = groupsForView(visible());
  const tpl = $("#tpl-card");

  for (const g of groups) {
    const sec = document.createElement("section");
    sec.className = "group";
    if (g.name || g.desc) {
      const head = document.createElement("div");
      head.className = "group-head";
      head.innerHTML =
        `<h2>${esc(g.name)}</h2><span class="g-desc">${esc(g.desc || "")}</span>` +
        `<span class="g-count">${g.items.length}</span>`;
      sec.appendChild(head);
    }

    if (!g.items.length) {
      const e = document.createElement("p");
      e.className = "empty";
      e.textContent = "— nothing here with the current filters —";
      sec.appendChild(e);
    } else {
      const grid = document.createElement("div");
      grid.className = state.view === "meaning" ? "grid m-" + g.key : "grid";
      for (const it of g.items) grid.appendChild(card(it, tpl));
      sec.appendChild(grid);
    }
    stage.appendChild(sec);
  }
}

function card(it, tpl) {
  const el = tpl.content.firstElementChild.cloneNode(true);
  el.classList.toggle("needed", it.status !== "collected");
  const img = $("img", el);
  if (it.file) {
    img.alt = it.title;
    img.addEventListener("load", () => maybeExtract(it, img), { once: true });
    img.addEventListener("error", () => el.classList.add("needed"), { once: true });
    img.src = encodeURI(it.file);
    if (img.complete && img.naturalWidth) maybeExtract(it, img);
  }
  $(".slip-rank", el).textContent = it.spectrum_rank ? "№ " + it.spectrum_rank : "";
  $(".slip-text", el).textContent = it.title;
  $(".cap-title", el).textContent = it.title;
  if (it.color && it.color.palette && it.color.palette.length) {
    const strip = document.createElement("div");
    strip.className = "swatch-strip";
    strip.innerHTML = it.color.palette.map(c => `<i style="background:${c}"></i>`).join("");
    $(".thumb", el).appendChild(strip);
  }
  el.addEventListener("click", () => openDrawer(it));
  return el;
}

/* ---------- drawer / editor ------------------------------------ */
function openDrawer(it) {
  const d = $("#drawer");
  const cats = state.doc.meta.categories;
  const opt = (v, cur, label) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(label ?? v)}</option>`;
  d.innerHTML = `
    <button class="d-close" aria-label="close">×</button>
    <h3>${esc(it.title)}</h3>
    <p class="d-meta">${it.id} · ${esc(it.arena_channel || it.source)}</p>
    ${it.aka && it.aka.length ? `<p class="d-aka">also: ${it.aka.map(esc).join(" · ")}</p>` : ""}
    <div class="d-media">${it.file
      ? `<img src="${encodeURI(it.file)}" alt="">`
      : `<span class="ph">no image yet<br>use the archive links below,<br>then paste a URL or upload</span>`}</div>

    <div class="d-row"><label>Spectrum — order → chaos</label>
      <select data-k="spectrum">
        ${opt("", it.spectrum || "", "— unsorted —")}
        ${opt("order", it.spectrum, "Order")}
        ${opt("inhabited", it.spectrum, "Bending")}
        ${opt("pressure", it.spectrum, "Under pressure")}
      </select></div>

    <div class="d-row"><label>Folder — subject</label>
      <select data-k="category">${cats.map(c => opt(c, it.category)).join("")}</select></div>

    <div class="d-row"><label>Meaning — what the grid is for</label>
      <select data-k="meaning">${MEANING_ORDER.map(m => opt(m, it.meaning, MEANING_META[m][0])).join("")}</select>
      ${it.meaning2 ? `<div class="d-meta">also reads as ${esc(MEANING_META[it.meaning2][0].toLowerCase())}</div>` : ""}
    </div>

    ${it.color && it.color.palette && it.color.palette.length ? `
    <div class="d-row"><label>Average colour</label>
      <div class="d-swatches">
        ${it.color.avg ? `<i class="d-avg" style="background:rgb(${it.color.avg.join(",")})"></i>` : ""}
        ${it.color.palette.map(c => `<i style="background:${esc(c)}"></i>`).join("")}
      </div>
    </div>` : ""}

    <div class="d-row"><label>Notes</label>
      <textarea data-k="notes" placeholder="why this one / how it reads / where shot…">${esc(it.notes || "")}</textarea></div>

    <div class="d-row"><label>Add / replace image</label>
      <input type="text" id="d-url" placeholder="paste direct image URL (.jpg/.png/…)">
      <div class="d-actions" style="margin-top:8px">
        <button id="d-fetch">↓ fetch URL into folder</button>
        <button id="d-upload">⤒ upload file…</button>
        <input type="file" id="d-file" accept="image/*" hidden>
      </div>
    </div>

    <div class="d-row"><label>Original source</label>
      ${it.source_url ? `<a href="${esc(it.source_url)}" target="_blank" rel="noopener">${esc(it.source_label || it.source_url)} ↗</a>`
                      : `<input type="text" id="d-srcurl" placeholder="source page URL" value="">`}
      ${it.image_credit ? `<div class="d-meta">${esc(it.image_credit.license || "")}${
          it.image_credit.artist ? " · " + esc(it.image_credit.artist) : ""}</div>` : ""}
      ${it.arena_block_url ? `<div class="d-meta"><a href="${esc(it.arena_block_url)}" target="_blank" rel="noopener">Are.na block ↗</a></div>` : ""}
    </div>

    ${it.archive_links && it.archive_links.length ? `
    <div class="d-row"><label>Where to source it (public archives)</label>
      <ul class="d-links">${it.archive_links.map(l =>
        `<li><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a></li>`).join("")}</ul>
    </div>` : ""}

    <div class="d-row d-actions">
      <button id="d-save" class="primary">save changes</button>
      <button id="d-del">delete item</button>
    </div>`;

  d.hidden = false; $("#scrim").hidden = false;

  const close = () => { d.hidden = true; $("#scrim").hidden = true; };
  $(".d-close", d).onclick = close;
  $("#scrim").onclick = close;

  $("#d-save", d).onclick = async () => {
    const fields = {
      spectrum: $('[data-k="spectrum"]', d).value || null,
      category: $('[data-k="category"]', d).value,
      meaning: $('[data-k="meaning"]', d).value,
      notes: $('[data-k="notes"]', d).value,
    };
    const su = $("#d-srcurl", d);
    if (su && su.value.trim()) { fields.source_url = su.value.trim();
      fields.source_label = hostOf(su.value.trim()); }
    await patchItem(it.id, fields);
    toast("saved"); close(); render(); refreshCounts();
  };

  $("#d-del", d).onclick = async () => {
    if (state.readonly) return toast("read-only — run  python3 serve.py  to edit");
    if (!confirm("Delete this item from the collection?")) return;
    await fetch("api/item?id=" + encodeURIComponent(it.id), { method: "DELETE" });
    state.items = state.items.filter(x => x.id !== it.id);
    toast("deleted"); close(); render(); refreshCounts();
  };

  $("#d-fetch", d).onclick = async () => {
    if (state.readonly) return toast("read-only — run  python3 serve.py  to edit");
    const url = $("#d-url", d).value.trim();
    if (!url) return;
    $("#d-fetch", d).textContent = "fetching…";
    const j = await fetch("api/fetch-image", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: it.id, url }),
    }).then(r => r.json());
    if (j.error) { alert(j.error); $("#d-fetch", d).textContent = "↓ fetch URL into folder"; return; }
    syncItem(j.item); toast("image saved"); openDrawer(j.item); render(); refreshCounts();
  };

  $("#d-upload", d).onclick = () => state.readonly
    ? toast("read-only — run  python3 serve.py  to edit")
    : $("#d-file", d).click();
  $("#d-file", d).onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const fr = new FileReader();
    fr.onload = async () => {
      const j = await fetch("api/upload", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: it.id, dataUrl: fr.result }),
      }).then(r => r.json());
      if (j.error) { alert(j.error); return; }
      syncItem(j.item); toast("image saved"); openDrawer(j.item); render(); refreshCounts();
    };
    fr.readAsDataURL(f);
  };
}

function syncItem(item) {
  const i = state.items.findIndex(x => x.id === item.id);
  if (i >= 0) state.items[i] = item;
}
async function refreshCounts() {
  if (state.readonly) { $("#c-total").textContent = state.items.length; return; }
  const r = await fetch("api/collection", { cache: "no-store" });
  const d = await r.json();
  $("#c-total").textContent = d.meta.total;
}

/* ---------- colour extraction (canvas, same-origin) ------------ */
function maybeExtract(it, img) {
  if (it.color && Array.isArray(it.color.avg)) return;   // already have an average colour
  state.colorQueue.push([it, img]);
  pumpColour();
}
async function pumpColour() {
  if (state.colorBusy) return;
  state.colorBusy = true;
  while (state.colorQueue.length) {
    const [it, img] = state.colorQueue.shift();
    try {
      const color = extractColor(img);
      if (color) { await patchItem(it.id, { color }); }
    } catch (e) { /* tainted canvas on file:// — ignore */ }
  }
  state.colorBusy = false;
  if (state.view === "colour") render();
}
function extractColor(img) {
  const W = 44, r = img.naturalWidth / img.naturalHeight || 1;
  const w = r >= 1 ? W : Math.round(W * r), h = r >= 1 ? Math.round(W / r) : W;
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, w, h);
  const px = ctx.getImageData(0, 0, w, h).data;
  let R = 0, G = 0, B = 0, n = 0;
  const bins = new Map();
  for (let i = 0; i < px.length; i += 4) {
    const a = px[i + 3]; if (a < 128) continue;
    const rr = px[i], gg = px[i + 1], bb = px[i + 2];
    R += rr; G += gg; B += bb; n++;
    const key = (rr >> 5) + "," + (gg >> 5) + "," + (bb >> 5);
    const e = bins.get(key) || [0, 0, 0, 0];
    e[0] += rr; e[1] += gg; e[2] += bb; e[3]++; bins.set(key, e);
  }
  if (!n) return null;
  R = R / n; G = G / n; B = B / n;
  const palette = [...bins.values()].sort((a, b) => b[3] - a[3]).slice(0, 5)
    .map(e => hex(e[0] / e[3], e[1] / e[3], e[2] / e[3]));
  return { hex: hex(R, G, B), palette, avg: [Math.round(R), Math.round(G), Math.round(B)] };
}
const hex = (r, g, b) => "#" + [r, g, b].map(v =>
  Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");

/* ---------- misc UI ------------------------------------------- */
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function hostOf(u) { try { return new URL(u).host.replace(/^www\./, ""); } catch { return "source"; } }
let toastT;
function toast(msg) {
  let t = $(".toast"); if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg; t.classList.add("show");
  clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 1600);
}

$$(".view-btn").forEach(b => b.onclick = () => {
  $$(".view-btn").forEach(x => x.classList.remove("is-active"));
  b.classList.add("is-active");
  state.view = b.dataset.view;
  render();
});
$("#q").addEventListener("input", e => { state.q = e.target.value; render(); });
$("#add-btn").onclick = async () => {
  if (state.readonly) return toast("read-only — run  python3 serve.py  to edit");
  const title = prompt("Title for the new item:");
  if (!title) return;
  const j = await fetch("api/new", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  }).then(r => r.json());
  if (j.item) { state.items.push(j.item); render(); openDrawer(j.item); refreshCounts(); }
};
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && !$("#drawer").hidden) { $("#drawer").hidden = true; $("#scrim").hidden = true; }
});

loadCollection().catch(err => {
  $("#stage").innerHTML = `<p class="empty" style="padding:40px 0">Could not load the collection.<br>
    Run <b>python3 serve.py</b> from the project folder and open <b>http://localhost:8256</b>.<br><br>${esc(err.message)}</p>`;
});
