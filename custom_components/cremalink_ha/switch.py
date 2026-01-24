from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device = data["device"]
    async_add_entities([CremalinkPowerSwitch(coordinator, device, entry)])


class CremalinkPowerSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, device, entry):
        super().__init__(coordinator)
        self.device = device
        self._attr_name = f"{entry.title} Power"
        self._attr_unique_id = f"{entry.entry_id}_power"
        self._attr_icon = "mdi:power"

    @property
    def is_on(self):
        if not self.coordinator.data or not self.coordinator.data.status_name:
            return None
        return self.coordinator.data.status_name.lower() not in ["standby", "in_standby"]

    @property
    def available(self):
        if not self.coordinator.data:
            return False
        return super().available

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self.device.do, "wakeup")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self.device.do, "standby")
        await self.coordinator.async_request_refresh()
