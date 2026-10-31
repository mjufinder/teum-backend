from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.deps import get_current_user, get_timetable_repository
from app.core.supabase import get_supabase
from app.main import app
from app.domain.timetable import Timetable
from app.repositories.timetable_repository import TimetableRepository

URL = "/api/v1/timetable"


@pytest.fixture
def setup():
    previous = app.dependency_overrides.copy()
    repository = Mock()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=42)
    app.dependency_overrides[get_timetable_repository] = lambda: repository
    with TestClient(app) as client:
        yield client, repository
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def saved_row(class_bits, manual_bits, version=1):
    return dict(class_bits=class_bits, manual_bits=manual_bits,
                available_bits=Timetable(class_bits, manual_bits).available_bits,
                timetable_version=version,
                timetable_registered_at="2026-11-01T00:00:00Z",
                updated_at="2026-11-01T00:00:00Z")


@pytest.mark.parametrize("manual", ["1" * 182, "1" * 130 + "0" * 52])
def test_save_unedited_or_weekend_edited(setup, manual):
    client, repo = setup
    classes = "0" + "1" * 181
    repo.save.return_value = saved_row(classes, manual)
    response = client.put(URL, json={"class_bits": classes, "manual_bits": manual})
    assert response.status_code == 200
    assert response.json()["manual_bits"] == manual
    assert response.json()["available_bits"] == Timetable(classes, manual).available_bits
    repo.save.assert_called_once_with(42, Timetable(classes, manual))


@pytest.mark.parametrize("change", [
    {"class_bits": "1" * 181}, {"manual_bits": "1" * 183},
    {"class_bits": "x" * 182}, {"manual_bits": None}, {"class_bits": 123},
    {"manual_bits": "1" * 181 + "\n"}, {"user_id": 99}, {"available_bits": "1" * 182},
])
def test_invalid_payload_does_not_write(setup, change):
    client, repo = setup
    payload = dict(class_bits="1" * 182, manual_bits="1" * 182)
    payload.update(change)
    assert client.put(URL, json=payload).status_code == 422
    repo.save.assert_not_called()


def test_manual_bits_required(setup):
    client, repo = setup
    assert client.put(URL, json={"class_bits": "1" * 182}).status_code == 422
    repo.save.assert_not_called()


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_save_requires_auth(setup, headers):
    client, repo = setup
    app.dependency_overrides.pop(get_current_user)
    db = Mock()
    db.auth.get_user.side_effect = ValueError("invalid")
    app.dependency_overrides[get_supabase] = lambda: db
    response = client.put(URL, headers=headers,
                          json=dict(class_bits="1" * 182, manual_bits="1" * 182))
    assert response.status_code == 401
    repo.save.assert_not_called()


@pytest.mark.parametrize("code,status", [("PT401", 401), ("PGRST202", 503)])
def test_database_failure(setup, code, status):
    client, repo = setup
    repo.save.side_effect = APIError({"code": code, "message": "private database detail",
                                     "details": None, "hint": None})
    response = client.put(URL, json=dict(class_bits="1" * 182, manual_bits="1" * 182))
    assert response.status_code == status
    assert "private database detail" not in response.text


def test_repository_uses_single_rpc():
    db = Mock()
    row = saved_row("1" * 182, "1" * 182)
    db.rpc.return_value.execute.return_value.data = [row]
    assert TimetableRepository(db).save(42, Timetable("1" * 182, "1" * 182)) == row
    db.rpc.assert_called_once_with("save_timetable", {
        "p_user_id": 42, "p_class_bits": "1" * 182, "p_manual_bits": "1" * 182,
    })
