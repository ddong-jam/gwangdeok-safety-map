"""전체 배치도(plans/site.svg)를 위성사진처럼 꾸민다.

- 선을 진하게 (확대·축소해도 화면에서 같은 굵기)
- 없어진 양궁장 지우기 (체육실동은 남김)
- 도로·운동장·트랙·잔디·중정·주차장·숲·나무 색칠

usage: python tools/decorate_site.py   (build_plans.py 다음에 실행. 여러 번 실행해도 결과는 같다)
필요: pip install shapely
"""
import math  # 삼각함수(sin·cos)와 원주율 같은 수학 도구
import os  # 폴더·파일 경로 도구
import random  # 나무·꽃을 자연스럽게 흩어 놓을 무작위 수 도구
import re  # 글자 패턴(정규식)으로 SVG 를 읽는 도구

from shapely.geometry import LineString, Point, Polygon, box  # 도형 도구: 선, 점, 다각형, 네모
from shapely.ops import unary_union  # 여러 도형을 하나로 합치는 도구

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 프로젝트 맨 위 폴더
SITE = os.path.join(ROOT, "plans", "site.svg")  # 꾸밀 전체 배치도 파일

# 도면은 남쪽이 위 (위성사진을 180° 돌린 방향)
ARCHERY = (180, 228, 322, 266)        # 양궁장: 이 안의 선·글자는 모두 지운다
ARCHERY_EDGE = (322, 228, 342, 266)   # 체육실동과 겹치는 곳: 양궁장 점무늬(아주 작은 조각)만 지운다
# 실제와 맞지 않는 도면 표시: 이 안에 완전히 들어가는 선·글자는 지운다 (위성사진과 비교)
ERASE = [  # 지울 영역 목록 (왼쪽, 위, 오른쪽, 아래)
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
]  # 지울 영역 목록 끝
# 도면 글씨를 지우고 웹 글꼴로 다시 쓰는 곳: (지울 영역, 글자, 가운데 좌표, 크기)
RETEXT = [((231, 383, 277, 394), "대운동장", (254, 389), 17),  # 대운동장 글자를 크게 다시 쓴다
          ((458, 245, 491, 258), "소운동장", (527, 288), 9)]  # 소운동장 글자는 정원 아래쪽으로 옮겨 쓴다
FONT = "Pretendard, 'Malgun Gothic', sans-serif"  # 다시 쓰는 글자의 글꼴

LINE = {"l": ("#475569", 0.6), "m": ("#1e293b", 1.0), "w": ("#0f172a", 1.7)}  # 색, 화면 px 굵기
TEXT = "#0f172a"  # 도면 글자 색 (진한 남색)

C = {  # 꾸미기에 쓰는 색 모음
    "campus": "#f6f2e9", "road": "#d5dae1", "dirt": "#eadbbd", "track": "#d9b38c",  # 학교 땅, 도로, 흙, 트랙
    "turf": "#7dbb67", "turf2": "#74b25e", "lawn": "#c3e1aa", "path": "#efe4cb",  # 인조잔디 두 색, 잔디밭, 산책길
    "sand": "#f1e6cc", "forest": "#b5d69b", "tree": "#79b05f", "tree2": "#5f9a49", "park": "#cfd5dc", "court": "#4f8fbf", "court_key": "#3d7aa8", "court_edge": "#c9b48f",  # 모래, 숲, 나무 두 색, 주차장, 농구장 바닥·골밑·테두리
    "bench": "#b98a5a",  # 벤치 나무색
}  # 색 모음 끝

ROAD_SEEDS = [(300, 3), (590, 60), (697, 450), (400, 667)]  # 도로 위에 확실히 있는 점들 (여기서 도로 영역을 찾는다)
CAMPUS_SEED = (470, 600)  # 학교 땅 안에 확실히 있는 점


# ── SVG 읽기 ─────────────────────────────────────
def attrs_of(tag):  # SVG 태그의 속성들을 사전으로 꺼내는 함수
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))  # 이름="값" 을 모두 찾아 {이름: 값} 으로


def subpaths(d):  # 경로(d)를 M 으로 시작하는 조각들로 나누는 함수
    return [s for s in re.split(r"(?=M)", d) if s]  # M 앞에서 자르고 빈 조각은 버린다


def nums(s):  # 글자 속 숫자들을 꺼내는 함수
    return [float(v) for v in re.findall(r"-?\d*\.?\d+", s)]  # 음수·소수 포함 숫자를 모두 실수로


def points(sub):  # 경로 조각의 점 목록을 만드는 함수
    """하위 경로의 점들 (곡선은 몇 점으로 나눠 근사)."""  # 이 함수가 하는 일을 적은 설명글
    pts = []  # 점 목록
    for cmd, args in re.findall(r"([MLCZ])([^MLCZ]*)", sub):  # 명령(M·L·C·Z)과 그 숫자들마다
        v = nums(args)  # 숫자들
        if cmd in "ML":  # 이동·직선이면
            pts += list(zip(v[0::2], v[1::2]))  # (x, y) 쌍으로 묶어 넣는다
        elif cmd == "C":  # 곡선이면
            for i in range(0, len(v) - 5, 6):  # 숫자 6개(조절점 2개 + 끝점)씩
                p0 = pts[-1] if pts else (v[i], v[i + 1])  # 곡선 시작점 (바로 앞 점)
                c1, c2, p3 = (v[i], v[i + 1]), (v[i + 2], v[i + 3]), (v[i + 4], v[i + 5])  # 조절점 두 개와 끝점
                for t in (0.25, 0.5, 0.75, 1):  # 곡선을 4등분한 자리마다
                    u = 1 - t  # 남은 비율
                    pts.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d  # 베지어 곡선 공식으로 점 위치를 계산
                                     for a, b, c, d in zip(p0, c1, c2, p3)))  # x 와 y 각각
        elif cmd == "Z" and pts:  # 닫기면
            pts.append(pts[0])  # 처음 점으로 돌아간다
    return pts  # 점 목록을 돌려준다


def inside(pts, r):  # 모든 점이 네모 r 안에 있는지 확인하는 함수
    return all(r[0] <= x <= r[2] and r[1] <= y <= r[3] for x, y in pts)  # 하나라도 밖이면 False


def size(pts):  # 점들이 차지하는 크기(가로·세로 중 긴 쪽)를 재는 함수
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]  # x 들, y 들
    return max(max(xs) - min(xs), max(ys) - min(ys))  # 가로 폭과 세로 높이 중 큰 값


# ── 모양 만들기 ───────────────────────────────────
def fmt(v):  # 숫자를 짧은 글자로 바꾸는 함수 (파일을 작게)
    s = f"{v:.1f}".rstrip("0").rstrip(".")  # 소수 첫째 자리까지, 뒤의 0 과 점은 지운다
    return "0" if s in ("-0", "") else s  # -0 이나 빈칸이면 0


def poly_d(geom):  # 도형을 SVG 경로 글자(d)로 바꾸는 함수
    out = []  # 경로 조각들
    polys = getattr(geom, "geoms", [geom])  # 여러 조각이면 조각들, 하나면 그것만
    for p in polys:  # 조각마다
        for ring in [p.exterior, *p.interiors]:  # 바깥 테두리와 안쪽 구멍 테두리마다
            c = list(ring.coords)  # 테두리 점들
            out.append("M" + "L".join(f"{fmt(x)} {fmt(y)}" for x, y in c[:-1]) + "Z")  # 점을 이어 닫힌 경로로
    return "".join(out)  # 모두 이어 붙인 경로


def fill(geom, color, extra=""):  # 도형을 색으로 칠한 SVG 요소를 만드는 함수
    return f'<path fill="{color}" d="{poly_d(geom)}"{extra}/>'  # 채우기 색 + 경로


def stadium(x0, y0, x1, y1):  # 육상 트랙 모양을 만드는 함수
    """세로로 긴 트랙 모양 (위아래가 반원)."""  # 이 함수가 하는 일을 적은 설명글
    r = (x1 - x0) / 2  # 반원의 반지름 (폭의 절반)
    cx = (x0 + x1) / 2  # 가운데 x
    top, bot = Point(cx, y0 + r).buffer(r, 48), Point(cx, y1 - r).buffer(r, 48)  # 위·아래 동그라미
    return unary_union([top, bot, box(x0, y0 + r, x1, y1 - r)])  # 두 동그라미와 가운데 네모를 합친다


def court(cx, cy, w=60, h=30):  # 농구장 그림을 만드는 함수
    """위에서 본 농구장 (가로로 긴 코트, 양쪽 골대)."""  # 이 함수가 하는 일을 적은 설명글
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2  # 코트의 네 변
    ln = 'fill="none" stroke="#ffffff" stroke-width="0.7"'  # 흰 코트 선 모양
    key_w, key_h = w * 0.19, h * 0.4  # 골밑 구역(페인트존)의 폭과 높이
    out = [fill(box(x0 - 2, y0 - 2, x1 + 2, y1 + 2), C["court_edge"]),  # 코트 바깥 테두리 바닥
           fill(box(x0, y0, x1, y1), C["court"]),  # 파란 코트 바닥
           fill(box(x0, cy - key_h / 2, x0 + key_w, cy + key_h / 2), C["court_key"]),  # 왼쪽 골밑 구역
           fill(box(x1 - key_w, cy - key_h / 2, x1, cy + key_h / 2), C["court_key"]),  # 오른쪽 골밑 구역
           f'<rect x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(w)}" height="{fmt(h)}" {ln}/>',  # 코트 바깥선
           f'<line x1="{fmt(cx)}" y1="{fmt(y0)}" x2="{fmt(cx)}" y2="{fmt(y1)}" {ln}/>',  # 가운데 선
           f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(h * 0.16)}" {ln}/>']  # 가운데 원
    for side in (-1, 1):  # 왼쪽(-1)·오른쪽(1) 골대마다
        ex = x0 if side < 0 else x1                     # 끝선
        kx = ex - side * key_w                         # 자유투 선
        r3 = h * 0.42                                  # 3점 선
        out.append(f'<rect x="{fmt(min(ex, kx))}" y="{fmt(cy - key_h / 2)}" width="{fmt(key_w)}" height="{fmt(key_h)}" {ln}/>')  # 골밑 구역 선
        out.append(f'<circle cx="{fmt(kx)}" cy="{fmt(cy)}" r="{fmt(key_h / 2)}" {ln}/>')  # 자유투 원
        sweep = 1 if side < 0 else 0  # 3점 선 호가 휘는 방향
        out.append(f'<path d="M{fmt(ex)} {fmt(cy - r3)}A{fmt(r3)} {fmt(r3)} 0 0 {sweep} {fmt(ex)} {fmt(cy + r3)}" {ln}/>')  # 3점 선 (반원 호)
        hx = ex - side * 1.6                           # 골대(백보드 + 링)
        out.append(f'<line x1="{fmt(hx)}" y1="{fmt(cy - 2.4)}" x2="{fmt(hx)}" y2="{fmt(cy + 2.4)}" stroke="#334155" stroke-width="0.9"/>')  # 백보드
        out.append(f'<circle cx="{fmt(hx - side * 1.3)}" cy="{fmt(cy)}" r="1" fill="none" stroke="#ea580c" stroke-width="0.6"/>')  # 주황 링
    return out  # 농구장 그림 요소들


def benches(points, w=7, h=2.4):  # 벤치 그림들을 만드는 함수
    """위에서 본 벤치 (나무 판)."""  # 이 함수가 하는 일을 적은 설명글
    return [f'<rect x="{fmt(x - w / 2)}" y="{fmt(y - h / 2)}" width="{fmt(w)}" height="{fmt(h)}" rx="0.6" '  # 모서리가 살짝 둥근 네모
            f'fill="{C["bench"]}" stroke="#7c5a3a" stroke-width="0.35"/>' for x, y in points]  # 나무색 판, 자리마다 하나씩


SMALL = (402, 210, 552, 295)   # 소운동장 (도면 테두리)


def taegeuk_flag(cx, cy, h):  # 태극기 모양 마당을 만드는 함수 (지금은 쓰지 않음)
    """위에서 본 태극기 모양 마당: 흰 바닥 + 가운데 태극 + 네 귀퉁이 괘 (건·곤·감·리)."""  # 이 함수가 하는 일을 적은 설명글
    w = h * 1.5  # 태극기 가로 = 세로 × 1.5
    out = [f'<rect x="{fmt(cx - w / 2)}" y="{fmt(cy - h / 2)}" width="{fmt(w)}" height="{fmt(h)}" rx="1.5" '  # 흰 바닥 네모
           f'fill="#fbfaf6" stroke="#cbbf9f" stroke-width="0.6"/>']  # 흰색 바닥, 옅은 테두리
    r = h / 4  # 태극 원의 반지름
    tilt = math.degrees(math.atan2(2, 3))  # 태극이 기울어진 각도
    out.append(f'<g transform="translate({fmt(cx)} {fmt(cy)}) rotate({fmt(tilt)})">'  # 가운데로 옮기고 기울인다
               f'<circle r="{fmt(r)}" fill="#0047a0"/>'  # 파란 원
               f'<path fill="#cd2e3a" d="M{fmt(-r)} 0A{fmt(r)} {fmt(r)} 0 0 1 {fmt(r)} 0'  # 빨간 위쪽 반원
               f'A{fmt(r / 2)} {fmt(r / 2)} 0 0 0 0 0A{fmt(r / 2)} {fmt(r / 2)} 0 0 1 {fmt(-r)} 0Z"/></g>')  # 작은 반원 두 개로 물결 모양
    # 괘: (방향, 막대 3개가 끊겼는지) — 건 ☰ 왼쪽 위, 감 ☵ 오른쪽 위, 리 ☲ 왼쪽 아래, 곤 ☷ 오른쪽 아래
    bar_l, bar_t, gap = h / 4, h / 24, h / 48  # 막대 길이, 막대 두께, 막대 사이 틈
    for sx, sy, broken in ((-1, -1, (0, 0, 0)), (1, -1, (1, 0, 1)), (-1, 1, (0, 1, 0)), (1, 1, (1, 1, 1))):  # 네 귀퉁이 괘마다
        ang = math.atan2(sy * h, sx * w)  # 가운데에서 귀퉁이 방향의 각도
        d = h * 0.25 + h / 6 + bar_l * 0.1  # 가운데에서 괘까지 거리
        tx, ty = cx + d * math.cos(ang) * 1.12, cy + d * math.sin(ang)  # 괘의 위치
        rot = math.degrees(ang) + 90  # 괘가 가운데를 보도록 돌리는 각도
        g = [f'<g transform="translate({fmt(tx)} {fmt(ty)}) rotate({fmt(rot)})" fill="#1f2937">']  # 괘 묶음 시작 (검은색)
        for i, br in enumerate(broken):  # 막대 3개마다
            y = (i - 1) * (bar_t + gap) - bar_t / 2  # 막대의 세로 위치
            if br:  # 끊어진 막대면
                half = bar_l / 2 - gap / 2  # 반쪽 길이
                g.append(f'<rect x="{fmt(-bar_l / 2)}" y="{fmt(y)}" width="{fmt(half)}" height="{fmt(bar_t)}"/>')  # 왼쪽 반
                g.append(f'<rect x="{fmt(gap / 2)}" y="{fmt(y)}" width="{fmt(half)}" height="{fmt(bar_t)}"/>')  # 오른쪽 반
            else:  # 이어진 막대면
                g.append(f'<rect x="{fmt(-bar_l / 2)}" y="{fmt(y)}" width="{fmt(bar_l)}" height="{fmt(bar_t)}"/>')  # 긴 막대 하나
        out.append("".join(g) + "</g>")  # 괘 묶음 끝
    return out, box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)  # 그림과 차지하는 영역


def pavilion(cx, cy, r):  # 정자 지붕 그림을 만드는 함수
    """위에서 본 육각 정자 지붕."""  # 이 함수가 하는 일을 적은 설명글
    pts = [(cx + r * math.cos(math.radians(30 + 60 * i)), cy + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]  # 육각형 꼭짓점 6개
    ring = "L".join(f"{fmt(x)} {fmt(y)}" for x, y in pts)  # 꼭짓점을 잇는 경로
    ridges = "".join(f"M{fmt(cx)} {fmt(cy)}L{fmt(x)} {fmt(y)}" for x, y in pts)  # 가운데에서 꼭짓점으로 가는 지붕 마루선
    return [f'<path d="M{ring}Z" fill="#9a6a43" stroke="#5b3a22" stroke-width="0.6" stroke-linejoin="round"/>',  # 갈색 지붕
            f'<path d="{ridges}" fill="none" stroke="#5b3a22" stroke-width="0.45"/>',  # 마루선
            f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(r * 0.18)}" fill="#c9a227"/>'], Point(cx, cy).buffer(r + 1.5)  # 꼭대기 장식, 그리고 차지하는 영역


def pond():  # 연못 그림을 만드는 함수
    """정자 옆 연못 (가장자리 돌, 연잎)."""  # 이 함수가 하는 일을 적은 설명글
    water = unary_union([Point(458, 279).buffer(9), Point(472, 282).buffer(8), Point(484, 278).buffer(6.5),  # 동그라미 여러 개를 합쳐
                         Point(466, 272).buffer(6)]).buffer(1.5).buffer(-1.5)  # 울퉁불퉁한 곳을 부드럽게 만든 물 모양
    out = [fill(water.buffer(1.4), "#a8a29e"), fill(water, "#7cc4e4"), fill(water.buffer(-2.2), "#5fb0d8")]  # 돌 테두리, 얕은 물, 깊은 물
    rnd = random.Random(7)  # 항상 같은 모양이 나오게 정한 무작위 수
    edge = water.exterior  # 물가 테두리
    for i in range(22):  # 테두리를 따라 돌 22개
        p = edge.interpolate(i / 22, normalized=True)  # 테두리 위의 자리
        out.append(f'<circle cx="{fmt(p.x)}" cy="{fmt(p.y)}" r="{fmt(rnd.uniform(.9, 1.5))}" fill="#d6d3d1" stroke="#78716c" stroke-width="0.25"/>')  # 크기가 조금씩 다른 돌
    for x, y in [(456, 280), (461, 284), (474, 280), (470, 286)]:  # 연잎 자리마다
        out.append(f'<circle cx="{x}" cy="{y}" r="1.5" fill="#4d9a52"/>')  # 초록 연잎
    return out, water.buffer(2.5)  # 그림과 차지하는 영역


FLOWER_COLORS = ["#f472b6", "#fb7185", "#facc15", "#fb923c", "#a78bfa", "#ffffff", "#ef4444", "#f9a8d4"]  # 꽃 색 8가지


def flowers(area, step, seed, avoid=None):  # 꽃밭을 만드는 함수
    """area 안에 꽃밭(초록 잎 위에 알록달록한 꽃송이)과 작은 덤불을 골고루 흩어 심는다."""  # 이 함수가 하는 일을 적은 설명글
    rnd = random.Random(seed)  # 항상 같은 배치가 나오게 정한 무작위 수
    x0, y0, x1, y1 = area.bounds  # 영역을 감싸는 네모
    out = []  # 그림 요소들
    y, row = y0 + step / 2, 0  # 첫 줄의 y, 줄 번호
    while y < y1:  # 아래 끝까지 줄마다
        x = x0 + step / 2 + (step / 2 if row % 2 else 0)  # 홀수 줄은 반 칸 밀어서 엇갈리게
        while x < x1:  # 오른쪽 끝까지
            px, py = x + rnd.uniform(-step * .3, step * .3), y + rnd.uniform(-step * .3, step * .3)  # 자리를 조금 흔들어 자연스럽게
            pt = Point(px, py)  # 심을 자리
            if area.contains(pt) and not (avoid and avoid.contains(pt)):  # 영역 안이고 피할 곳(길·연못)이 아니면
                if rnd.random() < .7:  # 꽃송이
                    out.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(rnd.uniform(2, 2.8))}" fill="#86c46f"/>')  # 초록 잎 바탕
                    col = rnd.choice(FLOWER_COLORS)  # 이 꽃송이의 주된 색
                    for k in range(rnd.randint(4, 7)):  # 꽃 4~7송이
                        a = rnd.uniform(0, math.tau)  # 방향
                        d = rnd.uniform(.4, 1.9)  # 가운데에서 거리
                        c = col if rnd.random() < .75 else rnd.choice(FLOWER_COLORS)  # 대부분 주된 색, 가끔 다른 색
                        out.append(f'<circle cx="{fmt(px + d * math.cos(a))}" cy="{fmt(py + d * math.sin(a))}" '  # 꽃 한 송이 위치
                                   f'r="{fmt(rnd.uniform(.6, .95))}" fill="{c}"/>')  # 작은 꽃 동그라미
                else:  # 작은 덤불
                    out.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(rnd.uniform(1.8, 2.5))}" '  # 덤불 위치·크기
                               f'fill="{rnd.choice([C["tree"], C["tree2"]])}" fill-opacity=".9"/>')  # 나무색 중 하나
            x += step  # 다음 칸
        y += step * .87  # 다음 줄 (엇갈린 줄이라 조금 좁게)
        row += 1  # 줄 번호 +1
    return out  # 꽃밭 그림 요소들


def cherry(cx, cy, r, rnd):  # 벚꽃나무 한 그루를 그리는 함수
    """위에서 본 벚꽃나무: 분홍 꽃구름 몇 덩이 + 밝은 꽃잎."""  # 이 함수가 하는 일을 적은 설명글
    out = []  # 그림 요소들
    for _ in range(5):  # 꽃구름 5덩이
        a, d = rnd.uniform(0, math.tau), rnd.uniform(0, r * .45)  # 방향과 가운데에서 거리
        out.append(f'<circle cx="{fmt(cx + d * math.cos(a))}" cy="{fmt(cy + d * math.sin(a))}" '  # 덩이 위치
                   f'r="{fmt(r * rnd.uniform(.55, .75))}" fill="{rnd.choice(["#f9a8d4", "#f472b6", "#fbcfe8"])}" fill-opacity=".92"/>')  # 분홍 세 가지 중 하나
    for _ in range(7):  # 밝은 꽃잎 7개
        a, d = rnd.uniform(0, math.tau), rnd.uniform(0, r * .9)  # 방향과 거리
        out.append(f'<circle cx="{fmt(cx + d * math.cos(a))}" cy="{fmt(cy + d * math.sin(a))}" r="{fmt(r * .12)}" fill="#fff1f7"/>')  # 거의 흰 분홍 점
    return out  # 벚꽃나무 그림 요소들


def gate_trees():  # 정문 쪽 나무숲을 만드는 함수
    """수위실(부1동) 오른쪽 빈터: 큰 벚꽃나무와 큰 나무 (위성사진에서 나무가 빽빽한 곳)."""  # 이 함수가 하는 일을 적은 설명글
    rnd = random.Random(11)  # 항상 같은 배치가 나오게 정한 무작위 수
    area = Polygon([(463, 588), (690, 588), (690, 644), (463, 644)])  # 나무를 심을 빈터
    out = []  # 그림 요소들
    x0, y0, x1, y1 = area.bounds  # 빈터를 감싸는 네모
    step = 17  # 나무 사이 간격
    y, row = y0 + step / 2, 0  # 첫 줄의 y, 줄 번호
    while y < y1:  # 아래 끝까지 줄마다
        x = x0 + step / 2 + (step / 2 if row % 2 else 0)  # 홀수 줄은 반 칸 밀기
        while x < x1:  # 오른쪽 끝까지
            px, py = x + rnd.uniform(-3, 3), y + rnd.uniform(-3, 3)  # 자리를 조금 흔든다
            if area.contains(Point(px, py)):  # 빈터 안이면
                if rnd.random() < .65:  # 65% 는
                    out += cherry(px, py, rnd.uniform(7.5, 9.5), rnd)  # 벚꽃나무
                else:  # 나머지는
                    col = C["tree"] if rnd.random() < .5 else C["tree2"]  # 초록 두 색 중 하나
                    out.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(rnd.uniform(7, 8.5))}" fill="{col}" fill-opacity=".9"/>')  # 큰 초록 나무
            x += step  # 다음 칸
        y += step * .87  # 다음 줄
        row += 1  # 줄 번호 +1
    return out  # 나무 그림 요소들


def stone_path(line, width, seed, clip=None):  # 돌길을 만드는 함수
    """돌을 깐 길: 길 바탕 위에 납작한 돌(포장석) 무늬."""  # 이 함수가 하는 일을 적은 설명글
    rnd = random.Random(seed)  # 항상 같은 무늬가 나오게 정한 무작위 수
    band = line.buffer(width / 2, cap_style=1)  # 선을 폭만큼 두껍게 한 길 모양 (끝은 둥글게)
    if clip is not None:  # 잘라낼 영역이 있으면
        band = band.intersection(clip)  # 그 안만 남긴다
    out = [fill(band, "#e7dcc3"), f'<path d="{poly_d(band)}" fill="none" stroke="#bfae8a" stroke-width="0.35"/>']  # 길 바탕색과 테두리
    n = max(2, int(line.length / 2.6))  # 길이에 맞춘 돌 줄 수 (최소 2)
    for k in range(n):  # 돌 줄마다
        p = line.interpolate((k + .5) / n, normalized=True)  # 길 가운데선 위의 자리
        for off in (-width * .22, width * .22):  # 길 왼쪽·오른쪽에 하나씩
            q = line.interpolate(min(line.length, max(0, line.project(p) + 0.3)))  # 조금 앞의 점 (길 방향을 알기 위해)
            dx, dy = q.x - p.x, q.y - p.y  # 길 방향
            L = math.hypot(dx, dy) or 1  # 방향의 길이 (0 이면 1)
            nx, ny = -dy / L, dx / L  # 길에 수직인 방향
            cx, cy = p.x + nx * off + rnd.uniform(-.3, .3), p.y + ny * off + rnd.uniform(-.3, .3)  # 돌 위치 (조금 흔들기)
            if clip is not None and not clip.buffer(-1.2).contains(Point(cx, cy)):  # 영역 가장자리를 넘으면
                continue  # 이 돌은 건너뛴다
            out.append(f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="{fmt(rnd.uniform(.85, 1.15))}" ry="{fmt(rnd.uniform(.65, .9))}" '  # 납작한 타원 돌
                       f'fill="{rnd.choice(["#cfc3a8", "#d8cdb4", "#c6b998"])}" stroke="#a8977a" stroke-width="0.2"/>')  # 돌 색 세 가지 중 하나
    return out, band  # 그림과 길 영역


def stepping_stones(points, seed):  # 디딤돌을 만드는 함수
    """디딤돌: 꽃밭 사이에 띄엄띄엄 놓인 둥근 돌."""  # 이 함수가 하는 일을 적은 설명글
    rnd = random.Random(seed)  # 항상 같은 모양이 나오게 정한 무작위 수
    out, geoms = [], []  # 그림 요소들, 차지하는 영역들
    for x, y in points:  # 돌 자리마다
        rx, ry = rnd.uniform(1.6, 2.1), rnd.uniform(1.2, 1.6)  # 가로·세로 반지름
        out.append(f'<ellipse cx="{fmt(x)}" cy="{fmt(y)}" rx="{fmt(rx)}" ry="{fmt(ry)}" fill="#d6d3d1" stroke="#8a857f" stroke-width="0.3"/>')  # 회색 둥근 돌
        geoms.append(Point(x, y).buffer(2.4))  # 돌이 차지하는 영역
    return out, unary_union(geoms)  # 그림과 합친 영역


def small_garden():  # 소운동장 정원 전체를 만드는 함수
    x0, y0, x1, y1 = SMALL  # 소운동장 테두리
    area = box(x0 + 1, y0 + 1, x1 - 1, y1 - 1)  # 테두리 선 안쪽 영역
    out = [fill(area, "#d9cfa6")]  # 흙빛 바탕
    water, water_area = pond()  # 연못
    pav, pav_area = pavilion(425, 277, 11)  # 정자
    # 돌길: 가로 큰길 + 위쪽 둥근 산책길 + 이어주는 길 + 가운데 작은 쉼터
    lines = [  # 돌길 선 목록
        LineString([(x0, 262), (x1, 262)]),                                   # 가로 큰길
        LineString([(425, 262), (425, 268)]),                                 # 큰길 → 정자
        LineString([(476 + 42 * math.cos(t / 40 * math.tau), 236 + 17 * math.sin(t / 40 * math.tau))  # 타원 위의 점 41개로
                    for t in range(41)]),                                     # 둥근 산책길
        LineString([(476, 253), (476, 262)]),                                 # 산책길 ↔ 큰길
        LineString([(418, 236), (434, 236)]),                                 # 왼쪽 문 → 산책길
        LineString([(518, 236), (x1, 236)]),                                  # 산책길 → 오른쪽
        LineString([(476, y0), (476, 219)]),                                  # 위쪽 문 → 산책길
        LineString([(x0, 236), (418, 236)]),  # 왼쪽 끝 → 왼쪽 문
    ]  # 돌길 선 목록 끝
    walk_geoms = []  # 돌길 영역들
    for k, ln in enumerate(lines):  # 돌길마다
        o, g = stone_path(ln, 4.6 if k == 0 else 3.6, 20 + k, clip=area)  # 큰길은 넓게(4.6), 나머지는 3.6
        out += o  # 그림 추가
        walk_geoms.append(g)  # 영역 추가
    plaza = Point(476, 236).buffer(7)  # 가운데 둥근 쉼터
    out += [fill(plaza, "#e7dcc3"), f'<circle cx="476" cy="236" r="7" fill="none" stroke="#bfae8a" stroke-width="0.4"/>',  # 쉼터 바닥과 테두리
            f'<circle cx="476" cy="236" r="3.2" fill="#86c46f"/>', f'<circle cx="476" cy="236" r="1.6" fill="#f472b6"/>']  # 가운데 화단과 분홍 꽃
    out += benches([(476, 226.5), (476, 245.5)], w=6, h=2)  # 쉼터 위아래 벤치
    # 디딤돌: 큰길 → 연못가, 큰길 → 오른쪽 아래
    st, st_area = stepping_stones([(497, 266.5), (500, 271), (504, 275.5), (529, 266.5), (532, 271.5)], 31)  # 디딤돌 5개
    out += water + st + pav  # 연못, 디딤돌, 정자를 그린다
    walk = unary_union(walk_geoms + [plaza])  # 모든 길과 쉼터 영역
    avoid = unary_union([walk.buffer(.6), water_area, pav_area, st_area, box(505, 282, 550, 294)])  # 꽃·나무를 심지 않을 곳 (길·연못·정자·디딤돌·글자 자리)
    out += flowers(area.buffer(-2), 7, 5, avoid=avoid)  # 꽃밭
    out += trees(area.buffer(-3), 19, 3.4, 9, avoid=avoid.buffer(2))  # 나무
    return out  # 정원 그림 요소들


def trees(area, step, r, seed, avoid=None):  # 영역 안에 나무를 심는 함수
    """area 안에 나무(동그라미)를 고르게 흩어 심는다."""  # 이 함수가 하는 일을 적은 설명글
    rnd = random.Random(seed)  # 항상 같은 배치가 나오게 정한 무작위 수
    x0, y0, x1, y1 = area.bounds  # 영역을 감싸는 네모
    out = []  # 그림 요소들
    y = y0 + step / 2  # 첫 줄의 y
    row = 0  # 줄 번호
    while y < y1:  # 아래 끝까지 줄마다
        x = x0 + step / 2 + (step / 2 if row % 2 else 0)  # 홀수 줄은 반 칸 밀기
        while x < x1:  # 오른쪽 끝까지
            px, py = x + rnd.uniform(-step * .3, step * .3), y + rnd.uniform(-step * .3, step * .3)  # 자리를 조금 흔든다
            if area.contains(Point(px, py)) and not (avoid and avoid.contains(Point(px, py))):  # 영역 안이고 피할 곳이 아니면
                rr = r * rnd.uniform(.8, 1.2)  # 나무 크기 (조금씩 다르게)
                col = C["tree"] if rnd.random() < .6 else C["tree2"]  # 초록 두 색 중 하나
                out.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(rr)}" fill="{col}" fill-opacity=".9"/>')  # 나무 동그라미
            x += step  # 다음 칸
        y += step * .87  # 다음 줄
        row += 1  # 줄 번호 +1
    return out  # 나무 그림 요소들


def row_of_trees(p0, p1, gap, r, seed):  # 두 점 사이에 가로수를 한 줄로 심는 함수
    rnd = random.Random(seed)  # 항상 같은 모양이 나오게 정한 무작위 수
    n = max(1, int(math.dist(p0, p1) // gap))  # 간격에 맞춘 나무 칸 수
    out = []  # 그림 요소들
    for i in range(n + 1):  # 양 끝 포함 나무마다
        t = i / n  # 시작점에서 끝점까지 비율
        x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t  # 그 비율의 위치
        col = C["tree"] if rnd.random() < .6 else C["tree2"]  # 초록 두 색 중 하나
        out.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r * rnd.uniform(.85, 1.15))}" fill="{col}" fill-opacity=".9"/>')  # 나무 동그라미
    return out  # 가로수 그림 요소들


# ── 실행 ─────────────────────────────────────────
def main():  # 배치도를 꾸며 저장하는 함수
    s = open(SITE, encoding="utf-8").read()  # 배치도 SVG 를 읽는다
    # 꾸미기 묶음(deco)은 맨 앞에 있고 바로 뒤에 도면 선(<path class=…>)이 온다. 안에 <g> 가 또 있어도 통째로 지운다
    s = re.sub(r'<g id="deco">.*?</g>(?=<path class=)', "", s, flags=re.S)  # 예전에 꾸민 것을 지운다 (여러 번 실행해도 같게)
    head = s[: s.index(">", s.index("<svg")) + 1]  # <svg ...> 시작 태그
    W, H = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head).groups())  # 도면 가로·세로 크기

    paths, bold_lines, removed = [], [], 0  # 다시 쓸 선들, 굵은 선 목록, 지운 조각 수
    for tag in re.findall(r"<path [^>]*/>", s):  # 도면의 경로 요소마다
        a = attrs_of(tag)  # 속성들
        cls = a["class"]  # 선 종류 (t 글자, h 빗금, l 가는 선, m 중간 선, w 굵은 선)
        keep = []  # 남길 조각들
        for sub in subpaths(a["d"]):  # 경로 조각마다
            pts = points(sub)  # 조각의 점들
            # ERASE 는 굵은 선(담장·도로 경계, class w)은 남긴다 — 지우면 도로 색칠이 새어 나간다
            if pts and (inside(pts, ARCHERY) or (cls != "w" and any(inside(pts, r) for r in ERASE)) or (cls != "t" and inside(pts, ARCHERY_EDGE) and size(pts) <= 0.6)  # 양궁장 안, 지울 영역 안, 양궁장 가장자리의 작은 점이거나
                        or (cls == "t" and any(inside(pts, r[0]) for r in RETEXT))):  # 다시 쓸 글자 자리의 글자면
                removed += 1  # 지운 수 +1
                continue  # 남기지 않는다
            keep.append(sub)  # 남긴다
            if cls == "w" and len(pts) > 1:  # 굵은 선이면
                bold_lines.append(LineString(pts))  # 영역 나누기에 쓰려고 모아 둔다
        if not keep:  # 남은 조각이 없으면
            continue  # 이 요소는 버린다
        d = "".join(keep)  # 남은 조각들을 이은 경로
        if cls in LINE:  # 선 종류면
            col, w = LINE[cls]  # 정한 색과 굵기
            paths.append(f'<path class="{cls}" fill="none" stroke="{col}" stroke-width="{w}" vector-effect="non-scaling-stroke" '  # 확대해도 굵기가 같은 선
                         f'stroke-linecap="round" stroke-linejoin="round" d="{d}"/>')  # 둥근 끝, 둥근 꺾임
        else:  # 채우기(글자·빗금)면
            paths.append(f'<path class="{cls}" fill="{TEXT if cls == "t" else a.get("fill", "#d1d5db")}" d="{d}"/>')  # 글자는 진한 색, 빗금은 원래 색

    # 굵은 선(담장·도로 경계·건물)으로 나뉜 빈 곳 → 도로, 학교 땅
    # 선끼리 살짝 떨어진 틈은 선을 gap 만큼 두껍게 해서 메운다. 도로가 끝나는 x=100, 768 에는 가상의 벽을 세운다.
    sheet = box(0, 0, W, H)  # 도면 전체 네모
    walls = bold_lines + [LineString([(x, 0), (x, H)]) for x in (100, 768)]  # 굵은 선 + 양옆 가상의 벽

    def region_at(seeds, gap):  # 씨앗 점이 들어 있는 빈 영역을 찾는 함수
        space = sheet.difference(unary_union([l.buffer(gap) for l in walls]))  # 도면에서 벽(두껍게 한 선)을 뺀 빈 곳들
        comps = list(getattr(space, "geoms", [space]))  # 따로 떨어진 빈 곳 조각들
        found = [c for c in comps if any(c.contains(Point(p)) for p in seeds)]  # 씨앗 점이 들어 있는 조각들
        return unary_union(found).buffer(gap).intersection(sheet) if found else None  # 합쳐서 두께만큼 다시 넓힌 영역 (없으면 None)

    roads = region_at(ROAD_SEEDS, 1.2)  # 도로 영역
    campus = region_at([CAMPUS_SEED], 3.0)  # 학교 땅 영역
    print("roads", round(roads.area) if roads else None, "campus", round(campus.area) if campus else None)  # 찾은 넓이를 보여준다 (확인용)

    deco = []  # 꾸미기 그림 요소들
    if campus is not None and campus.area < W * H * 0.6:  # 학교 땅을 찾았고 너무 크지 않으면 (새어 나가지 않았으면)
        deco.append(fill(campus, C["campus"]))  # 학교 땅을 칠한다
    if roads is not None and roads.area < W * H * 0.2:  # 도로를 찾았고 너무 크지 않으면
        deco.append(fill(roads, C["road"]))  # 도로를 칠한다

    # 숲: 증축예정부지 + 옛 양궁장 자리 + 담장 옆 (위성사진에서 나무가 빽빽한 곳)
    forest = unary_union([  # 숲 영역
        Polygon([(161, 193), (161, 48), (168, 47), (237, 28), (240, 24), (351, 24), (351, 73), (357, 90), (358, 193)]),  # 증축예정부지 모양
        box(155, 193, 326, 214),  # 옛 양궁장 자리 띠
    ])  # 숲 영역 끝
    deco.append(fill(forest, C["forest"]))  # 숲 바탕을 칠한다

    # 대운동장 (위성사진): 흙바닥 → 잔디 전체를 감싸는 타원 트랙 → 트랙 안 흙 → 위쪽 모래밭 → 인조잔디
    ground = box(155, 214, 331, 628).union(box(326, 214, 342, 560))  # 대운동장 땅
    deco.append(fill(ground, C["dirt"]))  # 흙바닥
    deco.append(fill(stadium(166, 218, 342, 558), C["track"]))  # 트랙
    deco.append(fill(stadium(172, 224, 336, 552), C["dirt"]))  # 트랙 안쪽 흙
    # 트랙과 골대 사이 (위·아래 끝) 농구장
    deco += court(254, 245)  # 위쪽 농구장
    deco += court(254, 531)  # 아래쪽 농구장
    field = box(178, 267, 330, 508)  # 인조잔디 축구장
    deco.append(fill(field, C["turf"]))  # 잔디를 칠한다
    for i, y in enumerate(range(267, 508, 20)):  # 20 간격 줄마다
        if i % 2:  # 하나 걸러
            deco.append(fill(box(178, y, 330, min(508, y + 20)), C["turf2"]))  # 조금 진한 잔디 줄무늬

    # 소운동장: 태극기 모양 마당 + 연못 + 정자 (위성사진)
    deco += small_garden()  # 소운동장 정원

    # 중정: 잔디 + 십자 길 + 가운데 원
    cx, cy = 573, 431  # 중정 가운데
    yard = box(518, 377, 627, 483)  # 중정 영역
    deco.append(fill(yard, C["lawn"]))  # 잔디를 칠한다
    paths_geom = unary_union([  # 중정 길 모양
        yard.exterior.buffer(3),  # 가장자리 길
        LineString([(518, 377), (627, 483)]).buffer(4.5),  # 대각선 길 하나
        LineString([(627, 377), (518, 483)]).buffer(4.5),  # 대각선 길 둘
        Point(cx, cy).buffer(19),  # 가운데 둥근 마당
    ]).intersection(yard)  # 중정 안만 남긴다
    deco.append(fill(paths_geom, C["path"]))  # 길을 칠한다
    deco.append(fill(Point(cx, cy).buffer(11), C["lawn"]))  # 가운데 둥근 잔디
    deco.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{C["tree2"]}"/>')  # 가운데 나무

    # 주차장
    for b in [(376, 32, 441, 44), (387, 58, 426, 82), (416, 132, 480, 143), (502, 552, 588, 564), (653, 359, 665, 374)]:  # 주차장 영역마다
        deco.append(fill(box(*b), C["park"]))  # 회색으로 칠한다

    # 나무: 숲 · 담장 · 길가 (위성사진의 나무 줄)
    deco += trees(forest, 9, 4.6, 1)  # 숲에 빽빽하게
    deco += trees(Polygon([(140, 60), (154, 60), (154, 628), (138, 628)]), 8, 4, 2)  # 왼쪽 담장을 따라
    deco += row_of_trees((172, 640), (318, 640), 9, 4, 3)  # 운동장 아래 가로수
    # 트랙과 야외 화장실(부3동) 사이: 나무 그늘 + 벤치
    rest = box(158, 566, 330, 628).difference(stadium(162, 214, 346, 562))  # 트랙 아래 쉼터 영역
    deco += benches([(x, 574) for x in range(186, 326, 26)] + [(x, 604) for x in range(199, 326, 26)])  # 벤치 두 줄
    deco += trees(rest, 12, 4.4, 6, avoid=unary_union([box(178, 571, 330, 577), box(191, 601, 330, 607)]))  # 벤치 줄은 피해 나무를 심는다
    deco += row_of_trees((676, 380), (684, 600), 10, 3.6, 4)  # 오른쪽 길가 가로수
    deco += gate_trees()  # 정문 쪽 벚꽃나무숲
    for (x, y) in [(522, 381), (623, 381), (522, 479), (623, 479)]:  # 중정 네 귀퉁이
        deco.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{C["tree"]}" fill-opacity=".9"/>')  # 나무 한 그루씩

    texts = [f'<text x="{x}" y="{fmt(y + size * 0.36)}" font-size="{size}" font-weight="800" font-family="{FONT}" '  # 굵은 웹 글꼴 글자
             f'text-anchor="middle" fill="{TEXT}" stroke="#ffffff" stroke-width="{fmt(min(2.4, size * 0.16))}" stroke-linejoin="round" '  # 가운데 정렬, 흰 테두리
             f'paint-order="stroke" letter-spacing="0.5">{word}</text>' for _, word, (x, y), size in RETEXT]  # 테두리를 먼저 그려 글자가 또렷하게, 다시 쓸 글자마다
    out = head + '<g id="deco">' + "".join(deco) + "</g>" + "".join(paths) + "".join(texts) + "</svg>"  # 시작 태그 + 꾸미기(맨 아래) + 도면 선 + 글자
    open(SITE, "w", encoding="utf-8").write(out)  # 파일에 저장한다
    print(f"removed {removed} archery pieces, {len(deco)} deco shapes, {len(out) // 1024} KB")  # 결과를 보여준다


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    main()  # 실행
