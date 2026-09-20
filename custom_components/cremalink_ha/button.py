"""Button platform for the Cremalink integration."""
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, CONF_CONNECTION_TYPE, CONNECTION_CLOUD


COMMAND_TRANSLATION_KEYS = {
    "americano": "brew_americano",
    "caffe_latte": "brew_caffe_latte",
    "cappuccino": "brew_cappuccino",
    "cappuccino_mix": "brew_cappuccino_mix",
    "cappuccino_plus": "brew_cappuccino_plus",
    "coffee": "brew_coffee",
    "cortado": "brew_cortado",
    "doppio_plus": "brew_doppio_plus",
    "double_espresso": "brew_double_espresso",
    "espresso": "brew_espresso",
    "espresso_macchiato": "brew_espresso_macchiato",
    "espresso_soul": "brew_espresso_soul",
    "flat_white": "brew_flat_white",
    "hot_milk": "brew_hot_milk",
    "hot_water": "brew_hot_water",
    "latte_macchiato": "brew_latte_macchiato",
    "long_coffee": "brew_long_coffee",
    "stop": "stop_brewing",
}


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the button platform.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Function to add entities.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device = data["device"]

    # Get available commands from the device
    cmds = await hass.async_add_executor_job(device.get_commands)

    entities = []
    for cmd in cmds:
        # Filter out power commands as they might be handled elsewhere
        if cmd.lower() not in ["wakeup", "standby", "refresh"]:
            entities.append(CremalinkButton(coordinator, device, cmd, entry))
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
        self._title = cmd.replace("_", " ").title()

        translation_key = COMMAND_TRANSLATION_KEYS.get(cmd)

        if translation_key is not None:
            self._attr_has_entity_name = True
            self._attr_translation_key = translation_key
        else:
            # Keep commands from newer device maps visible before a
            # dedicated translation has been added.
            self._attr_name = f"Brew {self._title}"
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
        if self._cmd == "stop":
            return super().available and self.coordinator.data.is_busy
        return super().available and not self.coordinator.data.is_busy

    async def async_press(self):
        """Handle the button press."""
        await self.hass.async_add_executor_job(self.device.do, self._cmd)
        await self.coordinator.async_request_refresh()
