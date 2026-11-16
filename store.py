# 신고 저장소
# - config.py 가 비어 있으면 체험 모드: 이 브라우저(localStorage)에만 저장
# - Supabase 주소/키를 넣으면 공용 모드: 모든 학생·선생님이 같은 신고를 본다
import json  # 파이썬 값을 글자(JSON)로 바꾸거나 되돌리는 도구
import time  # 지금 시각(초)을 얻는 도구 — 로그인 유지 기간 계산에 쓴다
import uuid  # 겹치지 않는 무작위 번호를 만드는 도구 — 신고 번호·기기 번호에 쓴다

from js import window  # 브라우저 창(저장 공간·주소 등)에 접근하는 도구
from pyodide.http import pyfetch  # 인터넷으로 서버에 요청을 보내는 도구

import config  # 설정 파일 (Supabase 주소·키, 로그인 설정)
import guard  # 장난 신고 검사 규칙
from common import now_iso  # 지금 시각을 글자로 돌려주는 함수

SHARED = bool(config.SUPABASE_URL and config.SUPABASE_ANON_KEY)  # 주소와 키가 둘 다 있으면 공용 모드
STUDENT_LOGIN = bool(getattr(config, "STUDENT_LOGIN", False))  # 학생이 신고할 때 로그인이 필요한지
SCHOOL_DOMAIN = (getattr(config, "SCHOOL_EMAIL_DOMAIN", "") or "").strip().lstrip("@").lower()  # 학교 계정 도메인 (앞의 @ 와 공백을 지우고 소문자로)
KEEP_DAYS = 14          # 선생님 '이 기기에서 로그인 유지' 기간
STUDENT_KEEP_DAYS = 30  # 학생 구글 로그인 유지 기간 (학생 폰)

# 학생 화면에 보여줘도 되는 칸 (신고자 이름·계정·사진·담당자·기기는 선생님만)
PUBLIC_FIELDS = ("id", "created_at", "map", "x", "y", "kind", "category", "severity", "title", "spot", "status")  # 공개 칸 목록
REPORT_FIELDS = PUBLIC_FIELDS + ("updated_at", "resolved_at", "description", "reporter", "photo", "assignee", "device",  # 선생님만 보는 칸까지 합친 전체 칸
                                 "reporter_uid", "reporter_email")  # 신고한 학생의 계정 번호·이메일


class StoreError(Exception):  # 저장소에서 생긴 문제를 알리는 오류 종류 (메시지를 학생에게 그대로 보여준다)
    pass  # 내용은 기본 오류와 같다


NO_NET = "서버에 연결하지 못했어요. 인터넷을 확인하고 다시 해 주세요."  # 인터넷이 끊겼을 때 안내 문구


async def _fetch(url, **kw):  # 서버에 요청을 보내는 함수
    """pyfetch 와 같지만, 인터넷이 끊겨 연결조차 못 하면 StoreError 로 알린다 (화면이 멈추지 않게)."""  # 이 함수가 하는 일을 적은 설명글
    try:  # 요청을 시도해 본다
        return await pyfetch(url, **kw)  # 서버 응답을 돌려준다
    except Exception:  # 연결 자체가 안 되면
        raise StoreError(NO_NET)  # 인터넷 확인 안내로 바꿔서 알린다


def _get(storage, key):  # 브라우저 저장 공간에서 값을 읽는 함수
    try:  # 저장 공간을 못 쓰는 브라우저도 있어서 시도해 본다
        return getattr(window, storage).getItem(key)  # sessionStorage 또는 localStorage 에서 읽는다
    except Exception:  # 실패하면
        return None  # 없음


def _set(storage, key, value):  # 브라우저 저장 공간에 값을 쓰거나 지우는 함수
    try:  # 시도해 본다
        if value is None:  # 값이 None 이면
            getattr(window, storage).removeItem(key)  # 지운다
        else:  # 값이 있으면
            getattr(window, storage).setItem(key, value)  # 저장한다
    except Exception:  # 실패해도
        pass  # 그냥 넘어간다


_device = None  # 이 기기 번호 (한 번 만든 뒤 계속 쓴다)


def device_id():  # 이 기기를 구분하는 번호를 돌려주는 함수
    """이 기기(브라우저)를 구분하는 무작위 번호. 장난 신고를 막을 때 쓴다 (이름·IP 같은 개인정보 아님)."""  # 이 함수가 하는 일을 적은 설명글
    global _device  # 위의 _device 변수를 고친다
    if not _device:  # 아직 번호를 안 읽었으면
        _device = _get("localStorage", "kd-safety-device")  # 저장해 둔 번호를 읽는다
        if not _device:  # 저장된 번호도 없으면
            _device = str(uuid.uuid4())  # 새 무작위 번호를 만든다
            _set("localStorage", "kd-safety-device", _device)  # 다음에도 쓰게 저장한다
    return _device  # 기기 번호를 돌려준다


def domain_ok(email):  # 이메일이 학교 계정 조건에 맞는지 확인하는 함수
    return not SCHOOL_DOMAIN or (email or "").lower().endswith("@" + SCHOOL_DOMAIN)  # 도메인 제한이 없거나, 학교 도메인으로 끝나면 통과


def domain_message():  # 학교 계정이 아닐 때 보여줄 문구
    return f"학교 구글 계정(@{SCHOOL_DOMAIN})으로 로그인해 주세요."  # 도메인을 넣은 안내


class Session:  # 로그인 정보를 브라우저에 보관하는 상자
    """로그인 정보 하나 (선생님 또는 학생). keep=True 면 이 기기(localStorage)에 days 일 동안 둔다."""  # 이 틀가 하는 일을 적은 설명글

    def __init__(self, key):  # 처음 만들 때
        self.key = key  # 저장 공간에서 쓸 이름

    def get(self):  # 보관한 로그인 정보를 꺼내는 함수
        for storage in ("sessionStorage", "localStorage"):  # 창을 닫으면 지워지는 곳, 계속 남는 곳 순서로 찾는다
            raw = _get(storage, self.key)  # 저장된 글자를 읽는다
            if raw:  # 있으면
                try:  # 글자를 값으로 바꿔 본다
                    s = json.loads(raw)  # JSON 글자 → 파이썬 값
                except Exception:  # 망가진 값이면
                    continue  # 다음 저장 공간을 본다
                if s.get("keep_until", 0) and s["keep_until"] < time.time():  # 유지 기간이 정해져 있고 이미 지났으면
                    _set(storage, self.key, None)  # 유지 기간이 끝났다
                    return None  # 로그인 안 된 것으로 본다
                return s  # 로그인 정보를 돌려준다
        return None  # 어디에도 없으면 None

    def save(self, s, keep, days):  # 로그인 정보를 보관하는 함수
        old = self.get()  # 이전에 보관한 정보
        s = dict(s, keep=keep, keep_until=time.time() + days * 86400 if keep else 0)  # 유지 여부와 끝나는 시각을 붙인다
        if old and old.get("keep") and keep:  # 유지 기간은 처음 로그인한 때부터 센다
            s["keep_until"] = old["keep_until"]  # 처음 정한 끝나는 시각을 그대로 쓴다
        self.clear()  # 두 저장 공간에서 옛 정보를 지운다
        _set("localStorage" if keep else "sessionStorage", self.key, json.dumps(s, ensure_ascii=False))  # 유지하면 계속 남는 곳, 아니면 창을 닫으면 지워지는 곳에 저장

    def clear(self):  # 로그인 정보를 지우는 함수 (로그아웃)
        _set("sessionStorage", self.key, None)  # 창 저장 공간에서 지운다
        _set("localStorage", self.key, None)  # 기기 저장 공간에서도 지운다


class LocalStore:  # 체험 모드 저장소
    """체험 모드: 브라우저 localStorage 에 JSON 으로 저장. 공용 모드의 데이터베이스 규칙을 흉내 낸다."""  # 이 틀가 하는 일을 적은 설명글
    KEY_R = "kd-safety-v2-reports"  # 신고 목록을 저장하는 이름
    KEY_E = "kd-safety-v2-events"  # 처리 기록을 저장하는 이름
    KEY_B = "kd-safety-v2-blocked"  # 차단 목록을 저장하는 이름
    KEY_L = "kd-safety-v2-likes"  # 공감 목록을 저장하는 이름
    shared = False  # 공용 모드가 아님

    def __init__(self):  # 처음 만들 때
        self.student_session = Session("kd-safety-demo-student")  # 체험용 학생 로그인 상자

    def _load(self, key):  # 저장된 목록을 읽는 함수
        try:  # 읽어 본다
            return json.loads(window.localStorage.getItem(key) or "[]")  # 글자를 목록으로 바꾼다 (없으면 빈 목록)
        except Exception:  # 망가졌으면
            return []  # 빈 목록

    def _save(self, key, data):  # 목록을 저장하는 함수
        try:  # 저장해 본다
            window.localStorage.setItem(key, json.dumps(data, ensure_ascii=False))  # 목록을 글자로 바꿔 저장한다
        except Exception:  # 저장 공간이 꽉 찼으면
            raise StoreError("브라우저 저장 공간이 부족해요. 사진이 있는 오래된 신고를 정리해 주세요.")  # 정리하라고 알린다

    # 학생 로그인 (체험: 진짜 구글 대신 이름만 받는다)
    @property  # 아래 함수를 값처럼 쓴다
    def student(self):  # 지금 로그인한 학생 정보
        return self.student_session.get()  # 보관한 정보를 돌려준다 (없으면 None)

    async def student_login(self, name="체험 학생"):  # 체험용 학생 로그인
        uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, name))  # 이름으로 항상 같은 계정 번호를 만든다
        self.student_session.save({"uid": uid, "email": f"{uid[:8]}@demo.student", "name": name}, True, STUDENT_KEEP_DAYS)  # 가짜 계정 정보를 30일 보관
        return True  # 성공

    def student_logout(self):  # 학생 로그아웃
        self.student_session.clear()  # 로그인 정보를 지운다

    # 학생
    async def list_public(self, map_id=None):  # 학생에게 보여줄 신고 목록
        counts = {}  # 신고별 공감 수
        for l in self._load(self.KEY_L):  # 공감을 하나씩 보면서
            counts[l["report_id"]] = counts.get(l["report_id"], 0) + 1  # 그 신고의 공감 수를 1 늘린다
        rows = [{k: r.get(k) for k in PUBLIC_FIELDS} | {"likes": counts.get(r["id"], 0)} for r in self._load(self.KEY_R)]  # 공개 칸만 골라 공감 수를 붙인다
        return [r for r in rows if not map_id or r["map"] == map_id]  # 층을 정했으면 그 층 신고만

    async def add(self, report):  # 새 신고 저장
        rows = self._load(self.KEY_R)  # 지금까지 신고들
        st = self.student  # 로그인한 학생
        if STUDENT_LOGIN and not st:  # 로그인이 필요한데 안 했으면
            raise StoreError("로그인한 뒤에 신고할 수 있어요.")  # 막는다
        report = report | {"device": device_id(), "reporter_uid": st["uid"] if st else None,  # 기기 번호·학생 계정 번호를 붙인다
                           "reporter_email": st["email"] if st else None}  # 학생 이메일도 붙인다
        if any(b["device"] in (report["device"], report["reporter_uid"]) for b in self._load(self.KEY_B)):  # 이 기기나 계정이 차단 목록에 있으면
            raise StoreError(guard.MESSAGES["blocked"])  # 신고 제한 안내
        err = guard.check_text(report.get("title"), report.get("description"), report.get("spot"),  # 글 내용 검사
                               report.get("reporter")) or guard.check_rate(rows, report)  # 통과하면 횟수 검사
        if err:  # 문제가 있으면
            raise StoreError(err)  # 그 안내를 보여준다
        r = {k: None for k in REPORT_FIELDS} | report | {"id": str(uuid.uuid4()), "created_at": now_iso(), "status": "new"}  # 빈 칸 + 신고 내용 + 번호·시각·상태 "접수"
        rows.insert(0, r)  # 목록 맨 앞에 넣는다
        self._save(self.KEY_R, rows)  # 저장한다
        return r["id"]  # 새 신고 번호를 돌려준다

    # 공감 "나도 봤어요" (데이터베이스의 toggle_like() 와 같은 규칙)
    async def my_likes(self):  # 내가 공감한 신고 번호들
        st = self.student  # 로그인한 학생
        return {l["report_id"] for l in self._load(self.KEY_L) if st and l["uid"] == st["uid"]}  # 내 계정의 공감만 모은다

    async def toggle_like(self, rid):  # 공감 누르기/취소
        st = self.student  # 로그인한 학생
        if not st:  # 로그인 안 했으면
            raise StoreError("로그인한 뒤에 공감할 수 있어요.")  # 막는다
        r = next((x for x in self._load(self.KEY_R) if x["id"] == rid), None)  # 공감할 신고를 찾는다
        if not r:  # 없으면
            raise StoreError("없어진 신고예요.")  # 알린다
        if r.get("reporter_uid") == st["uid"]:  # 내가 한 신고면
            raise StoreError("내가 한 신고에는 공감할 수 없어요.")  # 막는다
        if any(b["device"] == st["uid"] for b in self._load(self.KEY_B)):  # 차단된 계정이면
            raise StoreError(guard.MESSAGES["blocked"])  # 막는다
        likes = self._load(self.KEY_L)  # 전체 공감 목록
        mine = [l for l in likes if l["report_id"] == rid and l["uid"] == st["uid"]]  # 이 신고에 내가 누른 공감
        if mine:  # 이미 눌렀으면
            likes = [l for l in likes if l not in mine]  # 취소한다 (목록에서 뺀다)
        elif r["status"] not in ("new", "doing"):  # 처리가 끝난 신고면
            raise StoreError("처리가 끝난 신고에는 공감할 수 없어요.")  # 막는다
        else:  # 처음 누르는 거면
            likes.append({"report_id": rid, "uid": st["uid"], "created_at": now_iso()})  # 공감을 추가한다
        self._save(self.KEY_L, likes)  # 저장한다
        return {"liked": not mine, "likes": sum(1 for l in likes if l["report_id"] == rid)}  # 눌렀는지와 새 공감 수를 돌려준다

    # 선생님
    async def login(self, email, password, keep=False):  # 선생님 로그인 (체험 모드는 항상 성공)
        return True  # 성공

    def logout(self):  # 선생님 로그아웃 (체험 모드는 할 일 없음)
        pass  # 아무것도 안 한다

    @property  # 값처럼 쓴다
    def logged_in(self):  # 선생님이 로그인했는지
        return True  # 체험 모드는 항상 로그인된 것으로 본다

    async def list_all(self):  # 선생님용 전체 신고 목록
        rows = self._load(self.KEY_R)  # 모든 신고
        counts = {}  # 신고별 공감 수
        for l in self._load(self.KEY_L):  # 공감을 하나씩 보면서
            counts[l["report_id"]] = counts.get(l["report_id"], 0) + 1  # 공감 수를 센다
        return [{k: v for k, v in r.items() if k != "photo"} | {"has_photo": bool(r.get("photo")), "likes": counts.get(r["id"], 0)}  # 사진은 빼고(무거워서) 사진 여부와 공감 수를 붙인다
                for r in rows]  # 모든 신고에 대해

    async def get(self, rid):  # 신고 하나를 자세히 가져오기
        return next((r for r in self._load(self.KEY_R) if r["id"] == rid), None)  # 번호가 같은 신고 (없으면 None)

    async def update(self, rid, patch):  # 신고 내용 바꾸기 (상태·담당자 등)
        rows = self._load(self.KEY_R)  # 모든 신고
        for r in rows:  # 하나씩 보면서
            if r["id"] == rid:  # 바꿀 신고면
                r.update(patch, updated_at=now_iso())  # 바꾸고 바꾼 시각을 적는다
        self._save(self.KEY_R, rows)  # 저장한다

    async def list_events(self, rid):  # 신고 하나의 처리 기록
        return [e for e in self._load(self.KEY_E) if e["report_id"] == rid]  # 그 신고의 기록만 모은다

    async def add_event(self, rid, kind, body, actor):  # 처리 기록 남기기
        evs = self._load(self.KEY_E)  # 모든 기록
        evs.insert(0, {"report_id": rid, "kind": kind, "body": body, "actor": actor, "created_at": now_iso()})  # 새 기록을 맨 앞에 넣는다
        self._save(self.KEY_E, evs)  # 저장한다

    async def delete(self, rid):  # 신고 지우기
        self._save(self.KEY_R, [r for r in self._load(self.KEY_R) if r["id"] != rid])  # 그 신고를 뺀 목록을 저장
        self._save(self.KEY_E, [e for e in self._load(self.KEY_E) if e["report_id"] != rid])  # 그 신고의 기록도 지운다

    # 막기: device 칸에 기기 번호 또는 학생 계정 번호(uid)를 넣는다
    async def is_blocked(self, key):  # 차단됐는지 확인
        return any(b["device"] == key for b in self._load(self.KEY_B))  # 차단 목록에 있으면 True

    async def block(self, key, reason, actor):  # 차단하기
        rows = [b for b in self._load(self.KEY_B) if b["device"] != key]  # 같은 대상이 이미 있으면 뺀다
        rows.insert(0, {"device": key, "reason": reason, "blocked_by": actor, "created_at": now_iso()})  # 대상·이유·차단한 선생님·시각을 넣는다
        self._save(self.KEY_B, rows)  # 저장한다

    async def unblock(self, key):  # 차단 풀기
        self._save(self.KEY_B, [b for b in self._load(self.KEY_B) if b["device"] != key])  # 그 대상을 뺀 목록을 저장


class SupabaseStore:  # 공용 모드 저장소 (실제 서버)
    """공용 모드: Supabase(PostgreSQL) REST API. 권한과 장난 신고 막기는 tools/supabase_setup.py 의 규칙이 지킨다.

    선생님: 이메일·비밀번호 로그인. 학생: 구글 로그인 (Supabase 가 구글과 연결해 준다).
    접속 토큰(1시간)이 끝나기 전에 갱신 토큰으로 자동으로 새로 받는다.
    """
    shared = True  # 공용 모드

    def __init__(self, url, key):  # 처음 만들 때
        self.url = url.rstrip("/")  # 서버 주소 (끝의 / 는 뗀다)
        self.key = key  # 공개 키
        self.teacher_session = Session("kd-safety-teacher-session")  # 선생님 로그인 상자
        self.student_session = Session("kd-safety-student-session")  # 학생 로그인 상자

    # ── 토큰 ──
    def _session_data(self, data, extra=None):  # 서버가 준 로그인 정보에서 필요한 것만 고르는 함수
        return {"access_token": data["access_token"], "refresh_token": data["refresh_token"],  # 접속 토큰과 갱신 토큰
                "expires_at": time.time() + int(data.get("expires_in", 3600))} | (extra or {})  # 끝나는 시각 (+ 추가 정보)

    async def _token(self, sess, days):  # 쓸 수 있는 접속 토큰을 돌려주는 함수
        s = sess.get()  # 보관한 로그인 정보
        if not s:  # 로그인 안 했으면
            return None  # 없음
        if s["expires_at"] - time.time() < 120:  # 2분 안에 끝나면 미리 새로 받는다
            res = await _fetch(self.url + "/auth/v1/token?grant_type=refresh_token", method="POST",  # 갱신 토큰으로 새 토큰을 요청한다
                                headers={"apikey": self.key, "Content-Type": "application/json"},  # 공개 키와 형식 표시
                                body=json.dumps({"refresh_token": s["refresh_token"]}))  # 갱신 토큰을 보낸다
            if not res.ok:  # 실패하면 (오래돼서 만료 등)
                sess.clear()  # 로그인 정보를 지운다
                return None  # 다시 로그인해야 한다
            keep = {k: s[k] for k in ("uid", "email", "name") if k in s}  # 학생 정보는 그대로 옮긴다
            sess.save(self._session_data(await res.json(), keep), s.get("keep", False), days)  # 새 토큰을 보관한다
            s = sess.get()  # 새로 보관한 정보를 읽는다
        return s["access_token"]  # 접속 토큰을 돌려준다

    async def _req(self, method, path, body=None, auth=None, prefer=None):  # 서버에 데이터 요청을 보내는 공통 함수
        """auth: None(학생·익명 공개 키) | "teacher" | "student" """  # 이 함수가 하는 일을 적은 설명글
        token = None  # 로그인 토큰 (없으면 공개 키를 쓴다)
        if auth == "teacher":  # 선생님 권한이 필요하면
            token = await self._token(self.teacher_session, KEEP_DAYS)  # 선생님 토큰
            if not token:  # 없으면
                raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")  # 다시 로그인하라고 알린다
        elif auth == "student":  # 학생 권한이 필요하면
            token = await self._token(self.student_session, STUDENT_KEEP_DAYS)  # 학생 토큰
            if not token:  # 없으면
                raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")  # 다시 로그인하라고 알린다
        headers = {"apikey": self.key, "Authorization": f"Bearer {token or self.key}", "Content-Type": "application/json"}  # 요청 머리말: 공개 키 + 권한 토큰 + 형식
        if prefer:  # 추가 요청 사항이 있으면 (예: 결과를 돌려주지 말 것)
            headers["Prefer"] = prefer  # 머리말에 넣는다
        res = await _fetch(self.url + path, method=method, headers=headers,  # 서버에 요청을 보낸다
                            body=json.dumps(body, ensure_ascii=False) if body is not None else None)  # 보낼 내용을 글자로 바꿔 넣는다
        if res.status == 401 and auth:  # 권한이 없다고 하면 (토큰이 무효)
            (self.teacher_session if auth == "teacher" else self.student_session).clear()  # 그 로그인 정보를 지운다
            raise StoreError("로그인이 만료됐어요. 다시 로그인해 주세요.")  # 다시 로그인하라고 알린다
        text = await res.string()  # 응답 내용을 글자로 읽는다
        if not res.ok:  # 실패 응답이면
            # 데이터베이스 규칙(check_report)이 막으면 '신고: …' 메시지를 그대로 보여준다
            try:  # 응답에서 메시지를 꺼내 본다
                msg = json.loads(text).get("message", "")  # 서버가 보낸 메시지
            except Exception:  # 꺼낼 수 없으면
                msg = ""  # 빈 메시지
            if msg.startswith("신고: "):  # 우리 규칙이 보낸 안내면
                raise StoreError(msg[4:])  # 앞의 "신고: " 를 떼고 학생에게 보여준다
            raise StoreError(f"서버 오류 ({res.status}). 잠시 뒤 다시 해 주세요.")  # 그 밖의 오류
        return json.loads(text) if text else None  # 성공하면 내용을 파이썬 값으로 돌려준다

    # ── 학생 구글 로그인 ──
    @property  # 값처럼 쓴다
    def student(self):  # 지금 로그인한 학생 정보
        return self.student_session.get()  # 보관한 정보 (없으면 None)

    def google_url(self, back_to):  # 구글 로그인 화면 주소를 만드는 함수
        """구글 로그인 화면 주소. 로그인하면 back_to#access_token=... 으로 돌아온다."""  # 이 함수가 하는 일을 적은 설명글
        enc = window.encodeURIComponent  # 주소에 넣을 글자를 안전하게 바꾸는 함수
        url = f"{self.url}/auth/v1/authorize?provider=google&redirect_to={enc(back_to)}"  # 구글로 로그인하고 back_to 로 돌아오라는 주소
        if SCHOOL_DOMAIN:  # 학교 도메인이 정해져 있으면
            url += f"&hd={enc(SCHOOL_DOMAIN)}"  # 구글 화면에서 학교 계정을 먼저 보여준다 (막는 건 서버가 한다)
        return url + "&prompt=select_account"  # 매번 계정을 고르게 한다

    async def finish_google(self, fragment):  # 구글 로그인에서 돌아왔을 때 마무리하는 함수
        """구글에서 돌아온 주소의 #access_token=... 을 읽어 로그인한다. 성공하면 학생 정보, 아니면 오류 메시지."""  # 이 함수가 하는 일을 적은 설명글
        params = dict(p.split("=", 1) for p in fragment.lstrip("#").split("&") if "=" in p)  # 주소 # 뒤의 "이름=값" 들을 사전으로
        if "error" in params:  # 오류가 왔으면 (취소 등)
            return window.decodeURIComponent(params.get("error_description", "로그인을 취소했어요").replace("+", " "))  # 오류 설명을 읽기 좋게 돌려준다
        if "access_token" not in params:  # 토큰이 없으면
            return "로그인하지 못했어요."  # 실패
        try:  # 토큰으로 사용자 정보를 받아 본다
            res = await _fetch(self.url + "/auth/v1/user", headers={"apikey": self.key,  # 사용자 정보 요청 (공개 키)
                                                                    "Authorization": f"Bearer {params['access_token']}"})  # 받은 토큰으로
        except StoreError as e:  # 인터넷 문제면
            return str(e)  # 그 안내를 돌려준다
        if not res.ok:  # 실패하면
            return "로그인하지 못했어요."  # 실패
        user = await res.json()  # 사용자 정보
        email = user.get("email") or ""  # 이메일
        if not domain_ok(email):  # 학교 계정 조건에 안 맞으면
            return domain_message()  # 학교 계정으로 하라고 안내
        meta = user.get("user_metadata") or {}  # 구글이 준 추가 정보 (이름 등)
        self.student_session.save(self._session_data(params, {  # 로그인 정보를 보관한다
            "uid": user["id"], "email": email, "name": meta.get("full_name") or meta.get("name") or ""}),  # 계정 번호·이메일·이름
            True, STUDENT_KEEP_DAYS)  # 이 기기에 30일 유지
        return None  # 성공 (오류 없음)

    def student_logout(self):  # 학생 로그아웃
        s = self.student_session.get()  # 로그인 정보
        if s:  # 있으면
            self._remote_logout(s["access_token"])  # 서버에서도 로그아웃
        self.student_session.clear()  # 기기에서 지운다

    def _remote_logout(self, token):  # 서버에 로그아웃을 알리는 함수
        """서버에서도 이 로그인(갱신 토큰)을 없앤다."""  # 이 함수가 하는 일을 적은 설명글
        from js import Object, fetch  # 브라우저의 요청 함수 (기다리지 않고 보내기 위해)
        from pyodide.ffi import to_js  # 파이썬 값을 자바스크립트 값으로 바꾸는 도구
        fetch(self.url + "/auth/v1/logout", to_js({"method": "POST", "headers": {  # 로그아웃 요청을 보낸다
            "apikey": self.key, "Authorization": f"Bearer {token}"}}, dict_converter=Object.fromEntries))  # 공개 키와 그 로그인 토큰

    # 학생
    async def list_public(self, map_id=None):  # 학생에게 보여줄 신고 목록
        path = "/rest/v1/public_reports?select=*&order=created_at.desc"  # 공개용 목록(public_reports)을 최신순으로
        if map_id:  # 층을 정했으면
            path += f"&map=eq.{map_id}"  # 그 층 신고만
        return await self._req("GET", path)  # 서버에서 가져온다

    async def add(self, report):  # 새 신고 보내기
        if STUDENT_LOGIN and not self.student:  # 로그인이 필요한데 안 했으면
            raise StoreError("로그인한 뒤에 신고할 수 있어요.")  # 막는다
        rid = str(uuid.uuid4())  # 새 신고 번호
        # 신고한 계정(reporter_uid·email)은 데이터베이스가 로그인 정보로 채운다 (화면에서 속일 수 없게)
        await self._req("POST", "/rest/v1/reports", report | {"id": rid, "device": device_id()},  # 신고 내용 + 번호 + 기기 번호를 보낸다
                        auth="student" if self.student else None, prefer="return=minimal")  # 학생 권한으로, 결과는 돌려받지 않는다
        return rid  # 신고 번호를 돌려준다

    # 공감 "나도 봤어요" (규칙은 데이터베이스의 toggle_like() 가 지킨다)
    async def my_likes(self):  # 내가 공감한 신고 번호들
        if not self.student:  # 로그인 안 했으면
            return set()  # 없음
        try:  # 서버에 물어본다
            rows = await self._req("GET", "/rest/v1/report_likes?select=report_id", auth="student")  # 내 공감 목록 (서버가 내 것만 보여준다)
        except StoreError:  # 실패하면
            return set()  # 없음으로 본다
        return {r["report_id"] for r in rows or []}  # 신고 번호만 모은다

    async def toggle_like(self, rid):  # 공감 누르기/취소
        if not self.student:  # 로그인 안 했으면
            raise StoreError("로그인한 뒤에 공감할 수 있어요.")  # 막는다
        try:  # 서버의 공감 함수를 불러 본다
            return await self._req("POST", "/rest/v1/rpc/toggle_like", {"rid": rid}, auth="student")  # 결과: {"liked": ..., "likes": ...}
        except StoreError as e:  # 실패하면
            if "404" in str(e):  # 서버에 공감 함수가 아직 없으면
                raise StoreError("공감 기능을 준비 중이에요. 선생님께 말씀해 주세요.")  # 준비 중 안내
            raise  # 그 밖의 오류는 그대로 알린다

    # 선생님
    async def login(self, email, password, keep=False):  # 선생님 로그인
        res = await _fetch(self.url + "/auth/v1/token?grant_type=password", method="POST",  # 이메일·비밀번호로 토큰을 요청한다
                            headers={"apikey": self.key, "Content-Type": "application/json"},  # 공개 키와 형식 표시
                            body=json.dumps({"email": email, "password": password}))  # 이메일·비밀번호를 보낸다
        if not res.ok:  # 틀렸으면
            return False  # 실패
        self.teacher_session.save(self._session_data(await res.json()), keep, KEEP_DAYS)  # 받은 토큰을 보관한다
        return True  # 성공

    def logout(self):  # 선생님 로그아웃
        s = self.teacher_session.get()  # 로그인 정보
        if s:  # 있으면
            self._remote_logout(s["access_token"])  # 서버에서도 로그아웃
        self.teacher_session.clear()  # 기기에서 지운다

    @property  # 값처럼 쓴다
    def logged_in(self):  # 선생님이 로그인했는지
        return self.teacher_session.get() is not None  # 로그인 정보가 있으면 True

    async def list_all(self):  # 선생님용 전체 신고 목록
        cols = ",".join(f for f in REPORT_FIELDS if f != "photo") + ",has_photo"  # 사진은 빼고(무거워서) 사진 여부만 가져올 칸 목록
        rows = await self._req("GET", f"/rest/v1/reports?select={cols}&order=created_at.desc", auth="teacher")  # 최신순으로 가져온다
        try:  # 공감 수는 공개 목록에서 가져온다 (데이터베이스를 v2.6.0 으로 올리기 전이면 0)
            likes = {r["id"]: r.get("likes") or 0 for r in await self._req("GET", "/rest/v1/public_reports?select=*")}  # 신고 번호 → 공감 수
        except StoreError:  # 실패하면
            likes = {}  # 공감 수 없음
        return [r | {"likes": likes.get(r["id"], 0)} for r in rows or []]  # 각 신고에 공감 수를 붙여 돌려준다

    async def get(self, rid):  # 신고 하나를 자세히 가져오기 (사진 포함)
        rows = await self._req("GET", f"/rest/v1/reports?select=*&id=eq.{rid}", auth="teacher")  # 번호가 같은 신고
        return rows[0] if rows else None  # 있으면 첫 번째, 없으면 None

    async def update(self, rid, patch):  # 신고 내용 바꾸기
        await self._req("PATCH", f"/rest/v1/reports?id=eq.{rid}", patch | {"updated_at": now_iso()}, auth="teacher",  # 바꿀 내용 + 바꾼 시각
                        prefer="return=minimal")  # 결과는 돌려받지 않는다

    async def list_events(self, rid):  # 처리 기록 가져오기
        return await self._req("GET", f"/rest/v1/report_events?select=*&report_id=eq.{rid}&order=created_at.desc",  # 그 신고의 기록을 최신순으로
                               auth="teacher")  # 선생님 권한

    async def add_event(self, rid, kind, body, actor):  # 처리 기록 남기기
        await self._req("POST", "/rest/v1/report_events",  # 기록 표에 추가한다
                        {"report_id": rid, "kind": kind, "body": body, "actor": actor}, auth="teacher",  # 신고 번호·종류·내용·처리한 선생님
                        prefer="return=minimal")  # 결과는 돌려받지 않는다

    async def delete(self, rid):  # 신고 지우기
        await self._req("DELETE", f"/rest/v1/reports?id=eq.{rid}", auth="teacher")  # 그 신고를 지운다 (기록도 함께 지워진다)

    # 막기: device 칸에 기기 번호 또는 학생 계정 번호(uid)를 넣는다
    async def is_blocked(self, key):  # 차단됐는지 확인
        rows = await self._req("GET", f"/rest/v1/blocked_devices?select=device&device=eq.{key}", auth="teacher")  # 차단 목록에서 찾는다
        return bool(rows)  # 찾으면 True

    async def block(self, key, reason, actor):  # 차단하기
        await self._req("POST", "/rest/v1/blocked_devices", {"device": key, "reason": reason, "blocked_by": actor},  # 대상·이유·차단한 선생님
                        auth="teacher", prefer="return=minimal,resolution=ignore-duplicates")  # 이미 있으면 그냥 넘어간다

    async def unblock(self, key):  # 차단 풀기
        await self._req("DELETE", f"/rest/v1/blocked_devices?device=eq.{key}", auth="teacher")  # 차단 목록에서 지운다


store = SupabaseStore(config.SUPABASE_URL, config.SUPABASE_ANON_KEY) if SHARED else LocalStore()  # 공용 모드면 서버 저장소, 아니면 체험 저장소를 쓴다
