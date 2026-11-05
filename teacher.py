# 선생님용 화면: 로그인 → 대시보드 · 신고 관리 · 지도. 신고 상태 변경, 담당자, 처리 기록.
# 화면 틀(pages.py)과 꾸미기(theme.py)를 먼저 그린다 — 아래 코드가 그 요소들을 찾기 때문
import pages
import theme

theme.apply()
pages.mount("teacher")

import asyncio
import csv
import io
from datetime import datetime, timedelta, timezone

from js import window

from campus import (BUILDING_BY_ID, BUILDINGS, CATEGORIES, FLOOR_INDEX, KINDS, SEVERITIES, SITE_ID, STATUSES,
                    building_of, kind_of, place_name, plan_of)
from common import (KST, SEVERITY_DOTS, category_name, closest, download, esc, fmt_time, hide_loading, is_open,
                    kind_badge, on,
                    parse_time, q, qa, status_badge, severity_badge, time_ago, toast)
import config
from store import SHARED, StoreError, store
import json
import time
from viewer import PlanViewer

NAME_KEY = "kd-safety-teacher-name"
state = {"rows": [], "sel": None, "detail": None, "tab": "dash", "map": SITE_ID, "map_loaded": None,
         "new_status": None}


FAIL_KEY = "kd-safety-login-fails"
MAX_FAILS, LOCK_SEC = 5, 180   # 비밀번호를 5번 틀리면 3분 동안 못 넣는다


def who():
    return window.sessionStorage.getItem(NAME_KEY) or window.localStorage.getItem(NAME_KEY) or ""


def _fails():
    try:
        return json.loads(window.localStorage.getItem(FAIL_KEY) or "{}")
    except Exception:
        return {}


def locked_for():
    """비밀번호를 여러 번 틀려서 잠긴 남은 초 (0 이면 안 잠김)."""
    return max(0, int(_fails().get("until", 0) - time.time()))


def note_fail():
    f = _fails()
    n = f.get("n", 0) + 1
    f = {"n": 0, "until": time.time() + LOCK_SEC} if n >= MAX_FAILS else {"n": n, "until": 0}
    window.localStorage.setItem(FAIL_KEY, json.dumps(f))
    return MAX_FAILS - n if n < MAX_FAILS else 0


def building_name(map_id):
    b = building_of(map_id)
    return b.name if b else "캠퍼스 야외"


async def safe(coro, ok_msg=None):
    """저장소 작업을 하고 오류는 화면에 알린다."""
    try:
        result = await coro
    except StoreError as e:
        toast(str(e))
        if not store.logged_in:
            show_login()
        return None
    if ok_msg:
        toast(ok_msg)
    return result if result is not None else True


# ── 로그인 ───────────────────────────────────────
def show_login():
    q("#app").hidden = True
    q("#login").hidden = False
    q("#btnLogout").hidden = True
    q("#who").textContent = ""
    q("#loginShared").hidden = not SHARED
    shared_account = bool(getattr(config, "TEACHER_EMAIL", ""))
    email = q("#loginForm").elements.namedItem("email")
    email.closest(".field").hidden = shared_account
    q("#loginNote").textContent = ("선생님 비밀번호를 넣으세요." if SHARED and shared_account
                                   else "학교에서 받은 선생님 계정으로 로그인하세요." if SHARED
                                   else "체험 모드예요. 이름만 적고 들어가면 돼요.")


async def on_login(e):
    f = q("#loginForm").elements
    name = str(f.namedItem("name").value).strip()
    if not name:
        return
    keep = bool(f.namedItem("keep").checked)
    err = q("#loginError")
    if SHARED:
        wait = locked_for()
        if wait:
            err.textContent = f"비밀번호를 여러 번 틀렸어요. {wait // 60}분 {wait % 60}초 뒤에 다시 해 주세요."
            err.hidden = False
            return
        btn = q("#loginForm button[type=submit]")
        btn.disabled = True
        email = getattr(config, "TEACHER_EMAIL", "") or str(f.namedItem("email").value).strip()
        try:
            ok = await store.login(email, str(f.namedItem("password").value), keep)
        except Exception:
            ok = None
        btn.disabled = False
        f.namedItem("password").value = ""
        if not ok:
            if ok is None:
                err.textContent = "서버에 연결하지 못했어요. 인터넷을 확인해 주세요."
            else:
                left = note_fail()
                what = "비밀번호가" if getattr(config, "TEACHER_EMAIL", "") else "이메일 또는 비밀번호가"
                err.textContent = (f"{what} 맞지 않아요. ({left}번 더 틀리면 3분 동안 잠겨요)" if left
                                   else "비밀번호를 여러 번 틀렸어요. 3분 뒤에 다시 해 주세요.")
            err.hidden = False
            return
        window.localStorage.removeItem(FAIL_KEY)
    err.hidden = True
    window.sessionStorage.removeItem(NAME_KEY)
    window.localStorage.removeItem(NAME_KEY)
    (window.localStorage if keep else window.sessionStorage).setItem(NAME_KEY, name[:30])
    await enter()


def on_logout(e):
    store.logout()
    window.sessionStorage.removeItem(NAME_KEY)
    window.localStorage.removeItem(NAME_KEY)
    show_login()


on(q("#loginForm"), "submit", on_login, prevent=True)
on(q("#btnLogout"), "click", on_logout)


async def enter():
    q("#login").hidden = True
    q("#app").hidden = False
    q("#btnLogout").hidden = False
    q("#who").textContent = f"{who()} 님"
    q("#demoNote").hidden = SHARED
    await reload()


async def reload():
    rows = await safe(store.list_all())
    if rows is None:
        return
    state["rows"] = rows if isinstance(rows, list) else []
    render_dash()
    render_table()
    if state["tab"] == "map":
        draw_map_pins()


# ── 탭 ──────────────────────────────────────────
def on_tab(e):
    btn = closest(e, "[data-tab]")
    if not btn:
        return
    state["tab"] = btn.dataset.tab
    for b in qa(".t-tabs [data-tab]"):
        b.setAttribute("aria-selected", str(b == btn).lower())
    for name in ("dash", "list", "map"):
        q(f"#tab-{name}").hidden = name != state["tab"]
    if state["tab"] == "map":
        asyncio.ensure_future(load_map(state["map"]))


on(q(".t-tabs"), "click", on_tab)


# ── 대시보드 ─────────────────────────────────────
def bars(items):
    """[(이름, 값)] → 가로 막대 (한 가지 색, 마우스를 올리면 값)."""
    if not items:
        return '<p class="t-empty">처리 전 신고가 없어요 👍</p>'
    top = max(v for _, v in items) or 1
    return '<div class="bars">' + "".join(
        f'<div class="bar-row" title="{esc(k)}: {v}건"><span class="bar-label">{esc(k)}</span>'
        f'<span class="bar-track"><span class="bar-fill" style="width:{v / top * 100:.1f}%"></span></span>'
        f'<span class="bar-val">{v}</span></div>' for k, v in items) + "</div>"


def render_dash():
    rows = state["rows"]
    now = datetime.now(timezone.utc)
    opened = [r for r in rows if is_open(r)]
    week = sum(1 for r in rows if parse_time(r["created_at"]) >= now - timedelta(days=7))
    done_hours = sorted((parse_time(r["resolved_at"]) - parse_time(r["created_at"])).total_seconds() / 3600
                        for r in rows if r["status"] == "done" and r.get("resolved_at"))
    if done_hours:
        mid = done_hours[len(done_hours) // 2]
        med = f"{mid / 24:.1f}일" if mid >= 24 else f"{mid:.0f}시간"
    else:
        med = "-"
    tiles = [("처리 전", len(opened), ""), ("긴급 (처리 전)", sum(r["severity"] == "urgent" for r in opened), "urgent"),
             ("처리중", sum(r["status"] == "doing" for r in rows), ""), ("최근 7일 접수", week, ""),
             ("처리 시간 (중앙값)", med, "")]
    q("#tiles").innerHTML = "".join(f'<div class="tile {c}"><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v, c in tiles)

    by_b = {}
    by_c = {}
    for r in opened:
        by_b[building_name(r["map"])] = by_b.get(building_name(r["map"]), 0) + 1
        by_c[category_name(r["category"])] = by_c.get(category_name(r["category"]), 0) + 1
    q("#chartBuilding").innerHTML = bars(sorted(by_b.items(), key=lambda kv: -kv[1]))
    q("#chartCategory").innerHTML = bars(sorted(by_c.items(), key=lambda kv: -kv[1]))

    today = now.astimezone(KST).date()
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    count = {d: 0 for d in days}
    for r in rows:
        d = parse_time(r["created_at"]).astimezone(KST).date()
        if d in count:
            count[d] += 1
    top = max(count.values()) or 1
    cols = "".join(f'<div class="col" title="{d:%m/%d} · {n}건"><span style="height:{n / top * 100:.1f}%"></span></div>'
                   for d, n in count.items())
    q("#chartDaily").innerHTML = (f'<div class="cols-wrap"><span class="cols-max">{top}건</span><div class="cols">{cols}</div></div>'
                                  f'<div class="cols-axis"><span>{days[0]:%m/%d}</span><span>{days[15]:%m/%d}</span><span>오늘</span></div>')

    hot = sorted((r for r in opened if r["severity"] in ("urgent", "high")), key=lambda r: r["created_at"])[:8]
    q("#hotList").innerHTML = "".join(
        f'<li><button class="report-item" data-id="{r["id"]}" type="button"><span class="sev-dot">{SEVERITY_DOTS[r["severity"]]}</span>'
        f'<span class="t">{kind_badge(r)} {esc(r["title"])}</span>{status_badge(r["status"])}'
        f'<span class="w">{esc(place_name(r["map"]))} · {time_ago(r["created_at"])}</span></button></li>'
        for r in hot) or '<li class="t-empty">없어요 👍</li>'


on(q("#hotList"), "click", lambda e: open_detail(closest(e, ".report-item").dataset.id) if closest(e, ".report-item") else None)


# ── 신고 관리 표 ──────────────────────────────────
q("#fSeverity").innerHTML = '<option value="">전체</option>' + "".join(
    f'<option value="{k}">{esc(n)}</option>' for k, (n, _) in SEVERITIES.items())
q("#fBuilding").innerHTML = '<option value="">전체</option><option value="site">캠퍼스 야외</option>' + "".join(
    f'<option value="{b.id}">{esc(b.name)}</option>' for b in BUILDINGS)


def filtered():
    st, sev, bid, kind = q("#fStatus").value, q("#fSeverity").value, q("#fBuilding").value, q("#fKind").value
    text = str(q("#fSearch").value).strip().lower()
    out = []
    for r in state["rows"]:
        if st == "open" and not is_open(r):
            continue
        if st and st != "open" and r["status"] != st:
            continue
        if sev and r["severity"] != sev:
            continue
        if kind and kind_of(r) != kind:
            continue
        if bid == "site" and r["map"] != SITE_ID:
            continue
        if bid and bid != "site" and (building_of(r["map"]) is None or building_of(r["map"]).id != bid):
            continue
        hay = " ".join(str(r.get(k) or "") for k in ("title", "spot", "description", "reporter")).lower()
        if text and text not in hay:
            continue
        out.append(r)
    rank = {k: i for i, k in enumerate(SEVERITIES)}
    # 급한 것 먼저, 같은 위험도는 최근 것 먼저
    out.sort(key=lambda r: r["created_at"], reverse=True)
    out.sort(key=lambda r: rank.get(r["severity"], 9))
    return out


def render_table():
    rows = filtered()
    q("#listCount").textContent = f"{len(rows)}건 · 줄을 누르면 자세한 내용과 처리 메뉴가 열려요"
    head = "<thead><tr><th>접수</th><th>종류</th><th>위험도</th><th>상태</th><th>제목</th><th>위치</th><th>장소</th><th>유형</th><th>담당</th><th>📷</th></tr></thead>"
    body = "".join(
        f'<tr data-id="{r["id"]}" class="{"is-selected" if r["id"] == state["sel"] else ""}">'
        f'<td>{parse_time(r["created_at"]).astimezone(KST):%m-%d %H:%M}</td><td>{kind_badge(r)}</td><td>{severity_badge(r["severity"])}</td>'
        f'<td>{status_badge(r["status"])}</td><td class="title">{esc(r["title"])}</td><td>{esc(place_name(r["map"]))}</td>'
        f'<td>{esc(r.get("spot") or "")}</td><td>{esc(category_name(r["category"]))}</td><td>{esc(r.get("assignee") or "")}</td>'
        f'<td>{"📷" if r.get("has_photo") else ""}</td></tr>' for r in rows)
    q("#reportTable").innerHTML = head + f"<tbody>{body or '<tr><td colspan=10 class=t-empty>조건에 맞는 신고가 없어요</td></tr>'}</tbody>"


for sel in ("#fStatus", "#fKind", "#fSeverity", "#fBuilding"):
    on(q(sel), "change", lambda e: render_table())
on(q("#fSearch"), "input", lambda e: render_table())
on(q("#reportTable"), "click", lambda e: open_detail(closest(e, "tr[data-id]").dataset.id) if closest(e, "tr[data-id]") else None)


def export_csv(e):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["접수일시", "종류", "위험도", "상태", "제목", "위치", "정확한 장소", "유형", "내용", "신고자", "담당자", "처리일시", "사진"])
    for r in state["rows"]:
        w.writerow([fmt_time(r["created_at"]), KINDS[kind_of(r)][0], SEVERITIES.get(r["severity"], ("",))[0], STATUSES.get(r["status"], r["status"]),
                    r["title"], place_name(r["map"]), r.get("spot") or "", category_name(r["category"]),
                    r.get("description") or "", r.get("reporter") or "", r.get("assignee") or "",
                    fmt_time(r.get("resolved_at")) if r.get("resolved_at") else "", "있음" if r.get("has_photo") else ""])
    # ﻿: 엑셀에서 한글이 깨지지 않게
    download(f"위험불편신고_{datetime.now(KST):%Y%m%d}.csv", "﻿" + buf.getvalue(), "text/csv")


on(q("#btnCsv"), "click", export_csv)


# ── 지도 탭 ──────────────────────────────────────
tmap = PlanViewer(q("#tmap"))
tmap.on_view_change = tmap.scale_markers
q("#mBuilding").innerHTML = f'<option value="{SITE_ID}">🏫 캠퍼스 전체</option>' + "".join(
    f'<option value="{b.id}">{esc(b.name)} ({esc(b.dong)})</option>' if b.dong else f'<option value="{b.id}">{esc(b.name)}</option>'
    for b in BUILDINGS)


async def load_map(map_id):
    state["map"] = map_id
    hit = FLOOR_INDEX.get(map_id)
    q("#mBuilding").value = hit[0].id if hit else SITE_ID
    q("#mFloors").innerHTML = "".join(
        f'<button data-mfloor="{f.id}" aria-selected="{str(f.id == map_id).lower()}">{esc(f.name)}</button>'
        for f in hit[0].floors) if hit else ""
    if state["map_loaded"] != map_id:
        state["map_loaded"] = map_id
        try:
            if not await tmap.load(plan_of(map_id)[0], locked=map_id == SITE_ID, crop=plan_of(map_id)[1]):
                return
        except Exception as e:
            toast(str(e))
            return
    draw_map_pins()


def draw_map_pins():
    map_id = state["map"]
    rows = [r for r in state["rows"] if r["map"] == map_id and (is_open(r) or not q("#mOnlyOpen").checked)]
    if map_id == SITE_ID:
        counts = {}
        for r in state["rows"]:
            b = building_of(r["map"])
            if b and is_open(r):
                counts[b.id] = counts.get(b.id, 0) + 1
        tmap.draw_buildings(counts)
    else:
        tmap.clear_overlay()
    tmap.draw_pins(rows, state["sel"])


def on_mbuilding(e):
    bid = q("#mBuilding").value
    asyncio.ensure_future(load_map(SITE_ID if bid == SITE_ID else BUILDING_BY_ID[bid].default_floor.id))


on(q("#mBuilding"), "change", on_mbuilding)
on(q("#mFloors"), "click", lambda e: asyncio.ensure_future(load_map(closest(e, "[data-mfloor]").dataset.mfloor))
   if closest(e, "[data-mfloor]") else None)
on(q("#mOnlyOpen"), "change", lambda e: draw_map_pins())


def on_tmap_tap(x, y, target):
    pin = target.closest(".pin") if hasattr(target, "closest") else None
    if pin:
        open_detail(pin.dataset.id)
        return
    if state["map"] == SITE_ID:
        from campus import building_at
        b = building_at(x, y)
        if b:
            asyncio.ensure_future(load_map(b.default_floor.id))


tmap.on_tap = on_tmap_tap


# ── 신고 상세 · 처리 ──────────────────────────────
dlg = q("#detailDialog")
mini = PlanViewer(q("#miniMap"))
mini.on_view_change = mini.scale_markers
q("#dStatus").innerHTML = "".join(f'<button type="button" data-v="{k}">{esc(v)}</button>' for k, v in STATUSES.items())


def open_detail(rid):
    asyncio.ensure_future(_open_detail(rid))


async def _open_detail(rid):
    r = await safe(store.get(rid))
    if not r or r is True:
        toast("신고를 찾을 수 없어요")
        return
    state["sel"] = rid
    state["detail"] = r
    state["new_status"] = None
    render_table()
    if state["tab"] == "map":
        draw_map_pins()
    q("#dHead").innerHTML = (f'<p class="eyebrow">{kind_badge(r)} {severity_badge(r["severity"])} · {esc(category_name(r["category"]))} · '
                             f'{status_badge(r["status"])}</p><h2>{esc(r["title"])}</h2>')
    rows = [("위치", place_name(r["map"])), ("정확한 장소", r.get("spot")), ("신고자", r.get("reporter") or "이름 안 적음"),
            ("구글 계정", r.get("reporter_email")),
            ("신고 일시", fmt_time(r["created_at"])), ("담당자", r.get("assignee")),
            ("처리 일시", fmt_time(r["resolved_at"]) if r.get("resolved_at") else None)]
    info = "".join(f"<dt>{k}</dt><dd>{esc(v)}</dd>" for k, v in rows if v)
    desc = f'<p class="detail-desc">{esc(r["description"])}</p>' if r.get("description") else ""
    photo = f'<img class="detail-photo" src="{esc(r["photo"])}" alt="신고 사진" />' if r.get("photo") else ""
    q("#dInfo").innerHTML = f'{desc}<dl class="detail-grid">{info}</dl>{photo}'
    q("#miniCap").textContent = f"{place_name(r['map'])} 위치"
    q("#dNote").value = ""
    q("#dMemo").value = ""
    q("#dAssignee").value = r.get("assignee") or ""
    for b in qa("#dStatus button"):
        b.setAttribute("aria-pressed", str(b.dataset.v == r["status"]).lower())
    q("#dStatusSave").disabled = True
    await render_events(rid)
    await render_abuse(r)
    if not dlg.open:
        dlg.showModal()
    # 작은 지도: 신고 위치를 확대해서 보여준다
    if await mini.load(plan_of(r["map"])[0], crop=plan_of(r["map"])[1]):
        mini.draw_pins([r], rid)
        mini.focus(r["x"], r["y"] - 8, min(mini.size[0], 260))


async def render_events(rid):
    evs = await safe(store.list_events(rid)) or []
    icons = {"status": "🔄", "assign": "👤", "memo": "📝"}
    q("#dEvents").innerHTML = "".join(
        f'<li><b>{icons.get(e["kind"], "•")} {esc(e["body"])}</b><span>{esc(e["actor"])} · {fmt_time(e["created_at"])}</span></li>'
        for e in (evs if isinstance(evs, list) else [])) or '<li class="t-empty">아직 기록이 없어요</li>'


def abuse_key(r):
    """장난 신고를 막을 대상: 구글 계정으로 신고했으면 그 계정, 아니면 기기."""
    if r.get("reporter_uid"):
        return "reporter_uid", r["reporter_uid"]
    return "device", r.get("device")


async def render_abuse(r):
    """장난 신고 막기: 같은 기기에서 온 신고 수, 차단 상태, 차단/해제 버튼."""
    box = q("#dAbuse")
    key, dev = abuse_key(r)
    if not dev:
        box.innerHTML = ""
        return
    same = [x for x in state["rows"] if x.get(key) == dev]
    rejected = sum(1 for x in same if x["status"] == "rejected")
    blocked = await safe(store.is_blocked(dev))
    blocked = blocked is True
    state["blocked"] = blocked
    who_txt = "이 계정" if key == "reporter_uid" else "이 기기"
    info = f"{who_txt}으로 온 신고 {len(same)}건" + (f" · 반려 {rejected}건" if rejected else "")
    btn = (f'<button class="btn btn-quiet" type="button" data-abuse="unblock">✅ {who_txt} 차단 풀기</button>' if blocked else
           f'<button class="btn-text-danger" type="button" data-abuse="block">🚫 장난 신고로 반려 + {who_txt} 신고 막기</button>')
    box.innerHTML = (f'<h4>장난 신고 막기</h4><p class="t-count">{esc(info)} · '
                     f'{"<b class=blocked>차단됨</b>" if blocked else "정상"}</p>{btn}')


async def on_abuse(e):
    b = closest(e, "button[data-abuse]")
    r = state["detail"]
    if not b or not r:
        return
    key, target = abuse_key(r)
    if not target:
        return
    who_txt = "이 계정" if key == "reporter_uid" else "이 기기"
    if b.dataset.abuse == "block":
        tip = ("" if key == "reporter_uid" else
               "\n(기기 차단은 브라우저 기록을 지우면 풀려서, 생활지도와 함께 쓰세요)")
        if not window.confirm(f"이 신고를 '장난 신고'로 반려하고, {who_txt}으로 더는 신고하지 못하게 막을까요?{tip}"):
            return
        if r["status"] != "rejected":
            await safe(store.update(r["id"], {"status": "rejected",
                                              "resolved_at": datetime.now(timezone.utc).isoformat()}))
        reason = f"장난 신고: {r['title'][:40]}" + (f" ({r['reporter_email']})" if r.get("reporter_email") else "")
        if await safe(store.block(target, reason[:100], who())):
            await safe(store.add_event(r["id"], "status", f"장난 신고로 반려 · {who_txt} 신고 막음", who()),
                       f"반려하고 {who_txt}의 신고를 막았어요")
    else:
        if not window.confirm(f"{who_txt}의 신고 막기를 풀까요?"):
            return
        if await safe(store.unblock(target)):
            await safe(store.add_event(r["id"], "memo", f"{who_txt} 신고 막기를 풀었어요", who()), "차단을 풀었어요")
    await reload()
    await _open_detail(r["id"])


def on_status_pick(e):
    b = closest(e, "button[data-v]")
    if not b or not state["detail"]:
        return
    state["new_status"] = b.dataset.v
    for x in qa("#dStatus button"):
        x.setAttribute("aria-pressed", str(x == b).lower())
    q("#dStatusSave").disabled = b.dataset.v == state["detail"]["status"]


async def on_status_save(e):
    r, st = state["detail"], state["new_status"]
    if not r or not st or st == r["status"]:
        return
    patch = {"status": st, "resolved_at": datetime.now(timezone.utc).isoformat() if st in ("done", "rejected") else None}
    note = str(q("#dNote").value).strip()
    if await safe(store.update(r["id"], patch)):
        await safe(store.add_event(r["id"], "status", f"상태 → {STATUSES[st]}" + (f" · {note}" if note else ""), who()),
                   f"'{STATUSES[st]}'(으)로 바꿨어요")
        await reload()
        await _open_detail(r["id"])


async def on_assignee_save(e):
    r = state["detail"]
    name = str(q("#dAssignee").value).strip()
    if not r or name == (r.get("assignee") or ""):
        return
    if await safe(store.update(r["id"], {"assignee": name})):
        await safe(store.add_event(r["id"], "assign", f"담당자 → {name or '없음'}", who()), "담당자를 저장했어요")
        await reload()
        await _open_detail(r["id"])


async def on_memo_save(e):
    r = state["detail"]
    memo = str(q("#dMemo").value).strip()
    if r and memo:
        await safe(store.add_event(r["id"], "memo", memo, who()), "메모를 남겼어요")
        q("#dMemo").value = ""
        await render_events(r["id"])


async def on_delete(e):
    r = state["detail"]
    if not r or not window.confirm("이 신고를 삭제할까요? 되돌릴 수 없어요.\n(장난·중복 신고는 보통 '반려'로 처리하는 걸 권해요)"):
        return
    if await safe(store.delete(r["id"]), "삭제했어요"):
        dlg.close()
        state["sel"] = state["detail"] = None
        await reload()


on(q("#dStatus"), "click", on_status_pick)
on(q("#dStatusSave"), "click", on_status_save)
on(q("#dAssigneeSave"), "click", on_assignee_save)
on(q("#dMemoSave"), "click", on_memo_save)
on(q("#dDelete"), "click", on_delete)
on(q("#dAbuse"), "click", on_abuse)
on(dlg.querySelector("[data-close]"), "click", lambda e: dlg.close())
on(dlg, "click", lambda e: dlg.close() if e.target == dlg else None)


# ── 시작 ─────────────────────────────────────────
if who() and store.logged_in:
    await enter()
else:
    show_login()
hide_loading()
