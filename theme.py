"""화면 꾸미기 (CSS). 시작할 때 apply() 가 페이지에 붙인다."""
from js import document

CSS = '''
:root {
  --bg: #eef1f5;
  --paper: #ffffff;
  --ink: #0f172a;
  --ink-2: #334155;
  --muted: #64748b;
  --line: #e2e8f0;
  --line-2: #cbd5e1;
  --accent: #2563eb;
  --danger: #dc2626;
  --danger-ink: #b91c1c;
  --ok: #16a34a;
  --warn: #d97706;
  --radius: 14px;
  --shadow: 0 1px 2px rgb(15 23 42 / 0.06), 0 8px 24px rgb(15 23 42 / 0.08);
  --topbar: 60px;
  font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}

* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); overflow: hidden; }
button, input, textarea { font: inherit; color: inherit; }
button { cursor: pointer; }
svg { display: block; }
[hidden] { display: none !important; }

/* ── 상단 바 ─────────────────────────── */
.topbar {
  height: var(--topbar);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
  position: relative; z-index: 5;
}
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; }
.brand-mark { width: 34px; height: 34px; border-radius: 10px; background: #fee2e2; display: grid; place-items: center; }
.brand-mark svg { width: 22px; height: 22px; }
.brand-mark path { fill: var(--danger); }
.brand-mark circle { fill: #fff; }
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }
.brand-text strong { font-size: 17px; letter-spacing: -0.02em; }
.brand-text small { font-size: 12px; color: var(--muted); }

.btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 40px; padding: 0 16px; border-radius: 999px; border: 0;
  font-weight: 600; font-size: 14px; letter-spacing: -0.01em;
  transition: background .15s, transform .1s;
}
.btn:active { transform: scale(.97); }
.btn svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover { background: var(--danger-ink); }
.btn-danger[aria-pressed="true"] { background: var(--ink); }
.btn-quiet { background: #f1f5f9; color: var(--ink-2); }
.btn-quiet:hover { background: #e2e8f0; }
.btn-ghost-light { background: rgb(255 255 255 / .16); color: #fff; height: 32px; padding: 0 12px; }
.btn-ghost-light:hover { background: rgb(255 255 255 / .26); }

/* ── 레이아웃 ───────────────────────── */
.layout {
  height: calc(100dvh - var(--topbar));
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
}
.stage { position: relative; overflow: hidden; background:
  radial-gradient(circle at 1px 1px, #d5dbe4 1px, transparent 0) 0 0 / 22px 22px, #f6f8fb; }
.panel {
  background: var(--paper); border-left: 1px solid var(--line);
  overflow-y: auto; display: flex; flex-direction: column;
}

/* ── 지도 ───────────────────────────── */
.map { width: 100%; height: 100%; touch-action: none; user-select: none; cursor: grab; }
.map.is-panning { cursor: grabbing; }
.map.is-locked { cursor: default; }
.map.is-locked ~ .map-tools { display: none; }
.map.is-loading .layer-plan { opacity: 0; }
.layer-plan { transition: opacity .2s; }
.map .layer-plan > path.l { transition: opacity .2s; }
body.reporting .map { cursor: crosshair; }

.bld { cursor: pointer; }
.bld path { fill: var(--c); fill-opacity: .26; stroke: var(--c); stroke-width: 1.4; vector-effect: non-scaling-stroke; transition: fill-opacity .15s; }
.bld:hover path, .bld.is-hot path { fill-opacity: .5; }
.bld-label { pointer-events: none; }
.bld-label rect { fill: #fff; stroke: var(--c); vector-effect: non-scaling-stroke; }
.bld-label text { fill: var(--ink); font-weight: 700; text-anchor: middle; dominant-baseline: central; letter-spacing: -0.02em; }
.bld-label .count { fill: #fff; }
.bld-label .count-bg { fill: var(--danger); stroke: #fff; }
body.reporting .bld { pointer-events: none; }

.pin { cursor: pointer; }
.pin .drop { stroke: #fff; stroke-width: 2; }
.pin .core { fill: #fff; }
.pin.done .drop { fill: #94a3b8 !important; }
.pin.is-selected .halo { opacity: 1; }
.pin .halo { opacity: 0; fill: none; stroke: currentColor; stroke-width: 3; }
.pin:hover .drop { filter: brightness(1.08); }
.draft-pin .drop { fill: var(--ink); }
.draft-pin .ring { fill: none; stroke: var(--ink); stroke-width: 2; animation: ring 1.4s ease-out infinite; transform-origin: 0 0; }
@keyframes ring { from { transform: scale(.4); opacity: .9; } to { transform: scale(1.8); opacity: 0; } }

/* ── 지도 위 UI ─────────────────────── */
.stage-top { position: absolute; top: 14px; left: 14px; right: 80px; display: flex; gap: 8px; pointer-events: none; }
.crumbs {
  pointer-events: auto;
  display: inline-flex; align-items: center; gap: 2px; flex-wrap: wrap;
  background: var(--paper); border-radius: 999px; padding: 4px; box-shadow: var(--shadow);
  font-size: 14px;
}
.crumbs a, .crumbs span { padding: 6px 12px; border-radius: 999px; text-decoration: none; color: var(--muted); font-weight: 600; }
.crumbs a:hover { background: #f1f5f9; color: var(--ink); }
.crumbs .sep { padding: 0; color: var(--line-2); }
.crumbs .here { color: var(--ink); }

.floorbar {
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);
  display: flex; flex-direction: column-reverse; gap: 4px;
  background: var(--paper); padding: 6px; border-radius: 16px; box-shadow: var(--shadow);
}
.floorbar:empty { display: none; }
.floorbar button {
  min-width: 46px; height: 40px; padding: 0 8px; border-radius: 11px; border: 0; background: transparent;
  font-weight: 700; font-size: 13px; color: var(--ink-2); position: relative;
}
.floorbar button:hover { background: #f1f5f9; }
.floorbar button[aria-selected="true"] { background: var(--ink); color: #fff; }
.floorbar .dot {
  position: absolute; top: 3px; right: 3px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 999px; background: var(--danger); color: #fff; font-size: 10px; line-height: 16px;
}

.map-tools {
  position: absolute; left: 14px; bottom: 14px;
  display: flex; gap: 2px; background: var(--paper); padding: 4px; border-radius: 14px; box-shadow: var(--shadow);
}
.tool { width: 38px; height: 38px; border: 0; border-radius: 10px; background: transparent; display: grid; place-items: center; color: var(--ink-2); }
.tool:hover { background: #f1f5f9; }
.tool svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.tool[aria-pressed="false"] { color: var(--line-2); }

.mode-banner {
  position: absolute; left: 50%; bottom: 18px; transform: translateX(-50%);
  display: flex; align-items: center; gap: 12px;
  background: var(--ink); color: #fff; padding: 8px 8px 8px 16px; border-radius: 999px;
  box-shadow: 0 10px 30px rgb(15 23 42 / .3); font-size: 14px; font-weight: 600; white-space: nowrap;
  max-width: calc(100% - 28px);
}
.mode-banner #modeText { overflow: hidden; text-overflow: ellipsis; }
.pulse { width: 10px; height: 10px; border-radius: 50%; background: #f87171; box-shadow: 0 0 0 0 rgb(248 113 113 / .7); animation: pulse 1.4s infinite; flex: none; }
@keyframes pulse { to { box-shadow: 0 0 0 10px rgb(248 113 113 / 0); } }

.loading { position: absolute; inset: 0; display: grid; place-items: center; color: var(--muted); font-weight: 600; pointer-events: none; }

/* ── 패널 ───────────────────────────── */
.ctx { padding: 20px 20px 8px; }
.ctx h1 { font-size: 22px; margin: 0; letter-spacing: -0.03em; }
.ctx .sub { color: var(--muted); font-size: 14px; margin: 4px 0 0; }
.ctx .meta { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
.tag { font-size: 12px; font-weight: 600; padding: 4px 9px; border-radius: 999px; background: #f1f5f9; color: var(--ink-2); }
.tag.color { color: #fff; background: var(--c); }
.hint { margin: 12px 0 0; font-size: 13px; color: var(--muted); line-height: 1.5; }

.bld-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; }
.bld-card {
  text-align: left; border: 1px solid var(--line); background: var(--paper); border-radius: 12px; padding: 10px 12px;
  display: flex; flex-direction: column; gap: 2px; position: relative; transition: border-color .15s, box-shadow .15s;
}
.bld-card::before { content: ""; position: absolute; left: 0; top: 10px; bottom: 10px; width: 3px; border-radius: 0 3px 3px 0; background: var(--c); }
.bld-card:hover { border-color: var(--c); box-shadow: var(--shadow); }
.bld-card strong { font-size: 15px; letter-spacing: -0.02em; }
.bld-card small { font-size: 12px; color: var(--muted); }
.bld-card .n { position: absolute; top: 8px; right: 8px; font-size: 11px; font-weight: 700; color: #fff; background: var(--danger); border-radius: 999px; padding: 1px 7px; }

.floor-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }
.floor-list button { border: 1px solid var(--line); background: var(--paper); border-radius: 10px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--ink-2); }
.floor-list button[aria-selected="true"] { background: var(--ink); border-color: var(--ink); color: #fff; }

.reports { border-top: 1px solid var(--line); margin-top: 12px; padding: 16px 20px 20px; display: flex; flex-direction: column; flex: 1; }
.reports-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.reports-head h2 { font-size: 16px; margin: 0; }
.stats { display: flex; gap: 10px; font-size: 12px; color: var(--muted); }
.stats b { color: var(--ink); font-size: 14px; margin-left: 2px; }
.stats .urgent b { color: var(--danger); }
.filters { display: flex; justify-content: space-between; gap: 8px; margin: 12px 0; flex-wrap: wrap; }
.seg { display: inline-flex; background: #f1f5f9; padding: 3px; border-radius: 10px; }
.seg button { border: 0; background: transparent; padding: 5px 10px; border-radius: 8px; font-size: 12.5px; font-weight: 600; color: var(--muted); }
.seg button[aria-pressed="true"] { background: var(--paper); color: var(--ink); box-shadow: 0 1px 2px rgb(15 23 42 / .1); }

.report-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.report-item {
  display: grid; grid-template-columns: 10px 1fr auto; gap: 4px 10px; align-items: start;
  padding: 12px; border-radius: 12px; border: 1px solid var(--line); background: var(--paper); cursor: pointer; text-align: left; width: 100%;
}
.report-item:hover { border-color: var(--line-2); box-shadow: var(--shadow); }
.report-item.is-selected { border-color: var(--ink); }
.report-item .sev-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 5px; }
.report-item .t { font-weight: 600; font-size: 14.5px; letter-spacing: -0.01em; line-height: 1.35; }
.report-item .w { grid-column: 2 / 4; font-size: 12.5px; color: var(--muted); }
.status { font-size: 11.5px; font-weight: 700; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }
.status.new { background: #fee2e2; color: var(--danger-ink); }
.status.doing { background: #fef3c7; color: #92400e; }
.status.done { background: #dcfce7; color: #166534; }
.empty { text-align: center; color: var(--muted); font-size: 14px; padding: 28px 12px; border: 1px dashed var(--line-2); border-radius: 12px; line-height: 1.6; }
.empty button { margin-top: 10px; }
.panel-foot { display: flex; gap: 16px; justify-content: center; margin-top: auto; padding-top: 20px; }
.link { background: none; border: 0; padding: 0; color: var(--muted); font-size: 12.5px; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }
.link:hover { color: var(--ink); }

/* ── 시트(다이얼로그) ────────────────── */
.sheet {
  border: 0; padding: 0; border-radius: 20px; width: min(520px, calc(100vw - 24px)); max-height: calc(100dvh - 32px);
  box-shadow: 0 30px 80px rgb(15 23 42 / .35); color: var(--ink); background: var(--paper);
}
.sheet::backdrop { background: rgb(15 23 42 / .45); backdrop-filter: blur(2px); }
.sheet form, #detailBody { display: flex; flex-direction: column; max-height: calc(100dvh - 32px); }
.sheet-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 20px 20px 8px; }
.sheet-head h2 { margin: 2px 0 0; font-size: 20px; letter-spacing: -0.03em; }
.eyebrow { margin: 0; font-size: 13px; font-weight: 600; color: var(--danger); }
.icon-btn { width: 36px; height: 36px; border-radius: 50%; border: 0; background: #f1f5f9; display: grid; place-items: center; flex: none; }
.icon-btn svg { width: 18px; height: 18px; stroke: var(--ink-2); stroke-width: 2.2; stroke-linecap: round; fill: none; }
.sheet-body { padding: 8px 20px 4px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.sheet-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px 20px; border-top: 1px solid var(--line); margin-top: 12px; }
fieldset { border: 0; margin: 0; padding: 0; }
legend, .field > span { font-size: 13px; font-weight: 700; color: var(--ink-2); margin-bottom: 8px; display: block; padding: 0; }
.field { display: flex; flex-direction: column; }
.field em { color: var(--danger); font-style: normal; }
.field input, .field textarea {
  border: 1px solid var(--line-2); border-radius: 10px; padding: 10px 12px; font-size: 15px; background: #fff; resize: vertical;
}
.field input:focus, .field textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; border-color: transparent; }
.chips, .sev { display: flex; flex-wrap: wrap; gap: 6px; }
.chips label, .sev label { position: relative; }
.chips input, .sev input { position: absolute; opacity: 0; pointer-events: none; }
.chips span, .sev span {
  display: inline-flex; align-items: center; gap: 5px; padding: 7px 12px; border-radius: 999px;
  border: 1px solid var(--line-2); font-size: 13.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; user-select: none;
}
.chips input:checked + span { background: var(--ink); border-color: var(--ink); color: #fff; }
.sev span::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
.sev input:checked + span { background: var(--c); border-color: var(--c); color: #fff; }
.sev input:checked + span::before { background: #fff; }
.chips input:focus-visible + span, .sev input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }
.photo-drop {
  display: grid; place-items: center; min-height: 88px; border: 1.5px dashed var(--line-2); border-radius: 12px;
  color: var(--muted); font-size: 14px; font-weight: 600; cursor: pointer; overflow: hidden; position: relative;
}
.photo-drop:hover { border-color: var(--ink-2); color: var(--ink); }
.photo-drop img { width: 100%; max-height: 220px; object-fit: cover; }
.photo-drop img:not([hidden]) + span { position: absolute; bottom: 8px; right: 8px; background: rgb(15 23 42 / .7); color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 12px; }

.detail-photo { width: 100%; max-height: 300px; object-fit: cover; border-radius: 12px; }
.detail-grid { display: grid; grid-template-columns: 84px 1fr; gap: 8px 12px; font-size: 14px; margin: 0; }
.detail-grid dt { color: var(--muted); }
.detail-grid dd { margin: 0; font-weight: 500; }
.detail-desc { white-space: pre-wrap; line-height: 1.6; font-size: 15px; margin: 0; background: #f8fafc; padding: 12px 14px; border-radius: 12px; }
.detail-actions { display: flex; gap: 8px; justify-content: space-between; align-items: center; flex-wrap: wrap; }
.btn-text-danger { background: none; border: 0; color: var(--danger); font-weight: 600; font-size: 13.5px; padding: 8px 4px; }

.toast {
  position: fixed; left: 50%; top: calc(var(--topbar) + 14px); transform: translate(-50%, -20px);
  background: var(--ink); color: #fff; padding: 10px 18px; border-radius: 999px; font-size: 14px; font-weight: 600;
  opacity: 0; pointer-events: none; transition: opacity .2s, transform .2s; z-index: 50;
}
.toast.show { opacity: 1; transform: translate(-50%, 0); }

/* ── 모바일 ─────────────────────────── */
@media (max-width: 880px) {
  body { overflow: auto; }
  .layout { display: flex; flex-direction: column; height: auto; }
  .stage { height: 62dvh; min-height: 360px; flex: none; }
  .panel { border-left: 0; border-top: 1px solid var(--line); overflow: visible; }
  .brand-text small { display: none; }
  .stage-top { right: 76px; }
  .floorbar { top: auto; bottom: 14px; transform: none; max-height: calc(100% - 80px); overflow-y: auto; }
  .floorbar button { min-width: 42px; height: 36px; }
  .mode-banner { bottom: 70px; }
  .sheet { width: 100vw; max-width: 100vw; margin: auto 0 0; border-radius: 20px 20px 0 0; max-height: 92dvh; }
  .sheet form, #detailBody { max-height: 92dvh; }
}
@media (max-width: 420px) {
  .topbar .btn { padding: 0 14px; }
  .brand-mark { width: 30px; height: 30px; }
}

/* ── v2 (PyScript) 추가 ───────────────── */
#loading {
  position: fixed; inset: 0; z-index: 60; display: grid; place-items: center;
  background: rgb(246 248 251 / .92); color: var(--ink-2); font-weight: 600; font-size: 15px;
}
.report-item .sev-dot { width: auto; height: auto; margin: 0; font-size: 11px; line-height: 1.6; }
.sev-tag { display: inline-flex; align-items: center; gap: 5px; font-weight: 700; color: var(--c); }
.sev-tag::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
.demo-note { margin: 14px 0 0; padding: 10px 12px; border-radius: 10px; background: #fef9c3; color: #854d0e; font-size: 12.5px; line-height: 1.5; }
.status.rejected { background: #e2e8f0; color: #475569; }
.btn:disabled { opacity: .5; cursor: default; }

/* ── 선생님 화면 ───────────────────────── */
body.teacher { overflow: auto; background: var(--bg); }
.t-mark { background: #dbeafe; font-size: 18px; }
.who { font-size: 14px; font-weight: 600; color: var(--ink-2); margin-right: 8px; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: #1d4ed8; }
.t-login { min-height: calc(100dvh - var(--topbar)); display: grid; place-items: center; padding: 16px; }
.t-login .t-card { width: min(400px, 100%); display: flex; flex-direction: column; gap: 14px; }
.t-login h1 { margin: 0; font-size: 22px; }
.t-login .sub { margin: -6px 0 0; color: var(--muted); font-size: 14px; }
.t-login .btn { justify-content: center; }
.t-error { margin: 0; color: var(--danger); font-size: 13.5px; font-weight: 600; }
.t-card { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); }
.t-card h3 { margin: 0 0 14px; font-size: 15px; letter-spacing: -0.02em; }
.t-card h3 small { color: var(--muted); font-weight: 500; font-size: 12.5px; margin-left: 6px; }
.t-main { max-width: 1180px; margin: 0 auto; padding: 18px 16px 48px; display: flex; flex-direction: column; gap: 16px; }
.t-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); overflow-x: auto; }
.t-tabs button { border: 0; background: none; padding: 10px 14px; font-weight: 600; font-size: 14.5px; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; white-space: nowrap; }
.t-tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); }
.t-tab { display: flex; flex-direction: column; gap: 16px; }
.t-tab[hidden] { display: none; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
.tile { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.tile span { color: var(--muted); font-size: 13px; font-weight: 600; }
.tile b { font-size: 28px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }
.tile.urgent b { color: var(--danger); }
.t-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.bars { display: flex; flex-direction: column; gap: 8px; }
.bar-row { display: grid; grid-template-columns: 110px 1fr 32px; gap: 10px; align-items: center; font-size: 13.5px; }
.bar-label { color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { height: 14px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.bar-fill { display: block; height: 100%; background: var(--accent); border-radius: 0 4px 4px 0; min-width: 4px; }
.bar-row:hover .bar-fill { background: #1d4ed8; }
.bar-val { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }
.cols-wrap { position: relative; padding-left: 36px; }
.cols-max { position: absolute; left: 0; top: -4px; font-size: 11.5px; color: var(--muted); }
.cols { height: 140px; display: flex; align-items: flex-end; gap: 3px; border-bottom: 1px solid var(--line-2); background: linear-gradient(#eef2f7 1px, transparent 1px) 0 0 / 100% 50%; }
.col { flex: 1; height: 100%; display: flex; align-items: flex-end; cursor: default; }
.col span { display: block; width: 100%; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 0; }
.col:hover span { background: #1d4ed8; }
.cols-axis { display: flex; justify-content: space-between; padding-left: 36px; margin-top: 6px; font-size: 12px; color: var(--muted); }
.hot-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.t-empty { color: var(--muted); font-size: 14px; text-align: center; padding: 10px; list-style: none; }
.t-filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }
.t-filters label { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; font-weight: 700; color: var(--ink-2); }
.t-filters label.grow { flex: 1; min-width: 180px; }
.t-filters select, .t-filters input, .t-input, .t-maptools select {
  border: 1px solid var(--line-2); border-radius: 10px; padding: 8px 10px; font-size: 14px; background: #fff; font-weight: 500;
}
.t-count { margin: 0; font-size: 13px; color: var(--muted); }
.t-table-wrap { overflow-x: auto; background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); }
.t-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.t-table th { text-align: left; font-size: 12px; color: var(--muted); font-weight: 700; padding: 10px 12px; border-bottom: 1px solid var(--line); background: #f8fafc; white-space: nowrap; }
.t-table td { padding: 10px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
.t-table td.title { white-space: normal; font-weight: 600; min-width: 180px; }
.t-table tbody tr { cursor: pointer; }
.t-table tbody tr:hover { background: #f8fafc; }
.t-table tbody tr.is-selected { background: #eff6ff; }
.t-maptools { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.t-maptools .floor-list { margin: 0; }
.t-maptools .floor-list button { cursor: pointer; }
.t-check { display: inline-flex; gap: 6px; align-items: center; font-size: 13.5px; font-weight: 600; color: var(--ink-2); }
.t-mapbox { height: min(70dvh, 640px); background: radial-gradient(circle at 1px 1px, #d5dbe4 1px, transparent 0) 0 0 / 22px 22px, #f6f8fb; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.sheet.wide { width: min(980px, calc(100vw - 24px)); }
.sheet.wide .sheet-body { overflow-y: auto; }
.t-detail { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.mini-map { height: 260px; border: 1px solid var(--line); border-radius: 12px; background: #f8fafc; }
.t-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; border-top: 1px solid var(--line); padding-top: 16px; margin-top: 4px; }
.t-actions > div { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }
.t-actions h4 { margin: 4px 0 0; font-size: 13.5px; }
.t-actions .t-input { width: 100%; }
.t-actions .seg { flex-wrap: wrap; }
.t-events { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; width: 100%; max-height: 220px; overflow-y: auto; }
.t-events li { border-left: 3px solid var(--line); padding: 2px 0 2px 10px; display: flex; flex-direction: column; font-size: 13px; }
.t-events li span { color: var(--muted); font-size: 12px; }
@media (max-width: 880px) {
  .t-grid2, .t-detail, .t-actions { grid-template-columns: 1fr; }
  .who { display: none; }
}

/* ── v2.2 연결복도 버튼 · 검색 ───────────── */
.link { cursor: pointer; }
.link rect { fill: var(--accent); stroke: #fff; stroke-width: 2; filter: drop-shadow(0 2px 4px rgb(15 23 42 / 0.25)); }
.link text { fill: #fff; font-weight: 700; text-anchor: middle; dominant-baseline: central; letter-spacing: -0.02em; }
.link .arrow { fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.link:hover rect { fill: #1d4ed8; }
body.reporting .link { pointer-events: none; opacity: 0.5; }

.hit { pointer-events: none; }
.hit .ring { fill: rgb(37 99 235 / 0.12); stroke: var(--accent); stroke-width: 3; }
.hit .wave { fill: none; stroke: var(--accent); stroke-width: 2; transform-box: fill-box; transform-origin: center; animation: hit-wave 1.4s ease-out 3; opacity: 0; }
@keyframes hit-wave { from { transform: scale(0.6); opacity: 0.9; } to { transform: scale(1.9); opacity: 0; } }

.stage-top { flex-wrap: wrap; align-items: flex-start; }
.search {
  pointer-events: auto; position: relative;
  display: flex; align-items: center; gap: 6px;
  background: var(--paper); border-radius: 999px; padding: 0 12px; height: 40px; box-shadow: var(--shadow);
  width: 230px; max-width: 100%;
}
.search > svg { width: 18px; height: 18px; flex: none; fill: none; stroke: var(--muted); stroke-width: 2; stroke-linecap: round; }
.search input { border: 0; outline: 0; background: transparent; font: inherit; font-size: 15px; color: var(--ink); width: 100%; min-width: 0; }
.search:focus-within { box-shadow: 0 0 0 2px var(--accent), var(--shadow); }
.search-results {
  position: absolute; top: calc(100% + 6px); left: 0; width: max(100%, 260px); margin: 0; padding: 6px; list-style: none;
  background: var(--paper); border-radius: 12px; box-shadow: var(--shadow); max-height: 50vh; overflow-y: auto; z-index: 5;
}
.search-results li { display: flex; flex-direction: column; gap: 1px; padding: 8px 10px; border-radius: 8px; cursor: pointer; }
.search-results li strong { font-size: 15px; color: var(--ink); }
.search-results li small { font-size: 12.5px; color: var(--muted); }
.search-results li[aria-selected="true"], .search-results li:hover { background: #eff6ff; }
.search-results .empty { cursor: default; color: var(--muted); font-size: 14px; }
.search-results .empty:hover { background: none; }
@media (max-width: 880px) {
  .search { width: 100%; }
}

/* ── v2.2.1 위험/불편 신고 ───────────── */
.kinds { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.kinds label { position: relative; cursor: pointer; }
.kinds input { position: absolute; opacity: 0; pointer-events: none; }
.kinds span {
  display: flex; flex-direction: column; gap: 2px; height: 100%;
  padding: 10px 12px; border: 2px solid var(--line); border-radius: 12px; background: var(--paper);
}
.kinds b { font-size: 16px; color: var(--ink); }
.kinds small { font-size: 12.5px; color: var(--muted); line-height: 1.35; }
.kinds .kind-danger input:checked + span { border-color: var(--danger); background: #fef2f2; }
.kinds .kind-incon input:checked + span { border-color: #7c3aed; background: #f5f3ff; }
.kinds input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }
.kind-tag { display: inline-block; font-size: 12px; font-weight: 700; padding: 1px 7px; border-radius: 999px; white-space: nowrap; vertical-align: 1px; }
.kind-tag.kind-danger { color: #b91c1c; background: #fee2e2; }
.kind-tag.kind-incon { color: #6d28d9; background: #ede9fe; }
#formDialog[data-kind="incon"] #formSubmit { background: #7c3aed; border-color: #7c3aed; }
#formDialog[data-kind="incon"] #formSubmit:hover { background: #6d28d9; }

/* ── v2.2.2 오른쪽 패널 뒤로 가기 ───────────── */
.back-btn {
  display: inline-flex; align-items: center; gap: 4px; margin-bottom: 10px;
  padding: 7px 14px 7px 10px; border-radius: 999px; background: #f1f5f9; color: var(--ink);
  font-size: 14px; font-weight: 700; text-decoration: none;
}
.back-btn:hover { background: #e2e8f0; }
.back-btn svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
/* ── 장난 신고 막기 · 로그인 유지 ─────── */
.check { display: flex; gap: 10px; align-items: flex-start; cursor: pointer; }
.check input { width: 20px; height: 20px; margin: 1px 0 0; accent-color: var(--accent); flex: none; }
.check span { display: flex; flex-direction: column; gap: 2px; }
.check b { font-size: 14.5px; color: var(--ink); }
.check small { font-size: 12.5px; color: var(--muted); line-height: 1.4; }
.notice { border: 1px solid #fcd34d; background: #fffbeb; border-radius: 12px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; }
.notice > b { font-size: 14px; color: #92400e; }
.notice ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--ink-2); }
.notice .check { padding-top: 6px; border-top: 1px dashed #fcd34d; }
.t-abuse { margin-top: 14px; }
.t-abuse:empty { display: none; }
.t-abuse .blocked { color: var(--danger); }

/* ── 학생 구글 로그인 ─────────────────── */
.login-lead { margin: 0; font-size: 14.5px; line-height: 1.55; color: var(--ink-2); }
.login-points { margin: 0; padding-left: 18px; font-size: 13.5px; line-height: 1.6; color: var(--ink-2); }
.btn-google { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 12px 16px;
  border: 1px solid var(--line-2); border-radius: 12px; background: #fff; color: #1f1f1f; font-weight: 700; font-size: 15px; }
.btn-google:hover { background: #f8fafc; }
.btn-google svg { width: 20px; height: 20px; }
.who-line { margin: 4px 0 0; font-size: 13px; color: var(--ink-2); display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }
.who-line small { color: var(--muted); font-size: 12px; }
.link-btn { background: none; border: 0; padding: 0; color: var(--accent); font-size: 12.5px; font-weight: 600; text-decoration: underline; }

'''


def apply():
    if document.getElementById("theme"):
        return
    style = document.createElement("style")
    style.id = "theme"
    style.textContent = CSS
    document.head.appendChild(style)
