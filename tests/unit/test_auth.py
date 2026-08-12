"""Unit tests for Auth middleware."""

import pytest
from gost_bi.core.auth import (
    API_KEYS,
    Role,
    User,
    _verify_jwt,
    get_current_user,
    require_admin,
    require_analyst,
    require_role,
)


class TestUser:
    def test_is_admin(self):
        admin = User(id="1", login="admin", full_name="Admin", roles=[Role.ADMIN])
        assert admin.is_admin

    def test_viewer_is_not_admin(self):
        viewer = User(id="2", login="viewer", full_name="Viewer", roles=[Role.VIEWER])
        assert not viewer.is_admin

    def test_is_analyst(self):
        analyst = User(id="3", login="analyst", full_name="Analyst", roles=[Role.ANALYST])
        assert analyst.is_analyst

    def test_admin_is_analyst(self):
        admin = User(id="4", login="admin", full_name="Admin", roles=[Role.ADMIN])
        assert admin.is_analyst

    def test_default_role(self):
        user = User(id="5", login="user", full_name="User")
        assert user.roles == [Role.VIEWER]


class TestAPIKeys:
    def test_dev_key_exists(self):
        assert "gost-bi-dev-key" in API_KEYS
        user = API_KEYS["gost-bi-dev-key"]
        assert user.is_admin

    def test_demo_analyst_has_org(self):
        user = API_KEYS["demo-analyst"]
        assert user.organization == "ООО Демо"
        assert Role.ANALYST in user.roles

    def test_demo_viewer_has_rls(self):
        user = API_KEYS["demo-viewer"]
        assert "region" in user.rls_filters


class TestJWTVerify:
    def test_invalid_token_returns_none(self):
        assert _verify_jwt("invalid-token") is None

    def test_empty_token(self):
        assert _verify_jwt("") is None


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_require_admin_with_admin(self):
        admin = User(id="1", login="admin", full_name="A", roles=[Role.ADMIN])
        checker = require_role(Role.ADMIN)
        result = await checker(admin)
        assert result.id == "1"

    @pytest.mark.asyncio
    async def test_require_admin_with_viewer_raises(self):
        from fastapi import HTTPException

        viewer = User(id="2", login="viewer", full_name="V", roles=[Role.VIEWER])
        checker = require_role(Role.ADMIN)
        with pytest.raises(HTTPException) as exc:
            await checker(viewer)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_analyst_allows_admin(self):
        admin = User(id="1", login="admin", full_name="A", roles=[Role.ADMIN])
        checker = require_role(Role.ADMIN, Role.ANALYST)
        result = await checker(admin)
        assert result.is_admin

    @pytest.mark.asyncio
    async def test_require_analyst_allows_analyst(self):
        analyst = User(id="3", login="analyst", full_name="B", roles=[Role.ANALYST])
        checker = require_role(Role.ADMIN, Role.ANALYST)
        result = await checker(analyst)
        assert result.is_analyst

    @pytest.mark.asyncio
    async def test_factory_functions(self):
        from gost_bi.core.auth import require_admin, require_analyst
        admin = User(id="1", login="admin", full_name="A", roles=[Role.ADMIN])
        checker = require_role(Role.ADMIN)
        result = await checker(admin)
        assert result.is_admin

        analyst = User(id="3", login="analyst", full_name="B", roles=[Role.ANALYST])
        checker = require_role(Role.ADMIN, Role.ANALYST)
        result = await checker(analyst)
        assert result.is_analyst
