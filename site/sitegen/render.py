# SPDX-FileCopyrightText: 2026 Matteo Beretta
# SPDX-License-Identifier: GPL-3.0-or-later
"""The pages, as static HTML. Adapted from the owner's Wheelly generator
(src/guide/site.py): the same fixed contents with a filter, the same step
layout (picture on the left, a few points beside it), the same EN/IT pill
of real links, hreflang alternates and the same language redirect.

What changed from Wheelly:
  - any number of languages (languages.yaml), not two;
  - English at the root, every other language in /<code>/;
  - the texts come from YAML + PO instead of Python catalogues;
  - point labels, photo placeholders, tables, the scorecard.

No framework, no build step beyond this file. The JavaScript only adds
comfort (contents following the step, the filter, the scorecard's clicks,
"Expand all" for the "More" parts); without it every page still reads and
prints, and every "More" still opens.
"""
import html
import json
import os
import re

from . import markup

_e = lambda t: html.escape(t, quote=True)

# The contents follow the step being read (Wheelly's FOLLOW, unchanged).
FOLLOW = """
(function () {
  var indice = document.getElementById('indice');
  if (indice && window.innerWidth <= 1040) { indice.open = false; }
  var voci = {}, passi = [].slice.call(document.querySelectorAll('.passo'));
  passi.forEach(function (p) {
    var a = document.querySelector('.passi a[href="#' + p.id + '"]');
    if (a) { voci[p.id] = a; }
  });
  if (!passi.length || !('IntersectionObserver' in window)) { return; }
  var visti = {};
  var occhio = new IntersectionObserver(function (righe) {
    righe.forEach(function (r) { visti[r.target.id] = r.isIntersecting; });
    var scelto = passi.filter(function (p) { return visti[p.id]; })[0];
    passi.forEach(function (p) {
      if (voci[p.id]) { voci[p.id].classList.toggle('qui', scelto === p); }
    });
  }, { rootMargin: '-10% 0px -70% 0px' });
  passi.forEach(function (p) { occhio.observe(p); });
})();
"""

# The filter of the contents (Wheelly's FILTER; group headings carry no
# data-cerca, so they hide while filtering).
FILTER = """
(function () {
  var campo = document.getElementById('filtro');
  if (!campo) { return; }
  var indice = document.getElementById('indice');
  var vuoto = document.querySelector('.filtro-vuoto');
  var capi = [].slice.call(document.querySelectorAll('.indice nav > ol > li'));
  function piano(t) {
    return (t || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/_/g, ' ');
  }
  function filtra() {
    var q = piano(campo.value).trim(), trovate = 0;
    indice.classList.toggle('filtrando', q !== '');
    capi.forEach(function (c) {
      if (c.classList.contains('gruppo')) { c.hidden = q !== ''; return; }
      var tutto = q === '' || piano(c.dataset.cerca).indexOf(q) >= 0, qui = 0;
      [].slice.call(c.querySelectorAll('.passi > li')).forEach(function (v) {
        var si = tutto || piano(v.dataset.cerca).indexOf(q) >= 0;
        v.hidden = !si;
        if (si) { qui++; }
      });
      c.hidden = !(tutto || qui > 0);
      if (!c.hidden) { trovate++; }
    });
    vuoto.hidden = trovate > 0;
  }
  campo.addEventListener('input', filtra);
  campo.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { campo.value = ''; filtra(); }
  });
  // following a match: the words may be inside a closed "More" of that step,
  // so the step opens it (MORE, window.hcTrova) - here, or on the next page
  indice.addEventListener('click', function (e) {
    var a = e.target.closest('.passi a');
    var q = campo.value.trim();
    if (!a || q === '') { return; }
    var id = (a.getAttribute('href') || '').split('#')[1];
    if (!id) { return; }
    if (a.pathname === window.location.pathname && window.hcTrova) {
      setTimeout(function () { window.hcTrova(id, q); }, 0);
    } else {
      try { window.sessionStorage.setItem('hexcalibr-trova', JSON.stringify({ id: id, q: q })); } catch (err) { /* no storage */ }
    }
  });
})();
"""

# The "More" parts (<details class="approfondisci">): native, so they open with
# the keyboard and without JavaScript. This only adds comfort:
#  - "Expand all / Collapse all", remembered per page in localStorage;
#  - a link to an anchor inside a closed "More" opens it;
#  - a step reached from the side filter opens the "More" holding the words;
#  - printing opens every "More" and puts them back afterwards.
MORE = """
(function () {
  var tutti = [].slice.call(document.querySelectorAll('details.approfondisci'));
  if (!tutti.length) { return; }
  var btn = document.getElementById('tutto');
  var KEY = 'hexcalibr-more:' + window.location.pathname.split('/').slice(-2).join('/');
  function piano(t) {
    return (t || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase().replace(/_/g, ' ').replace(/\\s+/g, ' ');
  }
  function etichetta() {
    if (!btn) { return; }
    var aperti = tutti.every(function (d) { return d.open; });
    btn.textContent = aperti ? btn.dataset.chiudi : btn.dataset.apri;
    btn.setAttribute('aria-pressed', aperti ? 'true' : 'false');
  }
  function tutto(apri) { tutti.forEach(function (d) { d.open = apri; }); etichetta(); }
  if (btn) {
    btn.hidden = false;
    var salvato = null;
    try { salvato = window.localStorage.getItem(KEY); } catch (e) { salvato = null; }
    if (salvato === '1') { tutto(true); }
    btn.addEventListener('click', function () {
      var apri = !tutti.every(function (d) { return d.open; });
      tutto(apri);
      try { window.localStorage.setItem(KEY, apri ? '1' : '0'); } catch (e) { /* no storage */ }
    });
    document.addEventListener('toggle', function (e) {
      if (e.target.classList && e.target.classList.contains('approfondisci')) { etichetta(); }
    }, true);
    etichetta();
  }
  function antenati(el) {
    for (var d = el && el.parentElement; d; d = d.parentElement) {
      if (d.tagName === 'DETAILS') { d.open = true; }
    }
  }
  function alHash() {
    var id = decodeURIComponent(window.location.hash.slice(1));
    var el = id && document.getElementById(id);
    if (el && el.closest('details.approfondisci')) { antenati(el); el.scrollIntoView(); }
  }
  // the side filter found `q` in step `id`: open its "More" if the words are there
  window.hcTrova = function (id, q) {
    var passo = document.getElementById(id);
    if (!passo) { return; }
    q = piano(q);
    [].slice.call(passo.querySelectorAll('details.approfondisci')).forEach(function (d) {
      if (piano(d.textContent).indexOf(q) >= 0) { d.open = true; }
    });
  };
  alHash();
  window.addEventListener('hashchange', alHash);
  try {
    var t = JSON.parse(window.sessionStorage.getItem('hexcalibr-trova') || 'null');
    window.sessionStorage.removeItem('hexcalibr-trova');
    if (t && t.id) { window.hcTrova(t.id, t.q); }
  } catch (e) { /* no storage */ }
  var prima = null;
  window.addEventListener('beforeprint', function () {
    prima = tutti.map(function (d) { return d.open; });
    tutti.forEach(function (d) { d.open = true; });
  });
  window.addEventListener('afterprint', function () {
    if (prima) { tutti.forEach(function (d, i) { d.open = prima[i]; }); prima = null; etichetta(); }
  });
})();
"""

# THE LANGUAGE A VISITOR GETS - Wheelly's rule, generalised to N languages.
# English is the default. A visitor arriving on an English page from OUTSIDE
# the site is sent to the first of their browser languages that the site
# has, unless English comes first in their list. Inside the site the
# referrer says "already here", so a reader who clicked EN stays in English.
# No cookie, no storage. ?lang=xx forces a language. Opened from disk
# (file://) there is no "outside", so only ?lang= redirects there.
REDIRECT = """
(function () {
  var twins = %s;
  var params = new URLSearchParams(window.location.search);
  var pick = params.get('lang');
  var here = false;
  try {
    here = document.referrer !== '' &&
           new URL(document.referrer).origin === window.location.origin;
  } catch (e) { here = false; }
  var target = null;
  if (pick && twins[pick]) { target = pick; }
  else if (pick === null && !here && window.location.protocol !== 'file:') {
    var prefs = navigator.languages && navigator.languages.length ?
                navigator.languages : [navigator.language || ''];
    for (var i = 0; i < prefs.length; i++) {
      var c = (prefs[i] || '').toLowerCase().split('-')[0];
      if (c === 'en') { break; }
      if (twins[c]) { target = c; break; }
    }
  }
  if (target) { window.location.replace(twins[target] + window.location.hash); }
})();
"""

# The scorecard: a click cycles a cell blank -> pass -> fail hot -> fail cold
# -> not scored; the passes column and the suggested block are computed with
# the rules written on the page (owner rule C: the gate feature excludes a
# block, then most passes, then fewest failures, then the cooler block).
# Columns of weight "confirms" (data-count="0", the temperature tower's hole)
# cycle like the others but are never counted. Nothing is stored: the card is meant to be
# printed (or screenshotted) and kept with the spool.
SCORE = """
(function () {
  var tab = document.getElementById('scheda');
  if (!tab) { return; }
  var cycle = ['', 'P', 'H', 'C', '-'];
  var words = JSON.parse(tab.dataset.words);
  var gate = tab.dataset.gate;
  var presets = JSON.parse(tab.dataset.presets);
  var rows = [].slice.call(tab.querySelectorAll('tbody tr'));
  function cells(r) { return [].slice.call(r.querySelectorAll('.cella')); }
  function score() {
    var best = null, results = [];
    rows.forEach(function (r, i) {
      var p = 0, hot = 0, cold = 0, any = false, gated = false;
      cells(r).forEach(function (c) {
        var v = c.dataset.v;
        if (c.dataset.count === '0') { return; }
        if (v) { any = true; }
        if (v === 'P') { p++; } else if (v === 'H') { hot++; } else if (v === 'C') { cold++; }
        if (c.dataset.f === gate && (v === 'C' || v === 'H')) { gated = true; }
      });
      r.querySelector('.voto').textContent = any ? (gated ? '\\u2715' : p) : '';
      r.classList.remove('migliore');
      if (any && !gated) { results.push({ i: i, p: p, f: hot + cold, t: r.querySelector('.temp input').value }); }
    });
    var out = document.getElementById('esito');
    if (!results.length) { out.textContent = ''; return; }
    var top = Math.max.apply(null, results.map(function (x) { return x.p; }));
    var tied = results.filter(function (x) { return x.p === top; });
    var fewest = Math.min.apply(null, tied.map(function (x) { return x.f; }));
    tied = tied.filter(function (x) { return x.f === fewest; });
    // still a tie: the cooler block wins. By the temperatures typed in when
    // every tied row has one; otherwise by position (block 1 is the hottest).
    var known = tied.every(function (x) { return x.t !== '' && !isNaN(parseFloat(x.t)); });
    var pick = tied.reduce(function (a, b) {
      if (known) { return parseFloat(b.t) < parseFloat(a.t) ? b : a; }
      return b.i > a.i ? b : a;
    });
    rows[pick.i].classList.add('migliore');
    out.textContent = words.best.replace('%s', pick.t ? pick.t + ' \u00b0C' : words.block + ' ' + (pick.i + 1)) +
                      (tied.length > 1 ? ' ' + words.tie : '');
  }
  tab.addEventListener('click', function (e) {
    var c = e.target.closest('.cella');
    if (!c) { return; }
    var v = cycle[(cycle.indexOf(c.dataset.v) + 1) % cycle.length];
    c.dataset.v = v; c.textContent = v === '-' ? '\\u2013' : (v === 'P' ? '\\u2713' : v);
    c.setAttribute('aria-label', c.dataset.name + ': ' + (words[v] || words.empty));
    score();
  });
  var sel = document.getElementById('preset');
  if (sel) {
    sel.addEventListener('change', function () {
      var t = presets[sel.value] || [];
      rows.forEach(function (r, i) {
        var inp = r.querySelector('.temp input');
        inp.value = t[i] !== undefined ? t[i] : '';
        r.hidden = sel.value !== '' && t[i] === undefined;
      });
      score();
    });
  }
  var clear = document.getElementById('azzera');
  if (clear) {
    clear.addEventListener('click', function () {
      rows.forEach(function (r) { cells(r).forEach(function (c) {
        c.dataset.v = ''; c.textContent = ''; c.setAttribute('aria-label', c.dataset.name + ': ' + words.empty); }); });
      score();
    });
  }
  var pr = document.getElementById('stampa');
  if (pr) { pr.addEventListener('click', function () { window.print(); }); }
})();
"""


# The pressure-advance card (features `scoring: bands`): a click cycles a cell
# blank -> pass -> L too low -> H too high -> not scored. The suggested band
# follows the rule written on the page (docs/dev/pressure-advance-features.md):
# a band qualifies when the 90 degree tips pass and no counted probe is too
# high; the lowest qualifying band wins, unless the band just above also
# qualifies with at least as many passes (tie: lean higher). Columns of weight
# "confirms" (data-count="0", v1.2.1: the inside corners, always rounded by the
# bead width whatever the PA) cycle like the others but are never counted:
# no passes, no tie-break, no veto. Band 1 or the top band means the range must be shifted. With a
# firmware preset (or typed values) it also suggests the fine-pass command.
SCORE_BANDS = """
(function () {
  var tab = document.getElementById('scheda');
  if (!tab) { return; }
  var cycle = ['', 'P', 'L', 'H', '-'];
  var words = JSON.parse(tab.dataset.words);
  var presets = JSON.parse(tab.dataset.presets);
  var rows = [].slice.call(tab.querySelectorAll('tbody tr'));
  var fw = '', pre = '', vari = '';
  function cells(r) { return [].slice.call(r.querySelectorAll('.cella')); }
  function value(r) { return r.querySelector('.temp input').value.trim().replace(',', '.'); }
  function fmt(x) { return String(parseFloat(x.toFixed(5))); }
  function qualifies(s) {
    if (s.tip90 !== 'P') { return false; }
    for (var k in s) { if (s[k] === 'H') { return false; } }
    return true;
  }
  function score() {
    var info = rows.filter(function (r) { return !r.hidden; }).map(function (r) {
      var s = {}, p = 0, any = false;
      cells(r).forEach(function (c) {
        if (c.dataset.v) { any = true; }
        if (c.dataset.count === '0') { return; }
        s[c.dataset.f] = c.dataset.v;
        if (c.dataset.v === 'P') { p++; }
      });
      r.querySelector('.voto').textContent = any ? p : '';
      r.classList.remove('migliore');
      return { r: r, p: p, any: any, ok: any && qualifies(s) };
    });
    var out = document.getElementById('esito'), fine = document.getElementById('fine');
    out.textContent = ''; fine.textContent = '';
    if (!info.some(function (x) { return x.any; })) { return; }
    var k = -1;
    for (var i = 0; i < info.length; i++) { if (info[i].ok) { k = i; break; } }
    if (k < 0) { out.textContent = words.none; return; }
    var tie = false;
    if (k + 1 < info.length && info[k + 1].ok && info[k + 1].p >= info[k].p) { k++; tie = true; }
    var pick = info[k];
    pick.r.classList.add('migliore');
    var v = value(pick.r);
    out.textContent = words.best.replace('%s', rows.indexOf(pick.r) + 1).replace('%s', v || '?') +
                      (tie ? ' ' + words.tie : '') +
                      (k === 0 || k === info.length - 1 ? ' ' + words.edge : '');
    if (!words.fine || !fw || k === 0 || k === info.length - 1) { return; }
    var here = parseFloat(value(pick.r)), below = parseFloat(value(info[k - 1].r));
    var step = here - below;
    if (isNaN(here) || isNaN(below) || step <= 0) { return; }
    // v1.3: after a coarse file, the fine file centred on the pick (the preset's fine step);
    // after a fine file, the same at a quarter of its step
    fine.textContent = words.fine.replace('%s', pre
      ? 'python3 -I calib.py pressure-advance --preset ' + pre + ' --centre ' + fmt(here) +
        (vari === 'coarse' ? '' : ' --step ' + fmt(step / 4))
      : 'python3 -I calib.py pressure-advance --firmware ' + fw +
        ' --start ' + fmt(Math.max(0, here - step)) + ' --end ' + fmt(here + step) + ' --step ' + fmt(step / 4));
  }
  tab.addEventListener('click', function (e) {
    var c = e.target.closest('.cella');
    if (!c) { return; }
    var v = cycle[(cycle.indexOf(c.dataset.v) + 1) % cycle.length];
    c.dataset.v = v; c.textContent = v === '-' ? '\\u2013' : (v === 'P' ? '\\u2713' : v);
    c.setAttribute('aria-label', c.dataset.name + ': ' + (words[v] || words.empty));
    score();
  });
  tab.addEventListener('input', score);
  var sel = document.getElementById('preset');
  if (sel) {
    sel.addEventListener('change', function () {
      var pr = presets[sel.value] || { v: [], fw: '' };
      fw = pr.fw; pre = pr.p || ''; vari = pr["var"] || '';
      rows.forEach(function (r, i) {
        r.querySelector('.temp input').value = pr.v[i] !== undefined ? pr.v[i] : '';
        r.hidden = sel.value !== '' && pr.v[i] === undefined;
      });
      score();
    });
  }
  var clear = document.getElementById('azzera');
  if (clear) {
    clear.addEventListener('click', function () {
      rows.forEach(function (r) { cells(r).forEach(function (c) {
        c.dataset.v = ''; c.textContent = ''; c.setAttribute('aria-label', c.dataset.name + ': ' + words.empty); }); });
      score();
    });
  }
  var pr = document.getElementById('stampa');
  if (pr) { pr.addEventListener('click', function () { window.print(); }); }
})();
"""


# The maximum-flow card (features `scoring: flow`): one wall cell per band that
# cycles blank -> pass -> degrading -> fail -> not scored, and two flags (heater
# sag, extruder clicks) that toggle. The rule is the one written on the page
# (docs/dev/max-flow-features.md §6): the onset is the lowest band whose wall
# fails or that has a flag; the limit is the band below it; the suggestion is
# 85 % of the limit (80 % when the limit band was degrading), with 80/85/90 %
# shown. Nothing is stored.
SCORE_FLOW = """
(function () {
  var tab = document.getElementById('scheda');
  if (!tab) { return; }
  var cycle = ['', 'P', 'D', 'F', '-'];
  var marks = { P: '\\u2713', D: '\\u25d0', F: '\\u2715', '-': '\\u2013', Y: '\\u25cf' };
  var words = JSON.parse(tab.dataset.words);
  var presets = JSON.parse(tab.dataset.presets);
  var rows = [].slice.call(tab.querySelectorAll('tbody tr'));
  function cell(r, f) { return r.querySelector('.cella[data-f="' + f + '"]'); }
  function flow(r) { return parseFloat(r.querySelector('.temp input').value.trim().replace(',', '.')); }
  function down(x) { return String(Math.floor(x * 10 + 1e-9) / 10); }
  function fill(t, a) { a.forEach(function (v) { t = t.replace('%s', v); }); return t; }
  function score() {
    var vis = rows.filter(function (r) { return !r.hidden; });
    var out = document.getElementById('esito'), more = document.getElementById('fine');
    out.textContent = ''; more.textContent = '';
    rows.forEach(function (r) { r.classList.remove('migliore'); });
    var info = vis.map(function (r) {
      var w = cell(r, 'wall').dataset.v, sag = cell(r, 'heater').dataset.v === 'Y',
          clk = cell(r, 'clicks').dataset.v === 'Y';
      return { r: r, w: w, bad: w === 'F' || sag || clk, any: w !== '' || sag || clk };
    });
    if (!info.some(function (x) { return x.any; })) { return; }
    var k = -1;
    for (var i = 0; i < info.length; i++) { if (info[i].bad) { k = i; break; } }
    if (k === 0) { out.textContent = words.first; return; }
    if (k < 0) {
      if (info.every(function (x) { return x.w === 'P' || x.w === 'D'; })) { out.textContent = words.none; }
      return;
    }
    var lim = info[k - 1];
    if (lim.w !== 'P' && lim.w !== 'D') { out.textContent = fill(words.unscored, [rows.indexOf(lim.r) + 1]); return; }
    lim.r.classList.add('migliore');
    var q = flow(lim.r), pct = lim.w === 'D' ? 80 : 85;
    if (isNaN(q)) { out.textContent = fill(words.noflow, [rows.indexOf(lim.r) + 1]); return; }
    out.textContent = fill(words.best, [rows.indexOf(info[k].r) + 1, rows.indexOf(lim.r) + 1, q, down(q * pct / 100), pct]);
    var extra = [fill(words.range, [down(q * 0.8), down(q * 0.85), down(q * 0.9)])];
    if (info.slice(k + 1).some(function (x) { return x.w === 'P'; })) { extra.push(words.noisy); }
    more.textContent = extra.join(' ');
  }
  tab.addEventListener('click', function (e) {
    var c = e.target.closest('.cella');
    if (!c) { return; }
    var v = c.dataset.toggle ? (c.dataset.v === 'Y' ? '' : 'Y') : cycle[(cycle.indexOf(c.dataset.v) + 1) % cycle.length];
    c.dataset.v = v; c.textContent = marks[v] || '';
    c.setAttribute('aria-label', c.dataset.name + ': ' + (words[v] || words.empty));
    score();
  });
  tab.addEventListener('input', score);
  var sel = document.getElementById('preset');
  if (sel) {
    sel.addEventListener('change', function () {
      var t = presets[sel.value] || [];
      rows.forEach(function (r, i) {
        r.querySelector('.temp input').value = t[i] !== undefined ? t[i] : '';
        r.hidden = sel.value !== '' && t[i] === undefined;
      });
      score();
    });
  }
  var clear = document.getElementById('azzera');
  if (clear) {
    clear.addEventListener('click', function () {
      rows.forEach(function (r) { [].slice.call(r.querySelectorAll('.cella')).forEach(function (c) {
        c.dataset.v = ''; c.textContent = ''; c.setAttribute('aria-label', c.dataset.name + ': ' + words.empty); }); });
      score();
    });
  }
  var pr = document.getElementById('stampa');
  if (pr) { pr.addEventListener('click', function () { window.print(); }); }
})();
"""


# The IDEX alignment card (features `scoring: idex`). IDEX_FIT is a line-by-line
# port of calib.py idex-analyze (hexcalibr-core suite/tests/idex_alignment.py:
# combine, fit_plane, analyze, corrections; thresholds from idex_alignment.toml
# [analysis]). Per axis, least squares reading = c0 + cx*x + cy*y over the
# stations' read positions (mm from the bed centre, features/idex-alignment.yaml).
# Kept free of the DOM so it can be checked against the Python analyzer with node
# (the markers below delimit it). Differences: a fine reading outside +-0.50 is
# skipped with a note instead of stopping the whole analysis; -0 prints as 0; the
# thresholds allow 1e-9 of float noise, so an effect of exactly 0.05 mm is always
# "watch"/"fix" (Python can land either side of it, depending on rounding).
IDEX_FIT = """
/*IDEX_FIT*/
var IDEX_FIT = (function () {
  // eps: a reading of exactly 0.05 or 0.10 mm must not flip on float noise ("ok below 0.05")
  var A = { sigma: 0.025, ok: 0.05, fix: 0.10, finePitch: 1.1, fineRange: 0.5, coarseStep: 0.2, eps: 1e-9 };
  function solve(M0, b) {
    var n = b.length, M = M0.map(function (r, i) { return r.slice().concat([b[i]]); }), r, k;
    for (var c = 0; c < n; c++) {
      var piv = c;
      for (r = c + 1; r < n; r++) { if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) { piv = r; } }
      if (Math.abs(M[piv][c]) < 1e-12) { throw new Error('singular'); }
      var t = M[c]; M[c] = M[piv]; M[piv] = t;
      for (r = 0; r < n; r++) {
        if (r !== c) { var f = M[r][c] / M[c][c]; for (k = c; k <= n; k++) { M[r][k] -= f * M[c][k]; } }
      }
    }
    return M.map(function (row, i) { return row[n] / row[i]; });
  }
  function inverse(M) {
    var n = M.length, cols = [];
    for (var j = 0; j < n; j++) {
      var e = []; for (var i = 0; i < n; i++) { e.push(i === j ? 1 : 0); }
      cols.push(solve(M, e));
    }
    return cols[0].map(function (_, i) { return cols.map(function (col) { return col[i]; }); });
  }
  function fitPlane(pts, floor) {
    var n = pts.length, full = n >= 3, c, inv, i, j;
    if (full) {
      var M = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], b = [0, 0, 0];
      pts.forEach(function (p) {
        var r = [1, p[0], p[1]];
        for (i = 0; i < 3; i++) { for (j = 0; j < 3; j++) { M[i][j] += r[i] * r[j]; } b[i] += r[i] * p[2]; }
      });
      try { c = solve(M, b); inv = inverse(M); } catch (e) { full = false; }
    }
    if (!full) {
      var mean = pts.reduce(function (s, p) { return s + p[2]; }, 0) / n;
      c = [mean, 0, 0]; inv = [[1 / n, 0, 0], [0, 0, 0], [0, 0, 0]];
    }
    var pred = pts.map(function (p) { return c[0] + c[1] * p[0] + c[2] * p[1]; });
    var res = pts.map(function (p, k) { return p[2] - pred[k]; });
    var dof = n - (full ? 3 : 1);
    var sres = dof > 0 ? Math.sqrt(res.reduce(function (s, r) { return s + r * r; }, 0) / dof) : 0;
    var sig = Math.max(sres, floor);
    var se = [0, 1, 2].map(function (k) { return sig * Math.sqrt(Math.max(inv[k][k], 0)); });
    return { c: c, se: se, pred: pred, res: res, rms: sres, full: full };
  }
  function r4(v) { return Math.round(v * 1e4) / 1e4; }
  function combine(f, co) {
    if (f == null && co == null) { return null; }
    if (f == null) { return { v: co, shift: 0, warn: false }; }
    if (co == null) { return { v: f, shift: 0, warn: false }; }
    var best = f;
    [-1, 0, 1].map(function (k) { return f + k * A.finePitch; }).forEach(function (v, i) {
      if (i === 0 || Math.abs(v - co) < Math.abs(best - co)) { best = v; }
    });
    return { v: r4(best), shift: best - f, warn: Math.abs(best - co) > A.coarseStep + 1e-9 };
  }
  function status(e, se) {
    e = Math.abs(e);
    if (e < A.ok - A.eps || e < 2 * se) { return 'ok'; }
    return e < A.fix - A.eps ? 'watch' : 'fix';
  }
  // bed = {vernier|lite: {span: [x, y], st: {n: [xx, xy, yx, yy]}}}; readings = {n: {x, y, xc, yc}}
  function analyze(bed, variant, readings) {
    var geo = bed[variant], rows = [], notes = [], per = { x: [], y: [] }, byStation = {};
    Object.keys(readings).map(Number).sort(function (a, b) { return a - b; }).forEach(function (st) {
      if (!geo.st[st]) { return; }
      var r = readings[st], row = { station: st };
      ['x', 'y'].forEach(function (ax) {
        var f = r[ax], co = r[ax + 'c'], val;
        if (variant === 'lite') {
          if (f == null) { return; }
          val = f;
        } else {
          if (f != null && Math.abs(f) > A.fineRange + 1e-9) { notes.push({ k: 'range', st: st, ax: ax }); return; }
          var cb = combine(f, co);
          if (!cb) { return; }
          val = cb.v;
          if (Math.abs(cb.shift) > 1e-9) { notes.push({ k: 'unwrapped', st: st, ax: ax, shift: cb.shift }); }
          if (cb.warn) { notes.push({ k: 'disagree', st: st, ax: ax, coarse: co, fine: cb.v }); }
        }
        var p = geo.st[st];
        per[ax].push(ax === 'x' ? [p[0], p[1], val, st] : [p[2], p[3], val, st]);
        row[ax] = val;
      });
      rows.push(row); byStation[st] = row;
    });
    var span = { x: geo.span[0], y: geo.span[1] }, fits = {}, terms = [];
    ['x', 'y'].forEach(function (ax) {
      var pts = per[ax];
      if (!pts.length) { return; }
      var f = fitPlane(pts.map(function (p) { return [p[0], p[1], p[2]]; }), A.sigma);
      fits[ax] = f;
      pts.forEach(function (p, i) {
        byStation[p[3]][ax + '_fit'] = r4(f.pred[i]);
        byStation[p[3]][ax + '_residual'] = r4(f.res[i]);
        if (Math.abs(f.res[i]) > Math.max(A.fix, 3 * A.sigma)) { notes.push({ k: 'outlier', st: p[3], ax: ax, res: f.res[i] }); }
      });
      terms.push({ term: ax + '0', value: f.c[0], se: f.se[0], status: Math.abs(f.c[0]) < A.ok - A.eps ? 'ok' : 'fix' });
      if (f.full) {
        [[1, 'x'], [2, 'y']].forEach(function (q) {
          var eff = f.c[q[0]] * span[q[1]], see = f.se[q[0]] * span[q[1]];
          terms.push({ term: 'd' + ax + '_d' + q[1], slope100: f.c[q[0]] * 100, effect: eff, seEffect: see,
                       status: status(eff, see) });
        });
      } else if (pts.length > 1) { notes.push({ k: 'few', ax: ax }); }
    });
    var out = { stations: rows, terms: terms, notes: notes };
    if (fits.x && fits.y && fits.x.full && fits.y.full) {
      var cxy = fits.x.c[2], cyx = fits.y.c[1], rot = (cyx - cxy) / 2, sh = (cxy + cyx) / 2;
      out.rotation = { mrad: rot * 1000, effect: rot * Math.max(span.x, span.y) };
      out.shear = { per100: sh * 100 };
    }
    out.offset = { x: fits.x ? fits.x.c[0] : 0, y: fits.y ? fits.y.c[0] : 0 };
    return out;
  }
  function sgn(v, d) { var s = v.toFixed(d); return s.charAt(0) === '-' ? s : '+' + s; }
  function g3(v) { var r = Math.round(v * 1000) / 1000; return String(r === 0 ? 0 : r); }
  // new = old + reading everywhere (idex_alignment.toml [[corrections]], tool 1)
  function corrections(dx, dy, cx, cy) {
    return {
      ratos: (cx != null && cy != null) ? 'SAVE_VARIABLE VARIABLE=idex_xoffset VALUE=' + g3(cx + dx) +
             '\\nSAVE_VARIABLE VARIABLE=idex_yoffset VALUE=' + g3(cy + dy) : null,
      prusaslicer: 'X ' + sgn(dx, 3) + ', Y ' + sgn(dy, 3),
      xl: 'X ' + sgn(dx, 2) + ', Y ' + sgn(dy, 2),
      marlin: 'M218 T1 X<current ' + sgn(dx, 3) + '> Y<current ' + sgn(dy, 3) + '>, then M500'
    };
  }
  return { analyze: analyze, corrections: corrections, fitPlane: fitPlane, combine: combine, sgn: sgn };
})();
/*END_IDEX_FIT*/
"""

SCORE_IDEX = """
(function () {
  var tab = document.getElementById('idex');
  if (!tab) { return; }
  var W = JSON.parse(tab.dataset.words), beds = JSON.parse(tab.dataset.beds), T = JSON.parse(tab.dataset.terms);
  var selBed = document.getElementById('idex-bed'), selVar = document.getElementById('idex-variant');
  var curX = document.getElementById('idex-cx'), curY = document.getElementById('idex-cy');
  var rows = [].slice.call(tab.querySelectorAll('tbody tr'));
  var out = document.getElementById('esito'), KEY = 'hexcalibr-idex-previous', last = null;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fill(s) { var a = [].slice.call(arguments, 1); return s.replace(/%s/g, function () { return a.length ? a.shift() : ''; }); }
  function num(s, lite) {
    s = (s || '').trim().replace(',', '.').replace(/\\u2212|\\u2013/g, '-');
    if (s === '') { return null; }
    if (lite) {
      if (s === '+') { return 0.1; }
      if (s === '-') { return -0.1; }
      if (/^ok$/i.test(s)) { return 0; }
    }
    return /^[+-]?(\\d+\\.?\\d*|\\.\\d+)$/.test(s) ? parseFloat(s) : NaN;
  }
  function bed() { for (var i = 0; i < beds.length; i++) { if (beds[i].id === selBed.value) { return beds[i]; } } return null; }
  function loadPrev() { try { return JSON.parse(window.localStorage.getItem(KEY) || 'null'); } catch (e) { return null; } }
  function f3(v) { return IDEX_FIT.sgn(v, 3); }
  function compute() {
    var b = bed(), lite = selVar.value === 'lite', readings = {}, bad = [], any = false;
    rows.forEach(function (r) {
      var st = r.dataset.st, on = !b || !!b[selVar.value].st[st];
      r.hidden = !on;
      r.querySelectorAll('input.c').forEach(function (i) { i.disabled = lite; });
      r.querySelector('.fit').textContent = ''; r.querySelector('.res').textContent = '';
      r.classList.remove('fuori');
      if (!on) { return; }
      var v = {};
      r.querySelectorAll('input').forEach(function (i) {
        if (i.disabled) { return; }
        var x = num(i.value, lite);
        if (x === null) { return; }
        any = true;
        if (isNaN(x)) { bad.push([st, i.dataset.k]); return; }
        v[i.dataset.k] = x;
      });
      if (Object.keys(v).length) { readings[st] = v; }
    });
    last = null;
    if (!any) { out.innerHTML = ''; return; }
    if (!b) { out.innerHTML = '<p>' + esc(W.need_bed) + '</p>'; return; }
    var res = IDEX_FIT.analyze(b, selVar.value, readings);
    res.bed = b.id; res.variant = selVar.value;
    last = res;
    res.stations.forEach(function (s) {
      var r = tab.querySelector('tr[data-st="' + s.station + '"]');
      r.querySelector('.fit').textContent = (s.x_fit !== undefined ? f3(s.x_fit) : '\\u2013') + ' / ' + (s.y_fit !== undefined ? f3(s.y_fit) : '\\u2013');
      r.querySelector('.res').textContent = (s.x_residual !== undefined ? f3(s.x_residual) : '\\u2013') + ' / ' + (s.y_residual !== undefined ? f3(s.y_residual) : '\\u2013');
    });
    var prev = loadPrev();
    if (prev && (prev.bed !== res.bed || prev.variant !== res.variant)) { prev = null; }
    var h = ['<h3>' + esc(W.result) + '</h3>'];
    if (lite) { h.push('<p>' + esc(W.lite_only) + '</p>'); }
    else { h.push('<p class="idex-offset">' + esc(fill(W.offset, f3(res.offset.x), f3(res.offset.y))) + '</p>'); }
    h.push('<div class="tabella"><table class="idex-termini"><thead><tr><th>' + esc(W.term) + '</th><th>' + esc(W.value) + '</th>' +
           (prev ? '<th>' + esc(W.previous) + '</th>' : '') + '<th>' + esc(W.verdict) + '</th><th>' + esc(W.cause) +
           '</th><th>' + esc(W.action) + '</th></tr></thead><tbody>');
    var mech = false;
    function val(t) { return t.value !== undefined ? f3(t.value) + ' mm' : fill(W.slope, f3(t.effect), IDEX_FIT.sgn(t.slope100, 4)); }
    res.terms.forEach(function (t) {
      var d = T[t.term] || {}, p = null;
      if (t.status === 'fix' && t.value === undefined) { mech = true; }
      if (prev) { prev.terms.forEach(function (q) { if (q.term === t.term) { p = q; } }); }
      h.push('<tr class="st-' + t.status + '"><th scope="row">' + esc(d.name || t.term) + ' <code>' + esc(t.term) + '</code></th><td>' +
             esc(val(t)) + '</td>' + (prev ? '<td>' + (p ? esc(val(p)) + ' (' + esc(W[p.status]) + ')' : '') + '</td>' : '') +
             '<td><b class="esito-' + t.status + '">' + esc(W[t.status]) + '</b></td><td>' + (d.cause || '') + '</td><td>' +
             (t.status !== 'ok' ? (d.action || '') + (d.vc4 ? '<br><small>' + d.vc4 + '</small>' : '') : '') + '</td></tr>');
    });
    h.push('</tbody></table></div>');
    if (res.rotation) {
      h.push('<p>' + esc(fill(W.rotation, IDEX_FIT.sgn(res.rotation.mrad, 3), f3(res.rotation.effect), IDEX_FIT.sgn(res.shear.per100, 4))) + '</p>');
    }
    var COL = { x: W.x_fine, xc: W.x_coarse, y: W.y_fine, yc: W.y_coarse };
    var notes = bad.map(function (x) { return fill(W.bad, x[0], COL[x[1]]); });
    res.notes.forEach(function (n) {
      var ax = (n.ax || '').toUpperCase();
      if (n.k === 'outlier') { notes.push(fill(W.outlier, n.st, ax, f3(n.res))); }
      else if (n.k === 'disagree') { notes.push(fill(W.disagree, n.st, ax, f3(n.coarse), f3(n.fine))); }
      else if (n.k === 'unwrapped') { notes.push(fill(W.unwrapped, n.st, ax, IDEX_FIT.sgn(n.shift, 2))); }
      else if (n.k === 'range') { notes.push(fill(W.range, n.st, ax)); }
      else if (n.k === 'few') { notes.push(fill(W.few, ax)); }
    });
    if (mech) { notes.unshift(W.mech_first); }
    if (notes.length) { h.push('<ul class="punti idex-note">' + notes.map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('') + '</ul>'); }
    if (!lite) {
      var cx = num(curX.value, false), cy = num(curY.value, false);
      cx = (cx === null || isNaN(cx)) ? null : cx; cy = (cy === null || isNaN(cy)) ? null : cy;
      var c = IDEX_FIT.corrections(res.offset.x, res.offset.y, cx, cy);
      h.push('<h3>' + esc(W.corr) + '</h3><p><b>RatOS</b></p>');
      h.push(c.ratos ? '<pre class="idex-cmd">' + esc(c.ratos) + '</pre>' : '<p>' + esc(W.ratos_cur) + '</p>');
      h.push('<p>' + esc(W.ps) + ' <code>' + esc(c.prusaslicer) + '</code></p>');
      h.push('<p>' + esc(W.xl) + ' <code>' + esc(c.xl) + '</code></p>');
      h.push('<p>' + esc(W.marlin) + ' <code>' + esc(c.marlin) + '</code></p>');
      h.push('<p class="idex-th1">' + esc(W.th1) + '</p>');
    }
    out.innerHTML = h.join('');
  }
  tab.addEventListener('input', compute);
  [selBed, selVar, curX, curY].forEach(function (el) { el.addEventListener('input', compute); el.addEventListener('change', compute); });
  document.getElementById('azzera').addEventListener('click', function () {
    tab.querySelectorAll('input').forEach(function (i) { i.value = ''; }); compute();
  });
  document.getElementById('stampa').addEventListener('click', function () { window.print(); });
  document.getElementById('idex-ricorda').addEventListener('click', function () {
    if (!last) { return; }
    try { window.localStorage.setItem(KEY, JSON.stringify({ bed: last.bed, variant: last.variant, terms: last.terms })); } catch (e) { return; }
    compute();
  });
  document.getElementById('idex-dimentica').addEventListener('click', function () {
    try { window.localStorage.removeItem(KEY); } catch (e) { /* nothing stored */ }
    compute();
  });
  document.getElementById('idex-copia').addEventListener('click', function () {
    var lines = [selBed.options[selBed.selectedIndex].text + ', ' + selVar.options[selVar.selectedIndex].text];
    rows.forEach(function (r) {
      if (r.hidden) { return; }
      var v = [].slice.call(r.querySelectorAll('input')).map(function (i) { return i.dataset.k + '=' + (i.value || '-'); });
      lines.push(r.dataset.st + ': ' + v.join(' '));
    });
    var text = lines.join('\\n') + '\\n\\n' + out.innerText;
    var done = function () { var b = document.getElementById('idex-copia'), t = b.textContent; b.textContent = W.copied; setTimeout(function () { b.textContent = t; }, 1500); };
    if (navigator.clipboard) { navigator.clipboard.writeText(text).then(done, function () {}); }
  });
  compute();
})();
"""


def page_file(pid):
    return "index.html" if pid == "home" else pid + ".html"


class Site:
    """One language's view of the site: translated sources plus the helpers
    every page needs."""

    def __init__(self, src, lang, langs, photos_dir, values):
        self.src, self.lang, self.langs = src, lang, langs
        self.site, self.ui, self.pages = src["site"], src["ui"], src["pages"]
        self.features = src["features"]
        self.photos_dir = photos_dir
        # photographer briefs: off on the published site, HEXCALIBR_BRIEFS=1 for the owner's local builds
        self.briefs = bool(self.site.get("show_photo_briefs")) or os.environ.get("HEXCALIBR_BRIEFS") == "1"
        # {{TBD}} marks: dropped on the public site, highlighted in drafts (HEXCALIBR_TBD=1)
        tbd = bool(self.site.get("show_tbd")) or os.environ.get("HEXCALIBR_TBD") == "1"
        # the model generator (calib.py) lives in a private repository: while it is,
        # the points that tell readers to run it are left out (generator_public: true
        # in site.yaml brings them back), and the PA card does not print a command
        self.generator = bool(self.site.get("generator_public"))
        self.values = dict(values, _tbd=tbd, _pending=self.ui["link_pending"])
        self.root = "" if lang == "en" else "../"
        self.base = (self.site.get("base_url") or "").rstrip("/")
        self.order = [e["page"] for g in self.site["contents"] for e in g["entries"]
                      if "page" in e]
        self.photos_used = []

    # ------------------------------------------------------------- helpers
    def T(self, key):
        return self.ui[key]

    def md(self, text):
        return markup.inline(text, self.values, self.resolve)

    def paras(self, text):
        return markup.paragraphs(text, self.values, self.resolve)

    def plain(self, text):
        return markup.plain(text, self.values)

    def resolve(self, target):
        """page:<id>[#anchor] -> a relative URL in this language;
        link:<name> -> the address in site.yaml `links:` ("#" while unknown)."""
        if target.startswith("link:"):
            name = target[len("link:"):]
            links = self.site.get("links") or {}
            if name not in links:
                raise SystemExit("link to an unknown address: link:%s (add it to site.yaml links:)" % name)
            addr = links[name]
            if isinstance(addr, dict):   # one address per language, e.g. a local Amazon store
                addr = addr.get(self.lang) or addr.get("default") or addr.get("en") or ""
            return addr or ""   # empty: markup shows the words greyed, "coming soon"
        target = target[len("page:"):]
        pid, _, anchor = target.partition("#")
        if pid not in self.pages:
            raise SystemExit("link to an unknown page: page:%s" % target)
        return page_file(pid) + ("#" + anchor if anchor else "")

    def twin(self, pid, towards):
        """Relative URL of page `pid` in language `towards`, from this page."""
        f = page_file(pid)
        if towards == self.lang:
            return f
        if self.lang == "en":
            return "%s/%s" % (towards, f)
        return ("../" + f) if towards == "en" else ("../%s/%s" % (towards, f))

    def absolute(self, pid, towards):
        rel = page_file(pid) if towards == "en" else "%s/%s" % (towards, page_file(pid))
        if self.base:
            return self.base + "/" + (rel if rel != "index.html" else "").replace("/index.html", "/")
        return self.twin(pid, towards)

    # ---------------------------------------------------------------- head
    def head(self, pid, title, description):
        r = ["<!doctype html>", "<html lang=\"%s\">" % self.lang, "<head>",
             "<meta charset=\"utf-8\">",
             "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
             "<meta name=\"color-scheme\" content=\"light dark\">",
             "<title>%s</title>" % _e(title),
             "<meta name=\"description\" content=\"%s\">" % _e(description),
             "<link rel=\"canonical\" href=\"%s\">" % self.absolute(pid, self.lang)]
        for code in self.langs:
            r.append("<link rel=\"alternate\" hreflang=\"%s\" href=\"%s\">"
                     % (code, self.absolute(pid, code)))
        r.append("<link rel=\"alternate\" hreflang=\"x-default\" href=\"%s\">"
                 % self.absolute(pid, "en"))
        if self.lang == "en" and len(self.langs) > 1:
            twins = {c: self.twin(pid, c) for c in self.langs if c != "en"}
            r.append("<script>%s</script>" % (REDIRECT % json.dumps(twins)))
        if self.base:   # link previews (Printables, forums, chats): the brand card
            r += ["<meta property=\"og:type\" content=\"website\">",
                  "<meta property=\"og:title\" content=\"%s\">" % _e(title),
                  "<meta property=\"og:description\" content=\"%s\">" % _e(description),
                  "<meta property=\"og:url\" content=\"%s\">" % self.absolute(pid, self.lang),
                  "<meta property=\"og:image\" content=\"%s/og-image.png\">" % self.base,
                  "<meta name=\"twitter:card\" content=\"summary_large_image\">"]
        r += ["<link rel=\"icon\" type=\"image/svg+xml\" href=\"%sfavicon.svg\">" % self.root,
              "<link rel=\"apple-touch-icon\" href=\"%sicon-256.png\">" % self.root,
              "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">",
              "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>",
              "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?"
              "family=Fredoka:wght@500;600&family=Sora:wght@400;700&display=swap\">",
              "<link rel=\"stylesheet\" href=\"%sguide.css\">" % self.root,
              "</head>", "<body>",
              "<a class=\"salta\" href=\"#contenuto\">%s</a>" % _e(self.T("skip_to_content")),
              "<div class=\"pagina\">"]
        return "\n".join(r)

    def language_switch(self, pid, expand=False):
        r = ["<div class=\"testata\">"]
        if expand:
            # shown by MORE (hidden without JavaScript, where it could do nothing)
            r.append("<button type=\"button\" class=\"tutto\" id=\"tutto\" hidden aria-pressed=\"false\" "
                     "data-apri=\"%s\" data-chiudi=\"%s\">%s</button>"
                     % (_e(self.T("more_expand_all")), _e(self.T("more_collapse_all")),
                        _e(self.T("more_expand_all"))))
        r.append("<nav class=\"lang-switch\" aria-label=\"%s\">" % _e(self.T("language")))
        for code, info in self.langs.items():
            active = code == self.lang
            r.append("<a class=\"lang-btn%s\"%s href=\"%s\" hreflang=\"%s\" lang=\"%s\" "
                     "aria-label=\"%s\">%s</a>"
                     % (" is-active" if active else "",
                        " aria-current=\"page\"" if active else "",
                        self.twin(pid, code), code, code, _e(info["name"]),
                        _e(code.upper())))
        r.append("</nav></div>")
        return "".join(r)

    # ------------------------------------------------------------ contents
    def numbering(self):
        """{page id or planned title: number} - only groups marked numbered,
        counted across groups so IDEX tests continue the sequence."""
        n, out = 0, {}
        for g in self.site["contents"]:
            if not g.get("numbered"):
                continue
            for e in g["entries"]:
                n += 1
                out[e.get("page") or e["planned"]] = n
        return out

    def steps_of(self, p):
        """(id, title, search text, is part heading) of a page's steps,
        feature steps expanded."""
        out = []
        for st in p.get("steps", []):
            if "part" in st:
                out.append((None, st["part"], st["part"], True))
            elif "features" in st:
                for x in self.features[st["features"]]["features"]:
                    words = [x.get(k, "") for k in ("name", "what", "pass", "fail_hot", "fail_cold",
                                                    "fail_low", "fail_high")]
                    out.append((x["id"], x["name"], " ".join(
                        self.plain(w) for w in words + self.texts(x) + self.texts(x.get("more", {}))), False))
            else:
                words = [st["title"]] + self.texts(st) + self.texts(st.get("more", {}))
                out.append((st["id"], st["title"], " ".join(self.plain(w) for w in words), False))
        return out

    def texts(self, st):
        """The searchable words of a step body or of its "More" part."""
        out = [st[k] for k in ("intro", "after") if isinstance(st.get(k), str)]
        out += [pt if isinstance(pt, str) else list(pt.values())[0] for pt in st.get("points", [])
                if self.shown(pt)]
        for box in st.get("callouts", []):
            out += [box.get("title", ""), box.get("text", "")] + list(box.get("items", []))
        tab = st.get("table")
        if tab:
            out += [str(c) for row in tab["rows"] for c in row]
        return out

    def side_contents(self, current):
        nums = self.numbering()
        r = ["<details class=\"indice\" id=\"indice\" open>",
             "<summary>%s</summary>" % _e(self.T("contents")),
             "<a class=\"marchio\" href=\"index.html\">"
             "<picture><source srcset=\"%slogo-dark.svg\" media=\"(prefers-color-scheme: dark)\">"
             "<img class=\"logo\" src=\"%slogo.svg\" alt=\"\" width=\"48\" height=\"64\"></picture>"
             "<span><span class=\"parola\">%s</span><span class=\"sotto\">%s</span></span></a>"
             % (self.root, self.root, wordmark(self.values["suite"]), _e(self.site["tagline"])),
             "<div class=\"filtro\"><input type=\"search\" id=\"filtro\" placeholder=\"%s\" "
             "aria-label=\"%s\" autocomplete=\"off\" spellcheck=\"false\"></div>"
             "<p class=\"filtro-vuoto\" hidden>%s</p>"
             % (_e(self.T("filter")), _e(self.T("filter")), _e(self.T("filter_empty"))),
             "<nav aria-label=\"%s\"><ol>" % _e(self.T("contents"))]
        for g in self.site["contents"]:
            r.append("<li class=\"gruppo\">%s</li>" % _e(g["group"]))
            for e in g["entries"]:
                num = nums.get(e.get("page") or e.get("planned"))
                numhtml = "<span class=\"num\">%s</span>" % (num if num else "")
                if "planned" in e:
                    r.append("<li class=\"manca\" data-cerca=\"%s\"><a>%s<span>%s</span></a></li>"
                             % (_e(e["planned"]), numhtml, _e(e["planned"])))
                    continue
                p = self.pages[e["page"]]
                here = p["id"] == current
                label = p.get("nav_title", p["title"])
                r.append("<li class=\"cap%s\" data-cerca=\"%s\"><a href=\"%s\"%s>%s<span>%s</span></a>"
                         % (" attuale" if here else "", _e(label + " " + self.plain(p.get("intro", ""))[:300]),
                            page_file(p["id"]), " aria-current=\"page\"" if here else "",
                            numhtml, _e(label)))
                steps = self.steps_of(p)
                if steps:
                    r.append("<ol class=\"passi%s\">" % ("" if here else " altrove"))
                    for sid, title, words, part in steps:
                        if part:
                            r.append("<li class=\"parte-voce\" data-cerca=\"%s\">%s</li>"
                                     % (_e(words), _e(title)))
                        else:
                            r.append("<li data-cerca=\"%s\"><a href=\"%s#%s\"><span>%s</span></a></li>"
                                     % (_e(words), "" if here else page_file(p["id"]), sid, _e(title)))
                    r.append("</ol>")
                r.append("</li>")
        r.append("</ol></nav></details>")
        return "\n".join(r)

    # --------------------------------------------------------------- parts
    @staticmethod
    def box(ph, default="4/3"):
        """The photo's fixed box: `aspect:` ("3/2", "1/1", "3/4"; default 4/3,
        16/9 for videos) and `focus:` (object-position, e.g. "50% 30%"). The
        image covers the box: cropped, never letterboxed (style.py)."""
        a, b = str(ph.get("aspect") or default).split("/")
        style = "aspect-ratio: %s / %s" % (a.strip(), b.strip())
        if ph.get("focus"):
            style += "; object-position: %s" % ph["focus"]
        return " style=\"%s\"" % _e(style)

    def photo(self, ph):
        self.photos_used.append(ph)
        if ph.get("kind") == "video":
            return self.video(ph)
        found = None
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            if os.path.exists(os.path.join(self.photos_dir, ph["id"] + ext)):
                found = ph["id"] + ext
                break
        cap = self.md(ph["caption"]) if ph.get("caption") else ""
        if ph.get("credit"):   # community photo: "Name" or {name, url}
            cr = ph["credit"] if isinstance(ph["credit"], dict) else {"name": ph["credit"]}
            who = ("<a href=\"%s\" rel=\"noopener\">%s</a>" % (_e(cr["url"]), _e(cr["name"]))) if cr.get("url") else _e(cr["name"])
            cap += " <span class=\"credito\">%s</span>" % (_e(self.T("photo_by")) % who if "%s" in self.T("photo_by") else who)
        cap = "<figcaption>%s</figcaption>" % cap if cap else ""
        if found:
            src = "%simg/%s" % (self.root, found)
            return ("<figure><a href=\"%s\"><img src=\"%s\" alt=\"%s\" loading=\"lazy\"%s></a>%s</figure>"
                    % (src, src, _e(self.plain(ph["alt"])), self.box(ph), cap))
        brief = ""
        if self.briefs and ph.get("shot"):
            brief = ("<details class=\"brief\"><summary>%s</summary><p>%s</p></details>"
                     % (_e(self.T("photo_brief")), self.md(ph["shot"])))
        return ("<figure class=\"foto-manca\"><div class=\"segnaposto\" role=\"img\" aria-label=\"%s\"%s>"
                "<strong>%s</strong>%s</div>%s%s</figure>"
                % (_e(self.plain(ph["alt"])), self.box(ph), _e(self.T("photo_to_come")),
                   "<code>%s</code>" % _e(ph["id"]) if self.briefs else "", cap, brief))

    def video(self, ph):
        """A short silent clip (e.g. nozzle cam): img/<id>.webm and/or .mp4, optional
        poster img/<id>.jpg. `youtube: <video id>` embeds a longer video instead."""
        cap = "<figcaption>%s</figcaption>" % self.md(ph["caption"]) if ph.get("caption") else ""
        alt = _e(self.plain(ph["alt"]))
        if ph.get("youtube"):
            return ("<figure class=\"video\"><iframe src=\"https://www.youtube-nocookie.com/embed/%s\" title=\"%s\" "
                    "loading=\"lazy\" allow=\"encrypted-media; picture-in-picture\" allowfullscreen%s></iframe>%s</figure>"
                    % (_e(ph["youtube"]), alt, self.box(ph, "16/9"), cap))
        sources = [(ext, mime) for ext, mime in ((".webm", "video/webm"), (".mp4", "video/mp4"))
                   if os.path.exists(os.path.join(self.photos_dir, ph["id"] + ext))]
        if sources:
            poster = ""
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                if os.path.exists(os.path.join(self.photos_dir, ph["id"] + ext)):
                    poster = " poster=\"%simg/%s%s\"" % (self.root, ph["id"], ext)
                    break
            srcs = "".join("<source src=\"%simg/%s%s\" type=\"%s\">" % (self.root, ph["id"], ext, mime)
                           for ext, mime in sources)
            return ("<figure class=\"video\"><video muted loop playsinline controls preload=\"metadata\"%s "
                    "aria-label=\"%s\"%s>%s</video>%s</figure>" % (poster, alt, self.box(ph, "16/9"), srcs, cap))
        brief = ""
        if self.briefs and ph.get("shot"):
            brief = ("<details class=\"brief\"><summary>%s</summary><p>%s</p></details>"
                     % (_e(self.T("photo_brief")), self.md(ph["shot"])))
        return ("<figure class=\"foto-manca\"><div class=\"segnaposto\" role=\"img\" aria-label=\"%s\"%s>"
                "<strong>%s</strong>%s</div>%s%s</figure>"
                % (alt, self.box(ph, "16/9"), _e(self.T("video_to_come")),
                   "<code>%s</code>" % _e(ph["id"]) if self.briefs else "", cap, brief))

    def callout(self, c):
        """A boxed warning or note, at the top of a page or of a step."""
        inner = []
        if c.get("title"):
            inner.append("<p class=\"avviso-titolo\"><strong>%s</strong></p>" % self.md(c["title"]))
        if c.get("text"):
            inner.append("<p>%s</p>" % self.md(c["text"]))
        if c.get("items"):
            inner.append("<ul>%s</ul>" % "".join("<li>%s</li>" % self.md(x) for x in c["items"]))
        return ("<div class=\"avviso %s\" role=\"note\"><div>%s</div></div>"
                % (_e(c.get("kind", "info")), "".join(inner)))

    GENERATOR = re.compile(r"calib\.py|`--[a-z]")

    def shown(self, pt):
        """False for a point that needs the (still private) generator."""
        text = pt if isinstance(pt, str) else next(iter(pt.values()))
        return self.generator or not self.GENERATOR.search(text)

    def printables(self, name):
        """The download box of a guide (`printables: <link name>` on a step):
        a button to the test's Printables page and a link to the whole
        collection; before upload, a disabled "Coming to Printables"."""
        links = self.site.get("links") or {}
        for n in (name, "printables-collection"):
            if n not in links:
                raise SystemExit("printables: unknown address %s (add it to site.yaml links:)" % n)
        url, hub = links[name], links["printables-collection"]
        r = ["<div class=\"scarica\">"]
        if url:
            label = (self.T("printables_collection") % self.values["suite"] if name == "printables-collection"
                     else self.T("download_printables"))
            r.append("<a class=\"bottone\" href=\"%s\" rel=\"noopener\">%s</a>" % (_e(url), _e(label)))
        else:
            r.append("<span class=\"bottone spento\" aria-disabled=\"true\">%s</span>" % _e(self.T("coming_to_printables")))
        if hub and name != "printables-collection":
            r.append("<a href=\"%s\" rel=\"noopener\">%s</a>" % (_e(hub), _e(self.T("printables_collection") % self.values["suite"])))
        r.append("</div>")
        return "".join(r)

    def points(self, pts):
        r = ["<ul class=\"punti\">"]
        for pt in pts:
            if not self.shown(pt):
                continue
            if isinstance(pt, str):
                r.append("<li>%s</li>" % self.md(pt))
                continue
            (kind, text), = pt.items()
            if kind == "warn":
                r.append("<li class=\"attenzione\">%s</li>" % self.md(text))
            else:
                r.append("<li class=\"k-%s\"><span class=\"etichetta\">%s</span>%s</li>"
                         % (kind, _e(self.T("kind_" + kind)), self.md(text)))
        r.append("</ul>")
        return "".join(r)

    def more(self, m):
        """The collapsed part of a step, a feature or a page intro: a native
        <details>, closed; never holds a warning (content.validate)."""
        if not m:
            return ""
        inner = []
        if m.get("intro"):
            inner.append("<div class=\"attacco\">%s</div>" % self.paras(m["intro"]))
        inner += [self.callout(c) for c in m.get("callouts", [])]
        if m.get("table"):
            inner.append(self.table(m["table"]))
        if m.get("points"):
            inner.append(self.points(m["points"]))
        if m.get("after"):
            inner.append("<div class=\"dopo\">%s</div>" % self.paras(m["after"]))
        if m.get("photos"):
            inner.append("<div class=\"foto foto-extra\">%s</div>" % "".join(self.photo(ph) for ph in m["photos"]))
        return ("<details class=\"approfondisci\"><summary>%s</summary><div class=\"approfondisci-corpo\">%s</div></details>"
                % (_e(self.T("more")), "".join(inner)))

    def cell(self, text):
        """A table cell: one line per "\\n". A .3mf file name in `code` keeps
        its words together and may wrap only once, before its numbers."""
        html = "<br>".join(self.md(line) for line in text.split("\n"))

        def file_name(m):
            name = m.group(1)
            if not name.endswith(".3mf"):
                return m.group(0)
            parts = re.split(r"(?<=_)(?=\d)", name, maxsplit=1)
            return "<code class=\"file\">%s</code>" % "<wbr>".join("<span>%s</span>" % x for x in parts)
        return re.sub(r"<code>(.*?)</code>", file_name, html)

    def table(self, tab):
        r = ["<div class=\"tabella\"><table><thead><tr>"]
        r += ["<th scope=\"col\">%s</th>" % self.md(h) for h in tab["head"]]
        r.append("</tr></thead><tbody>")
        for row in tab["rows"]:
            r.append("<tr>%s</tr>" % "".join("<td>%s</td>" % self.cell(str(c)) for c in row))
        r.append("</tbody></table></div>")
        return "".join(r)

    def step(self, sid, title, number, body_html, photos):
        r = ["<section class=\"passo\" id=\"%s\">" % sid,
             "<h2>%s<a class=\"ancora\" href=\"#%s\">%s</a></h2>"
             % ("<span class=\"numero\">%s</span> " % _e(self.T("step_n") % number) if number else "",
                sid, _e(title)),
             "<div class=\"corpo%s\">" % ("" if photos else " solo-testo")]
        if photos:
            r.append("<div class=\"foto\">%s</div>" % "".join(self.photo(ph) for ph in photos))
        r.append("<div>%s</div></div></section>" % body_html)
        return "\n".join(r)

    def feature_steps(self, fid, start):
        fs = self.features[fid]
        out, n = [], start
        for x in fs["features"]:
            n += 1 if start else 0
            body = []
            if x.get("weight"):
                # pressure advance: "primary" probes decide, "check" probes confirm
                body.append("<p class=\"peso peso-%s\">%s</p>"
                            % (_e(x["weight"]), _e(self.T("weight_" + x["weight"]))))
            if x.get("what"):
                body.append("<p class=\"attacco\">%s</p>" % self.md(x["what"]))
            body.append("<div class=\"esiti\">")
            for key, cls, label in (("pass", "ok", "state_pass"), ("fail", "caldo", "state_fail"),
                                    ("fail_hot", "caldo", "state_hot"),
                                    ("fail_cold", "freddo", "state_cold"), ("fail_low", "caldo", "state_low"),
                                    ("fail_high", "freddo", "state_high")):
                if x.get(key):
                    body.append("<div class=\"%s\"><b class=\"lab\">%s</b>%s</div>"
                                % (cls, _e(self.T(label)), self.md(x[key])))
            body.append("</div>")
            if x.get("points"):
                body.append(self.points(x["points"]))
            body.append(self.more(x.get("more")))
            out.append(self.step(x["id"], x["name"], n if start else None, "".join(body),
                                 x.get("photos", [])))
        return out, n

    def sketch(self, rel):
        """A page's pencil sketch (`sketch:`, under img/), inlined so its
        stroke="currentColor" follows the theme. Decorative: hidden from
        screen readers, its <title> dropped (no hover tooltip)."""
        with open(os.path.join(self.photos_dir, rel), encoding="utf-8") as f:
            svg = f.read().strip()
        svg = re.sub(r"<\?xml[^>]*>\s*", "", svg)
        svg = re.sub(r"<title>.*?</title>", "", svg, flags=re.S)
        svg = svg.replace("<svg ", "<svg focusable=\"false\" ", 1)
        return "<div class=\"schizzo\" aria-hidden=\"true\">%s</div>" % svg

    # ---------------------------------------------------------------- pages
    def page(self, pid):
        p = self.pages[pid]
        nums = self.numbering()
        title = p["title"]
        full_title = (self.T("page_title") % (self.plain(title), self.values["suite"])
                      if pid != "home" else "%s — %s" % (self.values["suite"], self.plain(title)))
        head = self.head(pid, full_title, self.plain(p.get("description", p.get("intro", "")))[:160])
        if p.get("kind") == "scorecard":
            # the card has one column per feature: it needs the long side of the sheet
            head = head.replace("</head>", "<style>@page { size: A4 portrait; margin: 12mm; }</style>\n</head>")
        has_more = p.get("kind") != "scorecard" and (
            "more" in p or any("more" in st for st in p.get("steps", []))
            or any("more" in x for st in p.get("steps", []) if "features" in st
                   for x in self.features[st["features"]]["features"]))
        r = [head,
             self.side_contents(pid),
             "<main id=\"contenuto\">",
             self.language_switch(pid, expand=has_more)]
        crumb = (self.T("test_n") % nums[pid]) if pid in nums else p.get("breadcrumb", "")
        if crumb:
            r.append("<p class=\"briciole\">%s</p>" % _e(crumb))
        r.append("<h1>%s</h1>" % self.md(title))
        sketch = self.sketch(p["sketch"]) if p.get("sketch") else ""
        if sketch:
            r.append("<div class=\"apertura\">" + sketch)
        if p.get("intro"):
            r.append("<div class=\"occhiello\">%s</div>" % self.paras(p["intro"]))
        if p.get("more"):
            r.append("<div class=\"occhiello-piu\">%s</div>" % self.more(p["more"]))
        if sketch:
            r.append("</div>")
        for c in p.get("callouts", []):
            r.append(self.callout(c))
        if p.get("need"):
            need = p["need"]
            r.append("<section class=\"serve\"><h2>%s</h2><div class=\"due\">" % _e(need["title"]))
            for col in need["columns"]:
                r.append("<div><h3>%s</h3><ul>%s</ul></div>"
                         % (_e(col["title"]), "".join("<li>%s</li>" % self.md(i) for i in col["items"])))
            r.append("</div></section>")
        if p.get("show_tests"):
            r.append(self.tests_list())
        if p.get("kind") == "scorecard":
            r.append(self.scorecard(p))
        n = 0
        numbered = p.get("numbered", False)
        for st in p.get("steps", []):
            if "part" in st:
                r.append("<h2 class=\"parte\">%s</h2>" % _e(st["part"]))
                continue
            if "features" in st:
                html_steps, n = self.feature_steps(st["features"], n if numbered else 0)
                r += html_steps
                continue
            if numbered:
                n += 1
            body = [self.callout(c) for c in st.get("callouts", [])]
            if st.get("intro"):
                body.append("<div class=\"attacco\">%s</div>" % self.paras(st["intro"]))
            if st.get("table"):
                body.append(self.table(st["table"]))
            if st.get("points"):
                body.append(self.points(st["points"]))
            if st.get("printables"):
                body.append(self.printables(st["printables"]))
            if st.get("translators"):
                names = ["<li><b>%s</b>: %s</li>" % (_e(info["name"]), _e(", ".join(info["translators"])))
                         for code, info in self.langs.items() if info.get("translators")]
                if names:
                    body.append("<ul class=\"punti\">%s</ul>" % "".join(names))
            if st.get("after"):
                body.append("<div class=\"dopo\">%s</div>" % self.paras(st["after"]))
            body.append(self.more(st.get("more")))
            r.append(self.step(st["id"], st["title"], n if numbered else None, "".join(body),
                               st.get("photos", [])))
        i = self.order.index(pid)
        before = self.order[i - 1] if i else None
        after = self.order[i + 1] if i + 1 < len(self.order) else None
        if before or after:
            r.append("<nav class=\"avanti\" aria-label=\"%s\">" % _e(self.T("pages_nav")))
            r.append(self.shortcut(before, "previous", "") if before else "<span></span>")
            r.append(self.shortcut(after, "next", " dopo-link") if after else "<span></span>")
            r.append("</nav>")
        score = ""
        if p.get("kind") == "scorecard":
            mode = self.features[p["features"]].get("scoring")
            score = {"bands": SCORE_BANDS, "idex": IDEX_FIT + SCORE_IDEX, "flow": SCORE_FLOW}.get(mode, SCORE)
        r.append("</main></div>\n<script>%s%s%s%s</script>\n</body>\n</html>\n"
                 % (FOLLOW, FILTER, MORE if has_more else "", score))
        return "\n".join(r)

    def shortcut(self, pid, label, cls):
        p = self.pages[pid]
        return ("<a class=\"%s\" href=\"%s\"><span>%s</span>%s</a>"
                % (cls.strip(), page_file(pid), _e(self.T(label)), _e(p.get("nav_title", p["title"]))))

    def tests_list(self):
        nums = self.numbering()
        r = ["<ul class=\"capitoli\">"]
        for g in self.site["contents"]:
            if not g.get("numbered"):
                continue
            r.append("<li class=\"gruppo\">%s</li>" % _e(g["group"]))
            for e in g["entries"]:
                note = e.get("note")
                if "planned" in e:
                    r.append("<li><span class=\"vuoto\"><span class=\"num\">%d</span>"
                             "<span><b>%s</b> <em>— %s</em></span></span></li>"
                             % (nums[e["planned"]], _e(e["planned"]),
                                self.md(note) + " · " + _e(self.T("not_written_yet")) if note
                                else _e(self.T("not_written_yet"))))
                else:
                    p = self.pages[e["page"]]
                    r.append("<li><a href=\"%s\"><span class=\"num\">%d</span>"
                             "<span><b>%s</b>%s</span></a></li>"
                             % (page_file(p["id"]), nums[p["id"]], _e(p.get("nav_title", p["title"])),
                                (" <em>— %s</em>" % self.md(note)) if note else ""))
        r.append("</ul>")
        return "\n".join(r)

    def scorecard(self, p):
        fs = self.features[p["features"]]
        if fs.get("scoring") == "bands":
            return self.scorecard_bands(fs)
        if fs.get("scoring") == "idex":
            return self.scorecard_idex(fs)
        if fs.get("scoring") == "flow":
            return self.scorecard_flow(fs)
        feats = fs["features"]
        nblocks = fs.get("blocks_max", 9)
        presets = {m["name"]: m["temps"] for m in fs.get("presets", [])}
        words = {"P": self.T("state_pass"), "H": self.T("state_hot"), "C": self.T("state_cold"),
                 "-": self.T("state_na"), "empty": self.T("state_empty"),
                 "best": self.T("score_best"), "tie": self.T("score_tie"),
                 "block": self.T("block")}
        r = ["<section class=\"scorecard\">"]
        if fs.get("rules"):
            r.append("<h2>%s</h2><ol class=\"regole\">%s</ol>"
                     % (_e(fs.get("rule_title", "")), "".join("<li>%s</li>" % self.md(x) for x in fs["rules"])))
        r.append("<div class=\"scheda-strumenti\">")
        if presets:
            r.append("<label>%s <select id=\"preset\"><option value=\"\">%s</option>%s</select></label>"
                     % (_e(self.T("score_material")), _e(self.T("score_material_none")),
                        "".join("<option value=\"%s\">%s</option>" % (_e(k), _e(k)) for k in presets)))
        r.append("<button type=\"button\" id=\"azzera\">%s</button>" % _e(self.T("score_clear")))
        r.append("<button type=\"button\" id=\"stampa\">%s</button>" % _e(self.T("score_print")))
        r.append("</div>")
        # weight "confirms": shown and marked, never counted (passes, tie-break, gate)
        nc = [x for x in feats if x.get("weight") == "confirms"]
        r.append("<p class=\"legenda\"><span><b class=\"P\">✓</b>%s</span><span><b class=\"H\">H</b>%s</span>"
                 "<span><b class=\"C\">C</b>%s</span><span><b>–</b>%s</span>%s</p>"
                 % (_e(self.T("state_pass")), _e(self.T("state_hot")), _e(self.T("state_cold")),
                    _e(self.T("state_na")),
                    "".join("<span class=\"nc\"><i>%s</i>: %s</span>"
                            % (_e(x.get("short", x["name"])), _e(self.T("score_not_counted"))) for x in nc)))
        r.append("<div class=\"scheda-wrap\"><table class=\"scheda\" id=\"scheda\" data-words=\"%s\" "
                 "data-gate=\"%s\" data-presets=\"%s\">"
                 % (_e(json.dumps(words, ensure_ascii=False)), _e(fs.get("gate", "")),
                    _e(json.dumps(presets))))
        r.append("<thead><tr><th scope=\"col\">%s</th><th scope=\"col\">°C</th>" % _e(self.T("block")))
        for x in feats:
            if x in nc:
                r.append("<th scope=\"col\" class=\"nc\" title=\"%s – %s\">%s</th>"
                         % (_e(self.plain(x["name"])), _e(self.T("score_not_counted")), _e(x.get("short", x["name"]))))
            else:
                r.append("<th scope=\"col\" title=\"%s\">%s</th>" % (_e(self.plain(x["name"])), _e(x.get("short", x["name"]))))
        r.append("<th scope=\"col\">%s</th><th scope=\"col\">%s</th></tr></thead><tbody>"
                 % (_e(self.T("score_passes")), _e(self.T("score_notes"))))
        for b in range(1, nblocks + 1):
            r.append("<tr><th scope=\"row\">%d</th><td class=\"temp\"><input type=\"text\" "
                     "inputmode=\"numeric\" aria-label=\"%s %d °C\" placeholder=\"____\"></td>"
                     % (b, _e(self.T("block")), b))
            for x in feats:
                name = self.plain(x.get("short", x["name"]))
                if x in nc:
                    name += " (%s)" % self.T("score_not_counted")
                r.append("<td%s><button type=\"button\" class=\"cella\" data-v=\"\" data-f=\"%s\"%s "
                         "data-name=\"%s %d, %s\" aria-label=\"%s %d, %s: %s\"></button></td>"
                         % (" class=\"nc\"" if x in nc else "", x["id"], " data-count=\"0\"" if x in nc else "",
                            _e(self.T("block")), b, _e(name),
                            _e(self.T("block")), b, _e(name), _e(self.T("state_empty"))))
            r.append("<td class=\"voto\"></td><td class=\"note\"></td></tr>")
        r.append("</tbody></table></div>")
        r.append("<p class=\"esito-scheda\" id=\"esito\" aria-live=\"polite\"></p>")
        r.append("<p class=\"nota\">%s</p>" % self.md(self.T("score_footer")))
        r.append("</section>")
        return "\n".join(r)

    def scorecard_bands(self, fs):
        """The pressure-advance card: one row per band with its PA value
        (filled from the firmware menu, or typed), states pass / L too low /
        H too high / not scored, and the band picked by the rule (SCORE_BANDS)."""
        feats = fs["features"]
        nbands = fs.get("blocks_max", 9)
        presets = {m["name"]: {"v": m["temps"], "fw": m.get("firmware", ""), "p": m.get("preset", ""),
                               "var": m.get("variant", "")} for m in fs.get("presets", [])}
        words = {"P": self.T("state_pass"), "L": self.T("state_low"), "H": self.T("state_high"),
                 "-": self.T("state_na"), "empty": self.T("state_empty"),
                 "best": self.T("score_band_best"), "tie": self.T("score_band_tie"),
                 "edge": self.T("score_band_edge"), "none": self.T("score_band_none"),
                 "fine": self.T("score_band_fine") if self.generator else ""}
        r = ["<section class=\"scorecard\">"]
        if fs.get("rules"):
            r.append("<h2>%s</h2><ol class=\"regole\">%s</ol>"
                     % (_e(fs.get("rule_title", "")), "".join("<li>%s</li>" % self.md(x) for x in fs["rules"])))
        r.append("<div class=\"scheda-strumenti\">")
        if presets:
            r.append("<label>%s <select id=\"preset\"><option value=\"\">%s</option>%s</select></label>"
                     % (_e(self.T("score_firmware")), _e(self.T("score_firmware_none")),
                        "".join("<option value=\"%s\">%s</option>" % (_e(k), _e(k)) for k in presets)))
        r.append("<button type=\"button\" id=\"azzera\">%s</button>" % _e(self.T("score_clear")))
        r.append("<button type=\"button\" id=\"stampa\">%s</button>" % _e(self.T("score_print")))
        r.append("</div>")
        # weight "confirms" (the inside corners): shown and marked, never counted
        nc = [x for x in feats if x.get("weight") == "confirms"]
        r.append("<p class=\"legenda legenda-pa\"><span><b class=\"P\">✓</b>%s</span><span><b class=\"L\">L</b>%s</span>"
                 "<span><b class=\"H\">H</b>%s</span><span><b>–</b>%s</span>%s</p>"
                 % (_e(self.T("state_pass")), _e(self.T("state_low")), _e(self.T("state_high")),
                    _e(self.T("state_na")),
                    "".join("<span class=\"nc\"><i>%s</i>: %s</span>"
                            % (_e(x.get("short", x["name"])), _e(self.T("score_not_counted"))) for x in nc)))
        r.append("<div class=\"scheda-wrap\"><table class=\"scheda scheda-pa\" id=\"scheda\" data-words=\"%s\" "
                 "data-presets=\"%s\">"
                 % (_e(json.dumps(words, ensure_ascii=False)), _e(json.dumps(presets))))
        r.append("<thead><tr><th scope=\"col\">%s</th><th scope=\"col\">PA</th>" % _e(self.T("band")))
        for x in feats:
            if x in nc:
                r.append("<th scope=\"col\" class=\"nc\" title=\"%s – %s\">%s</th>"
                         % (_e(self.plain(x["name"])), _e(self.T("score_not_counted")), _e(x.get("short", x["name"]))))
            else:
                r.append("<th scope=\"col\" title=\"%s\" class=\"%s\">%s</th>"
                         % (_e(self.plain(x["name"])), "secondaria" if x.get("weight") == "check" else "",
                            _e(x.get("short", x["name"]))))
        r.append("<th scope=\"col\">%s</th><th scope=\"col\">%s</th></tr></thead><tbody>"
                 % (_e(self.T("score_passes")), _e(self.T("score_notes"))))
        # band 1 is the bottom of the tower: the card lists it at the top, like the scoring order
        for b in range(1, nbands + 1):
            r.append("<tr><th scope=\"row\">%d</th><td class=\"temp\"><input type=\"text\" "
                     "inputmode=\"decimal\" aria-label=\"%s %d PA\" placeholder=\"%s\"></td>"
                     % (b, _e(self.T("band")), b, "0" if b == 1 else "_____"))
            for x in feats:
                name = self.plain(x.get("short", x["name"]))
                if x in nc:
                    name += " (%s)" % self.T("score_not_counted")
                r.append("<td%s><button type=\"button\" class=\"cella\" data-v=\"\" data-f=\"%s\"%s "
                         "data-name=\"%s %d, %s\" aria-label=\"%s %d, %s: %s\"></button></td>"
                         % (" class=\"nc\"" if x in nc else "", x["id"], " data-count=\"0\"" if x in nc else "",
                            _e(self.T("band")), b, _e(name),
                            _e(self.T("band")), b, _e(name), _e(self.T("state_empty"))))
            r.append("<td class=\"voto\"></td><td class=\"note\"></td></tr>")
        r.append("</tbody></table></div>")
        r.append("<p class=\"esito-scheda\" id=\"esito\" aria-live=\"polite\"></p>")
        r.append("<p class=\"esito-fine\" id=\"fine\"></p>")
        r.append("<p class=\"nota\">%s</p>" % self.md(self.T("score_band_footer")))
        r.append("</section>")
        return "\n".join(r)



    def scorecard_flow(self, fs):
        """The maximum-flow card: one row per band with its flow (filled from
        the file menu, or typed), the wall state pass / degrading / fail / not
        scored, the heater-sag and clicks flags, and the suggested max
        volumetric speed (SCORE_FLOW)."""
        nbands = fs.get("blocks_max", 16)
        presets = {m["name"]: m["flows"] for m in fs.get("presets", [])}
        words = {"P": self.T("state_pass"), "D": self.T("state_degrading"), "F": self.T("state_fail"),
                 "-": self.T("state_na"), "Y": self.T("state_yes"), "empty": self.T("state_empty"),
                 "best": self.T("score_flow_best"), "range": self.T("score_flow_range"),
                 "first": self.T("score_flow_first"), "none": self.T("score_flow_none"),
                 "unscored": self.T("score_flow_unscored"), "noflow": self.T("score_flow_noflow"),
                 "noisy": self.T("score_flow_noisy")}
        cols = (("wall", self.T("score_flow_wall"), False), ("heater", self.T("score_flow_heater"), True),
                ("clicks", self.T("score_flow_clicks"), True))
        r = ["<section class=\"scorecard\">"]
        if fs.get("rules"):
            r.append("<h2>%s</h2><ol class=\"regole\">%s</ol>"
                     % (_e(fs.get("rule_title", "")), "".join("<li>%s</li>" % self.md(x) for x in fs["rules"])))
        r.append("<div class=\"scheda-strumenti\">")
        if presets:
            r.append("<label>%s <select id=\"preset\"><option value=\"\">%s</option>%s</select></label>"
                     % (_e(self.T("score_file")), _e(self.T("score_file_none")),
                        "".join("<option value=\"%s\">%s</option>" % (_e(k), _e(k)) for k in presets)))
        r.append("<button type=\"button\" id=\"azzera\">%s</button>" % _e(self.T("score_clear")))
        r.append("<button type=\"button\" id=\"stampa\">%s</button>" % _e(self.T("score_print")))
        r.append("</div>")
        r.append("<p class=\"legenda legenda-flow\"><span><b class=\"P\">✓</b>%s</span><span><b class=\"D\">◐</b>%s</span>"
                 "<span><b class=\"F\">✕</b>%s</span><span><b>–</b>%s</span><span><b class=\"Y\">●</b>%s</span></p>"
                 % (_e(self.T("state_pass")), _e(self.T("state_degrading")), _e(self.T("state_fail")),
                    _e(self.T("state_na")), _e(self.T("score_flow_flag"))))
        r.append("<div class=\"scheda-wrap\"><table class=\"scheda scheda-flow\" id=\"scheda\" data-words=\"%s\" "
                 "data-presets=\"%s\">" % (_e(json.dumps(words, ensure_ascii=False)), _e(json.dumps(presets))))
        r.append("<thead><tr><th scope=\"col\">%s</th><th scope=\"col\">mm³/s</th>" % _e(self.T("band")))
        for _, name, flag in cols:
            r.append("<th scope=\"col\"%s>%s</th>" % (" class=\"secondaria\"" if flag else "", _e(name)))
        r.append("<th scope=\"col\">%s</th></tr></thead><tbody>" % _e(self.T("score_notes")))
        for b in range(1, nbands + 1):
            r.append("<tr><th scope=\"row\">%d</th><td class=\"temp\"><input type=\"text\" "
                     "inputmode=\"decimal\" aria-label=\"%s %d mm³/s\" placeholder=\"____\"></td>"
                     % (b, _e(self.T("band")), b))
            for fid, name, flag in cols:
                r.append("<td><button type=\"button\" class=\"cella\" data-v=\"\" data-f=\"%s\"%s "
                         "data-name=\"%s %d, %s\" aria-label=\"%s %d, %s: %s\"></button></td>"
                         % (fid, " data-toggle=\"1\"" if flag else "", _e(self.T("band")), b, _e(name),
                            _e(self.T("band")), b, _e(name), _e(self.T("state_empty"))))
            r.append("<td class=\"note\"></td></tr>")
        r.append("</tbody></table></div>")
        r.append("<p class=\"esito-scheda\" id=\"esito\" aria-live=\"polite\"></p>")
        r.append("<p class=\"esito-fine esito-flow\" id=\"fine\"></p>")
        r.append("<p class=\"nota\">%s</p>" % self.md(self.T("score_flow_footer")))
        r.append("</section>")
        return "\n".join(r)

    def scorecard_idex(self, fs):
        """The IDEX alignment card: one row per station (keypad numbering), X and
        Y fine and coarse readings, the fit of calib.py idex-analyze (IDEX_FIT),
        verdicts, diagnosis and firmware lines (SCORE_IDEX)."""
        words = {k[len("idex_"):]: self.T(k) for k in self.ui if k.startswith("idex_")}
        beds = [{"id": str(b["id"]), "name": b["name"], "vernier": b["vernier"], "lite": b["lite"]}
                for b in fs["beds"]]
        terms = {x["id"]: {"name": self.plain(x["name"]), "cause": self.md(x["cause"]),
                           "action": self.md(x["action"]), "vc4": self.md(x["vc4"]) if x.get("vc4") else ""}
                 for x in fs["features"]}
        r = ["<section class=\"scorecard scorecard-idex\">"]
        if fs.get("rules"):
            r.append("<h2>%s</h2><ol class=\"regole\">%s</ol>"
                     % (_e(fs.get("rule_title", "")), "".join("<li>%s</li>" % self.md(x) for x in fs["rules"])))
        r.append("<div class=\"scheda-strumenti\">")
        r.append("<label>%s <select id=\"idex-bed\"><option value=\"\">%s</option>%s</select></label>"
                 % (_e(words["bed"]), _e(words["bed_none"]),
                    "".join("<option value=\"%s\">%s</option>" % (_e(b["id"]), _e(b["name"])) for b in beds)))
        r.append("<label>%s <select id=\"idex-variant\"><option value=\"vernier\">%s</option>"
                 "<option value=\"lite\">%s</option></select></label>"
                 % (_e(words["variant"]), _e(words["vernier"]), _e(words["lite"])))
        r.append("<label>%s <input id=\"idex-cx\" class=\"idex-cur\" inputmode=\"decimal\" placeholder=\"X\" "
                 "aria-label=\"idex_xoffset\"> <input id=\"idex-cy\" class=\"idex-cur\" inputmode=\"decimal\" "
                 "placeholder=\"Y\" aria-label=\"idex_yoffset\"></label>" % _e(words["current"]))
        for bid, key in (("azzera", None), ("stampa", None), ("idex-ricorda", "remember"),
                         ("idex-dimentica", "forget"), ("idex-copia", "copy")):
            label = self.T("score_clear") if bid == "azzera" else self.T("score_print") if bid == "stampa" else words[key]
            r.append("<button type=\"button\" id=\"%s\">%s</button>" % (bid, _e(label)))
        r.append("</div>")
        r.append("<p class=\"legenda\">%s</p>" % _e(words["legend"]))
        r.append("<p class=\"solo-stampa\">%s</p>" % _e(words["paper"]))
        r.append("<div class=\"scheda-wrap\"><table class=\"scheda scheda-idex\" id=\"idex\" data-words=\"%s\" "
                 "data-beds=\"%s\" data-terms=\"%s\">"
                 % (_e(json.dumps(words, ensure_ascii=False)), _e(json.dumps(beds, separators=(",", ":"))),
                    _e(json.dumps(terms, ensure_ascii=False))))
        cols = (("x", "x_fine"), ("xc", "x_coarse"), ("y", "y_fine"), ("yc", "y_coarse"))
        r.append("<thead><tr><th scope=\"col\">%s</th>%s<th scope=\"col\">%s</th><th scope=\"col\">%s</th>"
                 "<th scope=\"col\">%s</th></tr></thead><tbody>"
                 % (_e(words["station"]), "".join("<th scope=\"col\">%s</th>" % _e(words[w]) for _, w in cols),
                    _e(words["fit"]), _e(words["resid"]), _e(self.T("score_notes"))))
        for n in range(1, 10):
            name = words["s%d" % n]
            r.append("<tr data-st=\"%d\"><th scope=\"row\"><span class=\"idex-n\">%d</span> %s</th>" % (n, n, _e(name)))
            for k, w in cols:
                r.append("<td class=\"temp\"><input type=\"text\" inputmode=\"decimal\" data-k=\"%s\" class=\"%s\" "
                         "aria-label=\"%s %d, %s\" placeholder=\"____\"></td>"
                         % (k, "c" if k.endswith("c") else "f", _e(words["station"]), n, _e(words[w])))
            r.append("<td class=\"fit\"></td><td class=\"res\"></td><td class=\"note\"></td></tr>")
        r.append("</tbody></table></div>")
        r.append("<div class=\"idex-esito\" id=\"esito\" aria-live=\"polite\"></div>")
        r.append("<p class=\"nota\">%s</p>" % self.md(words["footer"]))
        r.append("</section>")
        return "\n".join(r)

def wordmark(name):
    """'HexCalibr' -> <b>Hex</b>Calibr, as in the logo."""
    if name.startswith("Hex"):
        return "<b>Hex</b>%s" % _e(name[3:])
    return _e(name)


FAVICON_FALLBACK = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect x="9" y="3" width="14" height="26" rx="3" fill="#16191d"/>
<rect x="11" y="6" width="10" height="4" rx="1" fill="#f7f6f3"/>
<rect x="11" y="12" width="10" height="4" rx="1" fill="#efa00b"/>
<rect x="11" y="18" width="10" height="4" rx="1" fill="#f7f6f3"/>
</svg>
"""
