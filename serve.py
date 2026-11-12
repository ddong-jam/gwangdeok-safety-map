# 안전지도 테스트 서버
# 브라우저가 옛날 파일을 저장해 두고 쓰지 않도록(캐시 끄기) 항상 최신 파일을 보낸다.
# 실행: python serve.py  (또는 IDLE 에서 열고 F5)  →  브라우저가 http://localhost:5178 을 자동으로 연다
# 끄기: 이 창에서 Ctrl+C (IDLE 은 Shell 창을 닫기)
import http.server
import os
import sys
import threading
import webbrowser

os.chdir(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if a != "--no-open"]
PORT = int(args[0]) if args else 5178


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if "--no-open" not in sys.argv:
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
print(f"학생 화면: http://localhost:{PORT}   선생님 화면: http://localhost:{PORT}/teacher.html", flush=True)
print(f"Serving HTTP on port {PORT} (http://localhost:{PORT})", flush=True)
http.server.ThreadingHTTPServer(("", PORT), NoCacheHandler).serve_forever()
