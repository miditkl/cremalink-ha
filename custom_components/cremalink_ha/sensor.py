"""Sensor platform for the Cremalink integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CONNECTION_TYPE, CONNECTION_CLOUD

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
        self._connection_type = entry.data.get(CONF_CONNECTION_TYPE)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="cremalink",
        )

    @property
    def available(self):
        """Return True if entity is available."""
        if self._connection_type == CONNECTION_CLOUD:  # TODO: WORKAROUND Monitor in cremalink is not working properly, when using Cloud Device. 
            return True
        if not self.coordinator.data:
            return False
        return super().available

    @property
    def native_value(self):
        """Return the value of the sensor."""
        return getattr(self.coordinator.data, self._key, None)
