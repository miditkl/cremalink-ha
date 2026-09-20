"""Tests for the manual A2 statistics refresh button."""

import asyncio
from types import SimpleNamespace

from custom_components.cremalink_ha import button as module


ENTRY = SimpleNamespace(
    title="Test Coffee Machine",
    entry_id="test-ecam610",
)


class FakeStatisticsCoordinator:
    """Controllable statistics coordinator for button tests."""

    def __init__(self):
        self.refresh_in_progress = False
        self.refresh_calls = 0
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def async_force_refresh(self):
        """Simulate one complete A2 statistics run."""
        self.refresh_calls += 1
        self.refresh_in_progress = True
        self.started.set()

        try:
            await self.release.wait()
        finally:
            self.refresh_in_progress = False


def test_statistics_refresh_button_unavailable_while_running():
    """Manual A2 refresh must disable the button until the run completes."""

    async def _run():
        coordinator = FakeStatisticsCoordinator()

        button_class = getattr(
            module,
            "CremalinkStatisticsRefreshButton",
        )
        button = button_class(coordinator, ENTRY)

        assert button.available is True

        task = asyncio.create_task(button.async_press())
        await coordinator.started.wait()

        assert coordinator.refresh_calls == 1
        assert button.available is False

        coordinator.release.set()
        await task

        assert button.available is True

    asyncio.run(_run())


def test_statistics_refresh_button_is_added_when_supported():
    """The manual A2 refresh button must be exposed with statistics support."""

    class FakeDevice:
        def get_commands(self):
            return []

    class FakeHass:
        def __init__(self):
            self.data = {
                module.DOMAIN: {
                    ENTRY.entry_id: {
                        "coordinator": object(),
                        "statistics_coordinator": FakeStatisticsCoordinator(),
                        "device": FakeDevice(),
                    }
                }
            }

        async def async_add_executor_job(self, func, *args):
            return func(*args)

    async def _run():
        added = []

        def async_add_entities(entities):
            added.extend(entities)

        await module.async_setup_entry(
            FakeHass(),
            ENTRY,
            async_add_entities,
        )

        assert any(
            isinstance(
                entity,
                module.CremalinkStatisticsRefreshButton,
            )
            for entity in added
        )

    asyncio.run(_run())
