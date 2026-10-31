-- 사용자별 주간 시간표. 월~일 순서, 요일별 09:00~22:00의 30분 구간 26개.
-- 1=가능, 0=불가. 기존 timetable_slots와 데이터는 보존하며 자동 변환하지 않는다.
create table public.timetables (
    user_id bigint primary key references public.users(id) on delete cascade,
    class_bits bit(182) not null,
    manual_bits bit(182) not null default repeat('1', 182)::bit(182),
    available_bits bit(182) generated always as (class_bits & manual_bits) stored,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on table public.timetables is '사용자별 182비트 시간표: 월~일, 09~22시, 30분 단위';
comment on column public.timetables.class_bits is '이미지 인식 및 수정된 일정 기준. 1=가능, 0=불가';
comment on column public.timetables.manual_bits is '사용자가 추가한 제약 기준. 1=가능, 0=불가';
comment on column public.timetables.available_bits is 'class_bits & manual_bits로 자동 계산';

create function public.set_timetables_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = clock_timestamp();
    return new;
end;
$$;

create trigger timetables_updated_at
before update on public.timetables
for each row execute function public.set_timetables_updated_at();

-- 기존 테이블과 동일하게 백엔드 service_role을 통해서만 접근한다.
alter table public.timetables enable row level security;
revoke all on public.timetables from anon, authenticated;
grant select, insert, update, delete on public.timetables to service_role;
