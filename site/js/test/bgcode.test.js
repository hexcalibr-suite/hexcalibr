// SPDX-FileCopyrightText: 2026 Matteo Beretta
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Node test for ../bgcode.js. Run:  node site/js/test/bgcode.test.js [fixture-dir]
// (or set BGCODE_FIXTURES). For every <name>.bgcode in the directory that has a
// <name>_ref.gcode next to it, the decoded output must match byte for byte.
// Also checks that a flipped byte is caught by the CRC check.

'use strict';

const fs = require('fs');
const path = require('path');
const HexBgcode = require('../bgcode.js');

const DEFAULT_DIR = '/private/tmp/claude-501/-Users-matteo-Documents-Progetti-SlicerTest/8eedbe6d-313d-4cc8-a6ca-2dcb239d4d76/scratchpad/bgdata';
const dir = process.argv[2] || process.env.BGCODE_FIXTURES || DEFAULT_DIR;

let failures = 0;
function ok(msg) { console.log('ok   ' + msg); }
function bad(msg) { console.log('FAIL ' + msg); failures++; }

function firstDifference(a, b) {
  const n = Math.min(a.length, b.length);
  let i = 0;
  while (i < n && a[i] === b[i]) i++;
  if (i === n && a.length === b.length) return null;
  let line = 1;
  let lineStart = 0;
  for (let k = 0; k < i; k++) if (a[k] === 10) { line++; lineStart = k + 1; }
  const lineOf = (buf) => {
    let e = buf.indexOf(10, lineStart);
    if (e < 0) e = buf.length;
    return Buffer.from(buf.subarray(lineStart, e)).toString('utf8');
  };
  return { byte: i, line, got: lineOf(a), want: lineOf(b) };
}

function summary(blocks) {
  const combos = new Map();
  for (const b of blocks) {
    const key = b.typeName + ' comp=' + b.compression + (b.encoding !== undefined ? ' enc=' + b.encoding : ' fmt=' + b.format);
    combos.set(key, (combos.get(key) || 0) + 1);
  }
  return [...combos].map(([k, v]) => v + 'x ' + k).join(', ');
}

async function testFixture(bgPath, refPath) {
  const name = path.basename(bgPath);
  const input = new Uint8Array(fs.readFileSync(bgPath));
  const ref = new Uint8Array(fs.readFileSync(refPath));

  if (!HexBgcode.isBgcode(input)) { bad(name + ': isBgcode() returned false'); return; }
  console.log('     ' + name + ' blocks: ' + summary(HexBgcode.blocks(input)));

  const t0 = process.hrtime.bigint();
  const text = await HexBgcode.toAscii(input);
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  const got = new TextEncoder().encode(text);
  const diff = firstDifference(got, ref);
  if (diff) {
    bad(name + ': differs at byte ' + diff.byte + ', line ' + diff.line +
      ' (got ' + got.length + ' bytes, want ' + ref.length + ')\n       got:  ' + JSON.stringify(diff.got) +
      '\n       want: ' + JSON.stringify(diff.want));
  } else {
    ok(name + ': ' + got.length + ' bytes, identical to reference (' + ms.toFixed(1) + ' ms)');
  }

  const raw = await HexBgcode.toAsciiBytes(input);
  if (firstDifference(raw, ref)) bad(name + ': toAsciiBytes() differs from reference');
  else ok(name + ': toAsciiBytes() identical');
}

async function expectThrow(label, bytes, pattern) {
  try {
    await HexBgcode.toAscii(bytes);
    bad(label + ': did not throw');
  } catch (e) {
    if (pattern.test(e.message)) ok(label + ': threw "' + e.message + '"');
    else bad(label + ': threw unexpected message "' + e.message + '"');
  }
}

async function testErrors(bgPath) {
  const input = new Uint8Array(fs.readFileSync(bgPath));
  const blocks = HexBgcode.blocks(input);

  // Flip one byte inside the data of the first G-code block.
  const g = blocks.find((b) => b.type === 1);
  const flipped = input.slice();
  flipped[g.dataOffset + (g.dataSize >> 1)] ^= 0x01;
  await expectThrow('flipped data byte', flipped, /checksum mismatch/i);

  // Flip one byte in a stored checksum.
  const crcFlip = input.slice();
  crcFlip[blocks[0].end - 1] ^= 0x80;
  await expectThrow('flipped CRC byte', crcFlip, /checksum mismatch/i);

  const badMagic = input.slice();
  badMagic[0] = 0x58;
  await expectThrow('bad magic', badMagic, /not a binary g-code/i);
  if (HexBgcode.isBgcode(badMagic)) bad('isBgcode() accepted bad magic');

  const badVersion = input.slice();
  badVersion[4] = 2;
  await expectThrow('unsupported version', badVersion, /unsupported .*version/i);

  await expectThrow('truncated file', input.subarray(0, input.length - 3), /truncated/i);
}

async function main() {
  if (!fs.existsSync(dir)) {
    console.log('FAIL fixture directory not found: ' + dir);
    process.exit(1);
  }
  const files = fs.readdirSync(dir).filter((f) => f.endsWith('.bgcode')).sort();
  let tested = 0;
  for (const f of files) {
    const ref = path.join(dir, f.replace(/\.bgcode$/, '_ref.gcode'));
    if (!fs.existsSync(ref)) continue;
    await testFixture(path.join(dir, f), ref);
    tested++;
  }
  if (tested === 0) bad('no <name>.bgcode + <name>_ref.gcode pairs in ' + dir);
  else await testErrors(path.join(dir, files[0]));

  console.log(failures ? failures + ' failure(s)' : 'all tests passed');
  process.exit(failures ? 1 : 0);
}

main().catch((e) => { console.log('FAIL unexpected error: ' + (e && e.stack || e)); process.exit(1); });
