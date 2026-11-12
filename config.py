# 신고를 여러 사람이 함께 보려면 Supabase 주소와 공개 키(anon key)를 넣는다.
# 비워두면 "체험 모드": 신고가 이 브라우저에만 저장된다 (학생용·선생님용 페이지끼리는 같은 브라우저에서 공유됨).
# 설정 방법은 README.md 의 "신고를 모두 함께 보기" 참고.

SUPABASE_URL = "https://bxideaygpolfmfwxrjzo.supabase.co"        # 예: "https://abcdefgh.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4aWRlYXlncG9sZm1md3hyanpvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTM4ODE5NjcsImV4cCI6MjEwOTQ1Nzk2N30.8V1IOQ_Qfyvf7jsrtQdYcnfZS0UoDuGArhGoDjQk5FQ"   # Project Settings → API → anon public 키 (공개용 키라 올려도 됨)
# 선생님들이 계정 하나를 같이 쓸 때 그 이메일. 넣으면 로그인 화면에 이메일 칸 없이 이름 + 비밀번호만 나온다.
# 비워두면 선생님마다 자기 이메일·비밀번호로 로그인한다.
TEACHER_EMAIL = ""

# 학생도 구글 계정으로 로그인해야 신고할 수 있게 한다 (지도 보기는 로그인 없이 된다).
# 공용 모드에서는 Supabase → Authentication → Providers → Google 을 켜야 한다 (README 참고).
STUDENT_LOGIN = True
# 학교 구글 계정 도메인 (예: "gwangdeok.hs.kr"). 넣으면 그 도메인 계정만 신고할 수 있다. 비우면 아무 구글 계정.
SCHOOL_EMAIL_DOMAIN = ""
