-- =============================================================
-- 클래스 다이어그램 갱신 반영 (정리)
--  - 슬롯 기반 시간표(timetable_slots) → 비트 기반(timetables)로 대체됨: 옛 테이블 제거
--  - Supabase Auth 전환으로 users.provider / provider_user_id 미사용: 제거
-- =============================================================

-- 옛 슬롯 테이블 제거 (비트 모델 timetables 로 대체)
drop table if exists timetable_slots;

-- 소셜 식별 컬럼 제거 (식별은 auth_uid 로 일원화)
alter table users drop column if exists provider;
alter table users drop column if exists provider_user_id;
