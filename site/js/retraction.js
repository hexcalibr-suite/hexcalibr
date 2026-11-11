// SPDX-FileCopyrightText: 2026 Matteo Beretta
// SPDX-License-Identifier: GPL-3.0-or-later
//
// HexCalibr retraction test: the G-code rewriter. Runs in the browser (window.HexRetract) and in
// Node (module.exports); nothing is uploaded anywhere.
//
// The test object is a ring of N hexagonal pillars; gap k lies between pillar k and pillar k+1
// (counter-clockwise from the front, the last gap closes the ring). The 3MF changes nothing about
// retraction: it only puts one comment in the G-code, above the base,
//   ;HEXCALIBR retraction v1 lengths=0.0,0.2,...,2.0 radius=35.495 front=-90 pitch=20
// This file finds the pillars in the G-code and sets every retraction made on a travel between two
// neighbouring pillars to its gap's length; every other retraction stays as the slicer wrote it.
//
// A retraction "event" is everything from the first move that pulls filament back (an E-only move
// or a wipe move with negative E) to the matching E-only push back (the unretract). All the pulls
// of the event are scaled by the same factor so that they add up to the gap's length, and the push
// back becomes that length plus whatever extra the slicer added (retract_restart_extra). Absolute
// and relative E both work. Files it cannot handle are refused with a reason, never half-rewritten.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); }
  else { root.HexRetract = factory(); }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var MARKER = ';HEXCALIBR retraction v1 ';

  // Thrown for files the page refuses; `code` picks the message the page shows (in the user's
  // language), `info` fills it in.
  function RetractError(code, info) {
    var e = new Error(code + (info ? ' ' + JSON.stringify(info) : ''));
    e.name = 'RetractError';
    e.code = code;
    e.info = info || {};
    return e;
  }

  function parseMarker(line) {
    var out = {};
    line.slice(MARKER.length).trim().split(/\s+/).forEach(function (kv) {
      var i = kv.indexOf('=');
      if (i > 0) { out[kv.slice(0, i)] = kv.slice(i + 1); }
    });
    var lengths = (out.lengths || '').split(',').map(Number);
    var ring = { lengths: lengths, radius: Number(out.radius), front: Number(out.front), pitch: Number(out.pitch) };
    if (lengths.length < 3 || lengths.some(function (v) { return !isFinite(v) || v < 0; }) ||
        !(ring.radius > 0) || !isFinite(ring.front)) {
      throw RetractError('bad_marker');
    }
    return ring;
  }

  // One G-code line, split into its command and words. Only what the rewriter needs.
  var WORD = /([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+))/g;
  function parse(line) {
    var semi = line.indexOf(';');
    var code = (semi >= 0 ? line.slice(0, semi) : line).trim();
    if (!code) { return null; }
    var m = /^([GMT])(\d+)/i.exec(code);
    if (!m) { return { cmd: code.split(/\s/)[0].toUpperCase(), w: {} }; }
    var cmd = m[1].toUpperCase() + String(Number(m[2]));
    var w = {};
    var rest = code.slice(m[0].length);
    var mm;
    WORD.lastIndex = 0;
    while ((mm = WORD.exec(rest)) !== null) { w[mm[1].toUpperCase()] = Number(mm[2]); }
    return { cmd: cmd, w: w };
  }

  // PrusaSlicer style numbers: 5 decimals at most, no trailing zeros, no leading zero (-.8, .35).
  function num(v) {
    var s = (Math.round(v * 1e5) / 1e5).toFixed(5).replace(/0+$/, '').replace(/\.$/, '');
    if (s === '-0') { s = '0'; }
    return s.replace(/^(-?)0\./, '$1.');
  }

  // Replace the E word of a G1 line, keeping everything else (and any comment) as it was.
  function setE(line, value) {
    var semi = line.indexOf(';');
    var code = semi >= 0 ? line.slice(0, semi) : line;
    var comment = semi >= 0 ? line.slice(semi) : '';
    var done = false;
    code = code.replace(/E\s*[-+]?(?:\d+\.?\d*|\.\d+)/i, function () { done = true; return 'E' + num(value); });
    if (!done) { throw RetractError('internal'); }
    return code + comment;
  }

  function angleDiff(a, b) {           // degrees, -180..180
    var d = (a - b) % 360;
    if (d > 180) { d -= 360; }
    if (d < -180) { d += 360; }
    return d;
  }

  // Find the pillar centres: points of the extrusions above the marker, grouped around the ring
  // the marker describes. Only translation is allowed (PrusaSlicer moves the object when it
  // arranges it); a turned, mirrored or scaled ring does not match and is refused.
  function locate(points, ring) {
    var n = ring.lengths.length;
    var step = 360 / n;
    var exp = [];
    for (var k = 0; k < n; k++) {
      var a = (ring.front + k * step) * Math.PI / 180;
      exp.push([ring.radius * Math.cos(a), ring.radius * Math.sin(a)]);
    }
    if (points.length < n * 6) { throw RetractError('no_ring', { found: 0, expected: n }); }
    var cx = 0, cy = 0, i;
    for (i = 0; i < points.length; i++) { cx += points[i][0]; cy += points[i][1]; }
    cx /= points.length; cy /= points.length;
    var assign = new Array(points.length);
    for (var iter = 0; iter < 4; iter++) {
      var sx = new Array(n).fill(0), sy = new Array(n).fill(0), cnt = new Array(n).fill(0);
      for (i = 0; i < points.length; i++) {
        var best = -1, bd = Infinity;
        for (k = 0; k < n; k++) {
          var dx = points[i][0] - cx - exp[k][0], dy = points[i][1] - cy - exp[k][1];
          var d = dx * dx + dy * dy;
          if (d < bd) { bd = d; best = k; }
        }
        assign[i] = best; sx[best] += points[i][0]; sy[best] += points[i][1]; cnt[best]++;
      }
      var empty = cnt.filter(function (c) { return c === 0; }).length;
      if (empty) { throw RetractError('no_ring', { found: n - empty, expected: n }); }
      var ncx = 0, ncy = 0;
      for (k = 0; k < n; k++) { ncx += sx[k] / cnt[k] - exp[k][0]; ncy += sy[k] / cnt[k] - exp[k][1]; }
      cx = ncx / n; cy = ncy / n;
    }
    var centres = exp.map(function (e) { return [cx + e[0], cy + e[1]]; });
    // every point must sit on its pillar: a pillar is pitch/4 across at most (5 mm at pitch 20)
    var reach = ring.pitch * 0.25;
    var worst = 0;
    for (i = 0; i < points.length; i++) {
      var c = centres[assign[i]];
      worst = Math.max(worst, Math.hypot(points[i][0] - c[0], points[i][1] - c[1]));
    }
    if (worst > reach) { throw RetractError('ring_mismatch', { off: Math.round(worst * 10) / 10 }); }
    return { centres: centres, reach: reach + 1.0, cx: cx, cy: cy };
  }

  function pillarAt(loc, x, y) {
    for (var k = 0; k < loc.centres.length; k++) {
      if (Math.hypot(x - loc.centres[k][0], y - loc.centres[k][1]) <= loc.reach) { return k; }
    }
    return -1;
  }

  // gap index between pillars a and b, or -1 if they are not neighbours
  function gapOf(a, b, n) {
    if (a < 0 || b < 0 || a === b) { return -1; }
    if ((a + 1) % n === b) { return a; }
    if ((b + 1) % n === a) { return b; }
    return -1;
  }

  function rewrite(text) {
    var nl = text.indexOf('\r\n') >= 0 ? '\r\n' : '\n';
    var lines = text.split(/\r?\n/);
    var start = -1, i;
    for (i = 0; i < lines.length; i++) {
      if (lines[i].lastIndexOf(MARKER, 0) === 0) { start = i; break; }
    }
    if (start < 0) {
      if (text.indexOf(';HEXCALIBR retraction') >= 0) { throw RetractError('bad_marker'); }
      throw RetractError('no_marker');
    }
    if (text.indexOf(MARKER + 'rewritten') >= 0 || text.indexOf(';HEXCALIBR rewritten') >= 0) {
      throw RetractError('already');
    }
    var ring = parseMarker(lines[start]);
    var n = ring.lengths.length;
    if (/^;\s*use_firmware_retraction\s*=\s*1/m.test(text)) { throw RetractError('firmware_retraction'); }

    // the test region: from the marker to the end G-code (PrusaSlicer tags it ;TYPE:Custom)
    var end = lines.length;
    for (i = start + 1; i < lines.length; i++) {
      if (/^;TYPE:Custom\s*$/.test(lines[i])) { end = i; break; }
    }

    // state before the marker: E mode and position
    var absE = false, x = NaN, y = NaN, e = 0;
    function step(p) {                 // update the machine state, return the E delta of a move
      var de = 0;
      if (p.cmd === 'M82') { absE = true; }
      else if (p.cmd === 'M83') { absE = false; }
      else if (p.cmd === 'G92') { if ('E' in p.w) { e = p.w.E; } }
      else if (p.cmd === 'G0' || p.cmd === 'G1') {
        if ('X' in p.w) { x = p.w.X; }
        if ('Y' in p.w) { y = p.w.Y; }
        if ('E' in p.w) {
          if (absE) { de = p.w.E - e; e = p.w.E; } else { de = p.w.E; }
        }
      }
      return de;
    }
    for (i = 0; i < start; i++) { var p0 = parse(lines[i]); if (p0) { step(p0); } }
    var state0 = { absE: absE, x: x, y: y, e: e };

    // pass 1: extrusion points above the marker, for the pillar centres
    var points = [], type = '';
    for (i = start + 1; i < end; i++) {
      var ln = lines[i];
      if (ln.charAt(0) === ';') {
        if (ln.lastIndexOf(';TYPE:', 0) === 0) { type = ln.slice(6).trim(); }
        continue;
      }
      var p1 = parse(ln);
      if (!p1) { continue; }
      if (p1.cmd === 'G10' || p1.cmd === 'G11') { throw RetractError('firmware_retraction'); }
      if (p1.cmd === 'G91' || p1.cmd === 'G2' || p1.cmd === 'G3') { throw RetractError('unsupported', { cmd: p1.cmd }); }
      var px = x, py = y;
      var d1 = step(p1);
      if (d1 > 0 && ('X' in p1.w || 'Y' in p1.w) && !/skirt|brim|wipe tower/i.test(type)) {
        points.push([(px + x) / 2, (py + y) / 2]);
      }
    }
    var loc = locate(points, ring);

    // pass 2: the events
    absE = state0.absE; x = state0.x; y = state0.y; e = state0.e;
    var out = lines.slice();
    var offset = 0;                    // absolute E only: new coordinate minus the slicer's
    var lastPillar = -1;               // pillar of the last extrusion
    var ev = null;                     // the open event
    var counts = new Array(n).fill(0);
    var layer = -1, perLayer = [], layersSeen = 0;
    var kept = 0, rewritten = 0, profile = [];
    var wipe = false;

    function close(arrive) {
      var gap = gapOf(ev.from, arrive, n);
      if (gap < 0) { kept++; ev = null; return; }
      var pulled = -ev.pulls.reduce(function (s, q) { return s + q.de; }, 0);
      if (!(pulled > 1e-6)) { kept++; ev = null; return; }
      var L = ring.lengths[gap];
      var f = L / pulled;
      var extra = ev.push.de - pulled;
      var newPush = Math.max(0, L + extra);
      profile.push(pulled);
      // write the new numbers. Absolute E: replay the event from the offset it started with; a
      // G92 inside it (PrusaSlicer's layer change) resets the coordinate, the push back then
      // carries the difference on to the lines after the event.
      var off = ev.offset0;
      ev.items.forEach(function (q) {
        if (q.g92) { off = 0; return; }
        var nd = q === ev.push ? newPush : q.de * f;
        if (absE) { off += nd - q.de; out[q.i] = setE(lines[q.i], q.abs + off); }
        else { out[q.i] = setE(lines[q.i], nd); }
      });
      offset = absE ? off : 0;
      counts[gap]++;
      if (layer >= 0) { perLayer[layer][gap]++; }
      rewritten++;
      ev = null;
    }

    for (i = start + 1; i < lines.length; i++) {
      var line = lines[i];
      if (i >= end) {
        // the end G-code: no events, only an absolute-E offset carried until the next G92
        if (ev) { kept++; ev = null; }
        if (!absE || !offset) { break; }
        var pe = parse(line);
        if (!pe) { continue; }
        if (pe.cmd === 'M83' || (pe.cmd === 'G92' && 'E' in pe.w)) { break; }
        if ((pe.cmd === 'G0' || pe.cmd === 'G1') && 'E' in pe.w) { out[i] = setE(line, pe.w.E + offset); }
        continue;
      }
      if (line.charAt(0) === ';') {
        if (line.lastIndexOf(';LAYER_CHANGE', 0) === 0) {
          layer++; layersSeen++; perLayer.push(new Array(n).fill(0));
        } else if (line.lastIndexOf(';WIPE_START', 0) === 0) { wipe = true; }
        continue;
      }
      var p = parse(line);
      if (!p) { continue; }
      if (p.cmd === 'G92' && 'E' in p.w) {
        // a new E origin: the slicer's numbers after it need no offset
        step(p); offset = 0;
        if (ev) { ev.items.push({ g92: true }); }
        continue;
      }
      var hadE = (p.cmd === 'G0' || p.cmd === 'G1') && 'E' in p.w;
      var sx = x, sy = y;
      var de = step(p);
      var moves = 'X' in p.w || 'Y' in p.w;
      if (!hadE) { continue; }
      if (de < -1e-9) {                                 // a pull: starts or extends an event
        if (ev && ev.push) { kept++; ev = null; }        // pulled again before landing: start over
        if (!ev) { ev = { from: lastPillar, pulls: [], push: null, items: [], offset0: offset }; }
        var q = { i: i, de: de, abs: p.w.E };
        ev.pulls.push(q); ev.items.push(q);
        if (absE && offset) { out[i] = setE(line, p.w.E + offset); }
      } else if (de > 1e-9 && !moves) {                  // a push back (unretract)
        if (ev && !ev.push) { ev.push = { i: i, de: de, abs: p.w.E }; ev.items.push(ev.push); }
        if (absE && offset) { out[i] = setE(line, p.w.E + offset); }
      } else if (de > 1e-9 && moves) {                   // an extrusion
        if (ev && ev.push) { close(pillarAt(loc, sx, sy)); }
        else if (ev) { kept++; ev = null; }              // pulled but never pushed back: leave it
        if (absE && offset) { out[i] = setE(line, p.w.E + offset); }
        lastPillar = pillarAt(loc, x, y);
      } else if (absE && offset) {
        out[i] = setE(line, p.w.E + offset);
      }
    }
    if (rewritten === 0) {
      throw RetractError(kept ? 'no_gap_travels' : 'no_retracts');
    }
    var missing = [];
    for (var k = 0; k < n; k++) { if (!counts[k]) { missing.push(k); } }
    if (missing.length) {
      throw RetractError('gap_missed', { gaps: missing.map(function (k) { return ring.lengths[k]; }) });
    }
    // layers where every gap had its travel
    var full = perLayer.filter(function (r) { return r.every(function (c) { return c > 0; }); }).length;

    profile.sort(function (a, b) { return a - b; });
    var summary = {
      lengths: ring.lengths,
      perGap: counts,
      rewritten: rewritten,
      kept: kept,
      layers: layersSeen,
      fullLayers: full,
      absoluteE: state0.absE || absE,
      wipe: wipe,
      profileLength: profile.length ? Math.round(profile[profile.length >> 1] * 1000) / 1000 : 0
    };
    out.splice(start + 1, 0, ';HEXCALIBR rewritten: ' + rewritten + ' retractions on ' + n +
      ' gaps (' + ring.lengths.join(', ') + ' mm), ' + kept + ' others kept');
    return { gcode: out.join(nl), summary: summary };
  }

  function outputName(name, lengths) {
    var base = String(name || 'retraction').replace(/\.(bgcode|gcode|gco|g)$/i, '');
    return base + '_retraction-' + lengths[0] + '-' + lengths[lengths.length - 1] + '.gcode';
  }

  return { rewrite: rewrite, outputName: outputName, parseMarker: parseMarker, MARKER: MARKER, _num: num };
}));
