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
# 실제와 맞지 않는 도면 표시: 이 안에 완전히 들어가는 선·글자는 지운다 (위성사진과 비교)
ERASE = [
    (229, 542, 269, 612),    # 농구장 (위성사진에는 없음 — 트랙 끝 흙바닥)
    (250, 0, 296, 15),       # 건축선(도로경계선) 글자·지시선 (위)
    (580, 66, 664, 81),      # 〃 (오른쪽 위)
    (660, 344, 726, 359),    # 〃 (오른쪽)
    (577, 657, 630, 669),    # 〃 (아래)
    (84, 335, 137, 348),     # (인접대지경계선)
    (660, 400, 712, 437),    # 10M 치수선
    (402, 88, 418, 102),     # 높이 105.5
    (483, 128, 499, 138),    # 높이 105.5
    (673, 627, 876, 682),    # 제목 '전체 배치도 · SCALE' 과 동그라미 '1'
    (178, 226, 334, 236),    # 트랙 위를 가로지르는 옛 선
    (178, 212, 185, 266),    # 〃 (세로)
    (154, 260, 346, 269),    # 잔디 위쪽 옛 울타리 선
]
# 도면 글씨를 지우고 웹 글꼴로 다시 쓰는 곳: (지울 영역, 글자, 가운데 좌표, 크기)
RETEXT = [((231, 383, 277, 394), "대운동장", (254, 389), 17),
          ((458, 245, 491, 258), "소운동장", (424, 287), 9)]
FONT = "Pretendard, 'Malgun Gothic', sans-serif"

LINE = {"l": ("#475569", 0.6), "m": ("#1e293b", 1.0), "w": ("#0f172a", 1.7)}  # 색, 화면 px 굵기
TEXT = "#0f172a"

C = {
    "campus": "#f6f2e9", "road": "#d5dae1", "dirt": "#eadbbd", "track": "#d9b38c",
    "turf": "#7dbb67", "turf2": "#74b25e", "lawn": "#c3e1aa", "path": "#efe4cb",
    "sand": "#f1e6cc", "forest": "#b5d69b", "tree": "#79b05f", "tree2": "#5f9a49", "park": "#cfd5dc", "court": "#4f8fbf", "court_key": "#3d7aa8", "court_edge": "#c9b48f",
    "bench": "#b98a5a",
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


def court(cx, cy, w=60, h=30):
    """위에서 본 농구장 (가로로 긴 코트, 양쪽 골대)."""
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    ln = 'fill="none" stroke="#ffffff" stroke-width="0.7"'
    key_w, key_h = w * 0.19, h * 0.4
    out = [fill(box(x0 - 2, y0 - 2, x1 + 2, y1 + 2), C["court_edge"]),
           fill(box(x0, y0, x1, y1), C["court"]),
           fill(box(x0, cy - key_h / 2, x0 + key_w, cy + key_h / 2), C["court_key"]),
           fill(box(x1 - key_w, cy - key_h / 2, x1, cy + key_h / 2), C["court_key"]),
           f'<rect x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(w)}" height="{fmt(h)}" {ln}/>',
           f'<line x1="{fmt(cx)}" y1="{fmt(y0)}" x2="{fmt(cx)}" y2="{fmt(y1)}" {ln}/>',
           f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(h * 0.16)}" {ln}/>']
    for side in (-1, 1):
        ex = x0 if side < 0 else x1                     # 끝선
        kx = ex - side * key_w                         # 자유투 선
        r3 = h * 0.42                                  # 3점 선
        out.append(f'<rect x="{fmt(min(ex, kx))}" y="{fmt(cy - key_h / 2)}" width="{fmt(key_w)}" height="{fmt(key_h)}" {ln}/>')
        out.append(f'<circle cx="{fmt(kx)}" cy="{fmt(cy)}" r="{fmt(key_h / 2)}" {ln}/>')
        sweep = 1 if side < 0 else 0
        out.append(f'<path d="M{fmt(ex)} {fmt(cy - r3)}A{fmt(r3)} {fmt(r3)} 0 0 {sweep} {fmt(ex)} {fmt(cy + r3)}" {ln}/>')
        hx = ex - side * 1.6                           # 골대(백보드 + 링)
        out.append(f'<line x1="{fmt(hx)}" y1="{fmt(cy - 2.4)}" x2="{fmt(hx)}" y2="{fmt(cy + 2.4)}" stroke="#334155" stroke-width="0.9"/>')
        out.append(f'<circle cx="{fmt(hx - side * 1.3)}" cy="{fmt(cy)}" r="1" fill="none" stroke="#ea580c" stroke-width="0.6"/>')
    return out


def benches(points, w=7, h=2.4):
    """위에서 본 벤치 (나무 판)."""
    return [f'<rect x="{fmt(x - w / 2)}" y="{fmt(y - h / 2)}" width="{fmt(w)}" height="{fmt(h)}" rx="0.6" '
            f'fill="{C["bench"]}" stroke="#7c5a3a" stroke-width="0.35"/>' for x, y in points]


SMALL = (402, 210, 552, 295)   # 소운동장 (도면 테두리)


def taegeuk_flag(cx, cy, h):
    """위에서 본 태극기 모양 마당: 흰 바닥 + 가운데 태극 + 네 귀퉁이 괘 (건·곤·감·리)."""
    w = h * 1.5
    out = [f'<rect x="{fmt(cx - w / 2)}" y="{fmt(cy - h / 2)}" width="{fmt(w)}" height="{fmt(h)}" rx="1.5" '
           f'fill="#fbfaf6" stroke="#cbbf9f" stroke-width="0.6"/>']
    r = h / 4
    tilt = math.degrees(math.atan2(2, 3))
    out.append(f'<g transform="translate({fmt(cx)} {fmt(cy)}) rotate({fmt(tilt)})">'
               f'<circle r="{fmt(r)}" fill="#0047a0"/>'
               f'<path fill="#cd2e3a" d="M{fmt(-r)} 0A{fmt(r)} {fmt(r)} 0 0 1 {fmt(r)} 0'
               f'A{fmt(r / 2)} {fmt(r / 2)} 0 0 0 0 0A{fmt(r / 2)} {fmt(r / 2)} 0 0 1 {fmt(-r)} 0Z"/></g>')
    # 괘: (방향, 막대 3개가 끊겼는지) — 건 ☰ 왼쪽 위, 감 ☵ 오른쪽 위, 리 ☲ 왼쪽 아래, 곤 ☷ 오른쪽 아래
    bar_l, bar_t, gap = h / 4, h / 24, h / 48
    for sx, sy, broken in ((-1, -1, (0, 0, 0)), (1, -1, (1, 0, 1)), (-1, 1, (0, 1, 0)), (1, 1, (1, 1, 1))):
        ang = math.atan2(sy * h, sx * w)
        d = h * 0.25 + h / 6 + bar_l * 0.1
        tx, ty = cx + d * math.cos(ang) * 1.12, cy + d * math.sin(ang)
        rot = math.degrees(ang) + 90
        g = [f'<g transform="translate({fmt(tx)} {fmt(ty)}) rotate({fmt(rot)})" fill="#1f2937">']
        for i, br in enumerate(broken):
            y = (i - 1) * (bar_t + gap) - bar_t / 2
            if br:
                half = bar_l / 2 - gap / 2
                g.append(f'<rect x="{fmt(-bar_l / 2)}" y="{fmt(y)}" width="{fmt(half)}" height="{fmt(bar_t)}"/>')
                g.append(f'<rect x="{fmt(gap / 2)}" y="{fmt(y)}" width="{fmt(half)}" height="{fmt(bar_t)}"/>')
            else:
                g.append(f'<rect x="{fmt(-bar_l / 2)}" y="{fmt(y)}" width="{fmt(bar_l)}" height="{fmt(bar_t)}"/>')
        out.append("".join(g) + "</g>")
    return out, box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def pavilion(cx, cy, r):
    """위에서 본 육각 정자 지붕."""
    pts = [(cx + r * math.cos(math.radians(30 + 60 * i)), cy + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    ring = "L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)
    ridges = "".join(f"M{fmt(cx)} {fmt(cy)}L{fmt(x)} {fmt(y)}" for x, y in pts)
    return [f'<path d="M{ring}Z" fill="#9a6a43" stroke="#5b3a22" stroke-width="0.6" stroke-linejoin="round"/>',
            f'<path d="{ridges}" fill="none" stroke="#5b3a22" stroke-width="0.45"/>',
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r * 0.18)}" fill="#c9a227"/>'], Point(cx, cy).buffer(r + 1.5)


def pond():
    """정자 옆 연못 (가장자리 돌, 연잎)."""
    water = unary_union([Point(458, 279).buffer(9), Point(472, 282).buffer(8), Point(484, 278).buffer(6.5),
                         Point(466, 272).buffer(6)]).buffer(1.5).buffer(-1.5)
    out = [fill(water.buffer(1.4), "#a8a29e"), fill(water, "#7cc4e4"), fill(water.buffer(-2.2), "#5fb0d8")]
    rnd = random.Random(7)
    edge = water.exterior
    for i in range(22):
        p = edge.interpolate(i / 22, normalized=True)
        out.append(f'<circle cx="{fmt(p.x)}" cy="{fmt(p.y)}" r="{fmt(rnd.uniform(.9, 1.5))}" fill="#d6d3d1" stroke="#78716c" stroke-width="0.25"/>')
    for x, y in [(456, 280), (461, 284), (474, 280), (470, 286)]:
        out.append(f'<circle cx="{x}" cy="{y}" r="1.5" fill="#4d9a52"/>')
    return out, water.buffer(2.5)


def small_garden():
    x0, y0, x1, y1 = SMALL
    area = box(x0 + 1, y0 + 1, x1 - 1, y1 - 1)
    out = [fill(area, "#d9cfa6")]
    flag, flag_box = taegeuk_flag(486, 237, 40)
    water, water_area = pond()
    pav, pav_area = pavilion(504, 281, 7.5)
    # 돌길: 왼쪽 입구 → 태극기 마당 아래 → 정자
    walk = unary_union([LineString([(x0, 262), (440, 262), (504, 262), (504, 281)]).buffer(2.4),
                        flag_box.buffer(2.5)])
    out.append(fill(walk.intersection(area), C["path"]))
    out += flag + water + pav
    avoid = unary_union([walk, water_area, pav_area, box(405, 280, 444, 294)])
    out += trees(area.buffer(-2), 10, 2.8, 5, avoid=avoid)
    return out


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
            # ERASE 는 굵은 선(담장·도로 경계, class w)은 남긴다 — 지우면 도로 색칠이 새어 나간다
            if pts and (inside(pts, ARCHERY) or (cls != "w" and any(inside(pts, r) for r in ERASE)) or (cls != "t" and inside(pts, ARCHERY_EDGE) and size(pts) <= 0.6)
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
        box(155, 193, 326, 214),
    ])
    deco.append(fill(forest, C["forest"]))

    # 대운동장 (위성사진): 흙바닥 → 잔디 전체를 감싸는 타원 트랙 → 트랙 안 흙 → 위쪽 모래밭 → 인조잔디
    ground = box(155, 214, 331, 628).union(box(326, 214, 342, 560))
    deco.append(fill(ground, C["dirt"]))
    deco.append(fill(stadium(166, 218, 342, 558), C["track"]))
    deco.append(fill(stadium(172, 224, 336, 552), C["dirt"]))
    # 트랙과 골대 사이 (위·아래 끝) 농구장
    deco += court(254, 245)
    deco += court(254, 531)
    field = box(178, 267, 330, 508)
    deco.append(fill(field, C["turf"]))
    for i, y in enumerate(range(267, 508, 20)):
        if i % 2:
            deco.append(fill(box(178, y, 330, min(508, y + 20)), C["turf2"]))

    # 소운동장: 태극기 모양 마당 + 연못 + 정자 (위성사진)
    deco += small_garden()

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
    # 트랙과 야외 화장실(부3동) 사이: 나무 그늘 + 벤치
    rest = box(158, 566, 330, 628).difference(stadium(162, 214, 346, 562))
    deco += benches([(x, 574) for x in range(186, 326, 26)] + [(x, 604) for x in range(199, 326, 26)])
    deco += trees(rest, 12, 4.4, 6, avoid=unary_union([box(178, 571, 330, 577), box(191, 601, 330, 607)]))
    deco += row_of_trees((676, 380), (684, 600), 10, 3.6, 4)
    for (x, y) in [(522, 381), (623, 381), (522, 479), (623, 479)]:
        deco.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{C["tree"]}" fill-opacity=".9"/>')

    texts = [f'<text x="{x}" y="{fmt(y + size * 0.36)}" font-size="{size}" font-weight="800" font-family="{FONT}" '
             f'text-anchor="middle" fill="{TEXT}" stroke="#ffffff" stroke-width="{fmt(min(2.4, size * 0.16))}" stroke-linejoin="round" '
             f'paint-order="stroke" letter-spacing="0.5">{word}</text>' for _, word, (x, y), size in RETEXT]
    out = head + '<g id="deco">' + "".join(deco) + "</g>" + "".join(paths) + "".join(texts) + "</svg>"
    open(SITE, "w", encoding="utf-8").write(out)
    print(f"removed {removed} archery pieces, {len(deco)} deco shapes, {len(out) // 1024} KB")


if __name__ == "__main__":
    main()
