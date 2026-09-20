"""Sensor platform for the Cremalink integration."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfVolume,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CONNECTION_TYPE, CONNECTION_CLOUD

SENSORS = [
    ("status_name", "Status", "mdi:coffee-maker", None),
    ("progress_percent", "Progress", "mdi:progress-clock", PERCENTAGE),
    ("accessory_name", "Accessory", "mdi:cup", None),
]


STATISTICS_SENSORS = [
    # Overall totals
    (
        "total_beverages",
        "Total beverages",
        "mdi:counter",
        None,
    ),
    (
        "total_black_beverages",
        "Black beverages",
        "mdi:coffee",
        None,
    ),
    (
        "total_milk_beverages",
        "Milk beverages",
        "mdi:cup",
        None,
    ),
    (
        "total_other_beverages",
        "Other beverages",
        "mdi:counter",
        None,
    ),
    (
        "total_water_l",
        "Total water",
        "mdi:water",
        UnitOfVolume.LITERS,
    ),

    # ECAM610 top-level internal categories
    (
        "total_milk_coffee_beverages",
        "Milk coffee category",
        "mdi:coffee",
        None,
    ),
    (
        "total_milk_only_beverages",
        "Milk only category",
        "mdi:cup",
        None,
    ),
    (
        "total_espressos",
        "Espressos total",
        "mdi:coffee",
        None,
    ),

    # Individual beverages
    (
        "espresso",
        "Espresso",
        "mdi:coffee",
        None,
    ),
    (
        "coffee",
        "Coffee",
        "mdi:coffee",
        None,
    ),
    (
        "long_coffee",
        "Long coffee",
        "mdi:coffee",
        None,
    ),
    (
        "doppio",
        "Doppio+",
        "mdi:coffee",
        None,
    ),
    (
        "americano",
        "Americano",
        "mdi:coffee",
        None,
    ),
    (
        "cappuccino",
        "Cappuccino",
        "mdi:coffee",
        None,
    ),
    (
        "latte_macchiato",
        "Latte Macchiato",
        "mdi:coffee",
        None,
    ),
    (
        "caffe_latte",
        "Caffè Latte",
        "mdi:coffee",
        None,
    ),
    (
        "flat_white",
        "Flat White",
        "mdi:coffee",
        None,
    ),
    (
        "espresso_macchiato",
        "Espresso Macchiato",
        "mdi:coffee",
        None,
    ),
    (
        "hot_milk",
        "Hot milk",
        "mdi:cup",
        None,
    ),
    (
        "cappuccino_doppio",
        "Cappuccino Doppio+",
        "mdi:coffee",
        None,
    ),
    (
        "cappuccino_mix",
        "Cappuccino Mix",
        "mdi:coffee",
        None,
    ),
    (
        "hot_water",
        "Hot water",
        "mdi:cup-water",
        None,
    ),
    (
        "tea",
        "Tea",
        "mdi:tea",
        None,
    ),
    (
        "coffee_pot",
        "Coffee pot",
        "mdi:coffee-maker",
        None,
    ),

    (
        "espresso_soul",
        "Espresso SOUL",
        "mdi:coffee",
        None,
    ),
    (
        "over_ice",
        "Over Ice",
        "mdi:cup",
        None,
    ),
    (
        "custom_milk_coffee_beverages",
        "Custom milk-coffee beverages",
        "mdi:coffee",
        None,
    ),

    # Maintenance
    (
        "descale_count",
        "Descales",
        "mdi:shimmer",
        None,
    ),
    (
        "filter_replacements",
        "Filter replacements",
        "mdi:water-check",
        None,
    ),
    (
        "grounds_container_clean_count",
        "Grounds container cleanings",
        "mdi:delete-empty",
        None,
    ),
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
    statistics_coordinator = data.get("statistics_coordinator")

    entities = []
    for key, name, icon, unit in SENSORS:
        entities.append(CremalinkSensor(coordinator, entry, key, name, icon, unit))

    if statistics_coordinator is not None:
        for key, name, icon, unit in STATISTICS_SENSORS:
            entities.append(
                CremalinkStatisticsSensor(
                    statistics_coordinator,
                    entry,
                    key,
                    name,
                    icon,
                    unit,
                )
            )

        entities.append(
            CremalinkStatisticsDiagnosticsSensor(
                statistics_coordinator,
                entry,
            )
        )

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
        if not self.coordinator.data:
            return False
        return super().available

    @property
    def native_value(self):
        """Return the value of the sensor."""
        return getattr(self.coordinator.data, self._key, None)


class CremalinkStatisticsSensor(
    CoordinatorEntity,
    SensorEntity,
):
    """Representation of a live ECAM610 A2 statistic."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator,
        entry,
        key,
        name,
        icon,
        unit,
    ):
        """Initialize an ECAM610 statistics sensor."""

        super().__init__(coordinator)

        self._key = key
        self._attr_name = f"{entry.title} {name}"
        self._attr_unique_id = (
            f"{entry.entry_id}_statistics_{key}"
        )
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit

        if key == "total_water_l":
            self._attr_suggested_display_precision = 1

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="De'Longhi",
        )

    @property
    def available(self):
        """Return whether statistics are currently available."""

        data = self.coordinator.data

        if not isinstance(data, dict):
            return False

        known = data.get("known")

        if not isinstance(known, dict):
            return False

        # Lifetime/statistics values are slow-changing.  A transient
        # coordinator failure must not discard the last successfully
        # received value or mark the entity unavailable.
        return self._key in known

    @property
    def native_value(self):
        """Return the semantic A2 statistic."""

        data = self.coordinator.data or {}
        known = data.get("known", {})

        return known.get(self._key)


class CremalinkStatisticsDiagnosticsSensor(
    CoordinatorEntity,
    SensorEntity,
):
    """Diagnostic access to complete raw/unknown A2 statistics."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    # Avoid recording the complete raw statistics dictionary unless the
    # user explicitly enables this diagnostic entity.
    _attr_entity_registry_enabled_default = False

    _attr_icon = "mdi:code-braces"

    def __init__(
        self,
        coordinator,
        entry,
    ):
        """Initialize the raw statistics diagnostic entity."""

        super().__init__(coordinator)

        self._attr_name = (
            f"{entry.title} A2 statistics diagnostics"
        )
        self._attr_unique_id = (
            f"{entry.entry_id}_statistics_diagnostics"
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="De'Longhi",
        )

    @property
    def available(self):
        """Return whether a statistics snapshot exists."""

        return (
            isinstance(self.coordinator.data, dict)
            and super().available
        )

    @property
    def native_value(self):
        """Return the number of currently unknown A2 IDs."""

        data = self.coordinator.data or {}
        unknown = data.get("unknown", {})

        return len(unknown)

    @property
    def extra_state_attributes(self):
        """Expose unknown and complete raw A2 tables."""

        data = self.coordinator.data or {}

        unknown = data.get("unknown", {})
        raw = data.get("raw", {})

        progress = getattr(
            self.coordinator,
            "a2_progress",
            None,
        ) or {}

        # String keys are friendlier for HA's JSON/state machinery.
        return {
            "unknown_statistics": {
                str(key): value
                for key, value in unknown.items()
            },
            "raw_statistics": {
                str(key): value
                for key, value in raw.items()
            },
            "service_properties": data.get(
                "service_properties",
                {},
            ),
            "raw_count": len(raw),
            "snapshot_fetched_at": data.get("snapshot_fetched_at"),
            "refresh_in_progress": getattr(
                self.coordinator,
                "refresh_in_progress",
                False,
            ),
            "refresh_started_at": getattr(
                self.coordinator,
                "refresh_started_at",
                None,
            ),
            "refresh_running_for_seconds": getattr(
                self.coordinator,
                "refresh_running_for_seconds",
                None,
            ),
            "last_refresh_duration_seconds": getattr(
                self.coordinator,
                "last_refresh_duration_seconds",
                None,
            ),
            "a2_phase": progress.get("phase"),
            "a2_page": progress.get("page"),
            "a2_start_id": progress.get("start_id"),
            "a2_request_count": progress.get("request_count"),
            "a2_returned_count": progress.get("returned_count"),
            "a2_last_id": progress.get("last_id"),
            "a2_collected_count": progress.get("collected_count"),
        }
