-- 작성·수정과 동일하게 부모 공지 -> 댓글 순서로 잠근다.
create function public.delete_notice_comment(
    p_notice_id bigint, p_comment_id bigint, p_author_user_id bigint
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
        raise sqlstate 'PT403' using message = 'Only the comment author can delete it';
    end if;

    return query update public.notice_comments
    set deleted_at = clock_timestamp()
    where id = p_comment_id
    returning *;
end;
$$;

revoke all on function public.delete_notice_comment(bigint, bigint, bigint)
    from public, anon, authenticated;
grant execute on function public.delete_notice_comment(bigint, bigint, bigint) to service_role;
