"""층별 평면도(plans/*.svg, 배치도 빼고)를 보기 좋게 꾸민다.

- 교실 이름표 '호수 / 이름 / 반' 에서 가운데 이름(예: 생활수학)을 지운다 → '107 / 1-4'
- 덕린관 교실의 반 표시는 도면 글씨를 지우고 크게 새로 쓴다 (CLASS_TEXT 에서 반 이름을 바꿀 수 있다)
- 다른 방 이름도 크게, 글씨는 진하고 굵게
- 바닥 색: 방은 나무색, 복도는 연회색, 화장실(변기·세면대가 있는 방)은 하늘색 타일
- 문(열리는 호)은 나무색, 변기·세면대 같은 위생기구는 파란 선
- 학생에게 필요 없는 표시는 지운다: 치수선과 숫자, ±0·-280 같은 높이 표시, '홀' (자동으로 찾고, 못 찾는 것은 ERASE 표)

usage: python tools/decorate_floors.py   (build_plans.py 바로 다음에 한 번 실행. 이미 꾸민 도면은 건너뛴다)
필요: pip install shapely
"""
import glob
import os
import re
import sys

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
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
MARK = 'data-deco="floors"'

LABEL_SCALE = 1.5          # 방 이름 글씨 키우기 (배)
NUMBER_SCALE = 1.35        # 교실 호수(101 등) 키우기
MIN_LABEL_H = 4.0          # 이보다 작은 글씨(DN·UP·높이 표시 등)는 그대로 둔다
CLASS_SIZE = 12            # 새로 쓰는 반 표시 글자 크기 (도면 단위)
CLASS_COLOR = "#1d4ed8"    # 반 표시 색 (파랑)
FONT = "Pretendard, 'Malgun Gothic', sans-serif"
# 덕린관 교실 반 표시: 왼쪽 교실(x01호)부터 차례대로
CLASS_TEXT = {
    "b2-1f": [f"1-{n}" for n in range(10, 0, -1)],
    "b2-3f": [f"3-{n}" for n in range(10, 0, -1)],
    "b2-4f": [f"2-{n}" for n in range(9, 0, -1)] + ["자습실"],   # 2-1 자리는 자습실, 나머지는 하나씩 당김
}
# 교실이 아닌 방을 반으로 쓰는 곳: 이 네모 안의 도면 글씨(방 이름)를 지우고 반 표시를 새로 쓴다
RENAME = {
    "b2-2f": [((697, 73, 733, 82), "1-11")],   # 211 공용교실3실 → 1-11
}
# 자동으로 못 찾는 표시를 지울 네모 (x0, y0, x1, y1), 무엇을
#   "all": 네모 안에 통째로 들어 있는 선·글자 모두   "text": 글자만 (KEEP 의 이름표 글자는 남김)
_B3_EDGE = [((928, 75, 941, 195), "all")]            # 오른쪽 끝 치수 눈금
_B9 = [((540, 440, 700, 492), "all"),                 # 아래쪽 치수 숫자 남은 것
       ((0, 0, 1027.84, 60), "all"), ((965, 0, 1027.84, 646.42), "all")]   # 위·오른쪽 치수 눈금 남은 것
_B9_AREA = _B9 + [((465, 545, 505, 646), "all")]     # + 아래쪽 면적표(㎡) 칸
ERASE = {
    "b1-1f": [((370, 83.5, 385, 90.6), "text")],     # '홀 및 복도' → '복도'
    "b2-1f": [((236.5, 148, 242, 151.5), "text"), ((781.5, 109, 789.2, 113.6), "text"), ((247, 163, 259, 169.5), "text")],   # ±0 (모양이 달라 자동으로 못 찾음)
    "b1-4f": [((490, 95, 643, 245), "text"), ((645, 195, 657, 240), "text")],     # 도서관 책장 크기 메모 (2.6X0.45XH1.8 …)
    "b4-1f": [((114, 165, 124, 173), "text"), ((623, 215.5, 633, 223.5), "text")],   # '홀'
    "b8-b1": [((0, 0, 785.34, 50), "all"), ((0, 0, 42, 634.02), "all"),              # 축 번호 동그라미
              ((560, 45, 785.34, 110), "all")],                                       # 치수 눈금 남은 것
    "b8-rf": [((0, 0, 740.94, 42), "all"), ((0, 0, 40, 613.92), "all"),              # 축 번호 동그라미
              ((212, 205, 252, 300), "all"), ((350, 205, 390, 300), "all"), ((488, 205, 528, 300), "all"),
              ((212, 350, 252, 432), "all"), ((350, 350, 390, 432), "all"), ((488, 350, 528, 432), "all")],  # SLOPE 3/100
    "b9-1f": _B9, "b9-2f": _B9_AREA, "b9-3f": _B9_AREA, "b9-4f": _B9_AREA, "b9-5f": _B9_AREA,
    "b3-1f": _B3_EDGE, "b3-3f": [((905, 75, 922, 195), "all")], "b3-4f": [((905, 75, 922, 195), "all")],
    "b3-2f": _B3_EDGE + [((885, 131, 915, 141.5), "text")],                         # + 280
    "b2-b1": [((218, 141, 236, 149), "text"),                                        # '홀' (호~ㄹ)
              ((7.9, 83, 46, 93.6), "all"), ((45, 82.5, 72, 98.5), "all"),           # GL-4,940 · GL-5,507
              ((231, 79, 257.5, 86), "all"), ((238.5, 87, 256, 94.5), "all"),        # GL -3,240
              ((225.5, 80.5, 232.5, 87.5), "all"), ((282, 77.5, 317.2, 89), "all")],  # 표시 동그라미 · GL-2,840
    "b10-1f": [((100, 100, 130, 400), "all"), ((10, 375, 65, 395), "all")],          # 14,000 · 면적표
    "b5-1f": [((100, 438, 112, 495), "all"), ((425, 485, 440, 492), "all")],        # 치수 보조선 남은 것
    "wc-1f": [((340, 600, 400, 636), "all"), ((520, 610, 545, 636), "all")],        # 6,000
}
# ERASE "text" 네모 안이지만 지우지 않을 이름표 (이 네모 안의 큰 글자 조각은 남긴다)
KEEP = {"b1-4f": [(526, 169, 551, 196.5)]}            # 404 도서관


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


def without_hall(ps):
    """'홀' 이름표를 뺀다. 도면에는 '호 - ㄹ' 처럼 벌어진 세 조각(호, 짧은 줄, ㄹ)으로 그려져 있다."""
    drop = set()
    for i, d in enumerate(ps):
        dw, dh = d[2] - d[0], d[3] - d[1]
        if not (1.2 < dw < 3 and dh < 1.2 and dw > 1.8 * dh):
            continue
        cy = (d[1] + d[3]) / 2
        left = [j for j, a in enumerate(ps) if 0 <= d[0] - a[2] < 1.2 and 3.5 < a[3] - a[1] < 5
                and 5 < a[2] - a[0] < 7 and a[1] < cy < a[3]]
        right = [j for j, r in enumerate(ps) if 0 <= r[0] - d[2] < 2.5 and 2.5 < r[3] - r[1] < 4
                 and 3 < r[2] - r[0] < 4.5 and r[1] < cy < r[3]]
        if left and right:
            a, r = ps[left[0]], ps[right[0]]
            x0, y0, x1, y1 = a[0] - 0.2, min(a[1], r[1]) - 1.5, r[2] + 0.2, max(a[3], r[3]) + 0.2
            drop |= {j for j, p in enumerate(ps) if p[0] >= x0 and p[2] <= x1 and p[1] >= y0 and p[3] <= y1}
    return [p for j, p in enumerate(ps) if j not in drop]


def label_blocks(ps, pad=4.5, pad_y=7.0):
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


def bbox(ps):
    return min(p[0] for p in ps), min(p[1] for p in ps), max(p[2] for p in ps), max(p[3] for p in ps)


def scaled(ps, k, to=None, color=TEXT, around=None):
    """글자 조각들을 가운데(around 를 주면 그 덩어리의 가운데)를 기준으로 k 배 키운 path.
    to 를 주면 그 좌표로 옮긴다."""
    x0, y0, x1, y1 = bbox(around or ps)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = to or (cx, cy)
    d = "".join(p[4] for p in ps)
    if k == 1 and not to:
        return f'<path class="t" fill="{color}" stroke="{color}" stroke-width="{TEXT_BOLD}" stroke-linejoin="round" d="{d}"/>'
    return (f'<path class="t" fill="{color}" stroke="{color}" stroke-width="{fmt(TEXT_BOLD / k)}" stroke-linejoin="round" '
            f'transform="matrix({k} 0 0 {k} {fmt(nx - k * cx)} {fmt(ny - k * cy)})" d="{d}"/>')


def x_groups(ps, gap=0.35):
    """한 줄의 글자 조각을 글자(음절) 단위로 묶는다."""
    gs = []
    for p in sorted(ps, key=lambda p: p[0]):
        if gs and p[0] <= gs[-1]["x1"] + gap:
            gs[-1]["p"].append(p)
            gs[-1]["x1"] = max(gs[-1]["x1"], p[2])
        else:
            gs.append({"x0": p[0], "x1": p[2], "p": [p]})
    return gs


def syllables(ps, h):
    """글자 조각을 한 글자씩 묶는다. '사' 의 ㅅ·ㅏ 처럼 떨어진 좁은 조각 둘은
    합친 폭이 글자 높이 정도면 한 글자로 본다."""
    out = []
    for g in x_groups(ps, gap=0):
        last = out[-1] if out else None
        if (last and last["n"] == 1 and last["x1"] - last["x0"] < 0.75 * h
                and g["x1"] - g["x0"] < 0.75 * h and g["x1"] - last["x0"] <= 1.1 * h):
            last["p"] += g["p"]
            last["x1"] = max(last["x1"], g["x1"])
            last["n"] = 2
        else:
            out.append({"x0": g["x0"], "x1": g["x1"], "p": list(g["p"]), "n": 1})
    return out


def split_row(ps):
    """한 줄을 두 줄로 나눈다: 띄어쓰기가 있으면 가운데에 가까운 띄어쓰기에서,
    없으면 글자 수의 절반에서 (윗줄이 한 글자 더 길게)."""
    _, y0, _, y1 = bbox(ps)
    h = y1 - y0
    sy = syllables(ps, h)
    if len(sy) < 2:
        return None
    gaps = [sy[i + 1]["x0"] - sy[i]["x1"] for i in range(len(sy) - 1)]
    usual = sorted(gaps)[len(gaps) // 2]
    spaces = [i for i, g in enumerate(gaps) if g >= max(0.3 * h, 2 * usual)]
    if spaces:
        mid = (sy[0]["x0"] + sy[-1]["x1"]) / 2
        i = min(spaces, key=lambda i: abs((sy[i]["x1"] + sy[i + 1]["x0"]) / 2 - mid))
    else:
        i = (len(sy) + 1) // 2 - 1
    return [p for g in sy[:i + 1] for p in g["p"]], [p for g in sy[i + 1:] for p in g["p"]]


def is_toilet_label(rs):
    """첫 줄이 'W101' 처럼 W 로 시작하고 아래에 한 줄(화장실)이 더 있으면 화장실 이름표.
    W 는 가늘고 긴 획 4개가 겹쳐 그려져 있어서, 줄 맨 앞의 가는 획 수로 알아본다."""
    if len(rs) < 2:
        return False
    r = rs[0]
    h = max(p[3] - p[1] for p in r["p"])
    if h < 2:
        return False
    x0 = min(p[0] for p in r["p"])
    strokes = [p for p in r["p"] if p[0] < x0 + 0.75 * h and p[2] - p[0] < 0.3 * h and p[3] - p[1] > 0.85 * h]
    return len(strokes) >= 3


class Label:
    """여러 줄(줄마다 글자 조각·색)을 한 덩어리로 키우고, 필요하면 두 줄로 나누고, 옮긴다."""

    def __init__(self, rows, k):
        self.rows = rows          # [(조각들, 색)]
        self.k = k
        x0, y0, x1, y1 = bbox([p for ps, _ in rows for p in ps])
        self.c = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.to = None
        self.layout = [(ps, col, 0.0, 0.0) for ps, col in rows]   # 줄마다 (조각, 색, dx, dy)

    def size(self):
        """키운 뒤의 너비·높이."""
        boxes = [(a + dx, b + dy, c + dx, d + dy) for ps, _, dx, dy in self.layout for a, b, c, d in [bbox(ps)]]
        w = max(b[2] for b in boxes) - min(b[0] for b in boxes)
        h = max(b[3] for b in boxes) - min(b[1] for b in boxes)
        return w * self.k, h * self.k

    def wrap(self):
        """가장 긴 줄을 두 줄로 나눠 다시 쌓는다."""
        lines = list(self.rows)
        widths = [bbox(ps)[2] - bbox(ps)[0] for ps, _ in lines]
        i = widths.index(max(widths))
        parts = split_row(lines[i][0])
        if not parts:
            return False
        lines[i:i + 1] = [(parts[0], lines[i][1]), (parts[1], lines[i][1])]
        heights = [bbox(ps)[3] - bbox(ps)[1] for ps, _ in lines]
        gap = 0.45 * max(heights)
        y = self.c[1] - (sum(heights) + gap * (len(lines) - 1)) / 2
        self.layout = []
        for (ps, col), h in zip(lines, heights):
            a, b, c, d = bbox(ps)
            self.layout.append((ps, col, self.c[0] - (a + c) / 2, y - b))
            y += h + gap
        return True

    def box(self, at=None, margin=0.0):
        w, h = self.size()
        cx, cy = at or self.to or self.c
        return box(cx - w / 2 - margin, cy - h / 2 - margin, cx + w / 2 + margin, cy + h / 2 + margin)

    def svg(self):
        k, (cx, cy) = self.k, self.c
        nx, ny = self.to or self.c
        out = []
        for ps, col, dx, dy in self.layout:
            tx, ty = nx + k * (dx - cx), ny + k * (dy - cy)
            d = "".join(p[4] for p in ps)
            out.append(f'<path class="t" fill="{col}" stroke="{col}" stroke-width="{fmt(TEXT_BOLD / k)}" '
                       f'stroke-linejoin="round" transform="matrix({fmt(k)} 0 0 {fmt(k)} {fmt(tx)} {fmt(ty)})" d="{d}"/>')
        return "".join(out)


def room_width(regions, x, y):
    """(x, y) 가 들어 있는 방에서 그 높이의 가로 폭."""
    pt = Point(x, y)
    for r in regions:
        if r.contains(pt):
            minx, _, maxx, _ = r.bounds
            seg = LineString([(minx - 1, y), (maxx + 1, y)]).intersection(r)
            for part in getattr(seg, "geoms", [seg]):
                if part.length and part.distance(pt) < 1e-6:
                    return part.length
    return None


def fit(label, regions):
    """방보다 넓으면 두 줄로 나누고, 그래도 넓으면 조금 줄인다 (원래 크기보다 작게는 안 함)."""
    room = room_width(regions, *label.c)
    if not room:
        return
    limit = room * 0.9
    if label.size()[0] > limit:
        label.wrap()
    w = label.size()[0]
    if w > limit:
        label.k = max(1.0, label.k * limit / w)


def find_spot(label, obstacles, taken, W, H):
    """화장실 이름표: 선과 겹치지 않는 가장 가까운 빈 곳 (아래쪽 먼저)."""
    cx, cy = label.c
    cands = []
    for dy in range(-60, 91, 3):
        for dx in range(-60, 61, 3):
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= 90:
                cands.append((dist + (25 if dy < 0 else 0), dx, dy))
    for _, dx, dy in sorted(cands):
        b = label.box((cx + dx, cy + dy), margin=1.2)
        if b.bounds[0] < 0 or b.bounds[1] < 0 or b.bounds[2] > W or b.bounds[3] > H:
            continue
        if len(obstacles.query(b, predicate="intersects")) or any(b.intersects(t) for t in taken):
            continue
        return (cx + dx, cy + dy)
    return None


def class_text(cx, cy, name):
    """반 표시 (예: 1-1, 자습실) 를 (cx, cy) 가운데에 파랗고 크게 쓴다."""
    size = CLASS_SIZE if len(name) <= 4 else CLASS_SIZE * 0.8
    return (f'<text x="{fmt(cx)}" y="{fmt(cy + size * 0.36)}" font-size="{fmt(size)}" font-weight="800" '
            f'font-family="{FONT}" text-anchor="middle" fill="{CLASS_COLOR}" letter-spacing="-0.3">{name}</text>')


def text_layer(tags, floor_id, regions, obstacles, W, H):
    """글씨 전부를 다시 그린다: 과목실 이름 지우기, 반 표시 새로 쓰기, 방 이름 키우기·줄 바꾸기, 화장실 이름 옮기기."""
    out, small, rooms, labels, toilets = [], [], [], [], []
    pieces = text_pieces(tags)
    for (x0, y0, x1, y1), name in RENAME.get(floor_id, []):
        pieces = [p for p in pieces if not (p[0] >= x0 and p[2] <= x1 and p[1] >= y0 and p[3] <= y1)]
        out.append(class_text((x0 + x1) / 2, (y0 + y1) / 2 + 1, name))
    for block in label_blocks(pieces):
        rs = text_rows(block)
        if len(rs) == 3 and is_class_row(rs[2]) and all(r["y1"] - r["y0"] > 2 for r in rs):
            rooms.append(rs)  # 교실: 호수 / 이름 / 반
        elif len(rs) == 2 and is_class_row(rs[1]) and rs[0]["y1"] - rs[0]["y0"] > 2:
            # '201 / 1-1' 처럼 호수와 반만 있는 교실: 반 표시만 파랗게
            labels.append(Label([(rs[0]["p"], TEXT), (rs[1]["p"], CLASS_COLOR)], LABEL_SCALE))
        elif max(r["y1"] - r["y0"] for r in rs) >= MIN_LABEL_H:
            lab = Label([(r["p"], TEXT) for r in rs], LABEL_SCALE)
            fit(lab, regions)
            (toilets if is_toilet_label(rs) else labels).append(lab)
        else:
            small += block

    names = CLASS_TEXT.get(floor_id)
    if names and len(names) != len(rooms):
        print(f"  ! {floor_id}: 교실 {len(rooms)}곳을 찾았는데 반 이름은 {len(names)}개 → 원래 글씨를 키우기만 한다")
        names = None
    rooms.sort(key=lambda rs: rs[2]["x0"])
    for i, (num, _name, cls) in enumerate(rooms):
        if names:
            out.append(scaled(num["p"], NUMBER_SCALE))
            cx = (cls["x0"] + cls["x1"]) / 2
            cy = (_name["y0"] + cls["y1"]) / 2 + 1
            out.append(class_text(cx, cy, names[i]))
        else:
            labels.append(Label([(num["p"], TEXT), (cls["p"], CLASS_COLOR)], LABEL_SCALE))

    taken = [lab.box(margin=0.5) for lab in labels]
    moved = 0
    for lab in toilets:
        spot = find_spot(lab, obstacles, taken, W, H)
        if spot and spot != lab.c:
            lab.to = spot
            moved += 1
        taken.append(lab.box(margin=0.5))
    out += [lab.svg() for lab in labels + toilets]
    if small:
        out.append(scaled(small, 1))
    return out, len(rooms), moved


# ── 치수·높이 표시 지우기 ─────────────────────────────
# 학생들이 보기 어려운 표시(치수선과 숫자, ±0·-280 같은 높이 표시, 축 번호 동그라미 등)를 도면에서 뺀다.
TICK = 1.8                 # 이보다 작은 검은 점(채운 글자 조각)은 치수선의 눈금으로 본다


def path_segments(sub):
    """곡선 없는 하위 경로를 직선 조각 [(시작, 끝)] 으로. 곡선이 있으면 None."""
    if "C" in sub:
        return None
    pts = points(sub)
    segs = list(zip(pts, pts[1:]))
    if sub.rstrip().endswith("Z") and len(pts) > 2:
        segs.append((pts[-1], pts[0]))
    return segs


def axis_line(a, b):
    """수평·수직 직선 조각이면 ('h'|'v', 고정 좌표, 시작, 끝), 아니면 None."""
    (x0, y0), (x1, y1) = a, b
    if abs(y1 - y0) < 0.3 and abs(x1 - x0) >= 3:
        return ("h", (y0 + y1) / 2, min(x0, x1), max(x0, x1))
    if abs(x1 - x0) < 0.3 and abs(y1 - y0) >= 3:
        return ("v", (x0 + x1) / 2, min(y0, y1), max(y0, y1))
    return None


def along(o, x, y):
    return (x, y) if o == "h" else (y, x)


def find_dimensions(tags):
    """치수선: 곧은 선 위에 눈금(작은 검은 점)이 두 곳 이상 있고, 계단 디딤판처럼
    촘촘히 겹쳐 놓인 평행선이 아닌 것. 그 선에 끝이 닿는 보조선과 옆의 숫자도 함께 찾는다.
    돌려주는 값: ({(태그, 하위경로): 지울 조각 번호 집합}, 지울 글자 하위경로 집합)"""
    lines, ticks, texts = [], [], []
    for ti, a in enumerate(tags):
        for si, sub in enumerate(subpaths(a["d"])):
            pts = points(sub)
            if not pts:
                continue
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            small = max(xs) - min(xs) <= TICK and max(ys) - min(ys) <= TICK
            c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
            if a["class"] == "t":
                texts.append((c, sub))
                if small:
                    ticks.append(c)
            elif a["class"] in ("m", "w"):
                for k, (p, q) in enumerate(path_segments(sub) or []):
                    ax = axis_line(p, q)
                    if ax:
                        lines.append((ti, si, k, ax))
    grid = {}
    for x, y in ticks:
        grid.setdefault((int(x // 6), int(y // 6)), []).append((x, y))

    def near(x0, y0, x1, y1):
        for gx in range(int(x0 // 6) - 1, int(x1 // 6) + 2):
            for gy in range(int(y0 // 6) - 1, int(y1 // 6) + 2):
                yield from grid.get((gx, gy), ())

    by_axis = {"h": [], "v": []}
    for ln in lines:
        by_axis[ln[3][0]].append(ln[3])

    def stacked(ax):
        """비슷한 길이의 평행선이 가까이 둘 이상 → 계단 디딤판·창틀 같은 것."""
        o, c, a, b = ax
        n = 0
        for o2, c2, a2, b2 in by_axis[o]:
            if 0.3 < abs(c2 - c) < 8 and min(b, b2) - max(a, a2) > 0.5 * (b - a) and 0.7 < (b2 - a2) / (b - a) < 1.4:
                n += 1
        return n >= 2

    dims = []
    for ti, si, k, ax in lines:
        o, c, a, b = ax
        x0, y0 = along(o, a, c)
        x1, y1 = along(o, b, c)
        marks = {round(along(o, x, y)[0]) for x, y in near(x0, y0, x1, y1)
                 if abs(along(o, x, y)[1] - c) <= 0.7 and a - 2.5 <= along(o, x, y)[0] <= b + 2.5}
        if len(marks) >= 2 and max(marks) - min(marks) >= 3 and not stacked(ax):
            dims.append((ti, si, k, ax))
    # 같은 줄에 이어진 선도 치수선 (눈금이 짧은 선으로 그려진 줄)
    found = {(ti, si, k) for ti, si, k, _ in dims}
    grew = True
    while grew:
        grew = False
        for ti, si, k, ax in lines:
            if (ti, si, k) in found or stacked(ax):
                continue
            o, c, a, b = ax
            if any(o == d[0] and abs(c - d[1]) < 0.3 and a <= d[3] + 3 and b >= d[2] - 3 for *_, d in dims):
                dims.append((ti, si, k, ax))
                found.add((ti, si, k))
                grew = True
    drop = {}
    for ti, si, k, _ in dims:
        drop.setdefault((ti, si), set()).add(k)
    for ti, si, k, (o, c, a, b) in lines:
        for _, _, _, (do, dc, da, db) in dims:
            if do != o and da - 4 <= c <= db + 4 and (abs(a - dc) <= 4 or abs(b - dc) <= 4):
                drop.setdefault((ti, si), set()).add(k)  # 보조선
                break
    gone = set()
    for (x, y), sub in texts:
        for _, _, _, (o, c, a, b) in dims:
            u, v = along(o, x, y)
            if abs(v - c) <= 6.5 and a - 3 <= u <= b + 3:
                gone.add(sub)
                break
    return drop, gone, len(dims)


def level_marks(text):
    """'±0', '+ 280', '- 130' 같은 높이 표시: 부호(짧은 가로줄이 있는 작은 기호) 바로 뒤에 숫자 1~3개."""
    gone = set()
    for block in label_blocks(text):
        for r in text_rows(block):
            h = r["y1"] - r["y0"]
            if h < 1 or h > 8:
                continue
            gs = x_groups(r["p"], gap=0)
            digit = lambda g: (g["x1"] - g["x0"]) <= 0.75 * h and max(p[3] for p in g["p"]) - min(p[1] for p in g["p"]) >= 0.65 * h
            def sign(g):
                if (g["x1"] - g["x0"]) > 1.1 * h:
                    return False
                if len(g["p"]) == 1 and g["p"][0][3] - g["p"][0][1] <= 0.3 * h and g["p"][0][2] - g["p"][0][0] >= 0.3 * h:
                    return True  # -
                # + · ± : 폭과 높이가 비슷하고, 곡선 없이 가로·세로 선만으로 된 다각형 (꼭짓점 10개 이상)
                gw = g["x1"] - g["x0"]
                gh = max(p[3] for p in g["p"]) - min(p[1] for p in g["p"])
                if gw < 0.45 * h or not 0.7 < gw / max(gh, 0.01) < 1.4:
                    return False
                corners = 0
                for p in g["p"]:
                    pts = points(p[4])
                    if "C" in p[4] or any(abs(a[0] - b[0]) > 0.15 and abs(a[1] - b[1]) > 0.15 for a, b in zip(pts, pts[1:])):
                        return False
                    corners += len(pts)
                return corners >= 10
            for i, g in enumerate(gs):
                if not sign(g) or (i and g["x0"] - gs[i - 1]["x1"] < 0.8 * h):
                    continue
                j = i + 1
                while j < len(gs) and j - i <= 3 and digit(gs[j]) and gs[j]["x0"] - gs[j - 1]["x1"] < 0.8 * h:
                    j += 1
                if j - i >= 2 and (j == len(gs) or gs[j]["x0"] - gs[j - 1]["x1"] >= 0.8 * h):
                    gone |= {p[4] for g2 in gs[i:j] for p in g2["p"]}
    return gone


def strip_marks(tags, floor_id):
    """도면 태그에서 치수선·숫자, 높이 표시, '홀', ERASE 네모 안의 표시를 지운 새 태그 목록과 지운 개수."""
    drop, gone, n_dims = find_dimensions(tags)
    text = text_pieces(tags)
    # 치수 숫자가 절반 넘게 걸린 글자 덩어리는 통째로 (숫자 일부만 남지 않게)
    for block in label_blocks(text):
        if sum(p[4] in gone for p in block) * 2 >= len(block):
            gone |= {p[4] for p in block}
    gone |= level_marks([p for p in text if p[4] not in gone])
    kept = without_hall([p for p in text if p[4] not in gone])
    gone |= {p[4] for p in text} - {p[4] for p in kept}
    boxes = ERASE.get(floor_id, [])
    inside = lambda b, x0, y0, x1, y1: b[0] <= x0 and x1 <= b[2] and b[1] <= y0 and y1 <= b[3]
    for b, what in boxes:
        if what == "text":
            keep = KEEP.get(floor_id, [])
            small = [p for p in text if max(p[2] - p[0], p[3] - p[1]) <= 2.4]
            # 세로로 쓴 메모: 작은 글자 조각이 같은 왼쪽 끝에 넷 이상 세로로 쌓여 있다
            column = lambda p: p[2] - p[0] <= 2.4 and p[3] - p[1] <= 1.6 and sum(abs(q[0] - p[0]) <= 0.15 for q in small) >= 4
            gone |= {p[4] for p in text if inside(b, *p[:4])
                     and not any(inside(k, *p[:4]) and not column(p) for k in keep)}
    out = []
    for ti, a in enumerate(tags):
        subs = []
        for si, sub in enumerate(subpaths(a["d"])):
            pts = points(sub)
            if pts and any(what == "all" for _, what in boxes):
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                if any(what == "all" and inside(b, min(xs), min(ys), max(xs), max(ys)) for b, what in boxes):
                    continue
            if a["class"] == "t" and sub in gone:
                continue
            ks = drop.get((ti, si))
            if ks:
                segs = path_segments(sub)
                subs += [f"M{fmt(p[0])} {fmt(p[1])}L{fmt(q[0])} {fmt(q[1])}" for k, (p, q) in enumerate(segs) if k not in ks]
                continue
            subs.append(sub)
        if subs:
            out.append(dict(a, d="".join(subs)))
    return out, n_dims


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
    if length / thick > 8:
        return "hall" if 12 <= thick < 35 else None  # 폭이 아주 좁고 긴 것은 치수 띠 → 칠하지 않음
    inside = sum(1 for f in fixtures if region.contains(f))
    return "wet" if inside >= 2 else "room"


def decorate(path):
    s = open(path, encoding="utf-8").read()
    if MARK in s:
        return None  # 이미 꾸민 도면 (글씨를 두 번 키우지 않게)
    head = s[: s.index(">", s.index("<svg")) + 1]
    W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head).groups())
    tags = [attrs_of(t) for t in re.findall(r"<path [^>]*/>", s)]
    tags, n_dims = strip_marks(tags, os.path.basename(path)[:-4])

    lines, fixtures, fixture_lines = [], [], []
    doors_d, fixtures_d = [], []
    out = []
    for a in tags:
        cls = a["class"]
        if cls == "t":
            continue  # 글씨는 text_layer 가 따로 그린다
        keep = []
        for sub in subpaths(a["d"]):
            pts = points(sub)
            kind = door_or_fixture(sub, pts) if cls in ("m", "l", "w") else None
            if kind == "door":
                doors_d.append(sub)
                lines += door_closers(sub)
            elif kind == "fixture":
                fixtures_d.append(sub)
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                fixtures.append(Point((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
                if len(pts) > 1:
                    fixture_lines.append(LineString(pts))
            else:
                keep.append(sub)
            if cls in ("w", "m") and len(pts) > 1 and kind != "fixture":
                lines.append(LineString(pts))
        if not keep:
            continue
        d = "".join(keep)
        if cls == "h":
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
    obstacles = STRtree(lines + fixture_lines)
    texts, rooms, moved = text_layer(tags, os.path.basename(path)[:-4], regions, obstacles, W, H)
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

    head = head.replace("<svg", f"<svg {MARK}", 1)
    result = head + '<g id="deco">' + "".join(deco) + "</g>" + "".join(out) + "".join(texts) + "</svg>"
    open(path, "w", encoding="utf-8").write(result)
    counts = {k: len(v) for k, v in by_kind.items()}
    return rooms, moved, len(doors_d), len(fixtures_d), counts, len(result) // 1024


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for path in sorted(glob.glob(os.path.join(ROOT, "plans", "*.svg"))):
        if os.path.basename(path) == "site.svg":
            continue
        res = decorate(path)
        if res is None:
            print(f"{os.path.basename(path):12} 이미 꾸민 도면이라 건너뜀 (build_plans.py 로 다시 만든 뒤 실행)")
            continue
        rooms, moved, doors, fixtures, counts, kb = res
        print(f"{os.path.basename(path):12} 교실 {rooms:3}  화장실 이름 옮김 {moved}  문 {doors:3}  기구 {fixtures:3}  바닥 {counts}  {kb} KB")


if __name__ == "__main__":
    main()
