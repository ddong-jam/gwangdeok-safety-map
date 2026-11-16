# 학생용 화면: 캠퍼스 → 건물 → 층 평면도에서 위험한 곳을 찍어 신고한다.
# 화면 틀(pages.py)과 꾸미기(theme.py)를 먼저 그린다 — 아래 코드가 그 요소들을 찾기 때문
import pages  # 화면 틀(HTML)을 만드는 파일
import theme  # 화면 꾸미기(CSS)를 넣는 파일

theme.apply()  # 꾸미기를 화면에 넣는다
pages.mount("student")  # 학생용 화면 틀을 그린다

import asyncio  # 기다렸다 이어서 하는 함수(async)를 실행하는 도구
import json  # 값을 글자(JSON)로 바꾸는 도구 — 로그인하러 갈 때 보던 위치를 저장한다
import time  # 지금 시각(초) — 신고 창을 연 뒤 지난 시간을 잰다

from js import window  # 브라우저 창 (주소, 저장 공간 등)
from pyodide.ffi import create_proxy  # 파이썬 함수를 브라우저가 부를 수 있게 감싸는 도구

from campus import (BUILDING_BY_ID, BUILDINGS, CATEGORIES, FLOOR_INDEX, KINDS, LINKS, SEVERITIES, SITE_ID, building_at,  # 학교 건물·층·신고 분류 데이터와
                    kind_of, link_label, place_name, plan_of, search)  # 도우미 함수들
from common import (SEVERITY_DOTS, category_name, closest, esc, fmt_time, hide_loading, is_open, kind_badge, on, q, qa,  # 화면 조작·표시 도구들
                    shrink_photo, status_badge, severity_badge, time_ago, toast)  # 사진 줄이기·배지·시간·알림
import guard  # 장난 신고 검사 규칙
from store import SCHOOL_DOMAIN, SHARED, STUDENT_LOGIN, StoreError, store  # 신고 저장소와 설정
from viewer import PlanViewer  # 도면 뷰어

state = {  # 화면의 지금 상태를 모아 둔 사전
    "place": SITE_ID,     # 지금 보는 지도 ("site" 또는 층 id, 예: "b2-1f")
    "loaded": None,  # 지금 화면에 불러온 도면
    "mode": "browse",     # "browse" | "report"
    "draft": None,        # 찍은 위치 (x, y)
    "selected": None,  # 선택한 신고 번호
    "reports": [],        # 학생에게 보여도 되는 신고 전체
    "mine": set(),        # 이 화면에서 내가 접수한 신고
    "photo": None,  # 신고에 붙일 사진 (줄인 것)
    "hit": None,          # 검색으로 찾은 곳 (x, y)
    "liked": set(),       # 내가 공감한 신고
    "like_after": None,   # 로그인을 마치면 공감할 신고
}  # 상태 사전 끝
viewer = PlanViewer(q("#map"))  # 화면의 지도 영역으로 도면 뷰어를 만든다


def plan_url(place):  # 층의 도면 파일 주소
    return plan_of(place)[0]  # (주소, 범위) 중 주소만


def open_count(pred):  # 조건에 맞는 처리 전 신고 수를 세는 함수
    return sum(1 for r in state["reports"] if is_open(r) and pred(r))  # 처리 전이고 조건에 맞는 것만 센다


def floors_of(b):  # 건물의 층 id 들
    return {f.id for f in b.floors}  # 층 id 모음


async def refresh_reports():  # 서버에서 신고 목록을 새로 받아오는 함수
    try:  # 받아 본다
        state["reports"] = await store.list_public()  # 공개 신고 목록
        state["liked"] = await store.my_likes() if store.student else set()  # 로그인했으면 내가 공감한 신고들
    except StoreError as e:  # 실패하면
        toast(str(e))  # 안내를 띄운다


# ── 주소(#b2-1f)로 위치 기억 ─────────────────────────
def parse_hash():  # 주소 # 뒤를 읽어 보여줄 곳을 정하는 함수
    h = window.decodeURIComponent(window.location.hash.lstrip("#/"))  # # 뒤의 글자
    if not h:  # 없으면
        return SITE_ID  # 캠퍼스 배치도
    if h in FLOOR_INDEX:  # 층 id 면
        return h  # 그 층
    b = BUILDING_BY_ID.get(h)  # 건물 id 인지 확인
    return b.default_floor.id if b else SITE_ID  # 건물이면 그 건물 1층, 아니면 캠퍼스


def go(place):  # 다른 곳으로 이동하는 함수 (주소를 바꿔서)
    target = "" if place == SITE_ID else f"#{place}"  # 새 주소 # 부분
    if window.location.hash == target or (not target and not window.location.hash):  # 주소가 이미 같으면 (주소 변화 이벤트가 안 생긴다)
        asyncio.ensure_future(navigate(place))  # 직접 이동한다
    else:  # 다르면
        window.location.hash = target  # 주소를 바꾼다 (바뀌면 이동 함수가 불린다)


async def navigate(place, after=None):  # 실제로 그 곳의 화면을 보여주는 함수
    changed = place != state["loaded"]  # 다른 도면으로 바뀌는지
    state["place"] = place  # 지금 보는 곳을 바꾼다
    if changed:  # 도면이 바뀌면
        state["hit"] = None  # 검색 표시를 지운다
    if state["mode"] == "report":  # 신고 모드였으면
        set_draft(None)  # 찍은 자리를 지우고
        set_mode("report")  # 안내 문구를 새 곳에 맞게 다시 쓴다
    render_chrome()  # 위쪽 길·층 버튼·옆 패널을 그린다
    render_list()  # 신고 목록을 그린다
    if changed:  # 도면이 바뀌면
        state["loaded"] = place  # 불러온 도면을 기록한다
        try:  # 도면을 불러와 본다
            if not await viewer.load(plan_url(place), locked=False, crop=plan_of(place)[1]):  # 캠퍼스 배치도도 확대·이동 (v2.3.1)
                return  # 그 사이에 다른 곳을 눌렀으면 그만둔다
        except Exception as e:  # 실패하면
            toast(str(e))  # 안내
            return  # 그만둔다
        draw_map()  # 도면 위에 핀·버튼을 그린다
    if after:  # 다 그린 뒤 할 일이 있으면
        after()  # 한다


# ── 화면 그리기 ───────────────────────────────────
def render_chrome():  # 위쪽 길 표시·층 버튼·옆 패널을 그리는 함수
    place = state["place"]  # 지금 보는 곳
    hit = FLOOR_INDEX.get(place)  # 층이면 (건물, 층)
    b, fl = hit if hit else (None, None)  # 건물과 층 (캠퍼스면 없음)

    q("#crumbs").innerHTML = (  # 위쪽 "캠퍼스 › 건물" 길 표시
        '<span class="here">광덕중·고 캠퍼스</span>' if not b else  # 캠퍼스면 이것만
        f'<a href="#">캠퍼스</a><span class="sep">›</span><span class="here">{esc(b.name)}</span>')  # 건물이면 캠퍼스 링크 + 건물 이름

    if b:  # 건물 안이면
        btns = []  # 층 버튼들
        for f in b.floors:  # 층마다
            n = open_count(lambda r, f=f: r["map"] == f.id)  # 그 층의 처리 전 신고 수
            dot = f'<span class="dot">{n}</span>' if n else ""  # 신고가 있으면 빨간 숫자
            btns.append(f'<button role="tab" data-floor="{f.id}" aria-selected="{str(f.id == place).lower()}" '  # 층 버튼 (지금 층이면 선택 표시)
                        f'title="{esc(f.name)}">{esc(f.label)}{dot}</button>')  # 버튼 글자 = 1F 등
        q("#floorbar").innerHTML = "".join(btns)  # 오른쪽 층 버튼 막대에 넣는다
    else:  # 캠퍼스면
        q("#floorbar").innerHTML = ""  # 층 버튼 없음

    if not b:  # 캠퍼스면 옆 패널에 건물 카드들
        cards = []  # 건물 카드들
        for bb in BUILDINGS:  # 건물마다
            n = open_count(lambda r, bb=bb: r["map"] in floors_of(bb))  # 그 건물의 처리 전 신고 수
            sub = " · ".join(x for x in (bb.dong, bb.sub) if x)  # "2동 · 고등학교 교사" 같은 설명
            cards.append(f'<button class="bld-card" style="--c:{bb.color}" data-building="{bb.id}">'  # 건물 색 카드
                         f'<strong>{esc(bb.name)}</strong><small>{esc(sub)}</small>'  # 이름과 설명
                         f'{f"<span class=n>{n}</span>" if n else ""}</button>')  # 신고가 있으면 숫자
        q("#ctx").innerHTML = (  # 옆 패널 내용
            '<h1>캠퍼스 평면도</h1><p class="sub">건물을 누르면 층별 평면도가 열려요.</p>'  # 제목과 설명
            f'<div class="bld-grid">{"".join(cards)}</div>'  # 건물 카드 모음
            '<p class="hint">운동장·주차장 같은 야외의 위험·불편은 지도에서 건물 밖 그 자리를 누르면 바로 신고돼요.</p>')  # 야외 신고 안내
    else:  # 건물 안이면 옆 패널에 층 정보
        area = f'<span class="tag">바닥면적 {fl.area:,.2f}㎡</span>' if fl.area else ""  # 바닥면적 표시 (있으면)
        tabs = "".join(f'<button role="tab" data-floor="{f.id}" aria-selected="{str(f.id == place).lower()}">{esc(f.name)}</button>'  # 층 이름 버튼들
                       for f in b.floors)  # 층마다
        sub = " · ".join(x for x in (b.sub, b.dong) if x)  # 건물 설명
        q("#ctx").innerHTML = (  # 옆 패널 내용
            '<a class="back-btn" href="#"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>캠퍼스로 돌아가기</a>'  # 돌아가기 버튼
            f'<h1>{esc(b.name)} <span style="color:var(--muted);font-weight:600">{esc(fl.name)}</span></h1>'  # 건물 이름 + 층 이름
            f'<p class="sub">{esc(sub)}</p>'  # 건물 설명
            f'<div class="meta"><span class="tag color" style="--c:{b.color}">{esc(b.code)}</span>{area}'  # 도면 기호와 바닥면적
            f'<span class="tag">{len(b.floors)}개 층 도면</span></div>'  # 층 수
            f'<div class="floor-list" role="tablist">{tabs}</div>'  # 층 버튼들
            '<p class="hint">도면에서 <b>위험하거나 불편한 곳</b>을 누르면 그 자리에 바로 신고할 수 있어요.</p>')  # 신고 안내


def draw_map():  # 도면 위에 건물·버튼·핀을 그리는 함수
    here = [r for r in state["reports"] if r["map"] == state["place"]]  # 지금 보는 곳의 신고들
    if state["place"] == SITE_ID:  # 캠퍼스면
        counts = {b.id: open_count(lambda r, b=b: r["map"] in floors_of(b)) for b in BUILDINGS}  # 건물별 처리 전 신고 수
        viewer.draw_buildings(counts)  # 건물과 이름표를 그린다
    else:  # 층이면
        viewer.draw_links([(x, y, t, link_label(t)) for x, y, t in LINKS.get(state["place"], [])])  # 연결복도 버튼을 그린다
    viewer.draw_hit(state["hit"])  # 검색 표시
    viewer.draw_pins(here, state["selected"])  # 신고 핀
    viewer.draw_draft(state["draft"])  # 찍은 자리의 새 핀


def render_list():  # 옆 패널 아래 신고 목록을 그리는 함수
    allr = state["reports"]  # 모든 신고
    opened = [r for r in allr if is_open(r)]  # 처리 전 신고
    q("#stats").innerHTML = (f'<span>처리 전<b>{len(opened)}</b></span>'  # 처리 전 수
                             f'<span class="urgent">긴급<b>{sum(r["severity"] == "urgent" for r in opened)}</b></span>'  # 긴급 수
                             f'<span>완료<b>{len(allr) - len(opened)}</b></span>')  # 완료 수
    place = state["place"]  # 지금 보는 곳
    items = allr if place == SITE_ID else [r for r in allr if r["map"] == place]  # 캠퍼스면 전부, 층이면 그 층 것만
    q("#listTitle").textContent = "전체 신고" if place == SITE_ID else "이 층의 신고"  # 목록 제목
    if not items:  # 신고가 없으면
        q("#reportList").innerHTML = ('<li class="empty">아직 신고가 없어요.<br/>위험하거나 불편한 곳을 보면 '  # 빈 목록 안내
                                      '도면에서 그 자리를 눌러주세요.</li>')  # 안내 이어서
        return  # 끝
    rows = []  # 목록 줄들
    for r in items[:60]:  # 60개까지만
        dot = "✅" if not is_open(r) else "🟣" if kind_of(r) == "incon" else SEVERITY_DOTS.get(r["severity"], "🟡")  # 완료 체크 / 불편 보라 / 위험도 색
        sel = " is-selected" if r["id"] == state["selected"] else ""  # 선택한 신고면 강조
        spot = f' · {esc(r["spot"])}' if r.get("spot") else ""  # 정확한 장소 (있으면)
        rows.append(f'<li><button class="report-item{sel}" data-id="{r["id"]}" type="button">'  # 누를 수 있는 목록 줄
                    f'<span class="sev-dot">{dot}</span><span class="t">{kind_badge(r)} {esc(r["title"])}{like_badge(r)}</span>{status_badge(r["status"])}'  # 표시·종류·제목·공감 수·상태
                    f'<span class="w">{esc(place_name(r["map"]))}{spot} · {time_ago(r["created_at"])}</span></button></li>')  # 위치·장소·지난 시간
    q("#reportList").innerHTML = "".join(rows)  # 목록에 넣는다


def like_badge(r):  # 공감 수 표시를 만드는 함수
    n = r.get("likes") or 0  # 공감 수
    return f' <span class="like-count" title="나도 봤어요 {n}명">🙋{n}</span>' if n else ""  # 1 이상이면 🙋숫자


def render_all():  # 화면 전체를 다시 그리는 함수
    render_chrome()  # 길·층 버튼·옆 패널
    render_list()  # 신고 목록
    draw_map()  # 도면 위 표시


# ── 지도 누르기 ───────────────────────────────────
def on_tap(x, y, target):  # 지도를 눌렀을 때
    pin = target.closest(".pin") if hasattr(target, "closest") else None  # 핀을 눌렀는지
    link = target.closest(".link") if hasattr(target, "closest") else None  # 연결복도 버튼을 눌렀는지
    if state["hit"]:  # 검색 표시는 지도를 한 번 누르면 지운다
        state["hit"] = None  # 표시 위치를 지운다
        viewer.draw_hit(None)  # 화면에서도 지운다
    if link and state["mode"] != "report":  # 연결 버튼을 눌렀으면 (신고 모드가 아닐 때)
        go(link.dataset.target)  # 이어진 층으로 간다
        return  # 끝
    if pin and state["mode"] != "report":  # 핀을 눌렀으면
        open_detail(pin.dataset.id)  # 그 신고를 자세히 보여준다
        return  # 끝
    if state["place"] == SITE_ID and state["mode"] != "report":  # 캠퍼스에서 눌렀으면
        b = building_at(x, y)  # 누른 곳의 건물
        if b:  # 건물이면
            go(b.id)  # 그 건물로 간다
            return  # 끝
    # 도면 안을 누르면 그 자리에 바로 위험/불편 신고 (배치도에서는 건물 밖 = 야외)
    # 도면 둘레의 흰 여백을 누르면 신고 창을 열지 않는다
    w, h = viewer.size  # 도면 크기
    if not (0 <= x <= w and 0 <= y <= h) or not viewer.on_drawing(x, y, target):  # 도면 밖이거나 여백이면
        if state["mode"] == "report":  # 신고 모드면
            toast("도면 안쪽을 눌러주세요")  # 안내
        return  # 신고 창을 열지 않는다
    set_draft((x, y))  # 누른 자리를 기억하고 새 핀을 그린다
    open_form()  # 신고 창을 연다


viewer.on_tap = on_tap  # 지도를 누르면 위 함수가 불리게 한다
viewer.on_view_change = viewer.scale_markers  # 확대·이동하면 핀 크기를 다시 맞춘다


# ── 신고 모드 ─────────────────────────────────────
def set_mode(mode):  # 보기 모드 / 신고 모드를 바꾸는 함수
    state["mode"] = mode  # 모드 저장
    reporting = mode == "report"  # 신고 모드인지
    window.document.body.classList.toggle("reporting", reporting)  # 화면 꾸미기 표시 (신고 모드 색)
    q("#btnReport").setAttribute("aria-pressed", str(reporting).lower())  # 버튼 눌림 상태
    q("#btnReport span").textContent = "신고 취소" if reporting else "위험/불편 신고"  # 버튼 글자
    q("#modeBanner").hidden = not reporting  # 위쪽 안내 띠를 보이거나 숨긴다
    q("#modeText").textContent = (  # 안내 띠 글자
        "지도에서 위험하거나 불편한 곳을 눌러주세요 (건물 안은 건물을 먼저 선택)" if state["place"] == SITE_ID  # 캠퍼스일 때
        else f"{place_name(state['place'])} 도면에서 위험하거나 불편한 곳을 눌러주세요")  # 층일 때
    if not reporting:  # 보기 모드로 돌아가면
        set_draft(None)  # 찍은 자리를 지운다


def set_draft(point):  # 찍은 자리를 정하는 함수
    state["draft"] = point  # 저장
    viewer.draw_draft(point)  # 새 핀을 그린다 (None 이면 지운다)


on(q("#btnReport"), "click", lambda e: set_mode("browse" if state["mode"] == "report" else "report"))  # 신고 버튼: 모드를 바꾼다
on(q("#modeCancel"), "click", lambda e: set_mode("browse"))  # 안내 띠의 취소 버튼: 보기 모드로


def on_key(e):  # 키보드를 눌렀을 때
    if e.key == "Escape" and state["mode"] == "report" and not q("dialog[open]"):  # Esc 이고 신고 모드이고 열린 창이 없으면
        set_mode("browse")  # 보기 모드로


on(window.document, "keydown", on_key)  # 키보드 이벤트 연결


# ── 신고서 ───────────────────────────────────────
form = q("#reportForm")  # 신고 입력 양식
form_dialog = q("#formDialog")  # 신고 창

q("#catChips").innerHTML = "".join(  # 유형 고르기 버튼들을 만든다
    f'<label><input type="radio" name="category" value="{k}" {"checked" if i == 0 else ""}/><span>{esc(v)}</span></label>'  # 유형 버튼 (첫 번째가 기본)
    for i, (k, v) in enumerate(CATEGORIES.items()))  # 유형마다
q("#sevChips").innerHTML = "".join(  # 위험도 고르기 버튼들을 만든다
    f'<label style="--c:{c}"><input type="radio" name="severity" value="{k}" {"checked" if k == "mid" else ""}/><span>{esc(n)}</span></label>'  # 위험도 버튼 (보통이 기본)
    for k, (n, c) in SEVERITIES.items())  # 위험도마다


SEV_LEGEND = {"danger": "얼마나 위험한가요?", "incon": "얼마나 급한가요?"}  # 종류별 위험도 질문


def on_kind_change(e=None):  # 위험/불편 종류를 바꿨을 때
    k = checked("kind") or "danger"  # 고른 종류
    q("#sevLegend").textContent = SEV_LEGEND[k]  # 위험도 질문을 바꾼다
    q("#formSubmit").textContent = f"{KINDS[k][0]} 신고 접수"  # 접수 버튼 글자를 바꾼다
    form_dialog.dataset.kind = k  # 창 꾸미기용 표시


on(q("#kindChips"), "change", on_kind_change)  # 종류 버튼 변경 이벤트 연결


def open_form():  # 신고 창을 여는 함수
    if STUDENT_LOGIN and not store.student:  # 로그인이 필요한데 안 했으면
        open_login()  # 신고할 때만 로그인 (찍은 자리는 기억해 둔다)
        return  # 창은 아직 안 연다
    show_who()  # 누가 로그인했는지 보여준다
    form.reset()  # 입력 칸을 비운다
    on_kind_change()  # 종류에 맞게 글자를 맞춘다
    state["photo"] = None  # 사진을 비운다
    q("#photoPreview").hidden = True  # 사진 미리보기를 숨긴다
    q("#photoHint").textContent = "사진 추가 · 촬영"  # 사진 버튼 글자
    q("#formWhere").textContent = f"📍 {place_name(state['place'])}"  # 신고 위치 표시
    state["form_opened"] = time.time()  # 창을 연 시각 (너무 빨리 접수하는지 보려고)
    form_dialog.showModal()  # 창을 연다


def close_form(e=None):  # 신고 창을 닫는 함수
    form_dialog.close("cancel")  # 취소로 닫는다


# ── 학생 로그인 (신고할 때만) ──────────────────────
login_dialog = q("#loginDialog")  # 로그인 창
PENDING_KEY = "kd-safety-pending-report"  # 구글에 다녀오는 동안 보던 위치를 저장하는 이름


def show_who():  # 신고 창 위에 로그인한 계정을 보여주는 함수
    st = store.student if STUDENT_LOGIN else None  # 로그인한 학생
    who = q("#formWho")  # 계정 표시 칸
    who.hidden = not st  # 로그인 안 했으면 숨긴다
    if st:  # 로그인했으면
        who.innerHTML = (f'👤 {esc(st.get("name") or st["email"])} <small>{esc(st["email"])}</small> '  # 이름과 이메일
                         f'<button type="button" class="link-btn" id="btnStudentLogout">로그아웃</button>')  # 로그아웃 버튼
    q("#noticeRecord").textContent = ("신고하면 내 구글 계정과 시간이 함께 기록돼요. (선생님만 볼 수 있어요)" if st  # 로그인했을 때 기록 안내
                                      else "신고하면 시간과 이 기기 정보가 함께 기록돼요. (익명이어도 기록돼요)")  # 로그인 안 했을 때 기록 안내


def open_login(purpose="신고"):  # 로그인 창을 여는 함수
    q("#loginPurpose").textContent = "나도 봤어요" if purpose == "like" else "위험/불편 신고"  # 왜 로그인하는지 (공감 / 신고)
    q("#demoNameField").hidden = SHARED  # 체험 모드에서만 이름 칸을 보여준다
    q("#loginTitle").textContent = "학교 구글 계정으로 로그인" if SCHOOL_DOMAIN else "구글 계정으로 로그인"  # 창 제목
    dom = q("#loginDomain")  # 학교 계정 안내 칸
    dom.hidden = not SCHOOL_DOMAIN  # 학교 계정 제한이 없으면 숨긴다
    dom.innerHTML = f"<b>@{esc(SCHOOL_DOMAIN)}</b> 학교 계정만 신고할 수 있어요." if SCHOOL_DOMAIN else ""  # 안내 글
    login_dialog.showModal()  # 창을 연다


def on_login_close(e):  # 로그인 창이 닫혔을 때
    if not store.student:  # 로그인하지 않고 닫았으면
        state["like_after"] = None  # 공감 예약을 취소한다
    if not (STUDENT_LOGIN and store.student) and not form_dialog.open:  # 로그인 안 했고 신고 창도 안 열렸으면
        set_draft(None)  # 찍은 자리를 지운다


async def on_google(e):  # 구글 로그인 버튼을 눌렀을 때
    if not SHARED:  # 체험 모드: 구글 대신 이름만
        name = str(q("#demoName").value).strip() or "체험 학생"  # 적은 이름 (없으면 "체험 학생")
        await store.student_login(name)  # 체험 로그인
        rid, state["like_after"] = state["like_after"], None  # 공감 예약을 꺼내고 비운다
        login_dialog.close()  # 로그인 창을 닫는다
        if rid:  # 공감하려고 로그인한 거면
            await refresh_reports()  # 목록을 새로 받고
            await do_like(rid)  # 공감한다
        else:  # 신고하려고 로그인한 거면
            open_form()  # 신고 창을 연다
        return  # 끝
    # 구글에 다녀오면 페이지가 새로 열리니, 보던 층과 찍은 자리를 기억해 둔다
    window.sessionStorage.setItem(PENDING_KEY, json.dumps({"place": state["place"], "draft": state["draft"],  # 보던 층, 찍은 자리,
                                                           "like": state["like_after"]}))  # 공감할 신고를 저장
    back = window.location.origin + window.location.pathname  # 로그인 후 돌아올 주소 (이 페이지)
    window.location.href = store.google_url(back)  # 구글 로그인 화면으로 간다


async def finish_google_return():  # 구글에서 돌아왔을 때 마무리하는 함수
    """구글 로그인에서 돌아왔을 때: 로그인을 마치고, 보던 층으로 가서 신고 창을 다시 연다."""  # 이 함수가 하는 일을 적은 설명글
    h = str(window.location.hash)  # 주소 # 뒤
    if "access_token=" not in h and "error=" not in h:  # 구글에서 돌아온 게 아니면
        return None  # 할 일 없음
    err = await store.finish_google(h)  # 로그인을 마친다 (오류가 있으면 메시지)
    try:  # 저장해 둔 위치를 읽어 본다
        pending = json.loads(window.sessionStorage.getItem(PENDING_KEY) or "{}")  # 보던 층·찍은 자리·공감할 신고
    except Exception:  # 망가졌으면
        pending = {}  # 없음
    window.sessionStorage.removeItem(PENDING_KEY)  # 다 썼으니 지운다
    place = pending.get("place") or SITE_ID  # 보던 곳
    window.history.replaceState(None, "", window.location.pathname + ("" if place == SITE_ID else f"#{place}"))  # 주소에서 토큰을 지우고 보던 곳으로 바꾼다
    if err:  # 로그인에 실패했으면
        toast(err)  # 안내
        return None  # 끝
    toast("로그인했어요")  # 성공 안내
    return pending  # 저장해 둔 정보를 돌려준다


def on_who_click(e):  # 계정 표시 칸을 눌렀을 때
    if closest(e, "#btnStudentLogout"):  # 로그아웃 버튼이면
        store.student_logout()  # 로그아웃
        close_form()  # 신고 창을 닫는다
        toast("로그아웃했어요")  # 안내


on(q("#btnGoogle"), "click", on_google)  # 구글 버튼 연결
on(login_dialog, "close", on_login_close)  # 로그인 창 닫힘 연결
on(login_dialog.querySelector("[data-close]"), "click", lambda e: login_dialog.close())  # 로그인 창 X 버튼
on(login_dialog, "click", lambda e: login_dialog.close() if e.target == login_dialog else None)  # 창 바깥 어두운 곳을 누르면 닫기
on(q("#formWho"), "click", on_who_click)  # 계정 표시 칸 연결


for b in form_dialog.querySelectorAll("[data-close]"):  # 신고 창의 닫기 버튼들
    on(b, "click", close_form)  # 누르면 창을 닫는다


def on_form_close(e):  # 신고 창이 닫혔을 때
    # 취소하면 찍은 위치만 지우고 신고 모드는 유지 (다시 찍을 수 있게)
    if form_dialog.returnValue != "submitted":  # 접수가 아니라 취소로 닫혔으면
        set_draft(None)  # 찍은 자리를 지운다


on(form_dialog, "close", on_form_close)  # 신고 창 닫힘 연결
on(form_dialog, "click", lambda e: close_form() if e.target == form_dialog else None)  # 창 바깥을 누르면 닫기


async def on_photo(e):  # 사진을 골랐을 때
    files = form.elements.namedItem("photo").files  # 고른 파일들
    if not files.length:  # 없으면
        return  # 끝
    try:  # 사진을 줄여 본다
        state["photo"] = await shrink_photo(files.item(0))  # 첫 사진을 1024px 로 줄인다
    except Exception:  # 실패하면
        toast("사진을 읽지 못했어요")  # 안내
        return  # 끝
    q("#photoPreview").src = state["photo"]  # 미리보기에 넣는다
    q("#photoPreview").hidden = False  # 미리보기를 보여준다
    q("#photoHint").textContent = "사진 바꾸기"  # 버튼 글자


on(form.elements.namedItem("photo"), "change", on_photo)  # 사진 선택 이벤트 연결


def field(name):  # 입력 칸의 글자를 읽는 함수
    return str(form.elements.namedItem(name).value).strip()  # 앞뒤 공백을 지운 글자


def checked(name):  # 고른 버튼의 값을 읽는 함수
    el = form.querySelector(f'input[name="{name}"]:checked')  # 체크된 버튼
    return el.value if el else None  # 그 값 (없으면 None)


async def on_submit(e):  # 신고 접수 버튼을 눌렀을 때
    if not state["draft"]:  # 찍은 자리가 없으면
        return  # 아무것도 안 한다
    # 장난 신고 막기: 너무 빨리 누르면 한 번 더 확인, 글 내용 확인 (공용 모드에서는 서버가 한 번 더 확인)
    if time.time() - state.get("form_opened", 0) < guard.LIMITS["min_fill_sec"]:  # 창을 연 지 4초가 안 됐으면
        toast(guard.MESSAGES["fast"])  # 다시 확인하라는 안내
        return  # 접수하지 않는다
    problem = guard.check_text(field("title"), field("desc"), field("spot"), field("reporter"))  # 글 내용 검사
    if problem:  # 문제가 있으면
        toast(problem)  # 안내
        return  # 접수하지 않는다
    btn = q("#formSubmit")  # 접수 버튼
    btn.disabled = True  # 두 번 눌리지 않게 잠근다
    x, y = state["draft"]  # 찍은 자리
    report = {  # 보낼 신고 내용
        "map": state["place"], "x": round(x, 2), "y": round(y, 2), "kind": checked("kind") or "danger",  # 층·좌표(소수 둘째 자리)·종류
        "category": checked("category") or "etc", "severity": checked("severity") or "mid",  # 유형·위험도
        "title": field("title")[:60], "spot": field("spot")[:60], "description": field("desc")[:1000],  # 제목(60자)·장소(60자)·내용(1000자)
        "reporter": field("reporter")[:30], "photo": state["photo"],  # 이름(30자)·사진
    }  # 신고 내용 끝
    try:  # 저장해 본다
        rid = await store.add(report)  # 신고를 저장하고 번호를 받는다
    except StoreError as err:  # 막혔으면 (장난 신고 규칙 등)
        toast(str(err))  # 이유를 안내
        btn.disabled = False  # 버튼을 다시 풀어 준다
        return  # 끝
    btn.disabled = False  # 버튼을 풀어 준다
    form_dialog.close("submitted")  # 접수로 창을 닫는다
    state["mine"].add(rid)  # 내 신고로 기억한다
    state["selected"] = rid  # 방금 신고를 선택한다
    set_mode("browse")  # 보기 모드로
    await refresh_reports()  # 목록을 새로 받는다
    render_all()  # 화면을 다시 그린다
    toast(f"{KINDS[report['kind']][0]} 신고가 접수되었어요. 선생님이 확인할게요!")  # 접수 완료 안내


on(form, "submit", on_submit, prevent=True)  # 접수 이벤트 연결 (페이지 새로고침은 막는다)


# ── 신고 보기 (학생은 읽기만) ───────────────────────
detail_dialog = q("#detailDialog")  # 신고 자세히 보기 창


def open_detail(rid):  # 신고 하나를 자세히 보여주는 함수
    r = next((x for x in state["reports"] if x["id"] == rid), None)  # 그 신고를 찾는다
    if not r:  # 없으면
        return  # 끝
    state["selected"] = rid  # 선택한 신고로
    draw_map()  # 지도에서 강조
    render_list()  # 목록에서 강조
    mine = rid in state["mine"]  # 내가 한 신고인지
    if r["status"] == "done":  # 처리 완료면
        note = "처리가 끝난 신고예요. 문제가 다시 생기면 새로 신고해 주세요."  # 안내
    elif r["status"] == "rejected":  # 반려면
        note = "선생님이 확인 후 반려한 신고예요. 여전히 위험하다면 자세히 적어서 다시 신고해 주세요."  # 안내
    elif mine:  # 내 신고면
        note = "내가 접수한 신고예요. 처리 상태가 바뀌면 여기에서 확인할 수 있어요."  # 안내
    else:  # 다른 사람 신고면
        note = "이미 신고된 곳이에요. 같은 문제라면 다시 신고하지 않아도 돼요."  # 안내
    spot = f'<dt>정확한 장소</dt><dd>{esc(r["spot"])}</dd>' if r.get("spot") else ""  # 정확한 장소 줄 (있으면)
    n = r.get("likes") or 0  # 공감 수
    liked = rid in state["liked"]  # 내가 공감했는지
    if mine:  # 내 신고면 공감 버튼 없이
        like = f'<p class="like-line">🙋 나도 봤어요 <b>{n}</b>명</p>' if n else ""  # 공감 수만 보여준다
    elif is_open(r) or liked:  # 처리 전이거나 이미 공감했으면 (취소할 수 있게)
        like = (f'<button class="btn like-btn{" is-on" if liked else ""}" type="button" id="btnLike" aria-pressed="{str(liked).lower()}">'  # 공감 버튼 (눌렀으면 색칠)
                f'🙋 나도 봤어요 <b>{n}</b></button>'  # 버튼 글자 + 공감 수
                f'<p class="hint">같은 문제를 봤다면 다시 신고하지 말고 눌러 주세요. 많이 눌린 신고부터 처리해요.</p>')  # 안내
    else:  # 처리가 끝난 남의 신고면
        like = f'<p class="like-line">🙋 나도 봤어요 <b>{n}</b>명</p>' if n else ""  # 공감 수만 보여준다
    # 아래 창 내용(HTML): 머리(종류·위험도·유형, 제목, 닫기 버튼) → 몸통(상태, 위치, 정확한 장소, 신고 일시, 안내, 공감) → 바닥(닫기 버튼)
    q("#detailBody").innerHTML = f"""
      <header class="sheet-head"><!-- 창 머리 -->
        <div><p class="eyebrow">{kind_badge(r)} {severity_badge(r["severity"])} · {esc(category_name(r["category"]))}</p><!-- 종류·위험도·유형 -->
        <h2>{esc(r["title"])}</h2></div><!-- 신고 제목 -->
        <button class="icon-btn" type="button" data-close aria-label="닫기"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg></button><!-- X 닫기 버튼 -->
      </header><!-- 창 머리 끝 -->
      <div class="sheet-body"><!-- 창 몸통 -->
        <dl class="detail-grid"><!-- 항목 표 -->
          <dt>상태</dt><dd>{status_badge(r["status"])}</dd><!-- 처리 상태 -->
          <dt>위치</dt><dd>{esc(place_name(r["map"]))}</dd>{spot}<!-- 건물·층과 정확한 장소 -->
          <dt>신고 일시</dt><dd>{fmt_time(r["created_at"])}</dd><!-- 신고한 시각 -->
        </dl><!-- 항목 표 끝 -->
        <p class="hint">{note}</p><!-- 안내 문구 -->
        {like}<!-- 공감 버튼 또는 공감 수 -->
      </div><!-- 창 몸통 끝 -->
      <footer class="sheet-foot"><button class="btn btn-quiet" type="button" data-close>닫기</button></footer>"""  # 창 내용 끝
    for b in detail_dialog.querySelectorAll("[data-close]"):  # 닫기 버튼들
        on(b, "click", lambda e: detail_dialog.close())  # 누르면 창을 닫는다
    btn = q("#btnLike")  # 공감 버튼
    if btn:  # 있으면
        on(btn, "click", lambda e: asyncio.ensure_future(on_like(rid)))  # 누르면 공감
    if not detail_dialog.open:  # 창이 아직 안 열렸으면
        detail_dialog.showModal()  # 연다


on(detail_dialog, "click", lambda e: detail_dialog.close() if e.target == detail_dialog else None)  # 창 바깥을 누르면 닫기


# ── 공감 "나도 봤어요" ─────────────────────────────
async def on_like(rid):  # 공감 버튼을 눌렀을 때
    if not store.student:  # 공감도 한 사람이 한 번만 누르게 로그인한다
        state["like_after"] = rid  # 로그인 뒤 공감할 신고를 기억한다
        detail_dialog.close()  # 자세히 보기 창을 닫고
        open_login("like")  # 로그인 창을 연다
        return  # 끝
    await do_like(rid)  # 로그인돼 있으면 바로 공감


async def do_like(rid):  # 실제로 공감을 누르거나 취소하는 함수
    btn = q("#btnLike")  # 공감 버튼
    if btn:  # 있으면
        btn.disabled = True  # 두 번 눌리지 않게 잠근다
    try:  # 서버에 보내 본다
        res = await store.toggle_like(rid)  # 결과: 눌렀는지, 새 공감 수
    except StoreError as e:  # 막혔으면
        toast(str(e))  # 이유 안내
        if btn:  # 버튼이 있으면
            btn.disabled = False  # 다시 풀어 준다
        return  # 끝
    for r in state["reports"]:  # 신고 목록에서
        if r["id"] == rid:  # 그 신고를 찾아
            r["likes"] = res["likes"]  # 공감 수를 바꾼다
    (state["liked"].add if res["liked"] else state["liked"].discard)(rid)  # 내가 공감한 목록에 넣거나 뺀다
    toast("공감했어요. 선생님이 더 빨리 확인할게요!" if res["liked"] else "공감을 취소했어요")  # 결과 안내
    render_list()  # 목록을 다시 그린다
    open_detail(rid)  # 창을 다시 그린다 (새 공감 수)


def focus_report(r):  # 신고 위치로 지도를 옮기고 자세히 보여주는 함수
    def do_focus():  # 도면이 준비된 뒤 할 일
        viewer.focus(r["x"], r["y"] - 6, min(viewer.size[0], 220))  # 그 핀을 가운데에 크게
        draw_map()  # 지도를 다시 그린다
        render_list()  # 목록을 다시 그린다
        open_detail(r["id"])  # 자세히 보기 창을 연다

    state["selected"] = r["id"]  # 그 신고를 선택한다
    if r["map"] != state["loaded"]:  # 다른 층의 신고면
        window.history.replaceState(None, "", window.location.pathname if r["map"] == SITE_ID else f"#{r['map']}")  # 주소를 그 층으로 바꾼다
        asyncio.ensure_future(navigate(r["map"], do_focus))  # 그 층으로 간 뒤 do_focus 를 한다
    else:  # 같은 층이면
        do_focus()  # 바로 한다


def on_list_click(e):  # 신고 목록을 눌렀을 때
    item = closest(e, ".report-item")  # 누른 목록 줄
    if item:  # 있으면
        r = next((x for x in state["reports"] if x["id"] == item.dataset.id), None)  # 그 신고를 찾는다
        if r:  # 찾았으면
            focus_report(r)  # 그 위치로 간다


on(q("#reportList"), "click", on_list_click)  # 목록 클릭 연결


# ── 패널 · 층 버튼 · 도구 ──────────────────────────
def on_doc_click(e):  # 화면 어디든 눌렀을 때 (층 버튼·건물 카드 처리)
    fl = closest(e, "[data-floor]")  # 층 버튼을 눌렀는지
    if fl:  # 그렇다면
        go(fl.dataset.floor)  # 그 층으로
        return  # 끝
    card = closest(e, ".bld-card")  # 건물 카드를 눌렀는지
    if card:  # 그렇다면
        go(card.dataset.building)  # 그 건물로


on(window.document, "click", on_doc_click)  # 화면 전체 클릭 연결


def hot(e):  # 건물 카드에 마우스를 올렸을 때 지도에서 그 건물을 강조하는 함수
    card = closest(e, ".bld-card")  # 마우스가 올라간 카드
    bid = card.dataset.building if card else None  # 그 건물 id
    for g in qa(".bld"):  # 지도의 건물들
        g.classList.toggle("is-hot", g.dataset.building == bid)  # 같은 건물만 강조


on(q("#ctx"), "pointerover", hot)  # 마우스가 옆 패널 위에서 움직일 때
on(q("#ctx"), "pointerleave", lambda e: [g.classList.remove("is-hot") for g in qa(".bld")])  # 패널을 벗어나면 강조를 끈다

on(q("#zoomIn"), "click", lambda e: viewer.zoom_by(1.5))  # + 버튼: 1.5배 확대
on(q("#zoomOut"), "click", lambda e: viewer.zoom_by(1 / 1.5))  # - 버튼: 축소
on(q("#zoomFit"), "click", lambda e: viewer.fit())  # 맞춤 버튼: 전체 보기

on(window, "hashchange", lambda e: asyncio.ensure_future(navigate(parse_hash())))  # 주소 # 가 바뀌면 그 곳으로 이동


# ── 검색 (예: 2-1, 보건실, 409) ─────────────────────
search_input = q("#searchInput")  # 검색 입력 칸
search_list = q("#searchResults")  # 검색 결과 목록
search_state = {"items": [], "active": 0}  # 검색 결과와 지금 고른 줄 번호


def show_results(items):  # 검색 결과를 보여주는 함수
    search_state["items"] = items  # 결과 저장
    search_state["active"] = 0  # 첫 줄을 고른다
    if not search_input.value.strip():  # 검색어가 비었으면
        search_list.hidden = True  # 목록을 숨긴다
        return  # 끝
    if not items:  # 결과가 없으면
        search_list.innerHTML = '<li class="empty">찾는 곳이 없어요. 예) 2-1, 보건실, 409</li>'  # 없다는 안내
    else:  # 결과가 있으면
        search_list.innerHTML = "".join(  # 결과 줄들을 만든다
            f'<li role="option" data-i="{i}" aria-selected="{str(i == 0).lower()}">'  # 결과 줄 (첫 줄 선택 표시)
            f'<strong>{esc(r["title"])}</strong><small>{esc(r["sub"])}</small></li>'  # 이름과 설명
            for i, r in enumerate(items))  # 결과마다
    search_list.hidden = False  # 목록을 보여준다


def mark_active():  # 고른 줄을 표시하는 함수
    for li in qa("#searchResults li[data-i]"):  # 결과 줄마다
        li.setAttribute("aria-selected", str(int(li.dataset.i) == search_state["active"]).lower())  # 고른 줄만 선택 표시


def jump_to(r):  # 검색 결과로 이동하는 함수
    search_list.hidden = True  # 결과 목록을 숨긴다
    search_input.blur()  # 입력 칸에서 나간다 (휴대폰 자판을 내린다)

    def do_focus():  # 도면이 준비된 뒤 할 일
        if r["x"] is not None:  # 위치가 있으면 (방·반)
            state["hit"] = (r["x"], r["y"])  # 찾은 곳을 기억한다
            viewer.focus(r["x"], r["y"], min(viewer.size[0], 260))  # 그 곳을 가운데에
            viewer.draw_hit(state["hit"])  # 동그라미 표시
            toast(f"{r['title']} · {r['sub']}")  # 이름 안내

    if state["mode"] == "report":  # 신고 모드였으면
        set_mode("browse")  # 보기 모드로
    if r["floor"] != state["loaded"]:  # 다른 층이면
        window.history.replaceState(None, "", f"#{r['floor']}")  # 주소를 바꾸고
        asyncio.ensure_future(navigate(r["floor"], do_focus))  # 그 층으로 간 뒤 표시
    else:  # 같은 층이면
        state["place"] = r["floor"]  # 지금 곳을 맞추고
        do_focus()  # 바로 표시


def on_search_key(e):  # 검색 칸에서 키를 눌렀을 때
    items = search_state["items"]  # 지금 결과
    if e.key == "Enter":  # Enter 면
        e.preventDefault()  # 기본 동작을 막는다
        if not items:  # 결과가 아직 없으면
            show_results(search(search_input.value))  # 검색한다
            items = search_state["items"]  # 새 결과
        if items:  # 결과가 있으면
            jump_to(items[search_state["active"]])  # 고른 결과로 간다
    elif e.key in ("ArrowDown", "ArrowUp") and items:  # 위·아래 화살표면
        e.preventDefault()  # 커서가 움직이지 않게 막는다
        step = 1 if e.key == "ArrowDown" else -1  # 아래면 +1, 위면 -1
        search_state["active"] = (search_state["active"] + step) % len(items)  # 고른 줄을 옮긴다 (끝에서 처음으로 돈다)
        mark_active()  # 표시를 바꾼다
    elif e.key == "Escape":  # Esc 면
        search_input.value = ""  # 검색어를 지우고
        search_list.hidden = True  # 목록을 숨긴다


def on_result_click(e):  # 검색 결과를 눌렀을 때
    li = closest(e, "li[data-i]")  # 누른 줄
    if li:  # 있으면
        jump_to(search_state["items"][int(li.dataset.i)])  # 그 결과로 간다


on(search_input, "input", lambda e: show_results(search(search_input.value)))  # 글자를 칠 때마다 검색
on(search_input, "keydown", on_search_key)  # 키 입력 연결
on(search_input, "focus", lambda e: show_results(search(search_input.value)))  # 검색 칸을 누르면 결과를 다시 보여준다
on(search_list, "pointerdown", lambda e: e.preventDefault())  # 누르는 동안 입력창 포커스 유지
on(search_list, "click", on_result_click)  # 결과 클릭 연결
_hide_results = create_proxy(lambda: setattr(search_list, "hidden", True))  # 한 번만 만들어 계속 쓴다
on(search_input, "blur", lambda e: window.setTimeout(_hide_results, 150))  # 검색 칸에서 나가면 잠시 뒤 결과를 숨긴다


# ── 시작 ─────────────────────────────────────────
q("#demoNote").hidden = SHARED  # 체험 모드일 때만 안내를 보여준다
pending = await finish_google_return()  # 구글 로그인에서 돌아왔으면 마무리
await refresh_reports()  # 신고 목록을 받는다
await navigate(parse_hash())  # 주소에 맞는 곳을 보여준다
if pending and pending.get("like") and store.student:  # 공감하려고 로그인하고 돌아왔으면
    await do_like(pending["like"])  # 공감한다
elif pending and pending.get("draft") and STUDENT_LOGIN and store.student:  # 신고하려고 로그인하고 돌아왔으면
    set_mode("report")  # 신고 모드로
    set_draft(tuple(pending["draft"]))  # 찍었던 자리를 되살리고
    open_form()  # 신고 창을 연다
q("#btnReport").disabled = False  # 신고 버튼을 쓸 수 있게 한다
hide_loading()  # 준비 화면을 없앤다
