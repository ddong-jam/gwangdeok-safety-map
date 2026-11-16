"""윈도우 글자 인식(OCR, 한국어)으로 도면 그림 속 글자와 위치를 읽는다.

    pip install winrt-runtime winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging \
        winrt-Windows.Storage winrt-Windows.Storage.Streams winrt-Windows.Foundation \
        winrt-Windows.Foundation.Collections winrt-Windows.Globalization
    python tools/ocr.py <png 폴더> <결과.tsv>

결과는 한 줄에 하나: 층 id, x0, y0, x1, y1 (그림 픽셀), 글자  (탭으로 구분)
윈도우 설정에 한국어 언어 팩(글자 인식 포함)이 있어야 한다.
"""
import asyncio  # 기다렸다 이어서 하는 함수(async)를 실행하는 도구
import os  # 폴더·파일 경로 도구
import sys  # 실행할 때 받은 값을 읽고, 실패하면 끝내는 도구

from winrt.windows.graphics.imaging import BitmapDecoder  # 윈도우: 그림 파일을 읽는 도구
from winrt.windows.media.ocr import OcrEngine  # 윈도우: 글자 인식 엔진
from winrt.windows.storage import FileAccessMode, StorageFile  # 윈도우: 파일을 여는 도구


async def read_image(engine, path):  # 그림 한 장에서 글자를 읽는 함수
    f = await StorageFile.get_file_from_path_async(os.path.abspath(path))  # 그림 파일을 찾는다
    stream = await f.open_async(FileAccessMode.READ)  # 읽기용으로 연다
    try:  # 읽는 중 문제가 생겨도 파일은 닫게 한다
        decoder = await BitmapDecoder.create_async(stream)  # 그림 해석 도구
        bitmap = await decoder.get_software_bitmap_async()  # 그림 데이터
        result = await engine.recognize_async(bitmap)  # 글자를 인식한다
    finally:  # 끝나면 항상
        stream.close()  # 파일을 닫는다
    rows = []  # 결과 줄들
    for line in result.lines:  # 인식한 글자 줄마다
        rects = [w.bounding_rect for w in line.words]  # 단어들을 둘러싼 네모들
        x0 = min(r.x for r in rects)  # 줄 전체의 왼쪽
        y0 = min(r.y for r in rects)  # 줄 전체의 위
        x1 = max(r.x + r.width for r in rects)  # 줄 전체의 오른쪽
        y1 = max(r.y + r.height for r in rects)  # 줄 전체의 아래
        rows.append((int(x0), int(y0), int(x1), int(y1), line.text))  # 위치와 글자를 저장
    return rows  # 결과를 돌려준다


async def main(folder, out):  # 폴더의 모든 그림을 읽어 결과 파일을 만드는 함수
    engine = OcrEngine.try_create_from_user_profile_languages()  # 윈도우 언어 설정으로 인식 엔진을 만든다
    if engine is None:  # 못 만들면
        sys.exit("글자 인식 엔진을 만들 수 없어요 (윈도우 한국어 언어 팩 확인)")  # 안내하고 끝낸다
    lines = []  # 결과 줄들
    for name in sorted(os.listdir(folder)):  # 폴더의 파일을 이름순으로
        if name.endswith(".png"):  # png 그림이면
            for x0, y0, x1, y1, text in await read_image(engine, os.path.join(folder, name)):  # 글자를 읽어
                lines.append(f"{name[:-4]}\t{x0}\t{y0}\t{x1}\t{y1}\t{text}")  # "층 id, 위치, 글자" 줄로 만든다
    with open(out, "w", encoding="utf-8") as f:  # 결과 파일을 열어
        f.write("\n".join(lines) + "\n")  # 모든 줄을 쓴다
    print(f"{out}: {len(lines)}줄")  # 몇 줄인지 보여준다


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    asyncio.run(main(sys.argv[1], sys.argv[2]))  # 받은 폴더와 결과 파일 이름으로 실행
