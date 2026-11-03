# 벡터 도면 뷰어: <svg> 의 viewBox 를 바꿔서 확대/이동한다.
# (그림을 키우는 게 아니라 벡터를 다시 그려서, 확대해도 선과 글자가 흐려지지 않는다)
import math
import re

from js import DOMPoint, ResizeObserver, document, window
from pyodide.ffi import create_proxy
from pyodide.http import pyfetch

from campus import BUILDINGS, SEVERITIES
from common import esc, on

NS = "http://www.w3.org/2000/svg"
ROOM = 1.3       # 도면 크기의 130% 까지만 멀어지고, 그 밖으로는 끌고 갈 수 없다
MAX_ZOOM = 10    # 가장 멀리 본 것보다 10배까지 가까이
PLANS_VERSION = "2.1.3"  # plans/*.svg 를 고치면 올린다 (브라우저가 옛날 도면을 쓰지 않게)
PIN_PATH = "M0 0C-1.6-5.4-11-9.6-11-18.5a11 11 0 0 1 22 0C11-9.6 1.6-5.4 0 0z"
_svg_cache = {}


async def fetch_plan(url):
    if url not in _svg_cache:
        res = await pyfetch(f"{url}?v={PLANS_VERSION}")
        if not res.ok:
            raise RuntimeError(f"도면을 불러오지 못했어요: {url}")
        _svg_cache[url] = await res.string()
    return _svg_cache[url]


def el(tag, attrs=None, cls=None):
    e = document.createElementNS(NS, tag)
    for k, v in (attrs or {}).items():
        e.setAttribute(k, str(v))
    if cls:
        e.setAttribute("class", cls)
    return e


class PlanViewer:
    _count = 0

    def __init__(self, svg):
        self.svg = svg
        self.layers = {}
        # 도면 틀 밖으로 삐져나온 선(치수 눈금 등)은 잘라서 안 보이게
        PlanViewer._count += 1
        clip_id = f"plan-clip-{PlanViewer._count}"
        clip = el("clipPath", {"id": clip_id})
        self._clip_rect = el("rect", {"x": 0, "y": 0, "width": 100, "height": 100})
        clip.appendChild(self._clip_rect)
        svg.appendChild(clip)
        for name in ("plan", "overlay", "pins", "draft"):
            g = el("g", cls=f"layer-{name}")
            svg.appendChild(g)
            self.layers[name] = g
        self.layers["plan"].setAttribute("clip-path", f"url(#{clip_id})")
        self.size = (100.0, 100.0)
        self.bounds = (0.0, 0.0, 100.0, 100.0)  # 실제로 그림이 있는 영역
        self.view = [0.0, 0.0, 100.0, 100.0]
        self.on_tap = None          # (x, y, 누른 요소) → 도면 좌표로 알려준다
        self.on_view_change = None
        self._token = 0
        self._pointers = {}
        self._drag = None
        self._pinch = None
        self._raf = None
        self._bind()
        ResizeObserver.new(create_proxy(lambda *a: self.apply())).observe(svg)

    # ── 도면 불러오기 ──
    async def load(self, url):
        self._token += 1
        token = self._token
        self.layers["plan"].innerHTML = ""
        self.svg.classList.add("is-loading")
        text = await fetch_plan(url)
        if token != self._token:
            return False  # 그 사이에 다른 층을 눌렀다
        m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', text[:400])
        self.size = (float(m.group(1)), float(m.group(2)))
        self._clip_rect.setAttribute("width", self.size[0])
        self._clip_rect.setAttribute("height", self.size[1])
        inner = text[text.index(">", text.index("<svg")) + 1: text.rindex("</svg>")]
        self.layers["plan"].innerHTML = inner
        self.svg.classList.remove("is-loading")
        self.bounds = self._content_box()
        self.fit()
        return True

    def _content_box(self):
        """도면 안에서 선·글자가 실제로 있는 영역 (화면에 안 보일 때는 도면 전체)."""
        W, H = self.size
        try:
            b = self.layers["plan"].getBBox()
            x0, y0 = max(0, b.x), max(0, b.y)
            x1, y1 = min(W, b.x + b.width), min(H, b.y + b.height)
            if x1 - x0 > W * 0.2 and y1 - y0 > H * 0.2:
                return (x0, y0, x1 - x0, y1 - y0)
        except Exception:
            pass
        return (0.0, 0.0, W, H)

    # ── 보기 영역 ──
    def fit(self):
        bx, by, bw, bh = self.bounds
        pad = max(bw, bh) * 0.04
        self.view = [bx - pad, by - pad, bw + pad * 2, bh + pad * 2]
        self.apply()

    def zoom_by(self, factor, cx=None, cy=None):
        x, y, w, h = self.view
        k = 1 / factor
        if cx is None:
            cx, cy = x + w / 2, y + h / 2
        self.view = [cx - (cx - x) * k, cy - (cy - y) * k, w * k, h * k]
        self.apply()

    def focus(self, x, y, width):
        r = self.svg.getBoundingClientRect()
        h = width * r.height / max(1, r.width)
        self.view = [x - width / 2, y - h / 2, width, h]
        self.apply()

    @property
    def units_per_px(self):
        """화면 1px 이 도면 좌표로 얼마인지 (핀 크기를 화면 기준으로 고정할 때 쓴다)."""
        r = self.svg.getBoundingClientRect()
        if not r.width or not r.height:
            return 1
        return max(self.view[2] / r.width, self.view[3] / r.height)

    def to_plan(self, client_x, client_y):
        p = DOMPoint.new(client_x, client_y).matrixTransform(self.svg.getScreenCTM().inverse())
        return p.x, p.y

    def apply(self):
        r = self.svg.getBoundingClientRect()
        x, y, w, h = self.view
        if r.width and r.height:
            aspect = r.width / r.height
            # 화면 비율에 맞춰 viewBox 를 맞춘다 (클릭 좌표가 어긋나지 않게)
            if w / h > aspect:
                nh = w / aspect
                y -= (nh - h) / 2
                h = nh
            else:
                nw = h * aspect
                x -= (nw - w) / 2
                w = nw
            # 확대·축소 한계: 도면의 130% 가 화면에 꽉 차는 것보다 멀리는 못 간다
            bx, by, bw, bh = self.bounds
            rx, ry, rw, rh = bx - bw * (ROOM - 1) / 2, by - bh * (ROOM - 1) / 2, bw * ROOM, bh * ROOM
            max_w = max(rw, rh * aspect)
            nw = min(max_w, max(max_w / MAX_ZOOM, w))
            if nw != w:
                cx, cy = x + w / 2, y + h / 2
                w, h = nw, nw / aspect
                x, y = cx - w / 2, cy - h / 2
            # 이동 한계: 130% 영역 밖으로 끌고 갈 수 없다
            x = rx + (rw - w) / 2 if w >= rw else min(max(x, rx), rx + rw - w)
            y = ry + (rh - h) / 2 if h >= rh else min(max(y, ry), ry + rh - h)
        self.view = [x, y, w, h]
        self.svg.setAttribute("viewBox", f"{x} {y} {w} {h}")
        if self.on_view_change:
            self.on_view_change()

    def _schedule(self):
        if self._raf is None:
            def run(*_):
                self._raf = None
                self.apply()
            self._raf = window.requestAnimationFrame(create_proxy(run))

    # ── 마우스 · 손가락 ──
    def _bind(self):
        svg = self.svg

        def wheel(e):
            e.preventDefault()
            x, y = self.to_plan(e.clientX, e.clientY)
            self.zoom_by(math.exp(-e.deltaY * (0.01 if e.ctrlKey else 0.0015)), x, y)

        def down(e):
            if e.pointerType == "mouse" and e.button != 0:
                return
            svg.setPointerCapture(e.pointerId)
            self._pointers[e.pointerId] = (e.clientX, e.clientY)
            if len(self._pointers) == 1:
                self._drag = {"sx": e.clientX, "sy": e.clientY, "view": list(self.view), "moved": False, "target": e.target}
            elif len(self._pointers) == 2:
                (ax, ay), (bx, by) = list(self._pointers.values())[:2]
                self._pinch = {"dist": math.hypot(ax - bx, ay - by), "view": list(self.view)}
                self._drag = None

        def move(e):
            if e.pointerId not in self._pointers:
                return
            self._pointers[e.pointerId] = (e.clientX, e.clientY)
            r = svg.getBoundingClientRect()
            if self._pinch and len(self._pointers) == 2:
                (ax, ay), (bx, by) = list(self._pointers.values())[:2]
                dist = math.hypot(ax - bx, ay - by)
                mx, my = self.to_plan((ax + bx) / 2, (ay + by) / 2)
                vx, vy, vw, vh = self._pinch["view"]
                k = self._pinch["dist"] / max(1, dist)
                self.view = [mx - (mx - vx) * k, my - (my - vy) * k, vw * k, vh * k]
                self._schedule()
            elif self._drag:
                dx, dy = e.clientX - self._drag["sx"], e.clientY - self._drag["sy"]
                if math.hypot(dx, dy) > 4:
                    self._drag["moved"] = True
                    svg.classList.add("is-panning")
                if self._drag["moved"]:
                    vx, vy, vw, vh = self._drag["view"]
                    s = max(vw / r.width, vh / r.height)
                    self.view = [vx - dx * s, vy - dy * s, vw, vh]
                    self._schedule()

        def up(e):
            if e.pointerId not in self._pointers:
                return
            del self._pointers[e.pointerId]
            if self._drag and not self._drag["moved"] and e.type == "pointerup" and self.on_tap:
                x, y = self.to_plan(e.clientX, e.clientY)
                self.on_tap(x, y, self._drag["target"])
            if len(self._pointers) < 2:
                self._pinch = None
            if not self._pointers:
                self._drag = None
            svg.classList.remove("is-panning")

        on(svg, "wheel", wheel, passive=False)
        on(svg, "pointerdown", down)
        on(svg, "pointermove", move)
        on(svg, "pointerup", up)
        on(svg, "pointercancel", up)

    # ── 핀 · 건물 ──
    def scale_markers(self):
        """핀과 이름표가 확대해도 화면에서 같은 크기로 보이게."""
        u = self.units_per_px
        for g in document.querySelectorAll(".pin, .draft-pin, .bld-label"):
            if self.svg.contains(g):
                g.setAttribute("transform", f"translate({g.dataset.x} {g.dataset.y}) scale({u})")

    def draw_pins(self, reports, selected=None):
        layer = self.layers["pins"]
        layer.innerHTML = ""
        sev_order = list(SEVERITIES)

        def order(r):  # 처리 끝난 신고는 아래, 급한 신고는 위에 그린다
            done = r["status"] in ("done", "rejected")
            return (r["id"] == selected, not done, -sev_order.index(r["severity"]) if r["severity"] in sev_order else 0)

        for r in sorted(reports, key=order):
            done = r["status"] in ("done", "rejected")
            color = SEVERITIES.get(r["severity"], ("", "#ca8a04"))[1]
            g = el("g", cls="pin" + (" done" if done else "") + (" is-selected" if r["id"] == selected else ""))
            g.dataset.id = r["id"]
            g.dataset.x = r["x"]
            g.dataset.y = r["y"]
            g.style.color = color
            mark = ('<path d="M-4.5-18.5l3 3 6-6" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
                    if done else '<circle class="core" cy="-18.5" r="4.5"/>')
            g.innerHTML = (f'<circle class="halo" cy="-18.5" r="17"/><path class="drop" d="{PIN_PATH}" fill="{color}"/>'
                           f'{mark}<title>{esc(r["title"])}</title>')
            layer.appendChild(g)
        self.scale_markers()

    def draw_draft(self, point):
        layer = self.layers["draft"]
        layer.innerHTML = ""
        if point:
            g = el("g", cls="draft-pin")
            g.dataset.x, g.dataset.y = point
            g.innerHTML = f'<circle class="ring" r="14"/><path class="drop" d="{PIN_PATH}"/><circle cy="-18.5" r="4.5" fill="#fff"/>'
            layer.appendChild(g)
        self.scale_markers()

    def draw_buildings(self, counts=None):
        """배치도 위에 건물 영역과 이름표를 그린다. counts: {건물 id: 처리 전 신고 수}"""
        layer = self.layers["overlay"]
        layer.innerHTML = ""
        for b in BUILDINGS:
            if not b.polys:
                continue
            g = el("g", cls="bld")
            g.dataset.building = b.id
            g.style.setProperty("--c", b.color)
            for poly in b.polys:
                g.appendChild(el("path", {"d": "M" + "L".join(f"{x},{y}" for x, y in poly) + "Z"}))
            t = el("title")
            t.textContent = f"{b.name} ({b.dong}) — 눌러서 층별 평면도 보기"
            g.appendChild(t)
            layer.appendChild(g)
        for b in BUILDINGS:
            if not b.polys:
                continue
            xs = [p[0] for p in b.polys[0]]
            ys = [p[1] for p in b.polys[0]]
            g = el("g", cls="bld-label")
            g.style.setProperty("--c", b.color)
            g.dataset.x = (min(xs) + max(xs)) / 2
            g.dataset.y = (min(ys) + max(ys)) / 2
            w = len(b.name) * 12.5 + 18
            n = (counts or {}).get(b.id, 0)
            g.innerHTML = (f'<rect x="{-w / 2}" y="-11" width="{w}" height="22" rx="11"/><text font-size="12.5">{esc(b.name)}</text>'
                           + (f'<circle class="count-bg" cx="{w / 2}" cy="-10" r="9"/>'
                              f'<text class="count" x="{w / 2}" y="-10" font-size="10.5">{n}</text>' if n else ""))
            layer.appendChild(g)
        self.scale_markers()

    def clear_overlay(self):
        self.layers["overlay"].innerHTML = ""
