"""Switch platform for the Cremalink integration."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, GITHUB_URL


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the switch platform.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Function to add entities.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device = data["device"]
    async_add_entities([CremalinkPowerSwitch(coordinator, device, entry)])


class CremalinkPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Cremalink power switch."""

    _attr_icon = "mdi:power"
    _attr_has_entity_name = True

    def __init__(self, coordinator, device, entry):
        """Initialize the switch.

        Args:
            coordinator: The data update coordinator.
            device: The Cremalink device instance.
            entry: The config entry.
        """
        super().__init__(coordinator)
        self.device = device
        self.entry = entry
        self._attr_name = "Power"
        self._attr_unique_id = f"{device.dsn}_power"
        self._attr_icon = "mdi:power"

    #
    # ---- DEVICE INFO (⭐ REQUIRED FOR DEVICE PAGE) ----
    #
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Cremalink hub."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.dsn)},
            name=self.entry.title,
            manufacturer="Cremalink",
            model="Local Device",
            sw_version=getattr(self.device, "firmware_version", None),
            configuration_url= GITHUB_URL,
        )

    @property
    def is_on(self):
        """Return true if the switch is on."""
        if not self.coordinator.data or not self.coordinator.data.status_name:
            return None
        # Check if the status indicates the device is not in standby
        return self.coordinator.data.status_name.lower() not in ["standby", "in_standby"]

    @property
    def available(self):
        """Return True if entity is available."""
        if not self.coordinator.data:
            return False
        return super().available

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self.hass.async_add_executor_job(self.device.do, "wakeup")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self.hass.async_add_executor_job(self.device.do, "standby")
        await self.coordinator.async_request_refresh()
