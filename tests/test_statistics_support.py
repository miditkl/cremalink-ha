"""Tests for ECAM610 statistics capability gating."""

from custom_components.cremalink_ha import supports_ecam610_statistics


def test_ecam610_statistics_supported():
    assert supports_ecam610_statistics("ECAM610")
    assert supports_ecam610_statistics("ecam610")
    assert supports_ecam610_statistics("ECAM610.json")


def test_other_models_do_not_use_ecam610_statistics_semantics():
    assert not supports_ecam610_statistics("ECAM612")
    assert not supports_ecam610_statistics("ECAM452")
    assert not supports_ecam610_statistics("custom:ECAM610.json")
    assert not supports_ecam610_statistics("")
