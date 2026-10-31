-- 마이그레이션 적용 후 psql -v ON_ERROR_STOP=1로 실행. 테스트 데이터는 롤백.
begin;
do $$
declare
    first_user bigint;
    second_user bigint;
    result record;
    original_time timestamptz;
    original_update timestamptz;
begin
    insert into public.users(name) values ('timetable test A') returning id into first_user;
    insert into public.users(name) values ('timetable test B') returning id into second_user;

    select * into result from public.save_timetable(first_user, '0' || repeat('1',181), repeat('1',182));
    assert result.timetable_version = 1;
    assert result.available_bits = '0' || repeat('1',181);
    assert result.timetable_registered_at is not null;
    original_time := result.timetable_registered_at;
    original_update := result.updated_at;

    select * into result from public.save_timetable(first_user, '0' || repeat('1',181), repeat('1',182));
    assert result.timetable_version = 1;
    assert result.updated_at = original_update;

    select * into result from public.save_timetable(first_user, '0' || repeat('1',181), repeat('1',130) || repeat('0',52));
    assert result.timetable_version = 2;
    assert result.timetable_registered_at = original_time;
    assert result.available_bits = '0' || repeat('1',129) || repeat('0',52);

    perform * from public.save_timetable(second_user, repeat('1',182), repeat('1',182));
    assert (select t.available_bits::text = repeat('1',182) from public.timetables t where user_id=second_user);
    assert (select count(*) = 1 from public.timetables where user_id=first_user);

    begin
        perform * from public.save_timetable(first_user, repeat('1',183), repeat('1',182));
        raise exception 'Invalid length accepted';
    exception when invalid_parameter_value then null;
    end;
    assert (select timetable_version = 2 from public.users where id=first_user);

    update public.users set deleted_at=now() where id=first_user;
    begin
        perform * from public.save_timetable(first_user, repeat('1',182), repeat('1',182));
        raise exception 'Deleted user accepted';
    exception when sqlstate 'PT401' then null;
    end;
    assert not has_function_privilege('anon', 'public.save_timetable(bigint,text,text)', 'EXECUTE');
    assert not has_function_privilege('authenticated', 'public.save_timetable(bigint,text,text)', 'EXECUTE');
    assert has_function_privilege('service_role', 'public.save_timetable(bigint,text,text)', 'EXECUTE');
end;
$$;
rollback;
