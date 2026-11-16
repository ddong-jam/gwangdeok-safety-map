"""장난·허위 신고 막기.

학생 화면(접수 전 확인), 체험 저장소(LocalStore), Supabase 데이터베이스 규칙(tools/supabase_setup.py)이
같은 기준을 쓴다. 학생 화면의 확인은 건너뛸 수 있어서, 공용 모드에서는 데이터베이스가 한 번 더 막는다.
"""
import re  # 글자 패턴(정규식)으로 반복 글자·이상한 제목을 찾기 위해 불러온다
from datetime import datetime, timedelta, timezone  # 신고 시각을 비교하기 위해 날짜·시간 도구를 불러온다

LIMITS = {  # 장난 신고를 막는 숫자 기준 모음
    "per_10min": 3,      # 한 기기에서 10분에 3건까지
    "per_day": 10,       # 한 기기에서 하루(24시간)에 10건까지
    "all_per_10min": 60,  # 학교 전체 10분에 60건까지 (한꺼번에 도배 막기)
    "dup_minutes": 30,   # 같은 기기 · 같은 층 · 가까운 자리 신고는 30분에 한 번
    "dup_dist": 25,      # '가까운 자리' 거리 (도면 단위)
    "min_fill_sec": 4,   # 신고 창을 열고 4초 안에 접수하면 다시 확인
}  # 기준 모음 끝

# 신고 글에 쓰면 안 되는 말 (영어는 소문자로 바꿔서 찾는다)
# 띄어쓰기는 그대로 두고 찾는다: 띄어쓰기를 빼면 "다시 발생", "유리병 신고", "아저씨 바쁘셔서" 같은
# 멀쩡한 글이 막힌다. "불이 꺼져 있어요" 처럼 신고에 흔히 쓰는 말(꺼져)은 목록에 넣지 않는다.
BAD_WORDS = [  # 금지어 목록 시작
    "씨발", "시발", "씨바", "ㅅㅂ", "ㅆㅂ", "병신", "ㅂㅅ", "븅신", "개새끼", "개새", "좆", "존나", "졸라",  # 욕설 1
    "지랄", "ㅈㄹ", "미친놈", "미친년", "닥쳐", "느금", "니애미", "엠창", "애미", "애비",  # 욕설 2
    "섹스", "야동", "fuck", "shit", "bitch",  # 성적인 말·영어 욕설
]  # 금지어 목록 끝

MESSAGES = {  # 신고가 막혔을 때 학생에게 보여줄 안내 문구 모음
    "title": "제목을 알아볼 수 있게 4글자 이상 적어 주세요.",  # 제목이 짧거나 의미 없을 때
    "bad": "바르고 고운 말로 적어 주세요.",  # 욕설이 들어 있을 때
    "blocked": "신고가 제한되었어요. 선생님께 말씀해 주세요.",  # 선생님이 차단한 계정일 때
    "per_10min": f"신고가 너무 잦아요. 10분 뒤에 다시 해 주세요. (10분에 {LIMITS['per_10min']}건까지)",  # 10분 제한을 넘었을 때
    "per_day": f"오늘은 더 신고할 수 없어요. (하루 {LIMITS['per_day']}건까지)",  # 하루 제한을 넘었을 때
    "all_per_10min": "지금 신고가 몰려 있어요. 잠시 뒤에 다시 해 주세요.",  # 학교 전체 신고가 몰렸을 때
    "dup": "같은 자리를 방금 신고했어요. 선생님이 확인할 때까지 기다려 주세요.",  # 같은 자리 반복 신고일 때
    "fast": "내용을 한 번 더 확인하고 접수해 주세요.",  # 창을 열자마자 접수했을 때
    "device": "다시 시도해 주세요. (기기 정보를 만들지 못했어요)",  # 기기 번호를 못 만들었을 때
    "login": "구글 계정으로 로그인한 뒤에 신고할 수 있어요.",  # 로그인하지 않았을 때
    "domain": "학교 구글 계정으로 로그인해 주세요.",  # 학교 계정만 받을 때 다른 계정으로 왔을 때
}  # 안내 문구 모음 끝

REPEAT = r"(.)\1{4,}"            # 같은 글자 5번 이상 (ㅋㅋㅋㅋㅋ, !!!!!)
MEANINGFUL = r"[가-힣A-Za-z0-9]"   # 알아볼 수 있는 글자


def squash(*texts) -> str:  # 여러 글을 하나로 합쳐 띄어쓰기를 지우고 소문자로 바꾸는 함수
    return re.sub(r"\s+", "", "".join(t or "" for t in texts)).lower()  # 합치기 → 공백 지우기 → 소문자로 돌려준다


def check_text(title, desc="", spot="", reporter="") -> str | None:  # 신고 글 내용을 검사하는 함수
    """글 내용 확인. 문제가 있으면 학생에게 보여줄 말, 없으면 None."""  # 이 함수가 하는 일을 적은 설명글
    t = squash(title)  # 제목에서 띄어쓰기를 뺀 글자
    if len(t) < 4 or re.search(REPEAT, t) or len(re.findall(MEANINGFUL, t)) < 3:  # 4글자 미만·같은 글자 반복·의미 있는 글자 3개 미만이면
        return MESSAGES["title"]  # 제목을 다시 쓰라는 안내를 돌려준다
    allt = " ".join(x or "" for x in (title, desc, spot, reporter)).lower()  # 제목·내용·장소·이름을 띄어쓰기 그대로 합친다
    if any(w in allt for w in BAD_WORDS):  # 금지어가 하나라도 들어 있으면
        return MESSAGES["bad"]  # 바른 말로 쓰라는 안내를 돌려준다
    return None  # 문제가 없으면 None(통과)


def _time(iso):  # 글자로 된 시각을 날짜 값으로 바꾸는 함수
    try:  # 바꾸다 실패할 수 있어서 시도해 본다
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00"))  # "…Z"(세계 표준시)를 파이썬이 아는 꼴로 바꿔 읽는다
    except Exception:  # 형식이 이상하면
        return None  # 시각 없음으로 돌려준다


def check_rate(rows, report, now=None) -> str | None:  # 신고 횟수·반복을 검사하는 함수
    """보낸 횟수 확인 (rows: 지금까지 신고들). 데이터베이스의 check_report() 와 같은 규칙."""  # 이 함수가 하는 일을 적은 설명글
    now = now or datetime.now(timezone.utc)  # 기준 시각 (따로 안 주면 지금)
    # '같은 사람' = 로그인한 학생이면 같은 구글 계정, 아니면 같은 기기
    who_key, who = ("reporter_uid", report.get("reporter_uid")) if report.get("reporter_uid") else ("device", report.get("device"))  # 사람을 구별할 칸과 값
    recent = [(r, _time(r.get("created_at"))) for r in rows]  # 모든 신고에 시각을 붙인다
    recent = [(r, t) for r, t in recent if t]  # 시각을 읽을 수 있는 신고만 남긴다
    mine = [(r, t) for r, t in recent if who and r.get(who_key) == who]  # 그중 이 사람이 한 신고만 고른다
    if sum(1 for _, t in mine if t > now - timedelta(minutes=10)) >= LIMITS["per_10min"]:  # 최근 10분 동안 3건 이상 했으면
        return MESSAGES["per_10min"]  # 10분 제한 안내
    if sum(1 for _, t in mine if t > now - timedelta(days=1)) >= LIMITS["per_day"]:  # 최근 하루 동안 10건 이상 했으면
        return MESSAGES["per_day"]  # 하루 제한 안내
    if sum(1 for _, t in recent if t > now - timedelta(minutes=10)) >= LIMITS["all_per_10min"]:  # 학교 전체가 10분에 60건 이상이면
        return MESSAGES["all_per_10min"]  # 신고가 몰렸다는 안내
    for r, t in mine:  # 이 사람의 신고를 하나씩 보면서
        if (t > now - timedelta(minutes=LIMITS["dup_minutes"]) and r.get("map") == report.get("map")  # 30분 안이고 같은 층이고
                and ((r["x"] - report["x"]) ** 2 + (r["y"] - report["y"]) ** 2) ** 0.5 < LIMITS["dup_dist"]):  # 거리가 25 미만으로 가까우면
            return MESSAGES["dup"]  # 같은 자리 반복 신고 안내
    return None  # 모두 통과하면 None
