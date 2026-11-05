"""장난·허위 신고 막기.

학생 화면(접수 전 확인), 체험 저장소(LocalStore), Supabase 데이터베이스 규칙(tools/supabase_setup.py)이
같은 기준을 쓴다. 학생 화면의 확인은 건너뛸 수 있어서, 공용 모드에서는 데이터베이스가 한 번 더 막는다.
"""
import re
from datetime import datetime, timedelta, timezone

LIMITS = {
    "per_10min": 3,      # 한 기기에서 10분에 3건까지
    "per_day": 10,       # 한 기기에서 하루(24시간)에 10건까지
    "all_per_10min": 60,  # 학교 전체 10분에 60건까지 (한꺼번에 도배 막기)
    "dup_minutes": 30,   # 같은 기기 · 같은 층 · 가까운 자리 신고는 30분에 한 번
    "dup_dist": 25,      # '가까운 자리' 거리 (도면 단위)
    "min_fill_sec": 4,   # 신고 창을 열고 4초 안에 접수하면 다시 확인
}

# 신고 글에 쓰면 안 되는 말 (띄어쓰기를 빼고, 영어는 소문자로 바꿔서 찾는다)
BAD_WORDS = [
    "씨발", "시발", "씨바", "ㅅㅂ", "ㅆㅂ", "병신", "ㅂㅅ", "븅신", "개새끼", "개새", "좆", "존나", "졸라",
    "지랄", "ㅈㄹ", "미친놈", "미친년", "닥쳐", "꺼져", "느금", "니애미", "엠창", "애미", "애비",
    "섹스", "야동", "fuck", "shit", "bitch",
]

MESSAGES = {
    "title": "제목을 알아볼 수 있게 4글자 이상 적어 주세요.",
    "bad": "바르고 고운 말로 적어 주세요.",
    "blocked": "신고가 제한되었어요. 선생님께 말씀해 주세요.",
    "per_10min": f"신고가 너무 잦아요. 10분 뒤에 다시 해 주세요. (10분에 {LIMITS['per_10min']}건까지)",
    "per_day": f"오늘은 더 신고할 수 없어요. (하루 {LIMITS['per_day']}건까지)",
    "all_per_10min": "지금 신고가 몰려 있어요. 잠시 뒤에 다시 해 주세요.",
    "dup": "같은 자리를 방금 신고했어요. 선생님이 확인할 때까지 기다려 주세요.",
    "fast": "내용을 한 번 더 확인하고 접수해 주세요.",
    "device": "다시 시도해 주세요. (기기 정보를 만들지 못했어요)",
    "login": "학교 구글 계정으로 로그인한 뒤에 신고할 수 있어요.",
    "domain": "학교 구글 계정으로 로그인해 주세요.",
}

REPEAT = r"(.)\1{4,}"            # 같은 글자 5번 이상 (ㅋㅋㅋㅋㅋ, !!!!!)
MEANINGFUL = r"[가-힣A-Za-z0-9]"   # 알아볼 수 있는 글자


def squash(*texts) -> str:
    return re.sub(r"\s+", "", "".join(t or "" for t in texts)).lower()


def check_text(title, desc="", spot="", reporter="") -> str | None:
    """글 내용 확인. 문제가 있으면 학생에게 보여줄 말, 없으면 None."""
    t = squash(title)
    if len(t) < 4 or re.search(REPEAT, t) or len(re.findall(MEANINGFUL, t)) < 3:
        return MESSAGES["title"]
    allt = squash(title, desc, spot, reporter)
    if any(w in allt for w in BAD_WORDS):
        return MESSAGES["bad"]
    return None


def _time(iso):
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except Exception:
        return None


def check_rate(rows, report, now=None) -> str | None:
    """보낸 횟수 확인 (rows: 지금까지 신고들). 데이터베이스의 check_report() 와 같은 규칙."""
    now = now or datetime.now(timezone.utc)
    # '같은 사람' = 로그인한 학생이면 같은 구글 계정, 아니면 같은 기기
    who_key, who = ("reporter_uid", report.get("reporter_uid")) if report.get("reporter_uid") else ("device", report.get("device"))
    recent = [(r, _time(r.get("created_at"))) for r in rows]
    recent = [(r, t) for r, t in recent if t]
    mine = [(r, t) for r, t in recent if who and r.get(who_key) == who]
    if sum(1 for _, t in mine if t > now - timedelta(minutes=10)) >= LIMITS["per_10min"]:
        return MESSAGES["per_10min"]
    if sum(1 for _, t in mine if t > now - timedelta(days=1)) >= LIMITS["per_day"]:
        return MESSAGES["per_day"]
    if sum(1 for _, t in recent if t > now - timedelta(minutes=10)) >= LIMITS["all_per_10min"]:
        return MESSAGES["all_per_10min"]
    for r, t in mine:
        if (t > now - timedelta(minutes=LIMITS["dup_minutes"]) and r.get("map") == report.get("map")
                and ((r["x"] - report["x"]) ** 2 + (r["y"] - report["y"]) ** 2) ** 0.5 < LIMITS["dup_dist"]):
            return MESSAGES["dup"]
    return None
