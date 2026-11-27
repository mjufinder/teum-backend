create function public.set_notice_comments_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = clock_timestamp();
    return new;
end;
$$;

create trigger notice_comments_updated_at
before update on public.notice_comments
for each row execute function public.set_notice_comments_updated_at();

-- 부모 공지 -> 댓글 순서로 잠가 삭제와 수정이 동시에 실행되어도 상태 검사를 유지한다.
create function public.update_notice_comment(
    p_notice_id bigint, p_comment_id bigint, p_author_user_id bigint, p_content text
)
returns setof public.notice_comments
language plpgsql
security invoker
set search_path = ''
as $$
declare
    target public.notice_comments%rowtype;
begin
    perform 1 from public.notices
    where id = p_notice_id and deleted_at is null for update;
    if not found then return; end if;

    select * into target from public.notice_comments
    where id = p_comment_id and notice_id = p_notice_id and deleted_at is null
    for update;
    if not found then return; end if;
    if target.author_user_id <> p_author_user_id or p_author_user_id is null then
        raise sqlstate 'PT403' using message = 'Only the comment author can update it';
    end if;

    return query update public.notice_comments
    set content = p_content
    where id = p_comment_id
    returning *;
end;
$$;

revoke all on function public.update_notice_comment(bigint, bigint, bigint, text)
    from public, anon, authenticated;
grant execute on function public.update_notice_comment(bigint, bigint, bigint, text) to service_role;
