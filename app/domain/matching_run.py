from __future__ import annotations

from datetime import datetime

from app.repositories.matching_run_repository import MatchingRunRepository


class MatchingRun:
    """공강 계산 실행/이력 도메인 객체 (클래스 다이어그램의 MATCHING_RUN).

    한 번의 공강 계산 실행을 나타낸다. 비트 벡터 AND 연산으로 공통 공강을
    구하고 상위 후보를 추천한다. DB 입출력은 `MatchingRunRepository` 에 위임.

    > 핵심 알고리즘(비트 벡터 공강 계산)은 보고서 §3-다 참고.
    >   주간 120 슬롯을 가능(1)/불가(0) 비트 벡터로 모델링 →
    >   참여자 벡터들에 비트 AND → 모두 1인 구간이 공통 공강. O(N).
    """

    SLOT_COUNT = 120  # 주간 시간 슬롯 수 (보고서 §3-다)

    # ── 속성 (클래스 다이어그램 기준) ──────────────────────────────
    def __init__(
        self,
        *,
        run_id: int | None,
        meeting_id: int,
        trigger_type: str,
        cond_snapshot: dict,
        total_member_count: int,
        timetable_input_count: int,
        input_hash: str,
        calculated_at: datetime | None = None,
        repo: MatchingRunRepository,
    ):
        self.run_id = run_id                            # Long
        self.meeting_id = meeting_id                    # Long
        self.trigger_type = trigger_type                # String (JOIN/ADMIN_RECALC/PRE_CONFIRM_RECHECK)
        self.cond_snapshot = cond_snapshot              # Map<String,Object> (jsonb)
        self.total_member_count = total_member_count    # Integer
        self.timetable_input_count = timetable_input_count  # Integer
        self.input_hash = input_hash                    # String (입력 상태 비교용 해시)
        self.calculated_at = calculated_at              # LocalDateTime
        self._repo = repo

    @classmethod
    def _from_row(cls, row: dict, repo: MatchingRunRepository) -> MatchingRun:
        return cls(
            run_id=row["id"],
            meeting_id=row["meeting_id"],
            trigger_type=row["trigger_type"],
            cond_snapshot=row["cond_snapshot"],
            total_member_count=row["total_member_count"],
            timetable_input_count=row["timetable_input_count"],
            input_hash=row["input_hash"],
            calculated_at=row.get("calculated_at"),
            repo=repo,
        )

    # ── 기능 (클래스 다이어그램 기준) ──────────────────────────────
    @classmethod
    def calculate(
        cls,
        *,
        meeting_id: int,
        trigger_type: str,
        cond_snapshot: dict,
        member_vectors: list[int],
        repo: MatchingRunRepository,
    ):
        """공강 계산 실행 → calculate():CANDIDATE_SET.

        1) 실행 이력(MatchingRun) 기록 →
        2) find_common_free_time 로 공통 공강 비트 벡터 산출 →
        3) recommend_top3 로 CandidateSet 생성.
        """
        run_row = repo.insert(
            {
                "meeting_id": meeting_id,
                "trigger_type": trigger_type,
                "cond_snapshot": cond_snapshot,
                "total_member_count": len(member_vectors),
                "timetable_input_count": sum(1 for v in member_vectors if v),
                "input_hash": cls._hash_inputs(member_vectors),
            }
        )
        run = cls._from_row(run_row, repo)
        common = run.find_common_free_time(member_vectors)
        return run.recommend_top3(common)

    def find_common_free_time(self, member_vectors: list[int]) -> int:
        """공통 공강 비트 벡터 계산 → findCommonFreeTime():CANDIDATE[].

        각 참여자의 120비트 가용 벡터에 비트 AND 를 누적 → 모두 1인
        슬롯만 1로 남는다. 워드 단위 연산이라 참여자 수 N 에 선형(O(N)).
        """
        if not member_vectors:
            return 0
        common = (1 << self.SLOT_COUNT) - 1  # 전 슬롯 가능으로 시작
        for vec in member_vectors:
            common &= vec
        return common

    def recommend_top3(self, common_free: int):
        """상위 3개 후보 추천 → recommendTop3():CANDIDATE_SET.

        공통 공강 비트 벡터에서 min_duration/travel_buffer 조건을 만족하는
        연속 구간을 뽑아 득표 전 후보 묶음(CandidateSet)을 만든다.
        """
        # TODO: 비트 벡터 → 연속 가용 구간 추출 → rank 상위 3개 Candidate 생성
        #       → CandidateSet 반환. (CandidateSet/Candidate 영속성 연동)
        raise NotImplementedError("후보 추출/저장은 CandidateSet·Candidate 연동 후 구현 예정입니다.")

    def recheck(self, member_vectors: list[int]) -> bool:
        """확정 직전 재검사 → recheck():Boolean.

        최근 입력 해시와 현재 입력 해시가 같으면(변경 없음) True.
        시간표가 바뀌었으면 False → 재계산 필요.
        """
        return self.input_hash == self._hash_inputs(member_vectors)

    @staticmethod
    def _hash_inputs(member_vectors: list[int]) -> str:
        """입력 상태(참여자 벡터 집합)를 비교용 해시 문자열로 변환."""
        import hashlib

        joined = ",".join(str(v) for v in member_vectors)
        return hashlib.sha256(joined.encode()).hexdigest()
