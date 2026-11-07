-- 입력 스냅샷: 시간표/멤버/조건을 하나의 SQL 스냅샷으로 읽는다.
create function public.meeting_matching_input(p_meeting_id bigint)
returns jsonb language sql stable security invoker set search_path = '' as $$
    select jsonb_build_object('meeting', jsonb_build_object(
        'period_start', m.period_start, 'period_end', m.period_end,
        'search_start_time', m.search_start_time, 'search_end_time', m.search_end_time,
        'min_duration_min', m.min_duration_min, 'travel_buffer_min', m.travel_buffer_min),
        'members', coalesce((select jsonb_agg(jsonb_build_object(
            'member_id', mm.id, 'user_id', mm.user_id,
            'class_bits', t.class_bits::text, 'manual_bits', t.manual_bits::text,
            'timetable_version', u.timetable_version) order by mm.id)
        from public.meeting_members mm join public.users u on u.id = mm.user_id
        left join public.timetables t on t.user_id = mm.user_id
        where mm.meeting_id = m.id and mm.status = 'ACTIVE' and u.deleted_at is null), '[]'::jsonb))
    from public.meetings m where m.id = p_meeting_id and m.deleted_at is null;
$$;

create function public.join_member_and_prepare_matching(p_meeting_id bigint, p_user_id bigint)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    meeting public.meetings%rowtype;
    member public.meeting_members%rowtype;
    snapshot jsonb;
    run bigint;
begin
    select * into meeting from public.meetings
    where id = p_meeting_id and deleted_at is null for update;
    if not found then
        raise exception using errcode = 'PT404', message = 'Meeting not found';
    end if;
    perform 1 from public.users where id = p_user_id and deleted_at is null;
    if not found then
        raise exception using errcode = 'PT404', message = 'User not found';
    end if;
    select * into member from public.meeting_members
    where meeting_id = p_meeting_id and user_id = p_user_id;
    if found then
        if member.status = 'ACTIVE' and not meeting.needs_recalc then
            raise exception using errcode = 'PT409', message = 'Already a member';
        end if;
        if member.status <> 'ACTIVE' then
            update public.meeting_members set status = 'ACTIVE', role = 'MEMBER'
            where id = member.id returning * into member;
        end if;
    else
        insert into public.meeting_members(meeting_id, user_id, role, status)
        values(p_meeting_id, p_user_id, 'MEMBER', 'ACTIVE') returning * into member;
    end if;
    update public.meetings set needs_recalc = true where id = p_meeting_id;
    update public.candidate_sets s set vote_status = 'DISCARDED'
    from public.matching_runs r
    where r.id = s.run_id and r.meeting_id = p_meeting_id and s.vote_status = 'OPEN';
    snapshot := public.meeting_matching_input(p_meeting_id);
    insert into public.matching_runs(meeting_id, trigger_type, cond_snapshot,
        total_member_count, timetable_input_count, input_hash)
    values(p_meeting_id, 'JOIN', jsonb_build_object('input_state', snapshot),
        jsonb_array_length(snapshot->'members'),
        (select count(*) from jsonb_array_elements(snapshot->'members') item
         where item->>'class_bits' is not null), md5(snapshot::text)) returning id into run;
    return jsonb_build_object('run_id', run, 'member', to_jsonb(member), 'input_state', snapshot);
end;
$$;

create function public.complete_join_matching(p_run_id bigint, p_candidates jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
    run public.matching_runs%rowtype;
    result jsonb;
begin
    select * into run from public.matching_runs where id = p_run_id;
    if not found then
        raise exception using errcode = 'PT404', message = 'Run not found';
    end if;
    perform 1 from public.meetings where id = run.meeting_id and deleted_at is null for update;
    if not found then
        raise exception using errcode = 'PT404', message = 'Meeting not found';
    end if;
    -- 저장 중 멤버 탈퇴/시간표 저장이 검증을 추월하지 않도록 잠근다.
    -- save_timetable은 users 행을 FOR UPDATE로 잠그므로 시간표 변경도 직렬화된다.
    perform 1 from public.meeting_members where meeting_id = run.meeting_id for share;
    perform 1 from public.users where id in (
        select user_id from public.meeting_members where meeting_id = run.meeting_id
    ) order by id for share;
    if run.cond_snapshot->'input_state' is distinct from public.meeting_matching_input(run.meeting_id) then
        raise exception using errcode = 'PT409', message = 'Matching input changed';
    end if;
    result := public.save_recommended_candidates(p_run_id, p_candidates);
    update public.meetings set needs_recalc = false where id = run.meeting_id;
    return result;
end;
$$;

revoke all on function public.meeting_matching_input(bigint) from public, anon, authenticated;
revoke all on function public.join_member_and_prepare_matching(bigint,bigint) from public, anon, authenticated;
revoke all on function public.complete_join_matching(bigint,jsonb) from public, anon, authenticated;
grant execute on function public.meeting_matching_input(bigint) to service_role;
grant execute on function public.join_member_and_prepare_matching(bigint,bigint) to service_role;
grant execute on function public.complete_join_matching(bigint,jsonb) to service_role;
