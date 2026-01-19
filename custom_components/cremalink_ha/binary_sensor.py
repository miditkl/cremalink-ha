from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

BINARY_SENSORS = [
    ("is_busy", "Busy", None, BinarySensorDeviceClass.RUNNING),
    ("is_idle", "Idle", "mdi:sleep", None),
    ("is_watertank_open", "Water Tank Open", "mdi:water-boiler-alert", BinarySensorDeviceClass.DOOR),
    ("is_watertank_empty", "Water Tank Empty", "mdi:water-off", BinarySensorDeviceClass.PROBLEM),
    ("is_waste_container_full", "Waste Container Full", "mdi:delete-alert", BinarySensorDeviceClass.PROBLEM),
    ("is_waste_container_missing", "Waste Container Missing", "mdi:delete-alert", BinarySensorDeviceClass.PROBLEM),
]


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    entities = []
    for key, name, icon, dev_class in BINARY_SENSORS:
        entities.append(CremalinkBinarySensor(coordinator, entry, key, name, icon, dev_class))

    async_add_entities(entities)


class CremalinkBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, name, icon, dev_class):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"{entry.title} {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = icon
        self._attr_device_class = dev_class

    @property
    def is_on(self):
        return getattr(self.coordinator.data, self._key, None)
