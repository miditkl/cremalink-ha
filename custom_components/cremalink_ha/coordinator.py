"""Data update coordinator for the Cremalink integration."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from cremalink.domain.device import Device

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL_FAST = timedelta(seconds=1)
SCAN_INTERVAL_SLOW = timedelta(seconds=30)

# Keep the last known-good monitor snapshot across a very short run of
# malformed/missed polls. This prevents normal entities from flapping to
# unavailable on isolated transport/parser errors while still surfacing a
# sustained device disconnect.
MONITOR_TRANSIENT_FAILURE_LIMIT = 2

class CremalinkCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Cremalink device."""

    def __init__(self, hass: HomeAssistant, device: Device):
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            device: The Cremalink device instance.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # Poll the device every second for updates
            update_interval=SCAN_INTERVAL_FAST,
        )
        self.device = device
        self.monitor_consecutive_failures = 0

    async def _async_update_data(self):
        """Fetch data from the device.

        Returns:
            The monitoring data from the device.

        Raises:
            UpdateFailed: If there is an error communicating with the device.
        """
        try:
            data = await self.hass.async_add_executor_job(
                self.device.get_monitor
            )

            # Any genuinely successful monitor read ends a transient
            # failure streak.
            self.monitor_consecutive_failures = 0

            if (
                data
                and hasattr(data, "parsed")
                and isinstance(data.parsed, dict)
            ):
                status = data.parsed.get("status")

                if status == 0:
                    # Standby: poll slowly.
                    self.update_interval = SCAN_INTERVAL_SLOW
                elif status is not None:
                    self.update_interval = SCAN_INTERVAL_FAST

            return data

        except Exception as err:
            self.monitor_consecutive_failures += 1

            # A single malformed/truncated monitor frame should not make
            # all normal entities unavailable. Retain a previously
            # successful snapshot for a very short failure streak.
            if (
                self.data is not None
                and self.monitor_consecutive_failures
                <= MONITOR_TRANSIENT_FAILURE_LIMIT
            ):
                _LOGGER.debug(
                    "Transient monitor failure %s/%s; retaining last "
                    "known-good snapshot: %s",
                    self.monitor_consecutive_failures,
                    MONITOR_TRANSIENT_FAILURE_LIMIT,
                    err,
                )
                return self.data

            raise UpdateFailed(
                f"Error communicating with device: {err}"
            ) from err
