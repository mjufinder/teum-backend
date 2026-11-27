create table public.notice_comments (
    id bigint generated always as identity primary key,
    notice_id bigint not null references public.notices(id),
    author_user_id bigint not null references public.users(id),
    content text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    deleted_at timestamptz,
    constraint ck_notice_comments_content check (
        char_length(content) between 1 and 1000 and content ~ '[^[:space:]]'
    )
);

create index idx_notice_comments_notice_created_id
    on public.notice_comments (notice_id, created_at, id) where deleted_at is null;
create index idx_notice_comments_author on public.notice_comments (author_user_id);

alter table public.notice_comments enable row level security;
revoke all on public.notice_comments from public, anon, authenticated;
grant select, insert, update, delete on public.notice_comments to service_role;
revoke all on sequence public.notice_comments_id_seq from public, anon, authenticated;
grant usage, select on sequence public.notice_comments_id_seq to service_role;

-- 공지 삭제와 댓글 작성이 동시에 진행되어도 부모 확인과 INSERT가 분리되지 않게 한다.
-- service_role 전용 RPC이며 작성자는 API가 검증된 사용자 ID로 전달한다.
create function public.create_notice_comment(
    p_notice_id bigint, p_author_user_id bigint, p_content text
)
returns setof public.notice_comments
language plpgsql
security invoker
set search_path = ''
as $$
begin
    perform 1 from public.notices
    where id = p_notice_id and deleted_at is null
    for update;
    if not found then
        return;
    end if;

    return query
    insert into public.notice_comments (notice_id, author_user_id, content)
    values (p_notice_id, p_author_user_id, p_content)
    returning *;
end;
$$;

revoke all on function public.create_notice_comment(bigint, bigint, text)
    from public, anon, authenticated;
grant execute on function public.create_notice_comment(bigint, bigint, text) to service_role;
