# 주간 추천 후보 저장 및 조회

## 주간 후보

후보는 날짜 대신 `day_of_week`(월=0, 화=1, 수=2, 목=3, 금=4, 토=5, 일=6),
`start_time`, `end_time`으로 저장한다. 시각은 한국 현지 시각이며 UTC 변환을 하지 않는다.

```json
{
  "candidate_id": 10,
  "rank_no": 1,
  "day_of_week": 0,
  "start_time": "10:00:00",
  "end_time": "11:00:00",
  "available_count": 2,
  "available_member_ids": [1, 2]
}
```

- 월~일 09~22시, 시작 시각 30분 간격으로 탐색한다.
- 회의 길이, 일일 탐색 시간대, 회의 전후 이동 여유를 적용한다.
- 수업/수동 불가 시간을 모두 반영하며 미등록 시간표는 참여 가능 인원에서 제외한다.
- 참여 가능 인원수 내림차순 → 월~일 → 이른 시작 시각순으로 최대 3개를 고른다.
- 겹치는 후보는 허용한다. 참여 가능 인원 0명인 구간은 제외한다.
- 현재 날짜/과거 여부/모임 날짜 기간으로 필터링하지 않는다.
- 모임 API의 `period_start`, `period_end`는 호환성을 위해 유지하지만 추천에 사용하지 않는다.

## 자동 연결

`POST /api/v1/meetings/{meeting_id}/members` 성공 시 다음 처리가 끝난다.

1. 팀원 등록/재가입, 이전 OPEN 후보 폐기, `needs_recalc=true` 설정,
   전체 팀원 시간표와 모임 조건 스냅샷 및 계산 실행 생성
2. `calculate_weekly_candidates()`에서 요일별 계산과 후보 선정
3. 최신 실행/입력 변경 여부 검증 후 후보 저장과 `needs_recalc=false`를 한 트랜잭션으로 처리

실패 시 등록은 유지되고 503의 `detail.member_added=true`로 알린다.
같은 팀원 추가 요청을 재전송하면 재계산 미완료 상태에서 중복 등록 없이 재시도한다.
이미 계산까지 완료된 활성 팀원 추가는 409다. 실패 후 재시도 성공 응답도 201이다.

## 저장과 조회

별도 저장 POST API는 없다. `GET /api/v1/meetings/{meeting_id}/candidates`는
활성 팀원에게 최신 저장 후보를 반환한다.
`meeting_id`, `run_id`, `set_id`, `result_status`, `vote_status`, `created_at`, `candidates`를 포함한다.
팀원 ID는 `users.id`가 아닌 **meeting_members.id**다.

독립 저장 계약은 아래와 같다. 합류 흐름은 스냅샷 검증까지 수행하는
`join_member_and_prepare_matching` / `complete_join_matching` RPC를 사용한다.

```python
saved = save_recommended_candidates(
    run_id=run_id,
    candidates=[CandidateInput(
        day_of_week=0, start_time="10:00", end_time="11:00",
        available_count=2, available_member_ids=[member_id_a, member_id_b],
    )],
    repository=repository,
)
```

- 200 + 빈 목록: 계산했지만 가능 후보 없음 (`NO_CANDIDATE`, `CLOSED`)
- 404: 모임이 없거나 최신 실행의 후보 묶음이 아직 없음
- 401/403: 인증 없음/활성 팀원 아님
- 503: DB 조회 실패

새 결과는 기존 후보를 덮어쓰지 않고 이전 OPEN 묶음을 DISCARDED로 바꾼다.
과거 후보/투표 ID는 보존한다. 투표 화면과 투표 API는 OPEN 여부를 확인해야 한다.
최종 확정 이력은 별도 기능이다. `matching_runs`는 후보 묶음의 실행 컨텍스트다.

## 마이그레이션

`20261108000000_recommended_candidates.sql`, `20261108010000_join_matching.sql`,
`20261108020000_weekly_candidates.sql`을 순서대로 적용한다.
마지막 마이그레이션은 기존 후보의 한국 시간 기준 요일/시각을 변환하고 날짜 컬럼을 제거한다.
후보 ID·묶음 ID·순위·투표 참조를 유지하며 기존 후보를 재선정하지는 않는다.

```powershell
npx supabase migration up --local
.\.venv\Scripts\python.exe -m pytest -q
```

백엔드는 service_role 키를 사용한다. anon/authenticated의 직접 RPC 실행은 금지한다.
`tests/test_recommended_candidates.sql`, `tests/test_join_matching.sql`은
최신 마이그레이션을 적용한 테스트 DB에서 BEGIN/ROLLBACK으로 감싸 실행한다.
