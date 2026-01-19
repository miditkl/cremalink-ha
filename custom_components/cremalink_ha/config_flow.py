import logging
import os
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from cremalink.devices import get_device_maps

from .const import *

_LOGGER = logging.getLogger(__name__)


def get_available_maps(hass: HomeAssistant) -> list[str]:
    try:
        maps = list(get_device_maps())
    except Exception:
        maps = []

    custom_dir = hass.config.path(CUSTOM_MAP_DIR)
    if os.path.exists(custom_dir):
        for f in os.listdir(custom_dir):
            if f.endswith(".json"):
                maps.append(f"custom:{f}")
    maps.sort()
    return maps


class CremalinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _addon_url = DEFAULT_ADDON_URL

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            self._addon_url = user_input[CONF_ADDON_URL]
            try:
                import requests
                def _check():
                    return requests.get(f"{self._addon_url.rstrip('/')}/health", timeout=5)

                resp = await self.hass.async_add_executor_job(_check)
                if resp.status_code == 200:
                    return await self.async_step_device()
            except Exception:
                pass

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDON_URL, default=DEFAULT_ADDON_URL): str}),
            errors=errors
        )

    async def async_step_device(self, user_input=None):
        errors = {}
        maps = await self.hass.async_add_executor_job(get_available_maps, self.hass)
        if user_input:
            user_input[CONF_ADDON_URL] = self._addon_url
            return self.async_create_entry(title=f"{user_input[DEVICE_NAME]}", data=user_input)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({
                vol.Required(DEVICE_NAME): str,
                vol.Required(CONF_DSN): str,
                vol.Required(CONF_LAN_KEY): str,
                vol.Required(CONF_DEVICE_IP): str,
                vol.Required(CONF_DEVICE_MAP): vol.In(maps) if maps else str,
            }),
            errors=errors,
        )
