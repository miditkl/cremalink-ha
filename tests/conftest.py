"""Shared fixtures for Cremalink tests.

Mock homeassistant at module level so imports work during collection.
Ported from delonghi-ha/tests/conftest.py's approach: stub HA modules with
MagicMock, then replace the specific bases config_flow.py/diagnostics.py
actually subclass or call with real, minimal stand-ins.
"""

import sys
from unittest.mock import MagicMock

_HA_MODULES = [
    "homeassistant",
    "homeassistant.core",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.data_entry_flow",
    "homeassistant.components",
    "homeassistant.components.diagnostics",
]


def _real_redact(data, keys_to_redact):
    """Stand-in for HA's async_redact_data — redacts top-level keys."""
    if not isinstance(data, dict):
        return data
    return {k: ("**REDACTED**" if k in keys_to_redact else v) for k, v in data.items()}


for mod_name in _HA_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

sys.modules["homeassistant.components.diagnostics"].async_redact_data = _real_redact


# Real ConfigFlow stub so config_flow.py's `class Foo(ConfigFlow, domain=...)`
# subclasses a real class instead of silently producing a MagicMock.
class _ConfigFlowBase:
    """Stand-in for HA's config_entries.ConfigFlow base."""

    def __init_subclass__(cls, **_kwargs) -> None:  # accept domain= kwarg
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id: str) -> None:
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        return None

    def async_create_entry(self, *, title: str, data: dict) -> dict:
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id: str, data_schema=None, errors=None, description_placeholders=None) -> dict:
        return {
            "type": "form",
            "step_id": step_id,
            "data_schema": data_schema,
            "errors": errors or {},
            "description_placeholders": description_placeholders,
        }

    def async_show_menu(self, *, step_id: str, menu_options=None) -> dict:
        return {"type": "menu", "step_id": step_id, "menu_options": menu_options}

    def async_abort(self, *, reason: str) -> dict:
        return {"type": "abort", "reason": reason}


_ce_mod = sys.modules["homeassistant.config_entries"]
_ce_mod.ConfigFlow = _ConfigFlowBase

_ha_mod = sys.modules["homeassistant"]
_ha_mod.config_entries = _ce_mod
_ha_mod.const = sys.modules["homeassistant.const"]
_ha_mod.core = sys.modules["homeassistant.core"]
_ha_mod.exceptions = sys.modules["homeassistant.exceptions"]
_ha_mod.helpers = sys.modules["homeassistant.helpers"]
_ha_mod.components = sys.modules["homeassistant.components"]

_exc_mod = sys.modules["homeassistant.exceptions"]
_exc_mod.ConfigEntryNotReady = type("ConfigEntryNotReady", (Exception,), {})
_exc_mod.HomeAssistantError = type("HomeAssistantError", (Exception,), {})

sys.modules["homeassistant.const"].Platform = MagicMock()
