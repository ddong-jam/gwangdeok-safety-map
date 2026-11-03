"""Regenerate plans/*.svg from the original CAD PDFs.

usage: python tools/build_plans.py <전체배치도.pdf> <면적 PDF>
"""
import os, sys
import pymupdf
sys.path.insert(0, os.path.dirname(__file__))
from pdf2svg import convert

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# (file id, page number in the area PDF)
PAGES = {
    "b1-b1": 1, "b1-1f": 2, "b1-2f": 3, "b1-3f": 4, "b1-4f": 5, "b1-rf": 6,
    "b2-b1": 7, "b2-1f": 8, "b2-2f": 9, "b2-3f": 10, "b2-4f": 11,
    "b4-1f": 12, "b4-2f": 13, "b4-3f": 14, "b4-4f": 15,
    "b6-1f": 16, "b6-2f": 17, "b6-l1": 18, "b6-l2": 19, "b6-lr": 20,
    "b3-b1": 21, "b3-1f": 22, "b3-2f": 23, "b3-3f": 24, "b3-4f": 25, "b3-rf": 26,
    "b8-b1": 27, "b8-1f": 28, "b8-2f": 29, "b8-rf": 30,
    "b9-1f": 31, "b9-2f": 32, "b9-3f": 33, "b9-4f": 34, "b9-5f": 35,
    "b10-1f": 36, "b5-1f": 37, "wc-1f": 38,
}
SITE_CROP = pymupdf.Rect(160, 97.44, 1035, 775)
# sheets where the automatic crop misses the drawing
CROPS = {"b5-1f": pymupdf.Rect(335, 150, 875, 650), "wc-1f": pymupdf.Rect(232, 78, 968, 714)}

def main(site_pdf, area_pdf):
    svg, crop = convert(pymupdf.open(site_pdf)[0], "site", crop=SITE_CROP)
    open(os.path.join(ROOT, "plans", "site.svg"), "w", encoding="utf-8").write(svg)
    doc = pymupdf.open(area_pdf)
    for pid, n in PAGES.items():
        svg, crop = convert(doc[n - 1], "floor", crop=CROPS.get(pid))
        open(os.path.join(ROOT, "plans", pid + ".svg"), "w", encoding="utf-8").write(svg)
        print(pid, round(crop.width, 2), round(crop.height, 2), len(svg) // 1024, "KB")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
