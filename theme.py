"""화면 꾸미기 (CSS). 시작할 때 apply() 가 페이지에 붙인다."""
from js import document  # 브라우저 문서 (꾸미기 요소를 넣는 데 쓴다)

CSS = '''
:root {  /* 페이지 전체에서 쓰는 색·크기 변수 시작 */
  --bg: #eef1f5;  /* 변수 --bg: 바탕 회색 */
  --paper: #ffffff;  /* 변수 --paper: 카드·패널 흰색 */
  --ink: #0f172a;  /* 변수 --ink: 기본 글자색(진한 남색) */
  --ink-2: #334155;  /* 변수 --ink-2: 조금 연한 글자색 */
  --muted: #64748b;  /* 변수 --muted: 흐린 설명 글자색 */
  --line: #e2e8f0;  /* 변수 --line: 옅은 선 색 */
  --line-2: #cbd5e1;  /* 변수 --line-2: 조금 진한 선 색 */
  --accent: #2563eb;  /* 변수 --accent: 강조 파랑 */
  --danger: #dc2626;  /* 변수 --danger: 위험 빨강 */
  --danger-ink: #b91c1c;  /* 변수 --danger-ink: 진한 빨강 (마우스 올릴 때) */
  --ok: #16a34a;  /* 변수 --ok: 완료 초록 */
  --warn: #d97706;  /* 변수 --warn: 주의 주황 */
  --radius: 14px;  /* 변수 --radius: 모서리 둥글기 기본값 */
  --shadow: 0 1px 2px rgb(15 23 42 / 0.06), 0 8px 24px rgb(15 23 42 / 0.08);  /* 변수 --shadow: 카드 그림자 기본값 */
  --topbar: 60px;  /* 변수 --topbar: 위 막대 높이 */
  font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;  /* 글꼴 종류 */
  color: var(--ink);  /* 글자색 */
  -webkit-font-smoothing: antialiased;  /* 글자 부드럽게 */
}  /* 규칙 끝 */

* { box-sizing: border-box; }  /* * 꾸미기: 크기 계산 방식 */
html, body { height: 100%; }  /* html, body 꾸미기: 높이 */
body { margin: 0; background: var(--bg); overflow: hidden; }  /* body 꾸미기: 바깥 여백, 배경, 넘침 처리 */
button, input, textarea { font: inherit; color: inherit; }  /* button, input, textarea 꾸미기: 글꼴, 글자색 */
button { cursor: pointer; }  /* button 꾸미기: 마우스 모양 */
svg { display: block; }  /* svg 꾸미기: 배치 방식 */
[hidden] { display: none !important; }  /* [hidden] 꾸미기: 배치 방식 */

/* ── 상단 바 ─────────────────────────── */
.topbar {  /* .topbar 꾸미기 시작 */
  height: var(--topbar);  /* 높이 */
  display: flex; align-items: center; justify-content: space-between;  /* 배치 방식, 세로 정렬, 가로 정렬 */
  padding: 0 16px;  /* 안쪽 여백 */
  background: var(--paper);  /* 배경 */
  border-bottom: 1px solid var(--line);  /* 아래 테두리 */
  position: relative; z-index: 5;  /* 위치 방식, 겹침 순서 */
}  /* 규칙 끝 */
.brand { display: flex; align-items: center; gap: 10px; text-decoration: none; color: inherit; }  /* .brand 꾸미기: 배치 방식, 세로 정렬, 사이 간격, 밑줄, 글자색 */
.brand-mark { width: 34px; height: 34px; border-radius: 10px; background: #fee2e2; display: grid; place-items: center; }  /* .brand-mark 꾸미기: 너비, 높이, 모서리 둥글기, 배경, 배치 방식, 가운데 정렬 */
.brand-mark svg { width: 22px; height: 22px; }  /* .brand-mark svg 꾸미기: 너비, 높이 */
.brand-mark path { fill: var(--danger); }  /* .brand-mark path 꾸미기: 도형 채우기 색 */
.brand-mark circle { fill: #fff; }  /* .brand-mark circle 꾸미기: 도형 채우기 색 */
.brand-text { display: flex; flex-direction: column; line-height: 1.15; }  /* .brand-text 꾸미기: 배치 방식, 쌓는 방향, 줄 높이 */
.brand-text strong { font-size: 17px; letter-spacing: -0.02em; }  /* .brand-text strong 꾸미기: 글자 크기, 글자 사이 간격 */
.brand-text small { font-size: 12px; color: var(--muted); }  /* .brand-text small 꾸미기: 글자 크기, 글자색 */

.btn {  /* .btn 꾸미기 시작 */
  display: inline-flex; align-items: center; gap: 6px;  /* 배치 방식, 세로 정렬, 사이 간격 */
  height: 40px; padding: 0 16px; border-radius: 999px; border: 0;  /* 높이, 안쪽 여백, 모서리 둥글기, 테두리 */
  font-weight: 600; font-size: 14px; letter-spacing: -0.01em;  /* 글자 굵기, 글자 크기, 글자 사이 간격 */
  transition: background .15s, transform .1s;  /* 부드러운 변화 */
}  /* 규칙 끝 */
.btn:active { transform: scale(.97); }  /* .btn:active 꾸미기: 모양 변형 */
.btn svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; }  /* .btn svg 꾸미기: 너비, 높이, 도형 채우기 색, 선 색, 선 두께, 선 끝 모양 */
.btn-danger { background: var(--danger); color: #fff; }  /* .btn-danger 꾸미기: 배경, 글자색 */
.btn-danger:hover { background: var(--danger-ink); }  /* .btn-danger:hover 꾸미기: 배경 */
.btn-danger[aria-pressed="true"] { background: var(--ink); }  /* .btn-danger[aria-pressed="true"] 꾸미기: 배경 */
.btn-quiet { background: #f1f5f9; color: var(--ink-2); }  /* .btn-quiet 꾸미기: 배경, 글자색 */
.btn-quiet:hover { background: #e2e8f0; }  /* .btn-quiet:hover 꾸미기: 배경 */
.btn-ghost-light { background: rgb(255 255 255 / .16); color: #fff; height: 32px; padding: 0 12px; }  /* .btn-ghost-light 꾸미기: 배경, 글자색, 높이, 안쪽 여백 */
.btn-ghost-light:hover { background: rgb(255 255 255 / .26); }  /* .btn-ghost-light:hover 꾸미기: 배경 */

/* ── 레이아웃 ───────────────────────── */
.layout {  /* .layout 꾸미기 시작 */
  height: calc(100dvh - var(--topbar));  /* 높이 */
  display: grid;  /* 배치 방식 */
  grid-template-columns: minmax(0, 1fr) 380px;  /* 칸 나누기 */
}  /* 규칙 끝 */
.stage { position: relative; overflow: hidden; background:  /* .stage 꾸미기: 위치 방식, 넘침 처리, 배경(다음 줄: 점무늬 바탕) */
  radial-gradient(circle at 1px 1px, #d5dbe4 1px, transparent 0) 0 0 / 22px 22px, #f6f8fb; }  /* 22px 마다 작은 점이 찍힌 바탕 (규칙 끝) */
.panel {  /* .panel 꾸미기 시작 */
  background: var(--paper); border-left: 1px solid var(--line);  /* 배경, 왼쪽 테두리 */
  overflow-y: auto; display: flex; flex-direction: column;  /* 세로 넘침 처리, 배치 방식, 쌓는 방향 */
}  /* 규칙 끝 */

/* ── 지도 ───────────────────────────── */
.map { width: 100%; height: 100%; touch-action: none; user-select: none; cursor: grab; }  /* .map 꾸미기: 너비, 높이, 손가락 동작 처리, 글자 선택 여부, 마우스 모양 */
.map.is-panning { cursor: grabbing; }  /* .map.is-panning 꾸미기: 마우스 모양 */
.map.is-locked { cursor: default; }  /* .map.is-locked 꾸미기: 마우스 모양 */
.map.is-locked ~ .map-tools { display: none; }  /* .map.is-locked ~ .map-tools 꾸미기: 배치 방식 */
.map.is-loading .layer-plan { opacity: 0; }  /* .map.is-loading .layer-plan 꾸미기: 투명도 */
.layer-plan { transition: opacity .2s; }  /* .layer-plan 꾸미기: 부드러운 변화 */
.map .layer-plan > path.l { transition: opacity .2s; }  /* .map .layer-plan > path.l 꾸미기: 부드러운 변화 */
body.reporting .map { cursor: crosshair; }  /* body.reporting .map 꾸미기: 마우스 모양 */

.bld { cursor: pointer; }  /* .bld 꾸미기: 마우스 모양 */
.bld path { fill: var(--c); fill-opacity: .26; stroke: var(--c); stroke-width: 1.4; vector-effect: non-scaling-stroke; transition: fill-opacity .15s; }  /* .bld path 꾸미기: 도형 채우기 색, 채우기 투명도, 선 색, 선 두께, 확대해도 선 두께 유지, 부드러운 변화 */
.bld:hover path, .bld.is-hot path { fill-opacity: .5; }  /* .bld:hover path, .bld.is-hot path 꾸미기: 채우기 투명도 */
.bld-label { pointer-events: none; }  /* .bld-label 꾸미기: 마우스 반응 여부 */
.bld-label rect { fill: #fff; stroke: var(--c); vector-effect: non-scaling-stroke; }  /* .bld-label rect 꾸미기: 도형 채우기 색, 선 색, 확대해도 선 두께 유지 */
.bld-label text { fill: var(--ink); font-weight: 700; text-anchor: middle; dominant-baseline: central; letter-spacing: -0.02em; }  /* .bld-label text 꾸미기: 도형 채우기 색, 글자 굵기, 글자 기준점, 글자 세로 기준, 글자 사이 간격 */
.bld-label .count { fill: #fff; }  /* .bld-label .count 꾸미기: 도형 채우기 색 */
.bld-label .count-bg { fill: var(--danger); stroke: #fff; }  /* .bld-label .count-bg 꾸미기: 도형 채우기 색, 선 색 */
body.reporting .bld { pointer-events: none; }  /* body.reporting .bld 꾸미기: 마우스 반응 여부 */

.pin { cursor: pointer; }  /* .pin 꾸미기: 마우스 모양 */
.pin .drop { stroke: #fff; stroke-width: 2; }  /* .pin .drop 꾸미기: 선 색, 선 두께 */
.pin .core { fill: #fff; }  /* .pin .core 꾸미기: 도형 채우기 색 */
.pin.done .drop { fill: #94a3b8 !important; }  /* .pin.done .drop 꾸미기: 도형 채우기 색 */
.pin.is-selected .halo { opacity: 1; }  /* .pin.is-selected .halo 꾸미기: 투명도 */
.pin .halo { opacity: 0; fill: none; stroke: currentColor; stroke-width: 3; }  /* .pin .halo 꾸미기: 투명도, 도형 채우기 색, 선 색, 선 두께 */
.pin:hover .drop { filter: brightness(1.08); }  /* .pin:hover .drop 꾸미기: 그림 효과 */
.draft-pin .drop { fill: var(--ink); }  /* .draft-pin .drop 꾸미기: 도형 채우기 색 */
.draft-pin .ring { fill: none; stroke: var(--ink); stroke-width: 2; animation: ring 1.4s ease-out infinite; transform-origin: 0 0; }  /* .draft-pin .ring 꾸미기: 도형 채우기 색, 선 색, 선 두께, 움직임 효과, 변형 기준점 */
@keyframes ring { from { transform: scale(.4); opacity: .9; } to { transform: scale(1.8); opacity: 0; } }  /* 움직임 효과 'ring': 작고 진한 원에서 크고 투명한 원으로 퍼진다 */

/* ── 지도 위 UI ─────────────────────── */
.stage-top { position: absolute; top: 14px; left: 14px; right: 80px; display: flex; gap: 8px; pointer-events: none; }  /* .stage-top 꾸미기: 위치 방식, 위 위치, 왼쪽 위치, 오른쪽 위치, 배치 방식, 사이 간격, 마우스 반응 여부 */
.crumbs {  /* .crumbs 꾸미기 시작 */
  pointer-events: auto;  /* 마우스 반응 여부 */
  display: inline-flex; align-items: center; gap: 2px; flex-wrap: wrap;  /* 배치 방식, 세로 정렬, 사이 간격, 줄바꿈 */
  background: var(--paper); border-radius: 999px; padding: 4px; box-shadow: var(--shadow);  /* 배경, 모서리 둥글기, 안쪽 여백, 그림자 */
  font-size: 14px;  /* 글자 크기 */
}  /* 규칙 끝 */
.crumbs a, .crumbs span { padding: 6px 12px; border-radius: 999px; text-decoration: none; color: var(--muted); font-weight: 600; }  /* .crumbs a, .crumbs span 꾸미기: 안쪽 여백, 모서리 둥글기, 밑줄, 글자색, 글자 굵기 */
.crumbs a:hover { background: #f1f5f9; color: var(--ink); }  /* .crumbs a:hover 꾸미기: 배경, 글자색 */
.crumbs .sep { padding: 0; color: var(--line-2); }  /* .crumbs .sep 꾸미기: 안쪽 여백, 글자색 */
.crumbs .here { color: var(--ink); }  /* .crumbs .here 꾸미기: 글자색 */

.floorbar {  /* .floorbar 꾸미기 시작 */
  position: absolute; right: 14px; top: 50%; transform: translateY(-50%);  /* 위치 방식, 오른쪽 위치, 위 위치, 모양 변형 */
  display: flex; flex-direction: column-reverse; gap: 4px;  /* 배치 방식, 쌓는 방향, 사이 간격 */
  background: var(--paper); padding: 6px; border-radius: 16px; box-shadow: var(--shadow);  /* 배경, 안쪽 여백, 모서리 둥글기, 그림자 */
}  /* 규칙 끝 */
.floorbar:empty { display: none; }  /* .floorbar:empty 꾸미기: 배치 방식 */
.floorbar button {  /* .floorbar button 꾸미기 시작 */
  min-width: 46px; height: 40px; padding: 0 8px; border-radius: 11px; border: 0; background: transparent;  /* 최소 너비, 높이, 안쪽 여백, 모서리 둥글기, 테두리, 배경 */
  font-weight: 700; font-size: 13px; color: var(--ink-2); position: relative;  /* 글자 굵기, 글자 크기, 글자색, 위치 방식 */
}  /* 규칙 끝 */
.floorbar button:hover { background: #f1f5f9; }  /* .floorbar button:hover 꾸미기: 배경 */
.floorbar button[aria-selected="true"] { background: var(--ink); color: #fff; }  /* .floorbar button[aria-selected="true"] 꾸미기: 배경, 글자색 */
.floorbar .dot {  /* .floorbar .dot 꾸미기 시작 */
  position: absolute; top: 3px; right: 3px; min-width: 16px; height: 16px; padding: 0 4px;  /* 위치 방식, 위 위치, 오른쪽 위치, 최소 너비, 높이, 안쪽 여백 */
  border-radius: 999px; background: var(--danger); color: #fff; font-size: 10px; line-height: 16px;  /* 모서리 둥글기, 배경, 글자색, 글자 크기, 줄 높이 */
}  /* 규칙 끝 */

.map-tools {  /* .map-tools 꾸미기 시작 */
  position: absolute; left: 14px; bottom: 14px;  /* 위치 방식, 왼쪽 위치, 아래 위치 */
  display: flex; gap: 2px; background: var(--paper); padding: 4px; border-radius: 14px; box-shadow: var(--shadow);  /* 배치 방식, 사이 간격, 배경, 안쪽 여백, 모서리 둥글기, 그림자 */
}  /* 규칙 끝 */
.tool { width: 38px; height: 38px; border: 0; border-radius: 10px; background: transparent; display: grid; place-items: center; color: var(--ink-2); }  /* .tool 꾸미기: 너비, 높이, 테두리, 모서리 둥글기, 배경, 배치 방식, 가운데 정렬, 글자색 */
.tool:hover { background: #f1f5f9; }  /* .tool:hover 꾸미기: 배경 */
.tool svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }  /* .tool svg 꾸미기: 너비, 높이, 도형 채우기 색, 선 색, 선 두께, 선 끝 모양, 선 꺾임 모양 */
.tool[aria-pressed="false"] { color: var(--line-2); }  /* .tool[aria-pressed="false"] 꾸미기: 글자색 */

.mode-banner {  /* .mode-banner 꾸미기 시작 */
  position: absolute; left: 50%; bottom: 18px; transform: translateX(-50%);  /* 위치 방식, 왼쪽 위치, 아래 위치, 모양 변형 */
  display: flex; align-items: center; gap: 12px;  /* 배치 방식, 세로 정렬, 사이 간격 */
  background: var(--ink); color: #fff; padding: 8px 8px 8px 16px; border-radius: 999px;  /* 배경, 글자색, 안쪽 여백, 모서리 둥글기 */
  box-shadow: 0 10px 30px rgb(15 23 42 / .3); font-size: 14px; font-weight: 600; white-space: nowrap;  /* 그림자, 글자 크기, 글자 굵기, 줄바꿈 방식 */
  max-width: calc(100% - 28px);  /* 최대 너비 */
}  /* 규칙 끝 */
.mode-banner #modeText { overflow: hidden; text-overflow: ellipsis; }  /* .mode-banner #modeText 꾸미기: 넘침 처리, 넘치는 글자 처리 */
.pulse { width: 10px; height: 10px; border-radius: 50%; background: #f87171; box-shadow: 0 0 0 0 rgb(248 113 113 / .7); animation: pulse 1.4s infinite; flex: none; }  /* .pulse 꾸미기: 너비, 높이, 모서리 둥글기, 배경, 그림자, 움직임 효과, 늘어나는 비율 */
@keyframes pulse { to { box-shadow: 0 0 0 10px rgb(248 113 113 / 0); } }  /* 움직임 효과 'pulse' 정의: to { box-shadow */

.loading { position: absolute; inset: 0; display: grid; place-items: center; color: var(--muted); font-weight: 600; pointer-events: none; }  /* .loading 꾸미기: 위치 방식, 네 방향 위치, 배치 방식, 가운데 정렬, 글자색, 글자 굵기, 마우스 반응 여부 */

/* ── 패널 ───────────────────────────── */
.ctx { padding: 20px 20px 8px; }  /* .ctx 꾸미기: 안쪽 여백 */
.ctx h1 { font-size: 22px; margin: 0; letter-spacing: -0.03em; }  /* .ctx h1 꾸미기: 글자 크기, 바깥 여백, 글자 사이 간격 */
.ctx .sub { color: var(--muted); font-size: 14px; margin: 4px 0 0; }  /* .ctx .sub 꾸미기: 글자색, 글자 크기, 바깥 여백 */
.ctx .meta { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }  /* .ctx .meta 꾸미기: 배치 방식, 사이 간격, 줄바꿈, 위 바깥 여백 */
.tag { font-size: 12px; font-weight: 600; padding: 4px 9px; border-radius: 999px; background: #f1f5f9; color: var(--ink-2); }  /* .tag 꾸미기: 글자 크기, 글자 굵기, 안쪽 여백, 모서리 둥글기, 배경, 글자색 */
.tag.color { color: #fff; background: var(--c); }  /* .tag.color 꾸미기: 글자색, 배경 */
.hint { margin: 12px 0 0; font-size: 13px; color: var(--muted); line-height: 1.5; }  /* .hint 꾸미기: 바깥 여백, 글자 크기, 글자색, 줄 높이 */

.bld-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 16px; }  /* .bld-grid 꾸미기: 배치 방식, 칸 나누기, 사이 간격, 위 바깥 여백 */
.bld-card {  /* .bld-card 꾸미기 시작 */
  text-align: left; border: 1px solid var(--line); background: var(--paper); border-radius: 12px; padding: 10px 12px;  /* 글자 정렬, 테두리, 배경, 모서리 둥글기, 안쪽 여백 */
  display: flex; flex-direction: column; gap: 2px; position: relative; transition: border-color .15s, box-shadow .15s;  /* 배치 방식, 쌓는 방향, 사이 간격, 위치 방식, 부드러운 변화 */
}  /* 규칙 끝 */
.bld-card::before { content: ""; position: absolute; left: 0; top: 10px; bottom: 10px; width: 3px; border-radius: 0 3px 3px 0; background: var(--c); }  /* .bld-card::before 꾸미기: 내용, 위치 방식, 왼쪽 위치, 위 위치, 아래 위치, 너비, 모서리 둥글기, 배경 */
.bld-card:hover { border-color: var(--c); box-shadow: var(--shadow); }  /* .bld-card:hover 꾸미기: 테두리 색, 그림자 */
.bld-card strong { font-size: 15px; letter-spacing: -0.02em; }  /* .bld-card strong 꾸미기: 글자 크기, 글자 사이 간격 */
.bld-card small { font-size: 12px; color: var(--muted); }  /* .bld-card small 꾸미기: 글자 크기, 글자색 */
.bld-card .n { position: absolute; top: 8px; right: 8px; font-size: 11px; font-weight: 700; color: #fff; background: var(--danger); border-radius: 999px; padding: 1px 7px; }  /* .bld-card .n 꾸미기: 위치 방식, 위 위치, 오른쪽 위치, 글자 크기, 글자 굵기, 글자색, 배경, 모서리 둥글기, 안쪽 여백 */

.floor-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }  /* .floor-list 꾸미기: 배치 방식, 줄바꿈, 사이 간격, 위 바깥 여백 */
.floor-list button { border: 1px solid var(--line); background: var(--paper); border-radius: 10px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--ink-2); }  /* .floor-list button 꾸미기: 테두리, 배경, 모서리 둥글기, 안쪽 여백, 글자 크기, 글자 굵기, 글자색 */
.floor-list button[aria-selected="true"] { background: var(--ink); border-color: var(--ink); color: #fff; }  /* .floor-list button[aria-selected="true"] 꾸미기: 배경, 테두리 색, 글자색 */

.reports { border-top: 1px solid var(--line); margin-top: 12px; padding: 16px 20px 20px; display: flex; flex-direction: column; flex: 1; }  /* .reports 꾸미기: 위 테두리, 위 바깥 여백, 안쪽 여백, 배치 방식, 쌓는 방향, 늘어나는 비율 */
.reports-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }  /* .reports-head 꾸미기: 배치 방식, 세로 정렬, 가로 정렬, 사이 간격 */
.reports-head h2 { font-size: 16px; margin: 0; }  /* .reports-head h2 꾸미기: 글자 크기, 바깥 여백 */
.stats { display: flex; gap: 10px; font-size: 12px; color: var(--muted); }  /* .stats 꾸미기: 배치 방식, 사이 간격, 글자 크기, 글자색 */
.stats b { color: var(--ink); font-size: 14px; margin-left: 2px; }  /* .stats b 꾸미기: 글자색, 글자 크기, 왼쪽 바깥 여백 */
.stats .urgent b { color: var(--danger); }  /* .stats .urgent b 꾸미기: 글자색 */
.filters { display: flex; justify-content: space-between; gap: 8px; margin: 12px 0; flex-wrap: wrap; }  /* .filters 꾸미기: 배치 방식, 가로 정렬, 사이 간격, 바깥 여백, 줄바꿈 */
.seg { display: inline-flex; background: #f1f5f9; padding: 3px; border-radius: 10px; }  /* .seg 꾸미기: 배치 방식, 배경, 안쪽 여백, 모서리 둥글기 */
.seg button { border: 0; background: transparent; padding: 5px 10px; border-radius: 8px; font-size: 12.5px; font-weight: 600; color: var(--muted); }  /* .seg button 꾸미기: 테두리, 배경, 안쪽 여백, 모서리 둥글기, 글자 크기, 글자 굵기, 글자색 */
.seg button[aria-pressed="true"] { background: var(--paper); color: var(--ink); box-shadow: 0 1px 2px rgb(15 23 42 / .1); }  /* .seg button[aria-pressed="true"] 꾸미기: 배경, 글자색, 그림자 */

.report-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }  /* .report-list 꾸미기: 목록 점 모양, 바깥 여백, 안쪽 여백, 배치 방식, 쌓는 방향, 사이 간격 */
.report-item {  /* .report-item 꾸미기 시작 */
  display: grid; grid-template-columns: 10px 1fr auto; gap: 4px 10px; align-items: start;  /* 배치 방식, 칸 나누기, 사이 간격, 세로 정렬 */
  padding: 12px; border-radius: 12px; border: 1px solid var(--line); background: var(--paper); cursor: pointer; text-align: left; width: 100%;  /* 안쪽 여백, 모서리 둥글기, 테두리, 배경, 마우스 모양, 글자 정렬, 너비 */
}  /* 규칙 끝 */
.report-item:hover { border-color: var(--line-2); box-shadow: var(--shadow); }  /* .report-item:hover 꾸미기: 테두리 색, 그림자 */
.report-item.is-selected { border-color: var(--ink); }  /* .report-item.is-selected 꾸미기: 테두리 색 */
.like-count { font-size: 12px; font-weight: 600; color: var(--ink-2, #555); margin-left: 4px; white-space: nowrap; }  /* .like-count 꾸미기: 글자 크기, 글자 굵기, 글자색, 왼쪽 바깥 여백, 줄바꿈 방식 */
.like-btn { width: 100%; margin-top: 12px; justify-content: center; gap: 6px; border: 1.5px solid var(--line-2, #ccc); background: var(--bg, #fff); }  /* .like-btn 꾸미기: 너비, 위 바깥 여백, 가로 정렬, 사이 간격, 테두리, 배경 */
.like-btn.is-on { border-color: #e8833a; background: #fff3e8; color: #b4541a; }  /* .like-btn.is-on 꾸미기: 테두리 색, 배경, 글자색 */
.like-btn b { font-variant-numeric: tabular-nums; }  /* .like-btn b 꾸미기: 숫자 모양 */
.like-line { margin-top: 10px; font-size: 14px; }  /* .like-line 꾸미기: 위 바깥 여백, 글자 크기 */
.report-item .sev-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 5px; }  /* .report-item .sev-dot 꾸미기: 너비, 높이, 모서리 둥글기, 위 바깥 여백 */
.report-item .t { font-weight: 600; font-size: 14.5px; letter-spacing: -0.01em; line-height: 1.35; }  /* .report-item .t 꾸미기: 글자 굵기, 글자 크기, 글자 사이 간격, 줄 높이 */
.report-item .w { grid-column: 2 / 4; font-size: 12.5px; color: var(--muted); }  /* .report-item .w 꾸미기: 차지할 칸, 글자 크기, 글자색 */
.status { font-size: 11.5px; font-weight: 700; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }  /* .status 꾸미기: 글자 크기, 글자 굵기, 안쪽 여백, 모서리 둥글기, 줄바꿈 방식 */
.status.new { background: #fee2e2; color: var(--danger-ink); }  /* .status.new 꾸미기: 배경, 글자색 */
.status.doing { background: #fef3c7; color: #92400e; }  /* .status.doing 꾸미기: 배경, 글자색 */
.status.done { background: #dcfce7; color: #166534; }  /* .status.done 꾸미기: 배경, 글자색 */
.empty { text-align: center; color: var(--muted); font-size: 14px; padding: 28px 12px; border: 1px dashed var(--line-2); border-radius: 12px; line-height: 1.6; }  /* .empty 꾸미기: 글자 정렬, 글자색, 글자 크기, 안쪽 여백, 테두리, 모서리 둥글기, 줄 높이 */
.empty button { margin-top: 10px; }  /* .empty button 꾸미기: 위 바깥 여백 */
.panel-foot { display: flex; gap: 16px; justify-content: center; margin-top: auto; padding-top: 20px; }  /* .panel-foot 꾸미기: 배치 방식, 사이 간격, 가로 정렬, 위 바깥 여백, 위 안쪽 여백 */
.link { background: none; border: 0; padding: 0; color: var(--muted); font-size: 12.5px; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }  /* .link 꾸미기: 배경, 테두리, 안쪽 여백, 글자색, 글자 크기, 밑줄, 밑줄 간격, 마우스 모양 */
.link:hover { color: var(--ink); }  /* .link:hover 꾸미기: 글자색 */

/* ── 시트(다이얼로그) ────────────────── */
.sheet {  /* .sheet 꾸미기 시작 */
  border: 0; padding: 0; border-radius: 20px; width: min(520px, calc(100vw - 24px)); max-height: calc(100dvh - 32px);  /* 테두리, 안쪽 여백, 모서리 둥글기, 너비, 최대 높이 */
  box-shadow: 0 30px 80px rgb(15 23 42 / .35); color: var(--ink); background: var(--paper);  /* 그림자, 글자색, 배경 */
}  /* 규칙 끝 */
.sheet::backdrop { background: rgb(15 23 42 / .45); backdrop-filter: blur(2px); }  /* .sheet::backdrop 꾸미기: 배경, 뒤쪽 흐림 */
.sheet form, #detailBody { display: flex; flex-direction: column; max-height: calc(100dvh - 32px); }  /* .sheet form, #detailBody 꾸미기: 배치 방식, 쌓는 방향, 최대 높이 */
.sheet-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding: 20px 20px 8px; }  /* .sheet-head 꾸미기: 배치 방식, 가로 정렬, 세로 정렬, 사이 간격, 안쪽 여백 */
.sheet-head h2 { margin: 2px 0 0; font-size: 20px; letter-spacing: -0.03em; }  /* .sheet-head h2 꾸미기: 바깥 여백, 글자 크기, 글자 사이 간격 */
.eyebrow { margin: 0; font-size: 13px; font-weight: 600; color: var(--danger); }  /* .eyebrow 꾸미기: 바깥 여백, 글자 크기, 글자 굵기, 글자색 */
.icon-btn { width: 36px; height: 36px; border-radius: 50%; border: 0; background: #f1f5f9; display: grid; place-items: center; flex: none; }  /* .icon-btn 꾸미기: 너비, 높이, 모서리 둥글기, 테두리, 배경, 배치 방식, 가운데 정렬, 늘어나는 비율 */
.icon-btn svg { width: 18px; height: 18px; stroke: var(--ink-2); stroke-width: 2.2; stroke-linecap: round; fill: none; }  /* .icon-btn svg 꾸미기: 너비, 높이, 선 색, 선 두께, 선 끝 모양, 도형 채우기 색 */
.sheet-body { padding: 8px 20px 4px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }  /* .sheet-body 꾸미기: 안쪽 여백, 세로 넘침 처리, 배치 방식, 쌓는 방향, 사이 간격 */
.sheet-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 16px 20px 20px; border-top: 1px solid var(--line); margin-top: 12px; }  /* .sheet-foot 꾸미기: 배치 방식, 가로 정렬, 사이 간격, 안쪽 여백, 위 테두리, 위 바깥 여백 */
fieldset { border: 0; margin: 0; padding: 0; }  /* fieldset 꾸미기: 테두리, 바깥 여백, 안쪽 여백 */
legend, .field > span { font-size: 13px; font-weight: 700; color: var(--ink-2); margin-bottom: 8px; display: block; padding: 0; }  /* legend, .field > span 꾸미기: 글자 크기, 글자 굵기, 글자색, 아래 바깥 여백, 배치 방식, 안쪽 여백 */
.field { display: flex; flex-direction: column; }  /* .field 꾸미기: 배치 방식, 쌓는 방향 */
.field em { color: var(--danger); font-style: normal; }  /* .field em 꾸미기: 글자색, 글자 기울임 */
.field input, .field textarea {  /* .field input, .field textarea 꾸미기 시작 */
  border: 1px solid var(--line-2); border-radius: 10px; padding: 10px 12px; font-size: 15px; background: #fff; resize: vertical;  /* 테두리, 모서리 둥글기, 안쪽 여백, 글자 크기, 배경, 크기 조절 */
}  /* 규칙 끝 */
.field input:focus, .field textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; border-color: transparent; }  /* .field input:focus, .field textarea:focus 꾸미기: 강조 테두리, 강조 테두리 간격, 테두리 색 */
.chips, .sev { display: flex; flex-wrap: wrap; gap: 6px; }  /* .chips, .sev 꾸미기: 배치 방식, 줄바꿈, 사이 간격 */
.chips label, .sev label { position: relative; }  /* .chips label, .sev label 꾸미기: 위치 방식 */
.chips input, .sev input { position: absolute; opacity: 0; pointer-events: none; }  /* .chips input, .sev input 꾸미기: 위치 방식, 투명도, 마우스 반응 여부 */
.chips span, .sev span {  /* .chips span, .sev span 꾸미기 시작 */
  display: inline-flex; align-items: center; gap: 5px; padding: 7px 12px; border-radius: 999px;  /* 배치 방식, 세로 정렬, 사이 간격, 안쪽 여백, 모서리 둥글기 */
  border: 1px solid var(--line-2); font-size: 13.5px; font-weight: 600; color: var(--ink-2); cursor: pointer; user-select: none;  /* 테두리, 글자 크기, 글자 굵기, 글자색, 마우스 모양, 글자 선택 여부 */
}  /* 규칙 끝 */
.chips input:checked + span { background: var(--ink); border-color: var(--ink); color: #fff; }  /* .chips input:checked + span 꾸미기: 배경, 테두리 색, 글자색 */
.sev span::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--c); }  /* .sev span::before 꾸미기: 내용, 너비, 높이, 모서리 둥글기, 배경 */
.sev input:checked + span { background: var(--c); border-color: var(--c); color: #fff; }  /* .sev input:checked + span 꾸미기: 배경, 테두리 색, 글자색 */
.sev input:checked + span::before { background: #fff; }  /* .sev input:checked + span::before 꾸미기: 배경 */
.chips input:focus-visible + span, .sev input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }  /* .chips input:focus-visible + span, .sev input:focus-visible + span 꾸미기: 강조 테두리, 강조 테두리 간격 */
.photo-drop {  /* .photo-drop 꾸미기 시작 */
  display: grid; place-items: center; min-height: 88px; border: 1.5px dashed var(--line-2); border-radius: 12px;  /* 배치 방식, 가운데 정렬, 최소 높이, 테두리, 모서리 둥글기 */
  color: var(--muted); font-size: 14px; font-weight: 600; cursor: pointer; overflow: hidden; position: relative;  /* 글자색, 글자 크기, 글자 굵기, 마우스 모양, 넘침 처리, 위치 방식 */
}  /* 규칙 끝 */
.photo-drop:hover { border-color: var(--ink-2); color: var(--ink); }  /* .photo-drop:hover 꾸미기: 테두리 색, 글자색 */
.photo-drop img { width: 100%; max-height: 220px; object-fit: cover; }  /* .photo-drop img 꾸미기: 너비, 최대 높이, 그림 맞추기 */
.photo-drop img:not([hidden]) + span { position: absolute; bottom: 8px; right: 8px; background: rgb(15 23 42 / .7); color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 12px; }  /* .photo-drop img:not([hidden]) + span 꾸미기: 위치 방식, 아래 위치, 오른쪽 위치, 배경, 글자색, 안쪽 여백, 모서리 둥글기, 글자 크기 */

.detail-photo { width: 100%; max-height: 300px; object-fit: cover; border-radius: 12px; }  /* .detail-photo 꾸미기: 너비, 최대 높이, 그림 맞추기, 모서리 둥글기 */
.detail-grid { display: grid; grid-template-columns: 84px 1fr; gap: 8px 12px; font-size: 14px; margin: 0; }  /* .detail-grid 꾸미기: 배치 방식, 칸 나누기, 사이 간격, 글자 크기, 바깥 여백 */
.detail-grid dt { color: var(--muted); }  /* .detail-grid dt 꾸미기: 글자색 */
.detail-grid dd { margin: 0; font-weight: 500; }  /* .detail-grid dd 꾸미기: 바깥 여백, 글자 굵기 */
.detail-desc { white-space: pre-wrap; line-height: 1.6; font-size: 15px; margin: 0; background: #f8fafc; padding: 12px 14px; border-radius: 12px; }  /* .detail-desc 꾸미기: 줄바꿈 방식, 줄 높이, 글자 크기, 바깥 여백, 배경, 안쪽 여백, 모서리 둥글기 */
.detail-actions { display: flex; gap: 8px; justify-content: space-between; align-items: center; flex-wrap: wrap; }  /* .detail-actions 꾸미기: 배치 방식, 사이 간격, 가로 정렬, 세로 정렬, 줄바꿈 */
.btn-text-danger { background: none; border: 0; color: var(--danger); font-weight: 600; font-size: 13.5px; padding: 8px 4px; }  /* .btn-text-danger 꾸미기: 배경, 테두리, 글자색, 글자 굵기, 글자 크기, 안쪽 여백 */

.toast {  /* .toast 꾸미기 시작 */
  position: fixed; left: 50%; top: calc(var(--topbar) + 14px); transform: translate(-50%, -20px);  /* 위치 방식, 왼쪽 위치, 위 위치, 모양 변형 */
  background: var(--ink); color: #fff; padding: 10px 18px; border-radius: 999px; font-size: 14px; font-weight: 600;  /* 배경, 글자색, 안쪽 여백, 모서리 둥글기, 글자 크기, 글자 굵기 */
  opacity: 0; pointer-events: none; transition: opacity .2s, transform .2s; z-index: 50;  /* 투명도, 마우스 반응 여부, 부드러운 변화, 겹침 순서 */
}  /* 규칙 끝 */
.toast.show { opacity: 1; transform: translate(-50%, 0); }  /* .toast.show 꾸미기: 투명도, 모양 변형 */

/* ── 모바일 ─────────────────────────── */
@media (max-width: 880px) {  /* 화면 너비가 880px 이하일 때 (휴대폰 등) 시작 */
  body { overflow: auto; }  /* body 꾸미기: 넘침 처리 */
  .layout { display: flex; flex-direction: column; height: auto; }  /* .layout 꾸미기: 배치 방식, 쌓는 방향, 높이 */
  .stage { height: 62dvh; min-height: 360px; flex: none; }  /* .stage 꾸미기: 높이, 최소 높이, 늘어나는 비율 */
  .panel { border-left: 0; border-top: 1px solid var(--line); overflow: visible; }  /* .panel 꾸미기: 왼쪽 테두리, 위 테두리, 넘침 처리 */
  .brand-text small { display: none; }  /* .brand-text small 꾸미기: 배치 방식 */
  .stage-top { right: 76px; }  /* .stage-top 꾸미기: 오른쪽 위치 */
  .floorbar { top: auto; bottom: 14px; transform: none; max-height: calc(100% - 80px); overflow-y: auto; }  /* .floorbar 꾸미기: 위 위치, 아래 위치, 모양 변형, 최대 높이, 세로 넘침 처리 */
  .floorbar button { min-width: 42px; height: 36px; }  /* .floorbar button 꾸미기: 최소 너비, 높이 */
  .mode-banner { bottom: 70px; }  /* .mode-banner 꾸미기: 아래 위치 */
  .sheet { width: 100vw; max-width: 100vw; margin: auto 0 0; border-radius: 20px 20px 0 0; max-height: 92dvh; }  /* .sheet 꾸미기: 너비, 최대 너비, 바깥 여백, 모서리 둥글기, 최대 높이 */
  .sheet form, #detailBody { max-height: 92dvh; }  /* .sheet form, #detailBody 꾸미기: 최대 높이 */
}  /* 규칙 끝 */
@media (max-width: 420px) {  /* 화면 너비가 420px 이하일 때 (휴대폰 등) 시작 */
  .topbar .btn { padding: 0 14px; }  /* .topbar .btn 꾸미기: 안쪽 여백 */
  .brand-mark { width: 30px; height: 30px; }  /* .brand-mark 꾸미기: 너비, 높이 */
}  /* 규칙 끝 */

/* ── v2 (PyScript) 추가 ───────────────── */
#loading {  /* #loading 꾸미기 시작 */
  position: fixed; inset: 0; z-index: 60; display: grid; place-items: center;  /* 위치 방식, 네 방향 위치, 겹침 순서, 배치 방식, 가운데 정렬 */
  background: rgb(246 248 251 / .92); color: var(--ink-2); font-weight: 600; font-size: 15px;  /* 배경, 글자색, 글자 굵기, 글자 크기 */
}  /* 규칙 끝 */
.report-item .sev-dot { width: auto; height: auto; margin: 0; font-size: 11px; line-height: 1.6; }  /* .report-item .sev-dot 꾸미기: 너비, 높이, 바깥 여백, 글자 크기, 줄 높이 */
.sev-tag { display: inline-flex; align-items: center; gap: 5px; font-weight: 700; color: var(--c); }  /* .sev-tag 꾸미기: 배치 방식, 세로 정렬, 사이 간격, 글자 굵기, 글자색 */
.sev-tag::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--c); }  /* .sev-tag::before 꾸미기: 내용, 너비, 높이, 모서리 둥글기, 배경 */
.demo-note { margin: 14px 0 0; padding: 10px 12px; border-radius: 10px; background: #fef9c3; color: #854d0e; font-size: 12.5px; line-height: 1.5; }  /* .demo-note 꾸미기: 바깥 여백, 안쪽 여백, 모서리 둥글기, 배경, 글자색, 글자 크기, 줄 높이 */
.status.rejected { background: #e2e8f0; color: #475569; }  /* .status.rejected 꾸미기: 배경, 글자색 */
.btn:disabled { opacity: .5; cursor: default; }  /* .btn:disabled 꾸미기: 투명도, 마우스 모양 */

/* ── 선생님 화면 ───────────────────────── */
body.teacher { overflow: auto; background: var(--bg); }  /* body.teacher 꾸미기: 넘침 처리, 배경 */
.t-mark { background: #dbeafe; font-size: 18px; }  /* .t-mark 꾸미기: 배경, 글자 크기 */
.who { font-size: 14px; font-weight: 600; color: var(--ink-2); margin-right: 8px; }  /* .who 꾸미기: 글자 크기, 글자 굵기, 글자색, 오른쪽 바깥 여백 */
.btn-primary { background: var(--accent); color: #fff; }  /* .btn-primary 꾸미기: 배경, 글자색 */
.btn-primary:hover { background: #1d4ed8; }  /* .btn-primary:hover 꾸미기: 배경 */
.t-login { min-height: calc(100dvh - var(--topbar)); display: grid; place-items: center; padding: 16px; }  /* .t-login 꾸미기: 최소 높이, 배치 방식, 가운데 정렬, 안쪽 여백 */
.t-login .t-card { width: min(400px, 100%); display: flex; flex-direction: column; gap: 14px; }  /* .t-login .t-card 꾸미기: 너비, 배치 방식, 쌓는 방향, 사이 간격 */
.t-login h1 { margin: 0; font-size: 22px; }  /* .t-login h1 꾸미기: 바깥 여백, 글자 크기 */
.t-login .sub { margin: -6px 0 0; color: var(--muted); font-size: 14px; }  /* .t-login .sub 꾸미기: 바깥 여백, 글자색, 글자 크기 */
.t-login .btn { justify-content: center; }  /* .t-login .btn 꾸미기: 가로 정렬 */
.t-error { margin: 0; color: var(--danger); font-size: 13.5px; font-weight: 600; }  /* .t-error 꾸미기: 바깥 여백, 글자색, 글자 크기, 글자 굵기 */
.t-card { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow); }  /* .t-card 꾸미기: 배경, 테두리, 모서리 둥글기, 안쪽 여백, 그림자 */
.t-card h3 { margin: 0 0 14px; font-size: 15px; letter-spacing: -0.02em; }  /* .t-card h3 꾸미기: 바깥 여백, 글자 크기, 글자 사이 간격 */
.t-card h3 small { color: var(--muted); font-weight: 500; font-size: 12.5px; margin-left: 6px; }  /* .t-card h3 small 꾸미기: 글자색, 글자 굵기, 글자 크기, 왼쪽 바깥 여백 */
.t-main { max-width: 1180px; margin: 0 auto; padding: 18px 16px 48px; display: flex; flex-direction: column; gap: 16px; }  /* .t-main 꾸미기: 최대 너비, 바깥 여백, 안쪽 여백, 배치 방식, 쌓는 방향, 사이 간격 */
.t-tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--line); overflow-x: auto; }  /* .t-tabs 꾸미기: 배치 방식, 사이 간격, 아래 테두리, 가로 넘침 처리 */
.t-tabs button { border: 0; background: none; padding: 10px 14px; font-weight: 600; font-size: 14.5px; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; white-space: nowrap; }  /* .t-tabs button 꾸미기: 테두리, 배경, 안쪽 여백, 글자 굵기, 글자 크기, 글자색, 아래 테두리, 아래 바깥 여백, 줄바꿈 방식 */
.t-tabs button[aria-selected="true"] { color: var(--ink); border-bottom-color: var(--accent); }  /* .t-tabs button[aria-selected="true"] 꾸미기: 글자색, 아래 테두리 색 */
.t-tab { display: flex; flex-direction: column; gap: 16px; }  /* .t-tab 꾸미기: 배치 방식, 쌓는 방향, 사이 간격 */
.t-tab[hidden] { display: none; }  /* .t-tab[hidden] 꾸미기: 배치 방식 */
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }  /* .tiles 꾸미기: 배치 방식, 칸 나누기, 사이 간격 */
.tile { background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }  /* .tile 꾸미기: 배경, 테두리, 모서리 둥글기, 안쪽 여백, 배치 방식, 쌓는 방향, 사이 간격 */
.tile span { color: var(--muted); font-size: 13px; font-weight: 600; }  /* .tile span 꾸미기: 글자색, 글자 크기, 글자 굵기 */
.tile b { font-size: 28px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }  /* .tile b 꾸미기: 글자 크기, 글자 사이 간격, 숫자 모양 */
.tile.urgent b { color: var(--danger); }  /* .tile.urgent b 꾸미기: 글자색 */
.t-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }  /* .t-grid2 꾸미기: 배치 방식, 칸 나누기, 사이 간격 */
.bars { display: flex; flex-direction: column; gap: 8px; }  /* .bars 꾸미기: 배치 방식, 쌓는 방향, 사이 간격 */
.bar-row { display: grid; grid-template-columns: 110px 1fr 32px; gap: 10px; align-items: center; font-size: 13.5px; }  /* .bar-row 꾸미기: 배치 방식, 칸 나누기, 사이 간격, 세로 정렬, 글자 크기 */
.bar-label { color: var(--ink-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }  /* .bar-label 꾸미기: 글자색, 넘침 처리, 넘치는 글자 처리, 줄바꿈 방식 */
.bar-track { height: 14px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }  /* .bar-track 꾸미기: 높이, 배경, 모서리 둥글기, 넘침 처리 */
.bar-fill { display: block; height: 100%; background: var(--accent); border-radius: 0 4px 4px 0; min-width: 4px; }  /* .bar-fill 꾸미기: 배치 방식, 높이, 배경, 모서리 둥글기, 최소 너비 */
.bar-row:hover .bar-fill { background: #1d4ed8; }  /* .bar-row:hover .bar-fill 꾸미기: 배경 */
.bar-val { text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; }  /* .bar-val 꾸미기: 글자 정렬, 글자 굵기, 숫자 모양 */
.cols-wrap { position: relative; padding-left: 36px; }  /* .cols-wrap 꾸미기: 위치 방식, 왼쪽 안쪽 여백 */
.cols-max { position: absolute; left: 0; top: -4px; font-size: 11.5px; color: var(--muted); }  /* .cols-max 꾸미기: 위치 방식, 왼쪽 위치, 위 위치, 글자 크기, 글자색 */
.cols { height: 140px; display: flex; align-items: flex-end; gap: 3px; border-bottom: 1px solid var(--line-2); background: linear-gradient(#eef2f7 1px, transparent 1px) 0 0 / 100% 50%; }  /* .cols 꾸미기: 높이, 배치 방식, 세로 정렬, 사이 간격, 아래 테두리, 배경 */
.col { flex: 1; height: 100%; display: flex; align-items: flex-end; cursor: default; }  /* .col 꾸미기: 늘어나는 비율, 높이, 배치 방식, 세로 정렬, 마우스 모양 */
.col span { display: block; width: 100%; background: var(--accent); border-radius: 3px 3px 0 0; min-height: 0; }  /* .col span 꾸미기: 배치 방식, 너비, 배경, 모서리 둥글기, 최소 높이 */
.col:hover span { background: #1d4ed8; }  /* .col:hover span 꾸미기: 배경 */
.cols-axis { display: flex; justify-content: space-between; padding-left: 36px; margin-top: 6px; font-size: 12px; color: var(--muted); }  /* .cols-axis 꾸미기: 배치 방식, 가로 정렬, 왼쪽 안쪽 여백, 위 바깥 여백, 글자 크기, 글자색 */
.hot-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }  /* .hot-list 꾸미기: 목록 점 모양, 바깥 여백, 안쪽 여백, 배치 방식, 쌓는 방향, 사이 간격 */
.t-empty { color: var(--muted); font-size: 14px; text-align: center; padding: 10px; list-style: none; }  /* .t-empty 꾸미기: 글자색, 글자 크기, 글자 정렬, 안쪽 여백, 목록 점 모양 */
.t-filters { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; }  /* .t-filters 꾸미기: 배치 방식, 줄바꿈, 사이 간격, 세로 정렬 */
.t-filters label { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; font-weight: 700; color: var(--ink-2); }  /* .t-filters label 꾸미기: 배치 방식, 쌓는 방향, 사이 간격, 글자 크기, 글자 굵기, 글자색 */
.t-filters label.grow { flex: 1; min-width: 180px; }  /* .t-filters label.grow 꾸미기: 늘어나는 비율, 최소 너비 */
.t-filters select, .t-filters input, .t-input, .t-maptools select {  /* .t-filters select, .t-filters input, .t-input, .t-maptools select 꾸미기 시작 */
  border: 1px solid var(--line-2); border-radius: 10px; padding: 8px 10px; font-size: 14px; background: #fff; font-weight: 500;  /* 테두리, 모서리 둥글기, 안쪽 여백, 글자 크기, 배경, 글자 굵기 */
}  /* 규칙 끝 */
.t-count { margin: 0; font-size: 13px; color: var(--muted); }  /* .t-count 꾸미기: 바깥 여백, 글자 크기, 글자색 */
.t-table-wrap { overflow-x: auto; background: var(--paper); border: 1px solid var(--line); border-radius: var(--radius); }  /* .t-table-wrap 꾸미기: 가로 넘침 처리, 배경, 테두리, 모서리 둥글기 */
.t-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }  /* .t-table 꾸미기: 너비, 표 테두리 합치기, 글자 크기 */
.t-table th { text-align: left; font-size: 12px; color: var(--muted); font-weight: 700; padding: 10px 12px; border-bottom: 1px solid var(--line); background: #f8fafc; white-space: nowrap; }  /* .t-table th 꾸미기: 글자 정렬, 글자 크기, 글자색, 글자 굵기, 안쪽 여백, 아래 테두리, 배경, 줄바꿈 방식 */
.t-table td { padding: 10px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }  /* .t-table td 꾸미기: 안쪽 여백, 아래 테두리, 줄바꿈 방식 */
.t-table td.title { white-space: normal; font-weight: 600; min-width: 180px; }  /* .t-table td.title 꾸미기: 줄바꿈 방식, 글자 굵기, 최소 너비 */
.t-table tbody tr { cursor: pointer; }  /* .t-table tbody tr 꾸미기: 마우스 모양 */
.t-table tbody tr:hover { background: #f8fafc; }  /* .t-table tbody tr:hover 꾸미기: 배경 */
.t-table tbody tr.is-selected { background: #eff6ff; }  /* .t-table tbody tr.is-selected 꾸미기: 배경 */
.t-maptools { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }  /* .t-maptools 꾸미기: 배치 방식, 줄바꿈, 사이 간격, 세로 정렬 */
.t-maptools .floor-list { margin: 0; }  /* .t-maptools .floor-list 꾸미기: 바깥 여백 */
.t-maptools .floor-list button { cursor: pointer; }  /* .t-maptools .floor-list button 꾸미기: 마우스 모양 */
.t-check { display: inline-flex; gap: 6px; align-items: center; font-size: 13.5px; font-weight: 600; color: var(--ink-2); }  /* .t-check 꾸미기: 배치 방식, 사이 간격, 세로 정렬, 글자 크기, 글자 굵기, 글자색 */
.t-mapbox { height: min(70dvh, 640px); background: radial-gradient(circle at 1px 1px, #d5dbe4 1px, transparent 0) 0 0 / 22px 22px, #f6f8fb; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }  /* .t-mapbox 꾸미기: 높이, 배경, 테두리, 모서리 둥글기, 넘침 처리 */
.sheet.wide { width: min(980px, calc(100vw - 24px)); }  /* .sheet.wide 꾸미기: 너비 */
.sheet.wide .sheet-body { overflow-y: auto; }  /* .sheet.wide .sheet-body 꾸미기: 세로 넘침 처리 */
.t-detail { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }  /* .t-detail 꾸미기: 배치 방식, 칸 나누기, 사이 간격 */
.mini-map { height: 260px; border: 1px solid var(--line); border-radius: 12px; background: #f8fafc; }  /* .mini-map 꾸미기: 높이, 테두리, 모서리 둥글기, 배경 */
.t-actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; border-top: 1px solid var(--line); padding-top: 16px; margin-top: 4px; }  /* .t-actions 꾸미기: 배치 방식, 칸 나누기, 사이 간격, 위 테두리, 위 안쪽 여백, 위 바깥 여백 */
.t-actions > div { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; }  /* .t-actions > div 꾸미기: 배치 방식, 쌓는 방향, 사이 간격, 세로 정렬 */
.t-actions h4 { margin: 4px 0 0; font-size: 13.5px; }  /* .t-actions h4 꾸미기: 바깥 여백, 글자 크기 */
.t-actions .t-input { width: 100%; }  /* .t-actions .t-input 꾸미기: 너비 */
.t-actions .seg { flex-wrap: wrap; }  /* .t-actions .seg 꾸미기: 줄바꿈 */
.t-events { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; width: 100%; max-height: 220px; overflow-y: auto; }  /* .t-events 꾸미기: 목록 점 모양, 바깥 여백, 안쪽 여백, 배치 방식, 쌓는 방향, 사이 간격, 너비, 최대 높이, 세로 넘침 처리 */
.t-events li { border-left: 3px solid var(--line); padding: 2px 0 2px 10px; display: flex; flex-direction: column; font-size: 13px; }  /* .t-events li 꾸미기: 왼쪽 테두리, 안쪽 여백, 배치 방식, 쌓는 방향, 글자 크기 */
.t-events li span { color: var(--muted); font-size: 12px; }  /* .t-events li span 꾸미기: 글자색, 글자 크기 */
@media (max-width: 880px) {  /* 화면 너비가 880px 이하일 때 (휴대폰 등) 시작 */
  .t-grid2, .t-detail, .t-actions { grid-template-columns: 1fr; }  /* .t-grid2, .t-detail, .t-actions 꾸미기: 칸 나누기 */
  .who { display: none; }  /* .who 꾸미기: 배치 방식 */
}  /* 규칙 끝 */

/* ── v2.2 연결복도 버튼 · 검색 ───────────── */
.link { cursor: pointer; }  /* .link 꾸미기: 마우스 모양 */
.link rect { fill: var(--accent); stroke: #fff; stroke-width: 2; filter: drop-shadow(0 2px 4px rgb(15 23 42 / 0.25)); }  /* .link rect 꾸미기: 도형 채우기 색, 선 색, 선 두께, 그림 효과 */
.link text { fill: #fff; font-weight: 700; text-anchor: middle; dominant-baseline: central; letter-spacing: -0.02em; }  /* .link text 꾸미기: 도형 채우기 색, 글자 굵기, 글자 기준점, 글자 세로 기준, 글자 사이 간격 */
.link .arrow { fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }  /* .link .arrow 꾸미기: 도형 채우기 색, 선 색, 선 두께, 선 끝 모양, 선 꺾임 모양 */
.link:hover rect { fill: #1d4ed8; }  /* .link:hover rect 꾸미기: 도형 채우기 색 */
body.reporting .link { pointer-events: none; opacity: 0.5; }  /* body.reporting .link 꾸미기: 마우스 반응 여부, 투명도 */

.hit { pointer-events: none; }  /* .hit 꾸미기: 마우스 반응 여부 */
.hit .ring { fill: rgb(37 99 235 / 0.12); stroke: var(--accent); stroke-width: 3; }  /* .hit .ring 꾸미기: 도형 채우기 색, 선 색, 선 두께 */
.hit .wave { fill: none; stroke: var(--accent); stroke-width: 2; transform-box: fill-box; transform-origin: center; animation: hit-wave 1.4s ease-out 3; opacity: 0; }  /* .hit .wave 꾸미기: 도형 채우기 색, 선 색, 선 두께, 변형 기준 상자, 변형 기준점, 움직임 효과, 투명도 */
@keyframes hit-wave { from { transform: scale(0.6); opacity: 0.9; } to { transform: scale(1.9); opacity: 0; } }  /* 움직임 효과 'hit-wave': 검색 표시 물결이 커지며 사라진다 */

.stage-top { flex-wrap: wrap; align-items: flex-start; }  /* .stage-top 꾸미기: 줄바꿈, 세로 정렬 */
.search {  /* .search 꾸미기 시작 */
  pointer-events: auto; position: relative;  /* 마우스 반응 여부, 위치 방식 */
  display: flex; align-items: center; gap: 6px;  /* 배치 방식, 세로 정렬, 사이 간격 */
  background: var(--paper); border-radius: 999px; padding: 0 12px; height: 40px; box-shadow: var(--shadow);  /* 배경, 모서리 둥글기, 안쪽 여백, 높이, 그림자 */
  width: 230px; max-width: 100%;  /* 너비, 최대 너비 */
}  /* 규칙 끝 */
.search > svg { width: 18px; height: 18px; flex: none; fill: none; stroke: var(--muted); stroke-width: 2; stroke-linecap: round; }  /* .search > svg 꾸미기: 너비, 높이, 늘어나는 비율, 도형 채우기 색, 선 색, 선 두께, 선 끝 모양 */
.search input { border: 0; outline: 0; background: transparent; font: inherit; font-size: 15px; color: var(--ink); width: 100%; min-width: 0; }  /* .search input 꾸미기: 테두리, 강조 테두리, 배경, 글꼴, 글자 크기, 글자색, 너비, 최소 너비 */
.search:focus-within { box-shadow: 0 0 0 2px var(--accent), var(--shadow); }  /* .search:focus-within 꾸미기: 그림자 */
.search-results {  /* .search-results 꾸미기 시작 */
  position: absolute; top: calc(100% + 6px); left: 0; width: max(100%, 260px); margin: 0; padding: 6px; list-style: none;  /* 위치 방식, 위 위치, 왼쪽 위치, 너비, 바깥 여백, 안쪽 여백, 목록 점 모양 */
  background: var(--paper); border-radius: 12px; box-shadow: var(--shadow); max-height: 50vh; overflow-y: auto; z-index: 5;  /* 배경, 모서리 둥글기, 그림자, 최대 높이, 세로 넘침 처리, 겹침 순서 */
}  /* 규칙 끝 */
.search-results li { display: flex; flex-direction: column; gap: 1px; padding: 8px 10px; border-radius: 8px; cursor: pointer; }  /* .search-results li 꾸미기: 배치 방식, 쌓는 방향, 사이 간격, 안쪽 여백, 모서리 둥글기, 마우스 모양 */
.search-results li strong { font-size: 15px; color: var(--ink); }  /* .search-results li strong 꾸미기: 글자 크기, 글자색 */
.search-results li small { font-size: 12.5px; color: var(--muted); }  /* .search-results li small 꾸미기: 글자 크기, 글자색 */
.search-results li[aria-selected="true"], .search-results li:hover { background: #eff6ff; }  /* .search-results li[aria-selected="true"], .search-results li:hover 꾸미기: 배경 */
.search-results .empty { cursor: default; color: var(--muted); font-size: 14px; }  /* .search-results .empty 꾸미기: 마우스 모양, 글자색, 글자 크기 */
.search-results .empty:hover { background: none; }  /* .search-results .empty:hover 꾸미기: 배경 */
@media (max-width: 880px) {  /* 화면 너비가 880px 이하일 때 (휴대폰 등) 시작 */
  .search { width: 100%; }  /* .search 꾸미기: 너비 */
}  /* 규칙 끝 */

/* ── v2.2.1 위험/불편 신고 ───────────── */
.kinds { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }  /* .kinds 꾸미기: 배치 방식, 칸 나누기, 사이 간격 */
.kinds label { position: relative; cursor: pointer; }  /* .kinds label 꾸미기: 위치 방식, 마우스 모양 */
.kinds input { position: absolute; opacity: 0; pointer-events: none; }  /* .kinds input 꾸미기: 위치 방식, 투명도, 마우스 반응 여부 */
.kinds span {  /* .kinds span 꾸미기 시작 */
  display: flex; flex-direction: column; gap: 2px; height: 100%;  /* 배치 방식, 쌓는 방향, 사이 간격, 높이 */
  padding: 10px 12px; border: 2px solid var(--line); border-radius: 12px; background: var(--paper);  /* 안쪽 여백, 테두리, 모서리 둥글기, 배경 */
}  /* 규칙 끝 */
.kinds b { font-size: 16px; color: var(--ink); }  /* .kinds b 꾸미기: 글자 크기, 글자색 */
.kinds small { font-size: 12.5px; color: var(--muted); line-height: 1.35; }  /* .kinds small 꾸미기: 글자 크기, 글자색, 줄 높이 */
.kinds .kind-danger input:checked + span { border-color: var(--danger); background: #fef2f2; }  /* .kinds .kind-danger input:checked + span 꾸미기: 테두리 색, 배경 */
.kinds .kind-incon input:checked + span { border-color: #7c3aed; background: #f5f3ff; }  /* .kinds .kind-incon input:checked + span 꾸미기: 테두리 색, 배경 */
.kinds input:focus-visible + span { outline: 2px solid var(--accent); outline-offset: 2px; }  /* .kinds input:focus-visible + span 꾸미기: 강조 테두리, 강조 테두리 간격 */
.kind-tag { display: inline-block; font-size: 12px; font-weight: 700; padding: 1px 7px; border-radius: 999px; white-space: nowrap; vertical-align: 1px; }  /* .kind-tag 꾸미기: 배치 방식, 글자 크기, 글자 굵기, 안쪽 여백, 모서리 둥글기, 줄바꿈 방식, 세로 맞춤 */
.kind-tag.kind-danger { color: #b91c1c; background: #fee2e2; }  /* .kind-tag.kind-danger 꾸미기: 글자색, 배경 */
.kind-tag.kind-incon { color: #6d28d9; background: #ede9fe; }  /* .kind-tag.kind-incon 꾸미기: 글자색, 배경 */
#formDialog[data-kind="incon"] #formSubmit { background: #7c3aed; border-color: #7c3aed; }  /* #formDialog[data-kind="incon"] #formSubmit 꾸미기: 배경, 테두리 색 */
#formDialog[data-kind="incon"] #formSubmit:hover { background: #6d28d9; }  /* #formDialog[data-kind="incon"] #formSubmit:hover 꾸미기: 배경 */

/* ── v2.2.2 오른쪽 패널 뒤로 가기 ───────────── */
.back-btn {  /* .back-btn 꾸미기 시작 */
  display: inline-flex; align-items: center; gap: 4px; margin-bottom: 10px;  /* 배치 방식, 세로 정렬, 사이 간격, 아래 바깥 여백 */
  padding: 7px 14px 7px 10px; border-radius: 999px; background: #f1f5f9; color: var(--ink);  /* 안쪽 여백, 모서리 둥글기, 배경, 글자색 */
  font-size: 14px; font-weight: 700; text-decoration: none;  /* 글자 크기, 글자 굵기, 밑줄 */
}  /* 규칙 끝 */
.back-btn:hover { background: #e2e8f0; }  /* .back-btn:hover 꾸미기: 배경 */
.back-btn svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }  /* .back-btn svg 꾸미기: 너비, 높이, 도형 채우기 색, 선 색, 선 두께, 선 끝 모양, 선 꺾임 모양 */
/* ── 장난 신고 막기 · 로그인 유지 ─────── */
.check { display: flex; gap: 10px; align-items: flex-start; cursor: pointer; }  /* .check 꾸미기: 배치 방식, 사이 간격, 세로 정렬, 마우스 모양 */
.check input { width: 20px; height: 20px; margin: 1px 0 0; accent-color: var(--accent); flex: none; }  /* .check input 꾸미기: 너비, 높이, 바깥 여백, 체크 상자 색, 늘어나는 비율 */
.check span { display: flex; flex-direction: column; gap: 2px; }  /* .check span 꾸미기: 배치 방식, 쌓는 방향, 사이 간격 */
.check b { font-size: 14.5px; color: var(--ink); }  /* .check b 꾸미기: 글자 크기, 글자색 */
.check small { font-size: 12.5px; color: var(--muted); line-height: 1.4; }  /* .check small 꾸미기: 글자 크기, 글자색, 줄 높이 */
.notice { border: 1px solid #fcd34d; background: #fffbeb; border-radius: 12px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; }  /* .notice 꾸미기: 테두리, 배경, 모서리 둥글기, 안쪽 여백, 배치 방식, 쌓는 방향, 사이 간격 */
.notice > b { font-size: 14px; color: #92400e; }  /* .notice > b 꾸미기: 글자 크기, 글자색 */
.notice ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--ink-2); }  /* .notice ul 꾸미기: 바깥 여백, 왼쪽 안쪽 여백, 글자 크기, 줄 높이, 글자색 */
.notice .check { padding-top: 6px; border-top: 1px dashed #fcd34d; }  /* .notice .check 꾸미기: 위 안쪽 여백, 위 테두리 */
.t-abuse { margin-top: 14px; }  /* .t-abuse 꾸미기: 위 바깥 여백 */
.t-abuse:empty { display: none; }  /* .t-abuse:empty 꾸미기: 배치 방식 */
.t-abuse .blocked { color: var(--danger); }  /* .t-abuse .blocked 꾸미기: 글자색 */

/* ── 학생 구글 로그인 ─────────────────── */
.login-lead { margin: 0; font-size: 14.5px; line-height: 1.55; color: var(--ink-2); }  /* .login-lead 꾸미기: 바깥 여백, 글자 크기, 줄 높이, 글자색 */
.login-points { margin: 0; padding-left: 18px; font-size: 13.5px; line-height: 1.6; color: var(--ink-2); }  /* .login-points 꾸미기: 바깥 여백, 왼쪽 안쪽 여백, 글자 크기, 줄 높이, 글자색 */
.btn-google { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 12px 16px;  /* .btn-google 꾸미기 시작: 배치 방식, 세로 정렬, 가로 정렬, 사이 간격, 너비, 안쪽 여백 */
  border: 1px solid var(--line-2); border-radius: 12px; background: #fff; color: #1f1f1f; font-weight: 700; font-size: 15px; }  /* 테두리, 모서리 둥글기, 배경, 글자색, 글자 굵기, 글자 크기 (규칙 끝) */
.btn-google:hover { background: #f8fafc; }  /* .btn-google:hover 꾸미기: 배경 */
.btn-google svg { width: 20px; height: 20px; }  /* .btn-google svg 꾸미기: 너비, 높이 */
.who-line { margin: 4px 0 0; font-size: 13px; color: var(--ink-2); display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }  /* .who-line 꾸미기: 바깥 여백, 글자 크기, 글자색, 배치 방식, 줄바꿈, 사이 간격, 세로 정렬 */
.who-line small { color: var(--muted); font-size: 12px; }  /* .who-line small 꾸미기: 글자색, 글자 크기 */
.link-btn { background: none; border: 0; padding: 0; color: var(--accent); font-size: 12.5px; font-weight: 600; text-decoration: underline; }  /* .link-btn 꾸미기: 배경, 테두리, 안쪽 여백, 글자색, 글자 크기, 글자 굵기, 밑줄 */

'''  # 꾸미기 글 끝


def apply():  # 꾸미기를 페이지에 붙이는 함수
    if document.getElementById("theme"):  # 이미 붙였으면
        return  # 또 붙이지 않는다
    style = document.createElement("style")  # <style> 요소를 만든다
    style.id = "theme"  # 이름을 붙인다 (두 번 붙이지 않게 확인용)
    style.textContent = CSS  # 위의 꾸미기 글을 넣는다
    document.head.appendChild(style)  # 페이지 머리에 붙인다
