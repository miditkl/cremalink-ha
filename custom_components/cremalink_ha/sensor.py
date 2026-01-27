"""Sensor platform for the Cremalink integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

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

    entities = []
    for key, name, icon, unit in SENSORS:
        entities.append(CremalinkSensor(coordinator, entry, key, name, icon, unit))

    async_add_entities(entities)


class CremalinkSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Cremalink sensor."""

    def __init__(self, coordinator, entry, key, name, icon, unit):
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
        self._key = key
        self._attr_name = f"{entry.title} {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        """Return the value of the sensor."""
        return getattr(self.coordinator.data, self._key, None)
