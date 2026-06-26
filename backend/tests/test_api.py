"""TruthTrace AI backend tests."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "TruthTrace AI"


@pytest.mark.asyncio
async def test_verify_question(client):
    response = await client.post(
        "/api/v1/verify",
        json={"question": "What is the capital of France?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "confidence_score" in data
    assert "trust_report" in data
    assert data["confidence_score"] >= 0


@pytest.mark.asyncio
async def test_verify_validation(client):
    response = await client.post("/api/v1/verify", json={"question": "ab"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_dashboard_stats(client):
    response = await client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_queries" in data
    assert "confidence_trend" in data
