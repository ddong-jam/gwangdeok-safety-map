"""Regenerate plans/*.svg from the original CAD PDFs.

usage: python tools/build_plans.py <전체배치도.pdf> <면적 PDF>
"""
import os, sys  # 폴더 경로 도구, 실행할 때 받은 값을 읽는 도구
import pymupdf  # PDF 를 읽는 도구
sys.path.insert(0, os.path.dirname(__file__))  # 이 폴더(tools)의 파일도 불러올 수 있게 한다
from pdf2svg import convert  # PDF 한 쪽을 SVG 도면으로 바꾸는 함수

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 프로젝트 맨 위 폴더
# (file id, page number in the area PDF)
PAGES = {  # 층 id → 면적 PDF 의 몇 쪽인지
    "b1-b1": 1, "b1-1f": 2, "b1-2f": 3, "b1-3f": 4, "b1-4f": 5, "b1-rf": 6,  # 만대관: 지하 1층 ~ 옥상
    "b2-b1": 7, "b2-1f": 8, "b2-2f": 9, "b2-3f": 10, "b2-4f": 11,  # 덕린관: 지하 1층 ~ 4층
    "b4-1f": 12, "b4-2f": 13, "b4-3f": 14, "b4-4f": 15,  # 중학교: 1 ~ 4층
    "b6-1f": 16, "b6-2f": 17, "b6-l1": 18, "b6-l2": 19, "b6-lr": 20,  # 복지관: 1·2층, 연결통로
    "b3-b1": 21, "b3-1f": 22, "b3-2f": 23, "b3-3f": 24, "b3-4f": 25, "b3-rf": 26,  # 단재관: 지하 1층 ~ 옥상
    "b8-b1": 27, "b8-1f": 28, "b8-2f": 29, "b8-rf": 30,  # 체육관: 지하 1층 ~ 지붕
    "b9-1f": 31, "b9-2f": 32, "b9-3f": 33, "b9-4f": 34, "b9-5f": 35,  # 특별교실동(덕후재+귀촌관): 1 ~ 5층
    "b10-1f": 36, "b5-1f": 37, "wc-1f": 38,  # 체육실동, 수위실, 야외 화장실
}  # 쪽 번호 목록 끝
SITE_CROP = pymupdf.Rect(160, 97.44, 1035, 775)  # 전체 배치도에서 잘라 쓸 영역
# sheets where the automatic crop misses the drawing
CROPS = {"b5-1f": pymupdf.Rect(335, 150, 875, 650), "wc-1f": pymupdf.Rect(232, 78, 968, 714)}  # 자동으로 잘 못 자르는 쪽은 직접 영역을 정한다

def main(site_pdf, area_pdf):  # 모든 도면을 다시 만드는 함수
    svg, crop = convert(pymupdf.open(site_pdf)[0], "site", crop=SITE_CROP)  # 전체 배치도 첫 쪽을 SVG 로
    open(os.path.join(ROOT, "plans", "site.svg"), "w", encoding="utf-8").write(svg)  # plans/site.svg 로 저장
    doc = pymupdf.open(area_pdf)  # 층별 면적 PDF 를 연다
    for pid, n in PAGES.items():  # 층마다
        svg, crop = convert(doc[n - 1], "floor", crop=CROPS.get(pid))  # 그 쪽을 SVG 로 (정한 영역이 있으면 그걸로)
        open(os.path.join(ROOT, "plans", pid + ".svg"), "w", encoding="utf-8").write(svg)  # plans/<층 id>.svg 로 저장
        print(pid, round(crop.width, 2), round(crop.height, 2), len(svg) // 1024, "KB")  # 층 id, 크기, 파일 용량을 보여준다

if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    main(sys.argv[1], sys.argv[2])  # 받은 두 PDF 경로로 실행
