"""Sensor platform for the Cremalink integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, GITHUB_URL

SENSORS = [
    ("status_name", "Status", "mdi:coffee-maker", None),
    ("progress_percent", "Progress", "mdi:progress-clock", PERCENTAGE),
    ("accessory_name", "Accessory", "mdi:cup", None),
]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Function to add entities.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    device = data["device"]

    entities = [
        CremalinkSensor(coordinator, device, entry, key, name, icon, unit)
        for key, name, icon, unit in SENSORS
    ]
    async_add_entities(entities)


class CremalinkSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Cremalink sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, device, entry, key, name, icon, unit):
        """Initialize the sensor.

        Args:
            coordinator: The data update coordinator.
            entry: The config entry.
            key: The key to identify the sensor data.
            name: The name of the sensor.
            icon: The icon for the sensor.
            unit: The unit of measurement for the sensor.
        """
        super().__init__(coordinator)
        self.device = device
        self.entry = entry
        self._key = key

        # Short entity name; device name comes from device_info
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{device.dsn}_{key}"
        self._attr_native_unit_of_measurement = unit

    @property
    def device_info(self):
        """Return device information so HA groups sensors under the Hub device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.dsn)},   # Must be identical across all entities
            name=self.entry.title,                     # Device (Hub) name
            manufacturer="Cremalink",
            model="Smart Coffee Machine",
            sw_version=getattr(self.device, "firmware_version", None),
            # Leave the GitHub URL on the Device page:
            configuration_url= GITHUB_URL,
        )

    @property
    def available(self):
        """Entity is available only when coordinator has data."""
        return bool(self.coordinator.data)

    @property
    def native_value(self):
        """Return the current sensor value from coordinator data."""
        data = self.coordinator.data
        return getattr(data, self._key, None) if data else None

