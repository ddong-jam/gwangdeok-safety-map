"""층별 평면도(plans/*.svg, 배치도 빼고)를 보기 좋게 꾸민다.

- 교실 이름표 '호수 / 이름 / 반' 에서 가운데 이름(예: 생활수학)을 지운다 → '107 / 1 - 4'
- 글씨를 진하고 굵게
- 바닥 색: 방은 나무색, 복도는 연회색, 화장실(변기·세면대가 있는 방)은 하늘색 타일
- 문(열리는 호)은 나무색, 변기·세면대 같은 위생기구는 파란 선

usage: python tools/decorate_floors.py   (build_plans.py 다음에 실행. 여러 번 실행해도 결과는 같다)
필요: pip install shapely
"""
import glob
import os
import re
import sys

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.geometry import box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decorate_site import attrs_of, fmt, points, poly_d, subpaths  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEXT = "#0b1220"
TEXT_BOLD = 0.2            # 글자 테두리 굵기 (도면 단위) → 글씨가 굵어 보인다
FLOOR = {"room": "#f5ead6", "hall": "#eceff3", "wet": "#dcebf7"}
DOOR = "#b45309"           # 문: 나무색
FIXTURE = "#0369a1"        # 변기·세면대: 파랑
WALL_GAP = 0.9             # 선 사이 이만큼 벌어진 틈은 막힌 것으로 본다 (방 찾기)


# ── 교실 이름표 ─────────────────────────────────────
def text_pieces(tags):
    out = []
    for a in tags:
        if a["class"] != "t":
            continue
        for sub in subpaths(a["d"]):
            p = points(sub)
            if p:
                xs, ys = [q[0] for q in p], [q[1] for q in p]
                out.append((min(xs), min(ys), max(xs), max(ys), sub))
    return out


def label_blocks(ps, pad=2.2, pad_y=7.0):
    """가까운 글자 조각끼리 묶어 이름표 덩어리를 만든다."""
    parent = list(range(len(ps)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    order = sorted(range(len(ps)), key=lambda i: ps[i][0])
    for k, i in enumerate(order):
        a = ps[i]
        for j in order[k + 1:]:
            b = ps[j]
            if b[0] > a[2] + pad:
                break
            if b[1] <= a[3] + pad_y and a[1] <= b[3] + pad_y:
                parent[root(i)] = root(j)
    groups = {}
    for i, p in enumerate(ps):
        groups.setdefault(root(i), []).append(p)
    return list(groups.values())


def text_rows(block, gap=1.4):
    out = []
    for p in sorted(block, key=lambda p: p[1]):
        if out and p[1] <= out[-1]["y1"] + gap:
            out[-1]["p"].append(p)
            out[-1]["y1"] = max(out[-1]["y1"], p[3])
        else:
            out.append({"y0": p[1], "y1": p[3], "p": [p]})
    for r in out:
        r["x0"], r["x1"] = min(p[0] for p in r["p"]), max(p[2] for p in r["p"])
    return out


def is_class_row(r):
    """'1 - 10' 같은 반 표시: 숫자 무리 + (대시나 빈칸) + 숫자 무리."""
    h = r["y1"] - r["y0"]
    if h < 2 or r["x1"] - r["x0"] > 4.5 * h or len(r["p"]) > 10:
        return False
    tall = [p for p in r["p"] if p[3] - p[1] >= 0.2 * h]
    dashes = [p for p in r["p"] if p[3] - p[1] < 0.25 * h and 0.15 * h < p[2] - p[0] < 0.8 * h
              and 0.3 < ((p[1] + p[3]) / 2 - r["y0"]) / h < 0.7]
    groups = []
    for a, b in sorted((p[0], p[2]) for p in tall):
        if groups and a <= groups[-1][1] + 0.9:
            groups[-1][1] = max(groups[-1][1], b)
        else:
            groups.append([a, b])
    if len(groups) < 2:
        return False
    g, i = max((groups[k + 1][0] - groups[k][1], k) for k in range(len(groups) - 1))
    left = [p for p in tall if p[2] <= groups[i][1] + 0.01]
    right = [p for p in tall if p[0] >= groups[i + 1][0] - 0.01]
    span = lambda qs: max(q[3] for q in qs) - min(q[1] for q in qs)
    has_dash = any(groups[i][1] - 0.2 <= d[0] and d[2] <= groups[i + 1][0] + 0.2 for d in dashes)
    return (has_dash or g >= h) and span(left) > 0.6 * h and span(right) > 0.6 * h


def subject_names(tags):
    """지울 글자 조각 (하위 경로 문자열) 집합."""
    drop = set()
    for block in label_blocks(text_pieces(tags)):
        rs = text_rows(block)
        if len(rs) == 3 and is_class_row(rs[2]) and all(r["y1"] - r["y0"] > 2 for r in rs):
            drop.update(p[4] for p in rs[1]["p"])
    return drop


# ── 문 · 위생기구 ───────────────────────────────────
def is_curve(sub):
    return "C" in sub


def closed(pts):
    return len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 0.05 and abs(pts[0][1] - pts[-1][1]) < 0.05


def door_or_fixture(sub, pts):
    """곡선이 들어간 작은 모양: 열린 호 → 문, 닫힌 모양 → 위생기구."""
    if not is_curve(sub) or len(pts) < 3:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    if closed(pts) or sub.rstrip().endswith("Z"):
        return "fixture" if 0.8 < max(w, h) < 8 else None
    return "door" if 2.5 < max(w, h) < 16 else None


def door_closers(sub):
    """문 호의 경첩(원의 중심)에서 양 끝까지 선을 그어 문 자리를 막는다 (방과 복도를 따로 칠하려고)."""
    out = []
    for args in re.findall(r"C([^MLCZ]*)", sub):
        v = [float(x) for x in re.findall(r"-?\d*\.?\d+", args)]
        start = re.findall(r"(-?\d*\.?\d+) (-?\d*\.?\d+)(?=C)", sub)
        if len(v) < 6 or not start:
            continue
        p0 = tuple(map(float, start[0]))
        c1, c2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
        # 중심: p0 에서 (c1-p0) 에 수직인 직선 과 p3 에서 (c2-p3) 에 수직인 직선의 교점
        d1 = (c1[0] - p0[0], c1[1] - p0[1])
        d2 = (c2[0] - p3[0], c2[1] - p3[1])
        det = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(det) < 1e-6:
            continue
        b1 = d1[0] * p0[0] + d1[1] * p0[1]
        b2 = d2[0] * p3[0] + d2[1] * p3[1]
        cx = (b1 * d2[1] - b2 * d1[1]) / det
        cy = (d1[0] * b2 - d2[0] * b1) / det
        out += [LineString([(cx, cy), p0]), LineString([(cx, cy), p3])]
        break
    return out


# ── 바닥 색 ─────────────────────────────────────────
def floor_regions(lines, W, H):
    sheet = box(0, 0, W, H)
    walls = unary_union([l.buffer(WALL_GAP) for l in lines])
    space = sheet.difference(walls)
    out = []
    for r in getattr(space, "geoms", [space]):
        if r.area < 25:
            continue
        minx, miny, maxx, maxy = r.bounds
        if minx <= 0.5 or miny <= 0.5 or maxx >= W - 0.5 or maxy >= H - 0.5:
            continue  # 건물 밖
        if r.area > W * H * 0.6:
            continue
        thick = 2 * r.area / r.length
        if thick < 2.5:
            continue  # 벽 속 같은 가는 틈
        out.append(r)
    return out


def classify(region, fixtures):
    thick = 2 * region.area / region.length
    length = region.length / 2
    inside = sum(1 for f in fixtures if region.contains(f))
    if inside >= 2:
        return "wet"
    if length / thick > 8:
        return "hall" if 12 <= thick < 35 else None  # 폭이 아주 좁고 긴 것은 치수 띠 → 칠하지 않음
    return "room"


def decorate(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r'<g id="deco">.*?</g>', "", s, flags=re.S)
    head = s[: s.index(">", s.index("<svg")) + 1]
    W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head).groups())
    tags = [attrs_of(t) for t in re.findall(r"<path [^>]*/>", s)]

    drop = subject_names(tags)
    lines, fixtures = [], []
    doors_d, fixtures_d = [], []
    out = []
    for a in tags:
        cls = a["class"]
        if cls in ("door", "fixture"):  # 이전 실행에서 나눠 둔 것 → 원래 선으로 되돌려 다시 판단
            cls = "m"
        keep = []
        for sub in subpaths(a["d"]):
            if cls == "t":
                if sub not in drop:
                    keep.append(sub)
                continue
            pts = points(sub)
            kind = door_or_fixture(sub, pts) if cls in ("m", "l", "w") else None
            if kind == "door":
                doors_d.append(sub)
                lines += door_closers(sub)
            elif kind == "fixture":
                fixtures_d.append(sub)
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                fixtures.append(Point((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
            else:
                keep.append(sub)
            if cls in ("w", "m") and len(pts) > 1 and kind != "fixture":
                lines.append(LineString(pts))
        if not keep:
            continue
        d = "".join(keep)
        if cls == "t":
            out.append(f'<path class="t" fill="{TEXT}" stroke="{TEXT}" stroke-width="{TEXT_BOLD}" stroke-linejoin="round" d="{d}"/>')
        elif cls == "h":
            out.append(f'<path class="h" fill="{a.get("fill", "#d1d5db")}" d="{d}"/>')
        else:
            out.append(f'<path class="{cls}" fill="none" stroke="{a["stroke"]}" stroke-linecap="round" '
                       f'stroke-linejoin="round" stroke-width="{a["stroke-width"]}" d="{d}"/>')
    if doors_d:
        out.append(f'<path class="door" fill="none" stroke="{DOOR}" stroke-linecap="round" stroke-width="0.45" d="{"".join(doors_d)}"/>')
    if fixtures_d:
        out.append(f'<path class="fixture" fill="#ffffff" stroke="{FIXTURE}" stroke-width="0.35" d="{"".join(fixtures_d)}"/>')

    deco = []
    regions = floor_regions(lines, W, H)
    by_kind = {}
    for r in regions:
        kind = classify(r, fixtures)
        if kind:
            by_kind.setdefault(kind, []).append(r.buffer(WALL_GAP))
    for kind in ("hall", "room", "wet"):
        if kind in by_kind:
            parts = [g.buffer(0).simplify(0.4) for g in by_kind[kind]]  # 점 수 줄이기 (파일 크기)
            try:
                shape = unary_union(parts)
                d = poly_d(shape)
            except Exception:  # 모양이 꼬여서 합치기 실패 → 하나씩 그린다
                d = "".join(poly_d(g) for g in parts if not g.is_empty)
            deco.append(f'<path fill="{FLOOR[kind]}" fill-rule="evenodd" d="{d}"/>')

    result = head + '<g id="deco">' + "".join(deco) + "</g>" + "".join(out) + "</svg>"
    open(path, "w", encoding="utf-8").write(result)
    counts = {k: len(v) for k, v in by_kind.items()}
    return len(drop), len(doors_d), len(fixtures_d), counts, len(result) // 1024


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for path in sorted(glob.glob(os.path.join(ROOT, "plans", "*.svg"))):
        if os.path.basename(path) == "site.svg":
            continue
        names, doors, fixtures, counts, kb = decorate(path)
        print(f"{os.path.basename(path):12} 이름 조각 {names:4}  문 {doors:3}  기구 {fixtures:3}  바닥 {counts}  {kb} KB")


if __name__ == "__main__":
    main()
