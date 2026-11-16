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
import glob  # 폴더 안의 파일을 패턴(*.svg)으로 찾는 도구
import os  # 폴더·파일 경로 도구
import re  # 글자 패턴(정규식)으로 SVG 를 읽는 도구
import sys  # 화면 출력 설정과 불러올 폴더 목록을 다루는 도구

from shapely.geometry import LineString, Point  # 도형 도구: 선, 점
from shapely.ops import unary_union  # 여러 도형을 하나로 합치는 도구
from shapely.strtree import STRtree  # 많은 도형 중 겹치는 것을 빨리 찾는 도구
from shapely.geometry import box  # 도형 도구: 네모

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # 이 폴더(tools)의 파일도 불러올 수 있게 한다
from decorate_site import attrs_of, fmt, points, poly_d, subpaths  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 프로젝트 맨 위 폴더

TEXT = "#0b1220"  # 글자 색 (아주 진한 남색)
TEXT_BOLD = 0.2            # 글자 테두리 굵기 (도면 단위) → 글씨가 굵어 보인다
FLOOR = {"room": "#f5ead6", "hall": "#eceff3", "wet": "#dcebf7"}  # 바닥 색: 방(나무색), 복도(연회색), 화장실(하늘색)
DOOR = "#b45309"           # 문: 나무색
FIXTURE = "#0369a1"        # 변기·세면대: 파랑
WALL_GAP = 0.9             # 선 사이 이만큼 벌어진 틈은 막힌 것으로 본다 (방 찾기)
MARK = 'data-deco="floors"'  # 꾸민 도면에 붙이는 표시 (두 번 꾸미지 않게)

LABEL_SCALE = 1.5          # 방 이름 글씨 키우기 (배)
NUMBER_SCALE = 1.35        # 교실 호수(101 등) 키우기
MIN_LABEL_H = 4.0          # 이보다 작은 글씨(DN·UP·높이 표시 등)는 그대로 둔다
CLASS_SIZE = 12            # 새로 쓰는 반 표시 글자 크기 (도면 단위)
CLASS_COLOR = "#1d4ed8"    # 반 표시 색 (파랑)
FONT = "Pretendard, 'Malgun Gothic', sans-serif"  # 새로 쓰는 글자의 글꼴
# 덕린관 교실 반 표시: 왼쪽 교실(x01호)부터 차례대로
CLASS_TEXT = {  # 층 id → 교실 반 이름 목록
    "b2-1f": [f"1-{n}" for n in range(10, 0, -1)],  # 덕린관 1층: 1-10 부터 1-1 까지
    "b2-3f": [f"3-{n}" for n in range(10, 0, -1)],  # 덕린관 3층: 3-10 부터 3-1 까지
    "b2-4f": [f"2-{n}" for n in range(9, 0, -1)] + ["자습실"],   # 2-1 자리는 자습실, 나머지는 하나씩 당김
}  # 반 이름 목록 끝
# 교실이 아닌 방을 반으로 쓰는 곳: 이 네모 안의 도면 글씨(방 이름)를 지우고 반 표시를 새로 쓴다
RENAME = {  # 층 id → (네모, 새 반 이름)
    "b2-2f": [((697, 73, 733, 82), "1-11")],   # 211 공용교실3실 → 1-11
}  # 바꿀 이름 끝
# 자동으로 못 찾는 표시를 지울 네모 (x0, y0, x1, y1), 무엇을
#   "all": 네모 안에 통째로 들어 있는 선·글자 모두   "text": 글자만 (KEEP 의 이름표 글자는 남김)
_B3_EDGE = [((928, 75, 941, 195), "all")]            # 오른쪽 끝 치수 눈금
_B9 = [((540, 440, 700, 492), "all"),                 # 아래쪽 치수 숫자 남은 것
       ((0, 0, 1027.84, 60), "all"), ((965, 0, 1027.84, 646.42), "all")]   # 위·오른쪽 치수 눈금 남은 것
_B9_AREA = _B9 + [((465, 545, 505, 646), "all")]     # + 아래쪽 면적표(㎡) 칸
ERASE = {  # 층 id → 지울 네모 목록
    "b1-1f": [((370, 83.5, 385, 90.6), "text")],     # '홀 및 복도' → '복도'
    "b2-1f": [((236.5, 148, 242, 151.5), "text"), ((781.5, 109, 789.2, 113.6), "text"), ((247, 163, 259, 169.5), "text")],   # ±0 (모양이 달라 자동으로 못 찾음)
    "b1-4f": [((490, 95, 643, 245), "text"), ((645, 195, 657, 240), "text")],     # 도서관 책장 크기 메모 (2.6X0.45XH1.8 …)
    "b4-1f": [((114, 165, 124, 173), "text"), ((623, 215.5, 633, 223.5), "text")],   # '홀'
    "b8-b1": [((0, 0, 785.34, 50), "all"), ((0, 0, 42, 634.02), "all"),              # 축 번호 동그라미
              ((560, 45, 785.34, 110), "all")],                                       # 치수 눈금 남은 것
    "b8-rf": [((0, 0, 740.94, 42), "all"), ((0, 0, 40, 613.92), "all"),              # 축 번호 동그라미
              ((212, 205, 252, 300), "all"), ((350, 205, 390, 300), "all"), ((488, 205, 528, 300), "all"),  # 지붕 경사 표시 (위쪽 줄)
              ((212, 350, 252, 432), "all"), ((350, 350, 390, 432), "all"), ((488, 350, 528, 432), "all")],  # SLOPE 3/100
    "b9-1f": _B9, "b9-2f": _B9_AREA, "b9-3f": _B9_AREA, "b9-4f": _B9_AREA, "b9-5f": _B9_AREA,  # 특별교실동 층마다 같은 네모
    "b3-1f": _B3_EDGE, "b3-3f": [((905, 75, 922, 195), "all")], "b3-4f": [((905, 75, 922, 195), "all")],  # 단재관 오른쪽 끝 치수 눈금
    "b3-2f": _B3_EDGE + [((885, 131, 915, 141.5), "text")],                         # + 280
    "b2-b1": [((218, 141, 236, 149), "text"),                                        # '홀' (호~ㄹ)
              ((7.9, 83, 46, 93.6), "all"), ((45, 82.5, 72, 98.5), "all"),           # GL-4,940 · GL-5,507
              ((231, 79, 257.5, 86), "all"), ((238.5, 87, 256, 94.5), "all"),        # GL -3,240
              ((225.5, 80.5, 232.5, 87.5), "all"), ((282, 77.5, 317.2, 89), "all")],  # 표시 동그라미 · GL-2,840
    "b10-1f": [((100, 100, 130, 400), "all"), ((10, 375, 65, 395), "all")],          # 14,000 · 면적표
    "b5-1f": [((100, 438, 112, 495), "all"), ((425, 485, 440, 492), "all")],        # 치수 보조선 남은 것
    "wc-1f": [((340, 600, 400, 636), "all"), ((520, 610, 545, 636), "all")],        # 6,000
}  # 지울 네모 목록 끝
# ERASE "text" 네모 안이지만 지우지 않을 이름표 (이 네모 안의 큰 글자 조각은 남긴다)
KEEP = {"b1-4f": [(526, 169, 551, 196.5)]}            # 404 도서관


# ── 교실 이름표 ─────────────────────────────────────
def text_pieces(tags):  # 도면 글자를 조각(네모 영역 + 경로)으로 꺼내는 함수
    out = []  # 글자 조각들
    for a in tags:  # 도면 요소마다
        if a["class"] != "t":  # 글자가 아니면
            continue  # 건너뛴다
        for sub in subpaths(a["d"]):  # 글자 경로 조각마다
            p = points(sub)  # 점들
            if p:  # 점이 있으면
                xs, ys = [q[0] for q in p], [q[1] for q in p]  # x 들, y 들
                out.append((min(xs), min(ys), max(xs), max(ys), sub))  # (왼, 위, 오른, 아래, 경로) 로 저장
    return out  # 글자 조각 목록


def without_hall(ps):  # '홀' 글자를 빼는 함수
    """'홀' 이름표를 뺀다. 도면에는 '호 - ㄹ' 처럼 벌어진 세 조각(호, 짧은 줄, ㄹ)으로 그려져 있다."""  # 이 함수가 하는 일을 적은 설명글
    drop = set()  # 뺄 조각 번호들
    for i, d in enumerate(ps):  # 조각마다
        dw, dh = d[2] - d[0], d[3] - d[1]  # 조각의 폭과 높이
        if not (1.2 < dw < 3 and dh < 1.2 and dw > 1.8 * dh):  # 가운데 짧은 가로줄 모양이 아니면
            continue  # 건너뛴다
        cy = (d[1] + d[3]) / 2  # 줄의 세로 가운데
        left = [j for j, a in enumerate(ps) if 0 <= d[0] - a[2] < 1.2 and 3.5 < a[3] - a[1] < 5  # 줄 바로 왼쪽에 '호' 크기 조각이
                and 5 < a[2] - a[0] < 7 and a[1] < cy < a[3]]  # 같은 높이에 있는지
        right = [j for j, r in enumerate(ps) if 0 <= r[0] - d[2] < 2.5 and 2.5 < r[3] - r[1] < 4  # 줄 바로 오른쪽에 'ㄹ' 크기 조각이
                 and 3 < r[2] - r[0] < 4.5 and r[1] < cy < r[3]]  # 같은 높이에 있는지
        if left and right:  # 둘 다 있으면 '홀' 이다
            a, r = ps[left[0]], ps[right[0]]  # '호' 와 'ㄹ' 조각
            x0, y0, x1, y1 = a[0] - 0.2, min(a[1], r[1]) - 1.5, r[2] + 0.2, max(a[3], r[3]) + 0.2  # '홀' 전체를 감싸는 네모
            drop |= {j for j, p in enumerate(ps) if p[0] >= x0 and p[2] <= x1 and p[1] >= y0 and p[3] <= y1}  # 그 안의 조각을 모두 뺀다
    return [p for j, p in enumerate(ps) if j not in drop]  # 뺀 것을 제외한 조각들


def label_blocks(ps, pad=4.5, pad_y=7.0):  # 가까운 글자 조각을 이름표 덩어리로 묶는 함수
    """가까운 글자 조각끼리 묶어 이름표 덩어리를 만든다."""  # 이 함수가 하는 일을 적은 설명글
    parent = list(range(len(ps)))  # 조각마다 속한 덩어리의 대표 번호 (처음엔 자기 자신)

    def root(i):  # 조각 i 가 속한 덩어리의 대표를 찾는 함수
        while parent[i] != i:  # 대표에 닿을 때까지
            parent[i] = parent[parent[i]]  # 길을 줄여 다음에 빨리 찾게
            i = parent[i]  # 한 단계 위로
        return i  # 대표 번호

    order = sorted(range(len(ps)), key=lambda i: ps[i][0])  # 왼쪽 끝 순서로 정렬한 조각 번호
    for k, i in enumerate(order):  # 조각마다
        a = ps[i]  # 기준 조각
        for j in order[k + 1:]:  # 오른쪽에 있는 조각들
            b = ps[j]  # 비교할 조각
            if b[0] > a[2] + pad:  # 가로로 너무 멀면
                break  # 더 오른쪽은 볼 필요 없다
            if b[1] <= a[3] + pad_y and a[1] <= b[3] + pad_y:  # 세로로도 가까우면
                parent[root(i)] = root(j)  # 같은 덩어리로 합친다
    groups = {}  # 대표 번호 → 조각들
    for i, p in enumerate(ps):  # 조각마다
        groups.setdefault(root(i), []).append(p)  # 자기 덩어리에 넣는다
    return list(groups.values())  # 덩어리 목록


def text_rows(block, gap=1.4):  # 이름표 덩어리를 줄 단위로 나누는 함수
    out = []  # 줄들
    for p in sorted(block, key=lambda p: p[1]):  # 위에서 아래 순서로 조각마다
        if out and p[1] <= out[-1]["y1"] + gap:  # 마지막 줄과 세로로 겹치거나 가까우면
            out[-1]["p"].append(p)  # 그 줄에 넣는다
            out[-1]["y1"] = max(out[-1]["y1"], p[3])  # 줄의 아래 끝을 늘린다
        else:  # 멀면
            out.append({"y0": p[1], "y1": p[3], "p": [p]})  # 새 줄을 만든다
    for r in out:  # 줄마다
        r["x0"], r["x1"] = min(p[0] for p in r["p"]), max(p[2] for p in r["p"])  # 줄의 왼쪽·오른쪽 끝
    return out  # 줄 목록


def is_class_row(r):  # 한 줄이 반 표시(1-10 같은)인지 확인하는 함수
    """'1 - 10' 같은 반 표시: 숫자 무리 + (대시나 빈칸) + 숫자 무리."""  # 이 함수가 하는 일을 적은 설명글
    h = r["y1"] - r["y0"]  # 줄 높이
    if h < 2 or r["x1"] - r["x0"] > 4.5 * h or len(r["p"]) > 10:  # 너무 작거나, 너무 길거나, 조각이 너무 많으면
        return False  # 반 표시가 아니다
    tall = [p for p in r["p"] if p[3] - p[1] >= 0.2 * h]  # 키 큰 조각들 (숫자)
    dashes = [p for p in r["p"] if p[3] - p[1] < 0.25 * h and 0.15 * h < p[2] - p[0] < 0.8 * h  # 납작하고 적당히 긴 조각이
              and 0.3 < ((p[1] + p[3]) / 2 - r["y0"]) / h < 0.7]  # 줄 가운데 높이에 있으면 대시(-)
    groups = []  # 숫자 무리들 [왼, 오른]
    for a, b in sorted((p[0], p[2]) for p in tall):  # 숫자 조각을 왼쪽부터
        if groups and a <= groups[-1][1] + 0.9:  # 앞 무리와 가까우면
            groups[-1][1] = max(groups[-1][1], b)  # 같은 무리로 늘린다
        else:  # 멀면
            groups.append([a, b])  # 새 무리
    if len(groups) < 2:  # 숫자 무리가 둘이 안 되면
        return False  # 반 표시가 아니다
    g, i = max((groups[k + 1][0] - groups[k][1], k) for k in range(len(groups) - 1))  # 무리 사이 가장 넓은 틈과 그 위치
    left = [p for p in tall if p[2] <= groups[i][1] + 0.01]  # 틈 왼쪽 숫자들 (학년)
    right = [p for p in tall if p[0] >= groups[i + 1][0] - 0.01]  # 틈 오른쪽 숫자들 (반)
    span = lambda qs: max(q[3] for q in qs) - min(q[1] for q in qs)  # 조각들의 세로 높이를 재는 함수
    has_dash = any(groups[i][1] - 0.2 <= d[0] and d[2] <= groups[i + 1][0] + 0.2 for d in dashes)  # 틈 안에 대시가 있는지
    return (has_dash or g >= h) and span(left) > 0.6 * h and span(right) > 0.6 * h  # 대시나 넓은 틈이 있고 양쪽 숫자가 충분히 크면 반 표시


def bbox(ps):  # 조각들을 감싸는 네모를 구하는 함수
    return min(p[0] for p in ps), min(p[1] for p in ps), max(p[2] for p in ps), max(p[3] for p in ps)  # (왼, 위, 오른, 아래)


def scaled(ps, k, to=None, color=TEXT, around=None):  # 글자 조각을 키운 SVG 요소를 만드는 함수
    """글자 조각들을 가운데(around 를 주면 그 덩어리의 가운데)를 기준으로 k 배 키운 path.
    to 를 주면 그 좌표로 옮긴다."""
    x0, y0, x1, y1 = bbox(around or ps)  # 기준 덩어리를 감싸는 네모
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2  # 그 가운데
    nx, ny = to or (cx, cy)  # 옮길 자리 (안 주면 제자리)
    d = "".join(p[4] for p in ps)  # 조각 경로들을 하나로
    if k == 1 and not to:  # 키우지도 옮기지도 않으면
        return f'<path class="t" fill="{color}" stroke="{color}" stroke-width="{TEXT_BOLD}" stroke-linejoin="round" d="{d}"/>'  # 테두리만 더해 굵게
    return (f'<path class="t" fill="{color}" stroke="{color}" stroke-width="{fmt(TEXT_BOLD / k)}" stroke-linejoin="round" '  # 키운 만큼 테두리는 얇게 (화면 굵기 같게)
            f'transform="matrix({k} 0 0 {k} {fmt(nx - k * cx)} {fmt(ny - k * cy)})" d="{d}"/>')  # 가운데 기준 k 배 키우고 옮기는 변환


def x_groups(ps, gap=0.35):  # 한 줄의 조각을 글자 단위로 묶는 함수
    """한 줄의 글자 조각을 글자(음절) 단위로 묶는다."""  # 이 함수가 하는 일을 적은 설명글
    gs = []  # 글자 묶음들
    for p in sorted(ps, key=lambda p: p[0]):  # 왼쪽부터 조각마다
        if gs and p[0] <= gs[-1]["x1"] + gap:  # 앞 묶음과 가로로 겹치거나 가까우면
            gs[-1]["p"].append(p)  # 그 묶음에 넣는다
            gs[-1]["x1"] = max(gs[-1]["x1"], p[2])  # 오른쪽 끝을 늘린다
        else:  # 떨어져 있으면
            gs.append({"x0": p[0], "x1": p[2], "p": [p]})  # 새 묶음
    return gs  # 글자 묶음 목록


def syllables(ps, h):  # 조각을 한 글자(음절)씩 묶는 함수
    """글자 조각을 한 글자씩 묶는다. '사' 의 ㅅ·ㅏ 처럼 떨어진 좁은 조각 둘은
    합친 폭이 글자 높이 정도면 한 글자로 본다."""
    out = []  # 글자들
    for g in x_groups(ps, gap=0):  # 붙어 있는 조각 묶음마다
        last = out[-1] if out else None  # 바로 앞 글자
        if (last and last["n"] == 1 and last["x1"] - last["x0"] < 0.75 * h  # 앞 글자가 좁은 조각 하나이고
                and g["x1"] - g["x0"] < 0.75 * h and g["x1"] - last["x0"] <= 1.1 * h):  # 지금 것도 좁고 합쳐도 한 글자 폭이면
            last["p"] += g["p"]  # 한 글자로 합친다
            last["x1"] = max(last["x1"], g["x1"])  # 오른쪽 끝을 늘린다
            last["n"] = 2  # 두 조각짜리 글자 (더 합치지 않게)
        else:  # 아니면
            out.append({"x0": g["x0"], "x1": g["x1"], "p": list(g["p"]), "n": 1})  # 새 글자
    return out  # 글자 목록


def split_row(ps):  # 긴 줄을 두 줄로 나누는 함수
    """한 줄을 두 줄로 나눈다: 띄어쓰기가 있으면 가운데에 가까운 띄어쓰기에서,
    없으면 글자 수의 절반에서 (윗줄이 한 글자 더 길게)."""
    _, y0, _, y1 = bbox(ps)  # 줄의 위·아래
    h = y1 - y0  # 줄 높이
    sy = syllables(ps, h)  # 한 글자씩 묶는다
    if len(sy) < 2:  # 한 글자뿐이면
        return None  # 나눌 수 없다
    gaps = [sy[i + 1]["x0"] - sy[i]["x1"] for i in range(len(sy) - 1)]  # 글자 사이 간격들
    usual = sorted(gaps)[len(gaps) // 2]  # 보통 간격 (가운데 값)
    spaces = [i for i, g in enumerate(gaps) if g >= max(0.3 * h, 2 * usual)]  # 띄어쓰기로 볼 만큼 넓은 간격 위치
    if spaces:  # 띄어쓰기가 있으면
        mid = (sy[0]["x0"] + sy[-1]["x1"]) / 2  # 줄의 가운데
        i = min(spaces, key=lambda i: abs((sy[i]["x1"] + sy[i + 1]["x0"]) / 2 - mid))  # 가운데에 가장 가까운 띄어쓰기
    else:  # 없으면
        i = (len(sy) + 1) // 2 - 1  # 글자 수의 절반 (윗줄이 한 글자 더)
    return [p for g in sy[:i + 1] for p in g["p"]], [p for g in sy[i + 1:] for p in g["p"]]  # 윗줄 조각들, 아랫줄 조각들


def is_toilet_label(rs):  # 화장실 이름표인지 확인하는 함수
    """첫 줄이 'W101' 처럼 W 로 시작하고 아래에 한 줄(화장실)이 더 있으면 화장실 이름표.
    W 는 가늘고 긴 획 4개가 겹쳐 그려져 있어서, 줄 맨 앞의 가는 획 수로 알아본다."""
    if len(rs) < 2:  # 두 줄이 안 되면
        return False  # 아니다
    r = rs[0]  # 첫 줄
    h = max(p[3] - p[1] for p in r["p"])  # 첫 줄 높이
    if h < 2:  # 너무 작으면
        return False  # 아니다
    x0 = min(p[0] for p in r["p"])  # 첫 줄 왼쪽 끝
    strokes = [p for p in r["p"] if p[0] < x0 + 0.75 * h and p[2] - p[0] < 0.3 * h and p[3] - p[1] > 0.85 * h]  # 맨 앞의 가늘고 긴 획들
    return len(strokes) >= 3  # 3개 이상이면 W 로 본다


class Label:  # 이름표 하나를 다루는 틀
    """여러 줄(줄마다 글자 조각·색)을 한 덩어리로 키우고, 필요하면 두 줄로 나누고, 옮긴다."""  # 이 틀가 하는 일을 적은 설명글

    def __init__(self, rows, k):  # 이름표를 처음 만들 때
        self.rows = rows          # [(조각들, 색)]
        self.k = k  # 키울 배율
        x0, y0, x1, y1 = bbox([p for ps, _ in rows for p in ps])  # 모든 줄을 감싸는 네모
        self.c = ((x0 + x1) / 2, (y0 + y1) / 2)  # 이름표 가운데
        self.to = None  # 옮길 자리 (없으면 제자리)
        self.boxed = False  # 납작한 상자 안 이름표인지
        self.layout = [(ps, col, 0.0, 0.0) for ps, col in rows]   # 줄마다 (조각, 색, dx, dy)

    def size(self):  # 키운 뒤 크기를 재는 함수
        """키운 뒤의 너비·높이."""  # 이 함수가 하는 일을 적은 설명글
        boxes = [(a + dx, b + dy, c + dx, d + dy) for ps, _, dx, dy in self.layout for a, b, c, d in [bbox(ps)]]  # 줄마다 옮긴 뒤의 네모
        w = max(b[2] for b in boxes) - min(b[0] for b in boxes)  # 전체 폭
        h = max(b[3] for b in boxes) - min(b[1] for b in boxes)  # 전체 높이
        return w * self.k, h * self.k  # 배율을 곱한 크기

    def wrap(self):  # 가장 긴 줄을 두 줄로 나누는 함수
        """가장 긴 줄을 두 줄로 나눠 다시 쌓는다."""  # 이 함수가 하는 일을 적은 설명글
        lines = list(self.rows)  # 줄 목록 복사
        widths = [bbox(ps)[2] - bbox(ps)[0] for ps, _ in lines]  # 줄마다 폭
        i = widths.index(max(widths))  # 가장 긴 줄의 번호
        parts = split_row(lines[i][0])  # 그 줄을 둘로 나눈다
        if not parts:  # 못 나누면
            return False  # 그대로 둔다
        lines[i:i + 1] = [(parts[0], lines[i][1]), (parts[1], lines[i][1])]  # 긴 줄 자리에 두 줄을 넣는다 (색은 그대로)
        heights = [bbox(ps)[3] - bbox(ps)[1] for ps, _ in lines]  # 줄마다 높이
        gap = 0.45 * max(heights)  # 줄 사이 간격
        y = self.c[1] - (sum(heights) + gap * (len(lines) - 1)) / 2  # 첫 줄의 위 끝 (전체가 가운데에 오도록)
        self.layout = []  # 줄 배치를 새로 만든다
        for (ps, col), h in zip(lines, heights):  # 줄마다
            a, b, c, d = bbox(ps)  # 원래 자리
            self.layout.append((ps, col, self.c[0] - (a + c) / 2, y - b))  # 가로는 가운데로, 세로는 차례대로 옮긴다
            y += h + gap  # 다음 줄 위치
        return True  # 나눴다

    def box(self, at=None, margin=0.0):  # 이름표가 차지하는 네모를 구하는 함수
        w, h = self.size()  # 키운 크기
        cx, cy = at or self.to or self.c  # 가운데 (주어진 자리 → 옮길 자리 → 제자리)
        return box(cx - w / 2 - margin, cy - h / 2 - margin, cx + w / 2 + margin, cy + h / 2 + margin)  # 여백을 더한 네모

    def svg(self):  # 이름표를 SVG 요소로 만드는 함수
        k, (cx, cy) = round(self.k, 3), self.c  # 배율은 반올림한 값으로 위치도 계산해야 글자가 제자리에 온다
        nx, ny = self.to or self.c  # 그릴 자리
        out = []  # 줄마다 SVG 요소
        for ps, col, dx, dy in self.layout:  # 줄마다
            tx, ty = nx + k * (dx - cx), ny + k * (dy - cy)  # 키우고 옮긴 뒤의 이동량
            d = "".join(p[4] for p in ps)  # 줄의 경로들
            out.append(f'<path class="t" fill="{col}" stroke="{col}" stroke-width="{fmt(TEXT_BOLD / k)}" '  # 글자 색, 굵게 보이는 테두리
                       f'stroke-linejoin="round" transform="matrix({k:g} 0 0 {k:g} {fmt(tx)} {fmt(ty)})" d="{d}"/>')  # k 배 키우고 옮기는 변환
        return "".join(out)  # 모두 이은 글자


def room_width(regions, x, y):  # 한 점이 들어 있는 방의 가로 폭을 재는 함수
    """(x, y) 가 들어 있는 방에서 그 높이의 가로 폭."""  # 이 함수가 하는 일을 적은 설명글
    pt = Point(x, y)  # 그 점
    for r in regions:  # 방마다
        if r.contains(pt):  # 점이 그 방 안이면
            minx, _, maxx, _ = r.bounds  # 방의 왼쪽·오른쪽 끝
            seg = LineString([(minx - 1, y), (maxx + 1, y)]).intersection(r)  # 그 높이로 방을 가로지르는 선 중 방 안 부분
            for part in getattr(seg, "geoms", [seg]):  # 선 조각마다
                if part.length and part.distance(pt) < 1e-6:  # 그 점을 지나는 조각이면
                    return part.length  # 그 길이가 폭
    return None  # 방을 못 찾으면 없음


def room_height(regions, x, y):  # 한 점이 들어 있는 방의 세로 높이를 재는 함수
    """(x, y) 가 들어 있는 방에서 그 자리의 세로 높이."""  # 이 함수가 하는 일을 적은 설명글
    pt = Point(x, y)  # 그 점
    for r in regions:  # 방마다
        if r.contains(pt):  # 점이 그 방 안이면
            _, miny, _, maxy = r.bounds  # 방의 위·아래 끝
            seg = LineString([(x, miny - 1), (x, maxy + 1)]).intersection(r)  # 그 자리로 방을 세로로 가로지르는 선 중 방 안 부분
            for part in getattr(seg, "geoms", [seg]):  # 선 조각마다
                if part.length and part.distance(pt) < 1e-6:  # 그 점을 지나는 조각이면
                    return part.length  # 그 길이가 높이
    return None  # 방을 못 찾으면 없음


def fit(label, regions):  # 이름표를 방 크기에 맞추는 함수
    """방보다 넓으면 두 줄로 나누고, 그래도 넓으면 조금 줄인다 (원래 크기보다 작게는 안 함).
    - 짧은 글자(116 같은 번호, 두 글자 이름)는 세로로 긴 방이 아니면 나누지 않는다.
    - 한 줄짜리 납작한 칸(샤워.탈의실 같은 이름표 상자)은 두 줄이 들어가지 않으니 나누지 않고 상자에 맞춘다."""
    room = room_width(regions, *label.c)  # 이름표가 있는 방의 폭
    if not room:  # 방을 못 찾으면
        return  # 그대로 둔다
    limit = room * 0.9  # 이름표가 넘지 말아야 할 폭 (방의 90%)
    tall = room_height(regions, *label.c)  # 방의 높이
    if label.size()[0] > limit:  # 이름표가 방보다 넓으면
        x0, y0, x1, y1 = bbox([p for ps, _ in label.rows for p in ps])  # 원래 이름표 네모
        one_row = len(label.rows) == 1  # 한 줄짜리인지
        if one_row and tall and tall < 2.2 * (y1 - y0):  # 한 줄이고 방(칸)이 납작하면
            # 납작한 이름표 상자: 한 줄 그대로, 상자에 맞게만 키운다 (원래 크기보다 작게는 안 함)
            label.k = max(1.0, min(limit / (x1 - x0), tall * 0.9 / (y1 - y0)))  # 폭·높이 모두 들어가는 배율 (최소 1)
            label.boxed = True  # 상자 안 이름표는 옮기지 않는다
            return  # 끝
        # 나눌 줄(가장 넓은 줄)이 짧으면(116, 창 고) 세로로 긴 방에서만 나눈다 (창/고)
        rx0, ry0, rx1, ry1 = max((bbox(ps) for ps, _ in label.rows), key=lambda b: b[2] - b[0])  # 가장 넓은 줄의 네모
        short = (rx1 - rx0) < 2.5 * (ry1 - ry0)  # 글자 수가 적은 줄인지
        if not (short and (tall or 0) < 3 * (ry1 - ry0)):  # 짧은 줄인데 방이 세로로 길지 않은 경우만 빼고
            label.wrap()  # 두 줄로 나눈다
    w = label.size()[0]  # 지금 폭
    if w > limit:  # 그래도 넓으면
        label.k = max(1.0, label.k * limit / w)  # 방에 맞게 줄인다 (원래 크기 아래로는 안 함)


def find_spot(label, obstacles, taken, W, H):  # 화장실 이름표를 놓을 빈 자리를 찾는 함수
    """화장실 이름표: 선과 겹치지 않는 가장 가까운 빈 곳 (아래쪽 먼저)."""  # 이 함수가 하는 일을 적은 설명글
    cx, cy = label.c  # 원래 자리
    cands = []  # 후보 자리들
    for dy in range(-60, 91, 3):  # 위 60 ~ 아래 90 을 3 간격으로
        for dx in range(-60, 61, 3):  # 왼쪽 60 ~ 오른쪽 60 을 3 간격으로
            dist = (dx * dx + dy * dy) ** 0.5  # 원래 자리에서 거리
            if dist <= 90:  # 90 안이면
                cands.append((dist + (25 if dy < 0 else 0), dx, dy))  # 후보에 넣는다 (위쪽은 25 만큼 불리하게 → 아래쪽 먼저)
    for _, dx, dy in sorted(cands):  # 가까운 후보부터
        b = label.box((cx + dx, cy + dy), margin=1.2)  # 그 자리에 놓았을 때 차지하는 네모
        if b.bounds[0] < 0 or b.bounds[1] < 0 or b.bounds[2] > W or b.bounds[3] > H:  # 도면 밖으로 나가면
            continue  # 건너뛴다
        if len(obstacles.query(b, predicate="intersects")) or any(b.intersects(t) for t in taken):  # 선이나 다른 이름표와 겹치면
            continue  # 건너뛴다
        return (cx + dx, cy + dy)  # 빈 자리를 찾았다
    return None  # 못 찾으면 없음


def class_text(cx, cy, name):  # 반 표시 글자를 만드는 함수
    """반 표시 (예: 1-1, 자습실) 를 (cx, cy) 가운데에 파랗고 크게 쓴다."""  # 이 함수가 하는 일을 적은 설명글
    size = CLASS_SIZE if len(name) <= 4 else CLASS_SIZE * 0.8  # 글자가 길면 조금 작게
    return (f'<text x="{fmt(cx)}" y="{fmt(cy + size * 0.36)}" font-size="{fmt(size)}" font-weight="800" '  # 위치·크기·굵기
            f'font-family="{FONT}" text-anchor="middle" fill="{CLASS_COLOR}" letter-spacing="-0.3">{name}</text>')  # 글꼴, 가운데 정렬, 파란색


def text_layer(tags, floor_id, regions, obstacles, W, H):  # 도면의 글자를 모두 다시 그리는 함수
    """글씨 전부를 다시 그린다: 과목실 이름 지우기, 반 표시 새로 쓰기, 방 이름 키우기·줄 바꾸기, 화장실 이름 옮기기."""  # 이 함수가 하는 일을 적은 설명글
    out, small, rooms, labels, toilets = [], [], [], [], []  # 결과, 작은 글자, 교실, 이름표, 화장실 이름표
    pieces = text_pieces(tags)  # 글자 조각들
    for (x0, y0, x1, y1), name in RENAME.get(floor_id, []):  # 이 층에서 이름을 바꿀 방마다
        pieces = [p for p in pieces if not (p[0] >= x0 and p[2] <= x1 and p[1] >= y0 and p[3] <= y1)]  # 그 네모 안 글자를 지운다
        out.append(class_text((x0 + x1) / 2, (y0 + y1) / 2 + 1, name))  # 새 반 표시를 쓴다
    for block in label_blocks(pieces):  # 이름표 덩어리마다
        rs = text_rows(block)  # 줄로 나눈다
        if len(rs) == 3 and is_class_row(rs[2]) and all(r["y1"] - r["y0"] > 2 for r in rs):  # 세 줄이고 마지막이 반 표시면
            rooms.append(rs)  # 교실: 호수 / 이름 / 반
        elif len(rs) == 2 and is_class_row(rs[1]) and rs[0]["y1"] - rs[0]["y0"] > 2:  # 두 줄이고 아래가 반 표시면
            # '201 / 1-1' 처럼 호수와 반만 있는 교실: 반 표시만 파랗게
            labels.append(Label([(rs[0]["p"], TEXT), (rs[1]["p"], CLASS_COLOR)], LABEL_SCALE))  # 호수는 검게, 반은 파랗게
        elif max(r["y1"] - r["y0"] for r in rs) >= MIN_LABEL_H:  # 충분히 큰 글자면 (방 이름)
            lab = Label([(r["p"], TEXT) for r in rs], LABEL_SCALE)  # 이름표로 만든다
            fit(lab, regions)  # 방에 맞춘다
            (toilets if is_toilet_label(rs) and not lab.boxed else labels).append(lab)  # 화장실 이름표는 따로 (나중에 옮김)
        else:  # 작은 글자면 (DN·UP 등)
            small += block  # 그대로 둘 글자에 넣는다

    names = CLASS_TEXT.get(floor_id)  # 이 층의 반 이름 목록
    if names and len(names) != len(rooms):  # 찾은 교실 수와 반 이름 수가 다르면
        print(f"  ! {floor_id}: 교실 {len(rooms)}곳을 찾았는데 반 이름은 {len(names)}개 → 원래 글씨를 키우기만 한다")  # 경고
        names = None  # 반 이름을 쓰지 않는다
    rooms.sort(key=lambda rs: rs[2]["x0"])  # 교실을 왼쪽부터 정렬
    for i, (num, _name, cls) in enumerate(rooms):  # 교실마다 (호수, 과목 이름, 반)
        if names:  # 반 이름 목록이 있으면
            out.append(scaled(num["p"], NUMBER_SCALE))  # 호수만 키워 남긴다 (과목 이름은 지워짐)
            cx = (cls["x0"] + cls["x1"]) / 2  # 반 표시 가운데 x
            cy = (_name["y0"] + cls["y1"]) / 2 + 1  # 과목 이름과 반 표시 자리의 가운데 y
            out.append(class_text(cx, cy, names[i]))  # 새 반 표시를 크게 쓴다
        else:  # 없으면
            labels.append(Label([(num["p"], TEXT), (cls["p"], CLASS_COLOR)], LABEL_SCALE))  # 호수와 반만 남겨 키운다

    taken = [lab.box(margin=0.5) for lab in labels]  # 이미 이름표가 차지한 자리들
    moved = 0  # 옮긴 화장실 이름표 수
    for lab in toilets:  # 화장실 이름표마다
        spot = find_spot(lab, obstacles, taken, W, H)  # 빈 자리를 찾는다
        if spot and spot != lab.c:  # 다른 자리를 찾았으면
            lab.to = spot  # 그리로 옮긴다
            moved += 1  # 옮긴 수 +1
        taken.append(lab.box(margin=0.5))  # 이 이름표 자리도 차지한 것으로
    out += [lab.svg() for lab in labels + toilets]  # 모든 이름표를 그린다
    if small:  # 작은 글자가 있으면
        out.append(scaled(small, 1))  # 크기 그대로 굵게만
    return out, len(rooms), moved  # 글자 요소들, 교실 수, 옮긴 수


# ── 치수·높이 표시 지우기 ─────────────────────────────
# 학생들이 보기 어려운 표시(치수선과 숫자, ±0·-280 같은 높이 표시, 축 번호 동그라미 등)를 도면에서 뺀다.
TICK = 1.8                 # 이보다 작은 검은 점(채운 글자 조각)은 치수선의 눈금으로 본다


def path_segments(sub):  # 경로 조각을 직선 조각들로 나누는 함수
    """곡선 없는 하위 경로를 직선 조각 [(시작, 끝)] 으로. 곡선이 있으면 None."""  # 이 함수가 하는 일을 적은 설명글
    if "C" in sub:  # 곡선이 있으면
        return None  # 다루지 않는다
    pts = points(sub)  # 점들
    segs = list(zip(pts, pts[1:]))  # 이웃한 두 점씩 직선 조각
    if sub.rstrip().endswith("Z") and len(pts) > 2:  # 닫힌 경로면
        segs.append((pts[-1], pts[0]))  # 마지막 점 → 처음 점 조각도 더한다
    return segs  # 직선 조각 목록


def axis_line(a, b):  # 직선 조각이 수평·수직인지 확인하는 함수
    """수평·수직 직선 조각이면 ('h'|'v', 고정 좌표, 시작, 끝), 아니면 None."""  # 이 함수가 하는 일을 적은 설명글
    (x0, y0), (x1, y1) = a, b  # 두 끝점
    if abs(y1 - y0) < 0.3 and abs(x1 - x0) >= 3:  # y 가 거의 같고 충분히 길면
        return ("h", (y0 + y1) / 2, min(x0, x1), max(x0, x1))  # 수평선
    if abs(x1 - x0) < 0.3 and abs(y1 - y0) >= 3:  # x 가 거의 같고 충분히 길면
        return ("v", (x0 + x1) / 2, min(y0, y1), max(y0, y1))  # 수직선
    return None  # 기울어진 선


def along(o, x, y):  # 선 방향 기준 좌표로 바꾸는 함수
    return (x, y) if o == "h" else (y, x)  # 수평선이면 그대로, 수직선이면 x·y 를 바꾼다 (선을 따라가는 값이 앞에)


def find_dimensions(tags):  # 치수선을 찾는 함수
    """치수선: 곧은 선 위에 눈금(작은 검은 점)이 두 곳 이상 있고, 계단 디딤판처럼
    촘촘히 겹쳐 놓인 평행선이 아닌 것. 그 선에 끝이 닿는 보조선과 옆의 숫자도 함께 찾는다.
    돌려주는 값: ({(태그, 하위경로): 지울 조각 번호 집합}, 지울 글자 하위경로 집합)"""
    lines, ticks, texts = [], [], []  # 수평·수직 선들, 눈금 점들, 글자 조각들
    for ti, a in enumerate(tags):  # 도면 요소마다
        for si, sub in enumerate(subpaths(a["d"])):  # 경로 조각마다
            pts = points(sub)  # 점들
            if not pts:  # 점이 없으면
                continue  # 건너뛴다
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]  # x 들, y 들
            small = max(xs) - min(xs) <= TICK and max(ys) - min(ys) <= TICK  # 아주 작은 조각인지 (눈금 후보)
            c = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)  # 조각 가운데
            if a["class"] == "t":  # 글자(채운 모양)면
                texts.append((c, sub))  # 글자 목록에
                if small:  # 작으면
                    ticks.append(c)  # 눈금 목록에도
            elif a["class"] in ("m", "w"):  # 중간·굵은 선이면
                for k, (p, q) in enumerate(path_segments(sub) or []):  # 직선 조각마다
                    ax = axis_line(p, q)  # 수평·수직인지
                    if ax:  # 그렇다면
                        lines.append((ti, si, k, ax))  # 선 목록에 (요소 번호, 조각 번호, 직선 번호, 선 정보)
    grid = {}  # 눈금을 6×6 칸으로 나눠 담는 표 (빨리 찾기 위해)
    for x, y in ticks:  # 눈금마다
        grid.setdefault((int(x // 6), int(y // 6)), []).append((x, y))  # 그 칸에 넣는다

    def near(x0, y0, x1, y1):  # 네모 근처의 눈금들을 꺼내는 함수
        for gx in range(int(x0 // 6) - 1, int(x1 // 6) + 2):  # 주변 칸 (가로)
            for gy in range(int(y0 // 6) - 1, int(y1 // 6) + 2):  # 주변 칸 (세로)
                yield from grid.get((gx, gy), ())  # 그 칸의 눈금들을 하나씩 내보낸다

    by_axis = {"h": [], "v": []}  # 방향별 선 목록
    for ln in lines:  # 선마다
        by_axis[ln[3][0]].append(ln[3])  # 수평/수직 목록에 넣는다

    def stacked(ax):  # 평행선이 겹겹이 있는 곳인지 확인하는 함수
        """비슷한 길이의 평행선이 가까이 둘 이상 → 계단 디딤판·창틀 같은 것."""  # 이 함수가 하는 일을 적은 설명글
        o, c, a, b = ax  # 방향, 고정 좌표, 시작, 끝
        n = 0  # 가까운 평행선 수
        for o2, c2, a2, b2 in by_axis[o]:  # 같은 방향 선마다
            if 0.3 < abs(c2 - c) < 8 and min(b, b2) - max(a, a2) > 0.5 * (b - a) and 0.7 < (b2 - a2) / (b - a) < 1.4:  # 가깝고 많이 겹치고 길이가 비슷하면
                n += 1  # 센다
        return n >= 2  # 둘 이상이면 계단·창틀

    dims = []  # 치수선들
    for ti, si, k, ax in lines:  # 선마다
        o, c, a, b = ax  # 방향, 고정 좌표, 시작, 끝
        x0, y0 = along(o, a, c)  # 선 시작점 (실제 좌표)
        x1, y1 = along(o, b, c)  # 선 끝점 (실제 좌표)
        marks = {round(along(o, x, y)[0]) for x, y in near(x0, y0, x1, y1)  # 선 근처 눈금 중
                 if abs(along(o, x, y)[1] - c) <= 0.7 and a - 2.5 <= along(o, x, y)[0] <= b + 2.5}  # 선 위에 딱 놓인 것들의 위치
        if len(marks) >= 2 and max(marks) - min(marks) >= 3 and not stacked(ax):  # 떨어진 눈금이 두 곳 이상이고 계단이 아니면
            dims.append((ti, si, k, ax))  # 치수선
    # 같은 줄에 이어진 선도 치수선 (눈금이 짧은 선으로 그려진 줄)
    found = {(ti, si, k) for ti, si, k, _ in dims}  # 이미 찾은 치수선 번호들
    grew = True  # 새로 찾은 게 있는지
    while grew:  # 더 찾을 게 없을 때까지
        grew = False  # 일단 없다고 보고
        for ti, si, k, ax in lines:  # 선마다
            if (ti, si, k) in found or stacked(ax):  # 이미 찾았거나 계단이면
                continue  # 건너뛴다
            o, c, a, b = ax  # 방향, 고정 좌표, 시작, 끝
            if any(o == d[0] and abs(c - d[1]) < 0.3 and a <= d[3] + 3 and b >= d[2] - 3 for *_, d in dims):  # 치수선과 같은 줄에 이어져 있으면
                dims.append((ti, si, k, ax))  # 치수선에 더한다
                found.add((ti, si, k))  # 찾은 것으로
                grew = True  # 새로 찾았다
    drop = {}  # (요소, 조각) → 지울 직선 번호들
    for ti, si, k, _ in dims:  # 치수선마다
        drop.setdefault((ti, si), set()).add(k)  # 지울 목록에
    for ti, si, k, (o, c, a, b) in lines:  # 선마다
        for _, _, _, (do, dc, da, db) in dims:  # 치수선마다
            if do != o and da - 4 <= c <= db + 4 and (abs(a - dc) <= 4 or abs(b - dc) <= 4):  # 치수선에 수직으로 끝이 닿으면
                drop.setdefault((ti, si), set()).add(k)  # 보조선
                break  # 다음 선으로
    gone = set()  # 지울 글자(숫자) 조각들
    for (x, y), sub in texts:  # 글자 조각마다
        for _, _, _, (o, c, a, b) in dims:  # 치수선마다
            u, v = along(o, x, y)  # 선 방향 기준 좌표
            if abs(v - c) <= 6.5 and a - 3 <= u <= b + 3:  # 치수선 바로 옆에 있으면 (치수 숫자)
                gone.add(sub)  # 지운다
                break  # 다음 글자로
    return drop, gone, len(dims)  # 지울 선, 지울 글자, 치수선 수


def level_marks(text):  # 높이 표시(±0, +280 등)를 찾는 함수
    """'±0', '+ 280', '- 130' 같은 높이 표시: 부호(짧은 가로줄이 있는 작은 기호) 바로 뒤에 숫자 1~3개."""  # 이 함수가 하는 일을 적은 설명글
    gone = set()  # 지울 조각들
    for block in label_blocks(text):  # 글자 덩어리마다
        for r in text_rows(block):  # 줄마다
            h = r["y1"] - r["y0"]  # 줄 높이
            if h < 1 or h > 8:  # 너무 작거나 크면
                continue  # 높이 표시가 아니다
            gs = x_groups(r["p"], gap=0)  # 글자 단위로 묶는다
            digit = lambda g: (g["x1"] - g["x0"]) <= 0.75 * h and max(p[3] for p in g["p"]) - min(p[1] for p in g["p"]) >= 0.65 * h  # 좁고 키 큰 글자 = 숫자
            def sign(g):  # 부호(-, +, ±)인지 확인하는 함수
                if (g["x1"] - g["x0"]) > 1.1 * h:  # 너무 넓으면
                    return False  # 아니다
                if len(g["p"]) == 1 and g["p"][0][3] - g["p"][0][1] <= 0.3 * h and g["p"][0][2] - g["p"][0][0] >= 0.3 * h:  # 납작한 가로줄 하나면
                    return True  # -
                # + · ± : 폭과 높이가 비슷하고, 곡선 없이 가로·세로 선만으로 된 다각형 (꼭짓점 10개 이상)
                gw = g["x1"] - g["x0"]  # 폭
                gh = max(p[3] for p in g["p"]) - min(p[1] for p in g["p"])  # 높이
                if gw < 0.45 * h or not 0.7 < gw / max(gh, 0.01) < 1.4:  # 너무 좁거나 정사각형에 가깝지 않으면
                    return False  # 아니다
                corners = 0  # 꼭짓점 수
                for p in g["p"]:  # 조각마다
                    pts = points(p[4])  # 점들
                    if "C" in p[4] or any(abs(a[0] - b[0]) > 0.15 and abs(a[1] - b[1]) > 0.15 for a, b in zip(pts, pts[1:])):  # 곡선이나 비스듬한 선이 있으면
                        return False  # 아니다
                    corners += len(pts)  # 꼭짓점을 센다
                return corners >= 10  # 10개 이상이면 + 또는 ±
            for i, g in enumerate(gs):  # 글자마다
                if not sign(g) or (i and g["x0"] - gs[i - 1]["x1"] < 0.8 * h):  # 부호가 아니거나 앞 글자에 붙어 있으면
                    continue  # 건너뛴다
                j = i + 1  # 부호 다음 글자부터
                while j < len(gs) and j - i <= 3 and digit(gs[j]) and gs[j]["x0"] - gs[j - 1]["x1"] < 0.8 * h:  # 숫자가 붙어서 이어지는 동안 (최대 3개)
                    j += 1  # 다음 글자로
                if j - i >= 2 and (j == len(gs) or gs[j]["x0"] - gs[j - 1]["x1"] >= 0.8 * h):  # 숫자가 하나 이상 있고 뒤가 떨어져 있으면
                    gone |= {p[4] for g2 in gs[i:j] for p in g2["p"]}  # 부호와 숫자를 지운다
    return gone  # 지울 조각들


def strip_marks(tags, floor_id):  # 도면에서 필요 없는 표시를 지우는 함수
    """도면 태그에서 치수선·숫자, 높이 표시, '홀', ERASE 네모 안의 표시를 지운 새 태그 목록과 지운 개수."""  # 이 함수가 하는 일을 적은 설명글
    drop, gone, n_dims = find_dimensions(tags)  # 치수선과 치수 숫자를 찾는다
    text = text_pieces(tags)  # 글자 조각들
    # 치수 숫자가 절반 넘게 걸린 글자 덩어리는 통째로 (숫자 일부만 남지 않게)
    for block in label_blocks(text):  # 글자 덩어리마다
        if sum(p[4] in gone for p in block) * 2 >= len(block):  # 절반 이상이 지울 글자면
            gone |= {p[4] for p in block}  # 덩어리 전체를 지운다
    gone |= level_marks([p for p in text if p[4] not in gone])  # 높이 표시도 지운다
    kept = without_hall([p for p in text if p[4] not in gone])  # '홀' 을 뺀 남은 글자
    gone |= {p[4] for p in text} - {p[4] for p in kept}  # 빠진 '홀' 도 지울 목록에
    boxes = ERASE.get(floor_id, [])  # 이 층에서 직접 지울 네모들
    inside = lambda b, x0, y0, x1, y1: b[0] <= x0 and x1 <= b[2] and b[1] <= y0 and y1 <= b[3]  # 네모가 b 안에 통째로 들어가는지
    for b, what in boxes:  # 지울 네모마다
        if what == "text":  # 글자만 지우는 네모면
            keep = KEEP.get(floor_id, [])  # 남길 이름표 네모들
            small = [p for p in text if max(p[2] - p[0], p[3] - p[1]) <= 2.4]  # 작은 글자 조각들
            # 세로로 쓴 메모: 작은 글자 조각이 같은 왼쪽 끝에 넷 이상 세로로 쌓여 있다
            column = lambda p: p[2] - p[0] <= 2.4 and p[3] - p[1] <= 1.6 and sum(abs(q[0] - p[0]) <= 0.15 for q in small) >= 4  # 세로 메모 글자인지
            gone |= {p[4] for p in text if inside(b, *p[:4])  # 네모 안 글자 중
                     and not any(inside(k, *p[:4]) and not column(p) for k in keep)}  # 남길 이름표가 아닌 것을 지운다
    out = []  # 새 요소 목록
    for ti, a in enumerate(tags):  # 요소마다
        subs = []  # 남길 경로 조각들
        for si, sub in enumerate(subpaths(a["d"])):  # 경로 조각마다
            pts = points(sub)  # 점들
            if pts and any(what == "all" for _, what in boxes):  # "all" 네모가 있으면
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]  # x 들, y 들
                if any(what == "all" and inside(b, min(xs), min(ys), max(xs), max(ys)) for b, what in boxes):  # 그 안에 통째로 들어가면
                    continue  # 지운다
            if a["class"] == "t" and sub in gone:  # 지울 글자면
                continue  # 지운다
            ks = drop.get((ti, si))  # 이 조각에서 지울 직선 번호들
            if ks:  # 있으면
                segs = path_segments(sub)  # 직선 조각들
                subs += [f"M{fmt(p[0])} {fmt(p[1])}L{fmt(q[0])} {fmt(q[1])}" for k, (p, q) in enumerate(segs) if k not in ks]  # 지울 것만 빼고 직선을 하나씩 다시 쓴다
                continue  # 다음 조각
            subs.append(sub)  # 그대로 남긴다
        if subs:  # 남은 조각이 있으면
            out.append(dict(a, d="".join(subs)))  # 경로만 바꾼 새 요소
    return out, n_dims  # 새 요소 목록과 치수선 수


# ── 문 · 위생기구 ───────────────────────────────────
def is_curve(sub):  # 곡선이 들어 있는지 확인하는 함수
    return "C" in sub  # C 명령이 있으면 곡선


def closed(pts):  # 닫힌 모양인지 확인하는 함수
    return len(pts) > 2 and abs(pts[0][0] - pts[-1][0]) < 0.05 and abs(pts[0][1] - pts[-1][1]) < 0.05  # 처음 점과 끝 점이 거의 같으면 닫힘


def door_or_fixture(sub, pts):  # 문인지 위생기구인지 고르는 함수
    """곡선이 들어간 작은 모양: 열린 호 → 문, 닫힌 모양 → 위생기구."""  # 이 함수가 하는 일을 적은 설명글
    if not is_curve(sub) or len(pts) < 3:  # 곡선이 없거나 점이 적으면
        return None  # 둘 다 아니다
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]  # x 들, y 들
    w, h = max(xs) - min(xs), max(ys) - min(ys)  # 폭과 높이
    if closed(pts) or sub.rstrip().endswith("Z"):  # 닫힌 모양이면
        return "fixture" if 0.8 < max(w, h) < 8 else None  # 작으면 위생기구 (변기·세면대)
    return "door" if 2.5 < max(w, h) < 16 else None  # 열린 호이고 문 크기면 문


def door_closers(sub):  # 문 자리를 막는 선을 만드는 함수
    """문 호의 경첩(원의 중심)에서 양 끝까지 선을 그어 문 자리를 막는다 (방과 복도를 따로 칠하려고)."""  # 이 함수가 하는 일을 적은 설명글
    out = []  # 막는 선들
    for args in re.findall(r"C([^MLCZ]*)", sub):  # 곡선 명령마다
        v = [float(x) for x in re.findall(r"-?\d*\.?\d+", args)]  # 곡선 숫자들
        start = re.findall(r"(-?\d*\.?\d+) (-?\d*\.?\d+)(?=C)", sub)  # 곡선 바로 앞의 점 (시작점)
        if len(v) < 6 or not start:  # 숫자가 모자라거나 시작점이 없으면
            continue  # 건너뛴다
        p0 = tuple(map(float, start[0]))  # 시작점
        c1, c2, p3 = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])  # 조절점 두 개와 끝점
        # 중심: p0 에서 (c1-p0) 에 수직인 직선 과 p3 에서 (c2-p3) 에 수직인 직선의 교점
        d1 = (c1[0] - p0[0], c1[1] - p0[1])  # 시작점에서의 접선 방향
        d2 = (c2[0] - p3[0], c2[1] - p3[1])  # 끝점에서의 접선 방향
        det = d1[0] * d2[1] - d1[1] * d2[0]  # 두 직선이 만나는지 알려주는 값 (0 이면 평행)
        if abs(det) < 1e-6:  # 평행하면
            continue  # 중심을 못 구한다
        b1 = d1[0] * p0[0] + d1[1] * p0[1]  # 첫째 직선 식의 오른쪽 값
        b2 = d2[0] * p3[0] + d2[1] * p3[1]  # 둘째 직선 식의 오른쪽 값
        cx = (b1 * d2[1] - b2 * d1[1]) / det  # 교점 x (연립방정식 풀이)
        cy = (d1[0] * b2 - d2[0] * b1) / det  # 교점 y
        out += [LineString([(cx, cy), p0]), LineString([(cx, cy), p3])]  # 경첩 → 양 끝 선 두 개
        break  # 곡선 하나면 충분
    return out  # 막는 선들


# ── 바닥 색 ─────────────────────────────────────────
def floor_regions(lines, W, H):  # 벽으로 나뉜 방 영역들을 찾는 함수
    sheet = box(0, 0, W, H)  # 도면 전체 네모
    walls = unary_union([l.buffer(WALL_GAP) for l in lines])  # 벽 선을 두껍게 해서 합친다 (작은 틈은 막힘)
    space = sheet.difference(walls)  # 벽을 뺀 빈 곳들
    out = []  # 방 영역들
    for r in getattr(space, "geoms", [space]):  # 빈 곳 조각마다
        if r.area < 25:  # 너무 작으면
            continue  # 건너뛴다
        minx, miny, maxx, maxy = r.bounds  # 조각을 감싸는 네모
        if minx <= 0.5 or miny <= 0.5 or maxx >= W - 0.5 or maxy >= H - 0.5:  # 도면 가장자리에 닿으면
            continue  # 건물 밖
        if r.area > W * H * 0.6:  # 도면의 60% 보다 크면
            continue  # 방이 아니다 (새어 나간 것)
        thick = 2 * r.area / r.length  # 평균 두께 (넓이 ÷ 둘레의 절반)
        if thick < 2.5:  # 너무 가늘면
            continue  # 벽 속 같은 가는 틈
        out.append(r)  # 방으로 넣는다
    return out  # 방 영역 목록


def classify(region, fixtures):  # 영역이 방·복도·화장실 중 무엇인지 고르는 함수
    thick = 2 * region.area / region.length  # 평균 두께
    length = region.length / 2  # 대략적인 길이
    if length / thick > 8:  # 아주 길쭉하면
        return "hall" if 12 <= thick < 35 else None  # 폭이 아주 좁고 긴 것은 치수 띠 → 칠하지 않음
    inside = sum(1 for f in fixtures if region.contains(f))  # 안에 있는 위생기구 수
    return "wet" if inside >= 2 else "room"  # 2개 이상이면 화장실, 아니면 방


def decorate(path):  # 층 도면 하나를 꾸미는 함수
    s = open(path, encoding="utf-8").read()  # 도면 SVG 를 읽는다
    if MARK in s:  # 이미 꾸민 표시가 있으면
        return None  # 이미 꾸민 도면 (글씨를 두 번 키우지 않게)
    head = s[: s.index(">", s.index("<svg")) + 1]  # <svg ...> 시작 태그
    W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head).groups())  # 도면 가로·세로 크기
    tags = [attrs_of(t) for t in re.findall(r"<path [^>]*/>", s)]  # 모든 경로 요소의 속성들
    tags, n_dims = strip_marks(tags, os.path.basename(path)[:-4])  # 필요 없는 표시를 지운다

    lines, fixtures, fixture_lines = [], [], []  # 벽 선들, 위생기구 가운데 점들, 위생기구 선들
    doors_d, fixtures_d = [], []  # 문 경로들, 위생기구 경로들
    out = []  # 다시 쓸 선 요소들
    for a in tags:  # 요소마다
        cls = a["class"]  # 선 종류
        if cls == "t":  # 글자면
            continue  # 글씨는 text_layer 가 따로 그린다
        keep = []  # 남길 조각들
        for sub in subpaths(a["d"]):  # 경로 조각마다
            pts = points(sub)  # 점들
            kind = door_or_fixture(sub, pts) if cls in ("m", "l", "w") else None  # 선이면 문·위생기구인지 확인
            if kind == "door":  # 문이면
                doors_d.append(sub)  # 문 경로에 모은다
                lines += door_closers(sub)  # 문 자리를 막는 선을 벽에 더한다
            elif kind == "fixture":  # 위생기구면
                fixtures_d.append(sub)  # 위생기구 경로에 모은다
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]  # x 들, y 들
                fixtures.append(Point((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))  # 가운데 점 (화장실 찾기용)
                if len(pts) > 1:  # 선이 되면
                    fixture_lines.append(LineString(pts))  # 이름표가 피해야 할 선
            else:  # 나머지는
                keep.append(sub)  # 그대로 남긴다
            if cls in ("w", "m") and len(pts) > 1 and kind != "fixture":  # 굵은·중간 선이면 (위생기구 빼고)
                lines.append(LineString(pts))  # 벽 선으로
        if not keep:  # 남은 게 없으면
            continue  # 다음 요소
        d = "".join(keep)  # 남은 조각들
        if cls == "h":  # 빗금이면
            out.append(f'<path class="h" fill="{a.get("fill", "#d1d5db")}" d="{d}"/>')  # 원래 색으로 채운다
        else:  # 선이면
            out.append(f'<path class="{cls}" fill="none" stroke="{a["stroke"]}" stroke-linecap="round" '  # 원래 색, 둥근 끝
                       f'stroke-linejoin="round" stroke-width="{a["stroke-width"]}" d="{d}"/>')  # 원래 굵기
    if doors_d:  # 문이 있으면
        out.append(f'<path class="door" fill="none" stroke="{DOOR}" stroke-linecap="round" stroke-width="0.45" d="{"".join(doors_d)}"/>')  # 나무색 문 호
    if fixtures_d:  # 위생기구가 있으면
        out.append(f'<path class="fixture" fill="#ffffff" stroke="{FIXTURE}" stroke-width="0.35" d="{"".join(fixtures_d)}"/>')  # 흰 바탕, 파란 선

    deco = []  # 바닥 색 요소들
    regions = floor_regions(lines, W, H)  # 방 영역들을 찾는다
    obstacles = STRtree(lines + fixture_lines)  # 이름표가 피할 선들 (빨리 찾기용)
    texts, rooms, moved = text_layer(tags, os.path.basename(path)[:-4], regions, obstacles, W, H)  # 글자를 다시 그린다
    by_kind = {}  # 종류(복도·방·화장실) → 영역들
    for r in regions:  # 영역마다
        kind = classify(r, fixtures)  # 종류를 고른다
        if kind:  # 칠할 종류면
            by_kind.setdefault(kind, []).append(r.buffer(WALL_GAP))  # 벽 아래까지 조금 넓혀서 모은다
    for kind in ("hall", "room", "wet"):  # 복도 → 방 → 화장실 순서로
        if kind in by_kind:  # 그 종류가 있으면
            parts = [g.buffer(0).simplify(0.4) for g in by_kind[kind]]  # 점 수 줄이기 (파일 크기)
            try:  # 합치기를 시도한다
                shape = unary_union(parts)  # 모두 합친 모양
                d = poly_d(shape)  # 경로 글자로
            except Exception:  # 모양이 꼬여서 합치기 실패 → 하나씩 그린다
                d = "".join(poly_d(g) for g in parts if not g.is_empty)  # 조각마다 경로를 이어 붙인다
            deco.append(f'<path fill="{FLOOR[kind]}" fill-rule="evenodd" d="{d}"/>')  # 바닥 색 요소

    head = head.replace("<svg", f"<svg {MARK}", 1)  # 꾸민 표시를 붙인다
    result = head + '<g id="deco">' + "".join(deco) + "</g>" + "".join(out) + "".join(texts) + "</svg>"  # 바닥 색(맨 아래) + 선 + 글자
    open(path, "w", encoding="utf-8").write(result)  # 파일에 저장한다
    counts = {k: len(v) for k, v in by_kind.items()}  # 종류별 영역 수
    return rooms, moved, len(doors_d), len(fixtures_d), counts, len(result) // 1024  # 결과 숫자들


def main():  # 모든 층 도면을 꾸미는 함수
    sys.stdout.reconfigure(encoding="utf-8")  # 화면 출력을 UTF-8 로 (한글이 깨지지 않게)
    for path in sorted(glob.glob(os.path.join(ROOT, "plans", "*.svg"))):  # plans 폴더의 SVG 마다
        if os.path.basename(path) == "site.svg":  # 전체 배치도면
            continue  # 건너뛴다 (decorate_site.py 가 맡음)
        res = decorate(path)  # 꾸민다
        if res is None:  # 이미 꾸민 도면이면
            print(f"{os.path.basename(path):12} 이미 꾸민 도면이라 건너뜀 (build_plans.py 로 다시 만든 뒤 실행)")  # 안내
            continue  # 다음 도면
        rooms, moved, doors, fixtures, counts, kb = res  # 결과 숫자들
        print(f"{os.path.basename(path):12} 교실 {rooms:3}  화장실 이름 옮김 {moved}  문 {doors:3}  기구 {fixtures:3}  바닥 {counts}  {kb} KB")  # 결과를 보여준다


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    main()  # 실행
