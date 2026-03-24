import math
import requests
import logging
import voluptuous as vol

from dateutil.parser import parse
from calendar import weekday
from datetime import datetime, timedelta, date
from time import strptime
from urllib.parse import quote_plus

from homeassistant.components.binary_sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, STATE_ON, STATE_OFF)
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_PROPERTY_NUMBER = "Property Number"
ATTR_SUBURB = "Suburb"
ATTR_STREET = "Street"
ATTR_HOUSE_NUMBER = "House Number"
ATTR_COLLECTION_DAY = "Collection Day"
ATTR_COLLECTION_ZONE = "Collection Zone"
ATTR_NEXT_COLLECTION_DATE = "Next Collection Date"
ATTR_NEXT_KERBSIDE_COLLECTION_DATE = "Next Kerbside Collection Date"
ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE = "Next Kerbside On Footpath Date"
ATTR_KERBSIDE_DUE_IN = "Kerbside Due In"
ATTR_KERBSIDE_ALERT_HOURS = "Kerbside Alert Hours"
ATTR_DUE_IN = "Due In"
ATTR_ALERT_HOURS = "Alert Hours"
ATTR_EXTRA_BIN = "Extra Bin"
ATTR_RECYCLE_WEEK = "Recycle Week"

CONF_BASE_URL = 'base_url'
CONF_WASTE_DAYS_TABLE = 'days_table'
CONF_WASTE_WEEKS_TABLE = 'weeks_table'
CONF_KERBSIDE_TABLE = "kerbside_table"
CONF_PROPERTY_NUMBER = 'property_number'
CONF_ICON = 'icon'
CONF_RECYCLE_ICON = 'recycle_icon'
CONF_KERBSIDE_ICON = "kerbside_icon"
CONF_ALERT_HOURS = 'alert_hours'
CONF_KERBSIDE_ALERT_HOURS = "kerbside_alert_hours"
CONF_HAS_GREEN_BIN = 'green_bin'

DEFAULT_ICON = 'mdi:trash-can'
DEFAULT_RECYCLE_ICON = 'mdi:recycle'
DEFAULT_KERBSIDE_ICON = "mdi:truck-alert"
DEFAULT_ALERT_HOURS = 12
DEFAULT_KERBSIDE_ALERT_HOURS = 168

# Throttle updates to every 5 minutes 
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)

WEEK_DAYS = 7
DAY_HOURS = 24
HOUR_SECONDS = 3600

def is_valid_date(date_str):
    """Validate if a date string can be parsed."""
    if not date_str:
        return False
    try:
        parse(date_str)
        return True
    except (ValueError, TypeError):
        return False

def due_in_hours(time_stamp: datetime, *, label: str | None = None):
    """Get the remaining hours from now until a given datetime object."""
    diff = time_stamp - datetime.now()    
    total_seconds = diff.total_seconds()        
    if total_seconds < 0:        
        return 0  # Past due        
    hours = math.ceil(total_seconds / HOUR_SECONDS)
    _LOGGER.debug("...{0} Due In: Now: {1} Next Collection: {2} Seconds: {3}, Hours: {4}".format(label, datetime.now(), time_stamp, total_seconds, hours))
    return hours

def date_today():
    return datetime.combine(date.today(), datetime.min.time())
    
def week_day():
    return datetime.today().weekday()

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_BASE_URL): cv.string,
    vol.Required(CONF_WASTE_DAYS_TABLE): cv.string,
    vol.Required(CONF_WASTE_WEEKS_TABLE): cv.string,
    vol.Required(CONF_PROPERTY_NUMBER): cv.positive_int,
    vol.Optional(CONF_KERBSIDE_TABLE): cv.string,
    vol.Optional(CONF_ALERT_HOURS, default=DEFAULT_ALERT_HOURS): cv.positive_int,
    vol.Optional(CONF_KERBSIDE_ALERT_HOURS, default=DEFAULT_KERBSIDE_ALERT_HOURS): cv.positive_int,
    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    vol.Optional(CONF_RECYCLE_ICON, default=DEFAULT_RECYCLE_ICON): cv.string,
    vol.Optional(CONF_KERBSIDE_ICON, default=DEFAULT_KERBSIDE_ICON): cv.string,

    vol.Optional(CONF_HAS_GREEN_BIN, default=False): cv.boolean,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    shared_data = BneWasteCollectionData(
        base_url=config[CONF_BASE_URL],
        days_table=config[CONF_WASTE_DAYS_TABLE],
        weeks_table=config[CONF_WASTE_WEEKS_TABLE],
        kerbside_table=config.get(CONF_KERBSIDE_TABLE),  # optional
        property_number=config[CONF_PROPERTY_NUMBER],
        has_green_bin=config[CONF_HAS_GREEN_BIN],
    )

    sensors = [
        BneWasteCollectionSensor(
            shared_data=shared_data,
            name=config[CONF_NAME],
            icon=config[CONF_ICON],
            alert_hours=config[CONF_ALERT_HOURS],
            recycle_week=False,
        ),
        BneWasteCollectionSensor(
            shared_data=shared_data,
            name=f"{config[CONF_NAME]} (Recycle)",
            icon=config[CONF_RECYCLE_ICON],
            alert_hours=config[CONF_ALERT_HOURS],
            recycle_week=True,
        ),
    ]

    if CONF_KERBSIDE_TABLE in config:
        sensors.append(
            BneWasteCollectionKerbsideSensor(
                shared_data,
                f"{config[CONF_NAME]} (Kerbside)",
                config.get(CONF_KERBSIDE_ICON, DEFAULT_KERBSIDE_ICON),
                config.get(CONF_KERBSIDE_ALERT_HOURS, DEFAULT_KERBSIDE_ALERT_HOURS),
            )
        )
    else:
        _LOGGER.info(
            "Kerbside sensor not created: '%s' not configured",
            CONF_KERBSIDE_TABLE,
        )

    add_devices(sensors)

class BneWasteCollectionSensor(Entity):
    def __init__(self, shared_data, name, icon, alert_hours, recycle_week):
        self.data = shared_data
        self._name = name
        self._icon = icon
        self._alert_hours = alert_hours
        self._recycle_week = recycle_week
        self._attrs = {}

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        due = self._attrs.get(ATTR_DUE_IN, -1)
        return STATE_ON if 0 < due <= self._alert_hours else STATE_OFF

    @property
    def extra_state_attributes(self):
        attrs = {
            ATTR_ALERT_HOURS: self._alert_hours,
            ATTR_PROPERTY_NUMBER: self._attrs.get(ATTR_PROPERTY_NUMBER),
            ATTR_SUBURB: self._attrs.get(ATTR_SUBURB),
            ATTR_STREET: self._attrs.get(ATTR_STREET),
            ATTR_HOUSE_NUMBER: self._attrs.get(ATTR_HOUSE_NUMBER),
            ATTR_COLLECTION_DAY: self._attrs.get(ATTR_COLLECTION_DAY),
            ATTR_COLLECTION_ZONE: self._attrs.get(ATTR_COLLECTION_ZONE),
            ATTR_NEXT_COLLECTION_DATE: self._attrs.get(ATTR_NEXT_COLLECTION_DATE),
            ATTR_EXTRA_BIN: self._attrs.get(ATTR_EXTRA_BIN),
            ATTR_DUE_IN: self._attrs.get(ATTR_DUE_IN),
            ATTR_RECYCLE_WEEK: self._attrs.get(ATTR_RECYCLE_WEEK)
        }

        return attrs

    def update(self):
        self.data.update()
        base = dict(self.data.data)

        if ATTR_NEXT_COLLECTION_DATE not in base:
            _LOGGER.warning("%s: skipping update, no data available (API may have failed)", self._name)
            return

        week_rows = base.pop("_week_rows", [])

        base[ATTR_RECYCLE_WEEK] = self._recycle_week

        if self._recycle_week:
            # Recycling sensor represents recycling weeks
            base[ATTR_EXTRA_BIN] = "Yellow/Recycling"
            if not week_rows:
                # Not a recycling week → advance to next week
                base[ATTR_NEXT_COLLECTION_DATE] = (
                    parse(base[ATTR_NEXT_COLLECTION_DATE]) + timedelta(days=7)
                ).isoformat()
        else:
            # Normal bin sensor represents non-recycling weeks
            if week_rows:
                # This week is recycling → advance
                base[ATTR_NEXT_COLLECTION_DATE] = (
                    parse(base[ATTR_NEXT_COLLECTION_DATE]) + timedelta(days=7)
                ).isoformat()

            base[ATTR_EXTRA_BIN] = (
                "Green/Garden" if self.data._has_green_bin else ""
            )

        base[ATTR_DUE_IN] = due_in_hours(
            parse(base[ATTR_NEXT_COLLECTION_DATE]),
            label=self._name,
        )
        self._attrs = base

class BneWasteCollectionKerbsideSensor(Entity):
    def __init__(self, shared_data, name, icon, alert_hours):
        self.data = shared_data
        self._name = name
        self._icon = icon
        self._alert_hours = alert_hours
        self._attrs = {}

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        due = self._attrs.get(ATTR_KERBSIDE_DUE_IN, -1)
        return STATE_ON if 0 < due <= self._alert_hours else STATE_OFF

    @property
    def extra_state_attributes(self):
        return self._attrs

    def update(self):
        self.data.update()
        base = dict(self.data.data)

        if ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE not in base or ATTR_NEXT_KERBSIDE_COLLECTION_DATE not in base:
            _LOGGER.warning("Kerbside data unavailable (missing suburb or no API results)")
            self._attrs = {}
            return

        self._attrs = {
            ATTR_NEXT_KERBSIDE_COLLECTION_DATE: parse(base[ATTR_NEXT_KERBSIDE_COLLECTION_DATE]),
            ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE: parse(base[ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE]),
            ATTR_KERBSIDE_DUE_IN: due_in_hours(
                parse(base[ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE]),
                label=self._name,
            ),
            ATTR_KERBSIDE_ALERT_HOURS: self._alert_hours,
        }

class BneWasteCollectionData:
    """Fetches and caches all BNE waste + kerbside data."""

    _DAY_CACHE = {}       # property_number -> (fetched_at, data)
    _WEEK_CACHE = {}      # (zone, week_start) -> (fetched_at, rows)
    _KERBSIDE_CACHE = {}  # suburb -> (fetched_at, data)

    def __init__(
        self,
        base_url,
        days_table,
        weeks_table,
        kerbside_table,
        property_number,
        has_green_bin,
    ):
        self._base_url = base_url
        self._days_table = days_table
        self._weeks_table = weeks_table
        self._kerbside_table = kerbside_table
        self._property_number = property_number
        self._has_green_bin = has_green_bin
        self.data = {}

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        try:
            self.data = self._get_collection_day()
            self.data["_week_rows"] = self._get_collection_week(self.data)

            if self._kerbside_table:
                self.data.update(self._get_kerbside(self.data))
        except (requests.RequestException, ValueError) as err:
            _LOGGER.error("BneWasteCollection update failed, will retry next cycle: %s", err)

    def _is_cache_valid(self, cached_dt):
        return cached_dt and (datetime.now() - cached_dt) < timedelta(hours=1)

    def _get_collection_day(self):
        cache = self._DAY_CACHE.get(self._property_number)
        now = datetime.now()

        if cache and self._is_cache_valid(cache[0]):
            _LOGGER.debug("Using cached collection day data")
            return dict(cache[1])

        full_url = self._base_url.format(**{
            "dataset_id": self._days_table,
            # NOTE: API expects property_id (inconsistent with dataset)
            "query": quote_plus(f"property_id = {int(self._property_number)}"),
        })

        _LOGGER.debug("Collection day cache empty or expired.  Fetching data using API: %s", full_url)
        rows = self._execute_query(
            full_url,
            context="Collection day",
        )

        if not rows:
            raise ValueError(
                f"Collection day API returned no results for property "
                f"{self._property_number}. Please check that the property "
                f"number is correct."
            )

        row = rows[0]
        collection_day_no = strptime(row["collection_day"], "%A").tm_wday
        today_no = datetime.today().weekday()

        if collection_day_no > today_no:
            next_date = date_today() + timedelta(days=collection_day_no - today_no)
        else:
            next_date = date_today() + timedelta(days=7 + collection_day_no - today_no)

        data = {
            ATTR_PROPERTY_NUMBER: self._property_number,
            ATTR_SUBURB: row["suburb"],
            ATTR_STREET: row["street_name"],
            ATTR_HOUSE_NUMBER: row["house_number"],
            ATTR_COLLECTION_DAY: row["collection_day"],
            ATTR_COLLECTION_ZONE: row["zone"],
            ATTR_NEXT_COLLECTION_DATE: next_date.isoformat(),
        }

        self._DAY_CACHE[self._property_number] = (now, data)
        return dict(data)

    def _get_collection_week(self, base):
        collection_day_no = strptime(
            base[ATTR_COLLECTION_DAY], "%A"
        ).tm_wday
        week_start = (
            parse(base[ATTR_NEXT_COLLECTION_DATE]) -
            timedelta(days=collection_day_no)
        ).date()

        key = (base[ATTR_COLLECTION_ZONE], week_start)
        now = datetime.now()

        cache = self._WEEK_CACHE.get(key)
        if cache and self._is_cache_valid(cache[0]):
            _LOGGER.debug("Using cached collection week data")
            return cache[1]

        full_url = self._base_url.format(**{
            "dataset_id": self._weeks_table,
            "query": quote_plus(
                f"week_starting = date'{week_start:%Y-%m-%d}' "
                f"AND search(zone, '{base[ATTR_COLLECTION_ZONE]}')"
            ),
        })

        _LOGGER.debug("Collection week cache empty or expired.  Fetching data using API: %s", full_url)
        rows = self._execute_query(
            full_url,
            context="Collection week",
        )
        # An empty result is valid — it means this is not a recycling week
        self._WEEK_CACHE[key] = (now, rows)
        return rows

    def _get_kerbside(self, base):
        suburb = base.get(ATTR_SUBURB)
        ### Extra debug for testing - remove later
        _LOGGER.debug("_get_kerbside called, suburb=%s, table=%s", suburb, self._kerbside_table)
        ###
        if not suburb:
            return {}

        key = suburb.upper()
        now = datetime.now()

        cache = self._KERBSIDE_CACHE.get(key)
        if cache and self._is_cache_valid(cache[0]):
            _LOGGER.debug("Using cached kerbside data")
            return dict(cache[1])

        full_url = self._base_url.format(**{
            "dataset_id": self._kerbside_table,
            "query": quote_plus(f"suburb like '{suburb}'"),
        })

        _LOGGER.debug("Kerbside cache empty or expired.  Fetching data using API: %s", full_url)
        rows = self._execute_query(
            full_url,
            context="Kerbside collection",
        )
        row = rows[0]
        data = {
            ATTR_NEXT_KERBSIDE_COLLECTION_DATE: parse(
                row["date_of_collection"]
            ).isoformat(),
            ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE: parse(
                row["items_out_on_footpath"]
            ).isoformat(),
        }

        self._KERBSIDE_CACHE[key] = (now, data)
        return dict(data)

    def _execute_query(self, full_url, *, context):
        try:
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as err:
            _LOGGER.error("%s API request failed: %s", context, err)
            raise
        except ValueError as err:
            _LOGGER.error("%s API returned invalid JSON: %s", context, err)
            raise

        results = payload.get("results", [])

        # Handle logical API error embedded in row
        if results:
            first_row = results[0]
            if isinstance(first_row, dict) and "error_code" in first_row:
                raise ValueError(
                    f"{context} API error "
                    f"{first_row.get('error_code')}: "
                    f"{first_row.get('error_message')}"
                )

        return results