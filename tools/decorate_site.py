"""전체 배치도(plans/site.svg)를 위성사진처럼 꾸민다.

- 선을 진하게 (확대·축소해도 화면에서 같은 굵기)
- 없어진 양궁장 지우기 (체육실동은 남김)
- 도로·운동장·트랙·잔디·중정·주차장·숲·나무 색칠

usage: python tools/decorate_site.py   (build_plans.py 다음에 실행. 여러 번 실행해도 결과는 같다)
필요: pip install shapely
"""
import math
import os
import random
import re

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "plans", "site.svg")

# 도면은 남쪽이 위 (위성사진을 180° 돌린 방향)
ARCHERY = (180, 228, 322, 266)        # 양궁장: 이 안의 선·글자는 모두 지운다
ARCHERY_EDGE = (322, 228, 342, 266)   # 체육실동과 겹치는 곳: 양궁장 점무늬(아주 작은 조각)만 지운다
# 도면 글씨를 지우고 웹 글꼴로 다시 쓰는 곳: (지울 영역, 글자, 가운데 좌표, 크기)
RETEXT = [((231, 383, 277, 394), "대운동장", (254, 389), 17)]
FONT = "Pretendard, 'Malgun Gothic', sans-serif"

LINE = {"l": ("#475569", 0.6), "m": ("#1e293b", 1.0), "w": ("#0f172a", 1.7)}  # 색, 화면 px 굵기
TEXT = "#0f172a"

C = {
    "campus": "#f6f2e9", "road": "#d5dae1", "dirt": "#eadbbd", "track": "#d9b38c",
    "turf": "#7dbb67", "turf2": "#74b25e", "lawn": "#c3e1aa", "path": "#efe4cb",
    "forest": "#b5d69b", "tree": "#79b05f", "tree2": "#5f9a49", "park": "#cfd5dc", "court": "#9cc0dc",
}

ROAD_SEEDS = [(300, 3), (590, 60), (697, 450), (400, 667)]
CAMPUS_SEED = (470, 600)


# ── SVG 읽기 ─────────────────────────────────────
def attrs_of(tag):
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))


def subpaths(d):
    return [s for s in re.split(r"(?=M)", d) if s]


def nums(s):
    return [float(v) for v in re.findall(r"-?\d*\.?\d+", s)]


def points(sub):
    """하위 경로의 점들 (곡선은 몇 점으로 나눠 근사)."""
    pts = []
    for cmd, args in re.findall(r"([MLCZ])([^MLCZ]*)", sub):
        v = nums(args)
        if cmd in "ML":
            pts += list(zip(v[0::2], v[1::2]))
        elif cmd == "C":
            for i in range(0, len(v) - 5, 6):
                p0 = pts[-1] if pts else (v[i], v[i + 1])
                c1, c2, p3 = (v[i], v[i + 1]), (v[i + 2], v[i + 3]), (v[i + 4], v[i + 5])
                for t in (0.25, 0.5, 0.75, 1):
                    u = 1 - t
                    pts.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d
                                     for a, b, c, d in zip(p0, c1, c2, p3)))
        elif cmd == "Z" and pts:
            pts.append(pts[0])
    return pts


def inside(pts, r):
    return all(r[0] <= x <= r[2] and r[1] <= y <= r[3] for x, y in pts)


def size(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return max(max(xs) - min(xs), max(ys) - min(ys))


# ── 모양 만들기 ───────────────────────────────────
def fmt(v):
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def poly_d(geom):
    out = []
    polys = getattr(geom, "geoms", [geom])
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            c = list(ring.coords)
            out.append("M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in c[:-1]) + "Z")
    return "".join(out)


def fill(geom, color, extra=""):
    return f'<path fill="{color}" d="{poly_d(geom)}"{extra}/>'


def stadium(x0, y0, x1, y1):
    """세로로 긴 트랙 모양 (위아래가 반원)."""
    r = (x1 - x0) / 2
    cx = (x0 + x1) / 2
    top, bot = Point(cx, y0 + r).buffer(r, 48), Point(cx, y1 - r).buffer(r, 48)
    return unary_union([top, bot, box(x0, y0 + r, x1, y1 - r)])


def trees(area, step, r, seed, avoid=None):
    """area 안에 나무(동그라미)를 고르게 흩어 심는다."""
    rnd = random.Random(seed)
    x0, y0, x1, y1 = area.bounds
    out = []
    y = y0 + step / 2
    row = 0
    while y < y1:
        x = x0 + step / 2 + (step / 2 if row % 2 else 0)
        while x < x1:
            px, py = x + rnd.uniform(-step * .3, step * .3), y + rnd.uniform(-step * .3, step * .3)
            if area.contains(Point(px, py)) and not (avoid and avoid.contains(Point(px, py))):
                rr = r * rnd.uniform(.8, 1.2)
                col = C["tree"] if rnd.random() < .6 else C["tree2"]
                out.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(rr)}" fill="{col}" fill-opacity=".9"/>')
            x += step
        y += step * .87
        row += 1
    return out


def row_of_trees(p0, p1, gap, r, seed):
    rnd = random.Random(seed)
    n = max(1, int(math.dist(p0, p1) // gap))
    out = []
    for i in range(n + 1):
        t = i / n
        x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
        col = C["tree"] if rnd.random() < .6 else C["tree2"]
        out.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r * rnd.uniform(.85, 1.15))}" fill="{col}" fill-opacity=".9"/>')
    return out


# ── 실행 ─────────────────────────────────────────
def main():
    s = open(SITE, encoding="utf-8").read()
    s = re.sub(r'<g id="deco">.*?</g>', "", s, flags=re.S)
    head = s[: s.index(">", s.index("<svg")) + 1]
    W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head).groups())

    paths, bold_lines, removed = [], [], 0
    for tag in re.findall(r"<path [^>]*/>", s):
        a = attrs_of(tag)
        cls = a["class"]
        keep = []
        for sub in subpaths(a["d"]):
            pts = points(sub)
            if pts and (inside(pts, ARCHERY) or (cls != "t" and inside(pts, ARCHERY_EDGE) and size(pts) <= 0.6)
                        or (cls == "t" and any(inside(pts, r[0]) for r in RETEXT))):
                removed += 1
                continue
            keep.append(sub)
            if cls == "w" and len(pts) > 1:
                bold_lines.append(LineString(pts))
        if not keep:
            continue
        d = "".join(keep)
        if cls in LINE:
            col, w = LINE[cls]
            paths.append(f'<path class="{cls}" fill="none" stroke="{col}" stroke-width="{w}" vector-effect="non-scaling-stroke" '
                         f'stroke-linecap="round" stroke-linejoin="round" d="{d}"/>')
        else:
            paths.append(f'<path class="{cls}" fill="{TEXT if cls == "t" else a.get("fill", "#d1d5db")}" d="{d}"/>')

    # 굵은 선(담장·도로 경계·건물)으로 나뉜 빈 곳 → 도로, 학교 땅
    # 선끼리 살짝 떨어진 틈은 선을 gap 만큼 두껍게 해서 메운다. 도로가 끝나는 x=100, 768 에는 가상의 벽을 세운다.
    sheet = box(0, 0, W, H)
    walls = bold_lines + [LineString([(x, 0), (x, H)]) for x in (100, 768)]

    def region_at(seeds, gap):
        space = sheet.difference(unary_union([l.buffer(gap) for l in walls]))
        comps = list(getattr(space, "geoms", [space]))
        found = [c for c in comps if any(c.contains(Point(p)) for p in seeds)]
        return unary_union(found).buffer(gap).intersection(sheet) if found else None

    roads = region_at(ROAD_SEEDS, 1.2)
    campus = region_at([CAMPUS_SEED], 3.0)
    print("roads", round(roads.area) if roads else None, "campus", round(campus.area) if campus else None)

    deco = []
    if campus is not None and campus.area < W * H * 0.6:
        deco.append(fill(campus, C["campus"]))
    if roads is not None and roads.area < W * H * 0.2:
        deco.append(fill(roads, C["road"]))

    # 숲: 증축예정부지 + 옛 양궁장 자리 + 담장 옆 (위성사진에서 나무가 빽빽한 곳)
    forest = unary_union([
        Polygon([(161, 193), (161, 48), (168, 47), (237, 28), (240, 24), (351, 24), (351, 73), (357, 90), (358, 193)]),
        box(155, 193, 326, 236),
    ])
    deco.append(fill(forest, C["forest"]))

    # 대운동장: 흙바닥 → 트랙 → 인조잔디 (줄무늬)
    ground = box(155, 236, 331, 628).union(box(326, 266, 340, 545))
    deco.append(fill(ground, C["dirt"]))
    deco.append(fill(stadium(168, 238, 340, 538), C["track"]))
    deco.append(fill(stadium(176, 246, 332, 530), C["dirt"]))
    field = box(178, 267, 330, 508)
    deco.append(fill(field, C["turf"]))
    for i, y in enumerate(range(267, 508, 20)):
        if i % 2:
            deco.append(fill(box(178, y, 330, min(508, y + 20)), C["turf2"]))
    deco.append(fill(box(231, 544, 267, 610), C["court"]))  # 농구장

    # 소운동장
    deco.append(fill(box(402, 210, 552, 295), C["dirt"]))

    # 중정: 잔디 + 십자 길 + 가운데 원
    cx, cy = 573, 431
    yard = box(518, 377, 627, 483)
    deco.append(fill(yard, C["lawn"]))
    paths_geom = unary_union([
        yard.exterior.buffer(3),
        LineString([(518, 377), (627, 483)]).buffer(4.5),
        LineString([(627, 377), (518, 483)]).buffer(4.5),
        Point(cx, cy).buffer(19),
    ]).intersection(yard)
    deco.append(fill(paths_geom, C["path"]))
    deco.append(fill(Point(cx, cy).buffer(11), C["lawn"]))
    deco.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{C["tree2"]}"/>')

    # 주차장
    for b in [(376, 32, 441, 44), (387, 58, 426, 82), (416, 132, 480, 143), (502, 552, 588, 564), (653, 359, 665, 374)]:
        deco.append(fill(box(*b), C["park"]))

    # 나무: 숲 · 담장 · 길가 (위성사진의 나무 줄)
    deco += trees(forest, 9, 4.6, 1)
    deco += trees(Polygon([(140, 60), (154, 60), (154, 628), (138, 628)]), 8, 4, 2)
    deco += row_of_trees((172, 640), (318, 640), 9, 4, 3)
    deco += row_of_trees((676, 380), (684, 600), 10, 3.6, 4)
    deco += trees(box(406, 214, 548, 291), 22, 4.2, 5)
    for (x, y) in [(522, 381), (623, 381), (522, 479), (623, 479)]:
        deco.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{C["tree"]}" fill-opacity=".9"/>')

    texts = [f'<text x="{x}" y="{fmt(y + size * 0.36)}" font-size="{size}" font-weight="800" font-family="{FONT}" '
             f'text-anchor="middle" fill="{TEXT}" stroke="#ffffff" stroke-width="2.4" stroke-linejoin="round" '
             f'paint-order="stroke" letter-spacing="0.5">{word}</text>' for _, word, (x, y), size in RETEXT]
    out = head + '<g id="deco">' + "".join(deco) + "</g>" + "".join(paths) + "".join(texts) + "</svg>"
    open(SITE, "w", encoding="utf-8").write(out)
    print(f"removed {removed} archery pieces, {len(deco)} deco shapes, {len(out) // 1024} KB")


if __name__ == "__main__":
    main()
