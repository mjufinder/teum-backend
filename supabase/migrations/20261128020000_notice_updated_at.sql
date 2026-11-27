-- 수정 시각은 클라이언트 입력 대신 DB에서 관리한다.
create function public.set_notices_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = clock_timestamp();
    return new;
end;
$$;

create trigger notices_updated_at
before update on public.notices
for each row execute function public.set_notices_updated_at();
