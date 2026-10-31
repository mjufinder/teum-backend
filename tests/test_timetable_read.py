from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from httpx import ConnectError
from postgrest.exceptions import APIError

from app.api.deps import get_current_user, get_timetable_repository
from app.core.supabase import get_supabase
from app.main import app
from app.repositories.timetable_repository import TimetableRepository

URL = "/api/v1/timetable"


@pytest.fixture
def setup():
    previous = app.dependency_overrides.copy()
    repo = Mock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=42)
    app.dependency_overrides[get_timetable_repository] = lambda: repo
    with TestClient(app) as client:
        yield client, repo
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def test_read_preserves_saved_data_and_uses_authenticated_user(setup):
    client, repo = setup
    row = dict(class_bits="0" + "1" * 181, manual_bits="1" * 130 + "0" * 52,
               available_bits="0" + "1" * 129 + "0" * 52,
               timetable_version=3, timetable_registered_at="2026-11-01T00:00:00Z",
               updated_at="2026-11-01T01:00:00Z")
    repo.find_by_user.return_value = row
    response = client.get(URL, params={"user_id": 99})
    assert response.status_code == 200
    body = response.json()
    for key, value in row.items():
        assert body[key] == value
    assert body["days"] == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    assert (body["start_time"], body["end_time"], body["slot_minutes"]) == ("09:00", "22:00", 30)
    assert body["slots_per_day"] == 26 and body["bit_order"] == "day_major"
    repo.find_by_user.assert_called_once_with(42)
    repo.save.assert_not_called()


def test_unregistered_returns_404(setup):
    client, repo = setup
    repo.find_by_user.return_value = None
    assert client.get(URL).status_code == 404
    repo.save.assert_not_called()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_requires_auth(setup, headers):
    client, repo = setup
    app.dependency_overrides.pop(get_current_user)
    db = Mock()
    db.auth.get_user.side_effect = ValueError("invalid token")
    app.dependency_overrides[get_supabase] = lambda: db
    assert client.get(URL, headers=headers).status_code == 401
    repo.find_by_user.assert_not_called()


@pytest.mark.parametrize("error", [ConnectError("private detail"),
    APIError({"code": "XX000", "message": "private detail", "details": None, "hint": None})])
def test_database_error_is_not_misreported_as_unregistered(setup, error):
    client, repo = setup
    repo.find_by_user.side_effect = error
    response = client.get(URL)
    assert response.status_code == 503
    assert "private detail" not in response.text


@pytest.mark.parametrize("exists", [True, False])
def test_repository_scopes_query_and_flattens_user_metadata(exists):
    db = Mock()
    query = db.table.return_value.select.return_value
    query.eq.return_value.is_.return_value.limit.return_value.execute.return_value.data = (
        [{"class_bits": "1" * 182, "users": {"timetable_version": 1}}] if exists else []
    )
    result = TimetableRepository(db).find_by_user(42)
    db.table.assert_called_once_with("timetables")
    query.eq.assert_called_once_with("user_id", 42)
    query.eq.return_value.is_.assert_called_once_with("users.deleted_at", "null")
    assert result == ({"class_bits": "1" * 182, "timetable_version": 1} if exists else None)
