"""Unit tests for WebSocket hub."""

import pytest
from gost_bi.core.websocket import DashboardChannel, DashboardHub


class TestDashboardChannel:
    def test_init(self):
        ch = DashboardChannel("test-dash")
        assert ch.dashboard_id == "test-dash"
        assert len(ch.subscribers) == 0

    def test_last_data_persists(self):
        ch = DashboardChannel("test")
        ch.last_data = {"kpi": 42}
        assert ch.last_data["kpi"] == 42


class TestDashboardHub:
    def test_get_channel_creates(self):
        hub = DashboardHub()
        ch = hub.get_channel("new-dash")
        assert ch.dashboard_id == "new-dash"
        assert "new-dash" in hub.channels

    def test_get_channel_returns_same(self):
        hub = DashboardHub()
        ch1 = hub.get_channel("same")
        ch2 = hub.get_channel("same")
        assert ch1 is ch2
