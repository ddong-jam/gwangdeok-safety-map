# 학생용·선생님용 화면이 함께 쓰는 작은 도구들 (화면 조작, 배지, 시간 표시, 사진 줄이기)
import asyncio  # 기다렸다 이어서 하는 함수(async)를 실행하는 도구
import html  # 글자를 화면에 안전하게 넣기 위해 <, > 같은 기호를 바꾸는 도구
from datetime import datetime, timedelta, timezone  # 날짜·시간 도구

from js import Blob, Object, URL, document, window  # 브라우저(자바스크립트)의 기능들을 파이썬에서 쓰기 위해 불러온다
from pyodide.ffi import create_proxy, to_js  # 파이썬 함수·값을 자바스크립트로 넘기는 도구

from campus import CATEGORIES, KINDS, SEVERITIES, STATUSES, kind_of  # 신고 종류·유형·위험도·상태 이름표

KST = timezone(timedelta(hours=9))  # 한국 시간대 (세계 표준시 + 9시간)
SEVERITY_DOTS = {"urgent": "🔴", "high": "🟠", "mid": "🟡", "low": "🔵"}  # 위험도별 동그라미 색
_proxies = []  # 파이썬 함수를 브라우저 이벤트에 연결한 것들 (지워지지 않게 보관)


def js(o):  # 파이썬 값을 자바스크립트 값으로 바꾸는 함수
    """파이썬 dict/list → 자바스크립트 객체."""  # 이 함수가 하는 일을 적은 설명글
    return to_js(o, dict_converter=Object.fromEntries)  # 사전(dict)은 자바스크립트 객체로 바꿔서 돌려준다


def q(sel, root=None):  # 화면에서 요소 하나를 찾는 함수 (예: q("#map"))
    return (root or document).querySelector(sel)  # 처음으로 맞는 요소를 돌려준다


def qa(sel, root=None):  # 화면에서 맞는 요소를 모두 찾는 함수
    return list((root or document).querySelectorAll(sel))  # 찾은 요소들을 파이썬 목록으로 돌려준다


def on(el, event, fn, prevent=False, **opts):  # 요소에 클릭 같은 이벤트를 연결하는 함수
    """el 에 이벤트를 연결한다. async 함수도 된다.
    prevent=True 면 기본 동작(폼 전송 등)을 바로 막는다 (async 함수는 한 박자 늦게 돌기 때문)."""
    def handler(e):  # 이벤트가 일어나면 실제로 불리는 함수
        if prevent:  # 기본 동작을 막으라고 했으면
            e.preventDefault()  # 페이지 새로고침 같은 기본 동작을 막는다
        result = fn(e)  # 연결한 함수를 실행한다
        if asyncio.iscoroutine(result):  # 그 함수가 async 함수였으면
            asyncio.ensure_future(result)  # 끝날 때까지 이어서 실행되게 맡긴다

    proxy = create_proxy(handler)  # 파이썬 함수를 브라우저가 부를 수 있게 감싼다
    _proxies.append(proxy)  # 지워지지 않게 목록에 보관한다
    if opts:  # 추가 옵션(예: passive)이 있으면
        el.addEventListener(event, proxy, js(opts))  # 옵션과 함께 이벤트를 연결한다
    else:  # 옵션이 없으면
        el.addEventListener(event, proxy)  # 그냥 이벤트를 연결한다
    return proxy  # 나중에 떼어낼 수 있게 돌려준다


def esc(s):  # 글자를 화면 HTML 에 안전하게 넣을 수 있게 바꾸는 함수
    return html.escape(str(s if s is not None else ""))  # None 이면 빈칸, 아니면 <, >, & 등을 안전한 글자로 바꾼다


def closest(ev, sel):  # 누른 곳에서 가장 가까운 조상 요소를 찾는 함수
    t = ev.target  # 실제로 누른 요소
    return t.closest(sel) if t and hasattr(t, "closest") else None  # 조건에 맞는 가장 가까운 요소 (없으면 None)


# ── 시간 ──────────────────────────────────────────
def parse_time(iso):  # 글자로 된 시각을 날짜 값으로 바꾸는 함수
    if not iso:  # 시각이 비어 있으면
        return None  # 없음
    dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))  # "…Z" 를 파이썬이 읽을 수 있게 바꿔 읽는다
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # 시간대가 없으면 세계 표준시로 정한다


def now_iso():  # 지금 시각을 글자로 돌려주는 함수
    return datetime.now(timezone.utc).isoformat()  # 세계 표준시 기준 "2026-11-16T…" 형식


def fmt_time(iso):  # 시각을 "2026-11-16 14:30" 처럼 보기 좋게 바꾸는 함수
    dt = parse_time(iso)  # 날짜 값으로 바꾼다
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M") if dt else "-"  # 한국 시간으로 바꿔 글자로 (없으면 "-")


def time_ago(iso):  # "3분 전" 처럼 지난 시간을 보여주는 함수
    dt = parse_time(iso)  # 날짜 값으로 바꾼다
    if not dt:  # 시각이 없으면
        return ""  # 빈칸
    s = (datetime.now(timezone.utc) - dt).total_seconds()  # 지금까지 지난 초
    if s < 60:  # 1분 안이면
        return "방금"  # "방금"
    if s < 3600:  # 1시간 안이면
        return f"{int(s // 60)}분 전"  # "○분 전"
    if s < 86400:  # 하루 안이면
        return f"{int(s // 3600)}시간 전"  # "○시간 전"
    if s < 86400 * 7:  # 일주일 안이면
        return f"{int(s // 86400)}일 전"  # "○일 전"
    return dt.astimezone(KST).strftime("%Y-%m-%d")  # 더 오래됐으면 날짜를 보여준다


# ── 배지 ──────────────────────────────────────────
def status_badge(status):  # 처리 상태(접수·처리중 등) 표시를 만드는 함수
    return f'<span class="status {esc(status)}">{esc(STATUSES.get(status, status))}</span>'  # 상태별 색이 있는 작은 표시


def severity_badge(sev):  # 위험도(긴급·높음 등) 표시를 만드는 함수
    name, color = SEVERITIES.get(sev, (sev, "#94a3b8"))  # 위험도 이름과 색 (모르는 값이면 회색)
    return f'<span class="sev-tag" style="--c:{color}">{esc(name)}</span>'  # 색 점이 붙은 위험도 표시


def kind_badge(r):  # 위험/불편 종류 표시를 만드는 함수
    k = kind_of(r)  # 이 신고의 종류 (danger 또는 incon)
    name, icon, _ = KINDS[k]  # 종류 이름과 아이콘
    return f'<span class="kind-tag kind-{k}">{icon} {esc(name)}</span>'  # "⚠️ 위험" 같은 표시


def category_name(cat):  # 유형 코드를 한글 이름으로 바꾸는 함수
    return CATEGORIES.get(cat, cat)  # 예: "slip" → "미끄럼·낙상"


def is_open(r):  # 아직 처리가 안 끝난 신고인지 확인하는 함수
    return r.get("status") in ("new", "doing")  # 접수 또는 처리중이면 True


# ── 알림 · 파일 ───────────────────────────────────
_toast_timer = [None]  # 알림 메시지를 숨길 타이머 번호 보관
_hide_toast = create_proxy(lambda: q("#toast").classList.remove("show"))  # 한 번만 만들어 계속 쓴다


def toast(msg):  # 화면 아래에 잠깐 알림 메시지를 띄우는 함수
    t = q("#toast")  # 알림 상자
    t.textContent = msg  # 메시지를 넣는다
    t.classList.add("show")  # 보이게 한다
    if _toast_timer[0]:  # 이전 알림의 숨김 타이머가 있으면
        window.clearTimeout(_toast_timer[0])  # 취소한다
    _toast_timer[0] = window.setTimeout(_hide_toast, 2200)  # 2.2초 뒤에 숨긴다


def download(filename, text, mime="text/plain"):  # 글을 파일로 내려받게 하는 함수 (CSV 등)
    blob = Blob.new([text], js({"type": mime}))  # 글을 파일 덩어리로 만든다
    a = document.createElement("a")  # 보이지 않는 링크를 만든다
    a.href = URL.createObjectURL(blob)  # 파일 덩어리에 임시 주소를 붙인다
    a.download = filename  # 내려받을 파일 이름
    a.click()  # 링크를 눌러 내려받기를 시작한다
    URL.revokeObjectURL(a.href)  # 임시 주소를 지워 메모리를 돌려준다


async def shrink_photo(file, max_side=1024, quality=0.72):  # 사진을 작게 줄이는 함수
    """사진을 최대 1024px JPEG 로 줄여 data URL 로 돌려준다."""  # 이 함수가 하는 일을 적은 설명글
    bmp = await window.createImageBitmap(file)  # 사진 파일을 그림으로 읽는다
    k = min(1, max_side / max(bmp.width, bmp.height))  # 긴 변이 1024px 이 되도록 줄일 비율 (작으면 그대로)
    canvas = document.createElement("canvas")  # 그림을 다시 그릴 도화지
    canvas.width = round(bmp.width * k)  # 줄인 가로 크기
    canvas.height = round(bmp.height * k)  # 줄인 세로 크기
    canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height)  # 줄인 크기로 그린다
    return canvas.toDataURL("image/jpeg", quality)  # JPEG 글자 데이터로 바꿔 돌려준다


def hide_loading():  # 처음 준비 화면을 없애는 함수
    el = q("#loading")  # 준비 화면
    if el:  # 아직 있으면
        el.remove()  # 지운다
