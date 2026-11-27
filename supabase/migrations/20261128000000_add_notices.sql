-- 서비스 관리자 권한은 운영자가 지정하며 프로필 수정 API로 변경하지 않는다.
alter table public.users
    add column role text not null default 'USER'
    constraint ck_users_role check (role in ('USER', 'ADMIN'));

-- 사용자 데이터 변경은 백엔드를 통해서만 수행한다 (역할 직접 변경 방지).
revoke insert, update, delete on public.users from public, anon, authenticated;

create table public.notices (
    id bigint generated always as identity primary key,
    author_user_id bigint not null references public.users(id),
    title text not null,
    content text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz,
    constraint ck_notices_title check (
        char_length(title) between 1 and 200 and title ~ '[^[:space:]]'
    ),
    constraint ck_notices_content check (
        char_length(content) between 1 and 10000 and content ~ '[^[:space:]]'
    )
);

alter table public.notices enable row level security;
revoke all on public.notices from public, anon, authenticated;
grant select, insert, update, delete on public.notices to service_role;
revoke all on sequence public.notices_id_seq from public, anon, authenticated;
grant usage, select on sequence public.notices_id_seq to service_role;
