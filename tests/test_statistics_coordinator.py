"""Tests for the Cremalink statistics coordinator."""

import asyncio
from datetime import timedelta

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.cremalink_ha import statistics_coordinator as module
from custom_components.cremalink_ha.statistics_coordinator import (
    CremalinkStatisticsCoordinator,
    STATISTICS_UPDATE_INTERVAL,
)


class FakeHass:
    """Minimal Home Assistant executor stub."""

    async def async_add_executor_job(self, func, *args):
        return func(*args)


def test_statistics_poll_interval_is_slow():
    """Statistics must not use the fast monitor polling interval."""
    assert STATISTICS_UPDATE_INTERVAL == timedelta(minutes=10)


def test_statistics_coordinator_fetches_snapshot(monkeypatch):
    """Coordinator should expose the snapshot returned by the core library."""

    snapshot = {
        "known": {
            "total_beverages": 123,
            "descale_count": 4,
        },
        "unknown": {
            43000: 17,
        },
        "raw": {
            105: 4,
            43000: 17,
            43010: 123,
        },
    }

    calls = {}

    class FakeClient:
        def __init__(self, token_file):
            calls["token_file"] = token_file

        def get_ecam610_statistics(self, dsn, **_kwargs):
            calls["dsn"] = dsn
            return snapshot

    monkeypatch.setattr(module, "Client", FakeClient)

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )

    result = asyncio.run(coordinator._async_update_data())

    assert result["known"] == snapshot["known"]
    assert result["unknown"] == snapshot["unknown"]
    assert result["raw"] == snapshot["raw"]
    assert result["service_properties"] == {}
    assert "snapshot_fetched_at" in result

    assert calls == {
        "token_file": "/tmp/test-token.json",
        "dsn": "test-dsn",
    }


def test_statistics_coordinator_wraps_client_failure(monkeypatch):
    """Core/cloud errors should become Home Assistant UpdateFailed errors."""

    class FakeClient:
        def __init__(self, _token_file):
            pass

        def get_ecam610_statistics(self, _dsn, **_kwargs):
            raise RuntimeError("synthetic cloud failure")

    monkeypatch.setattr(module, "Client", FakeClient)

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )

    with pytest.raises(
        UpdateFailed,
        match="synthetic cloud failure",
    ):
        asyncio.run(coordinator._async_update_data())


def test_statistics_coordinator_retains_snapshot_on_a2_timeout(monkeypatch):
    """A transient A2 timeout must keep the last successful snapshot."""

    previous = {
        "known": {
            "total_beverages": 123,
        },
        "unknown": {},
        "raw": {
            43010: 123,
        },
    }

    class FakeClient:
        def __init__(self, _token_file):
            pass

        def get_ecam610_statistics(self, _dsn, **_kwargs):
            raise TimeoutError(
                "No A2 statistics response for start_id=3001 within 20s"
            )

    monkeypatch.setattr(module, "Client", FakeClient)

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )
    coordinator.data = previous

    result = asyncio.run(coordinator._async_update_data())

    assert result is previous
def test_statistics_snapshot_timestamp_changes_only_on_success(monkeypatch):
    """Only a successful A2 read may advance the snapshot timestamp."""

    snapshots = [
        {
            "known": {"total_beverages": 123},
            "unknown": {},
            "raw": {43010: 123},
        },
    ]

    class FakeClient:
        def __init__(self, _token_file):
            pass

        def get_ecam610_statistics(self, _dsn, **_kwargs):
            if snapshots:
                return snapshots.pop(0)

            raise TimeoutError("synthetic transient A2 timeout")

    times = iter(
        [
            "2026-08-25T07:00:00+00:00",
            "2026-08-25T07:01:00+00:00",
        ]
    )

    monkeypatch.setattr(module, "Client", FakeClient)
    monkeypatch.setattr(
        module,
        "_snapshot_timestamp",
        lambda: next(times),
        raising=False,
    )

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )

    first = asyncio.run(coordinator._async_update_data())
    coordinator.data = first

    assert first["snapshot_fetched_at"] == "2026-08-25T07:00:00+00:00"

    second = asyncio.run(coordinator._async_update_data())

    assert second is first
    assert second["snapshot_fetched_at"] == "2026-08-25T07:00:00+00:00"


def test_statistics_force_refresh_tracks_in_progress():
    """A manual full A2 refresh must expose its running state."""

    async def _run():
        coordinator = CremalinkStatisticsCoordinator(
            FakeHass(),
            dsn="test-dsn",
            token_file="/tmp/test-token.json",
        )

        started = asyncio.Event()
        release = asyncio.Event()

        async def fake_refresh():
            started.set()
            await release.wait()

        coordinator.async_refresh = fake_refresh
        coordinator.async_update_listeners = lambda: None

        assert coordinator.refresh_in_progress is False

        task = asyncio.create_task(
            coordinator.async_force_refresh()
        )

        await started.wait()

        assert coordinator.refresh_in_progress is True

        release.set()
        await task

        assert coordinator.refresh_in_progress is False

    asyncio.run(_run())



def test_statistics_coordinator_tracks_a2_progress(monkeypatch):
    """A2 page progress should be retained by the coordinator."""

    snapshot = {
        "known": {"total_beverages": 123},
        "unknown": {},
        "raw": {43010: 123},
    }

    class FakeClient:
        def __init__(self, _token_file):
            pass

        def get_ecam610_statistics(
            self,
            _dsn,
            *,
            progress_callback=None,
        ):
            assert progress_callback is not None

            progress_callback(
                {
                    "phase": "request",
                    "page": 4,
                    "start_id": 23000,
                    "request_count": 7,
                    "collected_count": 31,
                }
            )

            return snapshot

    monkeypatch.setattr(module, "Client", FakeClient)

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )
    coordinator.async_update_listeners = lambda: None

    result = asyncio.run(coordinator._async_update_data())

    assert result["raw"] == {43010: 123}
    assert coordinator.a2_progress == {
        "phase": "request",
        "page": 4,
        "start_id": 23000,
        "request_count": 7,
        "collected_count": 31,
    }


def test_statistics_snapshot_includes_service_properties(monkeypatch):
    """A2 diagnostics should carry the relevant Ayla service properties."""

    snapshot = {
        "known": {"total_beverages": 42},
        "unknown": {100: 111, 109: 222},
        "raw": {100: 111, 109: 222, 43010: 42},
    }

    service_properties = {
        "d550_water_calc_qty": 333,
        "d555_water_filter_qty": 444,
        "d556_water_hardness": 3,
        "d512_percentage_to_deca": 55,
        "d513_percentage_usage_fltr": 66,
    }

    class FakeClient:
        def __init__(self, _token_file):
            pass

        def get_ecam610_statistics(
            self,
            _dsn,
            *,
            progress_callback=None,
        ):
            return snapshot

        def get_ecam_service_properties(self, _dsn):
            return service_properties

    monkeypatch.setattr(module, "Client", FakeClient)

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )

    result = asyncio.run(coordinator._async_update_data())

    assert result["service_properties"] == service_properties


def test_statistics_service_property_failure_keeps_a2_snapshot(monkeypatch):
    """Auxiliary d5xx failure must not invalidate a successful A2 read."""

    snapshot = {
        "known": {"total_beverages": 42},
        "unknown": {100: 111, 109: 222},
        "raw": {100: 111, 109: 222, 43010: 42},
    }

    class FakeClient:
        def __init__(self, _token_file):
            pass

        def get_ecam610_statistics(
            self,
            _dsn,
            *,
            progress_callback=None,
        ):
            return snapshot

        def get_ecam_service_properties(self, _dsn):
            raise RuntimeError("synthetic d5xx failure")

    monkeypatch.setattr(module, "Client", FakeClient)

    coordinator = CremalinkStatisticsCoordinator(
        FakeHass(),
        dsn="test-dsn",
        token_file="/tmp/test-token.json",
    )

    result = asyncio.run(coordinator._async_update_data())

    assert result["known"]["total_beverages"] == 42
    assert result["raw"][100] == 111
    assert result["service_properties"] == {}
