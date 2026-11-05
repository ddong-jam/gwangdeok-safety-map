# 신고 저장소
# - config.py 가 비어 있으면 체험 모드: 이 브라우저(localStorage)에만 저장
# - Supabase 주소/키를 넣으면 공용 모드: 모든 학생·선생님이 같은 신고를 본다
import json
import time
import uuid

from js import window
from pyodide.http import pyfetch

import config
import guard
from common import now_iso

SHARED = bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY)
STUDENT_LOGIN = bool(getattr(config, "STUDENT_LOGIN", False))
SCHOOL_DOMAIN = (getattr(config, "SCHOOL_EMAIL_DOMAIN", "") or "").strip().lstrip("@").lower()
KEEP_DAYS = 14          # 선생님 '이 기기에서 로그인 유지' 기간
STUDENT_KEEP_DAYS = 30  # 학생 구글 로그인 유지 기간 (학생 폰)

# 학생 화면에 보여줘도 되는 칸 (신고자 이름·계정·사진·담당자·기기는 선생님만)
PUBLIC_FIELDS = ("id", "created_at", "map", "x", "y", "kind", "category", "severity", "title", "spot", "status")
REPORT_FIELDS = PUBLIC_FIELDS + ("updated_at", "resolved_at", "description", "reporter", "photo", "assignee", "device",
                                 "reporter_uid", "reporter_email")


class StoreError(Exception):
    pass


def _get(storage, key):
    try:
        return getattr(window, storage).getItem(key)
    except Exception:
        return None


def _set(storage, key, value):
    try:
        if value is None:
            getattr(window, storage).removeItem(key)
        else:
            getattr(window, storage).setItem(key, value)
    except Exception:
        pass


_device = None


def device_id():
    """이 기기(브라우저)를 구분하는 무작위 번호. 장난 신고를 막을 때 쓴다 (이름·IP 같은 개인정보 아님)."""
    global _device
    if not _device:
        _device = _get("localStorage", "kd-safety-device")
        if not _device:
            _device = str(uuid.uuid4())
            _set("localStorage", "kd-safety-device", _device)
    return _device


def domain_ok(email):
    return not SCHOOL_DOMAIN or (email or "").lower().endswith("@" + SCHOOL_DOMAIN)


def domain_message():
    return f"학교 구글 계정(@{SCHOOL_DOMAIN})으로 로그인해 주세요."


class Session:
    """로그인 정보 하나 (선생님 또는 학생). keep=True 면 이 기기(localStorage)에 days 일 동안 둔다."""

    def __init__(self, key):
        self.key = key

    def get(self):
        for storage in ("sessionStorage", "localStorage"):
            raw = _get(storage, self.key)
            if raw:
                try:
                    s = json.loads(raw)
                except Exception:
                    continue
                if s.get("keep_until", 0) and s["keep_until"] < time.time():
                    _set(storage, self.key, None)  # 유지 기간이 끝났다
                    return None
                return s
        return None

    def save(self, s, keep, days):
        old = self.get()
        s = dict(s, keep=keep, keep_until=time.time() + days * 86400 if keep else 0)
        if old and old.get("keep") and keep:  # 유지 기간은 처음 로그인한 때부터 센다
            s["keep_until"] = old["keep_until"]
        self.clear()
        _set("localStorage" if keep else "sessionStorage", self.key, json.dumps(s, ensure_ascii=False))

    def clear(self):
        _set("sessionStorage", self.key, None)
        _set("localStorage", self.key, None)


class LocalStore:
    """체험 모드: 브라우저 localStorage 에 JSON 으로 저장. 공용 모드의 데이터베이스 규칙을 흉내 낸다."""
    KEY_R = "kd-safety-v2-reports"
    KEY_E = "kd-safety-v2-events"
    KEY_B = "kd-safety-v2-blocked"
    shared = False

    def __init__(self):
        self.student_session = Session("kd-safety-demo-student")

    def _load(self, key):
        try:
            return json.loads(window.localStorage.getItem(key) or "[]")
        except Exception:
            return []

    def _save(self, key, data):
        try:
            window.localStorage.setItem(key, json.dumps(data, ensure_ascii=False))
        except Exception:
            raise StoreError("브라우저 저장 공간이 부족해요. 사진이 있는 오래된 신고를 정리해 주세요.")

    # 학생 로그인 (체험: 진짜 구글 대신 이름만 받는다)
    @property
    def student(self):
        return self.student_session.get()

    async def student_login(self, name="체험 학생"):
        uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))
        self.student_session.save({"uid": uid, "email": f"{uid[:8]}@demo.student", "name": name}, True, STUDENT_KEEP_DAYS)
        return True

    def student_logout(self):
        self.student_session.clear()

    # 학생
    async def list_public(self, map_id=None):
        rows = [{k: r.get(k) for k in PUBLIC_FIELDS} for r in self._load(self.KEY_R)]
        return [r for r in rows if not map_id or r["map"] == map_id]

    async def add(self, report):
        rows = self._load(self.KEY_R)
        st = self.student
        if STUDENT_LOGIN and not st:
            raise StoreError("로그인한 뒤에 신고할 수 있어요.")
        report = report | {"device": device_id(), "reporter_uid": st["uid"] if st else None,
                           "reporter_email": st["email"] if st else None}
        if any(b["device"] in (report["device"], report["reporter_uid"]) for b in self._load(self.KEY_B)):
            raise StoreError(guard.MESSAGES["blocked"])
        err = guard.check_text(report.get("title"), report.get("description"), report.get("spot"),
                               report.get("reporter")) or guard.check_rate(rows, report)
        if err:
            raise StoreError(err)
        r = {k: None for k in REPORT_FIELDS} | report | {"id": str(uuid.uuid4()), "created_at": now_iso(), "status": "new"}
        rows.insert(0, r)
        self._save(self.KEY_R, rows)
        return r["id"]

    # 선생님
    async def login(self, email, password, keep=False):
        return True

    def logout(self):
        pass

    @property
    def logged_in(self):
        return True

    async def list_all(self):
        rows = self._load(self.KEY_R)
        return [{k: v for k, v in r.items() if k != "photo"} | {"has_photo": bool(r.get("photo"))} for r in rows]

    async def get(self, rid):
        return next((r for r in self._load(self.KEY_R) if r["id"] == rid), None)

    async def update(self, rid, patch):
        rows = self._load(self.KEY_R)
        for r in rows:
            if r["id"] == rid:
                r.update(patch, updated_at=now_iso())
        self._save(self.KEY_R, rows)

    async def list_events(self, rid):
        return [e for e in self._load(self.KEY_E) if e["report_id"] == rid]

    async def add_event(self, rid, kind, body, actor):
        evs = self._load(self.KEY_E)
        evs.insert(0, {"report_id": rid, "kind": kind, "body": body, "actor": actor, "created_at": now_iso()})
        self._save(self.KEY_E, evs)

    async def delete(self, rid):
        self._save(self.KEY_R, [r for r in self._load(self.KEY_R) if r["id"] != rid])
        self._save(self.KEY_E, [e for e in self._load(self.KEY_E) if e["report_id"] != rid])

    # 막기: device 칸에 기기 번호 또는 학생 계정 번호(uid)를 넣는다
    async def is_blocked(self, key):
        return any(b["device"] == key for b in self._load(self.KEY_B))

    async def block(self, key, reason, actor):
        rows = [b for b in self._load(self.KEY_B) if b["device"] != key]
        rows.insert(0, {"device": key, "reason": reason, "blocked_by": actor, "created_at": now_iso()})
        self._save(self.KEY_B, rows)

    async def unblock(self, key):
        self._save(self.KEY_B, [b for b in self._load(self.KEY_B) if b["device"] != key])


class SupabaseStore:
    """공용 모드: Supabase(PostgreSQL) REST API. 권한과 장난 신고 막기는 tools/supabase_setup.py 의 규칙이 지킨다.

    선생님: 이메일·비밀번호 로그인. 학생: 구글 로그인 (Supabase 가 구글과 연결해 준다).
    접속 토큰(1시간)이 끝나기 전에 갱신 토큰으로 자동으로 새로 받는다.
    """
    shared = True

    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key
        self.teacher_session = Session("kd-safety-teacher-session")
        self.student_session = Session("kd-safety-student-session")

    # ── 토큰 ──
    def _session_data(self, data, extra=None):
        return {"access_token": data["access_token"], "refresh_token": data["refresh_token"],
                "expires_at": time.time() + int(data.get("expires_in", 3600))} | (extra or {})

    async def _token(self, sess, days):
        s = sess.get()
        if not s:
            return None
        if s["expires_at"] - time.time() < 120:  # 2분 안에 끝나면 미리 새로 받는다
            res = await pyfetch(self.url + "/auth/v1/token?grant_type=refresh_token", method="POST",
                                headers={"apikey": self.key, "Content-Type": "application/json"},
                                body=json.dumps({"refresh_token": s["refresh_token"]}))
            if not res.ok:
                sess.clear()
                return None
            keep = {k: s[k] for k in ("uid", "email", "name") if k in s}
            sess.save(self._session_data(await res.json(), keep), s.get("keep", False), days)
            s = sess.get()
        return s["access_token"]

    async def _req(self, method, path, body=None, auth=None, prefer=None):
        """auth: None(학생·익명 공개 키) | "teacher" | "student" """
        token = None
        if auth == "teacher":
            token = await self._token(self.teacher_session, KEEP_DAYS)
            if not token:
                raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")
        elif auth == "student":
            token = await self._token(self.student_session, STUDENT_KEEP_DAYS)
            if not token:
                raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")
        headers = {"apikey": self.key, "Authorization": f"Bearer {token or self.key}", "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        res = await pyfetch(self.url + path, method=method, headers=headers,
                            body=json.dumps(body, ensure_ascii=False) if body is not None else None)
        if res.status == 401 and auth:
            (self.teacher_session if auth == "teacher" else self.student_session).clear()
            raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")
        text = await res.string()
        if not res.ok:
            # 데이터베이스 규칙(check_report)이 막으면 '신고: …' 메시지를 그대로 보여준다
            try:
                msg = json.loads(text).get("message", "")
            except Exception:
                msg = ""
            if msg.startswith("신고: "):
                raise StoreError(msg[4:])
            raise StoreError(f"서버 오류 ({res.status}). 잠시 뒤 다시 해 주세요.")
        return json.loads(text) if text else None

    # ── 학생 구글 로그인 ──
    @property
    def student(self):
        return self.student_session.get()

    def google_url(self, back_to):
        """구글 로그인 화면 주소. 로그인하면 back_to#access_token=... 으로 돌아온다."""
        enc = window.encodeURIComponent
        url = f"{self.url}/auth/v1/authorize?provider=google&redirect_to={enc(back_to)}"
        if SCHOOL_DOMAIN:
            url += f"&hd={enc(SCHOOL_DOMAIN)}"  # 구글 화면에서 학교 계정을 먼저 보여준다 (막는 건 서버가 한다)
        return url + "&prompt=select_account"

    async def finish_google(self, fragment):
        """구글에서 돌아온 주소의 #access_token=... 을 읽어 로그인한다. 성공하면 학생 정보, 아니면 오류 메시지."""
        params = dict(p.split("=", 1) for p in fragment.lstrip("#").split("&") if "=" in p)
        if "error" in params:
            return window.decodeURIComponent(params.get("error_description", "로그인을 취소했어요").replace("+", " "))
        if "access_token" not in params:
            return "로그인하지 못했어요."
        res = await pyfetch(self.url + "/auth/v1/user", headers={"apikey": self.key,
                                                                 "Authorization": f"Bearer {params['access_token']}"})
        if not res.ok:
            return "로그인하지 못했어요."
        user = await res.json()
        email = user.get("email") or ""
        if not domain_ok(email):
            return domain_message()
        meta = user.get("user_metadata") or {}
        self.student_session.save(self._session_data(params, {
            "uid": user["id"], "email": email, "name": meta.get("full_name") or meta.get("name") or ""}),
            True, STUDENT_KEEP_DAYS)
        return None

    def student_logout(self):
        s = self.student_session.get()
        if s:
            self._remote_logout(s["access_token"])
        self.student_session.clear()

    def _remote_logout(self, token):
        """서버에서도 이 로그인(갱신 토큰)을 없앤다."""
        from js import Object, fetch
        from pyodide.ffi import to_js
        fetch(self.url + "/auth/v1/logout", to_js({"method": "POST", "headers": {
            "apikey": self.key, "Authorization": f"Bearer {token}"}}, dict_converter=Object.fromEntries))

    # 학생
    async def list_public(self, map_id=None):
        path = "/rest/v1/public_reports?select=*&order=created_at.desc"
        if map_id:
            path += f"&map=eq.{map_id}"
        return await self._req("GET", path)

    async def add(self, report):
        if STUDENT_LOGIN and not self.student:
            raise StoreError("로그인한 뒤에 신고할 수 있어요.")
        rid = str(uuid.uuid4())
        # 신고한 계정(reporter_uid·email)은 데이터베이스가 로그인 정보로 채운다 (화면에서 속일 수 없게)
        await self._req("POST", "/rest/v1/reports", report | {"id": rid, "device": device_id()},
                        auth="student" if self.student else None, prefer="return=minimal")
        return rid

    # 선생님
    async def login(self, email, password, keep=False):
        res = await pyfetch(self.url + "/auth/v1/token?grant_type=password", method="POST",
                            headers={"apikey": self.key, "Content-Type": "application/json"},
                            body=json.dumps({"email": email, "password": password}))
        if not res.ok:
            return False
        self.teacher_session.save(self._session_data(await res.json()), keep, KEEP_DAYS)
        return True

    def logout(self):
        s = self.teacher_session.get()
        if s:
            self._remote_logout(s["access_token"])
        self.teacher_session.clear()

    @property
    def logged_in(self):
        return self.teacher_session.get() is not None

    async def list_all(self):
        cols = ",".join(f for f in REPORT_FIELDS if f != "photo") + ",has_photo"
        return await self._req("GET", f"/rest/v1/reports?select={cols}&order=created_at.desc", auth="teacher")

    async def get(self, rid):
        rows = await self._req("GET", f"/rest/v1/reports?select=*&id=eq.{rid}", auth="teacher")
        return rows[0] if rows else None

    async def update(self, rid, patch):
        await self._req("PATCH", f"/rest/v1/reports?id=eq.{rid}", patch | {"updated_at": now_iso()}, auth="teacher",
                        prefer="return=minimal")

    async def list_events(self, rid):
        return await self._req("GET", f"/rest/v1/report_events?select=*&report_id=eq.{rid}&order=created_at.desc",
                               auth="teacher")

    async def add_event(self, rid, kind, body, actor):
        await self._req("POST", "/rest/v1/report_events",
                        {"report_id": rid, "kind": kind, "body": body, "actor": actor}, auth="teacher",
                        prefer="return=minimal")

    async def delete(self, rid):
        await self._req("DELETE", f"/rest/v1/reports?id=eq.{rid}", auth="teacher")

    # 막기: device 칸에 기기 번호 또는 학생 계정 번호(uid)를 넣는다
    async def is_blocked(self, key):
        rows = await self._req("GET", f"/rest/v1/blocked_devices?select=device&device=eq.{key}", auth="teacher")
        return bool(rows)

    async def block(self, key, reason, actor):
        await self._req("POST", "/rest/v1/blocked_devices", {"device": key, "reason": reason, "blocked_by": actor},
                        auth="teacher", prefer="return=minimal,resolution=ignore-duplicates")

    async def unblock(self, key):
        await self._req("DELETE", f"/rest/v1/blocked_devices?device=eq.{key}", auth="teacher")


store = SupabaseStore(config.SUPABASE_URL, config.SUPABASE_ANON_KEY) if SHARED else LocalStore()
