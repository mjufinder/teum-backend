# Supabase

teum 의 데이터베이스 스키마(마이그레이션)를 관리합니다.

## 디렉토리

```
supabase/
└── migrations/
    └── 20261021000000_init_schema.sql   # 초기 스키마 (ERD 11개 테이블)
```

## 적용 방법

### 방법 1. Supabase 대시보드 (가장 간단)

1. Supabase 프로젝트 → **SQL Editor**
2. `migrations/` 의 SQL 내용을 붙여넣고 **Run**

### 방법 2. Supabase CLI

```bash
# CLI 설치 (한 번만)
brew install supabase/tap/supabase

# 프로젝트 연결 후 적용
supabase link --project-ref <your-project-ref>
supabase db push
```

### 방법 3. psql 직접 적용

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/20261021000000_init_schema.sql
```

## 스키마 개요

진행보고서(상세설계) §3 ERD 기준. 11개 테이블:

| 영역 | 테이블 |
| --- | --- |
| 사용자/시간표 | `users`, `timetable_slots` |
| 모임/참여 | `meetings`, `meeting_members`, `meeting_memos` |
| 매칭/투표/확정 | `matching_runs`, `candidate_sets`, `candidates`, `vote_ballots`, `vote_selections`, `confirmed_schedules` |

- 소프트 삭제: `deleted_at`
- 투표 무결성: `vote_selections` 는 복합 FK 로 투표지·후보가 같은 후보 묶음(`set_id`)에 속하도록 강제
- 모임당 확정 일정 1개: `confirmed_schedules.meeting_id` 유니크

## RLS (Row Level Security)

모든 테이블에 RLS 를 **활성화**했습니다.

- 백엔드는 `service_role` 키로 접근하므로 RLS 를 우회합니다.
- 클라이언트(anon/authenticated) 직접 접근 정책은 **인증 연동 시** 테이블별로 추가합니다.
