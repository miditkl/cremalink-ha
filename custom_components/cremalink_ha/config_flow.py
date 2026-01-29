"""Config flow for the Cremalink integration."""
import logging
import os
import json
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from cremalink.devices import get_device_maps
from cremalink import Client

from .const import *

_LOGGER = logging.getLogger(__name__)


def get_available_maps(hass: HomeAssistant) -> list[str]:
    """Retrieve available device maps, including custom ones.

    Args:
        hass: The Home Assistant instance.

    Returns:
        A list of available device map identifiers.
    """
    try:
        # Get built-in maps from the library
        maps = list(get_device_maps())
    except Exception:
        maps = []

    # Check for custom maps in the configuration directory
    custom_dir = hass.config.path(CUSTOM_MAP_DIR)
    if os.path.exists(custom_dir):
        for f in os.listdir(custom_dir):
            if f.endswith(".json"):
                maps.append(f"custom:{f}")
    maps.sort()
    return maps


class CremalinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cremalink."""

    VERSION = 1
    _addon_url = DEFAULT_ADDON_URL
    _temp_token_file: str | None = None
    _discovered_devices: list[str] = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step.

        Args:
            user_input: Input data from the user.

        Returns:
            The next step in the flow.
        """
        return self.async_show_menu(
            step_id="user",
            menu_options={
                "local": "Local Network (Add-on) [recommended]",
                "cloud_auth": "Cloud (Ayla Networks)",
            }
        )

    async def async_step_local(self, user_input=None):
        """Handle the local connection step.

        Args:
            user_input: Input data from the user.

        Returns:
            The next step in the flow.
        """
        errors = {}
        if user_input is not None:
            self._addon_url = user_input[CONF_ADDON_URL]
            try:
                import requests

                def _check():
                    # Check health endpoint of the addon
                    return requests.get(f"{self._addon_url.rstrip('/')}/health", timeout=5)

                resp = await self.hass.async_add_executor_job(_check)
                if resp.status_code == 200:
                    return await self.async_step_device()
            except Exception:
                pass

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema({vol.Required(CONF_ADDON_URL, default=DEFAULT_ADDON_URL): str}),
            errors=errors
        )

    async def async_step_device(self, user_input=None):
        """Handle the local device configuration step.

        Args:
            user_input: Input data from the user
        Returns:
            The created config entry or the form to show.
        """
        errors = {}
        maps = await self.hass.async_add_executor_job(get_available_maps, self.hass)
        if user_input:
            user_input[CONF_ADDON_URL] = self._addon_url
            user_input[CONF_CONNECTION_TYPE] = CONNECTION_LOCAL

            await self.async_set_unique_id(user_input[CONF_DSN])
            self._abort_if_unique_id_configured()

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

    async def async_step_cloud_auth(self, user_input=None):
        """Handle the cloud authentication step.

        Args:
            user_input: Input data from the user.

        Returns:
            The next step in the flow.
        """
        errors = {}
        if user_input is not None:
            refresh_token = user_input[CONF_REFRESH_TOKEN]

            # Ensure token directory exists
            token_dir = self.hass.config.path(TOKEN_DIR)
            os.makedirs(token_dir, exist_ok=True)

            # Create a temporary token file
            temp_file = os.path.join(token_dir, "temp_token.json")

            try:
                def _auth_and_fetch():
                    with open(temp_file, "w") as f:
                        json.dump({"refresh_token": refresh_token}, f)

                    client = Client(temp_file)
                    return client.get_devices()

                self._discovered_devices = await self.hass.async_add_executor_job(_auth_and_fetch)
                self._temp_token_file = temp_file

                if not self._discovered_devices:
                    errors["base"] = "no_devices"
                else:
                    return await self.async_step_cloud_device()

            except Exception as e:
                _LOGGER.error("Authentication failed: %s", e)
                errors["base"] = "auth_failed"
                # Clean up if failed
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        return self.async_show_form(
            step_id="cloud_auth",
            data_schema=vol.Schema({
                vol.Required(CONF_REFRESH_TOKEN): str,
            }),
            errors=errors,
        )

    async def async_step_cloud_device(self, user_input=None):
        """Handle the cloud device selection step.

        Args:
            user_input: Input data from the user.

        Returns:
            The created config entry or the form to show.
        """
        errors = {}
        maps = await self.hass.async_add_executor_job(get_available_maps, self.hass)

        if user_input:
            dsn = user_input[CONF_DSN]

            # Check if already configured
            await self.async_set_unique_id(dsn)
            self._abort_if_unique_id_configured()

            # Move temp token file to permanent location
            token_dir = self.hass.config.path(TOKEN_DIR)
            final_token_path = os.path.join(token_dir, f"{dsn}.json")

            if self._temp_token_file and os.path.exists(self._temp_token_file):
                os.rename(self._temp_token_file, final_token_path)

            data = {
                CONF_CONNECTION_TYPE: CONNECTION_CLOUD,
                DEVICE_NAME: dsn,  # Default name, user can change later in HA entity settings
                CONF_DSN: dsn,
                CONF_DEVICE_MAP: user_input[CONF_DEVICE_MAP],
                CONF_TOKEN_FILE: final_token_path
            }

            return self.async_create_entry(title=dsn, data=data)

        return self.async_show_form(
            step_id="cloud_device",
            data_schema=vol.Schema({
                vol.Required(DEVICE_NAME): str,
                vol.Required(CONF_DSN): vol.In(self._discovered_devices),
                vol.Required(CONF_DEVICE_MAP): vol.In(maps) if maps else str,
            }),
            errors=errors,
        )
