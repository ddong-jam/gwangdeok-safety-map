"""검색용 교실 목록(rooms.py)을 만든다.

도면 글자는 모양(path)으로만 들어 있어서 그대로는 읽을 수 없다.
그래서 도면을 그림으로 바꿔 윈도우 한국어 글자 인식(OCR)으로 읽은 결과(ocr*.tsv)와
도면에 직접 넣은 반 이름(<text>, 예: 2-1)을 합쳐서 '어느 층 어디에 무슨 방'이 있는지 정리한다.

    python tools/build_rooms.py <png 폴더> <배율>             # 1) 배율(2·3·4·6)별로 도면을 그림으로 (PyMuPDF)
    powershell -File tools/ocr.ps1 <png 폴더> <ocrN.tsv>   # 2) 글자 인식
    python tools/build_rooms.py --index <배율>=<ocrN.tsv> ...  # 3) rooms.py 생성

결과 rooms.py 는 손으로 고쳐도 된다 (다시 만들면 덮어쓴다).
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLANS = os.path.join(ROOT, "plans")

NUM = re.compile(r"^[BW]?\d{3}$")
HANGUL = re.compile(r"[가-힣]")
CLEAN = re.compile(r"^[가-힣A-Za-z0-9 /()·]+$")
# 방 이름으로 쓰지 않을 글자 (복도·계단 표시 등)
SKIP_NAME = {"복도", "복 도", "UP", "DN"}
# 잘못 읽은 글자 바로잡기 (OCR 결과 → 실제 도면 글자)
FIX = {
    "휴계실": "휴게실", "처사실": "전산실", "중교장실": "중학교 교장실", "참괴": "창고",
    "장고2": "창고2", "차고": "창고", "차가": "창고", "막시": "음악실2", "분 스즫": "",
    "제육기구실": "체육기구실", "30프린 터실": "3D프린터실", "자율자동자": "자율자동차교실",
    "교육정": "", "화장": "화장실", "합주파트여스AI": "합주파트연습실", "학생 스달": "학생식당",
    "샤워 화실장": "화장실", "주 방": "주방", "창 고": "창고", "식 당": "식당", "준비": "준비실",
    "세면": "세면장", "홈베이": "홈베이스 B", "과학실l": "과학실I", "음악실I": "음악실",
    "태극기영상관": "태극기 영상관",
}


def render(out, scale):
    import pymupdf
    os.makedirs(out, exist_ok=True)
    for n in sorted(os.listdir(PLANS)):
        if not n.endswith(".svg") or n == "site.svg":
            continue
        page = pymupdf.open(os.path.join(PLANS, n))[0]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        pix.save(os.path.join(out, n[:-4] + ".png"))


def read_ocr(path, scale):
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < 6:
                continue
            fid = p[0].strip("﻿")
            x0, y0, x1, y1 = (float(v) / scale for v in p[1:5])
            rows.append((fid, x0, y0, x1, y1, p[5].strip()))
    return rows


def name_below(lines, cx, y1):
    """번호 바로 아래 줄(들)을 이어 붙여 방 이름을 만든다."""
    out, bottom = [], y1
    while True:
        best = None
        for (x0, y0, x1, yy1, t) in lines:
            mx = (x0 + x1) / 2
            gap = y0 - bottom
            if abs(mx - cx) < 22 and -2 < gap < (9 if out else 12) and t not in SKIP_NAME:
                if best is None or y0 < best[1]:
                    best = (x0, y0, x1, yy1, t)
        if not best or not CLEAN.match(best[4]) or NUM.match(best[4]):
            break
        out.append(best[4])
        bottom = best[3]
        if len(out) >= 3:
            break
    name = "".join(out) if all(HANGUL.search(t) for t in out) else " ".join(out)
    return name if len(HANGUL.findall(name)) >= 2 or re.search(r"[A-Za-z]{3}", name) else ""


# 원래 도면에 파란 글씨(모양)로 들어 있는 반 이름 — 왼쪽부터 차례대로 (반, 호실)
BLUE_LABELS = {
    "b4-2f": [("1-1", "201"), ("1-2", "203"), ("1-3", "204"), ("1-4", "206"), ("1-5", "207"), ("1-6", "208")],
    "b4-3f": [("2-1", "301"), ("2-2", "303"), ("2-3", "304"), ("2-4", "306"), ("2-5", "307"), ("2-6", "308"),
              ("2-7", "309")],
    "b4-4f": [("3-1", "401"), ("3-2", "403"), ("3-3", "404"), ("3-4", "406"), ("3-5", "407"), ("3-6", "408"),
              ("3-7", "409")],
}


def class_labels():
    """층별 반 이름 [(x, y, 반, 호실 또는 None)].
    도면에 넣은 <text>(예: 2-1)와, 원래 도면에 파란 글씨로 있던 반 이름(BLUE_LABELS)."""
    text = re.compile(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]+)</text>')
    blue = re.compile(r'<path[^>]*fill="#1d4ed8"[^>]*>')
    out = {}
    for n in sorted(os.listdir(PLANS)):
        if not n.endswith(".svg") or n == "site.svg":
            continue
        fid = n[:-4]
        with open(os.path.join(PLANS, n), encoding="utf-8") as f:
            svg = f.read()
        # <text> 의 y 는 글자 바닥선이라 가운데로 4 올린다
        out[fid] = [(float(x), round(float(y) - 4, 1), t, None) for x, y, t in text.findall(svg)]
        if fid in BLUE_LABELS:
            boxes = []
            for m in blue.finditer(svg):
                d = re.search(r' d="([^"]+)"', m.group(0)).group(1)
                v = [float(t) for t in re.findall(r"-?\d+\.?\d*", d)]
                xs, ys = v[0::2], v[1::2]
                boxes.append((round((min(xs) + max(xs)) / 2, 1), round((min(ys) + max(ys)) / 2, 1)))
            boxes.sort()
            assert len(boxes) == len(BLUE_LABELS[fid]), (fid, len(boxes))
            out[fid] += [(x, y, t, num) for (x, y), (t, num) in zip(boxes, BLUE_LABELS[fid])]
    return out


def build(sources):
    by_floor = {}
    for scale, path in sources:
        for fid, x0, y0, x1, y1, t in read_ocr(path, scale):
            by_floor.setdefault(fid, {}).setdefault(scale, []).append((x0, y0, x1, y1, t))

    rooms = []
    for fid in sorted(by_floor):
        clusters = []  # [num, cx, cy, y1, {scale: name}]
        for scale, lines in by_floor[fid].items():
            for (x0, y0, x1, y1, t) in lines:
                if not NUM.match(t):
                    continue
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                c = next((c for c in clusters if c[0] == t and abs(c[1] - cx) < 6 and abs(c[2] - cy) < 6), None)
                if c is None:
                    c = [t, cx, cy, y1, {}]
                    clusters.append(c)
                c[4][scale] = name_below(lines, cx, y1)
        for me in clusters:
            num, cx, cy, y1, names = me
            if len(names) < 2:  # 한 배율에서만 보인 번호는 잘못 읽었을 수 있다
                continue
            # 번호 바로 밑의 두 번째 번호(기숙사 호실 등)는 따로 세지 않는다
            if any(o is not me and 4 < cy - o[2] < 16 and abs(cx - o[1]) < 8 and len(o[4]) >= 2
                   for o in clusters):
                continue
            votes = Counter(n for n in names.values() if n)
            name = votes.most_common(1)[0][0] if votes else ""
            name = FIX.get(name, name)
            rooms.append([fid, num, name, round(cx, 1), round(cy + 6, 1)])
    return rooms


def main():
    if sys.argv[1:2] == ["--index"]:
        sources = []
        for arg in sys.argv[2:]:
            s, p = arg.split("=", 1)
            sources.append((float(s), p))
        rooms = build(sources)
        classes = class_labels()
        out = os.path.join(ROOT, "rooms.py")
        with open(out, "w", encoding="utf-8") as f:
            f.write('"""검색용 방 목록 — tools/build_rooms.py 가 만든다. (층, 번호, 이름, x, y)"""\n\n')
            f.write("ROOMS = [\n")
            for r in rooms:
                f.write(f"    {tuple(r)!r},\n")
            f.write("]\n\n")
            f.write('# 반 이름 (층, 반, 호실, x, y)\nCLASSES = [\n')
            for fid in sorted(classes):
                for x, y, t, num in classes[fid]:
                    if num is None:  # 바로 위에 있는 호실 번호
                        num = next((r[1] for r in rooms
                                    if r[0] == fid and abs(r[3] - x) < 20 and -26 < r[4] - y < 4), "")
                    f.write(f"    {(fid, t, num, x, y)!r},\n")
            f.write("]\n")
        print(f"rooms.py: 방 {len(rooms)}개, 반 {sum(len(v) for v in classes.values())}개")
    else:
        out, scale = sys.argv[1], float(sys.argv[2])
        render(out, scale)


if __name__ == "__main__":
    main()
