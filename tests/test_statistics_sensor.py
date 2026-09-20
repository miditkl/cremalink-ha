"""Tests for ECAM610 statistics sensors."""

from types import SimpleNamespace

from custom_components.cremalink_ha.sensor import (
    CremalinkStatisticsDiagnosticsSensor,
    CremalinkStatisticsSensor,
)


class FakeCoordinator:
    """Minimal coordinator carrying a statistics snapshot."""

    def __init__(self, data):
        self.data = data
        self.last_update_success = True
        self.refresh_in_progress = False


ENTRY = SimpleNamespace(
    title="Test Coffee Machine",
    entry_id="test-ecam610",
)


SNAPSHOT = {
    "known": {
        "total_beverages": 1234,
        "total_black_beverages": 234,
        "total_milk_beverages": 1000,
        "total_water_l": 321.5,
        "descale_count": 7,
        "filter_replacements": 4,
        "grounds_container_clean_count": 456,
    },
    "unknown": {
        43000: 111,
        43005: 222,
        43014: 333,
    },
    "raw": {
        105: 7,
        106: 643000,
        108: 4,
        115: 456,
        3000: 234,
        43000: 111,
        43005: 222,
        43010: 1234,
        43014: 333,
    },
    "snapshot_fetched_at": "2026-08-25T07:00:00+00:00",
}


def make_sensor(key, name="Test", unit=None):
    return CremalinkStatisticsSensor(
        FakeCoordinator(SNAPSHOT),
        ENTRY,
        key,
        name,
        "mdi:counter",
        unit,
    )


def test_total_beverages():
    sensor = make_sensor("total_beverages")

    assert sensor.available is True
    assert sensor.native_value == 1234
    assert sensor._attr_unique_id == (
        "test-ecam610_statistics_total_beverages"
    )


def test_total_milk_beverages():
    sensor = make_sensor("total_milk_beverages")

    assert sensor.available is True
    assert sensor.native_value == 1000


def test_total_water():
    sensor = make_sensor(
        "total_water_l",
        name="Total water",
        unit="L",
    )

    assert sensor.available is True
    assert sensor.native_value == 321.5
    assert sensor._attr_native_unit_of_measurement == "L"
    assert sensor._attr_suggested_display_precision == 1


def test_maintenance_statistics():
    assert make_sensor("descale_count").native_value == 7
    assert make_sensor("filter_replacements").native_value == 4
    assert make_sensor("grounds_container_clean_count").native_value == 456


def test_missing_statistic_is_unavailable():
    sensor = make_sensor("does_not_exist")

    assert sensor.available is False
    assert sensor.native_value is None


def test_statistics_retains_last_value_after_failed_update():
    coordinator = FakeCoordinator(SNAPSHOT)
    coordinator.last_update_success = False

    sensor = CremalinkStatisticsSensor(
        coordinator,
        ENTRY,
        "total_beverages",
        "Total beverages",
        "mdi:counter",
        None,
    )

    assert sensor.available is True
    assert sensor.native_value == 1234


def test_diagnostics_sensor_preserves_unknown_and_raw_values():
    sensor = CremalinkStatisticsDiagnosticsSensor(
        FakeCoordinator(SNAPSHOT),
        ENTRY,
    )

    assert sensor.available is True
    assert sensor.native_value == 3

    attrs = sensor.extra_state_attributes

    assert attrs["unknown_statistics"] == {
        "43000": 111,
        "43005": 222,
        "43014": 333,
    }
    assert attrs["raw_statistics"]["43010"] == 1234
    assert attrs["raw_statistics"]["106"] == 643000
    assert attrs["raw_count"] == 9
    assert (
        attrs["snapshot_fetched_at"]
        == "2026-08-25T07:00:00+00:00"
    )
    assert attrs["refresh_in_progress"] is False


def test_diagnostics_entity_disabled_by_default():
    sensor = CremalinkStatisticsDiagnosticsSensor(
        FakeCoordinator(SNAPSHOT),
        ENTRY,
    )

    assert sensor._attr_entity_registry_enabled_default is False



def test_diagnostics_sensor_exposes_refresh_progress():
    coordinator = FakeCoordinator(SNAPSHOT)
    coordinator.refresh_in_progress = True
    coordinator.refresh_started_at = "2026-08-25T10:00:00+00:00"
    coordinator.refresh_running_for_seconds = 42.5
    coordinator.last_refresh_duration_seconds = 123.4
    coordinator.a2_progress = {
        "phase": "page_complete",
        "page": 4,
        "start_id": 23000,
        "request_count": 7,
        "returned_count": 7,
        "last_id": 23006,
        "collected_count": 39,
    }

    sensor = CremalinkStatisticsDiagnosticsSensor(
        coordinator,
        ENTRY,
    )

    attrs = sensor.extra_state_attributes

    assert attrs["refresh_in_progress"] is True
    assert (
        attrs["refresh_started_at"]
        == "2026-08-25T10:00:00+00:00"
    )
    assert attrs["refresh_running_for_seconds"] == 42.5
    assert attrs["last_refresh_duration_seconds"] == 123.4
    assert attrs["a2_phase"] == "page_complete"
    assert attrs["a2_page"] == 4
    assert attrs["a2_start_id"] == 23000
    assert attrs["a2_request_count"] == 7
    assert attrs["a2_returned_count"] == 7
    assert attrs["a2_last_id"] == 23006
    assert attrs["a2_collected_count"] == 39


def test_diagnostics_sensor_exposes_service_properties():
    """Diagnostic attributes should expose auxiliary d5xx values."""

    snapshot = {
        "known": {"total_beverages": 42},
        "unknown": {100: 111, 109: 222},
        "raw": {100: 111, 109: 222, 43010: 42},
        "service_properties": {
            "d550_water_calc_qty": 333,
            "d555_water_filter_qty": 444,
            "d556_water_hardness": 3,
            "d512_percentage_to_deca": 55,
            "d513_percentage_usage_fltr": 66,
        },
    }

    sensor = CremalinkStatisticsDiagnosticsSensor(
        FakeCoordinator(snapshot),
        ENTRY,
    )

    attrs = sensor.extra_state_attributes

    assert attrs["service_properties"] == {
        "d550_water_calc_qty": 333,
        "d555_water_filter_qty": 444,
        "d556_water_hardness": 3,
        "d512_percentage_to_deca": 55,
        "d513_percentage_usage_fltr": 66,
    }
