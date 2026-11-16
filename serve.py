# 안전지도 테스트 서버
# 브라우저가 옛날 파일을 저장해 두고 쓰지 않도록(캐시 끄기) 항상 최신 파일을 보낸다.
# 실행: python serve.py  (또는 IDLE 에서 열고 F5)  →  브라우저가 http://localhost:5178 을 자동으로 연다
# 끄기: 이 창에서 Ctrl+C (IDLE 은 Shell 창을 닫기)
import http.server  # 파이썬에 들어 있는 간단한 웹 서버 도구
import os  # 폴더 위치를 다루는 도구
import sys  # 실행할 때 받은 값(포트 번호 등)을 읽는 도구
import threading  # 잠시 뒤에 일을 하게 하는 타이머 도구
import webbrowser  # 브라우저를 여는 도구

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # 이 파일이 있는 폴더를 기준 폴더로 정한다 (사이트 파일을 여기서 보낸다)
args = [a for a in sys.argv[1:] if a != "--no-open"]  # 실행할 때 받은 값 중 "--no-open" 을 뺀 나머지
PORT = int(args[0]) if args else 5178  # 포트 번호 (따로 안 주면 5178)


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):  # 파일을 보낼 때 "저장해 두지 마" 표시를 붙이는 처리기
    def end_headers(self):  # 응답 머리말을 끝내기 직전에 불리는 함수
        self.send_header("Cache-Control", "no-store")  # 브라우저에게 이 파일을 저장해 두지 말라고 알린다
        super().end_headers()  # 원래 하던 머리말 마무리를 그대로 한다


if "--no-open" not in sys.argv:  # "--no-open" 을 받지 않았으면
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()  # 1초 뒤 브라우저로 사이트를 연다
print(f"학생 화면: http://localhost:{PORT}   선생님 화면: http://localhost:{PORT}/teacher.html", flush=True)  # 주소를 화면에 보여준다
print(f"Serving HTTP on port {PORT} (http://localhost:{PORT})", flush=True)  # 서버가 켜졌다고 알린다
http.server.ThreadingHTTPServer(("", PORT), NoCacheHandler).serve_forever()  # 서버를 켜고 끌 때까지 계속 요청을 받는다
