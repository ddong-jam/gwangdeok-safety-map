# 학생용·선생님용 화면이 함께 쓰는 작은 도구들 (화면 조작, 배지, 시간 표시, 사진 줄이기)
import asyncio
import html
from datetime import datetime, timedelta, timezone

from js import Blob, Object, URL, document, window
from pyodide.ffi import create_proxy, to_js

from campus import CATEGORIES, KINDS, SEVERITIES, STATUSES, kind_of

KST = timezone(timedelta(hours=9))
SEVERITY_DOTS = {"urgent": "🔴", "high": "🟠", "mid": "🟡", "low": "🔵"}
_proxies = []  # 파이썬 함수를 브라우저 이벤트에 연결한 것들 (지워지지 않게 보관)


def js(o):
    """파이썬 dict/list → 자바스크립트 객체."""
    return to_js(o, dict_converter=Object.fromEntries)


def q(sel, root=None):
    return (root or document).querySelector(sel)


def qa(sel, root=None):
    return list((root or document).querySelectorAll(sel))


def on(el, event, fn, prevent=False, **opts):
    """el 에 이벤트를 연결한다. async 함수도 된다.
    prevent=True 면 기본 동작(폼 전송 등)을 바로 막는다 (async 함수는 한 박자 늦게 돌기 때문)."""
    def handler(e):
        if prevent:
            e.preventDefault()
        result = fn(e)
        if asyncio.iscoroutine(result):
            asyncio.ensure_future(result)

    proxy = create_proxy(handler)
    _proxies.append(proxy)
    if opts:
        el.addEventListener(event, proxy, js(opts))
    else:
        el.addEventListener(event, proxy)
    return proxy


def esc(s):
    return html.escape(str(s if s is not None else ""))


def closest(ev, sel):
    t = ev.target
    return t.closest(sel) if t and hasattr(t, "closest") else None


# ── 시간 ──────────────────────────────────────────
def parse_time(iso):
    if not iso:
        return None
    dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def fmt_time(iso):
    dt = parse_time(iso)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M") if dt else "-"


def time_ago(iso):
    dt = parse_time(iso)
    if not dt:
        return ""
    s = (datetime.now(timezone.utc) - dt).total_seconds()
    if s < 60:
        return "방금"
    if s < 3600:
        return f"{int(s // 60)}분 전"
    if s < 86400:
        return f"{int(s // 3600)}시간 전"
    if s < 86400 * 7:
        return f"{int(s // 86400)}일 전"
    return dt.astimezone(KST).strftime("%Y-%m-%d")


# ── 배지 ──────────────────────────────────────────
def status_badge(status):
    return f'<span class="status {esc(status)}">{esc(STATUSES.get(status, status))}</span>'


def severity_badge(sev):
    name, color = SEVERITIES.get(sev, (sev, "#94a3b8"))
    return f'<span class="sev-tag" style="--c:{color}">{esc(name)}</span>'


def kind_badge(r):
    k = kind_of(r)
    name, icon, _ = KINDS[k]
    return f'<span class="kind-tag kind-{k}">{icon} {esc(name)}</span>'


def category_name(cat):
    return CATEGORIES.get(cat, cat)


def is_open(r):
    return r.get("status") in ("new", "doing")


# ── 알림 · 파일 ───────────────────────────────────
_toast_timer = [None]
_hide_toast = create_proxy(lambda: q("#toast").classList.remove("show"))  # 한 번만 만들어 계속 쓴다


def toast(msg):
    t = q("#toast")
    t.textContent = msg
    t.classList.add("show")
    if _toast_timer[0]:
        window.clearTimeout(_toast_timer[0])
    _toast_timer[0] = window.setTimeout(_hide_toast, 2200)


def download(filename, text, mime="text/plain"):
    blob = Blob.new([text], js({"type": mime}))
    a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)


async def shrink_photo(file, max_side=1024, quality=0.72):
    """사진을 최대 1024px JPEG 로 줄여 data URL 로 돌려준다."""
    bmp = await window.createImageBitmap(file)
    k = min(1, max_side / max(bmp.width, bmp.height))
    canvas = document.createElement("canvas")
    canvas.width = round(bmp.width * k)
    canvas.height = round(bmp.height * k)
    canvas.getContext("2d").drawImage(bmp, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL("image/jpeg", quality)


def hide_loading():
    el = q("#loading")
    if el:
        el.remove()
