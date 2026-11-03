// 벡터 도면 뷰어: viewBox 를 직접 바꿔서 확대/이동한다.
// (CSS transform 확대와 달리 확대해도 선과 글자가 흐려지지 않는다)

const NS = "http://www.w3.org/2000/svg";
const cache = new Map();

async function fetchPlan(url) {
  if (!cache.has(url)) {
    cache.set(url, fetch(url).then((r) => {
      if (!r.ok) throw new Error(`도면을 불러오지 못했습니다: ${url}`);
      return r.text();
    }));
  }
  return cache.get(url);
}

export class PlanViewer {
  constructor(svg) {
    this.svg = svg;
    this.layers = {};
    for (const name of ["plan", "overlay", "pins", "draft"]) {
      const g = document.createElementNS(NS, "g");
      g.setAttribute("class", `layer-${name}`);
      svg.appendChild(g);
      this.layers[name] = g;
    }
    this.size = { w: 100, h: 100 };
    this.view = { x: 0, y: 0, w: 100, h: 100 };
    this.minW = 10;
    this.onTap = null; // (x, y, event) => void, 도면 좌표
    this.onViewChange = null;
    this.loadToken = 0;
    this._bindInput();
    new ResizeObserver(() => this._apply()).observe(svg);
  }

  async load(url, w, h) {
    const token = ++this.loadToken;
    this.size = { w, h };
    this.layers.plan.replaceChildren();
    this.svg.classList.add("is-loading");
    this.fit();
    const text = await fetchPlan(url);
    if (token !== this.loadToken) return false;
    const doc = new DOMParser().parseFromString(text, "image/svg+xml");
    const frag = document.createDocumentFragment();
    for (const node of [...doc.documentElement.childNodes]) frag.appendChild(document.importNode(node, true));
    this.layers.plan.replaceChildren(frag);
    this.svg.classList.remove("is-loading");
    return true;
  }

  fit() {
    const { w, h } = this.size;
    const pad = Math.max(w, h) * 0.04;
    this.view = { x: -pad, y: -pad, w: w + pad * 2, h: h + pad * 2 };
    this.minW = w / 40;
    this._apply();
  }

  zoomBy(factor, cx, cy) {
    const v = this.view;
    const maxW = Math.max(this.size.w, this.size.h) * 3;
    const nw = Math.min(maxW, Math.max(this.minW, v.w / factor));
    const k = nw / v.w;
    if (cx === undefined) { cx = v.x + v.w / 2; cy = v.y + v.h / 2; }
    this.view = { x: cx - (cx - v.x) * k, y: cy - (cy - v.y) * k, w: v.w * k, h: v.h * k };
    this._apply();
  }

  focus(x, y, widthPt) {
    const r = this.svg.getBoundingClientRect();
    const w = widthPt, h = (w * r.height) / Math.max(1, r.width);
    this.view = { x: x - w / 2, y: y - h / 2, w, h };
    this._apply();
  }

  /** 화면 1px 이 도면 좌표로 몇 단위인지 (핀 크기를 화면 기준으로 고정할 때 사용) */
  get unitsPerPx() {
    const r = this.svg.getBoundingClientRect();
    if (!r.width || !r.height) return 1;
    return Math.max(this.view.w / r.width, this.view.h / r.height);
  }

  toPlan(clientX, clientY) {
    const pt = new DOMPoint(clientX, clientY).matrixTransform(this.svg.getScreenCTM().inverse());
    return { x: pt.x, y: pt.y };
  }

  _apply() {
    const r = this.svg.getBoundingClientRect();
    // 화면 비율에 맞춰 viewBox 를 보정해 preserveAspectRatio 여백과 좌표가 어긋나지 않게 한다
    if (r.width && r.height) {
      const aspect = r.width / r.height;
      const v = this.view;
      if (v.w / v.h > aspect) { const nh = v.w / aspect; v.y -= (nh - v.h) / 2; v.h = nh; }
      else { const nw = v.h * aspect; v.x -= (nw - v.w) / 2; v.w = nw; }
    }
    const { x, y, w, h } = this.view;
    this.svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);
    this.onViewChange && this.onViewChange();
  }

  _bindInput() {
    const svg = this.svg;
    const pointers = new Map();
    let drag = null;
    let pinch = null;
    let raf = 0;
    const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; this._apply(); }); };

    svg.addEventListener("wheel", (e) => {
      e.preventDefault();
      const p = this.toPlan(e.clientX, e.clientY);
      const factor = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0015));
      this.zoomBy(factor, p.x, p.y);
    }, { passive: false });

    svg.addEventListener("pointerdown", (e) => {
      if (e.button !== 0 && e.pointerType === "mouse") return;
      svg.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pointers.size === 1) {
        drag = { sx: e.clientX, sy: e.clientY, view: { ...this.view }, moved: false, target: e.target };
      } else if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        pinch = { dist: Math.hypot(a.x - b.x, a.y - b.y), view: { ...this.view } };
        drag = null;
      }
    });

    svg.addEventListener("pointermove", (e) => {
      if (!pointers.has(e.pointerId)) return;
      pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      const r = svg.getBoundingClientRect();
      if (pinch && pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        const dist = Math.hypot(a.x - b.x, a.y - b.y);
        const mid = this.toPlan((a.x + b.x) / 2, (a.y + b.y) / 2);
        this.view = { ...pinch.view };
        this.view.w = pinch.view.w; this.view.h = pinch.view.h;
        const k = pinch.dist / Math.max(1, dist);
        const nw = Math.min(Math.max(this.size.w, this.size.h) * 3, Math.max(this.minW, pinch.view.w * k));
        const kk = nw / pinch.view.w;
        this.view = { x: mid.x - (mid.x - pinch.view.x) * kk, y: mid.y - (mid.y - pinch.view.y) * kk, w: pinch.view.w * kk, h: pinch.view.h * kk };
        schedule();
      } else if (drag) {
        const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
        if (Math.hypot(dx, dy) > 4) { drag.moved = true; svg.classList.add("is-panning"); }
        if (drag.moved) {
          const s = Math.max(drag.view.w / r.width, drag.view.h / r.height);
          this.view = { ...drag.view, x: drag.view.x - dx * s, y: drag.view.y - dy * s };
          schedule();
        }
      }
    });

    const end = (e) => {
      if (!pointers.has(e.pointerId)) return;
      pointers.delete(e.pointerId);
      if (drag && !drag.moved && e.type === "pointerup" && this.onTap) {
        const p = this.toPlan(e.clientX, e.clientY);
        this.onTap(p.x, p.y, drag.target);
      }
      if (pointers.size < 2) pinch = null;
      if (pointers.size === 0) drag = null;
      svg.classList.remove("is-panning");
    };
    svg.addEventListener("pointerup", end);
    svg.addEventListener("pointercancel", end);
  }
}
