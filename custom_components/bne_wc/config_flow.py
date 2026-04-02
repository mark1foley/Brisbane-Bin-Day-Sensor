"""Config flow for Brisbane Waste Collection integration."""
from __future__ import annotations
 
import logging
from typing import Any
 
import voluptuous as vol
import requests
 
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from urllib.parse import quote_plus
 
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_BASE_URL,
    DEFAULT_ICON,
    DEFAULT_RECYCLE_ICON,
    DEFAULT_KERBSIDE_ICON,
    DEFAULT_ALERT_HOURS,
    DEFAULT_KERBSIDE_ALERT_HOURS,
    DEFAULT_COLLECTION_TIME,
    CONF_BASE_URL,
    CONF_WASTE_DAYS_TABLE,
    CONF_WASTE_WEEKS_TABLE,
    CONF_KERBSIDE_TABLE,
    CONF_PROPERTY_NUMBER,
    CONF_ICON,
    CONF_RECYCLE_ICON,
    CONF_KERBSIDE_ICON,
    CONF_ALERT_HOURS,
    CONF_KERBSIDE_ALERT_HOURS,
    CONF_HAS_GREEN_BIN,
    CONF_COLLECTION_TIME,
)
 
_LOGGER = logging.getLogger(__name__)
 
 
def _validate_property_number(
    hass: HomeAssistant,
    base_url: str,
    days_table: str,
    property_number: int,
) -> None:
    """
    Call the collection-day API synchronously.
    Raises HomeAssistantError on failure.
    """
    full_url = base_url.format(
        dataset_id=days_table,
        query=quote_plus(f"property_id = {int(property_number)}"),
    )
    try:
        response = requests.get(full_url, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as err:
        raise CannotConnect(str(err)) from err
    except ValueError as err:
        raise InvalidResponse(str(err)) from err
 
    results = payload.get("results", [])
    if not results:
        raise InvalidPropertyNumber(
            f"No data returned for property number {property_number}."
        )
 
    # Check for API-level errors embedded in the result
    first = results[0]
    if isinstance(first, dict) and "error_code" in first:
        raise InvalidResponse(
            f"API error {first.get('error_code')}: {first.get('error_message')}"
        )
 
 
# ── Step 1: User form schema ─────────────────────────────────────────────────
 
STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Optional("name", default=DEFAULT_NAME): str,
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Required(CONF_WASTE_DAYS_TABLE): str,
        vol.Required(CONF_WASTE_WEEKS_TABLE): str,
        vol.Required(CONF_PROPERTY_NUMBER): vol.Coerce(int),
        vol.Optional(CONF_KERBSIDE_TABLE, default=""): str,
        vol.Optional(CONF_HAS_GREEN_BIN, default=False): bool,
        vol.Optional(CONF_COLLECTION_TIME, default=DEFAULT_COLLECTION_TIME): str,
        vol.Optional(CONF_ALERT_HOURS, default=DEFAULT_ALERT_HOURS): vol.Coerce(int),
        vol.Optional(
            CONF_KERBSIDE_ALERT_HOURS, default=DEFAULT_KERBSIDE_ALERT_HOURS
        ): vol.Coerce(int),
    }
)
 
# ── Options form schema ──────────────────────────────────────────────────────
 
def _options_schema(current: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(
                CONF_HAS_GREEN_BIN,
                default=current.get(CONF_HAS_GREEN_BIN, False),
            ): bool,
            vol.Optional(
                CONF_COLLECTION_TIME,
                default=current.get(CONF_COLLECTION_TIME, DEFAULT_COLLECTION_TIME),
            ): str,
            vol.Optional(
                CONF_ALERT_HOURS,
                default=current.get(CONF_ALERT_HOURS, DEFAULT_ALERT_HOURS),
            ): vol.Coerce(int),
            vol.Optional(
                CONF_KERBSIDE_ALERT_HOURS,
                default=current.get(
                    CONF_KERBSIDE_ALERT_HOURS, DEFAULT_KERBSIDE_ALERT_HOURS
                ),
            ): vol.Coerce(int),
            vol.Optional(
                CONF_ICON,
                default=current.get(CONF_ICON, DEFAULT_ICON),
            ): str,
            vol.Optional(
                CONF_RECYCLE_ICON,
                default=current.get(CONF_RECYCLE_ICON, DEFAULT_RECYCLE_ICON),
            ): str,
            vol.Optional(
                CONF_KERBSIDE_ICON,
                default=current.get(CONF_KERBSIDE_ICON, DEFAULT_KERBSIDE_ICON),
            ): str,
        }
    )
 
 
# ── Config Flow ───────────────────────────────────────────────────────────────
 
class BneWasteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Brisbane Waste Collection."""
 
    VERSION = 1
 
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user setup step."""
        errors: dict[str, str] = {}
 
        if user_input is not None:
            # Strip empty kerbside table
            if not user_input.get(CONF_KERBSIDE_TABLE, "").strip():
                user_input[CONF_KERBSIDE_TABLE] = None
 
            # Apply defaults for icons (not shown in initial step)
            user_input.setdefault(CONF_ICON, DEFAULT_ICON)
            user_input.setdefault(CONF_RECYCLE_ICON, DEFAULT_RECYCLE_ICON)
            user_input.setdefault(CONF_KERBSIDE_ICON, DEFAULT_KERBSIDE_ICON)
 
            try:
                await self.hass.async_add_executor_job(
                    _validate_property_number,
                    self.hass,
                    user_input[CONF_BASE_URL],
                    user_input[CONF_WASTE_DAYS_TABLE],
                    user_input[CONF_PROPERTY_NUMBER],
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidPropertyNumber:
                errors[CONF_PROPERTY_NUMBER] = "invalid_property_number"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during config validation")
                errors["base"] = "unknown"
            else:
                title = user_input.get("name", DEFAULT_NAME)
                return self.async_create_entry(title=title, data=user_input)
 
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )
 
    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BneWasteOptionsFlow:
        """Return the options flow handler."""
        return BneWasteOptionsFlow(config_entry)
 
 
# ── Options Flow ──────────────────────────────────────────────────────────────
 
class BneWasteOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Brisbane Waste Collection."""
 
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self._config_entry = config_entry
 
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
 
        current = {**self._config_entry.data, **self._config_entry.options}
 
        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(current),
        )
 
 
# ── Custom exceptions ─────────────────────────────────────────────────────────
 
class CannotConnect(HomeAssistantError):
    """Raised when we cannot reach the API."""
 
 
class InvalidPropertyNumber(HomeAssistantError):
    """Raised when the API returns no results for the property number."""
 
 
class InvalidResponse(HomeAssistantError):
    """Raised when the API returns an unexpected or error response."""
 