"""Config flow for the Cremalink integration."""

import json
import logging
import os

import voluptuous as vol
from cremalink.devices import get_device_maps, load_device_map
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from cremalink import Client, authenticate_cloud, detect_model_id

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


def get_map_data(hass: HomeAssistant, map_name: str) -> dict:
    """Retrieve data for a specific map."""
    if map_name.startswith("custom:"):
        filename = map_name.replace("custom:", "", 1)
        custom_dir = hass.config.path(CUSTOM_MAP_DIR)
        filepath = os.path.join(custom_dir, filename)
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    else:
        try:
            return load_device_map(map_name)
        except Exception:
            return {}


class CremalinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cremalink."""

    VERSION = 1
    _addon_url = DEFAULT_ADDON_URL
    _temp_token_file: str | None = None
    _discovered_devices: list[str] = []
    _selected_map: str | None = None

    # Cloud-assisted onboarding state (spec: Cloud-Assisted Device Onboarding)
    _cloud_token_file: str | None = None
    _cloud_devices: list[dict] = []
    _cloud_selected_device: dict | None = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step: cloud login (email/password), replacing the
        previous device-map-first flow. An "advanced setup" checkbox routes to
        :meth:`async_step_manual` for users without cloud account access.
        """
        errors = {}
        if user_input is not None:
            if user_input.get(CONF_MANUAL_SETUP):
                return await self.async_step_manual()

            email = user_input.get(CONF_EMAIL)
            password = user_input.get(CONF_PASSWORD)
            if not email or not password:
                errors["base"] = "missing_credentials"
            else:

                def _login_and_discover():
                    token = authenticate_cloud(email, password)
                    token_dir = self.hass.config.path(TOKEN_DIR)
                    os.makedirs(token_dir, exist_ok=True)
                    temp_file = os.path.join(token_dir, "temp_token.json")
                    token.save(temp_file)
                    client = Client(temp_file)
                    raw_devices = client.get_devices()
                    coffee_devices = client.list_account_devices()
                    return temp_file, raw_devices, coffee_devices

                try:
                    temp_file, raw_devices, coffee_devices = (
                        await self.hass.async_add_executor_job(_login_and_discover)
                    )
                except (
                    Exception
                ) as e:
                    _LOGGER.error("Cloud login failed: %s", e)
                    errors["base"] = "auth_failed"
                else:
                    self._cloud_token_file = temp_file
                    if not raw_devices:
                        errors["base"] = "no_devices"
                    elif not coffee_devices:
                        errors["base"] = "no_coffee_machine"
                    else:
                        self._cloud_devices = coffee_devices
                        if len(coffee_devices) > 1:
                            return await self.async_step_device_select()
                        return await self._async_select_cloud_device(coffee_devices[0])

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_EMAIL): str,
                    vol.Optional(CONF_PASSWORD): str,
                    vol.Optional(CONF_MANUAL_SETUP, default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_device_select(self, user_input=None):
        """Let the user pick which discovered coffee machine to add (>1 found)."""
        if user_input is not None:
            dsn = user_input[CONF_DSN]
            device = next((d for d in self._cloud_devices if d["dsn"] == dsn), None)
            if device is not None:
                return await self._async_select_cloud_device(device)

        options = {
            d["dsn"]: f"{d.get('product_name') or d['dsn']} ({d['dsn']})"
            for d in self._cloud_devices
        }
        return self.async_show_form(
            step_id="device_select",
            data_schema=vol.Schema({vol.Required(CONF_DSN): vol.In(options)}),
        )

    async def _async_select_cloud_device(self, device: dict):
        """Set the device's unique id, detect its model, and continue the flow."""
        await self.async_set_unique_id(device["dsn"])
        self._abort_if_unique_id_configured()
        self._cloud_selected_device = device

        def _detect():
            client = Client(self._cloud_token_file)
            serial = client.get_serial_number(device["dsn"])
            return detect_model_id(
                serial,
                {
                    "model": device.get("oem_model"),
                    "product_name": device.get("product_name"),
                },
                device.get("oem_model"),
            )

        model_id = await self.hass.async_add_executor_job(_detect)
        if model_id is None:
            return await self.async_step_manual_map()
        return await self._async_complete_cloud_entry(device, model_id)

    async def async_step_manual_map(self, user_input=None):
        """Fallback device-map picker when automatic detection is inconclusive.

        Shown only when :func:`detect_model_id` returns ``None`` — the DSN,
        friendly name, and any LAN details are already known from the cloud
        discovery step and are not re-requested from the user.
        """
        device = self._cloud_selected_device or {}
        if user_input is not None:
            return await self._async_complete_cloud_entry(
                device, user_input[CONF_DEVICE_MAP]
            )

        maps = await self.hass.async_add_executor_job(get_available_maps, self.hass)
        return self.async_show_form(
            step_id="manual_map",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_MAP): vol.In(maps) if maps else str,
                }
            ),
            description_placeholders={
                "dsn": device.get("dsn", ""),
                "device_name": device.get("product_name") or device.get("dsn", ""),
            },
        )

    async def _async_complete_cloud_entry(self, device: dict, device_map_id: str):
        """Fetch LAN details and create the entry as local (if supported and
        available) or cloud (fallback), per FR-006/FR-007/FR-008.
        """
        dsn = device["dsn"]
        device_name = device.get("product_name") or dsn

        def _fetch_lan():
            client = Client(self._cloud_token_file)
            return client.get_lan_config(dsn)

        map_data = await self.hass.async_add_executor_job(
            get_map_data, self.hass, device_map_id
        )
        support = map_data.get("support", {})

        lan = {"lan_enabled": False}
        if support.get("local"):
            lan = await self.hass.async_add_executor_job(_fetch_lan)

        if (
            lan.get("lan_enabled")
            and lan.get("lan_ip")
            and lan.get("lanip_key")
            and support.get("local")
        ):
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_LOCAL,
                DEVICE_NAME: device_name,
                CONF_DSN: dsn,
                CONF_DEVICE_MAP: device_map_id,
                CONF_ADDON_URL: self._addon_url,
                CONF_LAN_KEY: lan["lanip_key"],
                CONF_DEVICE_IP: lan["lan_ip"],
            }
            # Local connection doesn't need the cloud refresh token — discard it.
            if self._cloud_token_file and os.path.exists(self._cloud_token_file):
                os.remove(self._cloud_token_file)
        else:
            token_dir = self.hass.config.path(TOKEN_DIR)
            final_token_path = os.path.join(token_dir, f"{dsn}.json")
            if self._cloud_token_file and os.path.exists(self._cloud_token_file):
                os.rename(self._cloud_token_file, final_token_path)
            data = {
                CONF_CONNECTION_TYPE: CONNECTION_CLOUD,
                DEVICE_NAME: device_name,
                CONF_DSN: dsn,
                CONF_DEVICE_MAP: device_map_id,
                CONF_TOKEN_FILE: final_token_path,
            }

        return self.async_create_entry(title=device_name, data=data)

    async def async_step_manual(self, user_input=None):
        """Handle the advanced/manual setup step (device-map picker first).

        This is today's original first step, preserved verbatim for users
        without cloud account access or who prefer not to use cloud-assisted
        onboarding (FR-010).
        """
        errors = {}
        if user_input is not None:
            self._selected_map = user_input[CONF_DEVICE_MAP]

            # Check support
            map_data = await self.hass.async_add_executor_job(
                get_map_data, self.hass, self._selected_map
            )
            support = map_data.get("support", {})
            local_support = support.get("local", False)
            cloud_support = support.get("cloud", False)

            if local_support and cloud_support:
                return self.async_show_menu(
                    step_id="choose_connection",
                    menu_options={
                        "local": "Local Network (Add-on) [recommended]",
                        "cloud_auth": "Cloud (Ayla Networks)",
                    },
                )
            elif local_support:
                return await self.async_step_local()
            elif cloud_support:
                return await self.async_step_cloud_auth()
            else:
                errors["base"] = "no_support"

        maps = await self.hass.async_add_executor_job(get_available_maps, self.hass)
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_MAP): vol.In(maps)}),
            errors=errors,
        )

    async def async_step_choose_connection(self, user_input=None):
        """Handle the connection choice step."""
        if user_input == "local":
            return await self.async_step_local()
        elif user_input == "cloud_auth":
            return await self.async_step_cloud_auth()
        return self.async_abort(reason="unknown_choice")

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
                    return requests.get(
                        f"{self._addon_url.rstrip('/')}/health", timeout=5
                    )

                resp = await self.hass.async_add_executor_job(_check)
                if resp.status_code == 200:
                    return await self.async_step_device()
            except Exception:
                pass

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDON_URL, default=DEFAULT_ADDON_URL): str}
            ),
            errors=errors,
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

            if self._selected_map and CONF_DEVICE_MAP not in user_input:
                user_input[CONF_DEVICE_MAP] = self._selected_map

            await self.async_set_unique_id(user_input[CONF_DSN])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"{user_input[DEVICE_NAME]}", data=user_input
            )

        schema = {
            vol.Required(DEVICE_NAME): str,
            vol.Required(CONF_DSN): str,
            vol.Required(CONF_LAN_KEY): str,
            vol.Required(CONF_DEVICE_IP): str,
        }
        if not self._selected_map:
            schema[vol.Required(CONF_DEVICE_MAP)] = vol.In(maps) if maps else str

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(schema),
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

                self._discovered_devices = await self.hass.async_add_executor_job(
                    _auth_and_fetch
                )
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
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_REFRESH_TOKEN): str,
                }
            ),
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

            if self._selected_map and CONF_DEVICE_MAP not in user_input:
                user_input[CONF_DEVICE_MAP] = self._selected_map

            data = {
                CONF_CONNECTION_TYPE: CONNECTION_CLOUD,
                DEVICE_NAME: dsn,  # Default name, user can change later in HA entity settings
                CONF_DSN: dsn,
                CONF_DEVICE_MAP: user_input[CONF_DEVICE_MAP],
                CONF_TOKEN_FILE: final_token_path,
            }

            return self.async_create_entry(title=dsn, data=data)

        schema = {
            vol.Required(DEVICE_NAME): str,
            vol.Required(CONF_DSN): vol.In(self._discovered_devices),
        }
        if not self._selected_map:
            schema[vol.Required(CONF_DEVICE_MAP)] = vol.In(maps) if maps else str

        return self.async_show_form(
            step_id="cloud_device",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
