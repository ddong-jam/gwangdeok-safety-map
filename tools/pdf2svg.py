"""Convert CAD floor-plan PDF pages into compact, restyled SVGs (displayed-page pt coords)."""
import pymupdf, sys, json

COL = {"t": "#1f2937", "h": "#d1d5db", "l": "#8b93a1", "m": "#4b5563", "w": "#111827"}

def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def excluded(r, mode):
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
    if mode == "site":
        return cx > 1040 or cy < 40 or cy > 800
    return (cy < 45 or cy > 755 or cx < 60 or cx > 1140 or (cx > 1040 and cy < 150)
            or (cy > 635 and cx < 560) or (cx > 930 and cy > 680))

def classify(g):
    if g["type"] == "f" or (g["type"] == "fs" and not g.get("color")):
        f = g.get("fill") or (0, 0, 0)
        return "t" if max(f) < 0.3 else "h"
    w = g.get("width") or 0
    c = g.get("color") or (0, 0, 0)
    if max(c) > 0.6: return "l"
    if 0.25 < max(c) < 0.45 and w < 0.1: return "m"  # hairline wall pen used by 9동/수위실/화장실 sheets
    if w >= 0.6: return "w"
    if w >= 0.3: return "m"
    return "l"

def convert(page, mode, margin=14, crop=None):
    M = page.rotation_matrix
    drawings = []
    for g in page.get_drawings():
        r = g["rect"] * M
        r.normalize()
        r = r + (-0.3, -0.3, 0.3, 0.3)  # perfectly straight lines have zero-area rects, which never intersect
        if excluded(r, mode): continue
        drawings.append((g, r))
    if crop is None:
        box = pymupdf.Rect()
        for g, r in drawings:
            if g["type"] != "f" and (g.get("width") or 0) >= 0.6 and r.width < 700: box |= r
        if box.is_empty or box.width < 120 or box.height < 60:
            # some sheets draw walls with thinner pens: fall back to medium strokes
            box = pymupdf.Rect()
            for g, r in drawings:
                if g["type"] != "f" and (g.get("width") or 0) >= 0.3 and r.width < 700: box |= r
        if box.is_empty or box.width < 120 or box.height < 60:
            # hairline-only sheets (e.g. 9동, 화장실): take every stroke that is not a long grid line
            box = pymupdf.Rect()
            for g, r in drawings:
                if g["type"] != "f" and r.width < 700 and r.height < 520: box |= r
        crop = box + (-margin, -margin, margin, margin)
    ox, oy = crop.x0, crop.y0
    P = lambda p: (p * M)
    def pt(p):
        q = P(p); return f"{fmt(q.x-ox)} {fmt(q.y-oy)}"
    buckets = {}
    for g, r in drawings:
        if not r.intersects(crop): continue
        cls = classify(g)
        if cls == "l" and mode != "site": continue  # 층 평면도의 치수선·격자선·잔선은 뺀다 (배치도는 도로·운동장이라 둔다)
        w = round(g.get("width") or 0, 2)
        if cls == "m": w = max(w, 0.3)
        key = (cls, w if cls != "t" and cls != "h" else 0)
        parts = []; last = None
        for it in g["items"]:
            op = it[0]
            if op == "l":
                a, b = pt(it[1]), pt(it[2])
                parts.append(("L" if a == last else f"M{a}L") + b); last = b
            elif op == "c":
                a = pt(it[1])
                parts.append(("" if a == last else f"M{a}") + "C" + " ".join(pt(x) for x in it[2:5])); last = pt(it[4])
            elif op == "re":
                rr = it[1]; q = [pt(rr.tl), pt(rr.tr), pt(rr.br), pt(rr.bl)]
                parts.append(f"M{q[0]}L{q[1]}L{q[2]}L{q[3]}Z"); last = None
            elif op == "qu":
                qd = it[1]; q = [pt(qd.ul), pt(qd.ur), pt(qd.lr), pt(qd.ll)]
                parts.append(f"M{q[0]}L{q[1]}L{q[2]}L{q[3]}Z"); last = None
        if g.get("closePath") and parts: parts.append("Z"); last = None
        buckets.setdefault(key, []).append("".join(parts))
    out = []
    order = {"h": 0, "l": 1, "m": 2, "w": 3, "t": 4}
    for (cls, w), ds in sorted(buckets.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        d = "".join(ds)
        if cls in ("t", "h"):
            out.append(f'<path class="{cls}" fill="{COL[cls]}" d="{d}"/>')
        else:
            out.append(f'<path class="{cls}" fill="none" stroke="{COL[cls]}" stroke-linecap="round" stroke-linejoin="round" stroke-width="{fmt(max(w,0.12))}" d="{d}"/>')
    W, H = crop.width, crop.height
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt(W)} {fmt(H)}" width="{fmt(W)}" height="{fmt(H)}">'
           + "".join(out) + "</svg>")
    return svg, crop

if __name__ == "__main__":
    src, idx, mode, dst = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    d = pymupdf.open(src)
    svg, crop = convert(d[idx - 1], mode)
    open(dst, "w", encoding="utf-8").write(svg)
    print(json.dumps({"crop": [round(crop.x0, 2), round(crop.y0, 2), round(crop.width, 2), round(crop.height, 2)], "bytes": len(svg)}))
