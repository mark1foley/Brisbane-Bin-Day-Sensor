"""Config flow for Brisbane Bin Day Sensor."""
from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ENABLE_KERBSIDE,
    CONF_PROPERTY_NUMBER,
    DEFAULT_BASE_URL,
    DEFAULT_KERBSIDE_TABLE,
    DEFAULT_WASTE_DAYS_TABLE,
    DEFAULT_WASTE_WEEKS_TABLE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


# ── Brisbane Open Data API helpers ──────────────────────────────────────────

def _api_url(base_url: str, table: str) -> str:
    """Build the OpenDataSoft v2.1 records endpoint URL."""
    return f"{base_url}{table}/records"


def _fetch_suburbs(base_url: str, table: str) -> list[str]:
    """Return a sorted list of distinct suburbs from the days table."""
    url = _api_url(base_url, table)
    params = {
        "select": "Suburb",
        "group_by": "Suburb",
        "order_by": "Suburb",
        "limit": 200,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [r["Suburb"] for r in data.get("results", []) if r.get("Suburb")]


def _fetch_streets(base_url: str, table: str, suburb: str) -> list[str]:
    """Return a sorted list of distinct street names for a given suburb."""
    url = _api_url(base_url, table)
    params = {
        "select": "Street_Name",
        "group_by": "Street_Name",
        "where": f'Suburb="{suburb}"',
        "order_by": "Street_Name",
        "limit": 500,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [r["Street_Name"] for r in data.get("results", []) if r.get("Street_Name")]


def _fetch_properties(base_url: str, table: str, suburb: str, street: str) -> list[dict]:
    """Return property records (house_number + property_number) for suburb/street.

    NOTE: The API *returns* the property field as 'property_number' but
    *expects* it as 'property_id' when used as a filter in sensor.py queries.
    """
    url = _api_url(base_url, table)
    params = {
        "select": "house_number,property_number",
        "where": f'Suburb="{suburb}" AND Street_Name="{street}"',
        "order_by": "house_number",
        "limit": 200,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [
        r for r in data.get("results", [])
        if r.get("house_number") and r.get("property_number")
    ]


# ── Config Flow ──────────────────────────────────────────────────────────────

class BneWasteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Brisbane Bin Day Sensor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise flow state shared across steps."""
        self._suburbs: list[str] = []
        self._streets: list[str] = []
        self._properties: list[dict] = []
        self._selected_suburb: str = ""
        self._selected_street: str = ""

    # ── Step 1: Choose suburb ────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1 – select suburb."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_suburb = user_input["suburb"]
            try:
                self._streets = await self.hass.async_add_executor_job(
                    _fetch_streets,
                    DEFAULT_BASE_URL,
                    DEFAULT_WASTE_DAYS_TABLE,
                    self._selected_suburb,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Failed to fetch streets for %s", self._selected_suburb)
                errors["base"] = "cannot_connect"
            else:
                if self._streets:
                    return await self.async_step_street()
                errors["base"] = "no_streets_found"

        # Fetch suburbs on first render
        if not self._suburbs:
            try:
                self._suburbs = await self.hass.async_add_executor_job(
                    _fetch_suburbs,
                    DEFAULT_BASE_URL,
                    DEFAULT_WASTE_DAYS_TABLE,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Failed to fetch suburbs")
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required("suburb"): vol.In(self._suburbs),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    # ── Step 2: Choose street ────────────────────────────────────────────────

    async def async_step_street(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 – select street."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_street = user_input["street_name"]
            try:
                self._properties = await self.hass.async_add_executor_job(
                    _fetch_properties,
                    DEFAULT_BASE_URL,
                    DEFAULT_WASTE_DAYS_TABLE,
                    self._selected_suburb,
                    self._selected_street,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "Failed to fetch properties for %s / %s",
                    self._selected_suburb,
                    self._selected_street,
                )
                errors["base"] = "cannot_connect"
            else:
                if self._properties:
                    return await self.async_step_property()
                errors["base"] = "no_properties_found"

        schema = vol.Schema(
            {
                vol.Required("street_name"): vol.In(self._streets),
            }
        )

        return self.async_show_form(
            step_id="street",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "suburb": self._selected_suburb,
            },
        )

    # ── Step 3: Choose house number ──────────────────────────────────────────

    async def async_step_property(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 3 – select house number and optionally enable kerbside."""
        errors: dict[str, str] = {}

        # Build display map: "42" → property_number value
        # property_number is what the API returns in results;
        # sensor.py passes it to the API as property_id in the query URL.
        house_map: dict[str, str] = {
            str(p["house_number"]): str(p["property_number"])
            for p in self._properties
        }

        if user_input is not None:
            selected_house = user_input["house_number"]
            property_number = house_map.get(selected_house)
            if not property_number:
                errors["base"] = "property_not_found"
            else:
                entry_data = {
                    CONF_PROPERTY_NUMBER: property_number,
                    CONF_ENABLE_KERBSIDE: user_input.get(CONF_ENABLE_KERBSIDE, False),
                    # Silently stored defaults — not shown in UI
                    "base_url": DEFAULT_BASE_URL,
                    "waste_days_table": DEFAULT_WASTE_DAYS_TABLE,
                    "waste_weeks_table": DEFAULT_WASTE_WEEKS_TABLE,
                    "kerbside_table": DEFAULT_KERBSIDE_TABLE,
                    # Friendly address info stored for display purposes
                    "suburb": self._selected_suburb,
                    "street_name": self._selected_street,
                    "house_number": selected_house,
                }
                title = (
                    f"{selected_house} {self._selected_street}, "
                    f"{self._selected_suburb}"
                )
                return self.async_create_entry(title=title, data=entry_data)

        schema = vol.Schema(
            {
                vol.Required("house_number"): vol.In(sorted(house_map.keys())),
                vol.Optional(CONF_ENABLE_KERBSIDE, default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="property",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "suburb": self._selected_suburb,
                "street": self._selected_street,
            },
        )

    # ── Options Flow ─────────────────────────────────────────────────────────

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BneWasteOptionsFlow:
        """Return the options flow handler."""
        return BneWasteOptionsFlow(config_entry)


# ── Options Flow ─────────────────────────────────────────────────────────────

class BneWasteOptionsFlow(config_entries.OptionsFlow):
    """Handle options (reconfigure) for Brisbane Bin Day Sensor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options – only the kerbside toggle is user-configurable."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLE_KERBSIDE,
                    default=self._config_entry.options.get(
                        CONF_ENABLE_KERBSIDE,
                        self._config_entry.data.get(CONF_ENABLE_KERBSIDE, False),
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
