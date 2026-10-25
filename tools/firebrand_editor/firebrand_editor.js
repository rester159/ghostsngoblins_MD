// Firebrand pixel editor: palette-locked editing of Firebrand's sprite bank.
// A bank frame is 0x300 bytes (art/firebrand/src/build.py): 512 bytes = the 32x32
// body in Arthur's layout (16 tiles, column-major, canvas x 8..39), then two 8x32
// wing columns of 4 tiles each (x 0..7 and x 40..47). 108 frames: Arthur's 84
// frame slots, then Firebrand's walk and hover cycles (right, left).
// firebrand_flags.bin, one byte per frame: bit0/bit1 wing columns used, bit2 palette
// line 2, bit3 a walking slot (the game shows the walk cycle), bit4 faces left.
(() => {
  const D = window.FIREBRAND_DATA;
  const W = 48, H = 32, FRAME_BYTES = 0x300, COUNT = 108;
  const F_PAL2 = 4, F_RUN = 8, F_FACES_LEFT = 16;
  const FB_WALK = 84, FB_FLY = 96;
  const MARGIN = 3;
  const STORE = 'firebrand_editor_v1';
  const LINES = { 0: D.line0, 2: D.line2 };

  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const BANK = b64(D.bank), FLAGS = b64(D.flags), ARTHUR = b64(D.arthur), ARR = b64(D.arremer);
  const lineOf = s => FLAGS[s] & F_PAL2 ? 2 : 0;

  // ---------- bank format ----------
  function decodeTiles(bytes, off, g, x0, cols) {
    for (let tx = 0; tx < cols; tx++) for (let ty = 0; ty < 4; ty++) {
      const t = off + (tx * 4 + ty) * 32;
      for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
        const b = bytes[t + y * 4 + (x >> 1)];
        g[(ty * 8 + y) * W + x0 + tx * 8 + x] = x & 1 ? b & 15 : b >> 4;
      }
    }
  }
  function encodeTiles(g, out, off, x0, cols) {
    let p = off;
    for (let tx = 0; tx < cols; tx++) for (let ty = 0; ty < 4; ty++)
      for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x += 2) {
        const r = (ty * 8 + y) * W + x0 + tx * 8 + x;
        out[p++] = (g[r] << 4) | g[r + 1];
      }
  }
  function decodeFrame(bytes, off) {
    const g = new Uint8Array(W * H);
    decodeTiles(bytes, off, g, 8, 4);
    decodeTiles(bytes, off + 0x200, g, 0, 1);
    decodeTiles(bytes, off + 0x280, g, 40, 1);
    return g;
  }
  function encodeFrame(g, out, off) {
    encodeTiles(g, out, off, 8, 4);
    encodeTiles(g, out, off + 0x200, 0, 1);
    encodeTiles(g, out, off + 0x280, 40, 1);
  }
  const colUsed = (g, x0) => { for (let y = 0; y < H; y++) for (let x = x0; x < x0 + 8; x++) if (g[y * W + x]) return true; return false; };

  const GAME = Array.from({ length: COUNT }, (_, s) => decodeFrame(BANK, s * FRAME_BYTES));
  // Arthur's frame for slots 0..83, placed in the body columns
  const ARTHUR_F = Array.from({ length: COUNT }, (_, s) => {
    if (s >= 84) return null;
    const g = new Uint8Array(W * H);
    decodeTiles(ARTHUR, s * 0x200, g, 8, 4);
    return g;
  });
  const ARR_LINE2 = new Set(D.arremerLine2);
  const ARREMER = Array.from({ length: ARR.length / FRAME_BYTES }, (_, k) => {
    const g = new Uint8Array(W * H);
    for (let p = 0; p < W * H; p += 2) { const b = ARR[k * FRAME_BYTES + p / 2]; g[p] = b >> 4; g[p + 1] = b & 15; }
    return { g, line: ARR_LINE2.has(k) ? 2 : 0 };
  });

  // ---------- slots ----------
  const STREAM = ['A0', 'A1', 'A2', 'A3', 'A4', 'A7', 'A8', 'A9'];
  const NAMES = Array.from({ length: COUNT }, (_, s) => {
    if (s < 11) return 'boot A' + s;
    if (s < 84) { const k = s - 11; return k < 8 ? STREAM[k] : k === 8 ? 'B0/A10' : 'B' + (k - 8); }
    const c = ['Walk →', 'Walk ←', 'Hover →', 'Hover ←'][Math.floor((s - 84) / 6)];
    return `${c} ${(s - 84) % 6 + 1}`;
  });
  // Mirrors: the boot copies (slots 0..10) are never shown in play, their streamed
  // twins are; walking slots are replaced by the walk cycle in game.
  const ALIAS = {};
  [11, 12, 13, 14, 15, 14, 13, 16, 17, 18, 19].forEach((t, s) => { ALIAS[s] = t; });
  for (let s = 11; s < 84; s++) if (FLAGS[s] & F_RUN) ALIAS[s] = FB_WALK + (FLAGS[s] & F_FACES_LEFT ? 6 : 0);
  const src = s => ALIAS[s] ?? s;
  const EDITABLE = COUNT - Object.keys(ALIAS).length;
  const ANIMS = D.anims;
  const USED = NAMES.map(() => []);
  ANIMS.forEach(a => new Set(a.f.map(e => e[0])).forEach(s => { if (s >= 0) USED[s].push(`${a.group}: ${a.name}`); }));
  const NOTE = {};
  for (let s = 45; s <= 49; s++) NOTE[s] = 'not shown in play (Arthur\'s empty frame and armor pieces)';
  const aliasNote = s => s < 11 ? `boot copy; the game shows ${NAMES[ALIAS[s]]} — edit that`
    : `a walking slot; the game shows the walk cycle — edit ${NAMES[ALIAS[s]]}`;

  // ---------- working sheet ----------
  let frames = [];
  let sheetKind = 'game';
  function newSheet(kind) {
    sheetKind = kind;
    frames = GAME.map(g => {
      const base = kind === 'blank' ? new Uint8Array(W * H) : g.slice();
      return { base, cur: base.slice(), undo: [], redo: [] };
    });
  }
  const isMod = f => f.cur.some((v, i) => v !== f.base[i]);
  const hex = g => Array.from(g, v => v.toString(16)).join('');
  function save() {
    try { localStorage.setItem(STORE, JSON.stringify({ kind: sheetKind, frames: frames.map(f => hex(f.cur)) })); } catch (e) {}
  }
  function restore() {
    try {
      const s = JSON.parse(localStorage.getItem(STORE) || 'null');
      if (!s || (s.kind !== 'game' && s.kind !== 'blank')) return false;
      newSheet(s.kind);
      s.frames.forEach((h, i) => { if (frames[i] && h.length === W * H) for (let p = 0; p < h.length; p++) frames[i].cur[p] = parseInt(h[p], 16); });
      return true;
    } catch (e) { return false; }
  }
  if (!restore()) newSheet('game');

  // ---------- state ----------
  let sel = 28, color = 1, tool = 'pen', grid = true, tiles = true, overlay = '', overlayFull = false, arrPick = 5;
  let zoom = 12;
  const $ = id => document.getElementById(id);
  const ed = $('ed'), ctx = ed.getContext('2d');

  // ---------- palette (locked to the slot's line) ----------
  const palEl = $('pal');
  const swatches = Array.from({ length: 16 }, (_, i) => {
    const d = document.createElement('div');
    d.className = 'sw' + (i === 0 ? ' t' : '');
    d.innerHTML = `<span>${i.toString(16).toUpperCase()}</span>`;
    d.onclick = () => setColor(i);
    palEl.appendChild(d);
    return d;
  });
  function showPalette() {
    const line = lineOf(sel), pal = LINES[line];
    swatches.forEach((d, i) => {
      if (i) { d.style.background = `rgb(${pal[i]})`; d.title = `Index ${i}: rgb(${pal[i]})`; }
      else d.title = 'Index 0: transparent';
    });
    $('palLine').textContent = line === 2 ? 'line 2 — flames' : 'line 0 — Firebrand';
    $('palNote').textContent = line === 2
      ? 'This slot is drawn with palette line 2 (the burn-up flames). Its colors can\'t be mixed with line 0.'
      : 'This slot is drawn with palette line 0, shared with Arthur and every player sprite.';
  }
  function setColor(i) { color = i; swatches.forEach((d, k) => d.classList.toggle('sel', k === i)); }

  // nearest color of another line, for imports across the palette boundary
  function convert(g, fromLine, toLine) {
    if (fromLine === toLine) return g.slice();
    const a = LINES[fromLine], b = LINES[toLine], map = [0];
    for (let i = 1; i < 16; i++) {
      let best = 1, bd = Infinity;
      for (let j = 1; j < 16; j++) {
        const d = (a[i][0] - b[j][0]) ** 2 * 2 + (a[i][1] - b[j][1]) ** 2 * 4 + (a[i][2] - b[j][2]) ** 2 * 3;
        if (d < bd) { bd = d; best = j; }
      }
      map[i] = best;
    }
    return g.map(v => map[v]);
  }

  // ---------- drawing helpers ----------
  function drawSmall(c, g, line, scale) {
    if (c.width !== W * scale) { c.width = W * scale; c.height = H * scale; }
    const x = c.getContext('2d');
    x.clearRect(0, 0, c.width, c.height);
    if (!g) return;
    x.fillStyle = '#ffffff0a'; x.fillRect(8 * scale, 0, 32 * scale, c.height);   // body area
    const pal = LINES[line];
    for (let p = 0; p < W * H; p++) if (g[p]) {
      x.fillStyle = `rgb(${pal[g[p]]})`;
      x.fillRect((p % W) * scale, ((p / W) | 0) * scale, scale, scale);
    }
  }

  // ---------- thumbnails ----------
  const framesEl = $('frames');
  const thumbs = NAMES.map((name, s) => {
    const d = document.createElement('div');
    const alias = ALIAS[s] !== undefined;
    d.className = 'thumb' + ((USED[s].length || s >= 84) && !alias && !NOTE[s] ? '' : ' unused');
    d.title = alias ? `${name}: ${aliasNote(s)}` : NOTE[s] ? `${name}: ${NOTE[s]}`
      : USED[s].length ? `${name} — used in:\n${USED[s].join('\n')}` : `${name} — not seen in any recorded animation`;
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    d.appendChild(c);
    d.insertAdjacentHTML('beforeend', `<span class="n">${alias ? '= ' + NAMES[ALIAS[s]] : name}</span>` +
      (lineOf(s) === 2 ? '<span class="pl">line 2</span>' : ''));
    d.onclick = () => select(src(s));
    framesEl.appendChild(d);
    return d;
  });
  function refreshThumb(s) {
    drawSmall(thumbs[s].querySelector('canvas'), frames[src(s)].cur, lineOf(s), 1);
    thumbs[s].classList.toggle('mod', ALIAS[s] === undefined && isMod(frames[s]));
  }
  function progress() {
    const n = frames.filter((f, s) => ALIAS[s] === undefined && isMod(f)).length;
    $('progress').textContent = `Sheet started from ${sheetKind === 'blank' ? 'blank' : 'the in-game Firebrand'} · ${n}/${EDITABLE} frames changed`;
  }
  function refreshAll() { frames.forEach((_, s) => refreshThumb(s)); progress(); draw(); }

  // ---------- Red Arremer strip ----------
  const arrEl = $('arremer');
  const arrCanvases = ARREMER.map((a, k) => {
    const c = document.createElement('canvas');
    drawSmall(c, a.g, a.line, 1);
    c.title = `Red Arremer frame ${k} (palette line ${a.line})`;
    c.onclick = () => pickArremer(k);
    c.ondblclick = () => { pickArremer(k); importArremer(); };
    arrEl.appendChild(c);
    return c;
  });
  function pickArremer(k) {
    arrPick = k;
    arrCanvases.forEach((c, i) => c.classList.toggle('sel', i === k));
    if (overlay === 'arremer') draw();
  }

  // ---------- editor canvas ----------
  function fitZoom() {
    const w = $('work');
    const availW = w.clientWidth - 340 - 16 - 28, availH = w.clientHeight - 28 - 250;
    zoom = Math.max(5, Math.floor(Math.min(availW / (W + 2 * MARGIN), availH / (H + 2 * MARGIN))));
    ed.width = (W + 2 * MARGIN) * zoom; ed.height = (H + 2 * MARGIN) * zoom;
  }
  function overlayFrame() {
    if (overlay === 'game') return { g: GAME[sel], line: lineOf(sel) };
    if (overlay === 'arthur') return ARTHUR_F[sel] ? { g: ARTHUR_F[sel], line: 0 } : null;
    if (overlay === 'arremer') return { g: ARREMER[arrPick].g, line: ARREMER[arrPick].line };
    return null;
  }
  function draw() {
    const f = frames[sel], Z = zoom, O = MARGIN * Z, line = lineOf(sel), pal = LINES[line];
    const ref = overlayFrame();
    const full = overlayFull && ref;
    const g = full ? ref.g : f.cur, gp = full ? LINES[ref.line] : pal;
    ctx.fillStyle = '#16121a'; ctx.fillRect(0, 0, ed.width, ed.height);
    ctx.strokeStyle = '#ffffff0d'; ctx.lineWidth = 1;
    for (let k = -ed.height; k < ed.width; k += 8) { ctx.beginPath(); ctx.moveTo(k, 0); ctx.lineTo(k + ed.height, ed.height); ctx.stroke(); }
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
      const p = y * W + x, v = g[p], wing = x < 8 || x >= 40;
      if (v) ctx.fillStyle = `rgb(${gp[v]})`;
      else if (ref && !full && ref.g[p]) {
        const [r, gg, b] = LINES[ref.line][ref.g[p]];
        ctx.fillStyle = `rgb(${(r * .35 + 52 * .65) | 0},${(gg * .35 + 46 * .65) | 0},${(b * .35 + 58 * .65) | 0})`;
      } else ctx.fillStyle = wing ? ((x + y) & 1 ? '#2c3442' : '#27303c') : ((x + y) & 1 ? '#3d3544' : '#352e3b');
      ctx.fillRect(O + x * Z, O + y * Z, Z, Z);
    }
    if (grid && Z >= 7) {
      ctx.strokeStyle = '#00000040'; ctx.beginPath();
      for (let k = 1; k < W; k++) { ctx.moveTo(O + k * Z + .5, O); ctx.lineTo(O + k * Z + .5, O + H * Z); }
      for (let k = 1; k < H; k++) { ctx.moveTo(O, O + k * Z + .5); ctx.lineTo(O + W * Z, O + k * Z + .5); }
      ctx.stroke();
    }
    if (tiles) {
      ctx.strokeStyle = '#ffffff28'; ctx.beginPath();
      for (let k = 8; k < W; k += 8) { ctx.moveTo(O + k * Z + .5, O); ctx.lineTo(O + k * Z + .5, O + H * Z); }
      for (let k = 8; k < H; k += 8) { ctx.moveTo(O, O + k * Z + .5); ctx.lineTo(O + W * Z, O + k * Z + .5); }
      ctx.stroke();
    }
    // body (32x32) and the whole box (with wing columns)
    ctx.setLineDash([6, 4]); ctx.strokeStyle = '#ffffff70';
    ctx.strokeRect(O + 8 * Z + .5, O + .5, 32 * Z, H * Z);
    ctx.setLineDash([]);
    ctx.strokeStyle = full ? '#4aa3ff' : '#e8742e'; ctx.lineWidth = 2;
    ctx.strokeRect(O - 1, O - 1, W * Z + 2, H * Z + 2); ctx.lineWidth = 1;
    ctx.fillStyle = '#9a8fa2'; ctx.font = `${Math.max(10, Z)}px system-ui`;
    ctx.fillText('wing', O, O - 4); ctx.fillText('body', O + 8 * Z, O - 4); ctx.fillText('wing', O + 40 * Z, O - 4);
    if (full) { ctx.fillStyle = '#4aa3ff'; ctx.fillText('(reference)', O + 18 * Z, O - 4); }
    drawSmall($('refG'), GAME[sel], line, 2);
    drawSmall($('refA'), ARTHUR_F[sel], 0, 2);
    drawSmall($('refY'), f.cur, line, 2);
  }

  function select(s) {
    sel = src(Math.max(0, Math.min(COUNT - 1, s)));
    thumbs.forEach((t, k) => t.classList.toggle('sel', k === sel));
    thumbs[sel].scrollIntoView({ block: 'nearest' });
    $('usedIn').textContent = NOTE[sel] ? 'not shown in play' : USED[sel].length ? `${USED[sel].length} animation${USED[sel].length > 1 ? 's' : ''}` : 'unused in tests';
    showPalette(); draw(); info(null);
  }
  function stepFrame(d) {
    let s = sel + d;
    while (ALIAS[s] !== undefined) s += d;
    if (s >= 0 && s < COUNT) select(s);
  }
  function cellAt(e) {
    const r = ed.getBoundingClientRect();
    const x = Math.floor((e.clientX - r.left) * ed.width / r.width / zoom) - MARGIN;
    const y = Math.floor((e.clientY - r.top) * ed.height / r.height / zoom) - MARGIN;
    return { x, y, inside: x >= 0 && y >= 0 && x < W && y < H };
  }
  function info(c) {
    let s = `Slot ${sel}: ${NAMES[sel]}`;
    if (c) s += c.inside ? ` · x${c.x} y${c.y}${c.x < 8 || c.x >= 40 ? ' (wing column)' : ''} · index ${frames[sel].cur[c.y * W + c.x].toString(16).toUpperCase()}` : ' · outside the box (not paintable)';
    $('info').textContent = s;
  }

  function pushUndo(f) { f.undo.push(f.cur.slice()); if (f.undo.length > 200) f.undo.shift(); f.redo = []; }
  function commit() {
    refreshThumb(sel);
    for (const k in ALIAS) if (ALIAS[k] === sel) refreshThumb(+k);
    progress(); draw(); save();
  }
  function setFrame(g) { const f = frames[sel]; pushUndo(f); f.cur = g.slice(); commit(); }
  function importArremer() { const a = ARREMER[arrPick]; setFrame(convert(a.g, a.line, lineOf(sel))); }

  function fill(f, x, y, v) {
    const from = f.cur[y * W + x]; if (from === v) return;
    const st = [[x, y]];
    while (st.length) {
      const [cx, cy] = st.pop();
      if (cx < 0 || cy < 0 || cx >= W || cy >= H || f.cur[cy * W + cx] !== from) continue;
      f.cur[cy * W + cx] = v;
      st.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
    }
  }
  let painting = false;
  ed.addEventListener('contextmenu', e => e.preventDefault());
  ed.addEventListener('mousedown', e => {
    const c = cellAt(e); if (!c.inside || overlayFull) return;
    const f = frames[sel];
    if (e.button === 2 || tool === 'pick' || e.altKey) { setColor(f.cur[c.y * W + c.x]); return; }
    pushUndo(f);
    if (tool === 'fill') { fill(f, c.x, c.y, color); commit(); return; }
    painting = true; f.cur[c.y * W + c.x] = color; draw();
  });
  ed.addEventListener('mousemove', e => {
    const c = cellAt(e); info(c);
    if (painting && c.inside) { frames[sel].cur[c.y * W + c.x] = color; draw(); }
  });
  window.addEventListener('mouseup', () => { if (painting) { painting = false; commit(); } });
  function undo() { const f = frames[sel]; if (f.undo.length) { f.redo.push(f.cur); f.cur = f.undo.pop(); commit(); } }
  function redo() { const f = frames[sel]; if (f.redo.length) { f.undo.push(f.cur); f.cur = f.redo.pop(); commit(); } }
  function setTool(t) {
    tool = t;
    $('tPen').classList.toggle('on', t === 'pen');
    $('tFill').classList.toggle('on', t === 'fill');
    $('tPick').classList.toggle('on', t === 'pick');
  }
  $('tPen').onclick = () => setTool('pen');
  $('tFill').onclick = () => setTool('fill');
  $('tPick').onclick = () => setTool('pick');
  $('undo').onclick = undo; $('redo').onclick = redo;
  $('gridBtn').onclick = () => { grid = !grid; $('gridBtn').classList.toggle('on', grid); draw(); };
  $('tileBtn').onclick = () => { tiles = !tiles; $('tileBtn').classList.toggle('on', tiles); draw(); };
  $('overlaySel').onchange = e => { overlay = e.target.value; e.target.blur(); draw(); };
  $('impGame').onclick = () => setFrame(GAME[sel]);
  $('impArremer').onclick = importArremer;
  $('clearFrame').onclick = () => setFrame(new Uint8Array(W * H));
  $('revert').onclick = () => setFrame(frames[sel].base);
  $('refG').onclick = () => setFrame(GAME[sel]);
  $('refG').title = 'Click to import into your sheet';

  // ---------- new sheet ----------
  const dlg = $('newDlg');
  $('newBtn').onclick = () => dlg.showModal();
  dlg.querySelectorAll('button').forEach(b => b.onclick = () => {
    dlg.close();
    if (b.value === 'cancel') return;
    newSheet(b.value);
    if (b.value === 'blank' && !overlay) { overlay = 'game'; $('overlaySel').value = 'game'; }
    save(); refreshAll();
  });

  // ---------- animation tester ----------
  const animSel = $('animSel');
  let group = null, og = null;
  ANIMS.forEach((a, i) => {
    if (a.group !== group) { group = a.group; og = document.createElement('optgroup'); og.label = group; animSel.appendChild(og); }
    const o = document.createElement('option'); o.value = i; o.textContent = a.name + (a.loop ? ' ⟳' : ''); og.appendChild(o);
  });
  let anim = 0, tick = 0, playing = true, speed = 1, compare = true, acc = 0, last = 0;
  const AS = 3;
  const dyOf = (a, e) => a.loop ? 0 : e[1];
  function animRange(a) {
    let lo = 0, hi = 0;
    a.f.forEach(e => { lo = Math.min(lo, dyOf(a, e)); hi = Math.max(hi, dyOf(a, e)); });
    return { lo, hi };
  }
  function setAnim(i) {
    anim = (i + ANIMS.length) % ANIMS.length; tick = 0; animSel.value = anim;
    const used = new Set(ANIMS[anim].f.map(e => e[0]));
    thumbs.forEach((t, k) => t.classList.toggle('inanim', used.has(k)));
    const { lo, hi } = animRange(ANIMS[anim]);
    for (const c of [$('animY'), $('animG')]) { c.width = W * AS + 12; c.height = (H + hi - lo) * AS + 18; }
    drawAnim();
  }
  function drawAnimOn(c, sheet) {
    const a = ANIMS[anim], e = a.f[tick], s = e[0], { lo } = animRange(a);
    const x = c.getContext('2d');
    x.fillStyle = '#33283d'; x.fillRect(0, 0, c.width, c.height);
    const top = 6, groundY = top + (H - lo) * AS;
    x.fillStyle = '#3d4d38'; x.fillRect(0, groundY, c.width, c.height - groundY);
    if (s < 0) return;                    // hidden this tick (invincibility flash)
    const g = sheet[s], pal = LINES[lineOf(s)], ox = 6, oy = top + (dyOf(a, e) - lo) * AS;
    for (let p = 0; p < W * H; p++) if (g[p]) {
      x.fillStyle = `rgb(${pal[g[p]]})`;
      x.fillRect(ox + (p % W) * AS, oy + ((p / W) | 0) * AS, AS, AS);
    }
  }
  function drawAnim() {
    const a = ANIMS[anim], s = a.f[tick][0];
    drawAnimOn($('animY'), frames.map((_, k) => frames[src(k)].cur));
    if (compare) drawAnimOn($('animG'), GAME);
    $('animInfo').textContent = `tick ${tick + 1}/${a.f.length} (60 fps) · slot ${s < 0 ? '— (flash)' : `${s} ${NAMES[s]}`}${a.loop ? ' · loops' : ''}`;
  }
  function loop(t) {
    if (playing) {
      acc += Math.min(100, t - last) * speed;
      while (acc >= 1000 / 60) { acc -= 1000 / 60; tick++; if (tick >= ANIMS[anim].f.length) tick = 0; }
      drawAnim();
    }
    last = t; requestAnimationFrame(loop);
  }
  animSel.onchange = () => { setAnim(+animSel.value); animSel.blur(); };
  const setPlaying = p => { playing = p; $('playBtn').textContent = p ? 'Pause' : 'Play'; $('playBtn').classList.toggle('on', p); };
  $('playBtn').onclick = () => setPlaying(!playing);
  const step = d => { setPlaying(false); const a = ANIMS[anim]; tick = (tick + d + a.f.length) % a.f.length; drawAnim(); };
  $('stepBack').onclick = () => step(-1);
  $('stepFwd').onclick = () => step(1);
  $('speedSel').onchange = e => { speed = +e.target.value; e.target.blur(); };
  $('sideBtn').onclick = () => { compare = !compare; $('sideBtn').classList.toggle('on', compare); $('colG').style.display = compare ? '' : 'none'; drawAnim(); };
  const editCurrent = () => { const s = ANIMS[anim].f[tick][0]; if (s >= 0) { setPlaying(false); select(s); } };
  $('animY').onclick = editCurrent; $('animG').onclick = editCurrent;
  $('animY').title = $('animG').title = 'Click to edit the frame shown';

  // ---------- keyboard ----------
  window.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || dlg.open) return;
    const k = e.key.toLowerCase();
    if ((e.metaKey || e.ctrlKey) && k === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
    if ((e.metaKey || e.ctrlKey) && k === 'y') { e.preventDefault(); redo(); return; }
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (/^[0-9a-f]$/.test(k)) { setColor(parseInt(k, 16)); return; }
    if (k === 'b') setTool('pen');
    else if (k === 'g') setTool('fill');
    else if (k === 'i') setTool('pick');
    else if (k === 'h') $('gridBtn').click();
    else if (k === 'o' && overlay && !overlayFull) { overlayFull = true; draw(); }
    else if (k === 'arrowleft') { e.preventDefault(); stepFrame(-1); }
    else if (k === 'arrowright') { e.preventDefault(); stepFrame(1); }
    else if (k === 'arrowup') { e.preventDefault(); setAnim(anim - 1); }
    else if (k === 'arrowdown') { e.preventDefault(); setAnim(anim + 1); }
    else if (k === ' ') { e.preventDefault(); setPlaying(!playing); }
    else if (k === ',') step(-1);
    else if (k === '.') step(1);
  });
  window.addEventListener('keyup', e => { if (e.key.toLowerCase() === 'o' && overlayFull) { overlayFull = false; draw(); } });

  // ---------- export / import ----------
  // flags: the wing-column bits follow the pixels; palette line, walking and facing
  // bits stay as the game has them
  function exportFiles() {
    const bank = new Uint8Array(COUNT * FRAME_BYTES), flags = new Uint8Array(COUNT);
    for (let s = 0; s < COUNT; s++) {
      const g = frames[src(s)].cur;
      encodeFrame(g, bank, s * FRAME_BYTES);
      flags[s] = (FLAGS[s] & ~3) | (colUsed(g, 0) ? 1 : 0) | (colUsed(g, 40) ? 2 : 0);
    }
    return { bank, flags };
  }
  function download(name, blob) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  $('exportBtn').onclick = () => {
    const { bank, flags } = exportFiles();
    download('firebrand_bank.bin', new Blob([bank], { type: 'application/octet-stream' }));
    setTimeout(() => download('firebrand_flags.bin', new Blob([flags], { type: 'application/octet-stream' })), 300);
  };
  $('pngBtn').onclick = () => {
    const S = 3, cols = 12, cw = W * S + 6, ch = H * S + 6;
    const c = document.createElement('canvas');
    c.width = cols * cw; c.height = Math.ceil(COUNT / cols) * ch;
    const x = c.getContext('2d'); x.fillStyle = 'rgb(44,40,50)'; x.fillRect(0, 0, c.width, c.height);
    frames.forEach((_, s) => {
      const g = frames[src(s)].cur, pal = LINES[lineOf(s)], ox = (s % cols) * cw, oy = Math.floor(s / cols) * ch;
      for (let p = 0; p < W * H; p++) if (g[p]) {
        x.fillStyle = `rgb(${pal[g[p]]})`;
        x.fillRect(ox + (p % W) * S, oy + ((p / W) | 0) * S, S, S);
      }
    });
    c.toBlob(b => download('firebrand_edited_frames.png', b));
  };
  // A bank file replaces the sheet's pixels (undoable per frame); the flags file
  // is rebuilt on export, so loading one is not needed.
  $('loadBin').onchange = async e => {
    for (const file of e.target.files) {
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (bytes.length === COUNT) continue;
      if (bytes.length !== COUNT * FRAME_BYTES) { alert(`${file.name}: expected firebrand_bank.bin (${COUNT * FRAME_BYTES} bytes), got ${bytes.length}`); continue; }
      frames.forEach((f, s) => { pushUndo(f); f.cur = decodeFrame(bytes, s * FRAME_BYTES); });
    }
    e.target.value = '';
    save(); refreshAll();
  };

  // ---------- go ----------
  window.addEventListener('resize', () => { fitZoom(); draw(); });
  setColor(1);
  fitZoom(); pickArremer(arrPick); refreshAll(); select(sel); setAnim(0);
  requestAnimationFrame(t => { last = t; loop(t); });
})();
