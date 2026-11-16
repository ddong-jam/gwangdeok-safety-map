# 선생님용 화면: 로그인 → 대시보드 · 신고 관리 · 지도. 신고 상태 변경, 담당자, 처리 기록.
# 화면 틀(pages.py)과 꾸미기(theme.py)를 먼저 그린다 — 아래 코드가 그 요소들을 찾기 때문
import pages  # 화면 틀(HTML)을 만드는 파일
import theme  # 화면 꾸미기(CSS)를 넣는 파일

theme.apply()  # 꾸미기를 화면에 넣는다
pages.mount("teacher")  # 선생님용 화면 틀을 그린다

import asyncio  # 기다렸다 이어서 하는 함수(async)를 실행하는 도구
import csv  # 표를 CSV 파일 글자로 만드는 도구
import io  # 글자를 파일처럼 모으는 도구 (CSV 를 만들 때)
from datetime import datetime, timedelta, timezone  # 날짜·시간 도구

from js import window  # 브라우저 창 (저장 공간, 확인 창 등)

from campus import (BUILDING_BY_ID, BUILDINGS, CATEGORIES, FLOOR_INDEX, KINDS, SEVERITIES, SITE_ID, STATUSES,  # 학교 건물·층·신고 분류 데이터와
                    building_of, kind_of, place_name, plan_of)  # 도우미 함수들
from common import (KST, SEVERITY_DOTS, category_name, closest, download, esc, fmt_time, hide_loading, is_open,  # 화면 조작·표시 도구들
                    kind_badge, on,  # 종류 표시, 이벤트 연결
                    parse_time, q, qa, status_badge, severity_badge, time_ago, toast)  # 시간·요소 찾기·배지·알림
import config  # 설정 (선생님 공용 이메일)
from store import SHARED, StoreError, store  # 신고 저장소
import json  # 값을 글자(JSON)로 바꾸는 도구 — 비밀번호 틀린 횟수를 저장한다
import time  # 지금 시각(초) — 잠금 시간을 잰다
from viewer import PlanViewer  # 도면 뷰어

NAME_KEY = "kd-safety-teacher-name"  # 선생님 이름을 저장하는 이름
state = {"rows": [], "sel": None, "detail": None, "tab": "dash", "map": SITE_ID, "map_loaded": None,  # 화면 상태: 신고 목록, 선택한 신고, 자세히 볼 신고, 지금 탭, 지도 위치, 불러온 지도
         "new_status": None}  # 새로 고른 처리 상태


FAIL_KEY = "kd-safety-login-fails"  # 비밀번호 틀린 기록을 저장하는 이름
MAX_FAILS, LOCK_SEC = 5, 180   # 비밀번호를 5번 틀리면 3분 동안 못 넣는다


def who():  # 로그인한 선생님 이름을 돌려주는 함수
    return window.sessionStorage.getItem(NAME_KEY) or window.localStorage.getItem(NAME_KEY) or ""  # 창 저장 공간 → 기기 저장 공간 순서로 찾는다


def _fails():  # 비밀번호 틀린 기록을 읽는 함수
    try:  # 읽어 본다
        return json.loads(window.localStorage.getItem(FAIL_KEY) or "{}")  # {"n": 틀린 횟수, "until": 잠금 끝 시각}
    except Exception:  # 망가졌으면
        return {}  # 기록 없음


def locked_for():  # 잠긴 남은 시간을 돌려주는 함수
    """비밀번호를 여러 번 틀려서 잠긴 남은 초 (0 이면 안 잠김)."""  # 이 함수가 하는 일을 적은 설명글
    return max(0, int(_fails().get("until", 0) - time.time()))  # 잠금 끝 시각 - 지금 (음수면 0)


def note_fail():  # 비밀번호를 틀렸을 때 기록하는 함수
    f = _fails()  # 지금까지 기록
    n = f.get("n", 0) + 1  # 틀린 횟수 +1
    f = {"n": 0, "until": time.time() + LOCK_SEC} if n >= MAX_FAILS else {"n": n, "until": 0}  # 5번째면 3분 잠금, 아니면 횟수만 저장
    window.localStorage.setItem(FAIL_KEY, json.dumps(f))  # 저장한다
    return MAX_FAILS - n if n < MAX_FAILS else 0  # 남은 기회 (잠겼으면 0)


def building_name(map_id):  # 층 id 로 건물 이름을 돌려주는 함수
    b = building_of(map_id)  # 건물
    return b.name if b else "캠퍼스 야외"  # 건물이 없으면 야외


async def safe(coro, ok_msg=None):  # 저장소 작업을 안전하게 실행하는 함수
    """저장소 작업을 하고 오류는 화면에 알린다."""  # 이 함수가 하는 일을 적은 설명글
    try:  # 해 본다
        result = await coro  # 작업 결과
    except StoreError as e:  # 문제가 생기면
        toast(str(e))  # 안내
        if not store.logged_in:  # 로그인이 풀렸으면
            show_login()  # 로그인 화면으로
        return None  # 실패
    if ok_msg:  # 성공 안내 문구가 있으면
        toast(ok_msg)  # 보여준다
    return result if result is not None else True  # 결과 (없으면 True = 성공)


# ── 로그인 ───────────────────────────────────────
def show_login():  # 로그인 화면을 보여주는 함수
    q("#app").hidden = True  # 관리 화면을 숨긴다
    q("#login").hidden = False  # 로그인 화면을 보여준다
    q("#btnLogout").hidden = True  # 로그아웃 버튼을 숨긴다
    q("#who").textContent = ""  # 이름 표시를 지운다
    q("#loginShared").hidden = not SHARED  # 공용 모드일 때만 이메일·비밀번호 칸 묶음을 보여준다
    shared_account = bool(getattr(config, "TEACHER_EMAIL", ""))  # 공용 계정을 쓰는지
    email = q("#loginForm").elements.namedItem("email")  # 이메일 칸
    email.closest(".field").hidden = shared_account  # 공용 계정이면 이메일 칸을 숨긴다
    q("#loginNote").textContent = ("선생님 비밀번호를 넣으세요." if SHARED and shared_account  # 공용 계정일 때 안내
                                   else "학교에서 받은 선생님 계정으로 로그인하세요." if SHARED  # 각자 계정일 때 안내
                                   else "체험 모드예요. 이름만 적고 들어가면 돼요.")  # 체험 모드일 때 안내


async def on_login(e):  # 로그인 버튼을 눌렀을 때
    f = q("#loginForm").elements  # 로그인 양식의 칸들
    name = str(f.namedItem("name").value).strip()  # 이름 칸
    if not name:  # 이름이 비었으면
        return  # 아무것도 안 한다 (이름은 필수)
    keep = bool(f.namedItem("keep").checked)  # 로그인 유지 체크 여부
    err = q("#loginError")  # 오류 표시 칸
    if SHARED:  # 공용 모드면 실제 로그인
        wait = locked_for()  # 잠긴 남은 시간
        if wait:  # 잠겨 있으면
            err.textContent = f"비밀번호를 여러 번 틀렸어요. {wait // 60}분 {wait % 60}초 뒤에 다시 해 주세요."  # 남은 시간 안내
            err.hidden = False  # 보여준다
            return  # 끝
        btn = q("#loginForm button[type=submit]")  # 로그인 버튼
        btn.disabled = True  # 두 번 눌리지 않게 잠근다
        email = getattr(config, "TEACHER_EMAIL", "") or str(f.namedItem("email").value).strip()  # 공용 이메일 또는 적은 이메일
        try:  # 로그인해 본다
            ok = await store.login(email, str(f.namedItem("password").value), keep)  # 성공 True, 틀림 False
        except Exception:  # 연결 실패면
            ok = None  # None
        btn.disabled = False  # 버튼을 푼다
        f.namedItem("password").value = ""  # 비밀번호 칸을 비운다
        if not ok:  # 실패했으면
            if ok is None:  # 연결 실패면
                err.textContent = "서버에 연결하지 못했어요. 인터넷을 확인해 주세요."  # 인터넷 안내
            else:  # 비밀번호가 틀렸으면
                left = note_fail()  # 틀린 횟수를 기록하고 남은 기회를 받는다
                what = "비밀번호가" if getattr(config, "TEACHER_EMAIL", "") else "이메일 또는 비밀번호가"  # 무엇이 틀렸는지
                err.textContent = (f"{what} 맞지 않아요. ({left}번 더 틀리면 3분 동안 잠겨요)" if left  # 남은 기회 안내
                                   else "비밀번호를 여러 번 틀렸어요. 3분 뒤에 다시 해 주세요.")  # 잠겼다는 안내
            err.hidden = False  # 오류를 보여준다
            return  # 끝
        window.localStorage.removeItem(FAIL_KEY)  # 성공했으니 틀린 기록을 지운다
    err.hidden = True  # 오류 표시를 숨긴다
    window.sessionStorage.removeItem(NAME_KEY)  # 옛 이름을 지운다 (창)
    window.localStorage.removeItem(NAME_KEY)  # 옛 이름을 지운다 (기기)
    (window.localStorage if keep else window.sessionStorage).setItem(NAME_KEY, name[:30])  # 유지하면 기기에, 아니면 창에 이름 저장
    await enter()  # 관리 화면으로 들어간다


def on_logout(e):  # 로그아웃 버튼을 눌렀을 때
    store.logout()  # 로그아웃
    window.sessionStorage.removeItem(NAME_KEY)  # 이름 지우기 (창)
    window.localStorage.removeItem(NAME_KEY)  # 이름 지우기 (기기)
    show_login()  # 로그인 화면으로


on(q("#loginForm"), "submit", on_login, prevent=True)  # 로그인 양식 제출 연결 (새로고침은 막는다)
on(q("#btnLogout"), "click", on_logout)  # 로그아웃 버튼 연결


async def enter():  # 관리 화면으로 들어가는 함수
    q("#login").hidden = True  # 로그인 화면을 숨긴다
    q("#app").hidden = False  # 관리 화면을 보여준다
    q("#btnLogout").hidden = False  # 로그아웃 버튼을 보여준다
    q("#who").textContent = f"{who()} 님"  # 위쪽에 이름 표시
    q("#demoNote").hidden = SHARED  # 체험 모드일 때만 안내
    await reload()  # 신고 목록을 불러온다


async def reload():  # 신고 목록을 새로 불러와 화면을 다시 그리는 함수
    rows = await safe(store.list_all())  # 전체 신고
    if rows is None:  # 실패했으면
        return  # 끝
    state["rows"] = rows if isinstance(rows, list) else []  # 목록 저장
    render_dash()  # 대시보드를 그린다
    render_table()  # 신고 표를 그린다
    if state["tab"] == "map":  # 지도 탭이면
        draw_map_pins()  # 핀을 다시 그린다


# ── 탭 ──────────────────────────────────────────
def on_tab(e):  # 탭(대시보드·신고 관리·지도)을 눌렀을 때
    btn = closest(e, "[data-tab]")  # 누른 탭 버튼
    if not btn:  # 없으면
        return  # 끝
    state["tab"] = btn.dataset.tab  # 지금 탭 저장
    for b in qa(".t-tabs [data-tab]"):  # 탭 버튼마다
        b.setAttribute("aria-selected", str(b == btn).lower())  # 누른 것만 선택 표시
    for name in ("dash", "list", "map"):  # 탭 내용마다
        q(f"#tab-{name}").hidden = name != state["tab"]  # 고른 탭만 보여준다
    if state["tab"] == "map":  # 지도 탭이면
        asyncio.ensure_future(load_map(state["map"]))  # 지도를 불러온다


on(q(".t-tabs"), "click", on_tab)  # 탭 클릭 연결


# ── 대시보드 ─────────────────────────────────────
def bars(items):  # 가로 막대그래프를 만드는 함수
    """[(이름, 값)] → 가로 막대 (한 가지 색, 마우스를 올리면 값)."""  # 이 함수가 하는 일을 적은 설명글
    if not items:  # 값이 없으면
        return '<p class="t-empty">처리 전 신고가 없어요 👍</p>'  # 없다는 안내
    top = max(v for _, v in items) or 1  # 가장 큰 값 (막대 길이 기준)
    return '<div class="bars">' + "".join(  # 막대 묶음
        f'<div class="bar-row" title="{esc(k)}: {v}건"><span class="bar-label">{esc(k)}</span>'  # 한 줄: 이름
        f'<span class="bar-track"><span class="bar-fill" style="width:{v / top * 100:.1f}%"></span></span>'  # 값에 비례한 막대
        f'<span class="bar-val">{v}</span></div>' for k, v in items) + "</div>"  # 값 숫자


def render_dash():  # 대시보드(첫 화면)를 그리는 함수
    rows = state["rows"]  # 모든 신고
    now = datetime.now(timezone.utc)  # 지금
    opened = [r for r in rows if is_open(r)]  # 처리 전 신고
    week = sum(1 for r in rows if parse_time(r["created_at"]) >= now - timedelta(days=7))  # 최근 7일 접수 수
    done_hours = sorted((parse_time(r["resolved_at"]) - parse_time(r["created_at"])).total_seconds() / 3600  # 처리에 걸린 시간(시간 단위)들을
                        for r in rows if r["status"] == "done" and r.get("resolved_at"))  # 처리 완료된 신고에서 모아 정렬
    if done_hours:  # 있으면
        mid = done_hours[len(done_hours) // 2]  # 가운데 값 (중앙값)
        med = f"{mid / 24:.1f}일" if mid >= 24 else f"{mid:.0f}시간"  # 하루 넘으면 "일", 아니면 "시간"
    else:  # 없으면
        med = "-"  # 표시 없음
    tiles = [("처리 전", len(opened), ""), ("긴급 (처리 전)", sum(r["severity"] == "urgent" for r in opened), "urgent"),  # 숫자 카드: 처리 전, 긴급
             ("처리중", sum(r["status"] == "doing" for r in rows), ""), ("최근 7일 접수", week, ""),  # 처리중, 최근 7일
             ("처리 시간 (중앙값)", med, "")]  # 처리 시간
    q("#tiles").innerHTML = "".join(f'<div class="tile {c}"><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v, c in tiles)  # 카드들을 그린다

    by_b = {}  # 건물별 처리 전 신고 수
    by_c = {}  # 유형별 처리 전 신고 수
    for r in opened:  # 처리 전 신고마다
        by_b[building_name(r["map"])] = by_b.get(building_name(r["map"]), 0) + 1  # 건물 수 +1
        by_c[category_name(r["category"])] = by_c.get(category_name(r["category"]), 0) + 1  # 유형 수 +1
    q("#chartBuilding").innerHTML = bars(sorted(by_b.items(), key=lambda kv: -kv[1]))  # 건물별 막대 (많은 순)
    q("#chartCategory").innerHTML = bars(sorted(by_c.items(), key=lambda kv: -kv[1]))  # 유형별 막대 (많은 순)

    today = now.astimezone(KST).date()  # 오늘 (한국 날짜)
    days = [today - timedelta(days=i) for i in range(29, -1, -1)]  # 최근 30일 (오래된 날부터)
    count = {d: 0 for d in days}  # 날짜별 접수 수
    for r in rows:  # 신고마다
        d = parse_time(r["created_at"]).astimezone(KST).date()  # 접수 날짜
        if d in count:  # 최근 30일 안이면
            count[d] += 1  # 그 날 수 +1
    top = max(count.values()) or 1  # 가장 많은 날 (기둥 높이 기준)
    cols = "".join(f'<div class="col" title="{d:%m/%d} · {n}건"><span style="height:{n / top * 100:.1f}%"></span></div>'  # 날짜별 세로 기둥
                   for d, n in count.items())  # 날마다
    q("#chartDaily").innerHTML = (f'<div class="cols-wrap"><span class="cols-max">{top}건</span><div class="cols">{cols}</div></div>'  # 기둥 그래프 + 최댓값 표시
                                  f'<div class="cols-axis"><span>{days[0]:%m/%d}</span><span>{days[15]:%m/%d}</span><span>오늘</span></div>')  # 아래 날짜 축

    hot = sorted((r for r in opened if r["severity"] in ("urgent", "high")), key=lambda r: r["created_at"])[:8]  # 긴급·높음 처리 전 신고 (오래된 순 8개)
    q("#hotList").innerHTML = "".join(  # 급한 신고 목록
        f'<li><button class="report-item" data-id="{r["id"]}" type="button"><span class="sev-dot">{SEVERITY_DOTS[r["severity"]]}</span>'  # 위험도 색
        f'<span class="t">{kind_badge(r)} {esc(r["title"])}</span>{status_badge(r["status"])}'  # 종류·제목·상태
        f'<span class="w">{esc(place_name(r["map"]))} · {time_ago(r["created_at"])}</span></button></li>'  # 위치·지난 시간
        for r in hot) or '<li class="t-empty">없어요 👍</li>'  # 없으면 안내


on(q("#hotList"), "click", lambda e: open_detail(closest(e, ".report-item").dataset.id) if closest(e, ".report-item") else None)  # 급한 신고를 누르면 자세히 보기


# ── 신고 관리 표 ──────────────────────────────────
q("#fSeverity").innerHTML = '<option value="">전체</option>' + "".join(  # 위험도 거르기 선택지
    f'<option value="{k}">{esc(n)}</option>' for k, (n, _) in SEVERITIES.items())  # 위험도마다
q("#fBuilding").innerHTML = '<option value="">전체</option><option value="site">캠퍼스 야외</option>' + "".join(  # 건물 거르기 선택지
    f'<option value="{b.id}">{esc(b.name)}</option>' for b in BUILDINGS)  # 건물마다


def filtered():  # 거르기 조건에 맞는 신고만 골라 정렬하는 함수
    st, sev, bid, kind = q("#fStatus").value, q("#fSeverity").value, q("#fBuilding").value, q("#fKind").value  # 고른 상태·위험도·건물·종류
    text = str(q("#fSearch").value).strip().lower()  # 검색어
    out = []  # 결과
    for r in state["rows"]:  # 신고마다
        if st == "open" and not is_open(r):  # "처리 전" 을 골랐는데 끝난 신고면
            continue  # 뺀다
        if st and st != "open" and r["status"] != st:  # 특정 상태를 골랐는데 다르면
            continue  # 뺀다
        if sev and r["severity"] != sev:  # 위험도가 다르면
            continue  # 뺀다
        if kind and kind_of(r) != kind:  # 종류가 다르면
            continue  # 뺀다
        if bid == "site" and r["map"] != SITE_ID:  # 야외를 골랐는데 건물 신고면
            continue  # 뺀다
        if bid and bid != "site" and (building_of(r["map"]) is None or building_of(r["map"]).id != bid):  # 다른 건물이면
            continue  # 뺀다
        hay = " ".join(str(r.get(k) or "") for k in ("title", "spot", "description", "reporter")).lower()  # 제목·장소·내용·이름을 합친 글
        if text and text not in hay:  # 검색어가 없으면
            continue  # 뺀다
        out.append(r)  # 조건을 다 통과하면 넣는다
    rank = {k: i for i, k in enumerate(SEVERITIES)}  # 위험도 순위 (긴급 0, 높음 1 ...)
    # 급한 것 먼저, 같은 위험도는 공감(나도 봤어요) 많은 것 먼저, 그다음 최근 것 먼저
    out.sort(key=lambda r: r["created_at"], reverse=True)  # 먼저 최근 순으로
    out.sort(key=lambda r: (rank.get(r["severity"], 9), -(r.get("likes") or 0)))  # 그다음 위험도 → 공감 많은 순 (같으면 최근 순 유지)
    return out  # 결과


def render_table():  # 신고 관리 표를 그리는 함수
    rows = filtered()  # 거른 신고
    q("#listCount").textContent = f"{len(rows)}건 · 줄을 누르면 자세한 내용과 처리 메뉴가 열려요"  # 개수 안내
    head = "<thead><tr><th>접수</th><th>종류</th><th>위험도</th><th>상태</th><th>제목</th><th>위치</th><th>장소</th><th>유형</th><th>담당</th><th title='나도 봤어요'>🙋</th><th>📷</th></tr></thead>"  # 표 제목 줄
    body = "".join(  # 표 내용 줄들
        f'<tr data-id="{r["id"]}" class="{"is-selected" if r["id"] == state["sel"] else ""}">'  # 한 줄 (선택한 신고면 강조)
        f'<td>{parse_time(r["created_at"]).astimezone(KST):%m-%d %H:%M}</td><td>{kind_badge(r)}</td><td>{severity_badge(r["severity"])}</td>'  # 접수 시각·종류·위험도
        f'<td>{status_badge(r["status"])}</td><td class="title">{esc(r["title"])}</td><td>{esc(place_name(r["map"]))}</td>'  # 상태·제목·위치
        f'<td>{esc(r.get("spot") or "")}</td><td>{esc(category_name(r["category"]))}</td><td>{esc(r.get("assignee") or "")}</td>'  # 장소·유형·담당자
        f'<td>{r.get("likes") or ""}</td><td>{"📷" if r.get("has_photo") else ""}</td></tr>' for r in rows)  # 공감 수·사진 여부
    q("#reportTable").innerHTML = head + f"<tbody>{body or '<tr><td colspan=11 class=t-empty>조건에 맞는 신고가 없어요</td></tr>'}</tbody>"  # 표를 넣는다 (없으면 안내)


for sel in ("#fStatus", "#fKind", "#fSeverity", "#fBuilding"):  # 거르기 선택 칸마다
    on(q(sel), "change", lambda e: render_table())  # 바꾸면 표를 다시 그린다
on(q("#fSearch"), "input", lambda e: render_table())  # 검색어를 칠 때마다 표를 다시 그린다
on(q("#reportTable"), "click", lambda e: open_detail(closest(e, "tr[data-id]").dataset.id) if closest(e, "tr[data-id]") else None)  # 표의 줄을 누르면 자세히 보기


def csv_cell(v):  # CSV 칸 값을 안전하게 만드는 함수
    """엑셀이 =, +, -, @ 로 시작하는 칸을 수식으로 실행하지 않게 앞에 ' 를 붙인다 (학생이 쓴 글이 들어가므로)."""  # 이 함수가 하는 일을 적은 설명글
    s = str(v if v is not None else "")  # 글자로 바꾼다
    return "'" + s if s.lstrip()[:1] in ("=", "+", "-", "@") else s  # 위험한 첫 글자면 ' 를 붙인다


def export_csv(e):  # CSV 내려받기 버튼을 눌렀을 때
    buf = io.StringIO()  # 글자를 모을 곳
    w = csv.writer(buf)  # CSV 쓰기 도구
    w.writerow(["접수일시", "종류", "위험도", "상태", "제목", "위치", "정확한 장소", "유형", "내용", "신고자", "담당자", "처리일시", "사진", "나도 봤어요"])  # 제목 줄
    for r in state["rows"]:  # 신고마다
        w.writerow(csv_cell(c) for c in [fmt_time(r["created_at"]), KINDS[kind_of(r)][0], SEVERITIES.get(r["severity"], ("",))[0], STATUSES.get(r["status"], r["status"]),  # 접수일시·종류·위험도·상태
                    r["title"], place_name(r["map"]), r.get("spot") or "", category_name(r["category"]),  # 제목·위치·장소·유형
                    r.get("description") or "", r.get("reporter") or "", r.get("assignee") or "",  # 내용·신고자·담당자
                    fmt_time(r.get("resolved_at")) if r.get("resolved_at") else "", "있음" if r.get("has_photo") else "", r.get("likes") or 0])  # 처리일시·사진·공감 수
    # ﻿: 엑셀에서 한글이 깨지지 않게
    download(f"위험불편신고_{datetime.now(KST):%Y%m%d}.csv", "﻿" + buf.getvalue(), "text/csv")  # 오늘 날짜 이름으로 내려받는다


on(q("#btnCsv"), "click", export_csv)  # CSV 버튼 연결


# ── 지도 탭 ──────────────────────────────────────
tmap = PlanViewer(q("#tmap"))  # 지도 탭의 도면 뷰어
tmap.on_view_change = tmap.scale_markers  # 확대·이동하면 핀 크기를 맞춘다
q("#mBuilding").innerHTML = f'<option value="{SITE_ID}">🏫 캠퍼스 전체</option>' + "".join(  # 건물 고르기 선택지
    f'<option value="{b.id}">{esc(b.name)} ({esc(b.dong)})</option>' if b.dong else f'<option value="{b.id}">{esc(b.name)}</option>'  # "덕린관 (2동)" 처럼
    for b in BUILDINGS)  # 건물마다


async def load_map(map_id):  # 지도 탭에 그 곳의 도면을 보여주는 함수
    state["map"] = map_id  # 지금 지도 위치
    hit = FLOOR_INDEX.get(map_id)  # 층이면 (건물, 층)
    q("#mBuilding").value = hit[0].id if hit else SITE_ID  # 건물 선택 칸을 맞춘다
    q("#mFloors").innerHTML = "".join(  # 층 버튼들
        f'<button data-mfloor="{f.id}" aria-selected="{str(f.id == map_id).lower()}">{esc(f.name)}</button>'  # 층 버튼 (지금 층 선택 표시)
        for f in hit[0].floors) if hit else ""  # 그 건물의 층마다 (캠퍼스면 없음)
    if state["map_loaded"] != map_id:  # 다른 도면이면
        state["map_loaded"] = map_id  # 기록하고
        try:  # 불러와 본다
            if not await tmap.load(plan_of(map_id)[0], locked=map_id == SITE_ID, crop=plan_of(map_id)[1]):  # 도면을 불러온다 (캠퍼스는 고정)
                return  # 그 사이 다른 곳을 골랐으면 그만
        except Exception as e:  # 실패하면
            toast(str(e))  # 안내
            return  # 끝
    draw_map_pins()  # 핀을 그린다


def draw_map_pins():  # 지도 탭에 핀을 그리는 함수
    map_id = state["map"]  # 지금 지도 위치
    rows = [r for r in state["rows"] if r["map"] == map_id and (is_open(r) or not q("#mOnlyOpen").checked)]  # 그 곳의 신고 ("처리 전만" 체크하면 처리 전만)
    if map_id == SITE_ID:  # 캠퍼스면
        counts = {}  # 건물별 처리 전 신고 수
        for r in state["rows"]:  # 신고마다
            b = building_of(r["map"])  # 그 신고의 건물
            if b and is_open(r):  # 건물이 있고 처리 전이면
                counts[b.id] = counts.get(b.id, 0) + 1  # 수 +1
        tmap.draw_buildings(counts)  # 건물과 신고 수를 그린다
    else:  # 층이면
        tmap.clear_overlay()  # 건물 표시를 지운다
    tmap.draw_pins(rows, state["sel"])  # 핀을 그린다


def on_mbuilding(e):  # 건물 선택 칸을 바꿨을 때
    bid = q("#mBuilding").value  # 고른 건물
    asyncio.ensure_future(load_map(SITE_ID if bid == SITE_ID else BUILDING_BY_ID[bid].default_floor.id))  # 캠퍼스 또는 그 건물 1층을 보여준다


on(q("#mBuilding"), "change", on_mbuilding)  # 건물 선택 연결
on(q("#mFloors"), "click", lambda e: asyncio.ensure_future(load_map(closest(e, "[data-mfloor]").dataset.mfloor))  # 층 버튼을 누르면 그 층으로
   if closest(e, "[data-mfloor]") else None)  # 층 버튼이 아니면 아무것도 안 함
on(q("#mOnlyOpen"), "change", lambda e: draw_map_pins())  # "처리 전만" 체크를 바꾸면 핀을 다시 그린다


def on_tmap_tap(x, y, target):  # 지도 탭의 도면을 눌렀을 때
    pin = target.closest(".pin") if hasattr(target, "closest") else None  # 핀을 눌렀는지
    if pin:  # 핀이면
        open_detail(pin.dataset.id)  # 자세히 보기
        return  # 끝
    if state["map"] == SITE_ID:  # 캠퍼스에서 눌렀으면
        from campus import building_at  # 건물 찾기 함수
        b = building_at(x, y)  # 누른 곳의 건물
        if b:  # 건물이면
            asyncio.ensure_future(load_map(b.default_floor.id))  # 그 건물 1층으로


tmap.on_tap = on_tmap_tap  # 지도 누르기 연결


# ── 신고 상세 · 처리 ──────────────────────────────
dlg = q("#detailDialog")  # 신고 자세히 보기 창
mini = PlanViewer(q("#miniMap"))  # 창 안의 작은 지도
mini.on_view_change = mini.scale_markers  # 작은 지도도 핀 크기를 맞춘다
q("#dStatus").innerHTML = "".join(f'<button type="button" data-v="{k}">{esc(v)}</button>' for k, v in STATUSES.items())  # 상태 바꾸기 버튼들 (접수·처리중·완료·반려)


def open_detail(rid):  # 신고 자세히 보기를 여는 함수
    asyncio.ensure_future(_open_detail(rid))  # 실제 작업은 아래 async 함수가 한다


async def _open_detail(rid):  # 신고 자세히 보기 창을 채우고 여는 함수
    r = await safe(store.get(rid))  # 신고 하나 (사진 포함)
    if not r or r is True:  # 없으면
        toast("신고를 찾을 수 없어요")  # 안내
        return  # 끝
    state["sel"] = rid  # 선택한 신고
    state["detail"] = r  # 자세히 볼 신고
    state["new_status"] = None  # 새 상태는 아직 안 고름
    render_table()  # 표에서 강조
    if state["tab"] == "map":  # 지도 탭이면
        draw_map_pins()  # 지도에서도 강조
    q("#dHead").innerHTML = (f'<p class="eyebrow">{kind_badge(r)} {severity_badge(r["severity"])} · {esc(category_name(r["category"]))} · '  # 종류·위험도·유형
                             f'{status_badge(r["status"])}</p><h2>{esc(r["title"])}</h2>')  # 상태·제목
    rows = [("위치", place_name(r["map"])), ("정확한 장소", r.get("spot")), ("신고자", r.get("reporter") or "이름 안 적음"),  # 보여줄 정보: 위치·장소·신고자
            ("구글 계정", r.get("reporter_email")),  # 신고한 구글 계정 (선생님만 봄)
            ("신고 일시", fmt_time(r["created_at"])), ("담당자", r.get("assignee")),  # 신고 일시·담당자
            ("처리 일시", fmt_time(r["resolved_at"]) if r.get("resolved_at") else None)]  # 처리 일시
    info = "".join(f"<dt>{k}</dt><dd>{esc(v)}</dd>" for k, v in rows if v)  # 값이 있는 것만 이름-값 줄로
    desc = f'<p class="detail-desc">{esc(r["description"])}</p>' if r.get("description") else ""  # 내용 (있으면)
    photo = f'<img class="detail-photo" src="{esc(r["photo"])}" alt="신고 사진" />' if r.get("photo") else ""  # 사진 (있으면)
    q("#dInfo").innerHTML = f'{desc}<dl class="detail-grid">{info}</dl>{photo}'  # 창에 넣는다
    q("#miniCap").textContent = f"{place_name(r['map'])} 위치"  # 작은 지도 설명
    q("#dNote").value = ""  # 상태 변경 메모 칸 비우기
    q("#dMemo").value = ""  # 메모 칸 비우기
    q("#dAssignee").value = r.get("assignee") or ""  # 담당자 칸에 지금 담당자
    for b in qa("#dStatus button"):  # 상태 버튼마다
        b.setAttribute("aria-pressed", str(b.dataset.v == r["status"]).lower())  # 지금 상태만 눌림 표시
    q("#dStatusSave").disabled = True  # 상태 저장 버튼은 다른 상태를 고르기 전까지 잠근다
    await render_events(rid)  # 처리 기록을 그린다
    await render_abuse(r)  # 장난 신고 막기 칸을 그린다
    if not dlg.open:  # 창이 안 열렸으면
        dlg.showModal()  # 연다
    # 작은 지도: 신고 위치를 확대해서 보여준다
    if await mini.load(plan_of(r["map"])[0], crop=plan_of(r["map"])[1]):  # 그 층 도면을 불러오면
        mini.draw_pins([r], rid)  # 핀을 그리고
        mini.focus(r["x"], r["y"] - 8, min(mini.size[0], 260))  # 핀을 가운데에 크게


async def render_events(rid):  # 처리 기록을 그리는 함수
    evs = await safe(store.list_events(rid)) or []  # 기록 목록
    icons = {"status": "🔄", "assign": "👤", "memo": "📝"}  # 기록 종류별 아이콘
    q("#dEvents").innerHTML = "".join(  # 기록 줄들
        f'<li><b>{icons.get(e["kind"], "•")} {esc(e["body"])}</b><span>{esc(e["actor"])} · {fmt_time(e["created_at"])}</span></li>'  # 아이콘·내용·처리한 선생님·시각
        for e in (evs if isinstance(evs, list) else [])) or '<li class="t-empty">아직 기록이 없어요</li>'  # 없으면 안내


def abuse_key(r):  # 막을 대상을 정하는 함수
    """장난 신고를 막을 대상: 구글 계정으로 신고했으면 그 계정, 아니면 기기."""  # 이 함수가 하는 일을 적은 설명글
    if r.get("reporter_uid"):  # 구글 계정으로 신고했으면
        return "reporter_uid", r["reporter_uid"]  # 그 계정
    return "device", r.get("device")  # 아니면 기기


async def render_abuse(r):  # 장난 신고 막기 칸을 그리는 함수
    """장난 신고 막기: 같은 기기에서 온 신고 수, 차단 상태, 차단/해제 버튼."""  # 이 함수가 하는 일을 적은 설명글
    box = q("#dAbuse")  # 장난 신고 막기 칸
    key, dev = abuse_key(r)  # 막을 대상
    if not dev:  # 대상이 없으면
        box.innerHTML = ""  # 비운다
        return  # 끝
    same = [x for x in state["rows"] if x.get(key) == dev]  # 같은 계정(기기)에서 온 신고들
    rejected = sum(1 for x in same if x["status"] == "rejected")  # 그중 반려된 수
    blocked = await safe(store.is_blocked(dev))  # 이미 차단됐는지
    blocked = blocked is True  # 확실히 True 일 때만 차단
    state["blocked"] = blocked  # 저장
    who_txt = "이 계정" if key == "reporter_uid" else "이 기기"  # 안내에 쓸 말
    info = f"{who_txt}으로 온 신고 {len(same)}건" + (f" · 반려 {rejected}건" if rejected else "")  # 신고 수·반려 수 안내
    btn = (f'<button class="btn btn-quiet" type="button" data-abuse="unblock">✅ {who_txt} 차단 풀기</button>' if blocked else  # 차단됐으면 풀기 버튼
           f'<button class="btn-text-danger" type="button" data-abuse="block">🚫 장난 신고로 반려 + {who_txt} 신고 막기</button>')  # 아니면 막기 버튼
    box.innerHTML = (f'<h4>장난 신고 막기</h4><p class="t-count">{esc(info)} · '  # 제목과 안내
                     f'{"<b class=blocked>차단됨</b>" if blocked else "정상"}</p>{btn}')  # 상태와 버튼


async def on_abuse(e):  # 막기/풀기 버튼을 눌렀을 때
    b = closest(e, "button[data-abuse]")  # 누른 버튼
    r = state["detail"]  # 지금 보는 신고
    if not b or not r:  # 없으면
        return  # 끝
    key, target = abuse_key(r)  # 막을 대상
    if not target:  # 대상이 없으면
        return  # 끝
    who_txt = "이 계정" if key == "reporter_uid" else "이 기기"  # 안내에 쓸 말
    if b.dataset.abuse == "block":  # 막기 버튼이면
        tip = ("" if key == "reporter_uid" else  # 계정이면 추가 안내 없음
               "\n(기기 차단은 브라우저 기록을 지우면 풀려서, 생활지도와 함께 쓰세요)")  # 기기면 한계 안내
        if not window.confirm(f"이 신고를 '장난 신고'로 반려하고, {who_txt}으로 더는 신고하지 못하게 막을까요?{tip}"):  # 정말 할지 물어본다
            return  # 취소하면 끝
        if r["status"] != "rejected":  # 아직 반려가 아니면
            await safe(store.update(r["id"], {"status": "rejected",  # 반려로 바꾸고
                                              "resolved_at": datetime.now(timezone.utc).isoformat()}))  # 처리 시각을 적는다
        reason = f"장난 신고: {r['title'][:40]}" + (f" ({r['reporter_email']})" if r.get("reporter_email") else "")  # 차단 이유 (제목·계정)
        if await safe(store.block(target, reason[:100], who())):  # 차단 목록에 넣고 성공하면
            await safe(store.add_event(r["id"], "status", f"장난 신고로 반려 · {who_txt} 신고 막음", who()),  # 처리 기록을 남긴다
                       f"반려하고 {who_txt}의 신고를 막았어요")  # 안내
    else:  # 풀기 버튼이면
        if not window.confirm(f"{who_txt}의 신고 막기를 풀까요?"):  # 정말 할지 물어본다
            return  # 취소하면 끝
        if await safe(store.unblock(target)):  # 차단을 풀고 성공하면
            await safe(store.add_event(r["id"], "memo", f"{who_txt} 신고 막기를 풀었어요", who()), "차단을 풀었어요")  # 기록과 안내
    await reload()  # 목록을 새로 받는다
    await _open_detail(r["id"])  # 창을 다시 채운다


def on_status_pick(e):  # 상태 버튼을 골랐을 때
    b = closest(e, "button[data-v]")  # 누른 상태 버튼
    if not b or not state["detail"]:  # 없으면
        return  # 끝
    state["new_status"] = b.dataset.v  # 새 상태 저장
    for x in qa("#dStatus button"):  # 상태 버튼마다
        x.setAttribute("aria-pressed", str(x == b).lower())  # 누른 것만 표시
    q("#dStatusSave").disabled = b.dataset.v == state["detail"]["status"]  # 지금 상태와 같으면 저장 버튼 잠금


async def on_status_save(e):  # 상태 저장 버튼을 눌렀을 때
    r, st = state["detail"], state["new_status"]  # 신고와 새 상태
    if not r or not st or st == r["status"]:  # 바꿀 게 없으면
        return  # 끝
    patch = {"status": st, "resolved_at": datetime.now(timezone.utc).isoformat() if st in ("done", "rejected") else None}  # 새 상태 (완료·반려면 처리 시각도)
    note = str(q("#dNote").value).strip()  # 상태 변경 메모
    if await safe(store.update(r["id"], patch)):  # 저장에 성공하면
        await safe(store.add_event(r["id"], "status", f"상태 → {STATUSES[st]}" + (f" · {note}" if note else ""), who()),  # 처리 기록을 남기고
                   f"'{STATUSES[st]}'(으)로 바꿨어요")  # 안내
        await reload()  # 목록을 새로 받는다
        await _open_detail(r["id"])  # 창을 다시 채운다


async def on_assignee_save(e):  # 담당자 저장 버튼을 눌렀을 때
    r = state["detail"]  # 신고
    name = str(q("#dAssignee").value).strip()  # 적은 담당자
    if not r or name == (r.get("assignee") or ""):  # 바뀐 게 없으면
        return  # 끝
    if await safe(store.update(r["id"], {"assignee": name})):  # 담당자를 저장하고 성공하면
        await safe(store.add_event(r["id"], "assign", f"담당자 → {name or '없음'}", who()), "담당자를 저장했어요")  # 기록과 안내
        await reload()  # 목록을 새로 받는다
        await _open_detail(r["id"])  # 창을 다시 채운다


async def on_memo_save(e):  # 메모 저장 버튼을 눌렀을 때
    r = state["detail"]  # 신고
    memo = str(q("#dMemo").value).strip()  # 적은 메모
    if r and memo:  # 메모가 있으면
        await safe(store.add_event(r["id"], "memo", memo, who()), "메모를 남겼어요")  # 처리 기록으로 남긴다
        q("#dMemo").value = ""  # 칸을 비운다
        await render_events(r["id"])  # 기록을 다시 그린다


async def on_delete(e):  # 삭제 버튼을 눌렀을 때
    r = state["detail"]  # 신고
    if not r or not window.confirm("이 신고를 삭제할까요? 되돌릴 수 없어요.\n(장난·중복 신고는 보통 '반려'로 처리하는 걸 권해요)"):  # 정말 지울지 물어본다
        return  # 취소하면 끝
    if await safe(store.delete(r["id"]), "삭제했어요"):  # 지우고 성공하면
        dlg.close()  # 창을 닫는다
        state["sel"] = state["detail"] = None  # 선택을 비운다
        await reload()  # 목록을 새로 받는다


on(q("#dStatus"), "click", on_status_pick)  # 상태 버튼 연결
on(q("#dStatusSave"), "click", on_status_save)  # 상태 저장 연결
on(q("#dAssigneeSave"), "click", on_assignee_save)  # 담당자 저장 연결
on(q("#dMemoSave"), "click", on_memo_save)  # 메모 저장 연결
on(q("#dDelete"), "click", on_delete)  # 삭제 연결
on(q("#dAbuse"), "click", on_abuse)  # 장난 신고 막기 연결
on(dlg.querySelector("[data-close]"), "click", lambda e: dlg.close())  # 창 X 버튼
on(dlg, "click", lambda e: dlg.close() if e.target == dlg else None)  # 창 바깥을 누르면 닫기


# ── 시작 ─────────────────────────────────────────
if who() and store.logged_in:  # 이미 로그인돼 있으면 (로그인 유지)
    await enter()  # 바로 관리 화면으로
else:  # 아니면
    show_login()  # 로그인 화면
hide_loading()  # 준비 화면을 없앤다
