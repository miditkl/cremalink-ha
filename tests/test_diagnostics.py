"""Tests for diagnostics.py redaction of cloud-assisted onboarding secrets."""
import asyncio
from unittest.mock import MagicMock

from custom_components.cremalink_ha.const import DOMAIN
from custom_components.cremalink_ha.diagnostics import (
    REDACT_KEYS,
    async_get_config_entry_diagnostics,
)


def _run(coro):
    return asyncio.run(coro)


def test_diagnostics_redacts_sensitive_fields():
    entry = MagicMock()
    entry.data = {
        "email": "user@example.com",
        "password": "hunter2",
        "access_token": "at-secret",
        "refresh_token": "rt-secret",
        "lan_key": "lan-secret",
        "device_ip": "192.168.1.5",
        "dsn": "DSN1",
        "device_map": "ECAM452",
    }
    entry.options = {}
    entry.entry_id = "entry1"

    hass = MagicMock()
    coordinator = MagicMock()
    coordinator.data = {"status": "ok"}
    hass.data = {DOMAIN: {"entry1": {"coordinator": coordinator}}}

    result = _run(async_get_config_entry_diagnostics(hass, entry))

    redacted = result["entry_data"]
    for key in REDACT_KEYS:
        assert redacted[key] == "**REDACTED**"
    assert redacted["dsn"] == "DSN1"
    assert redacted["device_map"] == "ECAM452"
