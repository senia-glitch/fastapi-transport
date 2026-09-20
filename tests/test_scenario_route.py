"""Tests for fastbase.routing.scenario_route."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastbase.routing.scenario_route import _resolve_response_model, scenario_route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeResponse(BaseModel):
    id: int
    name: str


class _FakeScenario:
    response_model = _FakeResponse


def _fake_get_scenario(name: str) -> _FakeScenario:
    if name == "existing_scenario":
        return _FakeScenario()
    raise KeyError(f"Unknown scenario: {name}")


# ---------------------------------------------------------------------------
# _resolve_response_model
# ---------------------------------------------------------------------------


class TestResolveResponseModel:
    def test_returns_none_when_core_not_installed(self, monkeypatch) -> None:
        """If core-package is not importable, return None."""
        monkeypatch.delitem(sys.modules, "core", raising=False)
        monkeypatch.delitem(sys.modules, "core.registry", raising=False)
        result = _resolve_response_model("any_scenario")
        assert result is None

    def test_returns_response_model_from_core(self, monkeypatch) -> None:
        """If core-package has the scenario, return its response_model."""
        mock_core = MagicMock()
        mock_core.registry.get_scenario = _fake_get_scenario
        monkeypatch.setitem(sys.modules, "core", mock_core)
        monkeypatch.setitem(sys.modules, "core.registry", mock_core.registry)

        result = _resolve_response_model("existing_scenario")
        assert result is _FakeResponse

    def test_returns_none_when_scenario_not_found(self, monkeypatch) -> None:
        """If scenario doesn't exist in registry, return None."""
        mock_core = MagicMock()
        mock_core.registry.get_scenario = _fake_get_scenario
        monkeypatch.setitem(sys.modules, "core", mock_core)
        monkeypatch.setitem(sys.modules, "core.registry", mock_core.registry)

        result = _resolve_response_model("nonexistent_scenario")
        assert result is None

    def test_returns_none_when_no_response_model_attr(self, monkeypatch) -> None:
        """If scenario exists but has no response_model, return None."""
        scenario_no_model = MagicMock(spec=[])  # no response_model attr
        mock_core = MagicMock()
        mock_core.registry.get_scenario.return_value = scenario_no_model
        monkeypatch.setitem(sys.modules, "core", mock_core)
        monkeypatch.setitem(sys.modules, "core.registry", mock_core.registry)

        result = _resolve_response_model("some_scenario")
        assert result is None


# ---------------------------------------------------------------------------
# scenario_route decorator — behaviour tests
# ---------------------------------------------------------------------------


class TestScenarioRoute:
    def test_adds_post_route_to_router(self) -> None:
        router = APIRouter()

        @scenario_route(router, "/items", scenario="nonexistent", method="post")
        async def create_item() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.post("/items")
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_adds_get_route_to_router(self) -> None:
        router = APIRouter()

        @scenario_route(router, "/items", scenario="nonexistent", method="get")
        async def list_items() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.get("/items")
        assert r.status_code == 200

    def test_adds_put_route_to_router(self) -> None:
        router = APIRouter()

        @scenario_route(router, "/items/{id}", scenario="nonexistent", method="put")
        async def update_item() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.put("/items/1")
        assert r.status_code == 200

    def test_adds_delete_route_to_router(self) -> None:
        router = APIRouter()

        @scenario_route(router, "/items/{id}", scenario="nonexistent", method="delete")
        async def delete_item() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.delete("/items/1")
        assert r.status_code == 200

    def test_invalid_method_raises(self) -> None:
        router = APIRouter()
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            scenario_route(router, "/x", scenario="s", method="invalid")

    def test_passes_summary_to_route(self) -> None:
        router = APIRouter()

        @scenario_route(
            router,
            "/items",
            scenario="nonexistent",
            method="get",
            summary="Create item",
        )
        async def create_item() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        # Verify the route is registered and callable via OpenAPI
        schema = app.openapi()
        path_op = schema["paths"]["/items"]["get"]
        assert path_op["summary"] == "Create item"

    def test_sets_response_model_when_core_available(self, monkeypatch) -> None:
        mock_core = MagicMock()
        mock_core.registry.get_scenario = _fake_get_scenario
        monkeypatch.setitem(sys.modules, "core", mock_core)
        monkeypatch.setitem(sys.modules, "core.registry", mock_core.registry)

        router = APIRouter()

        @scenario_route(router, "/items", scenario="existing_scenario", method="post")
        async def create_item() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        # Verify response_model appears in the OpenAPI schema
        schema = app.openapi()
        path_op = schema["paths"]["/items"]["post"]
        resp_schema = path_op["responses"]["200"]["content"]["application/json"]["schema"]
        # FastAPI uses $ref for complex models
        if "$ref" in resp_schema:
            ref_name = resp_schema["$ref"].split("/")[-1]
            resolved = schema["components"]["schemas"][ref_name]
            assert resolved["title"] == "_FakeResponse"
        else:
            assert resp_schema.get("title") == "_FakeResponse"

    def test_no_response_model_when_core_not_installed(self, monkeypatch) -> None:
        monkeypatch.delitem(sys.modules, "core", raising=False)
        monkeypatch.delitem(sys.modules, "core.registry", raising=False)

        router = APIRouter()

        @scenario_route(router, "/items", scenario="any", method="post")
        async def create_item() -> dict:
            return {"ok": True}

        app = FastAPI()
        app.include_router(router)
        # When no response_model, OpenAPI schema should not define one for 200
        schema = app.openapi()
        path_op = schema["paths"]["/items"]["post"]
        resp_200 = path_op["responses"]["200"]
        # Either no content key or no schema with $ref
        content = resp_200.get("content", {})
        if content:
            json_schema = content.get("application/json", {}).get("schema", {})
            assert "$ref" not in json_schema, "Should not have a response model ref"
        else:
            # No content at all is fine — means no response_model
            pass


# ---------------------------------------------------------------------------
# Integration with FastAPI app
# ---------------------------------------------------------------------------


from fastapi import FastAPI  # noqa: E402  (imported after test class for clarity)


class TestScenarioRouteIntegration:
    def test_route_works_in_full_app(self) -> None:
        router = APIRouter(tags=["items"])

        @scenario_route(router, "/items", scenario="nonexistent", method="get")
        async def list_items() -> dict:
            return {"items": []}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        r = client.get("/items")
        assert r.status_code == 200
        assert r.json() == {"items": []}

    def test_multiple_routes_with_different_methods(self) -> None:
        router = APIRouter()

        @scenario_route(router, "/items", scenario="nonexistent", method="get")
        async def list_items() -> dict:
            return {"items": []}

        @scenario_route(router, "/items", scenario="nonexistent", method="post")
        async def create_item() -> dict:
            return {"created": True}

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        assert client.get("/items").status_code == 200
        assert client.post("/items").status_code == 200

    def test_response_model_appears_in_openapi_schema(self, monkeypatch) -> None:
        """When core is installed, response_model should appear in OpenAPI."""
        mock_core = MagicMock()
        mock_core.registry.get_scenario = _fake_get_scenario
        monkeypatch.setitem(sys.modules, "core", mock_core)
        monkeypatch.setitem(sys.modules, "core.registry", mock_core.registry)

        router = APIRouter()

        @scenario_route(router, "/items", scenario="existing_scenario", method="post")
        async def create_item() -> dict:
            return {"id": 1, "name": "test"}

        app = FastAPI()
        app.include_router(router)
        schema = app.openapi()
        path_op = schema["paths"]["/items"]["post"]
        response_schema = path_op["responses"]["200"]["content"]["application/json"]["schema"]
        # FastAPI uses $ref for complex models — resolve it
        if "$ref" in response_schema:
            ref_name = response_schema["$ref"].split("/")[-1]
            resolved = schema["components"]["schemas"][ref_name]
            assert resolved["title"] == "_FakeResponse"
            assert "id" in resolved["properties"]
            assert "name" in resolved["properties"]
        else:
            assert response_schema.get("title") == "_FakeResponse"

