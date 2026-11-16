# 벡터 도면 뷰어: <svg> 의 viewBox 를 바꿔서 확대/이동한다.
# (그림을 키우는 게 아니라 벡터를 다시 그려서, 확대해도 선과 글자가 흐려지지 않는다)
import math  # 거리·지수 계산 도구 (손가락 두 개 사이 거리, 휠 확대 비율)
import re  # 글자 패턴 도구 — 도면 파일에서 크기(viewBox)를 읽는다

from js import DOMPoint, ResizeObserver, document, window  # 브라우저 기능: 좌표 변환, 크기 변화 감지, 문서, 창
from pyodide.ffi import create_proxy  # 파이썬 함수를 브라우저가 부를 수 있게 감싸는 도구
from pyodide.http import pyfetch  # 도면 파일을 인터넷으로 받아오는 도구

from campus import BUILDINGS, KINDS, SEVERITIES, kind_of  # 건물 목록, 신고 종류·위험도 이름표
from common import esc, on  # 글자를 안전하게 바꾸는 함수, 이벤트 연결 함수

NS = "http://www.w3.org/2000/svg"  # SVG 요소를 만들 때 쓰는 이름표(네임스페이스)
ROOM = 1.3       # 도면 크기의 130% 까지만 멀어지고, 그 밖으로는 끌고 갈 수 없다
MAX_ZOOM = 10    # 가장 멀리 본 것보다 10배까지 가까이
PLANS_VERSION = "2.5.3"  # plans/*.svg 를 고치면 올린다 (브라우저가 옛날 도면을 쓰지 않게)
PIN_PATH = "M0 0C-1.6-5.4-11-9.6-11-18.5a11 11 0 0 1 22 0C11-9.6 1.6-5.4 0 0z"  # 물방울 모양 핀을 그리는 경로
_svg_cache = {}  # 한 번 받은 도면 파일을 보관해서 다시 받지 않게 한다


async def fetch_plan(url):  # 도면 파일을 받아오는 함수
    if url not in _svg_cache:  # 아직 받은 적이 없으면
        res = await pyfetch(f"{url}?v={PLANS_VERSION}")  # 버전 번호를 붙여 서버에서 받는다
        if not res.ok:  # 실패하면
            raise RuntimeError(f"도면을 불러오지 못했어요: {url}")  # 오류를 알린다
        _svg_cache[url] = await res.string()  # 받은 글자를 보관한다
    return _svg_cache[url]  # 도면 글자를 돌려준다


def el(tag, attrs=None, cls=None):  # SVG 요소를 하나 만드는 함수
    e = document.createElementNS(NS, tag)  # 요소를 만든다 (예: circle, g)
    for k, v in (attrs or {}).items():  # 속성들을 하나씩
        e.setAttribute(k, str(v))  # 요소에 붙인다
    if cls:  # 클래스 이름을 줬으면
        e.setAttribute("class", cls)  # 붙인다 (CSS 꾸미기용)
    return e  # 만든 요소를 돌려준다


class PlanViewer:  # 도면을 보여주고 확대·이동·누르기를 처리하는 뷰어
    _count = 0  # 뷰어를 몇 개 만들었는지 (자르기 영역 id 를 겹치지 않게)

    def __init__(self, svg):  # 처음 만들 때 (svg: 화면의 도면 영역)
        self.svg = svg  # 도면 영역
        self.layers = {}  # 층(레이어)별 그룹: 도면, 건물 표시, 표시, 핀, 새 핀
        # 도면 틀 밖으로 삐져나온 선(치수 눈금 등)은 잘라서 안 보이게
        PlanViewer._count += 1  # 뷰어 수를 늘린다
        clip_id = f"plan-clip-{PlanViewer._count}"  # 자르기 영역 이름
        clip = el("clipPath", {"id": clip_id})  # 자르기 영역 요소
        self._clip_rect = el("rect", {"x": 0, "y": 0, "width": 100, "height": 100})  # 자를 네모 (나중에 도면 크기로 바꾼다)
        clip.appendChild(self._clip_rect)  # 네모를 자르기 영역에 넣는다
        svg.appendChild(clip)  # 자르기 영역을 도면 영역에 넣는다
        for name in ("plan", "overlay", "mark", "pins", "draft"):  # 아래에서 위 순서로 레이어를 만든다
            g = el("g", cls=f"layer-{name}")  # 그룹 요소
            svg.appendChild(g)  # 도면 영역에 넣는다
            self.layers[name] = g  # 이름으로 찾을 수 있게 보관한다
        self.layers["plan"].setAttribute("clip-path", f"url(#{clip_id})")  # 도면 레이어에만 자르기를 적용한다
        self.size = (100.0, 100.0)  # 도면 전체 크기 (나중에 바뀜)
        self.bounds = (0.0, 0.0, 100.0, 100.0)  # 실제로 그림이 있는 영역
        self.view = [0.0, 0.0, 100.0, 100.0]  # 지금 보고 있는 영역 (x, y, 가로, 세로)
        self.on_tap = None          # (x, y, 누른 요소) → 도면 좌표로 알려준다
        self.on_view_change = None  # 보는 영역이 바뀔 때 부를 함수
        self.locked = False         # True 면 확대·이동 없이 전체만 보여준다 (캠퍼스 배치도)
        self._token = 0  # 도면을 불러올 때마다 늘어나는 번호 (늦게 온 옛 도면을 무시하려고)
        self._pointers = {}  # 지금 화면을 누르고 있는 손가락·마우스들
        self._drag = None  # 끌기 정보
        self._pinch = None  # 두 손가락 확대 정보
        self._raf = None  # 다음 화면 그리기 예약 번호
        self._raf_proxy = create_proxy(self._run_raf)  # 한 번만 만들어 계속 쓴다 (끌 때마다 새로 만들지 않게)
        self._bind()  # 마우스·손가락 이벤트를 연결한다
        ResizeObserver.new(create_proxy(lambda *a: self.fit() if self.locked else self.apply())).observe(svg)  # 화면 크기가 바뀌면 다시 맞춘다

    # ── 도면 불러오기 ──
    async def load(self, url, locked=False, crop=None):  # 도면을 불러와 보여주는 함수
        """crop=(x0, x1): 도면에서 이 x 범위만 보여준다 (한 장에 두 건물이 있는 층)."""  # 이 함수가 하는 일을 적은 설명글
        self._token += 1  # 새 불러오기 번호
        self.locked = locked  # 고정 여부
        self.svg.classList.toggle("is-locked", locked)  # 고정이면 꾸미기용 표시를 붙인다
        token = self._token  # 이번 불러오기 번호를 기억한다
        self.layers["plan"].innerHTML = ""  # 이전 도면을 지운다
        self.svg.classList.add("is-loading")  # 불러오는 중 표시
        text = await fetch_plan(url)  # 도면 파일을 받는다
        if token != self._token:  # 받는 동안 다른 층을 눌렀으면
            return False  # 그 사이에 다른 층을 눌렀다
        m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', text[:400])  # 도면 크기를 찾는다
        self.size = (float(m.group(1)), float(m.group(2)))  # 가로·세로 크기
        x0, x1 = crop or (0, self.size[0])  # 보여줄 x 범위 (자르지 않으면 전체)
        self._clip_rect.setAttribute("x", x0)  # 자르기 네모 왼쪽
        self._clip_rect.setAttribute("width", x1 - x0)  # 자르기 네모 가로
        self._clip_rect.setAttribute("height", self.size[1])  # 자르기 네모 세로
        inner = text[text.index(">", text.index("<svg")) + 1: text.rindex("</svg>")]  # <svg> 바깥 껍데기를 뺀 안쪽 그림
        self.layers["plan"].innerHTML = inner  # 도면 레이어에 그림을 넣는다
        self.svg.classList.remove("is-loading")  # 불러오는 중 표시를 뗀다
        self.bounds = self._content_box(x0, x1)  # 실제 그림이 있는 영역을 계산한다
        self.fit()  # 그 영역이 화면에 꽉 차게 맞춘다
        return True  # 성공

    def _content_box(self, cx0=0.0, cx1=None):  # 그림이 실제로 있는 영역을 계산하는 함수
        """도면 안에서 선·글자가 실제로 있는 영역 (화면에 안 보일 때는 도면 전체).
        cx0~cx1 로 잘라 보여줄 때는 그 안에 있는 그림만 센다."""
        W, H = self.size  # 도면 전체 크기
        cx1 = W if cx1 is None else cx1  # 오른쪽 끝을 안 줬으면 도면 끝
        try:  # 화면에 안 보이면 계산이 실패할 수 있어서 시도한다
            if cx0 > 0 or cx1 < W:  # 도면 일부만 보여줄 때
                xs, ys = [], []  # 그림들의 x 좌표들, y 좌표들
                for e in self.layers["plan"].querySelectorAll("path, rect, text, line, polyline, polygon"):  # 도면 안의 그림 요소를 하나씩
                    b = e.getBBox()  # 그 요소를 둘러싼 네모
                    if b.width * b.height == 0 and b.width + b.height == 0:  # 크기가 전혀 없는 요소면
                        continue  # 건너뛴다
                    # 경계에 걸친 그림(복도·바깥 벽처럼 두 건물에 이어진 것)도 잘린 부분만큼 센다
                    lx, rx = max(cx0, b.x), min(cx1, b.x + b.width)  # 보여줄 범위 안에 들어오는 부분의 왼쪽·오른쪽
                    if rx - lx > 0.5 or (b.width == 0 and cx0 <= b.x <= cx1):  # 범위 안에 조금이라도 들어오면 (세로선 포함)
                        xs += [lx, rx]  # x 좌표를 모은다
                        ys += [b.y, b.y + b.height]  # y 좌표를 모은다
                if xs:  # 모은 게 있으면
                    x0, x1 = max(cx0, min(xs)), min(cx1, max(xs))  # 가장 왼쪽·오른쪽
                    y0, y1 = max(0, min(ys)), min(H, max(ys))  # 가장 위·아래
                    return (x0, y0, x1 - x0, y1 - y0)  # 그 네모를 돌려준다
                return (cx0, 0.0, cx1 - cx0, H)  # 모은 게 없으면 보여줄 범위 전체
            b = self.layers["plan"].getBBox()  # 도면 전체 그림을 둘러싼 네모
            x0, y0 = max(0, b.x), max(0, b.y)  # 도면 밖으로 나가지 않게 왼쪽 위
            x1, y1 = min(W, b.x + b.width), min(H, b.y + b.height)  # 도면 밖으로 나가지 않게 오른쪽 아래
            if x1 - x0 > W * 0.2 and y1 - y0 > H * 0.2:  # 너무 작지 않으면 (계산이 이상하지 않으면)
                return (x0, y0, x1 - x0, y1 - y0)  # 그 네모를 쓴다
        except Exception:  # 계산이 실패하면
            pass  # 아래 기본값을 쓴다
        return (cx0, 0.0, cx1 - cx0, H)  # 기본: 보여줄 범위 전체

    # ── 보기 영역 ──
    def fit(self):  # 그림 전체가 화면에 들어오게 맞추는 함수
        bx, by, bw, bh = self.bounds  # 그림 영역
        pad = max(bw, bh) * 0.04  # 가장자리 여백 (4%)
        self.view = [bx - pad, by - pad, bw + pad * 2, bh + pad * 2]  # 여백을 두고 보는 영역을 정한다
        self.apply()  # 화면에 반영한다

    def zoom_by(self, factor, cx=None, cy=None):  # 확대·축소하는 함수 (factor > 1 이면 확대)
        if self.locked:  # 고정된 도면이면
            return  # 아무것도 안 한다
        x, y, w, h = self.view  # 지금 보는 영역
        k = 1 / factor  # 보는 영역을 줄일 비율
        if cx is None:  # 기준점을 안 줬으면
            cx, cy = x + w / 2, y + h / 2  # 화면 가운데를 기준으로
        self.view = [cx - (cx - x) * k, cy - (cy - y) * k, w * k, h * k]  # 기준점은 그대로 두고 영역 크기를 바꾼다
        self.apply()  # 화면에 반영한다

    def focus(self, x, y, width):  # 한 점을 가운데에 두고 보여주는 함수
        r = self.svg.getBoundingClientRect()  # 화면의 도면 영역 크기
        h = width * r.height / max(1, r.width)  # 화면 비율에 맞는 세로 길이
        self.view = [x - width / 2, y - h / 2, width, h]  # 그 점이 가운데가 되게
        self.apply()  # 화면에 반영한다

    @property  # 값처럼 쓴다
    def units_per_px(self):  # 화면 1픽셀이 도면 단위로 얼마인지
        """화면 1px 이 도면 좌표로 얼마인지 (핀 크기를 화면 기준으로 고정할 때 쓴다)."""  # 이 함수가 하는 일을 적은 설명글
        r = self.svg.getBoundingClientRect()  # 화면의 도면 영역 크기
        if not r.width or not r.height:  # 화면에 안 보이면
            return 1  # 기본값
        return max(self.view[2] / r.width, self.view[3] / r.height)  # 보는 영역 ÷ 화면 크기

    def to_plan(self, client_x, client_y):  # 화면 좌표를 도면 좌표로 바꾸는 함수
        p = DOMPoint.new(client_x, client_y).matrixTransform(self.svg.getScreenCTM().inverse())  # 화면 → 도면 변환을 거꾸로 적용
        return p.x, p.y  # 도면 좌표

    def on_drawing(self, x, y, target):  # 누른 곳이 도면 안쪽인지 확인하는 함수
        """(x, y) 가 도면 그림 위인지: 색칠한 바닥을 눌렀거나, 빈 곳이라도 사방이 도면 선으로 둘러싸여 있으면 안쪽.
        도면 둘레의 흰 여백을 누르면 False."""
        if hasattr(target, "closest") and target.closest("#deco"):  # 색칠한 바닥을 눌렀으면
            return True  # 안쪽
        m = self.svg.getScreenCTM()  # 도면 → 화면 변환
        if not m:  # 없으면 (화면에 안 보임)
            return False  # 바깥으로 본다
        p = DOMPoint.new(x, y).matrixTransform(m)  # 누른 도면 좌표를 화면 좌표로
        r = self.svg.getBoundingClientRect()  # 도면 영역의 화면 위치

        def hits(px, py):  # 화면의 한 점에 도면 선이 있는지
            for e in document.elementsFromPoint(px, py):  # 그 점에 있는 요소들을 하나씩
                if e.closest and e.closest(".layer-plan"):  # 도면 레이어의 요소면
                    return True  # 선이 있다
            return False  # 없다

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):  # 오른쪽·왼쪽·아래·위 네 방향으로
            d, found = 3, False  # 3픽셀부터 찾기 시작, 아직 못 찾음
            while True:  # 찾을 때까지 계속
                px, py = p.x + dx * d, p.y + dy * d  # 그 방향으로 d 만큼 떨어진 점
                if not (r.left <= px <= r.right and r.top <= py <= r.bottom):  # 도면 영역을 벗어나면
                    break  # 그 방향은 못 찾음
                if hits(px, py):  # 도면 선을 만나면
                    found = True  # 찾음
                    break  # 그만 찾는다
                d += 4  # 4픽셀 더 멀리
            if not found:  # 한 방향이라도 선이 없으면
                return False  # 바깥 여백
        return True  # 네 방향 모두 선으로 둘러싸여 있으면 안쪽

    def apply(self):  # 보는 영역을 화면에 반영하는 함수 (한계도 지킨다)
        r = self.svg.getBoundingClientRect()  # 화면의 도면 영역 크기
        x, y, w, h = self.view  # 원하는 보는 영역
        if r.width and r.height:  # 화면에 보일 때만
            aspect = r.width / r.height  # 화면 가로세로 비율
            # 화면 비율에 맞춰 viewBox 를 맞춘다 (클릭 좌표가 어긋나지 않게)
            if w / h > aspect:  # 보는 영역이 화면보다 납작하면
                nh = w / aspect  # 세로를 늘린다
                y -= (nh - h) / 2  # 위아래로 똑같이
                h = nh  # 새 세로
            else:  # 화면보다 길쭉하면
                nw = h * aspect  # 가로를 늘린다
                x -= (nw - w) / 2  # 양옆으로 똑같이
                w = nw  # 새 가로
            # 확대·축소 한계: 도면의 130% 가 화면에 꽉 차는 것보다 멀리는 못 간다
            bx, by, bw, bh = self.bounds  # 그림 영역
            rx, ry, rw, rh = bx - bw * (ROOM - 1) / 2, by - bh * (ROOM - 1) / 2, bw * ROOM, bh * ROOM  # 그림의 130% 영역
            max_w = max(rw, rh * aspect)  # 가장 멀리 볼 때의 가로
            nw = min(max_w, max(max_w / MAX_ZOOM, w))  # 가로를 최소~최대 사이로 맞춘다
            if nw != w:  # 한계를 넘었으면
                cx, cy = x + w / 2, y + h / 2  # 가운데는 그대로 두고
                w, h = nw, nw / aspect  # 크기를 고친다
                x, y = cx - w / 2, cy - h / 2  # 새 왼쪽 위
            # 이동 한계: 130% 영역 밖으로 끌고 갈 수 없다
            x = rx + (rw - w) / 2 if w >= rw else min(max(x, rx), rx + rw - w)  # 가로 위치를 영역 안으로
            y = ry + (rh - h) / 2 if h >= rh else min(max(y, ry), ry + rh - h)  # 세로 위치를 영역 안으로
        self.view = [x, y, w, h]  # 고친 보는 영역을 저장한다
        self.svg.setAttribute("viewBox", f"{x} {y} {w} {h}")  # 화면에 반영한다
        if self.on_view_change:  # 알려줄 함수가 있으면
            self.on_view_change()  # 부른다

    def _schedule(self):  # 다음 화면 그리기 때 반영하도록 예약하는 함수 (끌 때 버벅이지 않게)
        if self._raf is None:  # 아직 예약이 없으면
            self._raf = window.requestAnimationFrame(self._raf_proxy)  # 예약한다

    def _run_raf(self, *_):  # 예약한 때가 되면 불리는 함수
        self._raf = None  # 예약을 비운다
        self.apply()  # 화면에 반영한다

    # ── 마우스 · 손가락 ──
    def _bind(self):  # 마우스·손가락 이벤트를 연결하는 함수
        svg = self.svg  # 도면 영역

        def wheel(e):  # 마우스 휠을 굴렸을 때
            if self.locked:  # 고정된 도면이면
                return  # 아무것도 안 한다
            e.preventDefault()  # 페이지가 스크롤되지 않게 막는다
            x, y = self.to_plan(e.clientX, e.clientY)  # 마우스 위치를 도면 좌표로
            self.zoom_by(math.exp(-e.deltaY * (0.01 if e.ctrlKey else 0.0015)), x, y)  # 휠 양만큼 마우스 위치를 기준으로 확대·축소

        def down(e):  # 누르기 시작했을 때
            if e.pointerType == "mouse" and e.button != 0:  # 마우스 왼쪽 버튼이 아니면
                return  # 무시
            svg.setPointerCapture(e.pointerId)  # 영역 밖으로 나가도 계속 이벤트를 받게 한다
            self._pointers[e.pointerId] = (e.clientX, e.clientY)  # 누른 위치를 기억한다
            if len(self._pointers) == 1:  # 하나만 누르고 있으면 (끌기 또는 누르기)
                self._drag = {"sx": e.clientX, "sy": e.clientY, "view": list(self.view), "moved": False, "target": e.target}  # 시작 위치·보는 영역·누른 요소를 기억
            elif len(self._pointers) == 2 and not self.locked:  # 두 손가락이면 (확대)
                (ax, ay), (bx, by) = list(self._pointers.values())[:2]  # 두 손가락 위치
                self._pinch = {"dist": math.hypot(ax - bx, ay - by), "view": list(self.view)}  # 처음 거리와 보는 영역을 기억
                self._drag = None  # 끌기는 취소

        def move(e):  # 누른 채로 움직일 때
            if e.pointerId not in self._pointers:  # 누르고 있지 않은 포인터면
                return  # 무시
            self._pointers[e.pointerId] = (e.clientX, e.clientY)  # 새 위치를 기억한다
            r = svg.getBoundingClientRect()  # 도면 영역 크기
            if self._pinch and len(self._pointers) == 2:  # 두 손가락 확대 중이면
                (ax, ay), (bx, by) = list(self._pointers.values())[:2]  # 두 손가락 위치
                dist = math.hypot(ax - bx, ay - by)  # 지금 거리
                mx, my = self.to_plan((ax + bx) / 2, (ay + by) / 2)  # 두 손가락 가운데의 도면 좌표
                vx, vy, vw, vh = self._pinch["view"]  # 시작할 때 보는 영역
                k = self._pinch["dist"] / max(1, dist)  # 거리가 벌어진 만큼 영역을 줄인다
                self.view = [mx - (mx - vx) * k, my - (my - vy) * k, vw * k, vh * k]  # 가운데를 기준으로 확대·축소
                self._schedule()  # 화면 반영을 예약한다
            elif self._drag:  # 끌기 중이면
                dx, dy = e.clientX - self._drag["sx"], e.clientY - self._drag["sy"]  # 처음 누른 곳에서 움직인 거리
                if math.hypot(dx, dy) > 4:  # 4픽셀 넘게 움직였으면
                    self._drag["moved"] = True  # 누르기가 아니라 끌기로 본다
                    if not self.locked:  # 고정이 아니면
                        svg.classList.add("is-panning")  # 끄는 중 표시 (손 모양 커서)
                if self._drag["moved"] and not self.locked:  # 끄는 중이면
                    vx, vy, vw, vh = self._drag["view"]  # 시작할 때 보는 영역
                    s = max(vw / r.width, vh / r.height)  # 화면 1픽셀 = 도면 몇 단위
                    self.view = [vx - dx * s, vy - dy * s, vw, vh]  # 움직인 만큼 반대로 영역을 옮긴다
                    self._schedule()  # 화면 반영을 예약한다

        def up(e):  # 손을 뗐을 때 (또는 취소됐을 때)
            if e.pointerId not in self._pointers:  # 누르고 있지 않은 포인터면
                return  # 무시
            del self._pointers[e.pointerId]  # 목록에서 뺀다
            if self._drag and not self._drag["moved"] and e.type == "pointerup" and self.on_tap:  # 거의 안 움직이고 뗐으면 = 누르기
                x, y = self.to_plan(e.clientX, e.clientY)  # 누른 곳의 도면 좌표
                self.on_tap(x, y, self._drag["target"])  # 누르기를 알린다
            if len(self._pointers) < 2:  # 손가락이 하나 이하로 줄면
                self._pinch = None  # 확대 끝
            if not self._pointers:  # 다 뗐으면
                self._drag = None  # 끌기 끝
            svg.classList.remove("is-panning")  # 끄는 중 표시를 뗀다

        on(svg, "wheel", wheel, passive=False)  # 휠 이벤트 연결 (기본 스크롤을 막을 수 있게)
        on(svg, "pointerdown", down)  # 누르기 시작 연결
        on(svg, "pointermove", move)  # 움직임 연결
        on(svg, "pointerup", up)  # 떼기 연결
        on(svg, "pointercancel", up)  # 취소도 떼기처럼 처리

    # ── 핀 · 건물 ──
    def scale_markers(self):  # 핀·이름표 크기를 화면 기준으로 맞추는 함수
        """핀과 이름표가 확대해도 화면에서 같은 크기로 보이게."""  # 이 함수가 하는 일을 적은 설명글
        u = self.units_per_px  # 화면 1픽셀 = 도면 몇 단위
        for g in document.querySelectorAll(".pin, .draft-pin, .bld-label, .link, .hit"):  # 핀·새 핀·건물 이름표·연결 버튼·검색 표시를
            if self.svg.contains(g):  # 이 뷰어 안에 있는 것만
                g.setAttribute("transform", f"translate({g.dataset.x} {g.dataset.y}) scale({u})")  # 제자리로 옮기고 크기를 화면 기준으로 맞춘다

    def draw_pins(self, reports, selected=None):  # 신고 핀들을 그리는 함수
        layer = self.layers["pins"]  # 핀 레이어
        layer.innerHTML = ""  # 이전 핀을 지운다
        sev_order = list(SEVERITIES)  # 위험도 순서 (긴급 → 낮음)

        def order(r):  # 처리 끝난 신고는 아래, 급한 신고는 위에 그린다
            done = r["status"] in ("done", "rejected")  # 처리가 끝났는지
            return (r["id"] == selected, not done, -sev_order.index(r["severity"]) if r["severity"] in sev_order else 0)  # 선택한 신고 → 처리 전 → 급한 것 순으로 나중에(위에) 그린다

        for r in sorted(reports, key=order):  # 그릴 순서대로 신고를 하나씩
            done = r["status"] in ("done", "rejected")  # 처리가 끝났는지
            # 불편 신고는 보라색, 위험 신고는 위험도 색
            color = KINDS[kind_of(r)][2] or SEVERITIES.get(r["severity"], ("", "#ca8a04"))[1]  # 핀 색
            g = el("g", cls="pin" + (" done" if done else "") + (" is-selected" if r["id"] == selected else ""))  # 핀 그룹 (상태별 꾸미기 표시)
            g.dataset.id = r["id"]  # 신고 번호 (눌렀을 때 찾으려고)
            g.dataset.x = r["x"]  # 핀 위치 x
            g.dataset.y = r["y"]  # 핀 위치 y
            g.style.color = color  # 핀 색
            mark = ('<path d="M-4.5-18.5l3 3 6-6" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'  # 처리 끝 = 흰 체크 표시
                    if done else '<circle class="core" cy="-18.5" r="4.5"/>')  # 처리 전 = 흰 동그라미
            g.innerHTML = (f'<circle class="halo" cy="-18.5" r="17"/><path class="drop" d="{PIN_PATH}" fill="{color}"/>'  # 누르기 쉬운 넓은 원 + 물방울 핀
                           f'{mark}<title>{esc(r["title"])}</title>')  # 표시 + 마우스를 올리면 보이는 제목
            layer.appendChild(g)  # 레이어에 넣는다
        self.scale_markers()  # 크기를 맞춘다

    def draw_draft(self, point):  # 신고하려고 찍은 자리에 새 핀을 그리는 함수
        layer = self.layers["draft"]  # 새 핀 레이어
        layer.innerHTML = ""  # 이전 것을 지운다
        if point:  # 찍은 자리가 있으면
            g = el("g", cls="draft-pin")  # 새 핀 그룹
            g.dataset.x, g.dataset.y = point  # 위치
            g.innerHTML = f'<circle class="ring" r="14"/><path class="drop" d="{PIN_PATH}"/><circle cy="-18.5" r="4.5" fill="#fff"/>'  # 퍼지는 원 + 핀 + 흰 점
            layer.appendChild(g)  # 레이어에 넣는다
        self.scale_markers()  # 크기를 맞춘다

    def draw_buildings(self, counts=None):  # 캠퍼스 배치도 위에 건물을 그리는 함수
        """배치도 위에 건물 영역과 이름표를 그린다. counts: {건물 id: 처리 전 신고 수}"""  # 이 함수가 하는 일을 적은 설명글
        layer = self.layers["overlay"]  # 건물 표시 레이어
        layer.innerHTML = ""  # 이전 것을 지운다
        for b in BUILDINGS:  # 건물을 하나씩
            if not b.polys:  # 윤곽이 없으면 (위치 미표시)
                continue  # 건너뛴다
            g = el("g", cls="bld")  # 건물 그룹
            g.dataset.building = b.id  # 건물 id (눌렀을 때 찾으려고)
            g.style.setProperty("--c", b.color)  # 건물 색
            for poly in b.polys:  # 윤곽마다
                g.appendChild(el("path", {"d": "M" + "L".join(f"{x},{y}" for x, y in poly) + "Z"}))  # 꼭짓점을 이은 도형을 넣는다
            t = el("title")  # 마우스를 올리면 보이는 설명
            t.textContent = f"{b.name} ({b.dong}) — 눌러서 층별 평면도 보기"  # 설명 글
            g.appendChild(t)  # 그룹에 넣는다
            layer.appendChild(g)  # 레이어에 넣는다
        for b in BUILDINGS:  # 이름표는 건물 위에 오도록 따로 한 번 더
            if not b.polys:  # 윤곽이 없으면
                continue  # 건너뛴다
            xs = [p[0] for p in b.polys[0]]  # 첫 윤곽의 x 들
            ys = [p[1] for p in b.polys[0]]  # 첫 윤곽의 y 들
            g = el("g", cls="bld-label")  # 이름표 그룹
            g.style.setProperty("--c", b.color)  # 건물 색
            g.dataset.x = (min(xs) + max(xs)) / 2  # 가운데 x
            g.dataset.y = (min(ys) + max(ys)) / 2  # 가운데 y
            w = len(b.name) * 12.5 + 18  # 이름 길이에 맞는 이름표 너비
            n = (counts or {}).get(b.id, 0)  # 이 건물의 처리 전 신고 수
            g.innerHTML = (f'<rect x="{-w / 2}" y="-11" width="{w}" height="22" rx="11"/><text font-size="12.5">{esc(b.name)}</text>'  # 둥근 네모 + 건물 이름
                           + (f'<circle class="count-bg" cx="{w / 2}" cy="-10" r="9"/>'  # 신고가 있으면 오른쪽 위에 빨간 원
                              f'<text class="count" x="{w / 2}" y="-10" font-size="10.5">{n}</text>' if n else ""))  # 그 안에 신고 수
            layer.appendChild(g)  # 레이어에 넣는다
        self.scale_markers()  # 크기를 맞춘다

    def clear_overlay(self):  # 건물 표시·연결 버튼을 지우는 함수
        self.layers["overlay"].innerHTML = ""  # 레이어를 비운다

    def draw_links(self, links):  # 연결복도 버튼을 그리는 함수
        """연결복도 버튼. links: [(x, y, 갈 층 id, 글자)]"""  # 이 함수가 하는 일을 적은 설명글
        layer = self.layers["overlay"]  # 버튼 레이어
        layer.innerHTML = ""  # 이전 것을 지운다
        W = self.size[0]  # 도면 가로 크기
        for x, y, target, label in links:  # 버튼을 하나씩
            g = el("g", cls="link")  # 버튼 그룹
            g.dataset.x, g.dataset.y = x, y  # 위치
            g.dataset.target = target  # 누르면 갈 층
            w = len(label) * 11.5 + 34  # 글자 길이에 맞는 버튼 너비
            # 도면 가장자리 버튼은 안쪽으로 펼쳐서 화면 밖·층 버튼 뒤로 숨지 않게
            side = "left" if x < W * 0.2 else "right" if x > W * 0.8 else "mid"  # 왼쪽 끝·오른쪽 끝·가운데 중 어디인지
            x0 = {"left": -8, "right": 8 - w, "mid": -w / 2}[side]  # 버튼 왼쪽 시작 위치
            if side == "left":  # 왼쪽 끝이면
                arrow, tx = f'M{x0 + 19},-4l-5,4 5,4', x0 + w / 2 + 6  # 왼쪽 화살표, 글자는 조금 오른쪽
            else:  # 그 밖이면
                arrow, tx = f'M{x0 + w - 19},-4l5,4-5,4', x0 + w / 2 - 6  # 오른쪽 화살표, 글자는 조금 왼쪽
            g.innerHTML = (f'<rect x="{x0}" y="-13" width="{w}" height="26" rx="13"/>'  # 둥근 버튼 바탕
                           f'<path class="arrow" d="{arrow}" />'  # 화살표
                           f'<text x="{tx}" font-size="12">{esc(label)}</text>'  # 갈 곳 이름
                           f'<title>{esc(label)}(으)로 가기</title>')  # 마우스를 올리면 보이는 설명
            layer.appendChild(g)  # 레이어에 넣는다
        self.scale_markers()  # 크기를 맞춘다

    def draw_hit(self, point):  # 검색으로 찾은 곳을 표시하는 함수
        """검색으로 찾은 곳을 잠깐 동그라미로 알려준다."""  # 이 함수가 하는 일을 적은 설명글
        layer = self.layers["mark"]  # 표시 레이어
        layer.innerHTML = ""  # 이전 것을 지운다
        if point:  # 찾은 곳이 있으면
            g = el("g", cls="hit")  # 표시 그룹
            g.dataset.x, g.dataset.y = point  # 위치
            g.innerHTML = '<circle class="wave" r="26"/><circle class="ring" r="26"/>'  # 퍼지는 물결 + 고리
            layer.appendChild(g)  # 레이어에 넣는다
        self.scale_markers()  # 크기를 맞춘다
