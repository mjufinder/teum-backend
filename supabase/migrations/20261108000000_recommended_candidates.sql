-- 투표용 추천 후보 저장. 확정 일정(confirmed_schedules)과 별개이다.
alter table public.candidates
    add column available_member_ids bigint[] not null default '{}';

create function public.get_latest_recommended_candidates(p_meeting_id bigint)
returns jsonb language sql stable security invoker set search_path = ''
as $$
    select jsonb_build_object(
        'meeting_id', r.meeting_id, 'run_id', r.id, 'set_id', s.id,
        'result_status', s.result_status, 'vote_status', s.vote_status,
        'created_at', s.created_at,
        'candidates', coalesce((
            select jsonb_agg(jsonb_build_object(
                'candidate_id', c.id, 'rank_no', c.rank_no,
                'start_at', c.start_at, 'end_at', c.end_at,
                'available_count', c.available_count,
                'available_member_ids', c.available_member_ids
            ) order by c.rank_no)
            from public.candidates c where c.set_id = s.id
        ), '[]'::jsonb)
    )
    from (
        select id, meeting_id from public.matching_runs
        where meeting_id = p_meeting_id order by id desc limit 1
    ) r
    join lateral (
        select * from public.candidate_sets
        where run_id = r.id and set_type = 'RECOMMEND'
        order by id desc limit 1
    ) s on true;
$$;

create function public.save_recommended_candidates(p_run_id bigint, p_candidates jsonb)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare
    target_meeting bigint;
    target_set bigint;
    item jsonb;
    member_ids bigint[];
    position integer := 0;
begin
    if p_candidates is null or jsonb_typeof(p_candidates) <> 'array' then
        raise exception using errcode = '22023', message = 'Expected candidate array';
    end if;
    if jsonb_array_length(p_candidates) > 3 then
        raise exception using errcode = '22023', message = 'At most three candidates';
    end if;
    select meeting_id into target_meeting from public.matching_runs where id = p_run_id;
    if not found then
        raise exception using errcode = 'PT404', message = 'Matching run not found';
    end if;
    -- 같은 모임의 후보 교체를 직렬화하고 묶음/후보를 한 트랜잭션으로 저장한다.
    perform 1 from public.meetings
    where id = target_meeting and deleted_at is null for update;
    if not found then
        raise exception using errcode = 'PT404', message = 'Meeting not found';
    end if;
    if exists (select 1 from public.matching_runs
               where meeting_id = target_meeting and id > p_run_id)
       or exists (select 1 from public.candidate_sets
                  where run_id = p_run_id and set_type = 'RECOMMEND') then
        raise exception using errcode = 'PT409', message = 'Stale or already saved run';
    end if;

    update public.candidate_sets s set vote_status = 'DISCARDED'
    from public.matching_runs r
    where s.run_id = r.id and r.meeting_id = target_meeting and s.vote_status = 'OPEN';

    insert into public.candidate_sets(run_id, set_type, result_status, vote_status)
    values(p_run_id, 'RECOMMEND',
           case when jsonb_array_length(p_candidates) = 0 then 'NO_CANDIDATE' else 'HAS_CANDIDATE' end,
           case when jsonb_array_length(p_candidates) = 0 then 'CLOSED' else 'OPEN' end)
    returning id into target_set;

    for item in select value from jsonb_array_elements(p_candidates) loop
        position := position + 1;
        if not (item ?& array['rank_no', 'start_at', 'end_at', 'available_count', 'available_member_ids'])
           or (item->>'rank_no')::integer is distinct from position
           or jsonb_typeof(item->'available_member_ids') is distinct from 'array' then
            raise exception using errcode = '22023', message = 'Invalid candidate';
        end if;
        select coalesce(array_agg(value::bigint), '{}'::bigint[]) into member_ids
        from jsonb_array_elements_text(item->'available_member_ids');
        if cardinality(member_ids) = 0
           or (item->>'available_count')::integer is distinct from cardinality(member_ids)
           or (select count(distinct id) from unnest(member_ids) id) <> cardinality(member_ids)
           or exists (
               select 1 from unnest(member_ids) as requested(member_id)
               where not exists (select 1 from public.meeting_members m
                                 where m.id = requested.member_id and m.meeting_id = target_meeting and m.status = 'ACTIVE')
           ) then
            raise exception using errcode = '22023', message = 'Invalid available members';
        end if;
        insert into public.candidates(set_id, rank_no, start_at, end_at, available_count, available_member_ids)
        values(target_set, position, (item->>'start_at')::timestamptz,
               (item->>'end_at')::timestamptz, cardinality(member_ids), member_ids);
    end loop;
    return public.get_latest_recommended_candidates(target_meeting);
end;
$$;

-- 권한 검증을 거친 백엔드만 호출한다. 브라우저의 직접 RPC 접근은 금지한다.
revoke all on function public.save_recommended_candidates(bigint, jsonb) from public, anon, authenticated;
revoke all on function public.get_latest_recommended_candidates(bigint) from public, anon, authenticated;
grant execute on function public.save_recommended_candidates(bigint, jsonb) to service_role;
grant execute on function public.get_latest_recommended_candidates(bigint) to service_role;
