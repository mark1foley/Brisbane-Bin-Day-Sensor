import math
import requests
import logging

from dateutil.parser import parse
from datetime import datetime, timedelta
from time import strptime
from urllib.parse import quote_plus

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    ATTR_PROPERTY_NUMBER, ATTR_SUBURB, ATTR_STREET, ATTR_HOUSE_NUMBER,
    ATTR_COLLECTION_DAY, ATTR_COLLECTION_ZONE, ATTR_NEXT_COLLECTION_DATE,
    ATTR_NEXT_KERBSIDE_COLLECTION_DATE, ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE,
    ATTR_KERBSIDE_DUE_IN, ATTR_KERBSIDE_ALERT_HOURS, ATTR_DUE_IN,
    ATTR_ALERT_HOURS, ATTR_EXTRA_BIN, ATTR_RECYCLE_WEEK, ATTR_LAST_UPDATE_FAILED,
    CONF_WASTE_DAYS_TABLE, CONF_WASTE_WEEKS_TABLE,
    CONF_KERBSIDE_TABLE, CONF_PROPERTY_NUMBER, CONF_ICON, CONF_RECYCLE_ICON,
    CONF_KERBSIDE_ICON, CONF_ALERT_HOURS, CONF_KERBSIDE_ALERT_HOURS,
    CONF_HAS_GREEN_BIN, CONF_COLLECTION_TIME,
    DEFAULT_BASE_URL, DEFAULT_LIMIT,
    DEFAULT_ICON, DEFAULT_RECYCLE_ICON, DEFAULT_KERBSIDE_ICON,
    DEFAULT_ALERT_HOURS, DEFAULT_KERBSIDE_ALERT_HOURS,
    HOUR_SECONDS, CONF_ENABLE_KERBSIDE,
)

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)

WEEK_DAYS = 7
DAY_HOURS = 24


def due_in_hours(time_stamp: datetime, *, label: str | None = None):
    """Get the remaining hours from now until a given datetime object."""
    diff = time_stamp - dt_util.now()
    total_seconds = diff.total_seconds()
    if total_seconds < 0:
        return 0
    hours = math.ceil(total_seconds / HOUR_SECONDS)
    _LOGGER.debug(
        "...%s Due In: Now: %s Next Collection: %s Seconds: %s, Hours: %s",
        label, dt_util.now(), time_stamp, total_seconds, hours,
    )
    return hours


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brisbane Waste Collection sensors from a config entry."""
    config = {**entry.data, **entry.options}

    shared_data = BneWasteCollectionData(
        days_table=config[CONF_WASTE_DAYS_TABLE],
        weeks_table=config[CONF_WASTE_WEEKS_TABLE],
        kerbside_table=config.get(CONF_KERBSIDE_TABLE),
        property_number=config[CONF_PROPERTY_NUMBER],
        has_green_bin=config.get(CONF_HAS_GREEN_BIN, False),
        collection_time=config.get(CONF_COLLECTION_TIME, "05:00"),
    )

    name = config.get("name", "Brisbane Bin Day")

    sensors = [
        BneWasteCollectionSensor(
            shared_data=shared_data,
            name=name,
            icon=config.get(CONF_ICON, DEFAULT_ICON),
            alert_hours=config.get(CONF_ALERT_HOURS, DEFAULT_ALE*
