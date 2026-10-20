# teum-backend

teum (mjufinder) 프로젝트의 백엔드 API 서버입니다.

## 기술 스택

- **Python FastAPI** — API 프레임워크 (비트맵 연산 구현 고려)
- **Supabase** — DB / 인증 (PGVector 지원)
- **Pydantic** — 데이터 검증 / 설정 관리
- **Uvicorn** — ASGI 서버
- **pytest** — 테스트

## 요구사항

- Python 3.11+

## 시작하기

```bash
# 1. 가상환경 생성 & 활성화
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 에 Supabase 값을 채워주세요.

# 4. 개발 서버 실행
uvicorn app.main:app --reload
```

- API 서버: [http://localhost:8000](http://localhost:8000)
- Swagger 문서: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc 문서: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 환경변수

| 변수 | 설명 |
| --- | --- |
| `PROJECT_NAME` | 프로젝트 이름 |
| `DEBUG` | 디버그 모드 |
| `CORS_ORIGINS` | 허용할 프론트엔드 주소 (쉼표 구분) |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase service_role / anon 키 |

## 프로젝트 구조

```
app/
├── main.py           # FastAPI 앱 진입점, CORS, 라우터 등록
├── core/
│   ├── config.py     # 환경설정 (pydantic-settings)
│   └── supabase.py   # Supabase 클라이언트 (의존성 주입)
├── api/
│   ├── router.py     # 라우터 집약
│   └── routes/       # 기능별 엔드포인트 (모듈 단위)
│       └── health.py
├── schemas/          # Pydantic 요청/응답 모델
└── services/         # 비즈니스 로직
tests/                # pytest 테스트
```

## 모듈 단위 개발 방식

1. `app/api/routes/` 에 기능별 라우터 파일 추가 (예: `items.py`)
2. `app/schemas/` 에 요청/응답 스키마 정의
3. `app/services/` 에 비즈니스 로직 작성
4. `app/api/router.py` 에 `include_router` 로 등록
5. `/docs` 에서 자동 생성된 API 명세를 프론트엔드와 공유

## 테스트

```bash
pytest
```

## 연관 레포

- 프론트엔드: [teum-frontend](https://github.com/mjufinder/teum-frontend)
- 문서: [teum-docs](https://github.com/mjufinder/teum-docs)
