"""Brisbane Waste Collection integration."""
from __future__ import annotations
 
import logging
 
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
 
from .const import DOMAIN
 
_LOGGER = logging.getLogger(__name__)
 
PLATFORMS = ["sensor"]
 
 
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Brisbane Waste Collection from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
 
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
 
    # Listen for option updates and reload
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
 
    _LOGGER.debug("Brisbane Waste Collection entry set up: %s", entry.entry_id)
    return True
 
 
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
 
 
async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
 