"""Convert CAD floor-plan PDF pages into compact, restyled SVGs (displayed-page pt coords)."""
import pymupdf, sys, json  # PDF 를 읽는 도구, 실행할 때 받은 값, 결과를 JSON 글자로 보여주는 도구

COL = {"t": "#1f2937", "h": "#d1d5db", "l": "#8b93a1", "m": "#4b5563", "w": "#111827"}  # 선 종류별 색: 글자, 빗금, 가는 선, 중간 선, 벽

def fmt(v):  # 숫자를 짧은 글자로 바꾸는 함수 (파일을 작게)
    s = f"{v:.2f}".rstrip("0").rstrip(".")  # 소수 둘째 자리까지, 뒤의 0 과 점은 지운다
    return "0" if s in ("-0", "") else s  # -0 이나 빈칸이면 0

def excluded(r, mode):  # 도면 바깥 표(제목란 등)에 있는 그림인지 확인하는 함수
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2  # 그림의 가운데
    if mode == "site":  # 배치도면
        return cx > 1040 or cy < 40 or cy > 800  # 오른쪽 표·위아래 가장자리는 뺀다
    return (cy < 45 or cy > 755 or cx < 60 or cx > 1140 or (cx > 1040 and cy < 150)  # 층 도면: 가장자리·오른쪽 위 표를 뺀다
            or (cy > 635 and cx < 560) or (cx > 930 and cy > 680))  # 왼쪽 아래 표·오른쪽 아래 제목란도 뺀다

def classify(g):  # 그림 하나가 어떤 종류의 선인지 고르는 함수
    if g["type"] == "f" or (g["type"] == "fs" and not g.get("color")):  # 채우기만 있는 도형이면
        f = g.get("fill") or (0, 0, 0)  # 채우기 색
        return "t" if max(f) < 0.3 else "h"  # 진하면 글자(t), 옅으면 빗금(h)
    w = g.get("width") or 0  # 선 두께
    c = g.get("color") or (0, 0, 0)  # 선 색
    if max(c) > 0.6: return "l"  # 옅은 색이면 가는 선(치수선 등)
    if 0.25 < max(c) < 0.45 and w < 0.1: return "m"  # hairline wall pen used by 9동/수위실/화장실 sheets
    if w >= 0.6: return "w"  # 두꺼우면 벽
    if w >= 0.3: return "m"  # 중간이면 중간 선
    return "l"  # 나머지는 가는 선

def convert(page, mode, margin=14, crop=None):  # PDF 한 쪽을 SVG 글자로 바꾸는 함수
    M = page.rotation_matrix  # 쪽이 돌아가 있으면 바로 세우는 변환
    drawings = []  # 쓸 그림들
    for g in page.get_drawings():  # 쪽 안의 모든 그림마다
        r = g["rect"] * M  # 그림의 네모 영역 (바로 세운 좌표)
        r.normalize()  # 네모 방향을 바로잡는다
        r = r + (-0.3, -0.3, 0.3, 0.3)  # perfectly straight lines have zero-area rects, which never intersect
        if excluded(r, mode): continue  # 표·제목란이면 건너뛴다
        drawings.append((g, r))  # 쓸 그림에 넣는다
    if crop is None:  # 자를 영역을 안 정했으면 자동으로 찾는다
        box = pymupdf.Rect()  # 빈 네모에서 시작
        for g, r in drawings:  # 그림마다
            if g["type"] != "f" and (g.get("width") or 0) >= 0.6 and r.width < 700: box |= r  # 두꺼운 벽 선을 모두 감싸게 늘린다
        if box.is_empty or box.width < 120 or box.height < 60:  # 너무 작으면
            # some sheets draw walls with thinner pens: fall back to medium strokes
            box = pymupdf.Rect()  # 다시 빈 네모
            for g, r in drawings:  # 그림마다
                if g["type"] != "f" and (g.get("width") or 0) >= 0.3 and r.width < 700: box |= r  # 중간 두께 선으로 다시
        if box.is_empty or box.width < 120 or box.height < 60:  # 그래도 너무 작으면
            # hairline-only sheets (e.g. 9동, 화장실): take every stroke that is not a long grid line
            box = pymupdf.Rect()  # 다시 빈 네모
            for g, r in drawings:  # 그림마다
                if g["type"] != "f" and r.width < 700 and r.height < 520: box |= r  # 아주 긴 격자선만 빼고 모든 선으로
        crop = box + (-margin, -margin, margin, margin)  # 찾은 영역에 여백을 더한다
    ox, oy = crop.x0, crop.y0  # 자른 영역의 왼쪽 위 (새 좌표의 0)
    P = lambda p: (p * M)  # 점을 바로 세우는 함수
    def pt(p):  # 점을 "x y" 글자로 바꾸는 함수
        q = P(p); return f"{fmt(q.x-ox)} {fmt(q.y-oy)}"  # 바로 세우고, 자른 영역 기준으로 옮겨 글자로
    buckets = {}  # (선 종류, 두께) 별로 모은 그림 경로들
    for g, r in drawings:  # 그림마다
        if not r.intersects(crop): continue  # 자른 영역 밖이면 건너뛴다
        cls = classify(g)  # 선 종류
        if cls == "l" and mode != "site": continue  # 층 평면도의 치수선·격자선·잔선은 뺀다 (배치도는 도로·운동장이라 둔다)
        w = round(g.get("width") or 0, 2)  # 선 두께
        if cls == "m": w = max(w, 0.3)  # 중간 선은 최소 0.3
        key = (cls, w if cls != "t" and cls != "h" else 0)  # 모을 묶음 이름 (채우기는 두께 무관)
        parts = []; last = None  # 경로 조각들, 마지막 점
        for it in g["items"]:  # 그림을 이루는 조각마다
            op = it[0]  # 조각 종류
            if op == "l":  # 직선
                a, b = pt(it[1]), pt(it[2])  # 시작점, 끝점
                parts.append(("L" if a == last else f"M{a}L") + b); last = b  # 이어지면 L, 아니면 M 으로 새로 시작
            elif op == "c":  # 곡선
                a = pt(it[1])  # 시작점
                parts.append(("" if a == last else f"M{a}") + "C" + " ".join(pt(x) for x in it[2:5])); last = pt(it[4])  # 곡선 경로
            elif op == "re":  # 네모
                rr = it[1]; q = [pt(rr.tl), pt(rr.tr), pt(rr.br), pt(rr.bl)]  # 네 꼭짓점
                parts.append(f"M{q[0]}L{q[1]}L{q[2]}L{q[3]}Z"); last = None  # 닫힌 네모 경로
            elif op == "qu":  # 사각형(기울어진 것 포함)
                qd = it[1]; q = [pt(qd.ul), pt(qd.ur), pt(qd.lr), pt(qd.ll)]  # 네 꼭짓점
                parts.append(f"M{q[0]}L{q[1]}L{q[2]}L{q[3]}Z"); last = None  # 닫힌 경로
        if g.get("closePath") and parts: parts.append("Z"); last = None  # 닫힌 도형이면 닫는다
        buckets.setdefault(key, []).append("".join(parts))  # 같은 묶음에 모은다
    out = []  # SVG 경로 요소들
    order = {"h": 0, "l": 1, "m": 2, "w": 3, "t": 4}  # 그리는 순서: 빗금 → 가는 선 → 중간 → 벽 → 글자
    for (cls, w), ds in sorted(buckets.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):  # 순서대로 묶음마다
        d = "".join(ds)  # 묶음의 모든 경로를 하나로
        if cls in ("t", "h"):  # 채우기면
            out.append(f'<path class="{cls}" fill="{COL[cls]}" d="{d}"/>')  # 색을 채운 경로
        else:  # 선이면
            out.append(f'<path class="{cls}" fill="none" stroke="{COL[cls]}" stroke-linecap="round" stroke-linejoin="round" stroke-width="{fmt(max(w,0.12))}" d="{d}"/>')  # 둥근 끝 선 경로
    W, H = crop.width, crop.height  # 도면 크기
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(W)} {fmt(H)}" width="{fmt(W)}" height="{fmt(H)}">'  # SVG 시작 (크기)
           + "".join(out) + "</svg>")  # 경로들 + 끝
    return svg, crop  # SVG 글자와 자른 영역을 돌려준다

if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    src, idx, mode, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]  # PDF, 쪽 번호, 종류, 저장할 파일
    d = pymupdf.open(src)  # PDF 를 연다
    svg, crop = convert(d[idx - 1], mode)  # 그 쪽을 바꾼다
    open(dst, "w", encoding="utf-8").write(svg)  # 저장한다
    print(json.dumps({"crop": [round(crop.x0, 2), round(crop.y0, 2), round(crop.width, 2), round(crop.height, 2)], "bytes": len(svg)}))  # 자른 영역과 용량을 보여준다
