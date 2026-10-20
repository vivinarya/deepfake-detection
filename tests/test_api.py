import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from app import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "SafeGuard" in data["service"]

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_unsupported_file_extension():
    files = {"file": ("unsupported_data.txt", b"not a video", "text/plain")}
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "Unsupported video format" in response.json()["detail"]
