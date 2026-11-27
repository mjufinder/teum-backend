-- 공개 공지 목록의 삭제 필터 및 최신순 페이지 조회를 지원한다.
create index idx_notices_active_created_id
    on public.notices (created_at desc, id desc)
    where deleted_at is null;
