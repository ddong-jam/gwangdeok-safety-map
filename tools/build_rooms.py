"""검색용 교실 목록(rooms.py)을 만든다.

도면 글자는 모양(path)으로만 들어 있어서 그대로는 읽을 수 없다.
그래서 도면을 그림으로 바꿔 윈도우 한국어 글자 인식(OCR)으로 읽은 결과(ocr*.tsv)와
도면에 직접 넣은 반 이름(<text>, 예: 2-1)을 합쳐서 '어느 층 어디에 무슨 방'이 있는지 정리한다.

    python tools/build_rooms.py <png 폴더> <배율>             # 1) 배율(2·3·4·6)별로 도면을 그림으로 (PyMuPDF)
    python tools/ocr.py <png 폴더> <ocrN.tsv>              # 2) 글자 인식 (윈도우)
    python tools/build_rooms.py --index <배율>=<ocrN.tsv> ...  # 3) rooms.py 생성

결과 rooms.py 는 손으로 고쳐도 된다 (다시 만들면 덮어쓴다).
"""
import os  # 폴더·파일 경로 도구
import re  # 글자 패턴(정규식) 도구
import sys  # 실행할 때 받은 값을 읽는 도구
from collections import Counter  # 개수를 세는 도구 (여러 배율 결과 중 가장 많이 나온 이름 고르기)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 프로젝트 맨 위 폴더
PLANS = os.path.join(ROOT, "plans")  # 도면 폴더

NUM = re.compile(r"^[BW]?\d{3}$")  # 방 번호 모양 (예: 102, B101, W201)
HANGUL = re.compile(r"[가-힣]")  # 한글 한 글자
CLEAN = re.compile(r"^[가-힣A-Za-z0-9 /()·]+$")  # 방 이름에 쓸 수 있는 글자들만 있는지
# 방 이름으로 쓰지 않을 글자 (복도·계단 표시 등)
SKIP_NAME = {"복도", "복 도", "UP", "DN"}  # 무시할 글자 모음
# 잘못 읽은 글자 바로잡기 (OCR 결과 → 실제 도면 글자)
FIX = {  # 잘못 읽은 글자 → 바른 글자
    "휴계실": "휴게실", "처사실": "전산실", "중교장실": "중학교 교장실", "참괴": "창고",  # 고치기 1
    "장고2": "창고2", "차고": "창고", "차가": "창고", "막시": "음악실2", "분 스즫": "",  # 고치기 2 (빈칸 = 버림)
    "제육기구실": "체육기구실", "30프린 터실": "3D프린터실", "자율자동자": "자율자동차교실",  # 고치기 3
    "교육정": "", "화장": "화장실", "합주파트여스AI": "합주파트연습실", "학생 스달": "학생식당",  # 고치기 4
    "샤워 화실장": "화장실", "주 방": "주방", "창 고": "창고", "식 당": "식당", "준비": "준비실",  # 고치기 5
    "세면": "세면장", "홈베이": "홈베이스 B", "과학실l": "과학실I", "음악실I": "음악실",  # 고치기 6
    "태극기영상관": "태극기 영상관",  # 고치기 7
}  # 바로잡기 목록 끝


def render(out, scale):  # 도면들을 그림(png)으로 바꾸는 함수
    import pymupdf  # PDF·SVG 를 그림으로 바꾸는 도구
    os.makedirs(out, exist_ok=True)  # 결과 폴더를 만든다 (이미 있으면 그대로)
    for n in sorted(os.listdir(PLANS)):  # 도면 파일마다
        if not n.endswith(".svg") or n == "site.svg":  # 층 도면이 아니면
            continue  # 건너뛴다
        page = pymupdf.open(os.path.join(PLANS, n))[0]  # 도면을 연다
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)  # 배율만큼 키워 그림으로 그린다
        pix.save(os.path.join(out, n[:-4] + ".png"))  # png 로 저장


def read_ocr(path, scale):  # 글자 인식 결과 파일을 읽는 함수
    rows = []  # 결과
    with open(path, encoding="utf-8-sig") as f:  # 파일을 열어
        for line in f:  # 한 줄씩
            p = line.rstrip("\n").split("\t")  # 탭으로 나눈다
            if len(p) < 6:  # 칸이 모자라면
                continue  # 건너뛴다
            fid = p[0].strip("﻿")  # 층 id (파일 맨 앞 보이지 않는 글자 제거)
            x0, y0, x1, y1 = (float(v) / scale for v in p[1:5])  # 그림 좌표를 도면 좌표로 (배율로 나눈다)
            rows.append((fid, x0, y0, x1, y1, p[5].strip()))  # 층, 위치, 글자를 저장
    return rows  # 결과


def name_below(lines, cx, y1):  # 방 번호 아래 글자를 이어 방 이름을 만드는 함수
    """번호 바로 아래 줄(들)을 이어 붙여 방 이름을 만든다."""  # 이 함수가 하는 일을 적은 설명글
    out, bottom = [], y1  # 모은 이름 조각들, 지금까지의 아래쪽 위치
    while True:  # 더 이어 붙일 게 없을 때까지
        best = None  # 바로 아래에 있는 가장 가까운 글자 줄
        for (x0, y0, x1, yy1, t) in lines:  # 모든 글자 줄을 보면서
            mx = (x0 + x1) / 2  # 그 줄의 가운데 x
            gap = y0 - bottom  # 지금 아래쪽과의 간격
            if abs(mx - cx) < 22 and -2 < gap < (9 if out else 12) and t not in SKIP_NAME:  # 가로로 가깝고, 바로 아래이고, 무시할 글자가 아니면
                if best is None or y0 < best[1]:  # 더 위에 있는 것을 고른다
                    best = (x0, y0, x1, yy1, t)  # 후보
        if not best or not CLEAN.match(best[4]) or NUM.match(best[4]):  # 없거나, 이상한 글자거나, 또 다른 방 번호면
            break  # 그만
        out.append(best[4])  # 이름 조각을 더한다
        bottom = best[3]  # 아래쪽 위치를 그 줄 아래로
        if len(out) >= 3:  # 세 줄까지만
            break  # 그만
    name = "".join(out) if all(HANGUL.search(t) for t in out) else " ".join(out)  # 한글만이면 붙이고, 아니면 띄어 쓴다
    return name if len(HANGUL.findall(name)) >= 2 or re.search(r"[A-Za-z]{3}", name) else ""  # 한글 2자 이상이나 영어 3자 이상일 때만 이름으로 쓴다


# 원래 도면에 파란 글씨(모양)로 들어 있는 반 이름 — 왼쪽부터 차례대로 (반, 호실)
BLUE_LABELS = {  # 중학교 층별 반 이름
    "b4-2f": [("1-1", "201"), ("1-2", "203"), ("1-3", "204"), ("1-4", "206"), ("1-5", "207"), ("1-6", "208")],  # 중학교 2층 = 1학년
    "b4-3f": [("2-1", "301"), ("2-2", "303"), ("2-3", "304"), ("2-4", "306"), ("2-5", "307"), ("2-6", "308"),  # 중학교 3층 = 2학년
              ("2-7", "309")],  # 2-7반
    "b4-4f": [("3-1", "401"), ("3-2", "403"), ("3-3", "404"), ("3-4", "406"), ("3-5", "407"), ("3-6", "408"),  # 중학교 4층 = 3학년
              ("3-7", "409")],  # 3-7반
}  # 파란 글씨 반 이름 끝


def class_labels():  # 층별 반 이름과 위치를 모으는 함수
    """층별 반 이름 [(x, y, 반, 호실 또는 None)].
    도면에 넣은 <text>(예: 2-1)와, 원래 도면에 파란 글씨로 있던 반 이름(BLUE_LABELS)."""
    text = re.compile(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]+)</text>')  # 도면 속 <text> 글자를 찾는 패턴
    blue = re.compile(r'<path[^>]*fill="#1d4ed8"[^>]*>')  # 파란색으로 칠한 글자 모양을 찾는 패턴
    out = {}  # 층 id → 반 이름 목록
    for n in sorted(os.listdir(PLANS)):  # 도면 파일마다
        if not n.endswith(".svg") or n == "site.svg":  # 층 도면이 아니면
            continue  # 건너뛴다
        fid = n[:-4]  # 층 id
        with open(os.path.join(PLANS, n), encoding="utf-8") as f:  # 도면을 열어
            svg = f.read()  # 읽는다
        # <text> 의 y 는 글자 바닥선이라 가운데로 4 올린다
        out[fid] = [(float(x), round(float(y) - 4, 1), t, None) for x, y, t in text.findall(svg)]  # 찾은 반 이름들 (호실은 나중에)
        if fid in BLUE_LABELS:  # 파란 글씨 반 이름이 있는 층이면
            boxes = []  # 파란 글씨들의 가운데 위치
            for m in blue.finditer(svg):  # 파란 모양마다
                d = re.search(r' d="([^"]+)"', m.group(0)).group(1)  # 모양 경로
                v = [float(t) for t in re.findall(r"-?\d+\.?\d*", d)]  # 경로 안의 숫자들
                xs, ys = v[0::2], v[1::2]  # x 들과 y 들
                boxes.append((round((min(xs) + max(xs)) / 2, 1), round((min(ys) + max(ys)) / 2, 1)))  # 가운데 위치
            boxes.sort()  # 왼쪽부터 정렬
            assert len(boxes) == len(BLUE_LABELS[fid]), (fid, len(boxes))  # 개수가 맞는지 확인
            out[fid] += [(x, y, t, num) for (x, y), (t, num) in zip(boxes, BLUE_LABELS[fid])]  # 위치와 반 이름을 짝지어 더한다
    return out  # 결과


def build(sources):  # 글자 인식 결과들로 방 목록을 만드는 함수
    by_floor = {}  # 층 → 배율 → 글자 줄들
    for scale, path in sources:  # 배율별 결과 파일마다
        for fid, x0, y0, x1, y1, t in read_ocr(path, scale):  # 읽은 줄마다
            by_floor.setdefault(fid, {}).setdefault(scale, []).append((x0, y0, x1, y1, t))  # 층·배율별로 모은다

    rooms = []  # 결과 방 목록
    for fid in sorted(by_floor):  # 층마다
        clusters = []  # [num, cx, cy, y1, {scale: name}]
        for scale, lines in by_floor[fid].items():  # 배율마다
            for (x0, y0, x1, y1, t) in lines:  # 글자 줄마다
                if not NUM.match(t):  # 방 번호가 아니면
                    continue  # 건너뛴다
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2  # 번호의 가운데
                c = next((c for c in clusters if c[0] == t and abs(c[1] - cx) < 6 and abs(c[2] - cy) < 6), None)  # 다른 배율에서 같은 자리에 같은 번호를 찾았는지
                if c is None:  # 처음이면
                    c = [t, cx, cy, y1, {}]  # 새 묶음
                    clusters.append(c)  # 추가
                c[4][scale] = name_below(lines, cx, y1)  # 이 배율에서 읽은 방 이름
        for me in clusters:  # 번호 묶음마다
            num, cx, cy, y1, names = me  # 번호, 위치, 배율별 이름
            if len(names) < 2:  # 한 배율에서만 보인 번호는 잘못 읽었을 수 있다
                continue  # 버린다
            # 번호 바로 밑의 두 번째 번호(기숙사 호실 등)는 따로 세지 않는다
            if any(o is not me and 4 < cy - o[2] < 16 and abs(cx - o[1]) < 8 and len(o[4]) >= 2  # 바로 위에 다른 번호가 있으면
                   for o in clusters):  # 모든 묶음과 비교
                continue  # 버린다
            votes = Counter(n for n in names.values() if n)  # 배율별 이름의 개수를 센다
            name = votes.most_common(1)[0][0] if votes else ""  # 가장 많이 나온 이름 (없으면 빈칸)
            name = FIX.get(name, name)  # 잘못 읽은 글자를 바로잡는다
            rooms.append([fid, num, name, round(cx, 1), round(cy + 6, 1)])  # 층, 번호, 이름, 위치를 저장
    return rooms  # 결과


def owner(fid, x):  # 도면 파일과 x 좌표로 어느 건물 층인지 정하는 함수
    """도면 파일 + x → 층 id. 한 도면을 두 건물이 나눠 쓰면(덕후재 | 귀촌관) x 로 고른다."""  # 이 함수가 하는 일을 적은 설명글
    sys.path.insert(0, ROOT)  # 프로젝트 폴더의 파일을 불러올 수 있게
    from campus import BUILDINGS  # 건물 목록
    for b in BUILDINGS:  # 건물마다
        for f in b.floors:  # 층마다
            if (f.src or f.id) == fid and (f.crop is None or f.crop[0] <= x < f.crop[1]):  # 같은 도면 파일이고 x 가 그 건물 범위 안이면
                return f.id  # 그 층
    return fid  # 못 찾으면 파일 이름 그대로


def main():  # 실행했을 때 하는 일
    if sys.argv[1:2] == ["--index"]:  # "--index" 로 실행하면 rooms.py 를 만든다
        sources = []  # (배율, 결과 파일) 목록
        for arg in sys.argv[2:]:  # 받은 값마다
            s, p = arg.split("=", 1)  # "배율=파일" 을 나눈다
            sources.append((float(s), p))  # 목록에 넣는다
        rooms = build(sources)  # 방 목록을 만든다
        classes = class_labels()  # 반 이름을 모은다
        out = os.path.join(ROOT, "rooms.py")  # 만들 파일
        with open(out, "w", encoding="utf-8") as f:  # 파일을 열어
            f.write('"""검색용 방 목록 — tools/build_rooms.py 가 만든다. (층, 번호, 이름, x, y)"""\n\n')  # 맨 위 설명
            f.write("ROOMS = [\n")  # 방 목록 시작
            for r in rooms:  # 방마다
                f.write(f"    {(owner(r[0], r[3]), *r[1:])!r},\n")  # (층 id, 번호, 이름, x, y) 한 줄
            f.write("]\n\n")  # 방 목록 끝
            f.write('# 반 이름 (층, 반, 호실, x, y)\nCLASSES = [\n')  # 반 목록 시작
            for fid in sorted(classes):  # 층마다
                for x, y, t, num in classes[fid]:  # 반 이름마다
                    if num is None:  # 바로 위에 있는 호실 번호
                        num = next((r[1] for r in rooms  # 방 목록에서
                                    if r[0] == fid and abs(r[3] - x) < 20 and -26 < r[4] - y < 4), "")  # 같은 층, 가까운 번호를 찾는다 (없으면 빈칸)
                    f.write(f"    {(owner(fid, x), t, num, x, y)!r},\n")  # (층 id, 반, 호실, x, y) 한 줄
            f.write("]\n")  # 반 목록 끝
        print(f"rooms.py: 방 {len(rooms)}개, 반 {sum(len(v) for v in classes.values())}개")  # 결과 개수를 보여준다
    else:  # 그 밖에는 도면을 그림으로 바꾼다
        out, scale = sys.argv[1], float(sys.argv[2])  # 결과 폴더와 배율
        render(out, scale)  # 그림으로 바꾼다


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    main()  # 실행
