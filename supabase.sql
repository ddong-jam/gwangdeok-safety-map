-- 광덕 안전지도 · 공용 모드 데이터베이스 (Supabase → SQL Editor 에 통째로 붙여넣고 Run)
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
grant insert (id, map, x, y, category, severity, title, spot, description, reporter, photo)
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

-- ── 학생에게 보이는 신고 (공개 칸만) ──────────────
-- 뷰는 만든 사람 권한으로 돌아서 위 RLS 와 상관없이 이 칸들만 보여준다
create or replace view public.public_reports as
  select id, created_at, map, x, y, category, severity, title, spot, status
  from public.reports;
grant select on public.public_reports to anon, authenticated;

-- ── 선생님 계정 등록 ─────────────────────────────
-- 1) Authentication → Users → Add user 로 이메일·비밀번호 계정을 만든 뒤
-- 2) 아래 줄의 이메일을 바꿔서 실행 (선생님마다 한 번씩)
-- insert into public.admins (user_id) select id from auth.users where email = 'teacher@example.com';
