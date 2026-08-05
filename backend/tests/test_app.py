"""Basic application startup / wiring tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def test_app_starts_and_exposes_docs_routes():
    """Smoke test that the app object builds successfully and wires up docs."""
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/docs" in paths
    assert "/redoc" in paths
    assert "/openapi.json" in paths


@pytest.mark.asyncio
async def test_openapi_schema_is_served():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Theatre Social API"
    assert "/health" in schema["paths"]


@pytest.mark.asyncio
async def test_docs_ui_is_served():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
