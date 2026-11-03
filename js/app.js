import { SITE, PLAN_SIZES, BUILDINGS, CATEGORIES, SEVERITIES, STATUSES, buildingById, floorById } from "./data.js";
import { store } from "./store.js";
import { PlanViewer } from "./viewer.js";

const NS = "http://www.w3.org/2000/svg";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const sevOf = (id) => SEVERITIES.find((s) => s.id === id) || SEVERITIES[2];
const catOf = (id) => CATEGORIES.find((c) => c.id === id) || CATEGORIES.at(-1);
const statusOf = (id) => STATUSES.find((s) => s.id === id) || STATUSES[0];
const isOpen = (r) => r.status !== "done";

const PIN_PATH = "M0 0C-1.6-5.4-11-9.6-11-18.5a11 11 0 0 1 22 0C11-9.6 1.6-5.4 0 0z";

const state = {
  place: "site",      // "site" 또는 층 id (예: "b2-1f")
  loaded: null,
  mode: "browse",     // "browse" | "report"
  draft: null,        // { x, y }
  selected: null,
  scope: "here",
  status: "open",
  aux: true,
};

const viewer = new PlanViewer($("#map"));

// ── 위치 표시 ──────────────────────────────────────
function placeInfo(place) {
  if (place === "site") return { title: "캠퍼스 전체", short: "캠퍼스 야외", building: null, floor: null };
  const hit = floorById(place);
  if (!hit) return { title: place, short: place, building: null, floor: null };
  return { title: `${hit.building.name} ${hit.floor.name}`, short: `${hit.building.name} ${hit.floor.name}`, ...hit };
}

function timeAgo(iso) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "방금";
  if (s < 3600) return `${Math.floor(s / 60)}분 전`;
  if (s < 86400) return `${Math.floor(s / 3600)}시간 전`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)}일 전`;
  return new Date(iso).toLocaleDateString("ko-KR");
}

function openCount(pred) {
  return store.list().filter((r) => isOpen(r) && pred(r)).length;
}
const floorsOf = (b) => new Set(b.floors.map((f) => f.id));

// ── 라우팅 ────────────────────────────────────────
function parseHash() {
  const h = decodeURIComponent(location.hash.replace(/^#\/?/, ""));
  if (!h) return "site";
  if (PLAN_SIZES[h]) return h;
  const b = buildingById(h);
  if (b) return (b.floors.find((f) => f.label === "1F") || b.floors[0]).id;
  return "site";
}
function go(place) {
  const target = place === "site" ? "" : `#${place}`;
  if (location.hash === target || (!target && !location.hash)) navigate(place);
  else location.hash = target;
}

async function navigate(place, after) {
  const changed = place !== state.loaded;
  state.place = place;
  if (state.mode === "report") { setDraft(null); setMode("report"); }
  renderChrome();
  renderList();
  if (changed) {
    state.loaded = place;
    $("#loading").hidden = false;
    const file = place === "site" ? SITE.file : `plans/${place}.svg`;
    const [w, h] = place === "site" ? [SITE.w, SITE.h] : PLAN_SIZES[place];
    try {
      const ok = await viewer.load(file, w, h);
      if (!ok) return;
    } catch (e) {
      toast(e.message);
    } finally {
      $("#loading").hidden = true;
    }
    renderOverlay();
    renderPins();
  }
  after && after();
}

// ── 상단·층 선택·패널 ────────────────────────────────
function renderChrome() {
  const info = placeInfo(state.place);
  const crumbs = $("#crumbs");
  if (!info.building) {
    crumbs.innerHTML = `<span class="here">광덕중·고 캠퍼스</span>`;
  } else {
    crumbs.innerHTML = `<a href="#">캠퍼스</a><span class="sep">›</span><span class="here">${esc(info.building.name)}</span>`;
  }

  const bar = $("#floorbar");
  if (info.building) {
    bar.innerHTML = info.building.floors.map((f) => {
      const n = openCount((r) => r.place.map === f.id);
      return `<button role="tab" data-floor="${f.id}" aria-selected="${f.id === state.place}" title="${esc(f.name)}">${esc(f.label)}${n ? `<span class="dot">${n}</span>` : ""}</button>`;
    }).join("");
  } else bar.innerHTML = "";

  const ctx = $("#ctx");
  if (!info.building) {
    ctx.innerHTML = `
      <h1>캠퍼스 평면도</h1>
      <p class="sub">건물을 누르면 층별 평면도가 열립니다.</p>
      <div class="bld-grid">
        ${BUILDINGS.map((b) => {
          const n = openCount((r) => floorsOf(b).has(r.place.map));
          return `<button class="bld-card" style="--c:${b.color}" data-building="${b.id}">
            <strong>${esc(b.name)}</strong><small>${esc([b.dong, b.sub].filter(Boolean).join(" · "))}</small>
            ${n ? `<span class="n">${n}</span>` : ""}</button>`;
        }).join("")}
      </div>
      <p class="hint">운동장·주차장 같은 야외 위험은 이 화면에서 <b>위험 신고</b>를 누르고 지도 위를 찍어주세요.</p>`;
  } else {
    const b = info.building, fl = info.floor;
    ctx.innerHTML = `
      <h1>${esc(b.name)} <span style="color:var(--muted);font-weight:600">${esc(fl.name)}</span></h1>
      <p class="sub">${esc([b.sub, b.dong].filter(Boolean).join(" · "))}</p>
      <div class="meta">
        <span class="tag color" style="--c:${b.color}">${esc(b.code)}</span>
        ${fl.area ? `<span class="tag">바닥면적 ${fl.area.toLocaleString("ko-KR")}㎡</span>` : ""}
        <span class="tag">${b.floors.length}개 층 도면</span>
      </div>
      <div class="floor-list" role="tablist">
        ${b.floors.map((f) => `<button role="tab" data-floor="${f.id}" aria-selected="${f.id === state.place}">${esc(f.name)}</button>`).join("")}
      </div>`;
  }
  $("#scopeSeg").hidden = !info.building;
}

// ── 배치도 위 건물 ──────────────────────────────────
function polyBox(pts) {
  const xs = [], ys = [];
  pts.trim().split(/\s+/).forEach((p) => { const [x, y] = p.split(",").map(Number); xs.push(x); ys.push(y); });
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) };
}

function renderOverlay() {
  const g = viewer.layers.overlay;
  g.replaceChildren();
  if (state.place !== "site") return;
  for (const b of BUILDINGS) {
    if (!b.polys.length) continue;
    const grp = document.createElementNS(NS, "g");
    grp.setAttribute("class", "bld");
    grp.dataset.building = b.id;
    grp.style.setProperty("--c", b.color);
    for (const p of b.polys) {
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", "M" + p.trim().split(/\s+/).join("L") + "Z");
      grp.appendChild(path);
    }
    const title = document.createElementNS(NS, "title");
    title.textContent = `${b.name} (${b.dong}) — 눌러서 층별 평면도 보기`;
    grp.appendChild(title);
    g.appendChild(grp);
  }
  // 라벨은 건물 위에 따로 (화면 크기 고정)
  for (const b of BUILDINGS) {
    if (!b.polys.length) continue;
    const bx = polyBox(b.polys[0]);
    const n = openCount((r) => floorsOf(b).has(r.place.map));
    const lbl = document.createElementNS(NS, "g");
    lbl.setAttribute("class", "bld-label");
    lbl.style.setProperty("--c", b.color);
    lbl.dataset.cx = (bx.x0 + bx.x1) / 2;
    lbl.dataset.cy = (bx.y0 + bx.y1) / 2;
    const w = b.name.length * 12.5 + 18;
    lbl.innerHTML = `<rect x="${-w / 2}" y="-11" width="${w}" height="22" rx="11"/><text font-size="12.5">${esc(b.name)}</text>` +
      (n ? `<circle class="count-bg" cx="${w / 2}" cy="-10" r="9"/><text class="count" x="${w / 2}" y="-10" font-size="10.5">${n}</text>` : "");
    g.appendChild(lbl);
  }
  updateScales();
}

// ── 핀 ────────────────────────────────────────────
function makePin(r) {
  const sev = sevOf(r.severity);
  const g = document.createElementNS(NS, "g");
  g.setAttribute("class", `pin ${r.status === "done" ? "done" : ""} ${state.selected === r.id ? "is-selected" : ""}`);
  g.dataset.id = r.id;
  g.dataset.x = r.place.x;
  g.dataset.y = r.place.y;
  g.style.color = sev.color;
  g.innerHTML = `<circle class="halo" cy="-18.5" r="17"/><path class="drop" d="${PIN_PATH}" fill="${sev.color}"/>` +
    (r.status === "done"
      ? `<path d="M-4.5-18.5l3 3 6-6" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`
      : `<circle class="core" cy="-18.5" r="4.5"/>`) +
    `<title>${esc(r.title)} · ${statusOf(r.status).label}</title>`;
  return g;
}

function renderPins() {
  const g = viewer.layers.pins;
  g.replaceChildren();
  const here = store.list().filter((r) => r.place.map === state.place);
  // 완료된 신고는 아래, 긴급한 신고는 위에 그린다
  const order = (r) => (r.status === "done" ? -10 : 0) - SEVERITIES.findIndex((s) => s.id === r.severity);
  here.sort((a, b) => order(a) - order(b)).forEach((r) => g.appendChild(makePin(r)));
  renderDraft();
  updateScales();
}

function renderDraft() {
  const g = viewer.layers.draft;
  g.replaceChildren();
  if (!state.draft) return;
  const d = document.createElementNS(NS, "g");
  d.setAttribute("class", "draft-pin");
  d.dataset.x = state.draft.x;
  d.dataset.y = state.draft.y;
  d.innerHTML = `<circle class="ring" r="14"/><path class="drop" d="${PIN_PATH}"/><circle cy="-18.5" r="4.5" fill="#fff"/>`;
  g.appendChild(d);
  updateScales();
}

function updateScales() {
  const u = viewer.unitsPerPx;
  document.querySelectorAll(".pin, .draft-pin, .bld-label").forEach((el) => {
    const x = el.dataset.x ?? el.dataset.cx, y = el.dataset.y ?? el.dataset.cy;
    el.setAttribute("transform", `translate(${x} ${y}) scale(${u})`);
  });
}
viewer.onViewChange = updateScales;

// ── 지도 탭 ───────────────────────────────────────
viewer.onTap = (x, y, target) => {
  const pin = target.closest && target.closest(".pin");
  if (pin && state.mode !== "report") return openDetail(pin.dataset.id);
  if (state.mode === "report") {
    const { w, h } = viewer.size;
    if (x < 0 || y < 0 || x > w || y > h) return toast("도면 안쪽을 눌러주세요");
    setDraft({ x, y });
    openForm();
    return;
  }
  const bld = target.closest && target.closest(".bld");
  if (bld) go(bld.dataset.building);
};

// ── 신고 모드 ─────────────────────────────────────
function setMode(mode) {
  state.mode = mode;
  document.body.classList.toggle("reporting", mode === "report");
  $("#btnReport").setAttribute("aria-pressed", mode === "report");
  $("#btnReport span").textContent = mode === "report" ? "신고 취소" : "위험 신고";
  $("#modeBanner").hidden = mode !== "report";
  $("#modeText").textContent = state.place === "site"
    ? "지도에서 위험한 곳을 눌러주세요 (건물 안은 건물을 먼저 선택)"
    : `${placeInfo(state.place).title} 도면에서 위험한 곳을 눌러주세요`;
  if (mode !== "report") setDraft(null);
}
function setDraft(d) { state.draft = d; renderDraft(); }

$("#btnReport").addEventListener("click", () => setMode(state.mode === "report" ? "browse" : "report"));
$("#modeCancel").addEventListener("click", () => setMode("browse"));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && state.mode === "report" && !document.querySelector("dialog[open]")) setMode("browse");
});

// ── 신고 작성 폼 ──────────────────────────────────
const form = $("#reportForm");
const formDialog = $("#formDialog");
let photoData = null;

$("#catChips").innerHTML = CATEGORIES.map((c, i) =>
  `<label><input type="radio" name="category" value="${c.id}" ${i === 0 ? "checked" : ""}/><span>${c.icon} ${esc(c.label)}</span></label>`).join("");
$("#sevChips").innerHTML = SEVERITIES.map((s) =>
  `<label style="--c:${s.color}"><input type="radio" name="severity" value="${s.id}" ${s.id === "mid" ? "checked" : ""}/><span>${esc(s.label)}</span></label>`).join("");

function openForm() {
  form.reset();
  photoData = null;
  $("#photoPreview").hidden = true;
  $("#photoHint").textContent = "사진 추가 · 촬영";
  $("#formWhere").textContent = `📍 ${placeInfo(state.place).short}`;
  formDialog.showModal();
  setTimeout(() => form.elements.title.focus(), 50);
}
formDialog.querySelectorAll("[data-close]").forEach((b) => b.addEventListener("click", () => formDialog.close("cancel")));
formDialog.addEventListener("close", () => {
  // 취소하면 찍은 위치만 지우고 신고 모드는 유지해서 다시 찍을 수 있게 한다
  if (formDialog.returnValue !== "submitted") setDraft(null);
});

form.elements.photo.addEventListener("change", async () => {
  const file = form.elements.photo.files[0];
  if (!file) return;
  photoData = await shrinkImage(file, 1024, 0.72);
  $("#photoPreview").src = photoData;
  $("#photoPreview").hidden = false;
  $("#photoHint").textContent = "사진 바꾸기";
});

function shrinkImage(file, max, quality) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * k);
      c.height = Math.round(img.height * k);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      resolve(c.toDataURL("image/jpeg", quality));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (!state.draft) return;
  const fd = new FormData(form);
  const r = store.add({
    place: { map: state.place, x: +state.draft.x.toFixed(2), y: +state.draft.y.toFixed(2) },
    category: fd.get("category"),
    severity: fd.get("severity"),
    title: fd.get("title").trim(),
    spot: fd.get("spot").trim(),
    desc: fd.get("desc").trim(),
    reporter: fd.get("reporter").trim(),
    photo: photoData,
  });
  formDialog.close("submitted");
  setMode("browse");
  state.selected = r.id;
  toast("신고가 접수되었습니다");
});

// ── 신고 상세 ─────────────────────────────────────
const detailDialog = $("#detailDialog");

function openDetail(id) {
  const r = store.get(id);
  if (!r) return;
  state.selected = id;
  renderPins();
  renderList();
  const sev = sevOf(r.severity), cat = catOf(r.category), st = statusOf(r.status);
  $("#detailBody").innerHTML = `
    <header class="sheet-head">
      <div>
        <p class="eyebrow" style="color:${sev.color}">${esc(sev.label)} · ${cat.icon} ${esc(cat.label)}</p>
        <h2>${esc(r.title)}</h2>
      </div>
      <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
    </header>
    <div class="sheet-body">
      ${r.photo ? `<img class="detail-photo" src="${r.photo}" alt="신고 사진" />` : ""}
      ${r.desc ? `<p class="detail-desc">${esc(r.desc)}</p>` : ""}
      <dl class="detail-grid">
        <dt>상태</dt><dd><span class="status ${r.status}">${esc(st.label)}</span></dd>
        <dt>위치</dt><dd>${esc(placeInfo(r.place.map).short)}</dd>
        ${r.spot ? `<dt>정확한 장소</dt><dd>${esc(r.spot)}</dd>` : ""}
        <dt>신고자</dt><dd>${esc(r.reporter || "익명")}</dd>
        <dt>신고 일시</dt><dd>${new Date(r.createdAt).toLocaleString("ko-KR")}</dd>
        ${r.updatedAt ? `<dt>최근 변경</dt><dd>${new Date(r.updatedAt).toLocaleString("ko-KR")}</dd>` : ""}
      </dl>
      <div>
        <span class="field"><span>처리 상태 변경</span></span>
        <div class="seg" id="detailStatus">
          ${STATUSES.map((s) => `<button type="button" data-v="${s.id}" aria-pressed="${s.id === r.status}">${esc(s.label)}</button>`).join("")}
        </div>
      </div>
    </div>
    <footer class="sheet-foot detail-actions">
      <button class="btn-text-danger" type="button" id="detailDelete">삭제</button>
      <button class="btn btn-quiet" type="button" id="detailGo">위치 보기</button>
    </footer>`;
  detailDialog.querySelector("[data-close]").addEventListener("click", () => detailDialog.close());
  detailDialog.querySelectorAll("#detailStatus button").forEach((b) => b.addEventListener("click", () => {
    store.update(r.id, { status: b.dataset.v });
    openDetail(r.id);
    toast(`'${statusOf(b.dataset.v).label}'(으)로 변경했습니다`);
  }));
  $("#detailDelete").addEventListener("click", () => {
    if (!confirm("이 신고를 삭제할까요? 되돌릴 수 없습니다.")) return;
    store.remove(r.id);
    detailDialog.close();
    state.selected = null;
    toast("삭제했습니다");
  });
  $("#detailGo").addEventListener("click", () => { detailDialog.close(); focusReport(r); });
  if (!detailDialog.open) detailDialog.showModal();
}
detailDialog.addEventListener("click", (e) => { if (e.target === detailDialog) detailDialog.close(); });
formDialog.addEventListener("click", (e) => { if (e.target === formDialog) formDialog.close("cancel"); });

function focusReport(r) {
  state.selected = r.id;
  const doFocus = () => {
    viewer.focus(r.place.x, r.place.y - 6, Math.min(viewer.size.w, 220));
    renderPins();
    renderList();
  };
  if (r.place.map !== state.loaded) {
    history.replaceState(null, "", r.place.map === "site" ? location.pathname : `#${r.place.map}`);
    navigate(r.place.map, doFocus);
  } else doFocus();
}

// ── 신고 목록 ─────────────────────────────────────
function renderList() {
  const all = store.list();
  const open = all.filter(isOpen);
  $("#stats").innerHTML =
    `<span>미처리<b>${open.length}</b></span><span class="urgent">긴급<b>${open.filter((r) => r.severity === "urgent").length}</b></span><span>완료<b>${all.length - open.length}</b></span>`;

  let items = all;
  if (state.place !== "site" && state.scope === "here") items = items.filter((r) => r.place.map === state.place);
  if (state.status === "open") items = items.filter(isOpen);
  if (state.status === "done") items = items.filter((r) => !isOpen(r));

  const list = $("#reportList");
  if (!items.length) {
    list.innerHTML = `<li class="empty">${all.length
      ? "조건에 맞는 신고가 없습니다."
      : `아직 접수된 신고가 없습니다.<br/>위험한 곳을 발견하면 <b>위험 신고</b>를 눌러주세요.<br/><button class="btn btn-quiet" id="btnSample" type="button">예시 신고 불러오기</button>`}</li>`;
    $("#btnSample")?.addEventListener("click", loadSamples);
    return;
  }
  list.innerHTML = items.map((r) => {
    const sev = sevOf(r.severity), st = statusOf(r.status);
    return `<li><button class="report-item ${state.selected === r.id ? "is-selected" : ""}" data-id="${r.id}" type="button">
      <span class="sev-dot" style="background:${r.status === "done" ? "#94a3b8" : sev.color}" title="${esc(sev.label)}"></span>
      <span class="t">${esc(r.title)}</span>
      <span class="status ${r.status}">${esc(st.label)}</span>
      <span class="w">${esc(placeInfo(r.place.map).short)}${r.spot ? " · " + esc(r.spot) : ""} · ${timeAgo(r.createdAt)}</span>
    </button></li>`;
  }).join("");
}

$("#reportList").addEventListener("click", (e) => {
  const item = e.target.closest(".report-item");
  if (!item) return;
  const r = store.get(item.dataset.id);
  if (!r) return;
  focusReport(r);
  setTimeout(() => openDetail(r.id), r.place.map === state.loaded ? 0 : 350);
});

function bindSeg(el, key) {
  el.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    state[key] = b.dataset.v;
    el.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    renderList();
  });
}
bindSeg($("#scopeSeg"), "scope");
bindSeg($("#statusSeg"), "status");

// ── 패널·층 버튼 ──────────────────────────────────
document.addEventListener("click", (e) => {
  const fl = e.target.closest("[data-floor]");
  if (fl) return go(fl.dataset.floor);
  const bc = e.target.closest(".bld-card");
  if (bc) return go(bc.dataset.building);
});

// 목록 카드에 올리면 지도 위 건물 강조
$("#ctx").addEventListener("pointerover", (e) => {
  const id = e.target.closest(".bld-card")?.dataset.building;
  document.querySelectorAll(".bld").forEach((g) => g.classList.toggle("is-hot", g.dataset.building === id));
});
$("#ctx").addEventListener("pointerleave", () => document.querySelectorAll(".bld.is-hot").forEach((g) => g.classList.remove("is-hot")));

// ── 지도 도구 ─────────────────────────────────────
$("#zoomIn").addEventListener("click", () => viewer.zoomBy(1.5));
$("#zoomOut").addEventListener("click", () => viewer.zoomBy(1 / 1.5));
$("#zoomFit").addEventListener("click", () => viewer.fit());
$("#toggleAux").addEventListener("click", (e) => {
  state.aux = !state.aux;
  e.currentTarget.setAttribute("aria-pressed", state.aux);
  $("#map").classList.toggle("hide-aux", !state.aux);
});

// ── 내보내기 / 가져오기 ────────────────────────────
$("#btnExport").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(store.list(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `safety-reports-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
});
$("#fileImport").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    if (!Array.isArray(data) || !data.every((r) => r && r.id && r.place && r.title)) throw new Error();
    if (!confirm(`신고 ${data.length}건으로 현재 목록을 바꿀까요?`)) return;
    store.replaceAll(data);
    toast(`${data.length}건을 가져왔습니다`);
  } catch {
    toast("올바른 신고 JSON 파일이 아닙니다");
  }
});

function loadSamples() {
  const ago = (h) => new Date(Date.now() - h * 3600e3).toISOString();
  const samples = [
    { place: { map: "b2-1f", x: 268, y: 115 }, category: "slip", severity: "high", title: "중앙 복도 바닥 물기", spot: "1층 복도, 교무실 앞", desc: "비 오는 날마다 출입구 쪽에서 물이 들어와 미끄럽습니다.", reporter: "", createdAt: ago(3) },
    { place: { map: "b2-1f", x: 150, y: 150 }, category: "facility", severity: "urgent", title: "계단실 1 난간 흔들림", spot: "계단실 1, 1~2층 사이", desc: "난간 고정 볼트가 빠져서 손으로 밀면 크게 흔들립니다.", reporter: "2학년 학생", createdAt: ago(26) },
    { place: { map: "site", x: 330, y: 470 }, category: "traffic", severity: "mid", title: "운동장 옆 통로 차량 통행", spot: "대운동장 동쪽 통로", desc: "등교 시간에 차량이 학생 통로로 들어옵니다.", reporter: "", createdAt: ago(50) },
    { place: { map: "b4-2f", x: 420, y: 205 }, category: "fire", severity: "mid", title: "멀티탭 문어발 연결", spot: "2층 교실 뒤편", desc: "", reporter: "", status: "doing", createdAt: ago(80) },
    { place: { map: "b8-1f", x: 240, y: 300 }, category: "facility", severity: "low", title: "체육관 바닥 마감재 들뜸", spot: "코트 중앙", desc: "", reporter: "체육부", status: "done", createdAt: ago(200) },
  ];
  store.replaceAll(samples.map((s, i) => ({ id: `sample-${i + 1}`, status: "new", ...s })));
  toast("예시 신고 5건을 불러왔습니다");
}

// ── 공용 ──────────────────────────────────────────
let toastTimer;
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}

store.subscribe(() => {
  renderChrome();
  renderList();
  renderOverlay();
  renderPins();
});

window.addEventListener("hashchange", () => navigate(parseHash()));
navigate(parseHash());
