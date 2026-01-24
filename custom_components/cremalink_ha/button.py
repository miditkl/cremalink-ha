from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device = data["device"]

    cmds = await hass.async_add_executor_job(device.get_commands)

    entities = []
    for cmd in cmds:
        if cmd.lower() not in ["wakeup", "standby", "refresh"]:
            entities.append(CremalinkButton(coordinator, device, entry.title, cmd, entry.entry_id))
    async_add_entities(entities)


class CremalinkButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, device, dev_name, cmd, entry_id):
        super().__init__(coordinator)
        self.device = device
        self._cmd = cmd
        self._title = cmd.replace('_', ' ').title()
        self._attr_name = f"{"Brew" if self._title not in ["Stop"] else ""} {self._title} {"brewing" if self._title in ["Stop"] else ""}"
        self._attr_unique_id = f"{entry_id}_cmd_{cmd}"
        self._attr_icon = "mdi:coffee"

    @property
    def available(self):
        if self._title in ["Stop"]:
            return super().available and self.coordinator.data.is_busy
        return super().available and not self.coordinator.data.is_busy

    async def async_press(self):
        # Einfach device.do aufrufen!
        await self.hass.async_add_executor_job(self.device.do, self._cmd)
        await self.coordinator.async_request_refresh()
