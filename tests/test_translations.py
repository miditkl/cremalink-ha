import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "custom_components" / "cremalink_ha"


def load(path):
    return json.loads((BASE / path).read_text())


def shape(value):
    if isinstance(value, dict):
        return {key: shape(child) for key, child in value.items()}
    if isinstance(value, list):
        return [shape(child) for child in value]
    return None


def test_english_translations_match_strings():
    assert load("strings.json") == load("translations/en.json")


def test_german_translation_structure_is_complete():
    assert shape(load("strings.json")) == shape(load("translations/de.json"))


def test_expected_entity_platforms_exist():
    strings = load("strings.json")
    assert set(strings["entity"]) == {
        "sensor",
        "button",
        "binary_sensor",
        "switch",
    }


def test_expected_entity_keys_exist():
    entity = load("strings.json")["entity"]

    assert set(entity["sensor"]) == {
        "status_name",
        "progress_percent",
        "accessory_name",
    }

    assert set(entity["binary_sensor"]) == {
        "is_busy",
        "is_idle",
        "is_watertank_open",
        "is_watertank_empty",
        "is_waste_container_full",
        "is_waste_container_missing",
    }

    assert set(entity["switch"]) == {"power"}

    assert set(entity["button"]) == {
        "brew_americano",
        "brew_caffe_latte",
        "brew_cappuccino",
        "brew_cappuccino_mix",
        "brew_cappuccino_plus",
        "brew_coffee",
        "brew_cortado",
        "brew_doppio_plus",
        "brew_double_espresso",
        "brew_espresso",
        "brew_espresso_macchiato",
        "brew_espresso_soul",
        "brew_flat_white",
        "brew_hot_milk",
        "brew_hot_water",
        "brew_latte_macchiato",
        "brew_long_coffee",
        "stop_brewing",
    }
