-- =============================================================
-- Supabase Auth 연동
-- users 를 Supabase 인증 유저(auth.users)와 연결한다.
-- 로그인/회원가입(이메일·구글)은 Supabase Auth 가 담당하고,
-- 백엔드는 auth_uid 기준으로 public.users 행을 프로비저닝한다.
-- =============================================================

alter table users
    add column auth_uid uuid unique references auth.users (id) on delete cascade,
    add column email    text;

-- 식별을 Supabase Auth 가 담당하므로 기존 소셜 식별 컬럼은 선택값으로 완화
alter table users alter column provider         drop not null;
alter table users alter column provider_user_id drop not null;
alter table users drop constraint if exists uq_users_provider;

comment on column users.auth_uid is 'Supabase auth.users.id (이메일/구글 로그인 공통 식별자)';
comment on column users.email    is 'Supabase 인증 이메일 (표시/검색용 사본)';
