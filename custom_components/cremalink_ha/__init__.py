"""The Cremalink Home Assistant integration."""
import logging
from urllib.parse import urlparse
from functools import partial


from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from cremalink import create_local_device, device_map, Client

from .const import *
from .coordinator import CremalinkCoordinator
from .statistics_coordinator import CremalinkStatisticsCoordinator

_LOGGER = logging.getLogger(__name__)



def supports_ecam610_statistics(map_selection: str) -> bool:
    """Return whether verified ECAM610 A2 semantics apply."""
    return str(map_selection).upper().removesuffix(".JSON") == "ECAM610"

PLATFORMS = [Platform.SWITCH, Platform.BUTTON, Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cremalink from a config entry.

        Args:
            hass: The Home Assistant instance.
            entry: The config entry.

        Returns:
            True if the setup was successful, False otherwise.
    """
    connection_type = entry.data.get(CONF_CONNECTION_TYPE, CONNECTION_LOCAL)

    statistics_token_file = None

    dsn = entry.data[CONF_DSN]

    map_selection = entry.data[CONF_DEVICE_MAP]

    try:
        # Resolve the device map path
        if map_selection.startswith("custom:"):
            filename = map_selection.split(":", 1)[1]
            map_path = hass.config.path(CUSTOM_MAP_DIR, filename)
        else:
            map_path = await hass.async_add_executor_job(device_map, map_selection)

    except Exception as e:
        _LOGGER.error("Could not resolve device map '%s': %s", map_selection, e)
        return False

    try:
        if connection_type == CONNECTION_LOCAL:
            addon_url = entry.data[CONF_ADDON_URL]
            lan_key = entry.data[CONF_LAN_KEY]
            device_ip = entry.data[CONF_DEVICE_IP]

            # Parse the addon URL to get host and port
            parsed_url = urlparse(addon_url)
            server_host = parsed_url.hostname
            server_port = parsed_url.port or 80

            # Create the local device instance
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
        elif connection_type == CONNECTION_CLOUD:
            token_file = entry.data[CONF_TOKEN_FILE]
            statistics_token_file = token_file

            def _create_cloud_device():
                client = Client(token_file)
                return client.get_device(dsn, device_map_path=str(map_path))

            device = await hass.async_add_executor_job(_create_cloud_device)

            if device is None:
                raise ConfigEntryNotReady(f"Could not find cloud device with DSN {dsn}")

        else:
            _LOGGER.error("Unknown connection type: %s", connection_type)
            return False
        # Configure the device
        await hass.async_add_executor_job(device.configure)

    except Exception as e:
        raise ConfigEntryNotReady(f"Could not connect to Cremalink device: {e}") from e

    coordinator = CremalinkCoordinator(hass, device)
    await coordinator.async_config_entry_first_refresh()

    statistics_coordinator = None

    # b28 predates the merged core A2 implementation (#225). Keep the HA
    # feature harmless on older core versions while this PR is stacked and
    # waiting for the first upstream release that contains #225.
    core_statistics_supported = hasattr(
        Client,
        "get_ecam610_statistics",
    )

    if (
        statistics_token_file
        and supports_ecam610_statistics(map_selection)
        and core_statistics_supported
    ):
        statistics_coordinator = CremalinkStatisticsCoordinator(
            hass,
            dsn=dsn,
            token_file=statistics_token_file,
        )

        # A complete A2 scan is slow and must not delay normal integration
        # startup or the fast monitor coordinator.
        entry.async_create_background_task(
            hass,
            statistics_coordinator.async_refresh(),
            f"{DOMAIN} initial statistics refresh",
        )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "statistics_coordinator": statistics_coordinator,
        "device": device,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.

    Returns:
        True if unload was successful.
    """
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
