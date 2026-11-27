/* Annotation layer for investment memos.
 * Highlights + comments anchored by quote/prefix/suffix (W3C-annotation style),
 * autosaved to localStorage, exported to a sidecar {doc}.annotations.json.
 * Claude replies are merged in from the sidecar / embedded #annotations-data block. */
(function () {
  "use strict";
  var ROOT = document.body;
  var DOC = (location.pathname.split("/").pop() || "memo").replace(/\.html?$/, "");
  var LS_KEY = "ann:" + DOC;
  var CTX = 40; // prefix/suffix anchor length

  var store = { version: 1, doc: DOC, annotations: [], deleted: [] };
  var fileHandle = null;
  var dirty = false;
  var pending = null; // captured selection anchor awaiting toolbar action

  function uid(p) { return p + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7); }
  function now() { return new Date().toISOString(); }

  // ---------- text index over annotatable text nodes ----------
  function indexable(n) {
    var p = n.parentNode;
    if (!p || !p.closest) return false;
    var tag = p.nodeName;
    if (tag === "SCRIPT" || tag === "STYLE" || tag === "TEXTAREA") return false;
    if (p.namespaceURI && p.namespaceURI.indexOf("svg") !== -1) return false;
    if (p.closest("#ann-panel,#ann-toolbar,#ann-bar,#ann-orphans,#tip,svg")) return false;
    return true;
  }
  function buildIndex() {
    var w = document.createTreeWalker(ROOT, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) { return indexable(n) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT; }
    });
    var parts = [], nodes = [], pos = 0, n;
    while ((n = w.nextNode())) { nodes.push({ node: n, start: pos }); parts.push(n.nodeValue); pos += n.nodeValue.length; }
    return { text: parts.join(""), nodes: nodes };
  }
  function posAfter(idx, el) {
    for (var i = 0; i < idx.nodes.length; i++) {
      if (el.compareDocumentPosition(idx.nodes[i].node) & Node.DOCUMENT_POSITION_FOLLOWING) return idx.nodes[i].start;
    }
    return idx.text.length;
  }

  // ---------- wrapping ----------
  function wrapChars(s, e, ann) {
    var idx = buildIndex(), segs = [];
    idx.nodes.forEach(function (rec) {
      var ns = rec.start, ne = ns + rec.node.nodeValue.length;
      var a = Math.max(s, ns), b = Math.min(e, ne);
      if (a < b) segs.push({ node: rec.node, from: a - ns, to: b - ns });
    });
    var last = null;
    segs.forEach(function (sg) {
      var node = sg.node;
      if (sg.to < node.nodeValue.length) node.splitText(sg.to);
      var target = sg.from > 0 ? node.splitText(sg.from) : node;
      var m = document.createElement("mark");
      m.className = "ann";
      m.dataset.annId = ann.id;
      target.parentNode.insertBefore(m, target);
      m.appendChild(target);
      last = m;
    });
    decorate(ann);
    return last;
  }
  function marksFor(id) { return Array.prototype.slice.call(document.querySelectorAll('mark.ann[data-ann-id="' + id + '"]')); }
  function decorate(ann) {
    var ms = marksFor(ann.id);
    var flagged = !!(ann.note || (ann.replies && ann.replies.length));
    ms.forEach(function (m) { m.classList.toggle("has-note", flagged); });
    var old = document.querySelector('.ann-flag[data-ann-id="' + ann.id + '"]');
    if (old) old.remove();
    if (flagged && ms.length) {
      var f = document.createElement("span");
      f.className = "ann-flag"; f.dataset.annId = ann.id;
      f.textContent = "◆" + ((ann.replies && ann.replies.length) ? ann.replies.length : "");
      ms[ms.length - 1].after(f);
    }
  }
  function unwrap(id) {
    marksFor(id).forEach(function (m) {
      while (m.firstChild) m.parentNode.insertBefore(m.firstChild, m);
      m.remove();
    });
    var f = document.querySelector('.ann-flag[data-ann-id="' + id + '"]');
    if (f) f.remove();
    ROOT.normalize();
  }

  // ---------- anchoring ----------
  function locate(ann) {
    var idx = buildIndex(), t = idx.text, s = -1;
    if (ann.prefix || ann.suffix) {
      var i = t.indexOf((ann.prefix || "") + ann.quote + (ann.suffix || ""));
      if (i !== -1) s = i + (ann.prefix || "").length;
    }
    if (s === -1) s = t.indexOf(ann.quote);
    if (s === -1) return null;
    return { start: s, end: s + ann.quote.length };
  }
  function applyAll() {
    store.annotations.forEach(function (ann) {
      if (marksFor(ann.id).length) { decorate(ann); return; }
      var span = locate(ann);
      if (span) { ann.orphan = false; wrapChars(span.start, span.end, ann); }
      else ann.orphan = true;
    });
    renderOrphans();
    renderBar();
  }
  function renderOrphans() {
    var box = document.getElementById("ann-orphans");
    var orphans = store.annotations.filter(function (a) { return a.orphan; });
    if (!orphans.length) { if (box) box.remove(); return; }
    if (!box) {
      box = document.createElement("div");
      box.id = "ann-orphans";
      box.style.cssText = "margin-top:2em;padding:10px 14px;border:1px dashed var(--baseline,#c3c2b7);border-radius:8px;font:13px system-ui,sans-serif;color:var(--ink-2,#52514e)";
      ROOT.appendChild(box);
    }
    box.innerHTML = "<strong>Annotations that no longer match the text</strong>";
    orphans.forEach(function (a) {
      var d = document.createElement("div");
      d.style.marginTop = "6px";
      d.textContent = "“" + a.quote.slice(0, 90) + (a.quote.length > 90 ? "…" : "") + "”" + (a.note ? " — " + a.note : "");
      box.appendChild(d);
    });
  }

  // ---------- persistence ----------
  function persistLocal() {
    try { localStorage.setItem(LS_KEY, JSON.stringify(store)); } catch (e) {}
    dirty = true;
    renderBar();
  }
  function mergeStores(a, b) {
    if (!a) return b || store; if (!b) return a;
    var deleted = {}, map = {};
    (a.deleted || []).concat(b.deleted || []).forEach(function (id) { deleted[id] = 1; });
    function take(x) {
      if (deleted[x.id]) return;
      var ex = map[x.id];
      if (!ex) { map[x.id] = JSON.parse(JSON.stringify(x)); return; }
      var keep = ((x.updatedAt || "") > (ex.updatedAt || "")) ? JSON.parse(JSON.stringify(x)) : ex;
      var rmap = {};
      (ex.replies || []).concat(x.replies || []).forEach(function (r) { rmap[r.id] = r; });
      keep.replies = Object.keys(rmap).map(function (k) { return rmap[k]; })
        .sort(function (p, q) { return (p.createdAt || "") < (q.createdAt || "") ? -1 : 1; });
      map[x.id] = keep;
    }
    (a.annotations || []).forEach(take);
    (b.annotations || []).forEach(take);
    return { version: 1, doc: DOC, annotations: Object.keys(map).map(function (k) { return map[k]; }), deleted: Object.keys(deleted) };
  }
  function loadInitial() {
    var embedded = null, local = null, el = document.getElementById("annotations-data");
    if (el) { try { embedded = JSON.parse(el.textContent); } catch (e) {} }
    try { local = JSON.parse(localStorage.getItem(LS_KEY)); } catch (e) {}
    store = mergeStores(embedded, local);
    dirty = false;
    applyAll();
  }
  async function saveFile() {
    var json = JSON.stringify(store, null, 2);
    if (window.showSaveFilePicker) {
      try {
        if (!fileHandle) fileHandle = await window.showSaveFilePicker({
          suggestedName: DOC + ".annotations.json",
          types: [{ description: "JSON", accept: { "application/json": [".json"] } }]
        });
        var w = await fileHandle.createWritable();
        await w.write(json); await w.close();
        dirty = false; renderBar(); return;
      } catch (e) { if (e && e.name === "AbortError") return; }
    }
    var blob = new Blob([json], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = DOC + ".annotations.json";
    a.click();
    dirty = false; renderBar();
  }
  function loadFilePrompt() {
    var inp = document.createElement("input");
    inp.type = "file"; inp.accept = ".json,application/json";
    inp.onchange = function () {
      var f = inp.files[0]; if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try {
          var parsed = JSON.parse(r.result);
          store.annotations.forEach(function (a) { unwrap(a.id); });
          store = mergeStores(store, parsed);
          applyAll(); persistLocal(); dirty = false; renderBar();
        } catch (e) { alert("Could not parse annotations file."); }
      };
      r.readAsText(f);
    };
    inp.click();
  }

  // ---------- UI: bar, toolbar, panel ----------
  var bar = document.createElement("div"); bar.id = "ann-bar"; document.body.appendChild(bar);
  function renderBar() {
    var n = store.annotations.filter(function (a) { return !a.orphan; }).length;
    bar.innerHTML = "";
    var label = document.createElement("span");
    label.textContent = n + " annotation" + (n === 1 ? "" : "s");
    if (dirty) { var d = document.createElement("span"); d.className = "dirty"; d.textContent = "•"; d.title = "Unsaved changes"; label.appendChild(d); }
    bar.appendChild(label);
    var save = document.createElement("button"); save.textContent = "Save"; save.title = "Write sidecar " + DOC + ".annotations.json"; save.onclick = saveFile;
    var load = document.createElement("button"); load.textContent = "Load"; load.title = "Import an annotations JSON (e.g., after Claude replies)"; load.onclick = loadFilePrompt;
    bar.appendChild(save); bar.appendChild(load);
  }

  var toolbar = document.createElement("div"); toolbar.id = "ann-toolbar"; document.body.appendChild(toolbar);
  var hlBtn = document.createElement("button"); hlBtn.textContent = "Highlight";
  var cmBtn = document.createElement("button"); cmBtn.textContent = "Comment";
  toolbar.appendChild(hlBtn); toolbar.appendChild(cmBtn);

  var panel = document.createElement("div"); panel.id = "ann-panel"; document.body.appendChild(panel);
  function hideToolbar() { toolbar.style.display = "none"; pending = null; }
  function hidePanel() { panel.style.display = "none"; panel.dataset.annId = ""; }

  function captureSelection() {
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.rangeCount) return null;
    var text = sel.toString();
    if (!text.trim() || text.length > 4000) return null;
    var r = sel.getRangeAt(0);
    var anc = r.commonAncestorContainer;
    var ancEl = anc.nodeType === 1 ? anc : anc.parentNode;
    if (!ancEl || !ancEl.closest || !ROOT.contains(ancEl)) return null;
    if (ancEl.closest("#ann-panel,#ann-toolbar,#ann-bar,svg")) return null;
    var startSent = document.createElement("span"), endSent = document.createElement("span");
    var r2 = r.cloneRange(); r2.collapse(false); r2.insertNode(endSent);
    var r1 = r.cloneRange(); r1.collapse(true); r1.insertNode(startSent);
    var idx = buildIndex();
    var s = posAfter(idx, startSent), e = posAfter(idx, endSent);
    startSent.remove(); endSent.remove(); ROOT.normalize();
    if (e <= s) return null;
    var rect = r.getBoundingClientRect();
    return {
      start: s, end: e,
      quote: idx.text.slice(s, e),
      prefix: idx.text.slice(Math.max(0, s - CTX), s),
      suffix: idx.text.slice(e, e + CTX),
      rect: rect
    };
  }
  document.addEventListener("mouseup", function (ev) {
    if (toolbar.contains(ev.target) || panel.contains(ev.target) || bar.contains(ev.target)) return;
    setTimeout(function () {
      var cap = captureSelection();
      if (!cap) { hideToolbar(); return; }
      pending = cap;
      toolbar.style.display = "flex";
      toolbar.style.left = Math.max(8, window.scrollX + cap.rect.left) + "px";
      toolbar.style.top = (window.scrollY + cap.rect.bottom + 6) + "px";
    }, 0);
  });
  function createAnnotation(withComment) {
    if (!pending) return;
    var ann = {
      id: uid("a"), quote: pending.quote, prefix: pending.prefix, suffix: pending.suffix,
      note: null, author: "user", createdAt: now(), updatedAt: now(), replies: []
    };
    store.annotations.push(ann);
    var lastMark = wrapChars(pending.start, pending.end, ann);
    persistLocal(); renderBar();
    var rect = pending.rect;
    hideToolbar();
    window.getSelection().removeAllRanges();
    if (withComment && lastMark) openPanel(ann.id, rect);
  }
  hlBtn.onclick = function () { createAnnotation(false); };
  cmBtn.onclick = function () { createAnnotation(true); };

  function annById(id) { return store.annotations.filter(function (a) { return a.id === id; })[0]; }
  function openPanel(id, rect) {
    var ann = annById(id); if (!ann) return;
    panel.dataset.annId = id;
    panel.innerHTML = "";
    var q = document.createElement("p"); q.className = "ann-quote";
    q.textContent = "“" + ann.quote.slice(0, 160) + (ann.quote.length > 160 ? "…" : "") + "”";
    panel.appendChild(q);
    var ta = document.createElement("textarea");
    ta.placeholder = "Add a comment…"; ta.value = ann.note || "";
    panel.appendChild(ta);
    (ann.replies || []).forEach(function (r) {
      var d = document.createElement("div"); d.className = "ann-reply" + (r.author === "claude" ? " claude" : "");
      var meta = document.createElement("div"); meta.className = "ann-meta";
      meta.textContent = (r.author === "claude" ? "Claude" : "You") + " · " + (r.createdAt || "").slice(0, 10);
      var body = document.createElement("div"); body.textContent = r.text;
      d.appendChild(meta); d.appendChild(body); panel.appendChild(d);
    });
    var replyTa = null;
    if ((ann.replies || []).length) {
      replyTa = document.createElement("textarea");
      replyTa.placeholder = "Reply…"; replyTa.style.marginTop = "8px"; replyTa.style.minHeight = "40px";
      panel.appendChild(replyTa);
    }
    var row = document.createElement("div"); row.className = "ann-row";
    var left = document.createElement("div"); var right = document.createElement("div");
    var rm = document.createElement("button"); rm.className = "danger"; rm.textContent = "Remove";
    rm.onclick = function () {
      unwrap(id);
      store.annotations = store.annotations.filter(function (a) { return a.id !== id; });
      store.deleted.push(id);
      persistLocal(); renderBar(); hidePanel();
    };
    left.appendChild(rm);
    var closeB = document.createElement("button"); closeB.textContent = "Close"; closeB.onclick = hidePanel;
    var saveB = document.createElement("button"); saveB.className = "primary"; saveB.textContent = "Save";
    saveB.onclick = function () {
      var note = ta.value.trim();
      ann.note = note || null;
      if (replyTa && replyTa.value.trim()) {
        ann.replies.push({ id: uid("r"), author: "user", text: replyTa.value.trim(), createdAt: now() });
      }
      ann.updatedAt = now();
      decorate(ann);
      persistLocal(); hidePanel();
    };
    right.appendChild(closeB); right.appendChild(saveB);
    row.appendChild(left); row.appendChild(right);
    panel.appendChild(row);
    panel.style.display = "block";
    var top = window.scrollY + rect.bottom + 8;
    var left2 = Math.min(window.scrollX + rect.left, window.scrollX + document.documentElement.clientWidth - panel.offsetWidth - 16);
    panel.style.top = top + "px";
    panel.style.left = Math.max(8, left2) + "px";
    ta.focus();
  }
  document.addEventListener("click", function (ev) {
    var t = ev.target;
    if (t.classList && (t.classList.contains("ann") || t.classList.contains("ann-flag"))) {
      var id = t.dataset.annId;
      hideToolbar();
      openPanel(id, t.getBoundingClientRect());
      ev.stopPropagation();
    } else if (!panel.contains(t) && panel.style.display === "block") {
      hidePanel();
    }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { hidePanel(); hideToolbar(); }
  });

  loadInitial();
})();
