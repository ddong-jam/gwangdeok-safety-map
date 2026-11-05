"""윈도우 글자 인식(OCR, 한국어)으로 도면 그림 속 글자와 위치를 읽는다.

    pip install winrt-runtime winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging \
        winrt-Windows.Storage winrt-Windows.Storage.Streams winrt-Windows.Foundation \
        winrt-Windows.Foundation.Collections winrt-Windows.Globalization
    python tools/ocr.py <png 폴더> <결과.tsv>

결과는 한 줄에 하나: 층 id, x0, y0, x1, y1 (그림 픽셀), 글자  (탭으로 구분)
윈도우 설정에 한국어 언어 팩(글자 인식 포함)이 있어야 한다.
"""
import asyncio
import os
import sys

from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage import FileAccessMode, StorageFile


async def read_image(engine, path):
    f = await StorageFile.get_file_from_path_async(os.path.abspath(path))
    stream = await f.open_async(FileAccessMode.READ)
    try:
        decoder = await BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        result = await engine.recognize_async(bitmap)
    finally:
        stream.close()
    rows = []
    for line in result.lines:
        rects = [w.bounding_rect for w in line.words]
        x0 = min(r.x for r in rects)
        y0 = min(r.y for r in rects)
        x1 = max(r.x + r.width for r in rects)
        y1 = max(r.y + r.height for r in rects)
        rows.append((int(x0), int(y0), int(x1), int(y1), line.text))
    return rows


async def main(folder, out):
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        sys.exit("글자 인식 엔진을 만들 수 없어요 (윈도우 한국어 언어 팩 확인)")
    lines = []
    for name in sorted(os.listdir(folder)):
        if name.endswith(".png"):
            for x0, y0, x1, y1, text in await read_image(engine, os.path.join(folder, name)):
                lines.append(f"{name[:-4]}\t{x0}\t{y0}\t{x1}\t{y1}\t{text}")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{out}: {len(lines)}줄")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
