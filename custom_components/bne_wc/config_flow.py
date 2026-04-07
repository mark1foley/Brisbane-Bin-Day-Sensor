"""Config flow for Brisbane Bin Day Sensor."""
from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ALERT_HOURS,
    CONF_COLLECTION_TIME,
    CONF_ENABLE_KERBSIDE,
    CONF_HAS_GREEN_BIN,
    CONF_ICON,
    CONF_KERBSIDE_ALERT_HOURS,
    CONF_KERBSIDE_ICON,
    CONF_PROPERTY_NUMBER,
    CONF_RECYCLE_ICON,
    DEFAULT_BASE_URL,
    DEFAULT_WASTE_DAYS_TABLE,
    DEFAULT_WASTE_WEEKS_TABLE,
    DEFAULT_KERBSIDE_TABLE,
    DEFAULT_LIMIT,
    DEFAULT_ICON,
    DEFAULT_RECYCLE_ICON,
    DEFAULT_KERBSIDE_ICON,
    DEFAULT_ALERT_HOURS,
    DEFAULT_KERBSIDE_ALERT_HOURS,
    DEFAULT_COLLECTION_TIME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# ── Brisbane Open Data API helpers ──────────────────────────────────────────

def _fetch_suburbs(table: str) -> list[str]:
    """Return a sorted list of distinct suburbs from the days table."""
    base_url = DEFAULT_BASE_URL.format(
        dataset_id=table,
        query="suburb IS NOT NULL",
        limit=200,                    # Higher limit — ~150 suburbs exist
    )
    url = f"{base_url}&select=suburb&group_by=suburb&order_by=suburb"

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [r["suburb"] for r in data.get("results", []) if r.get("suburb")]


def _fetch_streets(table: str, suburb: str) -> list[str]:
    """Return a sorted list of distinct street names for a given suburb."""
    base_url = DEFAULT_BASE_URL.format(
        dataset_id=table,
        query=f'suburb="{suburb}"',
        limit=DEFAULT_LIMIT,
    )
    url = f"{base_url}&select=street_name&group_by=street_name&order_by=street_name"

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [r["street_name"] for r in data.get("results", []) if r.get("street_name")]


def _fetch_properties(table: str, suburb: str, street: str) -> list[dict]:
    """Return property records (house_number + property_id) for suburb/street."""
    base_url = DEFAULT_BASE_URL.format(
        dataset_id=table,
        query=f'suburb="{suburb}" AND street_name="{street}"',
        limit=DEFAULT_LIMIT,
    )
    url = f"{base_url}&select=house_number,property_id&order_by=house_number"
 
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [
            r for r in data.get("results", [])
            if r.get("house_number") and r.get("property_id")
        ]
    except Exception as e:
        _LOGGER.exception("Failed to fetch properties: %s", e)
        raise

def _options_schema(defaults: dict) -> vol.Schema:
    """Build the shared schema used by both Step 3 and the Options Flow."""
    return vol.Schema(
        {
            vol.Optional(CONF_ICON, default=defaults.get(CONF_ICON, DEFAULT_ICON)): selector.IconSelector(),
            vol.Optional(CONF_RECYCLE_ICON, default=defaults.get(CONF_RECYCLE_ICON, DEFAULT_RECYCLE_ICON)): selector.IconSelector(),
            vol.Optional(CONF_ALERT_HOURS, default=defaults.get(CONF_ALERT_HOURS, DEFAULT_ALERT_HOURS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=168, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_COLLECTION_TIME, default=defaults.get(CONF_COLLECTION_TIME, DEFAULT_COLLECTION_TIME)): selector.TimeSelector(),
            vol.Optional(CONF_HAS_GREEN_BIN, default=defaults.get(CONF_HAS_GREEN_BIN, False)): selector.BooleanSelector(),
            vol.Optional(CONF_ENABLE_KERBSIDE, default=defaults.get(CONF_ENABLE_KERBSIDE, False)): selector.BooleanSelector(),
            vol.Optional(CONF_KERBSIDE_ICON, default=defaults.get(CONF_KERBSIDE_ICON, DEFAULT_KERBSIDE_ICON)): selector.IconSelector(),
            vol.Optional(CONF_KERBSIDE_ALERT_HOURS, default=defaults.get(CONF_KERBSIDE_ALERT_HOURS, DEFAULT_KERBSIDE_ALERT_HOURS)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=168, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
    )

def _strip_seconds(time_str: str) -> str:
    """Ensure time value is stored as HH:MM, stripping seconds if present."""
    return time_str[:5] if len(time_str) > 5 else time_str

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
        self._config_entry: config_entries.ConfigEntry | None = None  # Initialize _config_entry

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 1 – select suburb."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_suburb = user_input["suburb"]
            try:
                self._streets = await self.hass.async_add_executor_job(_fetch_streets, DEFAULT_WASTE_DAYS_TABLE, self._selected_suburb)
            except Exception:
                _LOGGER.exception("Failed to fetch streets for %s", self._selected_suburb)
                errors["base"] = "cannot_connect"
            else:
                if self._streets:
                    return await self.async_step_street()
                errors["base"] = "no_streets_found"

        if not self._suburbs:
            try:
                self._suburbs = await self.hass.async_add_executor_job(_fetch_suburbs, DEFAULT_WASTE_DAYS_TABLE)
            except Exception:
                _LOGGER.exception("Failed to fetch suburbs")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("suburb"): vol.In(self._suburbs)}
            ),
            errors=errors,
        )

    async def async_step_street(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 2 – select street."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._selected_street = user_input["street_name"]
            try:
                self._properties = await self.hass.async_add_executor_job(_fetch_properties, DEFAULT_WASTE_DAYS_TABLE, self._selected_suburb, self._selected_street)
            except Exception:
                _LOGGER.exception("Failed to fetch properties for %s / %s", self._selected_suburb, self._selected_street)
                errors["base"] = "cannot_connect"
            else:
                if self._properties:
                    return await self.async_step_property()
                errors["base"] = "no_properties_found"

        return self.async_show_form(
            step_id="street",
            data_schema=vol.Schema(
                {vol.Required("street_name"): vol.In(self._streets)}
            ),
            errors=errors,
            description_placeholders={"suburb": self._selected_suburb},
        )

    async def async_step_property(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Step 3 – select house number and configure all sensor options."""
        errors: dict[str, str] = {}

        house_map: dict[str, str] = {
            str(p["house_number"]): str(p["property_id"])
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
                    CONF_ICON: user_input.get(CONF_ICON, DEFAULT_ICON),
                    CONF_RECYCLE_ICON: user_input.get(CONF_RECYCLE_ICON, DEFAULT_RECYCLE_ICON),
                    CONF_ALERT_HOURS: user_input.get(CONF_ALERT_HOURS, DEFAULT_ALERT_HOURS),
                    CONF_COLLECTION_TIME: _strip_seconds(user_input.get(CONF_COLLECTION_TIME, DEFAULT_COLLECTION_TIME)),
                    CONF_HAS_GREEN_BIN: user_input.get(CONF_HAS_GREEN_BIN, False),
                    CONF_KERBSIDE_ICON: user_input.get(CONF_KERBSIDE_ICON, DEFAULT_KERBSIDE_ICON),
                    CONF_KERBSIDE_ALERT_HOURS: user_input.get(CONF_KERBSIDE_ALERT_HOURS, DEFAULT_KERBSIDE_ALERT_HOURS),
                    "waste_days_table": DEFAULT_WASTE_DAYS_TABLE,
                    "waste_weeks_table": DEFAULT_WASTE_WEEKS_TABLE,
                    "kerbside_table": DEFAULT_KERBSIDE_TABLE,
                    "suburb": self._selected_suburb,
                    "street_name": self._selected_street,
                    "house_number": selected_house,
                }
                title = f"{selected_house} {self._selected_street}, {self._selected_suburb}"
                return self.async_create_entry(title=title, data=entry_data)

        # Use defaults for first run
        defaults = {
            CONF_ICON: DEFAULT_ICON,
            CONF_RECYCLE_ICON: DEFAULT_RECYCLE_ICON,
            CONF_ALERT_HOURS: DEFAULT_ALERT_HOURS,
            CONF_COLLECTION_TIME: DEFAULT_COLLECTION_TIME,
            CONF_HAS_GREEN_BIN: False,
            CONF_ENABLE_KERBSIDE: False,
        }

        # If this is a subsequent run, populate with current values
        if self._config_entry is not None:
            defaults.update(self._config_entry.data)

        house_schema = vol.Schema(
            {
                vol.Required("house_number"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted(house_map.keys()),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        ).extend(_options_schema(defaults).schema)

        return self.async_show_form(
            step_id="property",
            data_schema=house_schema,
            errors=errors,
            description_placeholders={
                "suburb": self._selected_suburb,
                "street": self._selected_street,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> BneWasteOptionsFlow:
        """Return the options flow handler."""
        return BneWasteOptionsFlow(config_entry)

class BneWasteOptionsFlow(config_entries.OptionsFlow):
    """Handle options (reconfigure) for Brisbane Bin Day Sensor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage all sensor options on a single page."""
        if user_input is not None:
            if CONF_COLLECTION_TIME in user_input:
                user_input[CONF_COLLECTION_TIME] = _strip_seconds(user_input[CONF_COLLECTION_TIME]) 
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self._config_entry.data, **self._config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(defaults),
        )
