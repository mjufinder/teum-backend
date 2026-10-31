from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from fastapi.testclient import TestClient
from google.api_core.exceptions import DeadlineExceeded, ServiceUnavailable
from google.auth.exceptions import DefaultCredentialsError
from PIL import Image

from app.api.deps import get_current_user
from app.core.supabase import get_supabase
from app.main import app
from app.services import timetable_service as service

URL = "/api/v1/timetable/recognize"


def image_bytes(fmt="PNG"):
    data = BytesIO()
    Image.new("RGB", (20, 20), "white").save(data, format=fmt)
    return data.getvalue()


@pytest.fixture
def client():
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_id=1)
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
def test_auth_required_before_recognition(client, monkeypatch, headers):
    app.dependency_overrides.pop(get_current_user)
    db = Mock()
    db.auth.get_user.side_effect = ValueError("invalid token")
    app.dependency_overrides[get_supabase] = lambda: db
    parser = Mock()
    monkeypatch.setattr(service, "get_exact_timetable_matrix", parser)
    response = client.post(URL, headers=headers, files={"file": ("test.png", image_bytes())})
    assert response.status_code == 401
    parser.assert_not_called()


def test_success_day_order_weekend_and_cleanup(client, monkeypatch):
    paths = []
    matrix = np.ones((26, 5), dtype=int)
    matrix[0, 0] = 0
    matrix[2, 1] = 0
    matrix[25, 4] = 0

    def parse(path):
        assert path.exists()
        paths.append(path)
        return matrix

    monkeypatch.setattr(service, "get_exact_timetable_matrix", parse)
    response = client.post(URL, files={"file": ("../../test.png", image_bytes())})
    assert response.status_code == 200
    result = response.json()
    bits = result["class_bits"]
    assert len(bits) == 182
    assert [i for i, bit in enumerate(bits) if bit == "0"] == [0, 28, 129]
    assert bits[130:] == "1" * 52
    assert result["manual_bits"] == "1" * 182
    assert result["available_bits"] == bits
    assert all(not path.exists() for path in paths)


@pytest.mark.parametrize("data,status", [(b"", 400), (b"not an image", 400), (image_bytes("GIF"), 415)])
def test_invalid_upload(client, monkeypatch, data, status):
    parser = Mock()
    monkeypatch.setattr(service, "get_exact_timetable_matrix", parser)
    assert client.post(URL, files={"file": ("fake.png", data)}).status_code == status
    parser.assert_not_called()


def test_size_limits_and_missing_file(client, monkeypatch):
    monkeypatch.setattr(service, "MAX_UPLOAD_BYTES", 10)
    assert client.post(URL, files={"file": ("test.png", image_bytes())}).status_code == 413
    assert client.post(URL).status_code == 422
    monkeypatch.setattr(service, "MAX_UPLOAD_BYTES", 10 * 1024 * 1024)
    monkeypatch.setattr(service, "MAX_IMAGE_PIXELS", 100)
    assert client.post(URL, files={"file": ("test.png", image_bytes())}).status_code == 413


@pytest.mark.parametrize("error,status", [
    (service.WeekdayHeaderError("요일 헤더를 확인할 수 없습니다."), 422),
    (ValueError("grid error"), 422),
    (DefaultCredentialsError("secret detail"), 503),
    (DeadlineExceeded("timeout"), 504),
    (ServiceUnavailable("upstream"), 502),
])
def test_ocr_failure_cleans_temporary_files(client, monkeypatch, error, status):
    paths = []

    def fail(path):
        paths.append(path)
        raise error

    monkeypatch.setattr(service, "get_exact_timetable_matrix", fail)
    response = client.post(URL, files={"file": ("test.jpg", image_bytes("JPEG"))})
    assert response.status_code == status
    assert "secret detail" not in response.text
    if isinstance(error, service.WeekdayHeaderError):
        assert response.json()["detail"] == str(error)
    assert paths and all(not path.exists() for path in paths)
