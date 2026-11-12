"""공용 모드(Supabase) 데이터베이스 설정.

    python tools/supabase_setup.py            # 화면에 출력 → 복사해서 Supabase SQL Editor 에 붙여넣고 Run
    python tools/supabase_setup.py --copy     # 클립보드로 바로 복사 (윈도우)

데이터베이스는 SQL 만 알아듣기 때문에 내용은 SQL 문장이고, 파이썬은 그것을 보관·출력한다.
"""
import subprocess
import sys

SQL = r'''-- 광덕 안전지도 · 공용 모드 데이터베이스 (Supabase → SQL Editor 에 통째로 붙여넣고 Run)
-- 학생(로그인 없음): 신고 접수 + 공개 칸만 보기 (신고자 이름·사진·담당자는 못 봄)
-- 선생님(admins 에 등록된 계정): 모든 신고 보기 · 처리 · 삭제

-- ── 신고 ─────────────────────────────────────────
create table if not exists public.reports (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz,
  resolved_at timestamptz,
  map         text not null check (length(map) <= 20),
  x           real not null,
  y           real not null,
  kind        text not null default 'danger' check (kind in ('danger','incon')),   -- 위험 / 불편
  category    text not null default 'etc' check (category in ('facility','slip','fire','traffic','hygiene','security','etc')),
  severity    text not null default 'mid' check (severity in ('urgent','high','mid','low')),
  title       text not null check (length(title) between 1 and 60),
  spot        text check (length(spot) <= 60),
  description text check (length(description) <= 1000),
  reporter    text check (length(reporter) <= 30),
  photo       text check (length(photo) <= 700000),          -- 줄인 JPEG data URL (약 500KB 까지)
  assignee    text check (length(assignee) <= 30),
  status      text not null default 'new' check (status in ('new','doing','done','rejected')),
  has_photo   boolean generated always as (photo is not null) stored
);
create index if not exists reports_created_idx on public.reports (created_at desc);
-- v2.2.1 이전에 만든 데이터베이스에는 종류 칸을 더한다
alter table public.reports add column if not exists kind text not null default 'danger' check (kind in ('danger','incon'));

-- ── 처리 기록 ─────────────────────────────────────
create table if not exists public.report_events (
  id         bigint generated always as identity primary key,
  report_id  uuid not null references public.reports (id) on delete cascade,
  kind       text not null check (kind in ('status','assign','memo')),
  body       text not null check (length(body) <= 1000),
  actor      text not null check (length(actor) <= 30),
  created_at timestamptz not null default now()
);
create index if not exists report_events_report_idx on public.report_events (report_id, created_at desc);

-- ── 선생님 명단 ───────────────────────────────────
create table if not exists public.admins (
  user_id uuid primary key references auth.users (id) on delete cascade
);

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

-- ── 권한 ─────────────────────────────────────────
alter table public.reports       enable row level security;
alter table public.report_events enable row level security;
alter table public.admins        enable row level security;   -- 정책 없음 = API 로는 아무도 못 봄

revoke all on public.reports, public.report_events, public.admins from anon, authenticated;

-- 학생: 정해진 칸만 넣을 수 있다 (상태·담당자는 못 정함)
alter table public.reports add column if not exists device text check (length(device) between 8 and 40);   -- v2.5.0
-- 신고한 학생의 구글 계정 (데이터베이스가 로그인 정보로 채운다 — 화면에서 보낼 수 없다)
alter table public.reports add column if not exists reporter_uid uuid;
alter table public.reports add column if not exists reporter_email text check (length(reporter_email) <= 120);
grant insert (id, map, x, y, kind, category, severity, title, spot, description, reporter, photo, device)
  on public.reports to anon, authenticated;
drop policy if exists "누구나 신고" on public.reports;
create policy "누구나 신고" on public.reports for insert to anon, authenticated
  with check (status = 'new');

-- 선생님: 보기 · 처리 · 삭제
grant select, delete on public.reports to authenticated;
grant update (status, resolved_at, assignee, updated_at) on public.reports to authenticated;
drop policy if exists "선생님 보기" on public.reports;
drop policy if exists "선생님 처리" on public.reports;
drop policy if exists "선생님 삭제" on public.reports;
create policy "선생님 보기" on public.reports for select to authenticated using (public.is_admin());
create policy "선생님 처리" on public.reports for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy "선생님 삭제" on public.reports for delete to authenticated using (public.is_admin());

grant select, insert on public.report_events to authenticated;
drop policy if exists "선생님 기록 보기" on public.report_events;
drop policy if exists "선생님 기록 남기기" on public.report_events;
create policy "선생님 기록 보기" on public.report_events for select to authenticated using (public.is_admin());
create policy "선생님 기록 남기기" on public.report_events for insert to authenticated with check (public.is_admin());

-- ── 장난 신고 막기 (v2.5.0) ───────────────────────
-- 기기 = 학생 브라우저가 만든 무작위 번호 (이름·IP 아님). 선생님이 장난 신고를 한 기기를 막을 수 있다.
create table if not exists public.blocked_devices (
  device     text primary key check (length(device) between 8 and 40),
  reason     text check (length(reason) <= 100),
  blocked_by text check (length(blocked_by) <= 30),
  created_at timestamptz not null default now()
);
alter table public.blocked_devices enable row level security;
revoke all on public.blocked_devices from anon, authenticated;
grant select, insert, delete on public.blocked_devices to authenticated;
drop policy if exists "선생님 차단 보기" on public.blocked_devices;
drop policy if exists "선생님 차단" on public.blocked_devices;
drop policy if exists "선생님 차단 풀기" on public.blocked_devices;
create policy "선생님 차단 보기" on public.blocked_devices for select to authenticated using (public.is_admin());
create policy "선생님 차단" on public.blocked_devices for insert to authenticated with check (public.is_admin());
create policy "선생님 차단 풀기" on public.blocked_devices for delete to authenticated using (public.is_admin());

-- 신고가 들어올 때마다 확인한다 (학생 화면의 확인을 건너뛰고 직접 보내도 여기서 막힌다). 기준은 guard.py 와 같다.
create or replace function public.check_report() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  who_uid   uuid := auth.uid();
  who_email text := lower(coalesce(auth.jwt() ->> 'email', ''));
  provider  text := coalesce(auth.jwt() -> 'app_metadata' ->> 'provider', '');
  t   text := regexp_replace(lower(coalesce(new.title, '')), '\s', '', 'g');
  -- 욕설은 띄어쓰기를 그대로 두고 찾는다 ("다시 발생" 같은 글이 막히지 않게, guard.py 와 같다)
  all_text text := lower(coalesce(new.title, '') || ' ' || coalesce(new.description, '') || ' ' ||
                         coalesce(new.spot, '') || ' ' || coalesce(new.reporter, ''));
begin
  -- 학생 구글 로그인 (config.py 의 STUDENT_LOGIN · SCHOOL_EMAIL_DOMAIN)
  new.reporter_uid := who_uid;
  new.reporter_email := nullif(who_email, '');
  if {require_login} and not public.is_admin() then
    if who_uid is null or provider <> 'google' then
      raise exception '신고: {MSG_login}';
    end if;
  end if;
  if '{domain}' <> '' and who_uid is not null and not public.is_admin() and who_email not like '%@{domain}' then
    raise exception '신고: {MSG_domain}';
  end if;
  if new.device is null then
    raise exception '신고: {MSG_device}';
  end if;
  if exists (select 1 from public.blocked_devices b where b.device = new.device or b.device = who_uid::text) then
    raise exception '신고: {MSG_blocked}';
  end if;
  if length(t) < 4 or t ~ '{REPEAT}'
     or length(regexp_replace(t, '[^가-힣a-z0-9]', '', 'g')) < 3 then
    raise exception '신고: {MSG_title}';
  end if;
  if all_text ~ '{BAD}' then
    raise exception '신고: {MSG_bad}';
  end if;
  if (select count(*) from public.reports r where (case when who_uid is not null then r.reporter_uid = who_uid else r.device = new.device end)
        and r.created_at > now() - interval '10 minutes') >= {per_10min} then
    raise exception '신고: {MSG_per_10min}';
  end if;
  if (select count(*) from public.reports r where (case when who_uid is not null then r.reporter_uid = who_uid else r.device = new.device end)
        and r.created_at > now() - interval '1 day') >= {per_day} then
    raise exception '신고: {MSG_per_day}';
  end if;
  if (select count(*) from public.reports r where r.created_at > now() - interval '10 minutes') >= {all_per_10min} then
    raise exception '신고: {MSG_all_per_10min}';
  end if;
  if exists (select 1 from public.reports r where (case when who_uid is not null then r.reporter_uid = who_uid else r.device = new.device end) and r.map = new.map
               and r.created_at > now() - interval '{dup_minutes} minutes'
               and sqrt(power(r.x - new.x, 2) + power(r.y - new.y, 2)) < {dup_dist}) then
    raise exception '신고: {MSG_dup}';
  end if;
  return new;
end;
$$;
drop trigger if exists check_report on public.reports;
create trigger check_report before insert on public.reports for each row execute function public.check_report();

-- ── 공감 "나도 봤어요" (v2.6.0) ──────────────────
-- 한 계정이 한 신고에 한 번만. 누가 눌렀는지는 공개하지 않고 개수만 보여준다.
create table if not exists public.report_likes (
  report_id  uuid not null references public.reports (id) on delete cascade,
  uid        uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  primary key (report_id, uid)
);
alter table public.report_likes enable row level security;
revoke all on public.report_likes from anon, authenticated;
grant select on public.report_likes to authenticated;
drop policy if exists "내 공감 보기" on public.report_likes;
create policy "내 공감 보기" on public.report_likes for select to authenticated using (uid = auth.uid() or public.is_admin());

-- 공감 누르기/취소 (로그인한 학생만, 내 신고·처리 끝난 신고는 안 됨). 결과: {"liked": true/false, "likes": 개수}
create or replace function public.toggle_like(rid uuid) returns json
language plpgsql security definer set search_path = public as $$
declare
  me uuid := auth.uid();
  r  public.reports%rowtype;
  on_now boolean;
begin
  if me is null then
    raise exception '신고: 로그인한 뒤에 공감할 수 있어요.';
  end if;
  select * into r from public.reports where id = rid;
  if not found then
    raise exception '신고: 없어진 신고예요.';
  end if;
  if r.reporter_uid = me then
    raise exception '신고: 내가 한 신고에는 공감할 수 없어요.';
  end if;
  if exists (select 1 from public.blocked_devices b where b.device = me::text) then
    raise exception '신고: {MSG_blocked}';
  end if;
  if exists (select 1 from public.report_likes where report_id = rid and uid = me) then
    delete from public.report_likes where report_id = rid and uid = me;
    on_now := false;
  else
    if r.status not in ('new', 'doing') then
      raise exception '신고: 처리가 끝난 신고에는 공감할 수 없어요.';
    end if;
    insert into public.report_likes (report_id, uid) values (rid, me);
    on_now := true;
  end if;
  return json_build_object('liked', on_now, 'likes', (select count(*) from public.report_likes where report_id = rid));
end;
$$;
revoke all on function public.toggle_like(uuid) from public, anon;
grant execute on function public.toggle_like(uuid) to authenticated;

-- ── 학생에게 보이는 신고 (공개 칸만) ──────────────
-- 뷰는 만든 사람 권한으로 돌아서 위 RLS 와 상관없이 이 칸들만 보여준다
create or replace view public.public_reports as
  select id, created_at, map, x, y, category, severity, title, spot, status, kind,   -- 새 칸은 맨 뒤에 (기존 뷰를 바꿀 수 있게)
         (select count(*) from public.report_likes l where l.report_id = reports.id)::int as likes
  from public.reports;
grant select on public.public_reports to anon, authenticated;

-- ── 선생님 계정 등록 ─────────────────────────────
-- 1) Authentication → Users → Add user 로 이메일·비밀번호 계정을 만든 뒤
-- 2) 아래 줄의 이메일을 바꿔서 실행 (선생님마다 한 번씩)
-- insert into public.admins (user_id) select id from auth.users where email = 'teacher@example.com';
'''


def build_sql():
    """장난 신고 기준(guard.py)을 SQL 안에 채워 넣는다."""
    import os
    import re
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import guard
    sql = SQL.replace("{REPEAT}", guard.REPEAT).replace("{BAD}", "|".join(re.escape(w) for w in guard.BAD_WORDS))
    import config
    domain = (getattr(config, "SCHOOL_EMAIL_DOMAIN", "") or "").strip().lstrip("@").lower()
    assert re.fullmatch(r"[a-z0-9.-]*", domain), "SCHOOL_EMAIL_DOMAIN 에 이상한 글자가 있어요"
    sql = sql.replace("{require_login}", "true" if getattr(config, "STUDENT_LOGIN", False) else "false")
    sql = sql.replace("{domain}", domain)
    for k, v in guard.LIMITS.items():
        sql = sql.replace("{" + k + "}", str(v))
    for k, v in guard.MESSAGES.items():
        sql = sql.replace("{MSG_" + k + "}", v.replace("'", "''"))
    assert "{" not in re.sub(r"\{\d+,?\d*\}", "", sql.split("as $$", 1)[1].split("$$;", 1)[0]), "빠진 값"
    return sql


def main():
    sql = build_sql()
    if "--copy" in sys.argv:
        subprocess.run("clip", input=sql.encode("utf-16-le"), check=True)
        print("복사했어요. Supabase → SQL Editor 에 붙여넣고 Run 하세요.")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(sql)


if __name__ == "__main__":
    main()
