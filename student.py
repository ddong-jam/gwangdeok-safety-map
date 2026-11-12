# 학생용 화면: 캠퍼스 → 건물 → 층 평면도에서 위험한 곳을 찍어 신고한다.
# 화면 틀(pages.py)과 꾸미기(theme.py)를 먼저 그린다 — 아래 코드가 그 요소들을 찾기 때문
import pages
import theme

theme.apply()
pages.mount("student")

import asyncio
import json
import time

from js import window
from pyodide.ffi import create_proxy

from campus import (BUILDING_BY_ID, BUILDINGS, CATEGORIES, FLOOR_INDEX, KINDS, LINKS, SEVERITIES, SITE_ID, building_at,
                    kind_of, link_label, place_name, plan_of, search)
from common import (SEVERITY_DOTS, category_name, closest, esc, fmt_time, hide_loading, is_open, kind_badge, on, q, qa,
                    shrink_photo, status_badge, severity_badge, time_ago, toast)
import guard
from store import SCHOOL_DOMAIN, SHARED, STUDENT_LOGIN, StoreError, store
from viewer import PlanViewer

state = {
    "place": SITE_ID,     # 지금 보는 지도 ("site" 또는 층 id, 예: "b2-1f")
    "loaded": None,
    "mode": "browse",     # "browse" | "report"
    "draft": None,        # 찍은 위치 (x, y)
    "selected": None,
    "reports": [],        # 학생에게 보여도 되는 신고 전체
    "mine": set(),        # 이 화면에서 내가 접수한 신고
    "photo": None,
    "hit": None,          # 검색으로 찾은 곳 (x, y)
    "liked": set(),       # 내가 공감한 신고
    "like_after": None,   # 로그인을 마치면 공감할 신고
}
viewer = PlanViewer(q("#map"))


def plan_url(place):
    return plan_of(place)[0]


def open_count(pred):
    return sum(1 for r in state["reports"] if is_open(r) and pred(r))


def floors_of(b):
    return {f.id for f in b.floors}


async def refresh_reports():
    try:
        state["reports"] = await store.list_public()
        state["liked"] = await store.my_likes() if store.student else set()
    except StoreError as e:
        toast(str(e))


# ── 주소(#b2-1f)로 위치 기억 ─────────────────────────
def parse_hash():
    h = window.decodeURIComponent(window.location.hash.lstrip("#/"))
    if not h:
        return SITE_ID
    if h in FLOOR_INDEX:
        return h
    b = BUILDING_BY_ID.get(h)
    return b.default_floor.id if b else SITE_ID


def go(place):
    target = "" if place == SITE_ID else f"#{place}"
    if window.location.hash == target or (not target and not window.location.hash):
        asyncio.ensure_future(navigate(place))
    else:
        window.location.hash = target


async def navigate(place, after=None):
    changed = place != state["loaded"]
    state["place"] = place
    if changed:
        state["hit"] = None
    if state["mode"] == "report":
        set_draft(None)
        set_mode("report")
    render_chrome()
    render_list()
    if changed:
        state["loaded"] = place
        try:
            if not await viewer.load(plan_url(place), locked=False, crop=plan_of(place)[1]):  # 캠퍼스 배치도도 확대·이동 (v2.3.1)
                return
        except Exception as e:
            toast(str(e))
            return
        draw_map()
    if after:
        after()


# ── 화면 그리기 ───────────────────────────────────
def render_chrome():
    place = state["place"]
    hit = FLOOR_INDEX.get(place)
    b, fl = hit if hit else (None, None)

    q("#crumbs").innerHTML = (
        '<span class="here">광덕중·고 캠퍼스</span>' if not b else
        f'<a href="#">캠퍼스</a><span class="sep">›</span><span class="here">{esc(b.name)}</span>')

    if b:
        btns = []
        for f in b.floors:
            n = open_count(lambda r, f=f: r["map"] == f.id)
            dot = f'<span class="dot">{n}</span>' if n else ""
            btns.append(f'<button role="tab" data-floor="{f.id}" aria-selected="{str(f.id == place).lower()}" '
                        f'title="{esc(f.name)}">{esc(f.label)}{dot}</button>')
        q("#floorbar").innerHTML = "".join(btns)
    else:
        q("#floorbar").innerHTML = ""

    if not b:
        cards = []
        for bb in BUILDINGS:
            n = open_count(lambda r, bb=bb: r["map"] in floors_of(bb))
            sub = " · ".join(x for x in (bb.dong, bb.sub) if x)
            cards.append(f'<button class="bld-card" style="--c:{bb.color}" data-building="{bb.id}">'
                         f'<strong>{esc(bb.name)}</strong><small>{esc(sub)}</small>'
                         f'{f"<span class=n>{n}</span>" if n else ""}</button>')
        q("#ctx").innerHTML = (
            '<h1>캠퍼스 평면도</h1><p class="sub">건물을 누르면 층별 평면도가 열려요.</p>'
            f'<div class="bld-grid">{"".join(cards)}</div>'
            '<p class="hint">운동장·주차장 같은 야외의 위험·불편은 지도에서 건물 밖 그 자리를 누르면 바로 신고돼요.</p>')
    else:
        area = f'<span class="tag">바닥면적 {fl.area:,.2f}㎡</span>' if fl.area else ""
        tabs = "".join(f'<button role="tab" data-floor="{f.id}" aria-selected="{str(f.id == place).lower()}">{esc(f.name)}</button>'
                       for f in b.floors)
        sub = " · ".join(x for x in (b.sub, b.dong) if x)
        q("#ctx").innerHTML = (
            '<a class="back-btn" href="#"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>캠퍼스로 돌아가기</a>'
            f'<h1>{esc(b.name)} <span style="color:var(--muted);font-weight:600">{esc(fl.name)}</span></h1>'
            f'<p class="sub">{esc(sub)}</p>'
            f'<div class="meta"><span class="tag color" style="--c:{b.color}">{esc(b.code)}</span>{area}'
            f'<span class="tag">{len(b.floors)}개 층 도면</span></div>'
            f'<div class="floor-list" role="tablist">{tabs}</div>'
            '<p class="hint">도면에서 <b>위험하거나 불편한 곳</b>을 누르면 그 자리에 바로 신고할 수 있어요.</p>')


def draw_map():
    here = [r for r in state["reports"] if r["map"] == state["place"]]
    if state["place"] == SITE_ID:
        counts = {b.id: open_count(lambda r, b=b: r["map"] in floors_of(b)) for b in BUILDINGS}
        viewer.draw_buildings(counts)
    else:
        viewer.draw_links([(x, y, t, link_label(t)) for x, y, t in LINKS.get(state["place"], [])])
    viewer.draw_hit(state["hit"])
    viewer.draw_pins(here, state["selected"])
    viewer.draw_draft(state["draft"])


def render_list():
    allr = state["reports"]
    opened = [r for r in allr if is_open(r)]
    q("#stats").innerHTML = (f'<span>처리 전<b>{len(opened)}</b></span>'
                             f'<span class="urgent">긴급<b>{sum(r["severity"] == "urgent" for r in opened)}</b></span>'
                             f'<span>완료<b>{len(allr) - len(opened)}</b></span>')
    place = state["place"]
    items = allr if place == SITE_ID else [r for r in allr if r["map"] == place]
    q("#listTitle").textContent = "전체 신고" if place == SITE_ID else "이 층의 신고"
    if not items:
        q("#reportList").innerHTML = ('<li class="empty">아직 신고가 없어요.<br/>위험하거나 불편한 곳을 보면 '
                                      '도면에서 그 자리를 눌러주세요.</li>')
        return
    rows = []
    for r in items[:60]:
        dot = "✅" if not is_open(r) else "🟣" if kind_of(r) == "incon" else SEVERITY_DOTS.get(r["severity"], "🟡")
        sel = " is-selected" if r["id"] == state["selected"] else ""
        spot = f' · {esc(r["spot"])}' if r.get("spot") else ""
        rows.append(f'<li><button class="report-item{sel}" data-id="{r["id"]}" type="button">'
                    f'<span class="sev-dot">{dot}</span><span class="t">{kind_badge(r)} {esc(r["title"])}{like_badge(r)}</span>{status_badge(r["status"])}'
                    f'<span class="w">{esc(place_name(r["map"]))}{spot} · {time_ago(r["created_at"])}</span></button></li>')
    q("#reportList").innerHTML = "".join(rows)


def like_badge(r):
    n = r.get("likes") or 0
    return f' <span class="like-count" title="나도 봤어요 {n}명">🙋{n}</span>' if n else ""


def render_all():
    render_chrome()
    render_list()
    draw_map()


# ── 지도 누르기 ───────────────────────────────────
def on_tap(x, y, target):
    pin = target.closest(".pin") if hasattr(target, "closest") else None
    link = target.closest(".link") if hasattr(target, "closest") else None
    if state["hit"]:  # 검색 표시는 지도를 한 번 누르면 지운다
        state["hit"] = None
        viewer.draw_hit(None)
    if link and state["mode"] != "report":
        go(link.dataset.target)
        return
    if pin and state["mode"] != "report":
        open_detail(pin.dataset.id)
        return
    if state["place"] == SITE_ID and state["mode"] != "report":
        b = building_at(x, y)
        if b:
            go(b.id)
            return
    # 도면 안을 누르면 그 자리에 바로 위험/불편 신고 (배치도에서는 건물 밖 = 야외)
    # 도면 둘레의 흰 여백을 누르면 신고 창을 열지 않는다
    w, h = viewer.size
    if not (0 <= x <= w and 0 <= y <= h) or not viewer.on_drawing(x, y, target):
        if state["mode"] == "report":
            toast("도면 안쪽을 눌러주세요")
        return
    set_draft((x, y))
    open_form()


viewer.on_tap = on_tap
viewer.on_view_change = viewer.scale_markers


# ── 신고 모드 ─────────────────────────────────────
def set_mode(mode):
    state["mode"] = mode
    reporting = mode == "report"
    window.document.body.classList.toggle("reporting", reporting)
    q("#btnReport").setAttribute("aria-pressed", str(reporting).lower())
    q("#btnReport span").textContent = "신고 취소" if reporting else "위험/불편 신고"
    q("#modeBanner").hidden = not reporting
    q("#modeText").textContent = (
        "지도에서 위험하거나 불편한 곳을 눌러주세요 (건물 안은 건물을 먼저 선택)" if state["place"] == SITE_ID
        else f"{place_name(state['place'])} 도면에서 위험하거나 불편한 곳을 눌러주세요")
    if not reporting:
        set_draft(None)


def set_draft(point):
    state["draft"] = point
    viewer.draw_draft(point)


on(q("#btnReport"), "click", lambda e: set_mode("browse" if state["mode"] == "report" else "report"))
on(q("#modeCancel"), "click", lambda e: set_mode("browse"))


def on_key(e):
    if e.key == "Escape" and state["mode"] == "report" and not q("dialog[open]"):
        set_mode("browse")


on(window.document, "keydown", on_key)


# ── 신고서 ───────────────────────────────────────
form = q("#reportForm")
form_dialog = q("#formDialog")

q("#catChips").innerHTML = "".join(
    f'<label><input type="radio" name="category" value="{k}" {"checked" if i == 0 else ""}/><span>{esc(v)}</span></label>'
    for i, (k, v) in enumerate(CATEGORIES.items()))
q("#sevChips").innerHTML = "".join(
    f'<label style="--c:{c}"><input type="radio" name="severity" value="{k}" {"checked" if k == "mid" else ""}/><span>{esc(n)}</span></label>'
    for k, (n, c) in SEVERITIES.items())


SEV_LEGEND = {"danger": "얼마나 위험한가요?", "incon": "얼마나 급한가요?"}


def on_kind_change(e=None):
    k = checked("kind") or "danger"
    q("#sevLegend").textContent = SEV_LEGEND[k]
    q("#formSubmit").textContent = f"{KINDS[k][0]} 신고 접수"
    form_dialog.dataset.kind = k


on(q("#kindChips"), "change", on_kind_change)


def open_form():
    if STUDENT_LOGIN and not store.student:
        open_login()  # 신고할 때만 로그인 (찍은 자리는 기억해 둔다)
        return
    show_who()
    form.reset()
    on_kind_change()
    state["photo"] = None
    q("#photoPreview").hidden = True
    q("#photoHint").textContent = "사진 추가 · 촬영"
    q("#formWhere").textContent = f"📍 {place_name(state['place'])}"
    state["form_opened"] = time.time()
    form_dialog.showModal()


def close_form(e=None):
    form_dialog.close("cancel")


# ── 학생 로그인 (신고할 때만) ──────────────────────
login_dialog = q("#loginDialog")
PENDING_KEY = "kd-safety-pending-report"


def show_who():
    st = store.student if STUDENT_LOGIN else None
    who = q("#formWho")
    who.hidden = not st
    if st:
        who.innerHTML = (f'👤 {esc(st.get("name") or st["email"])} <small>{esc(st["email"])}</small> '
                         f'<button type="button" class="link-btn" id="btnStudentLogout">로그아웃</button>')
    q("#noticeRecord").textContent = ("신고하면 내 구글 계정과 시간이 함께 기록돼요. (선생님만 볼 수 있어요)" if st
                                      else "신고하면 시간과 이 기기 정보가 함께 기록돼요. (익명이어도 기록돼요)")


def open_login(purpose="신고"):
    q("#loginPurpose").textContent = "나도 봤어요" if purpose == "like" else "위험/불편 신고"
    q("#demoNameField").hidden = SHARED
    q("#loginTitle").textContent = "학교 구글 계정으로 로그인" if SCHOOL_DOMAIN else "구글 계정으로 로그인"
    dom = q("#loginDomain")
    dom.hidden = not SCHOOL_DOMAIN
    dom.innerHTML = f"<b>@{esc(SCHOOL_DOMAIN)}</b> 학교 계정만 신고할 수 있어요." if SCHOOL_DOMAIN else ""
    login_dialog.showModal()


def on_login_close(e):
    if not store.student:
        state["like_after"] = None
    if not (STUDENT_LOGIN and store.student) and not form_dialog.open:
        set_draft(None)


async def on_google(e):
    if not SHARED:  # 체험 모드: 구글 대신 이름만
        name = str(q("#demoName").value).strip() or "체험 학생"
        await store.student_login(name)
        rid, state["like_after"] = state["like_after"], None
        login_dialog.close()
        if rid:
            await refresh_reports()
            await do_like(rid)
        else:
            open_form()
        return
    # 구글에 다녀오면 페이지가 새로 열리니, 보던 층과 찍은 자리를 기억해 둔다
    window.sessionStorage.setItem(PENDING_KEY, json.dumps({"place": state["place"], "draft": state["draft"],
                                                           "like": state["like_after"]}))
    back = window.location.origin + window.location.pathname
    window.location.href = store.google_url(back)


async def finish_google_return():
    """구글 로그인에서 돌아왔을 때: 로그인을 마치고, 보던 층으로 가서 신고 창을 다시 연다."""
    h = str(window.location.hash)
    if "access_token=" not in h and "error=" not in h:
        return None
    err = await store.finish_google(h)
    try:
        pending = json.loads(window.sessionStorage.getItem(PENDING_KEY) or "{}")
    except Exception:
        pending = {}
    window.sessionStorage.removeItem(PENDING_KEY)
    place = pending.get("place") or SITE_ID
    window.history.replaceState(None, "", window.location.pathname + ("" if place == SITE_ID else f"#{place}"))
    if err:
        toast(err)
        return None
    toast("로그인했어요")
    return pending


def on_who_click(e):
    if closest(e, "#btnStudentLogout"):
        store.student_logout()
        close_form()
        toast("로그아웃했어요")


on(q("#btnGoogle"), "click", on_google)
on(login_dialog, "close", on_login_close)
on(login_dialog.querySelector("[data-close]"), "click", lambda e: login_dialog.close())
on(login_dialog, "click", lambda e: login_dialog.close() if e.target == login_dialog else None)
on(q("#formWho"), "click", on_who_click)


for b in form_dialog.querySelectorAll("[data-close]"):
    on(b, "click", close_form)


def on_form_close(e):
    # 취소하면 찍은 위치만 지우고 신고 모드는 유지 (다시 찍을 수 있게)
    if form_dialog.returnValue != "submitted":
        set_draft(None)


on(form_dialog, "close", on_form_close)
on(form_dialog, "click", lambda e: close_form() if e.target == form_dialog else None)


async def on_photo(e):
    files = form.elements.namedItem("photo").files
    if not files.length:
        return
    try:
        state["photo"] = await shrink_photo(files.item(0))
    except Exception:
        toast("사진을 읽지 못했어요")
        return
    q("#photoPreview").src = state["photo"]
    q("#photoPreview").hidden = False
    q("#photoHint").textContent = "사진 바꾸기"


on(form.elements.namedItem("photo"), "change", on_photo)


def field(name):
    return str(form.elements.namedItem(name).value).strip()


def checked(name):
    el = form.querySelector(f'input[name="{name}"]:checked')
    return el.value if el else None


async def on_submit(e):
    if not state["draft"]:
        return
    # 장난 신고 막기: 너무 빨리 누르면 한 번 더 확인, 글 내용 확인 (공용 모드에서는 서버가 한 번 더 확인)
    if time.time() - state.get("form_opened", 0) < guard.LIMITS["min_fill_sec"]:
        toast(guard.MESSAGES["fast"])
        return
    problem = guard.check_text(field("title"), field("desc"), field("spot"), field("reporter"))
    if problem:
        toast(problem)
        return
    btn = q("#formSubmit")
    btn.disabled = True
    x, y = state["draft"]
    report = {
        "map": state["place"], "x": round(x, 2), "y": round(y, 2), "kind": checked("kind") or "danger",
        "category": checked("category") or "etc", "severity": checked("severity") or "mid",
        "title": field("title")[:60], "spot": field("spot")[:60], "description": field("desc")[:1000],
        "reporter": field("reporter")[:30], "photo": state["photo"],
    }
    try:
        rid = await store.add(report)
    except StoreError as err:
        toast(str(err))
        btn.disabled = False
        return
    btn.disabled = False
    form_dialog.close("submitted")
    state["mine"].add(rid)
    state["selected"] = rid
    set_mode("browse")
    await refresh_reports()
    render_all()
    toast(f"{KINDS[report['kind']][0]} 신고가 접수되었어요. 선생님이 확인할게요!")


on(form, "submit", on_submit, prevent=True)


# ── 신고 보기 (학생은 읽기만) ───────────────────────
detail_dialog = q("#detailDialog")


def open_detail(rid):
    r = next((x for x in state["reports"] if x["id"] == rid), None)
    if not r:
        return
    state["selected"] = rid
    draw_map()
    render_list()
    mine = rid in state["mine"]
    if r["status"] == "done":
        note = "처리가 끝난 신고예요. 문제가 다시 생기면 새로 신고해 주세요."
    elif r["status"] == "rejected":
        note = "선생님이 확인 후 반려한 신고예요. 여전히 위험하다면 자세히 적어서 다시 신고해 주세요."
    elif mine:
        note = "내가 접수한 신고예요. 처리 상태가 바뀌면 여기에서 확인할 수 있어요."
    else:
        note = "이미 신고된 곳이에요. 같은 문제라면 다시 신고하지 않아도 돼요."
    spot = f'<dt>정확한 장소</dt><dd>{esc(r["spot"])}</dd>' if r.get("spot") else ""
    n = r.get("likes") or 0
    liked = rid in state["liked"]
    if mine:
        like = f'<p class="like-line">🙋 나도 봤어요 <b>{n}</b>명</p>' if n else ""
    elif is_open(r) or liked:
        like = (f'<button class="btn like-btn{" is-on" if liked else ""}" type="button" id="btnLike" aria-pressed="{str(liked).lower()}">'
                f'🙋 나도 봤어요 <b>{n}</b></button>'
                f'<p class="hint">같은 문제를 봤다면 다시 신고하지 말고 눌러 주세요. 많이 눌린 신고부터 처리해요.</p>')
    else:
        like = f'<p class="like-line">🙋 나도 봤어요 <b>{n}</b>명</p>' if n else ""
    q("#detailBody").innerHTML = f"""
      <header class="sheet-head">
        <div><p class="eyebrow">{kind_badge(r)} {severity_badge(r["severity"])} · {esc(category_name(r["category"]))}</p>
        <h2>{esc(r["title"])}</h2></div>
        <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
      </header>
      <div class="sheet-body">
        <dl class="detail-grid">
          <dt>상태</dt><dd>{status_badge(r["status"])}</dd>
          <dt>위치</dt><dd>{esc(place_name(r["map"]))}</dd>{spot}
          <dt>신고 일시</dt><dd>{fmt_time(r["created_at"])}</dd>
        </dl>
        <p class="hint">{note}</p>
        {like}
      </div>
      <footer class="sheet-foot"><button class="btn btn-quiet" type="button" data-close>닫기</button></footer>"""
    for b in detail_dialog.querySelectorAll("[data-close]"):
        on(b, "click", lambda e: detail_dialog.close())
    btn = q("#btnLike")
    if btn:
        on(btn, "click", lambda e: asyncio.ensure_future(on_like(rid)))
    if not detail_dialog.open:
        detail_dialog.showModal()


on(detail_dialog, "click", lambda e: detail_dialog.close() if e.target == detail_dialog else None)


# ── 공감 "나도 봤어요" ─────────────────────────────
async def on_like(rid):
    if not store.student:  # 공감도 한 사람이 한 번만 누르게 로그인한다
        state["like_after"] = rid
        detail_dialog.close()
        open_login("like")
        return
    await do_like(rid)


async def do_like(rid):
    btn = q("#btnLike")
    if btn:
        btn.disabled = True
    try:
        res = await store.toggle_like(rid)
    except StoreError as e:
        toast(str(e))
        if btn:
            btn.disabled = False
        return
    for r in state["reports"]:
        if r["id"] == rid:
            r["likes"] = res["likes"]
    (state["liked"].add if res["liked"] else state["liked"].discard)(rid)
    toast("공감했어요. 선생님이 더 빨리 확인할게요!" if res["liked"] else "공감을 취소했어요")
    render_list()
    open_detail(rid)


def focus_report(r):
    def do_focus():
        viewer.focus(r["x"], r["y"] - 6, min(viewer.size[0], 220))
        draw_map()
        render_list()
        open_detail(r["id"])

    state["selected"] = r["id"]
    if r["map"] != state["loaded"]:
        window.history.replaceState(None, "", window.location.pathname if r["map"] == SITE_ID else f"#{r['map']}")
        asyncio.ensure_future(navigate(r["map"], do_focus))
    else:
        do_focus()


def on_list_click(e):
    item = closest(e, ".report-item")
    if item:
        r = next((x for x in state["reports"] if x["id"] == item.dataset.id), None)
        if r:
            focus_report(r)


on(q("#reportList"), "click", on_list_click)


# ── 패널 · 층 버튼 · 도구 ──────────────────────────
def on_doc_click(e):
    fl = closest(e, "[data-floor]")
    if fl:
        go(fl.dataset.floor)
        return
    card = closest(e, ".bld-card")
    if card:
        go(card.dataset.building)


on(window.document, "click", on_doc_click)


def hot(e):
    card = closest(e, ".bld-card")
    bid = card.dataset.building if card else None
    for g in qa(".bld"):
        g.classList.toggle("is-hot", g.dataset.building == bid)


on(q("#ctx"), "pointerover", hot)
on(q("#ctx"), "pointerleave", lambda e: [g.classList.remove("is-hot") for g in qa(".bld")])

on(q("#zoomIn"), "click", lambda e: viewer.zoom_by(1.5))
on(q("#zoomOut"), "click", lambda e: viewer.zoom_by(1 / 1.5))
on(q("#zoomFit"), "click", lambda e: viewer.fit())

on(window, "hashchange", lambda e: asyncio.ensure_future(navigate(parse_hash())))


# ── 검색 (예: 2-1, 보건실, 409) ─────────────────────
search_input = q("#searchInput")
search_list = q("#searchResults")
search_state = {"items": [], "active": 0}


def show_results(items):
    search_state["items"] = items
    search_state["active"] = 0
    if not search_input.value.strip():
        search_list.hidden = True
        return
    if not items:
        search_list.innerHTML = '<li class="empty">찾는 곳이 없어요. 예) 2-1, 보건실, 409</li>'
    else:
        search_list.innerHTML = "".join(
            f'<li role="option" data-i="{i}" aria-selected="{str(i == 0).lower()}">'
            f'<strong>{esc(r["title"])}</strong><small>{esc(r["sub"])}</small></li>'
            for i, r in enumerate(items))
    search_list.hidden = False


def mark_active():
    for li in qa("#searchResults li[data-i]"):
        li.setAttribute("aria-selected", str(int(li.dataset.i) == search_state["active"]).lower())


def jump_to(r):
    search_list.hidden = True
    search_input.blur()

    def do_focus():
        if r["x"] is not None:
            state["hit"] = (r["x"], r["y"])
            viewer.focus(r["x"], r["y"], min(viewer.size[0], 260))
            viewer.draw_hit(state["hit"])
            toast(f"{r['title']} · {r['sub']}")

    if state["mode"] == "report":
        set_mode("browse")
    if r["floor"] != state["loaded"]:
        window.history.replaceState(None, "", f"#{r['floor']}")
        asyncio.ensure_future(navigate(r["floor"], do_focus))
    else:
        state["place"] = r["floor"]
        do_focus()


def on_search_key(e):
    items = search_state["items"]
    if e.key == "Enter":
        e.preventDefault()
        if not items:
            show_results(search(search_input.value))
            items = search_state["items"]
        if items:
            jump_to(items[search_state["active"]])
    elif e.key in ("ArrowDown", "ArrowUp") and items:
        e.preventDefault()
        step = 1 if e.key == "ArrowDown" else -1
        search_state["active"] = (search_state["active"] + step) % len(items)
        mark_active()
    elif e.key == "Escape":
        search_input.value = ""
        search_list.hidden = True


def on_result_click(e):
    li = closest(e, "li[data-i]")
    if li:
        jump_to(search_state["items"][int(li.dataset.i)])


on(search_input, "input", lambda e: show_results(search(search_input.value)))
on(search_input, "keydown", on_search_key)
on(search_input, "focus", lambda e: show_results(search(search_input.value)))
on(search_list, "pointerdown", lambda e: e.preventDefault())  # 누르는 동안 입력창 포커스 유지
on(search_list, "click", on_result_click)
_hide_results = create_proxy(lambda: setattr(search_list, "hidden", True))  # 한 번만 만들어 계속 쓴다
on(search_input, "blur", lambda e: window.setTimeout(_hide_results, 150))


# ── 시작 ─────────────────────────────────────────
q("#demoNote").hidden = SHARED
pending = await finish_google_return()
await refresh_reports()
await navigate(parse_hash())
if pending and pending.get("like") and store.student:
    await do_like(pending["like"])
elif pending and pending.get("draft") and STUDENT_LOGIN and store.student:
    set_mode("report")
    set_draft(tuple(pending["draft"]))
    open_form()
q("#btnReport").disabled = False
hide_loading()
