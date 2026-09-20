"""Focused tests for CremalinkCoordinator without importing Home Assistant."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


# ---------------------------------------------------------------------
# Minimal module stubs required by coordinator.py.
# We deliberately load coordinator.py directly so package __init__.py
# cannot pull in the complete Home Assistant integration.
# ---------------------------------------------------------------------

homeassistant = ModuleType("homeassistant")
ha_core = ModuleType("homeassistant.core")
ha_helpers = ModuleType("homeassistant.helpers")
ha_update = ModuleType("homeassistant.helpers.update_coordinator")


class HomeAssistant:
    pass


class UpdateFailed(Exception):
    pass


class DataUpdateCoordinator:
    def __init__(
        self,
        hass,
        logger,
        *,
        name=None,
        update_interval=None,
        **_kwargs,
    ):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None


ha_core.HomeAssistant = HomeAssistant
ha_update.DataUpdateCoordinator = DataUpdateCoordinator
ha_update.UpdateFailed = UpdateFailed

sys.modules["homeassistant"] = homeassistant
sys.modules["homeassistant.core"] = ha_core
sys.modules["homeassistant.helpers"] = ha_helpers
sys.modules["homeassistant.helpers.update_coordinator"] = ha_update


cremalink = ModuleType("cremalink")
cremalink_domain = ModuleType("cremalink.domain")
cremalink_device = ModuleType("cremalink.domain.device")


class Device:
    pass


cremalink_device.Device = Device

sys.modules["cremalink"] = cremalink
sys.modules["cremalink.domain"] = cremalink_domain
sys.modules["cremalink.domain.device"] = cremalink_device


custom_components = ModuleType("custom_components")
custom_components.__path__ = []

package = ModuleType("custom_components.cremalink_ha")
package.__path__ = []

const = ModuleType("custom_components.cremalink_ha.const")
const.DOMAIN = "cremalink_ha"

sys.modules["custom_components"] = custom_components
sys.modules["custom_components.cremalink_ha"] = package
sys.modules["custom_components.cremalink_ha.const"] = const


ROOT = Path(__file__).resolve().parents[1]
COORDINATOR = (
    ROOT
    / "custom_components"
    / "cremalink_ha"
    / "coordinator.py"
)

spec = importlib.util.spec_from_file_location(
    "custom_components.cremalink_ha.coordinator",
    COORDINATOR,
)

if spec is None or spec.loader is None:
    raise RuntimeError("Could not create coordinator module spec")

module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class FakeHass:
    async def async_add_executor_job(self, func, *args):
        return func(*args)


class FakeDevice:
    def __init__(self, results):
        self._results = iter(results)

    def get_monitor(self):
        value = next(self._results)
        if isinstance(value, Exception):
            raise value
        return value


def monitor(status: int):
    return SimpleNamespace(parsed={"status": status})


def run(coro):
    return asyncio.run(coro)


def test_successful_read_sets_fast_polling():
    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice([monitor(1)]),
    )

    result = run(coordinator._async_update_data())

    assert result.parsed["status"] == 1
    assert coordinator.update_interval == module.SCAN_INTERVAL_FAST
    assert coordinator.monitor_consecutive_failures == 0


def test_standby_sets_slow_polling():
    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice([monitor(0)]),
    )

    result = run(coordinator._async_update_data())

    assert result.parsed["status"] == 0
    assert coordinator.update_interval == module.SCAN_INTERVAL_SLOW


def test_first_transient_failure_retains_last_snapshot():
    good = monitor(1)

    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice(
            [
                good,
                ValueError("synthetic malformed monitor frame"),
            ]
        ),
    )

    coordinator.data = run(coordinator._async_update_data())
    result = run(coordinator._async_update_data())

    assert result is good
    assert coordinator.monitor_consecutive_failures == 1


def test_second_transient_failure_still_retains_snapshot():
    good = monitor(1)

    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice(
            [
                good,
                RuntimeError("failure 1"),
                RuntimeError("failure 2"),
            ]
        ),
    )

    coordinator.data = run(coordinator._async_update_data())
    coordinator.data = run(coordinator._async_update_data())
    result = run(coordinator._async_update_data())

    assert result is good
    assert coordinator.monitor_consecutive_failures == 2


def test_third_consecutive_failure_surfaces():
    good = monitor(1)

    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice(
            [
                good,
                RuntimeError("failure 1"),
                RuntimeError("failure 2"),
                RuntimeError("failure 3"),
            ]
        ),
    )

    coordinator.data = run(coordinator._async_update_data())
    coordinator.data = run(coordinator._async_update_data())
    coordinator.data = run(coordinator._async_update_data())

    try:
        run(coordinator._async_update_data())
    except UpdateFailed as err:
        assert "failure 3" in str(err)
    else:
        raise AssertionError("third consecutive failure was hidden")

    assert coordinator.monitor_consecutive_failures == 3


def test_success_resets_failure_counter():
    first = monitor(1)
    second = monitor(1)

    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice(
            [
                first,
                RuntimeError("temporary"),
                second,
            ]
        ),
    )

    coordinator.data = run(coordinator._async_update_data())
    coordinator.data = run(coordinator._async_update_data())

    assert coordinator.monitor_consecutive_failures == 1

    result = run(coordinator._async_update_data())

    assert result is second
    assert coordinator.monitor_consecutive_failures == 0


def test_initial_failure_is_not_hidden():
    coordinator = module.CremalinkCoordinator(
        FakeHass(),
        FakeDevice([RuntimeError("initial failure")]),
    )

    try:
        run(coordinator._async_update_data())
    except UpdateFailed as err:
        assert "initial failure" in str(err)
    else:
        raise AssertionError("initial failure was hidden")
