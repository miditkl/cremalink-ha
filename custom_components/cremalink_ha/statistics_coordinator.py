"""Statistics update coordinator for Cremalink."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from cremalink import Client
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _snapshot_timestamp() -> str:
    """Return the UTC timestamp of a genuinely successful A2 snapshot."""
    return datetime.now(timezone.utc).isoformat()


# A complete ECAM610 A2 table currently takes about 15 seconds to read.
# Lifetime counters do not need the fast 1/30-second monitor polling.
STATISTICS_UPDATE_INTERVAL = timedelta(minutes=10)


class CremalinkStatisticsCoordinator(DataUpdateCoordinator[dict]):
    """Fetch slow-changing machine statistics independently of monitoring."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        dsn: str,
        token_file: str,
    ) -> None:
        """Initialize the statistics coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_statistics",
            update_interval=STATISTICS_UPDATE_INTERVAL,
        )

        self.dsn = dsn
        self.token_file = token_file
        self.refresh_in_progress = False
        self.refresh_started_at = None
        self._refresh_started_monotonic = None
        self.last_refresh_duration_seconds = None
        self.a2_progress = None

    @property
    def refresh_running_for_seconds(self):
        """Return elapsed seconds for the current manual refresh."""
        if (
            not self.refresh_in_progress
            or self._refresh_started_monotonic is None
        ):
            return None

        return round(
            time.monotonic() - self._refresh_started_monotonic,
            1,
        )

    def _apply_a2_progress(self, progress: dict) -> None:
        """Apply one A2 progress event on the Home Assistant loop."""
        self.a2_progress = dict(progress)
        self.async_update_listeners()

    def _publish_a2_progress(self, progress: dict) -> None:
        """Publish executor-thread A2 progress safely to Home Assistant."""
        loop = getattr(self.hass, "loop", None)

        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(
                self._apply_a2_progress,
                dict(progress),
            )
            return

        # Unit-test/minimal-HASS fallback.
        self._apply_a2_progress(progress)

    async def async_force_refresh(self) -> None:
        """Run one complete manual A2 statistics refresh."""
        if self.refresh_in_progress:
            return

        self.refresh_in_progress = True
        self.refresh_started_at = datetime.now(
            timezone.utc
        ).isoformat()
        self._refresh_started_monotonic = time.monotonic()
        self.last_refresh_duration_seconds = None
        self.a2_progress = None
        self.async_update_listeners()

        try:
            await self.async_refresh()
        finally:
            if self._refresh_started_monotonic is not None:
                self.last_refresh_duration_seconds = round(
                    time.monotonic()
                    - self._refresh_started_monotonic,
                    1,
                )

            self.refresh_in_progress = False
            self._refresh_started_monotonic = None
            self.async_update_listeners()

    async def _async_update_data(self) -> dict:
        """Fetch a complete live ECAM610 statistics snapshot."""

        def _read_statistics() -> dict:
            client = Client(self.token_file)

            snapshot = client.get_ecam610_statistics(
                self.dsn,
                progress_callback=self._publish_a2_progress,
            )

            # Service properties are auxiliary diagnostics used to
            # cross-check still-unidentified A2 counters. Failure to read
            # them must not invalidate an otherwise successful A2 snapshot.
            service_reader = getattr(
                client,
                "get_ecam_service_properties",
                None,
            )

            if callable(service_reader):
                try:
                    service_properties = service_reader(self.dsn)
                except Exception as err:
                    _LOGGER.debug(
                        "Could not read ECAM service properties: %s",
                        err,
                    )
                    service_properties = {}
            else:
                service_properties = {}

            snapshot = dict(snapshot)
            snapshot["service_properties"] = service_properties

            return snapshot

        try:
            snapshot = await self.hass.async_add_executor_job(
                _read_statistics
            )

            # Stamp only genuinely successful complete A2 reads.
            # A retained snapshot after a timeout keeps its old timestamp.
            snapshot["snapshot_fetched_at"] = _snapshot_timestamp()
            return snapshot
        except TimeoutError as err:
            # Lifetime statistics change slowly. If a transient A2 timeout
            # occurs after at least one successful read, keep the last
            # snapshot instead of making all statistics unavailable.
            if isinstance(self.data, dict) and self.data:
                _LOGGER.debug(
                    "A2 statistics refresh timed out; retaining previous "
                    "snapshot: %s",
                    err,
                )
                return self.data

            raise UpdateFailed(
                f"Error reading ECAM statistics: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Error reading ECAM statistics: {err}"
            ) from err
