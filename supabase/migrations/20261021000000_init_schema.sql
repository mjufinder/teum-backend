-- =============================================================
-- Teum 초기 스키마
-- 기준: 진행보고서(상세설계) §3 ERD / 클래스 다이어그램
-- 모든 시각은 timestamptz, 소프트 삭제는 deleted_at 사용
-- =============================================================

-- ----------------------------------------------------------------
-- 1. 사용자 / 시간표 영역
-- ----------------------------------------------------------------

-- 사용자 (USER): 소셜 로그인 사용자 정보와 시간표 등록 상태
create table users (
    id                      bigint generated always as identity primary key,
    provider                text        not null,            -- 소셜 로그인 제공자 (google/kakao/naver)
    provider_user_id        text        not null,            -- 제공자가 부여한 사용자 식별값
    name                    text        not null,
    major                   text,                            -- 전공 (온보딩 전이면 null)
    profile_completed       boolean     not null default false,
    timetable_registered_at timestamptz,                     -- null 이면 시간표 미등록
    timetable_version       integer     not null default 0,  -- 시간표 수정 시 +1
    deleted_at              timestamptz,                     -- 탈퇴 처리(Soft Delete)
    created_at              timestamptz not null default now(),
    -- 소셜 계정은 (provider, provider_user_id) 조합으로 식별 → 플랫폼 간 ID 충돌 방지
    constraint uq_users_provider unique (provider, provider_user_id)
);

-- 시간표 일정 (TIMETABLE_SLOT): 한 행 = 수업 하나
create table timetable_slots (
    id          bigint generated always as identity primary key,
    user_id     bigint   not null references users (id) on delete cascade,
    day_of_week smallint not null,                 -- 0(일)~6(토)
    start_time  time     not null,
    end_time    time     not null,
    title       text     not null,                 -- 과목명/일정명
    created_at  timestamptz not null default now(),
    constraint ck_slot_day   check (day_of_week between 0 and 6),
    constraint ck_slot_time  check (start_time < end_time)  -- 시작 >= 종료 차단
);

create index idx_slot_user on timetable_slots (user_id);

-- ----------------------------------------------------------------
-- 2. 모임 / 참여 영역
-- ----------------------------------------------------------------

-- 모임 (MEETING): 기본 정보 + 공강 탐색 조건 + 초대/공유 정보
create table meetings (
    id                bigint generated always as identity primary key,
    name              text        not null,
    description       text,
    period_start      date        not null,              -- 조회 기간 시작
    period_end        date        not null,              -- 조회 기간 종료
    search_start_time time        not null,              -- 하루 탐색 범위 시작
    search_end_time   time        not null,              -- 하루 탐색 범위 종료
    travel_buffer_min integer     not null default 0,    -- 이동 여유 시간(분)
    min_duration_min  integer     not null,              -- 최소 회의 시간(분)
    needs_recalc      boolean     not null default false,-- 재계산 필요 상태
    invite_code       text        unique,                -- 초대 코드
    invite_expires_at timestamptz,
    share_token       text        unique,                -- 결과 공유 링크 토큰
    deleted_at        timestamptz,
    created_at        timestamptz not null default now(),
    constraint ck_meeting_period   check (period_start <= period_end),
    constraint ck_meeting_search   check (search_start_time < search_end_time),
    constraint ck_meeting_duration check (min_duration_min > 0)
);

-- 모임 구성원 (MEETING_MEMBER): 사용자-모임 연결, 역할/상태
create table meeting_members (
    id         bigint generated always as identity primary key,
    meeting_id bigint not null references meetings (id) on delete cascade,
    user_id    bigint not null references users (id)    on delete cascade,
    role       text   not null default 'MEMBER',   -- ADMIN / MEMBER
    status     text   not null default 'ACTIVE',   -- ACTIVE / LEFT
    created_at timestamptz not null default now(),
    constraint ck_member_role   check (role in ('ADMIN', 'MEMBER')),
    constraint ck_member_status check (status in ('ACTIVE', 'LEFT')),
    -- 중복 가입 차단
    constraint uq_member unique (meeting_id, user_id)
);

create index idx_member_user    on meeting_members (user_id);
create index idx_member_meeting on meeting_members (meeting_id);

-- 모임 메모 (MEETING_MEMO)
create table meeting_memos (
    id             bigint generated always as identity primary key,
    meeting_id     bigint not null references meetings (id) on delete cascade,
    author_user_id bigint not null references users (id),
    content        text   not null,
    deleted_at     timestamptz,
    created_at     timestamptz not null default now()
);

create index idx_memo_meeting on meeting_memos (meeting_id);

-- ----------------------------------------------------------------
-- 3. 매칭 / 투표 / 확정 영역
-- ----------------------------------------------------------------

-- 매칭 계산 이력 (MATCHING_RUN): 공강 계산 실행마다 한 행
create table matching_runs (
    id                   bigint generated always as identity primary key,
    meeting_id           bigint not null references meetings (id) on delete cascade,
    trigger_type         text   not null,          -- JOIN / ADMIN_RECALC / PRE_CONFIRM_RECHECK
    cond_snapshot        jsonb  not null,           -- 계산 당시 탐색 조건
    total_member_count   integer not null,
    timetable_input_count integer not null,
    input_hash           text   not null,           -- 입력 상태 비교용 해시
    calculated_at        timestamptz not null default now(),
    constraint ck_run_trigger check (trigger_type in ('JOIN', 'ADMIN_RECALC', 'PRE_CONFIRM_RECHECK'))
);

-- 최신 결과 빠른 조회
create index idx_run_meeting_calc on matching_runs (meeting_id, calculated_at desc);

-- 후보 묶음 (CANDIDATE_SET): 투표 라운드 단위
create table candidate_sets (
    id            bigint generated always as identity primary key,
    run_id        bigint not null references matching_runs (id) on delete cascade,
    set_type      text   not null,          -- RECOMMEND(일반 추천) / ALTERNATIVE(차선책)
    reason        text,                      -- 차선책 진입 사유
    result_status text   not null,          -- HAS_CANDIDATE / NO_CANDIDATE
    vote_status   text   not null default 'OPEN', -- OPEN / CLOSED / DISCARDED
    created_at    timestamptz not null default now(),
    constraint ck_set_type   check (set_type in ('RECOMMEND', 'ALTERNATIVE')),
    constraint ck_set_result check (result_status in ('HAS_CANDIDATE', 'NO_CANDIDATE')),
    constraint ck_set_vote   check (vote_status in ('OPEN', 'CLOSED', 'DISCARDED')),
    -- 투표-후보 동일 집합 검증용 복합 FK 대상
    constraint uq_set_id unique (id, run_id)
);

create index idx_set_run on candidate_sets (run_id);

-- 후보 시간대 (CANDIDATE): 묶음당 최대 3개 (3개 제한은 애플리케이션 규칙)
create table candidates (
    id              bigint generated always as identity primary key,
    set_id          bigint not null references candidate_sets (id) on delete cascade,
    rank_no         integer not null,          -- 묶음 내 추천 순위
    start_at        timestamptz not null,
    end_at          timestamptz not null,
    available_count integer not null,          -- 참석 가능 인원 수
    constraint ck_cand_time check (start_at < end_at),
    -- 같은 묶음 내 순위 중복 방지
    constraint uq_cand_rank unique (set_id, rank_no),
    -- 투표 선택의 동일 집합 검증용 복합 유니크
    constraint uq_cand_id unique (id, set_id)
);

create index idx_cand_set on candidates (set_id);

-- 투표지 (VOTE_BALLOT): 구성원 1명이 후보 묶음 1개에 제출한 투표 1건
create table vote_ballots (
    id           bigint generated always as identity primary key,
    set_id       bigint not null references candidate_sets (id) on delete cascade,
    member_id    bigint not null references meeting_members (id) on delete cascade,
    no_available boolean not null default false, -- '참석 가능 후보 없음'
    created_at   timestamptz not null default now(),
    -- 한 묶음에 구성원당 투표지 1개
    constraint uq_ballot unique (set_id, member_id),
    -- 선택 항목의 동일 집합 검증용 복합 유니크
    constraint uq_ballot_id unique (id, set_id)
);

-- 투표 선택 항목 (VOTE_SELECTION): 투표지에서 선택한 후보
create table vote_selections (
    ballot_id    bigint not null,
    candidate_id bigint not null,
    set_id       bigint not null,            -- 정합성 검증용
    primary key (ballot_id, candidate_id),
    -- 투표지/후보가 반드시 같은 후보 묶음(set_id)에 속하도록 복합 FK 로 강제
    constraint fk_sel_ballot    foreign key (ballot_id, set_id)    references vote_ballots (id, set_id) on delete cascade,
    constraint fk_sel_candidate foreign key (candidate_id, set_id) references candidates (id, set_id)   on delete cascade
);

create index idx_sel_candidate on vote_selections (candidate_id);

-- 확정 일정 (CONFIRMED_SCHEDULE): 모임당 1개
create table confirmed_schedules (
    id             bigint generated always as identity primary key,
    meeting_id     bigint not null references meetings (id) on delete cascade,
    candidate_id   bigint not null references candidates (id),
    recheck_run_id bigint not null references matching_runs (id), -- 확정 직전 재검사 이력
    confirmed_at   timestamptz not null default now(),
    -- 모임당 확정 일정 1개 제약
    constraint uq_confirmed_meeting unique (meeting_id)
);

-- ----------------------------------------------------------------
-- 4. RLS 활성화
--    백엔드는 service_role 키로 접근하므로 RLS 를 우회한다.
--    클라이언트(anon/authed) 직접 접근 정책은 인증 연동 시 테이블별로 추가한다.
-- ----------------------------------------------------------------
alter table users               enable row level security;
alter table timetable_slots     enable row level security;
alter table meetings            enable row level security;
alter table meeting_members     enable row level security;
alter table meeting_memos       enable row level security;
alter table matching_runs       enable row level security;
alter table candidate_sets      enable row level security;
alter table candidates          enable row level security;
alter table vote_ballots        enable row level security;
alter table vote_selections     enable row level security;
alter table confirmed_schedules enable row level security;
