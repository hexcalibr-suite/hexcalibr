// SPDX-FileCopyrightText: 2026 Matteo Beretta
// SPDX-License-Identifier: GPL-3.0-or-later
//
// HexBgcode: decoder for Prusa binary G-code (.bgcode, format version 1).
// Turns a .bgcode file into the same plain-text G-code that the reference
// binary-to-ASCII conversion of libbgcode produces (metadata as "; key = value"
// comments, thumbnails as base64 comment blocks, G-code blocks with blank
// lines removed, slicer config at the end). Supports Deflate (through the
// standard DecompressionStream), Heatshrink 11/4 and 12/4, and MeatPack
// G-code encodings. No dependencies; works in browsers and in Node 18+.
//
// Usage:
//   HexBgcode.isBgcode(bytes)            -> boolean
//   await HexBgcode.toAscii(bytes)       -> string
//   await HexBgcode.toAsciiBytes(bytes)  -> Uint8Array (UTF-8 bytes, exact)
//   HexBgcode.blocks(bytes)              -> block list (debugging)

(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HexBgcode = api;
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : null), function () {
  'use strict';

  // ---- constants --------------------------------------------------------

  var BLOCK_FILE_META = 0;
  var BLOCK_GCODE = 1;
  var BLOCK_SLICER_META = 2;
  var BLOCK_PRINTER_META = 3;
  var BLOCK_PRINT_META = 4;
  var BLOCK_THUMBNAIL = 5;
  var BLOCK_NAMES = ['file metadata', 'gcode', 'slicer metadata', 'printer metadata', 'print metadata', 'thumbnail'];

  var COMP_NONE = 0;
  var COMP_DEFLATE = 1;
  var COMP_HS_11_4 = 2;
  var COMP_HS_12_4 = 3;

  var NL = 10, SP = 32, TAB = 9, SEMI = 59;

  var utf8 = (typeof TextEncoder !== 'undefined') ? new TextEncoder() : null;
  function bytesOf(s) { return utf8.encode(s); }
  function textOf(b) { return new TextDecoder('utf-8', { ignoreBOM: true }).decode(b); }

  var B_NL = bytesOf('\n');
  var B_SEMI_SP = bytesOf('; ');
  var B_EQ = bytesOf(' = ');

  function fail(msg) { throw new Error(msg); }

  // ---- CRC32 (IEEE 802.3, reflected, as used by zlib) --------------------

  var CRC_TABLE = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) {
      var c = n;
      for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();

  function crc32(bytes, start, end) {
    var c = 0xFFFFFFFF;
    for (var i = start; i < end; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  // ---- container parsing ------------------------------------------------

  function isBgcode(bytes) {
    return !!bytes && bytes.length >= 4 &&
      bytes[0] === 0x47 && bytes[1] === 0x43 && bytes[2] === 0x44 && bytes[3] === 0x45; // "GCDE"
  }

  function u16(b, o) { return b[o] | (b[o + 1] << 8); }
  function u32(b, o) { return (b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)) >>> 0; }

  // Parses the file header and every block header, verifying CRC32 when the
  // file declares it. Returns { version, checksumType, blocks: [...] }.
  function parse(bytes) {
    if (!(bytes instanceof Uint8Array)) fail('Expected the file contents as a Uint8Array.');
    if (bytes.length < 10) {
      if (!isBgcode(bytes)) fail('Not a binary G-code file (missing GCDE signature).');
      fail('The file is truncated (incomplete file header).');
    }
    if (!isBgcode(bytes)) fail('Not a binary G-code file (missing GCDE signature).');
    var version = u32(bytes, 4);
    if (version !== 1) fail('Unsupported binary G-code version ' + version + ' (only version 1 is supported).');
    var checksumType = u16(bytes, 8);
    if (checksumType > 1) fail('Unknown checksum type ' + checksumType + '.');
    var crcSize = checksumType === 1 ? 4 : 0;

    var blocks = [];
    var len = bytes.length;
    var off = 10;
    while (off < len) {
      if (off + 8 > len) fail('The file is truncated (incomplete block header at byte ' + off + ').');
      var type = u16(bytes, off);
      if (type > 5) fail('Unknown block type ' + type + ' at byte ' + off + '.');
      var compression = u16(bytes, off + 2);
      if (compression > 3) fail('Unknown compression ' + compression + ' in ' + BLOCK_NAMES[type] + ' block at byte ' + off + '.');
      var uncompressedSize = u32(bytes, off + 4);
      var headerSize = compression === COMP_NONE ? 8 : 12;
      if (off + headerSize > len) fail('The file is truncated (incomplete block header at byte ' + off + ').');
      var compressedSize = compression === COMP_NONE ? uncompressedSize : u32(bytes, off + 8);
      var paramsSize = type === BLOCK_THUMBNAIL ? 6 : 2;
      var paramsOffset = off + headerSize;
      var dataOffset = paramsOffset + paramsSize;
      var dataSize = compression === COMP_NONE ? uncompressedSize : compressedSize;
      var end = dataOffset + dataSize + crcSize;
      if (end > len) fail('The file is truncated (' + BLOCK_NAMES[type] + ' block at byte ' + off + ' runs past the end).');

      var block = {
        offset: off,
        type: type,
        typeName: BLOCK_NAMES[type],
        compression: compression,
        uncompressedSize: uncompressedSize,
        compressedSize: compression === COMP_NONE ? 0 : compressedSize,
        headerSize: headerSize,
        paramsOffset: paramsOffset,
        dataOffset: dataOffset,
        dataSize: dataSize,
        end: end
      };
      if (type === BLOCK_THUMBNAIL) {
        block.format = u16(bytes, paramsOffset);
        block.width = u16(bytes, paramsOffset + 2);
        block.height = u16(bytes, paramsOffset + 4);
        if (block.format > 2) fail('Unknown thumbnail format ' + block.format + ' at byte ' + off + '.');
        if (block.width === 0 || block.height === 0 || uncompressedSize === 0) fail('Invalid thumbnail block at byte ' + off + '.');
      } else {
        block.encoding = u16(bytes, paramsOffset);
        if (type === BLOCK_GCODE) {
          if (block.encoding > 2) fail('Unknown G-code encoding ' + block.encoding + ' at byte ' + off + '.');
        } else if (block.encoding > 1) {
          fail('Unknown metadata encoding ' + block.encoding + ' in ' + BLOCK_NAMES[type] + ' block at byte ' + off + '.');
        }
      }
      if (crcSize) {
        var stored = u32(bytes, end - 4);
        var computed = crc32(bytes, off, end - 4);
        if (stored !== computed) fail('Checksum mismatch in ' + BLOCK_NAMES[type] + ' block at byte ' + off + ': the file is corrupted.');
        block.crc = stored;
      }
      blocks.push(block);
      off = end;
    }
    return { version: version, checksumType: checksumType, blocks: blocks };
  }

  // ---- decompression ----------------------------------------------------

  function concatChunks(chunks, total) {
    var out = new Uint8Array(total);
    var p = 0;
    for (var i = 0; i < chunks.length; i++) { out.set(chunks[i], p); p += chunks[i].length; }
    return out;
  }

  // libbgcode writes zlib-wrapped streams (RFC 1950), i.e. format 'deflate'.
  async function inflate(data, expectedSize) {
    if (data.length === 0 && expectedSize === 0) return new Uint8Array(0);
    if (typeof DecompressionStream === 'undefined') fail('This browser cannot decompress Deflate data (DecompressionStream is missing).');
    var ds = new DecompressionStream('deflate');
    var writer = ds.writable.getWriter();
    writer.write(data).catch(function () {});
    writer.close().catch(function () {});
    var reader = ds.readable.getReader();
    var chunks = [];
    var total = 0;
    try {
      for (;;) {
        var r = await reader.read();
        if (r.done) break;
        chunks.push(r.value);
        total += r.value.length;
        if (total > expectedSize) break;
      }
    } catch (e) {
      fail('Deflate data is corrupted.');
    }
    if (total !== expectedSize) {
      reader.cancel().catch(function () {});
      fail('Deflate data does not match the declared size (' + total + ' instead of ' + expectedSize + ' bytes).');
    }
    return chunks.length === 1 ? chunks[0] : concatChunks(chunks, total);
  }

  // Heatshrink (LZSS) decoder, written from the published bitstream format:
  // MSB-first bits; tag 1 = literal byte (8 bits); tag 0 = back-reference with
  // (windowBits) index and (lookaheadBits) count, distance = index + 1,
  // length = count + 1. The window starts zero-filled.
  function unheatshrink(src, outSize, windowBits, lookaheadBits) {
    if (outSize === 0) {
      if (src.length !== 0) fail('Heatshrink data does not match the declared size.');
      return new Uint8Array(0);
    }
    var out = new Uint8Array(outSize);
    var o = 0;
    var inPos = 0;
    var inLen = src.length;
    var acc = 0;      // bit accumulator (at most 24 live bits)
    var accBits = 0;

    function bits(n) {
      while (accBits < n) {
        if (inPos >= inLen) return -1;
        acc = ((acc << 8) | src[inPos++]) & 0xFFFFFF;
        accBits += 8;
      }
      accBits -= n;
      return (acc >>> accBits) & ((1 << n) - 1);
    }

    while (o < outSize) {
      var tag = bits(1);
      if (tag < 0) break;
      if (tag === 1) {
        var lit = bits(8);
        if (lit < 0) break;
        out[o++] = lit;
      } else {
        var idx = bits(windowBits);
        if (idx < 0) break;
        var cnt = bits(lookaheadBits);
        if (cnt < 0) break;
        var dist = idx + 1;
        var n = cnt + 1;
        if (o + n > outSize) fail('Heatshrink data is longer than the declared size.');
        for (var k = 0; k < n; k++, o++) out[o] = o >= dist ? out[o - dist] : 0;
      }
    }
    if (o !== outSize) fail('Heatshrink data is shorter than the declared size.');
    if (inPos < inLen) fail('Heatshrink data is longer than the declared size.');
    return out;
  }

  async function blockData(bytes, b) {
    var raw = bytes.subarray(b.dataOffset, b.dataOffset + b.dataSize);
    switch (b.compression) {
      case COMP_NONE: return raw;
      case COMP_DEFLATE: return inflate(raw, b.uncompressedSize);
      case COMP_HS_11_4: return unheatshrink(raw, b.uncompressedSize, 11, 4);
      case COMP_HS_12_4: return unheatshrink(raw, b.uncompressedSize, 12, 4);
    }
    fail('Unknown compression ' + b.compression + '.');
  }

  // ---- MeatPack ---------------------------------------------------------

  // 4-bit codes: 0-9 digits, 10 '.', 11 ' ' (or 'E' in no-spaces mode),
  // 12 '\n', 13 'G', 14 'X'; 15 means "a full byte follows".
  var MP_CHARS = [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 46, SP, NL, 71, 88, 0];
  var MP_SIGNAL = 0xFF;
  var MP_CMD_ENABLE = 251, MP_CMD_DISABLE = 250, MP_CMD_RESET = 249;
  var MP_CMD_NOSPACES_ON = 247, MP_CMD_NOSPACES_OFF = 246;

  // Letters after which the converter re-inserts the separating space on
  // lines that start with 'G' (MeatPack drops spaces when packing them).
  var GPARAM = new Uint8Array(256);
  'XYZEFIJRSGPWHCA'.split('').forEach(function (ch) { GPARAM[ch.charCodeAt(0)] = 1; });

  function unmeatpack(src) {
    var cap = src.length * 2 + 64;
    var out = new Uint8Array(cap);
    var n = 0;
    var packing = false, noSpaces = false;
    var signalCount = 0, commandNext = false;
    var fullQueue = 0, held = 0;
    var spacing = false;

    function put(c) {
      if (n + 2 > cap) {
        cap *= 2;
        var bigger = new Uint8Array(cap);
        bigger.set(out.subarray(0, n));
        out = bigger;
      }
      var lineStartG = false;
      if (c === 71 && (n === 0 || out[n - 1] === NL)) { spacing = true; lineStartG = true; }
      else if (c === NL || c === SP) spacing = false;
      if (spacing && !lineStartG && GPARAM[c]) out[n++] = SP;
      if (c !== NL || n === 0 || out[n - 1] !== NL) out[n++] = c;
    }

    function nibble(v) { return (v === 11 && noSpaces) ? 69 : MP_CHARS[v]; }

    function receive(c) {
      if (!packing) { put(c); return; }
      if (fullQueue > 0) {
        put(c);
        if (held) { put(held); held = 0; }
        fullQueue--;
        return;
      }
      var lo = c & 15, hi = c >>> 4;
      if (lo === 15) {
        fullQueue++;
        if (hi === 15) fullQueue++;
        else held = nibble(hi);
      } else {
        var first = nibble(lo);
        put(first);
        if (first !== NL) {
          if (hi === 15) fullQueue++;
          else put(nibble(hi));
        }
      }
    }

    for (var i = 0, len = src.length; i < len; i++) {
      var c = src[i];
      if (c === MP_SIGNAL) {
        if (signalCount > 0) { commandNext = true; signalCount = 0; }
        else signalCount++;
      } else if (commandNext) {
        commandNext = false;
        if (c === MP_CMD_ENABLE) packing = true;
        else if (c === MP_CMD_DISABLE || c === MP_CMD_RESET) packing = false;
        else if (c === MP_CMD_NOSPACES_ON) noSpaces = true;
        else if (c === MP_CMD_NOSPACES_OFF) noSpaces = false;
      } else {
        if (signalCount > 0) { receive(MP_SIGNAL); signalCount = 0; }
        receive(c);
      }
    }
    return out.subarray(0, n);
  }

  // ---- output helpers ---------------------------------------------------

  // INI metadata: "key=value" lines; lines without '=' are ignored.
  // JSON metadata: one pair with an empty key.
  function metadataPairs(data, encoding) {
    var pairs = [];
    if (encoding === 1) { pairs.push({ key: new Uint8Array(0), value: data }); return pairs; }
    var i = 0, len = data.length;
    while (i < len) {
      var e = data.indexOf(NL, i);
      if (e < 0) e = len;
      var eq = data.indexOf(61, i); // '='
      if (eq >= 0 && eq < e) pairs.push({ key: data.subarray(i, eq), value: data.subarray(eq + 1, e) });
      i = e + 1;
    }
    return pairs;
  }

  function findValue(pairs, name) {
    for (var i = 0; i < pairs.length; i++) if (textOf(pairs[i].key) === name) return pairs[i].value;
    return null;
  }

  var B64 = bytesOf('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/');

  function base64(data) {
    var len = data.length;
    var out = new Uint8Array(Math.ceil(len / 3) * 4);
    var o = 0, i = 0;
    for (; i + 2 < len; i += 3) {
      var v = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
      out[o++] = B64[v >>> 18]; out[o++] = B64[(v >>> 12) & 63]; out[o++] = B64[(v >>> 6) & 63]; out[o++] = B64[v & 63];
    }
    if (i < len) {
      var w = data[i] << 16;
      if (i + 1 < len) w |= data[i + 1] << 8;
      out[o++] = B64[w >>> 18]; out[o++] = B64[(w >>> 12) & 63];
      out[o++] = (i + 1 < len) ? B64[(w >>> 6) & 63] : 61;
      out[o++] = 61;
    }
    return out;
  }

  // Keeps every line of a G-code block except those that are empty after
  // stripping spaces/tabs and at most one leading ';'. Each kept line gets
  // a '\n' (also the last one, if the block did not end with one).
  function pushNonEmptyLines(out, data) {
    var len = data.length;
    var runStart = 0;
    var i = 0;
    while (i < len) {
      var e = data.indexOf(NL, i);
      var last = e < 0;
      if (last) e = len;
      var p = i;
      while (p < e && (data[p] === SP || data[p] === TAB)) p++;
      if (p < e && data[p] === SEMI) {
        p++;
        while (p < e && (data[p] === SP || data[p] === TAB)) p++;
      }
      if (p === e) {
        // blank line: flush the run of kept lines before it
        if (i > runStart) out.push(data.subarray(runStart, i));
        runStart = e + 1;
      } else if (last) {
        out.push(data.subarray(runStart, len));
        out.push(B_NL);
        runStart = len + 1;
      }
      i = e + 1;
    }
    if (runStart < len) out.push(data.subarray(runStart, len));
  }

  function pushMetadata(out, pairs) {
    for (var i = 0; i < pairs.length; i++) {
      out.push(B_SEMI_SP, pairs[i].key, B_EQ, pairs[i].value, B_NL);
    }
  }

  function pushThumbnail(out, block, data) {
    var name = ['thumbnail', 'thumbnail_JPG', 'thumbnail_QOI'][block.format];
    var enc = base64(data);
    out.push(bytesOf('\n;\n; ' + name + ' begin ' + block.width + 'x' + block.height + ' ' + enc.length + '\n'));
    for (var p = 0; p < enc.length; p += 78) {
      out.push(B_SEMI_SP, enc.subarray(p, Math.min(p + 78, enc.length)), B_NL);
    }
    out.push(bytesOf('; ' + name + ' end\n;\n'));
  }

  // ---- conversion -------------------------------------------------------

  function orderError(what) { fail('Unexpected block order in the file (' + what + ').'); }

  async function metaOf(bytes, b) { return metadataPairs(await blockData(bytes, b), b.encoding); }

  async function toAsciiBytes(bytes) {
    var parsed = parse(bytes);
    var blocks = parsed.blocks;
    var nb = blocks.length;
    var out = [];
    var i = 0;

    if (nb === 0) orderError('no blocks');

    // 1. file metadata -> "; generated by ..." header
    if (blocks[0].type === BLOCK_FILE_META) {
      var fm = await metaOf(bytes, blocks[0]);
      var producer = findValue(fm, 'Producer');
      var producedOn = findValue(fm, 'Produced on');
      var preparedBy = findValue(fm, 'Prepared by');
      out.push(bytesOf('; generated by '), producer || bytesOf('Unknown'));
      if (producedOn) out.push(bytesOf(' on '), producedOn);
      if (preparedBy) out.push(bytesOf('\n; prepared by '), preparedBy);
      out.push(bytesOf('\n\n\n'));
      i = 1;
    }

    // 2. printer metadata
    if (i >= nb || blocks[i].type !== BLOCK_PRINTER_META) orderError('printer metadata missing');
    pushMetadata(out, await metaOf(bytes, blocks[i]));
    i++;

    // 3. thumbnails
    while (i < nb && blocks[i].type === BLOCK_THUMBNAIL) {
      pushThumbnail(out, blocks[i], await blockData(bytes, blocks[i]));
      i++;
    }
    var afterThumbs = i;
    out.push(B_NL);

    // 4. G-code: the first run of G-code blocks after the print metadata
    var g = afterThumbs + 1;
    while (g < nb && blocks[g].type !== BLOCK_GCODE) g++;
    if (g >= nb) orderError('no G-code blocks');
    var gEnd = g;
    while (gEnd < nb && blocks[gEnd].type === BLOCK_GCODE) gEnd++;
    // Decompress concurrently, emit in order.
    var pending = [];
    for (var k = g; k < gEnd; k++) pending.push(blockData(bytes, blocks[k]));
    var decoded = await Promise.all(pending);
    for (k = g; k < gEnd; k++) {
      var gb = blocks[k];
      var data = decoded[k - g];
      if (gb.encoding !== 0) data = unmeatpack(data);
      pushNonEmptyLines(out, data);
    }

    // 5. print metadata
    if (afterThumbs >= nb || blocks[afterThumbs].type !== BLOCK_PRINT_META) orderError('print metadata missing');
    out.push(B_NL);
    pushMetadata(out, await metaOf(bytes, blocks[afterThumbs]));

    // 6. slicer metadata (one or two blocks: legacy INI and/or JSON)
    var json = null, ini = null;
    for (var s = 0; s < 2; s++) {
      var sb = blocks[afterThumbs + 1 + s];
      if (!sb) orderError('slicer metadata missing');
      if (sb.type !== BLOCK_SLICER_META) {
        if (s === 0) orderError('slicer metadata missing');
        break;
      }
      var pairs = await metaOf(bytes, sb);
      if (sb.encoding === 1) json = pairs; else ini = pairs;
    }
    if (json) {
      out.push(bytesOf('\n; prusaslicer_json_config = begin\n'), B_SEMI_SP, json.length ? json[0].value : new Uint8Array(0), B_NL);
      out.push(bytesOf('; prusaslicer_json_config = end\n'));
    }
    if (ini) {
      out.push(bytesOf('\n; prusaslicer_config = begin\n'));
      pushMetadata(out, ini);
      out.push(bytesOf('; prusaslicer_config = end\n\n'));
    }

    var total = 0;
    for (k = 0; k < out.length; k++) total += out[k].length;
    return concatChunks(out, total);
  }

  async function toAscii(bytes) {
    return textOf(await toAsciiBytes(bytes));
  }

  function blocks(bytes) {
    return parse(bytes).blocks;
  }

  return {
    isBgcode: isBgcode,
    toAscii: toAscii,
    toAsciiBytes: toAsciiBytes,
    blocks: blocks
  };
});
