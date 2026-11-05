# 신고 저장소
# - config.py 가 비어 있으면 체험 모드: 이 브라우저(localStorage)에만 저장
# - Supabase 주소/키를 넣으면 공용 모드: 모든 학생·선생님이 같은 신고를 본다
import json
import uuid

from js import window
from pyodide.http import pyfetch

import config
from common import now_iso

SHARED = bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY)

# 학생 화면에 보여줘도 되는 칸 (신고자 이름·사진·담당자는 선생님만)
PUBLIC_FIELDS = ("id", "created_at", "map", "x", "y", "kind", "category", "severity", "title", "spot", "status")
REPORT_FIELDS = PUBLIC_FIELDS + ("updated_at", "resolved_at", "description", "reporter", "photo", "assignee")


class StoreError(Exception):
    pass


class LocalStore:
    """체험 모드: 브라우저 localStorage 에 JSON 으로 저장."""
    KEY_R = "kd-safety-v2-reports"
    KEY_E = "kd-safety-v2-events"
    shared = False

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

    # 학생
    async def list_public(self, map_id=None):
        rows = [{k: r.get(k) for k in PUBLIC_FIELDS} for r in self._load(self.KEY_R)]
        return [r for r in rows if not map_id or r["map"] == map_id]

    async def add(self, report):
        rows = self._load(self.KEY_R)
        r = {k: None for k in REPORT_FIELDS} | report | {"id": str(uuid.uuid4()), "created_at": now_iso(), "status": "new"}
        rows.insert(0, r)
        self._save(self.KEY_R, rows)
        return r["id"]

    # 선생님
    async def login(self, email, password):
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


class SupabaseStore:
    """공용 모드: Supabase(PostgreSQL) REST API. 권한은 tools/supabase_setup.py 의 규칙(RLS)이 지킨다."""
    shared = True
    TOKEN_KEY = "kd-safety-teacher-token"

    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key

    @property
    def token(self):
        return window.sessionStorage.getItem(self.TOKEN_KEY)

    @property
    def logged_in(self):
        return bool(self.token)

    async def _req(self, method, path, body=None, auth=False, prefer=None):
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.token if auth and self.token else self.key}",
                   "Content-Type": "application/json"}
        if prefer:
            headers["Prefer"] = prefer
        res = await pyfetch(self.url + path, method=method, headers=headers,
                            body=json.dumps(body, ensure_ascii=False) if body is not None else None)
        if res.status == 401 and auth:
            self.logout()
            raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")
        if not res.ok:
            raise StoreError(f"서버 오류 ({res.status}): {(await res.string())[:200]}")
        text = await res.string()
        return json.loads(text) if text else None

    # 학생
    async def list_public(self, map_id=None):
        path = "/rest/v1/public_reports?select=*&order=created_at.desc"
        if map_id:
            path += f"&map=eq.{map_id}"
        return await self._req("GET", path)

    async def add(self, report):
        rid = str(uuid.uuid4())
        await self._req("POST", "/rest/v1/reports", report | {"id": rid}, prefer="return=minimal")
        return rid

    # 선생님
    async def login(self, email, password):
        res = await pyfetch(self.url + "/auth/v1/token?grant_type=password", method="POST",
                            headers={"apikey": self.key, "Content-Type": "application/json"},
                            body=json.dumps({"email": email, "password": password}))
        if not res.ok:
            return False
        window.sessionStorage.setItem(self.TOKEN_KEY, (await res.json())["access_token"])
        return True

    def logout(self):
        window.sessionStorage.removeItem(self.TOKEN_KEY)

    async def list_all(self):
        cols = ",".join(f for f in REPORT_FIELDS if f != "photo") + ",has_photo"
        return await self._req("GET", f"/rest/v1/reports?select={cols}&order=created_at.desc", auth=True)

    async def get(self, rid):
        rows = await self._req("GET", f"/rest/v1/reports?select=*&id=eq.{rid}", auth=True)
        return rows[0] if rows else None

    async def update(self, rid, patch):
        await self._req("PATCH", f"/rest/v1/reports?id=eq.{rid}", patch | {"updated_at": now_iso()}, auth=True,
                        prefer="return=minimal")

    async def list_events(self, rid):
        return await self._req("GET", f"/rest/v1/report_events?select=*&report_id=eq.{rid}&order=created_at.desc", auth=True)

    async def add_event(self, rid, kind, body, actor):
        await self._req("POST", "/rest/v1/report_events",
                        {"report_id": rid, "kind": kind, "body": body, "actor": actor}, auth=True, prefer="return=minimal")

    async def delete(self, rid):
        await self._req("DELETE", f"/rest/v1/reports?id=eq.{rid}", auth=True)


store = SupabaseStore(config.SUPABASE_URL, config.SUPABASE_ANON_KEY) if SHARED else LocalStore()
