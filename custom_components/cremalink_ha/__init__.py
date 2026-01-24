import logging
from urllib.parse import urlparse
from functools import partial


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from cremalink import create_local_device, device_map
from cremalink.devices import device_map as resolve_device_map

from .const import *
from .coordinator import CremalinkCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SWITCH, Platform.BUTTON, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    addon_url = entry.data[CONF_ADDON_URL]
    dsn = entry.data[CONF_DSN]
    lan_key = entry.data[CONF_LAN_KEY]
    device_ip = entry.data[CONF_DEVICE_IP]
    map_selection = entry.data[CONF_DEVICE_MAP]

    parsed_url = urlparse(addon_url)
    server_host = parsed_url.hostname
    server_port = parsed_url.port or 80

    try:
        if map_selection.startswith("custom:"):
            filename = map_selection.split(":", 1)[1]
            map_path = hass.config.path(CUSTOM_MAP_DIR, filename)
        else:
            map_path = await hass.async_add_executor_job(resolve_device_map, map_selection)

    except Exception as e:
        _LOGGER.error("Could not resolve device map '%s': %s", map_selection, e)
        return False

    try:
        device = await hass.async_add_executor_job(
            partial(
                create_local_device,
                dsn=dsn,
                server_host=server_host,
                server_port=server_port,
                device_ip=device_ip,
                lan_key=lan_key,
                device_map_path=str(map_path)
            )
        )

        await hass.async_add_executor_job(device.configure)

    except Exception as e:
        raise ConfigEntryNotReady(f"Could not connect to Cremalink server: {e}") from e

    coordinator = CremalinkCoordinator(hass, device)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "device": device
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
