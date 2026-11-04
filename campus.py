"""캠퍼스 데이터: 건물 · 층 · 배치도 위 건물 윤곽 · 신고 분류.

배치도 좌표는 plans/site.svg 의 단위(pt)이며 원본 전체배치도 PDF에서 추출했다.
"""
import re
from dataclasses import dataclass, field

SITE_ID = "site"


@dataclass(frozen=True)
class Floor:
    id: str
    label: str      # 층 버튼에 쓰는 짧은 이름 (1F, B1 ...)
    name: str       # 화면에 쓰는 이름 (1층, 지하 1층 ...)
    area: float | None = None  # 바닥면적 ㎡


@dataclass(frozen=True)
class Building:
    id: str
    name: str
    sub: str
    dong: str
    code: str
    color: str
    polys: list[list[tuple[float, float]]] = field(default_factory=list)
    floors: list[Floor] = field(default_factory=list)

    @property
    def default_floor(self) -> Floor:
        return next((f for f in self.floors if f.label == "1F"), self.floors[0])


def _poly(text: str) -> list[tuple[float, float]]:
    return [tuple(map(float, p.split(","))) for p in text.split()]


BUILDINGS: list[Building] = [
    Building("b2", "덕린관", "고등학교 교사", "2동", "주2", "#2563eb",
             [_poly("417.1,315.7 653.2,315.7 653.2,339.3 606,339.3 606,345.7 607.2,345.7 610.8,349.2 610.8,355.2 594.2,355.2 594.2,358.9 547.6,358.9 547.6,351.6 522.7,351.6 522.7,358.9 482.2,358.9 482.2,361 476.1,361 476.1,355.2 459.6,355.2 459.6,349.2 463,345.7 464.2,345.7 464.2,339.3 417.1,339.3")],
             [Floor("b2-b1", "B1", "지하 1층", 372.63), Floor("b2-1f", "1F", "1층", 1526.08),
              Floor("b2-2f", "2F", "2층", 1503.34), Floor("b2-3f", "3F", "3층", 1503.34),
              Floor("b2-4f", "4F", "4층", 1503.34)]),
    Building("b1", "만대관", "본관", "1동", "주1", "#7c3aed",
             [_poly("476.1,361 482.2,361 482.2,379.2 483.2,379.2 483.2,414.7 486.7,414.7 491.5,409.9 497.4,409.9 497.4,451.3 483.2,451.3 483.2,498.4 487.9,498.4 487.9,517.4 476.1,517.4 476.1,493.8 464.7,493.8 464.7,486.7 454.9,486.7 454.9,404 447.8,404 447.8,379.2 476.1,379.2")],
             [Floor("b1-b1", "B1", "지하 1층", 244.47), Floor("b1-1f", "1F", "1층", 741.72),
              Floor("b1-2f", "2F", "2층", 741.72), Floor("b1-3f", "3F", "3층", 741.72),
              Floor("b1-4f", "4F", "4층", 912.72), Floor("b1-rf", "RF", "옥상층")]),
    Building("b4", "중학교 교사", "광덕중학교", "4동", "주3", "#059669",
             [_poly("457.6,517.4 654.7,517.4 654.7,568.3 632,568.3 632,549.2 629.1,549.2 627.1,547.4 627.1,541 610.8,541 604.9,546.9 608.4,550.4 608.4,557.5 591.8,557.5 591.8,541 574,541 563.4,551.6 529.2,551.6 518.5,541 498.6,541 498.6,557.5 482,557.5 482,550.4 485.6,546.9 485.6,541 457.6,541")],
             [Floor("b4-1f", "1F", "1층", 1170.95), Floor("b4-2f", "2F", "2층", 1138.39),
              Floor("b4-3f", "3F", "3층", 1138.39), Floor("b4-4f", "4F", "4층", 1138.39)]),
    Building("b6", "복지관", "급식실", "6동", "주4", "#d97706",
             [_poly("633.9,377.6 666.9,377.6 666.9,490.9 633.9,490.9")],
             [Floor("b6-1f", "1F", "1층", 676.8), Floor("b6-2f", "2F", "2층", 362.16),
              Floor("b6-l1", "통로1", "연결통로 1층"), Floor("b6-l2", "통로2", "연결통로 2층", 53.01),
              Floor("b6-lr", "통로R", "연결통로 지붕")]),
    Building("b3", "단재관", "교사", "3동", "주5", "#0891b2",
             [_poly("584.7,202.6 600.8,202.6 600.8,260 618.7,260 618.7,281.6 606.6,281.6 606.6,315.7 599.7,315.7 599.7,274.3 577.4,274.3 577.4,210.9 584.7,210.9")],
             [Floor("b3-b1", "B1", "지하 1층", 151.46), Floor("b3-1f", "1F", "1층", 379.97),
              Floor("b3-2f", "2F", "2층", 379.97), Floor("b3-3f", "3F", "3층", 345.05),
              Floor("b3-4f", "4F", "4층", 345.05), Floor("b3-rf", "RF", "옥상층")]),
    Building("b8", "체육관", "실내체육관", "8동", "주6", "#db2777",
             [_poly("455.1,41.1 563.1,38.5 565.3,123.4 457.2,126.2")],
             [Floor("b8-b1", "B1", "지하 1층", 108.0), Floor("b8-1f", "1F", "1층", 1555.8),
              Floor("b8-2f", "2F", "2층", 693.24), Floor("b8-rf", "RF", "지붕층")]),
    Building("b9", "특별교실", "특별교실동", "7·9동", "주7", "#4f46e5",
             [_poly("454.4,165.9 458.7,165.9 458.7,162.7 505.4,162.7 505.4,157.8 537.2,157.8 537.2,202 458.7,202 458.7,180 452.7,180 452.7,167.5"),
              _poly("537.4,152.7 577.2,152.7 577.2,168.1 585.2,168.1 585.2,173.4 593,173.4 593,183 597.2,183 597.2,202.9 593,202.9 593,188.7 537.4,188.7")],
             [Floor("b9-1f", "1F", "1층", 457.94), Floor("b9-2f", "2F", "2층", 833.95),
              Floor("b9-3f", "3F", "3층", 734.58), Floor("b9-4f", "4F", "4층", 734.58),
              Floor("b9-5f", "5F", "5층", 734.58)]),
    Building("b10", "체육실동", "체육실", "10동", "주8", "#65a30d",
             [_poly("327.4,216 356.6,216 356.6,226.3 335.4,226.3 335.4,229.8 327.4,229.8"),
              _poly("343,232.5 356.6,232.5 356.6,263.1 343,263.1")],
             [Floor("b10-1f", "1F", "1층", 120.54)]),
    Building("b5", "수위실", "부속동", "5동", "부1", "#64748b",
             [_poly("432,596 442,596 442,627 432,627")],
             [Floor("b5-1f", "1F", "1층", 90.02)]),
    # 배치도에 정확한 위치가 없어 지도 윤곽 없이 목록에서만 연다
    Building("wc", "화장실", "부속동 · 위치 미표시", "", "부3", "#64748b",
             [], [Floor("wc-1f", "1F", "1층", 25.2)]),
]

BUILDING_BY_ID = {b.id: b for b in BUILDINGS}
FLOOR_INDEX = {f.id: (b, f) for b in BUILDINGS for f in b.floors}

# ── 연결복도 버튼 ──────────────────────────────────
# 층 도면 위 연결복도 자리에 버튼을 놓고, 누르면 이어진 건물의 같은 층으로 간다.
# {층 id: [(x, y, 갈 층 id), ...]}  x, y 는 그 층 도면 좌표 (연결복도 글자 자리)
LINKS = {
    # 만대관: 왼쪽 끝 → 중학교, 오른쪽 끝 → 덕린관
    "b1-1f": [(73, 124, "b4-1f"), (732, 115, "b2-1f")],
    "b1-2f": [(73, 124, "b4-2f"), (732, 115, "b2-2f")],
    "b1-3f": [(83, 131, "b4-3f"), (732, 108, "b2-3f")],
    "b1-4f": [(75, 120, "b4-4f"), (732, 113, "b2-4f")],
    # 덕린관: 아래 왼쪽 → 만대관, 2층 위쪽 → 단재관
    "b2-1f": [(253, 222, "b1-1f")],
    "b2-2f": [(254, 246, "b1-2f"), (760, 40, "b3-2f")],
    "b2-3f": [(254, 222, "b1-3f")],
    "b2-4f": [(254, 222, "b1-4f")],
    # 단재관: 오른쪽 → 덕린관
    "b3-1f": [(799, 142, "b2-1f")],
    "b3-2f": [(799, 142, "b2-2f")],
    # 중학교: "본관에 연결" → 만대관, 오른쪽 위 연결복도 → 복지관 연결통로
    "b4-1f": [(113, 22, "b1-1f")],
    "b4-2f": [(96, 22, "b1-2f"), (830, 55, "b6-l2")],
    "b4-3f": [(96, 22, "b1-3f"), (826, 88, "b6-lr")],
    "b4-4f": [(96, 22, "b1-4f")],
    # 특별교실: 2층 연결복도 → 단재관
    "b9-2f": [(938, 333, "b3-2f")],
}

CATEGORIES = {
    "facility": "🛠 시설 파손",
    "slip": "⚠️ 미끄럼·낙상",
    "fire": "🔥 전기·화재",
    "traffic": "🚸 교통·보행",
    "hygiene": "🧴 위생·환경",
    "security": "🔒 방범·출입",
    "etc": "• 기타",
}

SEVERITIES = {  # id: (이름, 색)
    "urgent": ("긴급", "#dc2626"),
    "high": ("높음", "#ea580c"),
    "mid": ("보통", "#ca8a04"),
    "low": ("낮음", "#2563eb"),
}

# 신고 종류: id: (이름, 표시, 핀 색) — 불편 신고는 위험도와 상관없이 보라색 핀
KINDS = {
    "danger": ("위험", "⚠️", None),
    "incon": ("불편", "🙁", "#7c3aed"),
}


def kind_of(r: dict) -> str:
    """신고 종류 (예전 신고에는 없으니 위험으로 본다)."""
    return r.get("kind") if r.get("kind") in KINDS else "danger"


STATUSES = {
    "new": "접수",
    "doing": "처리중",
    "done": "처리완료",
    "rejected": "반려",
}
OPEN_STATUSES = ("new", "doing")


def place_name(map_id: str) -> str:
    """신고 위치(map id)를 사람이 읽는 이름으로."""
    if map_id == SITE_ID:
        return "캠퍼스 야외"
    hit = FLOOR_INDEX.get(map_id)
    return f"{hit[0].name} {hit[1].name}" if hit else map_id


def building_of(map_id: str) -> Building | None:
    hit = FLOOR_INDEX.get(map_id)
    return hit[0] if hit else None


def point_in_poly(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(poly) - 1
    for i, (xi, yi) in enumerate(poly):
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def building_at(x: float, y: float, pad: float = 4.0) -> Building | None:
    """배치도 좌표에 있는 건물. 작은 건물도 누르기 쉽게 주변 pad 만큼 여유를 준다."""
    for b in BUILDINGS:
        for poly in b.polys:
            if point_in_poly(x, y, poly):
                return b
    for b in BUILDINGS:
        for poly in b.polys:
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            if min(xs) - pad <= x <= max(xs) + pad and min(ys) - pad <= y <= max(ys) + pad:
                return b
    return None


def link_label(floor_id: str) -> str:
    """연결복도 버튼 글자, 예: '덕린관 2층'."""
    hit = FLOOR_INDEX.get(floor_id)
    return f"{hit[0].name.removesuffix(' 교사')} {hit[1].name}" if hit else floor_id


# ── 검색 ─────────────────────────────────────────
def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def search(text: str, limit: int = 8) -> list[dict]:
    """'2-1', '2학년 1반', '409', '보건실', '덕린관' 같은 말로 방·반·건물을 찾는다."""
    from rooms import CLASSES, ROOMS

    q = _norm(text)
    if not q:
        return []
    m = re.fullmatch(r"(\d)학년(\d{1,2})반?", q) or re.fullmatch(r"(\d)[-.](\d{1,2})반?", q)
    if m:
        q = f"{m.group(1)}-{m.group(2)}"
    q = q.removesuffix("호") if re.fullmatch(r"[bw]?\d{3}호", q) else q

    found = []  # (순위, 결과)

    def rank(*keys):
        best = None
        for i, k in enumerate(keys):
            k = _norm(k)
            if not k:
                continue
            r = 0 if k == q else 2 if k.startswith(q) else 4 if q in k else None
            if r is not None:
                r += min(i, 1)
                best = r if best is None else min(best, r)
        return best

    for fid, cls, num, x, y in CLASSES:
        r = rank(cls, num)
        if r is not None:
            found.append((r, {"floor": fid, "x": x, "y": y, "title": cls,
                              "sub": place_name(fid) + (f" · {num}호" if num else "")}))
    class_nums = {(fid, num) for fid, _, num, _, _ in CLASSES if num}
    for fid, num, name, x, y in ROOMS:
        if (fid, num) in class_nums:
            continue  # 반 교실은 반 이름(예: 2-1 · 409호)으로 나온다
        r = rank(num, name)
        if r is not None:
            found.append((r + 0.5, {"floor": fid, "x": x, "y": y, "title": f"{num} {name}".strip(),
                                    "sub": place_name(fid)}))
    for b in BUILDINGS:
        r = rank(b.name, b.sub)
        if r is not None and b.floors:
            found.append((r + 0.2, {"floor": b.default_floor.id, "x": None, "y": None, "title": b.name,
                                    "sub": "건물 · " + " · ".join(x for x in (b.dong, b.sub) if x)}))
    found.sort(key=lambda t: t[0])
    return [f for _, f in found[:limit]]
