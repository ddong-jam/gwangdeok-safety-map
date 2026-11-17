"""공용 모드(Supabase) 데이터베이스 설정.

    python tools/supabase_setup.py            # 화면에 출력 → 복사해서 Supabase SQL Editor 에 붙여넣고 Run
    python tools/supabase_setup.py --copy     # 클립보드로 바로 복사 (윈도우)

데이터베이스는 SQL 만 알아듣기 때문에 내용은 SQL 문장이고, 파이썬은 그것을 보관·출력한다.
"""
import subprocess  # 다른 프로그램(윈도우 clip)을 실행하는 도구 — 클립보드 복사에 쓴다
import sys  # 실행할 때 받은 값을 읽는 도구

SQL = r'''-- 광덕신문고 · 공용 모드 데이터베이스 (Supabase → SQL Editor 에 통째로 붙여넣고 Run)
-- 학생(로그인 없음): 신고 접수 + 공개 칸만 보기 (신고자 이름·사진·담당자는 못 봄)
-- 선생님(admins 에 등록된 계정): 모든 신고 보기 · 처리 · 삭제

-- ── 신고 ─────────────────────────────────────────
create table if not exists public.reports (  -- 신고 표를 만든다 (이미 있으면 그대로)
  id          uuid primary key default gen_random_uuid(),  -- 신고 번호 (겹치지 않는 무작위 번호)
  created_at  timestamptz not null default now(),  -- 신고 시각 (자동으로 지금)
  updated_at  timestamptz,  -- 마지막으로 바꾼 시각
  resolved_at timestamptz,  -- 처리 완료·반려한 시각
  map         text not null check (length(map) <= 20),  -- 층 id (예: b2-1f)
  x           real not null,  -- 도면 위 x 좌표
  y           real not null,  -- 도면 위 y 좌표
  kind        text not null default 'danger' check (kind in ('danger','incon')),   -- 위험 / 불편
  category    text not null default 'etc' check (category in ('facility','slip','fire','traffic','hygiene','security','etc')),  -- 유형 7가지 중 하나
  severity    text not null default 'mid' check (severity in ('urgent','high','mid','low')),  -- 위험도: 긴급·높음·보통·낮음
  title       text not null check (length(title) between 1 and 60),  -- 제목 (1~60자)
  spot        text check (length(spot) <= 60),  -- 정확한 장소 (60자까지)
  description text check (length(description) <= 1000),  -- 자세한 내용 (1000자까지)
  reporter    text check (length(reporter) <= 30),  -- 신고자 이름 (선택, 30자까지)
  photo       text check (length(photo) <= 700000),          -- 줄인 JPEG data URL (약 500KB 까지)
  assignee    text check (length(assignee) <= 30),  -- 담당자 (선생님이 적음)
  status      text not null default 'new' check (status in ('new','doing','done','rejected')),  -- 처리 상태: 접수·처리중·완료·반려
  has_photo   boolean generated always as (photo is not null) stored  -- 사진이 있는지 (자동 계산)
);  -- 신고 표 끝
create index if not exists reports_created_idx on public.reports (created_at desc);  -- 최신순으로 빨리 찾기 위한 색인
-- v2.2.1 이전에 만든 데이터베이스에는 종류 칸을 더한다
alter table public.reports add column if not exists kind text not null default 'danger' check (kind in ('danger','incon'));  -- 종류 칸이 없으면 더한다

-- ── 처리 기록 ─────────────────────────────────────
create table if not exists public.report_events (  -- 처리 기록 표
  id         bigint generated always as identity primary key,  -- 기록 번호 (1, 2, 3 ... 자동)
  report_id  uuid not null references public.reports (id) on delete cascade,  -- 어느 신고의 기록인지 (신고를 지우면 기록도 지워짐)
  kind       text not null check (kind in ('status','assign','memo')),  -- 기록 종류: 상태 변경·담당자·메모
  body       text not null check (length(body) <= 1000),  -- 기록 내용
  actor      text not null check (length(actor) <= 30),  -- 처리한 선생님 이름
  created_at timestamptz not null default now()  -- 기록 시각
);  -- 처리 기록 표 끝
create index if not exists report_events_report_idx on public.report_events (report_id, created_at desc);  -- 신고별 최신 기록을 빨리 찾는 색인

-- ── 선생님 명단 ───────────────────────────────────
create table if not exists public.admins (  -- 선생님 명단 표
  user_id uuid primary key references auth.users (id) on delete cascade  -- 선생님 계정 번호
);  -- 선생님 명단 끝

create or replace function public.is_admin() returns boolean  -- 지금 로그인한 사람이 선생님인지 알려주는 함수
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());  -- 선생님 명단에 내 계정이 있으면 true
$$;  -- 함수 끝

-- ── 권한 ─────────────────────────────────────────
alter table public.reports       enable row level security;  -- 신고 표: 줄마다 권한 검사 켜기
alter table public.report_events enable row level security;  -- 처리 기록 표: 권한 검사 켜기
alter table public.admins        enable row level security;   -- 정책 없음 = API 로는 아무도 못 봄

revoke all on public.reports, public.report_events, public.admins from anon, authenticated;  -- 일단 모든 권한을 빼고 필요한 것만 다시 준다

-- 학생: 정해진 칸만 넣을 수 있다 (상태·담당자는 못 정함)
alter table public.reports add column if not exists device text check (length(device) between 8 and 40);   -- v2.5.0
-- 신고한 학생의 구글 계정 (데이터베이스가 로그인 정보로 채운다 — 화면에서 보낼 수 없다)
alter table public.reports add column if not exists reporter_uid uuid;  -- 신고한 학생의 계정 번호 칸
alter table public.reports add column if not exists reporter_email text check (length(reporter_email) <= 120);  -- 신고한 학생의 이메일 칸
grant insert (id, map, x, y, kind, category, severity, title, spot, description, reporter, photo, device)  -- 학생은 이 칸들만 넣을 수 있다
  on public.reports to anon, authenticated;  -- 로그인 안 한 사람·한 사람 모두
drop policy if exists "누구나 신고" on public.reports;  -- 옛 규칙이 있으면 지운다
create policy "누구나 신고" on public.reports for insert to anon, authenticated  -- 신고 넣기 규칙
  with check (status = 'new');  -- 상태는 반드시 '접수' 로만 넣을 수 있다

-- 선생님: 보기 · 처리 · 삭제
grant select, delete on public.reports to authenticated;  -- 로그인한 사람에게 보기·지우기 권한 (아래 규칙으로 선생님만)
grant update (status, resolved_at, assignee, updated_at) on public.reports to authenticated;  -- 바꿀 수 있는 칸: 상태·처리 시각·담당자
drop policy if exists "선생님 보기" on public.reports;  -- 옛 규칙 지우기
drop policy if exists "선생님 처리" on public.reports;  -- 옛 규칙 지우기
drop policy if exists "선생님 삭제" on public.reports;  -- 옛 규칙 지우기
create policy "선생님 보기" on public.reports for select to authenticated using (public.is_admin());  -- 선생님만 신고 전체를 본다
create policy "선생님 처리" on public.reports for update to authenticated using (public.is_admin()) with check (public.is_admin());  -- 선생님만 바꾼다
create policy "선생님 삭제" on public.reports for delete to authenticated using (public.is_admin());  -- 선생님만 지운다

grant select, insert on public.report_events to authenticated;  -- 처리 기록 보기·넣기 권한 (아래 규칙으로 선생님만)
drop policy if exists "선생님 기록 보기" on public.report_events;  -- 옛 규칙 지우기
drop policy if exists "선생님 기록 남기기" on public.report_events;  -- 옛 규칙 지우기
create policy "선생님 기록 보기" on public.report_events for select to authenticated using (public.is_admin());  -- 선생님만 기록을 본다
create policy "선생님 기록 남기기" on public.report_events for insert to authenticated with check (public.is_admin());  -- 선생님만 기록을 남긴다

-- ── 장난 신고 막기 (v2.5.0) ───────────────────────
-- 기기 = 학생 브라우저가 만든 무작위 번호 (이름·IP 아님). 선생님이 장난 신고를 한 기기를 막을 수 있다.
create table if not exists public.blocked_devices (  -- 차단 목록 표
  device     text primary key check (length(device) between 8 and 40),  -- 막은 기기 번호 또는 계정 번호
  reason     text check (length(reason) <= 100),  -- 막은 이유
  blocked_by text check (length(blocked_by) <= 30),  -- 막은 선생님
  created_at timestamptz not null default now()  -- 막은 시각
);  -- 차단 목록 표 끝
alter table public.blocked_devices enable row level security;  -- 권한 검사 켜기
revoke all on public.blocked_devices from anon, authenticated;  -- 모든 권한을 뺀다
grant select, insert, delete on public.blocked_devices to authenticated;  -- 보기·넣기·지우기 권한 (아래 규칙으로 선생님만)
drop policy if exists "선생님 차단 보기" on public.blocked_devices;  -- 옛 규칙 지우기
drop policy if exists "선생님 차단" on public.blocked_devices;  -- 옛 규칙 지우기
drop policy if exists "선생님 차단 풀기" on public.blocked_devices;  -- 옛 규칙 지우기
create policy "선생님 차단 보기" on public.blocked_devices for select to authenticated using (public.is_admin());  -- 선생님만 본다
create policy "선생님 차단" on public.blocked_devices for insert to authenticated with check (public.is_admin());  -- 선생님만 막는다
create policy "선생님 차단 풀기" on public.blocked_devices for delete to authenticated using (public.is_admin());  -- 선생님만 푼다

-- 신고가 들어올 때마다 확인한다 (학생 화면의 확인을 건너뛰고 직접 보내도 여기서 막힌다). 기준은 guard.py 와 같다.
create or replace function public.check_report() returns trigger  -- 신고 검사 함수
language plpgsql security definer set search_path = public as $$
declare
  who_uid   uuid := auth.uid();  -- 신고한 사람의 계정 번호 (로그인 안 했으면 없음)
  who_email text := lower(coalesce(auth.jwt() ->> 'email', ''));  -- 신고한 사람의 이메일 (소문자)
  provider  text := coalesce(auth.jwt() -> 'app_metadata' ->> 'provider', '');  -- 로그인 방식 (google 등)
  t   text := regexp_replace(lower(coalesce(new.title, '')), '\s', '', 'g');  -- 제목에서 띄어쓰기를 뺀 글자
  -- 욕설은 띄어쓰기를 그대로 두고 찾는다 ("다시 발생" 같은 글이 막히지 않게, guard.py 와 같다)
  all_text text := lower(coalesce(new.title, '') || ' ' || coalesce(new.description, '') || ' ' ||  -- 제목·내용을 합치고
                         coalesce(new.spot, '') || ' ' || coalesce(new.reporter, ''));  -- 장소·이름도 합친 글
begin
  -- 학생 구글 로그인 (config.py 의 STUDENT_LOGIN · SCHOOL_EMAIL_DOMAIN)
  new.reporter_uid := who_uid;  -- 신고자 계정 번호를 데이터베이스가 직접 채운다 (속일 수 없게)
  new.reporter_email := nullif(who_email, '');  -- 신고자 이메일도 직접 채운다
  if {require_login} and not public.is_admin() then  -- 로그인이 필요하고 선생님이 아니면
    if who_uid is null or provider <> 'google' then  -- 구글로 로그인하지 않았으면
      raise exception '신고: {MSG_login}';  -- 막는다 (로그인 안내)
    end if;  -- 로그인 검사 끝
  end if;  -- 로그인 필요 여부 끝
  if '{domain}' <> '' and who_uid is not null and not public.is_admin() and who_email not like '%@{domain}' then  -- 학교 도메인 제한이 있는데 다른 계정이면
    raise exception '신고: {MSG_domain}';  -- 막는다
  end if;  -- 도메인 검사 끝
  if new.device is null then  -- 기기 번호가 없으면
    raise exception '신고: {MSG_device}';  -- 막는다
  end if;  -- 기기 검사 끝
  if exists (select 1 from public.blocked_devices b where b.device = new.device or b.device = who_uid::text) then  -- 기기나 계정이 차단 목록에 있으면
    raise exception '신고: {MSG_blocked}';  -- 막는다
  end if;  -- 차단 검사 끝
  if length(t) < 4 or t ~ '{REPEAT}'  -- 제목이 4글자 미만이거나 같은 글자가 5번 이상 반복되거나
     or length(regexp_replace(t, '[^가-힣a-z0-9]', '', 'g')) < 3 then  -- 알아볼 수 있는 글자가 3개 미만이면
    raise exception '신고: {MSG_title}';  -- 막는다
  end if;  -- 제목 검사 끝
  if all_text ~ '{BAD}' then  -- 금지어가 들어 있으면
    raise exception '신고: {MSG_bad}';  -- 막는다
  end if;  -- 금지어 검사 끝
  if (select count(*) from public.reports r where (case when who_uid is not null then r.reporter_uid = who_uid else r.device = new.device end)  -- 같은 사람(계정 또는 기기)의 신고 중
        and r.created_at > now() - interval '10 minutes') >= {per_10min} then  -- 최근 10분 안에 정해진 수 이상이면
    raise exception '신고: {MSG_per_10min}';  -- 막는다
  end if;  -- 10분 제한 끝
  if (select count(*) from public.reports r where (case when who_uid is not null then r.reporter_uid = who_uid else r.device = new.device end)  -- 같은 사람의 신고 중
        and r.created_at > now() - interval '1 day') >= {per_day} then  -- 최근 하루 안에 정해진 수 이상이면
    raise exception '신고: {MSG_per_day}';  -- 막는다
  end if;  -- 하루 제한 끝
  if (select count(*) from public.reports r where r.created_at > now() - interval '10 minutes') >= {all_per_10min} then  -- 학교 전체가 10분에 정해진 수 이상이면
    raise exception '신고: {MSG_all_per_10min}';  -- 막는다
  end if;  -- 전체 제한 끝
  if exists (select 1 from public.reports r where (case when who_uid is not null then r.reporter_uid = who_uid else r.device = new.device end) and r.map = new.map  -- 같은 사람이 같은 층에
               and r.created_at > now() - interval '{dup_minutes} minutes'  -- 정해진 시간 안에
               and sqrt(power(r.x - new.x, 2) + power(r.y - new.y, 2)) < {dup_dist}) then  -- 가까운 자리를 신고했으면
    raise exception '신고: {MSG_dup}';  -- 막는다
  end if;  -- 같은 자리 검사 끝
  return new;  -- 모두 통과하면 신고를 저장한다
end;
$$;  -- 검사 함수 끝
drop trigger if exists check_report on public.reports;  -- 옛 연결이 있으면 지운다
create trigger check_report before insert on public.reports for each row execute function public.check_report();  -- 신고가 들어오기 직전에 검사 함수를 실행하게 연결

-- ── 공감 "나도 봤어요" (v2.6.0) ──────────────────
-- 한 계정이 한 신고에 한 번만. 누가 눌렀는지는 공개하지 않고 개수만 보여준다.
create table if not exists public.report_likes (  -- 공감 표
  report_id  uuid not null references public.reports (id) on delete cascade,  -- 어느 신고에 공감했는지 (신고를 지우면 같이 지워짐)
  uid        uuid not null default auth.uid(),  -- 공감한 학생 계정 (자동으로 로그인한 계정)
  created_at timestamptz not null default now(),  -- 공감한 시각
  primary key (report_id, uid)  -- 같은 신고에 같은 계정은 한 번만
);  -- 공감 표 끝
alter table public.report_likes enable row level security;  -- 권한 검사 켜기
revoke all on public.report_likes from anon, authenticated;  -- 모든 권한을 뺀다
grant select on public.report_likes to authenticated;  -- 로그인한 사람은 보기만 (아래 규칙으로 자기 것만)
drop policy if exists "내 공감 보기" on public.report_likes;  -- 옛 규칙 지우기
create policy "내 공감 보기" on public.report_likes for select to authenticated using (uid = auth.uid() or public.is_admin());  -- 내 공감만 보인다 (선생님은 전부)

-- 공감 누르기/취소 (로그인한 학생만, 내 신고·처리 끝난 신고는 안 됨). 결과: {"liked": true/false, "likes": 개수}
create or replace function public.toggle_like(rid uuid) returns json  -- 공감 누르기/취소 함수
language plpgsql security definer set search_path = public as $$
declare
  me uuid := auth.uid();  -- 지금 로그인한 계정
  r  public.reports%rowtype;  -- 공감할 신고
  on_now boolean;  -- 누른 뒤 공감 상태
begin
  if me is null then  -- 로그인 안 했으면
    raise exception '신고: 로그인한 뒤에 공감할 수 있어요.';  -- 막는다
  end if;  -- 로그인 검사 끝
  select * into r from public.reports where id = rid;  -- 신고를 찾는다
  if not found then  -- 없으면
    raise exception '신고: 없어진 신고예요.';  -- 알린다
  end if;  -- 신고 확인 끝
  if r.reporter_uid = me then  -- 내 신고면
    raise exception '신고: 내가 한 신고에는 공감할 수 없어요.';  -- 막는다
  end if;  -- 내 신고 검사 끝
  if exists (select 1 from public.blocked_devices b where b.device = me::text) then  -- 차단된 계정이면
    raise exception '신고: {MSG_blocked}';  -- 막는다
  end if;  -- 차단 검사 끝
  if exists (select 1 from public.report_likes where report_id = rid and uid = me) then  -- 이미 공감했으면
    delete from public.report_likes where report_id = rid and uid = me;  -- 취소한다
    on_now := false;  -- 이제 공감 안 한 상태
  else  -- 처음 누르면
    if r.status not in ('new', 'doing') then  -- 처리가 끝난 신고면
      raise exception '신고: 처리가 끝난 신고에는 공감할 수 없어요.';  -- 막는다
    end if;  -- 상태 검사 끝
    insert into public.report_likes (report_id, uid) values (rid, me);  -- 공감을 넣는다
    on_now := true;  -- 이제 공감한 상태
  end if;  -- 누르기/취소 끝
  return json_build_object('liked', on_now, 'likes', (select count(*) from public.report_likes where report_id = rid));  -- 공감 상태와 새 공감 수를 돌려준다
end;
$$;  -- 공감 함수 끝
revoke all on function public.toggle_like(uuid) from public, anon;  -- 로그인 안 한 사람은 공감 함수를 못 쓴다
grant execute on function public.toggle_like(uuid) to authenticated;  -- 로그인한 사람만 쓸 수 있다

-- ── 학생에게 보이는 신고 (공개 칸만) ──────────────
-- 뷰는 만든 사람 권한으로 돌아서 위 RLS 와 상관없이 이 칸들만 보여준다
create or replace view public.public_reports as  -- 공개용 신고 목록 (보기 전용 표)
  select id, created_at, map, x, y, category, severity, title, spot, status, kind,   -- 새 칸은 맨 뒤에 (기존 뷰를 바꿀 수 있게)
         (select count(*) from public.report_likes l where l.report_id = reports.id)::int as likes  -- 신고별 공감 수
  from public.reports;  -- 신고 표에서 가져온다 (신고자·사진·담당자는 빠짐)
grant select on public.public_reports to anon, authenticated;  -- 누구나 볼 수 있다

-- ── 선생님 계정 등록 ─────────────────────────────
-- 1) Authentication → Users → Add user 로 이메일·비밀번호 계정을 만든 뒤
-- 2) 아래 줄의 이메일을 바꿔서 실행 (선생님마다 한 번씩)
-- insert into public.admins (user_id) select id from auth.users where email = 'teacher@example.com';
'''  # SQL 글 끝


def build_sql():  # 장난 신고 기준을 SQL 안에 채워 완성하는 함수
    """장난 신고 기준(guard.py)을 SQL 안에 채워 넣는다."""  # 이 함수가 하는 일을 적은 설명글
    import os  # 폴더 경로 도구
    import re  # 글자 패턴 도구
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 프로젝트 폴더의 파일을 불러올 수 있게
    import guard  # 장난 신고 기준
    sql = SQL.replace("{REPEAT}", guard.REPEAT).replace("{BAD}", "|".join(re.escape(w) for w in guard.BAD_WORDS))  # 반복 글자 패턴과 금지어 목록을 넣는다
    import config  # 설정
    domain = (getattr(config, "SCHOOL_EMAIL_DOMAIN", "") or "").strip().lstrip("@").lower()  # 학교 도메인 (없으면 빈칸)
    assert re.fullmatch(r"[a-z0-9.-]*", domain), "SCHOOL_EMAIL_DOMAIN 에 이상한 글자가 있어요"  # 도메인에 이상한 글자가 없는지 확인
    sql = sql.replace("{require_login}", "true" if getattr(config, "STUDENT_LOGIN", False) else "false")  # 로그인 필요 여부를 넣는다
    sql = sql.replace("{domain}", domain)  # 도메인을 넣는다
    for k, v in guard.LIMITS.items():  # 숫자 기준마다
        sql = sql.replace("{" + k + "}", str(v))  # 넣는다 (예: {per_10min} → 3)
    for k, v in guard.MESSAGES.items():  # 안내 문구마다
        sql = sql.replace("{MSG_" + k + "}", v.replace("'", "''"))  # 넣는다 (작은따옴표는 SQL 용으로 두 번)
    assert "{" not in re.sub(r"\{\d+,?\d*\}", "", sql.split("as $$", 1)[1].split("$$;", 1)[0]), "빠진 값"  # 검사 함수 안에 안 채운 칸이 없는지 확인
    return sql  # 완성된 SQL


def main():  # 실행했을 때 하는 일
    sql = build_sql()  # SQL 을 완성한다
    if "--copy" in sys.argv:  # "--copy" 로 실행하면
        subprocess.run("clip", input=sql.encode("utf-16-le"), check=True)  # 윈도우 클립보드에 복사한다 (한글이 깨지지 않게 UTF-16)
        print("복사했어요. Supabase → SQL Editor 에 붙여넣고 Run 하세요.")  # 안내
    else:  # 아니면
        sys.stdout.reconfigure(encoding="utf-8")  # 화면 출력을 UTF-8 로
        print(sql)  # SQL 을 화면에 보여준다


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    main()  # 실행
