-- 사용자 행 잠금으로 같은 사용자의 저장을 직렬화한다.
-- 백엔드가 검증한 내부 user_id만 전달하며 클라이언트 직접 호출은 금지한다.
create function public.save_timetable(
    p_user_id bigint, p_class_bits text, p_manual_bits text
)
returns table (
    class_bits text, manual_bits text, available_bits text,
    timetable_version integer, timetable_registered_at timestamptz,
    updated_at timestamptz
)
language plpgsql
security invoker
set search_path = ''
as $$
declare
    saved public.timetables%rowtype;
    changed boolean;
begin
    -- bit(n) 캐스팅의 자동 잘림/패딩 전에 원본 길이를 검사한다.
    if p_class_bits is null or p_manual_bits is null
       or length(p_class_bits) <> 182 or length(p_manual_bits) <> 182
       or p_class_bits ~ '[^01]' or p_manual_bits ~ '[^01]' then
        raise exception using errcode = '22023', message = 'Expected 182 binary digits';
    end if;

    perform 1 from public.users u
    where u.id = p_user_id and u.deleted_at is null for update;
    if not found then
        raise exception using errcode = 'PT401', message = 'Inactive or missing user';
    end if;

    select t.* into saved from public.timetables t where t.user_id = p_user_id;
    changed := not found;
    if changed then
        insert into public.timetables(user_id, class_bits, manual_bits)
        values(p_user_id, p_class_bits::bit(182), p_manual_bits::bit(182));
    elsif saved.class_bits::text <> p_class_bits or saved.manual_bits::text <> p_manual_bits then
        changed := true;
        update public.timetables t
        set class_bits = p_class_bits::bit(182), manual_bits = p_manual_bits::bit(182)
        where t.user_id = p_user_id;
    end if;

    if changed then
        update public.users u
        set timetable_registered_at = coalesce(u.timetable_registered_at, now()),
            timetable_version = u.timetable_version + 1
        where u.id = p_user_id;
    end if;

    return query
    select t.class_bits::text, t.manual_bits::text, t.available_bits::text,
           u.timetable_version, u.timetable_registered_at, t.updated_at
    from public.timetables t join public.users u on u.id = t.user_id
    where t.user_id = p_user_id;
end;
$$;

revoke all on function public.save_timetable(bigint, text, text) from public, anon, authenticated;
grant execute on function public.save_timetable(bigint, text, text) to service_role;
