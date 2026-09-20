"""Button platform for the Cremalink integration."""
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_CONNECTION_TYPE, CONNECTION_CLOUD


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the button platform.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Function to add entities.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    statistics_coordinator = data.get("statistics_coordinator")
    device = data["device"]

    # Get available commands from the device
    cmds = await hass.async_add_executor_job(device.get_commands)

    entities = []
    for cmd in cmds:
        # Filter out power commands as they might be handled elsewhere
        if cmd.lower() not in ["wakeup", "standby", "refresh"]:
            entities.append(CremalinkButton(coordinator, device, cmd, entry))
    if statistics_coordinator is not None:
        entities.append(
            CremalinkStatisticsRefreshButton(
                statistics_coordinator,
                entry,
            )
        )

    async_add_entities(entities)


class CremalinkButton(CoordinatorEntity, ButtonEntity):
    """Representation of a Cremalink button."""

    def __init__(self, coordinator, device, cmd, entry):
        """Initialize the button.

        Args:
            coordinator: The data update coordinator.
            device: The Cremalink device instance.
            cmd: The command associated with this button.
            entry: The config entry.
        """
        super().__init__(coordinator)
        self.device = device
        self._cmd = cmd
        self._title = cmd.replace('_', ' ').title()
        self._attr_name = f"{"Brew" if self._title not in ["Stop"] else ""} {self._title} {"brewing" if self._title in ["Stop"] else ""}"
        self._attr_unique_id = f"{entry.entry_id}_cmd_{cmd}"
        self._attr_icon = "mdi:coffee"
        self._connection_type = entry.data.get(CONF_CONNECTION_TYPE)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="cremalink",
        )

    @property
    def available(self):
        """Return True if entity is available."""
        if self._title in ["Stop"]:
            return super().available and self.coordinator.data.is_busy
        return super().available and not self.coordinator.data.is_busy

    async def async_press(self):
        """Handle the button press."""
        await self.hass.async_add_executor_job(self.device.do, self._cmd)
        await self.coordinator.async_request_refresh()



class CremalinkStatisticsRefreshButton(CoordinatorEntity, ButtonEntity):
    """Button that triggers one complete A2 statistics refresh."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:database-refresh"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, entry):
        """Initialize the manual statistics refresh button."""
        super().__init__(coordinator)

        self._attr_name = f"{entry.title} Refresh A2 statistics"
        self._attr_unique_id = (
            f"{entry.entry_id}_statistics_refresh"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="cremalink",
        )

    @property
    def available(self):
        """Disable the button while a full A2 refresh is running."""
        return not self.coordinator.refresh_in_progress

    async def async_press(self):
        """Run one complete A2 statistics refresh."""
        await self.coordinator.async_force_refresh()
