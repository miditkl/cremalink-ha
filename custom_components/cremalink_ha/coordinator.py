import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from cremalink.domain.device import Device

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class CremalinkCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, device: Device):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=1),
        )
        self.device = device

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.device.get_monitor)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
