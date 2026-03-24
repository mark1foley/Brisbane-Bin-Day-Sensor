"""
Script for quicker and easier testing of BNE_WC outside of Home Assistant.
Usage: test.py -f <yaml file> -d INFO|DEBUG { -l <outfile log file> }

<yaml file> contains the sensor configuration from HA.
<output file> is a text file for output
"""

import math
import requests
import logging
import argparse
import yaml

from dateutil.parser import parse
from calendar import weekday
from schema import Schema, SchemaError, Optional
from datetime import datetime, timedelta, date
from time import strptime
from urllib.parse import quote_plus

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
ATTR_DUE_IN = "Due In"
ATTR_KERBSIDE_DUE_IN = "Kerbside Due In"
ATTR_ALERT_HOURS = "Alert Hours"
ATTR_KERBSIDE_ALERT_HOURS = "Kerbside Alert Hours"
ATTR_EXTRA_BIN = "Extra Bin"
ATTR_RECYCLE_WEEK = "Recycle Week"

CONF_NAME = 'name'
CONF_BASE_URL = 'base_url'
CONF_WASTE_DAYS_TABLE = 'days_table'
CONF_WASTE_WEEKS_TABLE = 'weeks_table'
CONF_KERBSIDE_TABLE = 'kerbside_table'
CONF_PROPERTY_NUMBER = 'property_number'
CONF_ICON = 'icon'
CONF_RECYCLE_ICON = 'recycle_icon'
CONF_KERBSIDE_ICON = 'kerbside_icon'

CONF_ALERT_HOURS = 'alert_hours'
CONF_KERBSIDE_ALERT_HOURS = 'kerbside_alert_hours'
CONF_GREEN_BIN = 'green_bin'

DEFAULT_ICON = 'mdi:trash-can'
DEFAULT_RECYCLE_ICON = 'mdi:recycle'
DEFAULT_KERBSIDE_ICON = 'mdi:sofa'
DEFAULT_ALERT_HOURS = 12
DEFAULT_KERBSIDE_ALERT_HOURS = 168

WEEK_DAYS = 7
DAY_HOURS = 24
HOUR_SECONDS = 3600

def is_valid_date(date):
    if date:
        try:
            parse(date)
            return True
        except:
            return False
    return False

def due_in_hours(time_stamp: datetime):
    """Get the remaining hours from now until a given datetime object."""
    diff = time_stamp - datetime.now()
    _LOGGER.debug("...Due In: Now: {0} Next Collection: {1} Seconds: {2}, Hours: {3}".format(datetime.now(), time_stamp, diff.seconds, math.ceil(diff.seconds/HOUR_SECONDS)))
    return math.ceil(diff.seconds/HOUR_SECONDS) + (diff.days*DAY_HOURS)

def date_today():
    return datetime.combine(date.today(), datetime.min.time())
    
def week_day():
    return datetime.today().weekday()

PLATFORM_SCHEMA = Schema({
    CONF_NAME: str,
    CONF_BASE_URL: str,
    CONF_WASTE_DAYS_TABLE: str,
    CONF_WASTE_WEEKS_TABLE: str,
    CONF_KERBSIDE_TABLE: str,
    CONF_PROPERTY_NUMBER: str,
    Optional(CONF_ALERT_HOURS, default=DEFAULT_ALERT_HOURS): int,
    Optional(CONF_KERBSIDE_ALERT_HOURS, default=DEFAULT_KERBSIDE_ALERT_HOURS): int,
    Optional(CONF_ICON, default=DEFAULT_ICON): str,
    Optional(CONF_RECYCLE_ICON, default=DEFAULT_RECYCLE_ICON): str,
    Optional(CONF_KERBSIDE_ICON, default=DEFAULT_KERBSIDE_ICON): str,
    Optional(CONF_GREEN_BIN, default=False): bool
})

class BneWasteCollectionData:
    """Fetches and caches BNE waste collection data once per run."""

    _KERBSIDE_CACHE = {}

    def __init__(self, base_url, days_table, weeks_table, kerbside_table, property_number):
        self._base_url = base_url
        self._days_table = days_table
        self._weeks_table = weeks_table
        self._kerbside_table = kerbside_table
        self._property_number = property_number
        self.data = {}

    def update(self):
        """Fetch all data once and cache it."""
        try:
            self.data = self._get_collection_day()
            self.data["_week_rows"] = self._get_collection_week(self.data)
            self.data.update(self._get_kerbside(self.data))
        except requests.RequestException as e:
            _LOGGER.error("Network error during update: %s", e)
            raise
        except ValueError as e:
            _LOGGER.error("Data error during update: %s", e)
            raise

    def _get_collection_day(self):
        full_url = self._base_url.format(
            dataset_id=self._days_table,
            query=quote_plus(f"property_id = {int(self._property_number)}")
        )

        _LOGGER.info("Fetching collection day: %s", full_url)
        response = requests.get(full_url)
        response.raise_for_status()

        results = response.json().get("results", [])
        if not results:
            raise ValueError("Collection day dataset returned no rows")

        row = results[0]
        collection_day_no = strptime(row["collection_day"], "%A").tm_wday
        current_day_no = datetime.today().weekday()
        next_date = date_today() + timedelta(days=(collection_day_no - current_day_no + (7 if collection_day_no <= current_day_no else 0)))

        return {
            ATTR_PROPERTY_NUMBER: self._property_number,
            ATTR_SUBURB: row["suburb"],
            ATTR_STREET: row["street_name"],
            ATTR_HOUSE_NUMBER: row["house_number"],
            ATTR_COLLECTION_DAY: row["collection_day"],
            ATTR_COLLECTION_ZONE: row["zone"],
            ATTR_NEXT_COLLECTION_DATE: next_date.isoformat(),
        }

    def _get_collection_week(self, base):
        collection_day_no = strptime(base[ATTR_COLLECTION_DAY], "%A").tm_wday
        week_start = parse(base[ATTR_NEXT_COLLECTION_DATE]) - timedelta(days=collection_day_no)

        full_url = self._base_url.format(
            dataset_id=self._weeks_table,
            query=quote_plus(f"week_starting = date'{week_start:%Y-%m-%d}' AND search(zone, '{base[ATTR_COLLECTION_ZONE]}')")
        )

        _LOGGER.info("Fetching collection week: %s", full_url)
        response = requests.get(full_url)
        response.raise_for_status()
        return response.json().get("results", [])

    def _get_kerbside(self, base):
        suburb = base[ATTR_SUBURB]
        if suburb in self._KERBSIDE_CACHE:
            _LOGGER.debug("Using cached kerbside data for suburb: %s", suburb)
            return self._KERBSIDE_CACHE[suburb]

        full_url = self._base_url.format(
            dataset_id=self._kerbside_table,
            query=quote_plus(f"suburb like '{suburb}'")
        )

        _LOGGER.info("Fetching kerbside collection: %s", full_url)
        response = requests.get(full_url)
        response.raise_for_status()
        results = response.json().get("results", [])

        data = {}
        if results:
            row = results[0]
            data[ATTR_NEXT_KERBSIDE_COLLECTION_DATE] = parse(row["date_of_collection"]).isoformat()
            data[ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE] = parse(row["items_out_on_footpath"]).isoformat()

        self._KERBSIDE_CACHE[suburb] = data
        return data


class BneWasteCollectionSensor:
    """Sensor for normal and recycle week waste collection."""

    def __init__(self, shared_data, name, icon, alert_hours, recycle_week=False, green_bin=False):
        self.data = shared_data
        self._name = name
        self._icon = icon
        self._alert_hours = alert_hours
        self._recycle_week = recycle_week
        self._green_bin = green_bin
        self.info = {}

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        due = self.info.get(ATTR_DUE_IN, -1)
        return STATE_ON if 0 < due <= self._alert_hours else STATE_OFF

    @property
    def extra_state_attributes(self):
        # Include the Alert Hours attribute
        return {
            ATTR_PROPERTY_NUMBER: self.info.get(ATTR_PROPERTY_NUMBER),
            ATTR_SUBURB: self.info.get(ATTR_SUBURB),
            ATTR_STREET: self.info.get(ATTR_STREET),
            ATTR_HOUSE_NUMBER: self.info.get(ATTR_HOUSE_NUMBER),
            ATTR_COLLECTION_DAY: self.info.get(ATTR_COLLECTION_DAY),
            ATTR_COLLECTION_ZONE: self.info.get(ATTR_COLLECTION_ZONE),
            ATTR_NEXT_COLLECTION_DATE: self.info.get(ATTR_NEXT_COLLECTION_DATE),
            ATTR_DUE_IN: self.info.get(ATTR_DUE_IN),
            ATTR_EXTRA_BIN: self.info.get(ATTR_EXTRA_BIN),
            ATTR_RECYCLE_WEEK: self.info.get(ATTR_RECYCLE_WEEK),
            ATTR_ALERT_HOURS: self._alert_hours,  # Added back
        }

    def update(self):
        """Compute extra bin and due dates from cached shared data."""
        try:
            base = dict(self.data.data)
            week_rows = base.pop("_week_rows", [])

            if self._recycle_week:
                self.info[ATTR_EXTRA_BIN] = "Yellow/Recycling"
                if not week_rows:
                    base[ATTR_NEXT_COLLECTION_DATE] = (parse(base[ATTR_NEXT_COLLECTION_DATE]) + timedelta(days=7)).isoformat()
            else:
                self.info[ATTR_EXTRA_BIN] = "Green/Garden" if self._green_bin else ""
                if week_rows:
                    base[ATTR_NEXT_COLLECTION_DATE] = (parse(base[ATTR_NEXT_COLLECTION_DATE]) + timedelta(days=7)).isoformat()

            base[ATTR_DUE_IN] = due_in_hours(parse(base[ATTR_NEXT_COLLECTION_DATE]))
            self.info.update(base)
        except Exception as e:
            _LOGGER.error("Error updating sensor '%s': %s", self._name, e)
            self.info = {}


class BneWasteCollectionKerbsideSensor:
    """Sensor for kerbside collection dates only."""

    def __init__(self, shared_data, name, icon, kerbside_alert_hours):
        self.data = shared_data
        self._name = name
        self._icon = icon
        self._kerbside_alert_hours = kerbside_alert_hours
        self.info = {}

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def state(self):
        due = self.info.get(ATTR_KERBSIDE_DUE_IN, -1)
        return STATE_ON if 0 < due <= self._kerbside_alert_hours else STATE_OFF

    @property
    def extra_state_attributes(self):
        # Include the Kerbside Alert Hours attribute
        return {
            ATTR_NEXT_KERBSIDE_COLLECTION_DATE: self.info.get(ATTR_NEXT_KERBSIDE_COLLECTION_DATE),
            ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE: self.info.get(ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE),
            ATTR_KERBSIDE_DUE_IN: self.info.get(ATTR_KERBSIDE_DUE_IN),
            ATTR_KERBSIDE_ALERT_HOURS: self._kerbside_alert_hours,  # Added back
        }

    def update(self):
        """Update kerbside collection dates from shared data."""
        try:
            base = dict(self.data.data)
            self.info = {}

            next_collection = base.get(ATTR_NEXT_KERBSIDE_COLLECTION_DATE)
            on_footpath = base.get(ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE)

            self.info[ATTR_NEXT_KERBSIDE_COLLECTION_DATE] = next_collection
            self.info[ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE] = on_footpath
            self.info[ATTR_KERBSIDE_DUE_IN] = due_in_hours(parse(on_footpath)) if is_valid_date(on_footpath) else -1

        except Exception as e:
            _LOGGER.error("Error updating kerbside sensor '%s': %s", self._name, e)
            self.info = {}
#
#
#
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test script for BNE Waste Collection')
    parser.add_argument("-f", "--file", dest="file", help="Config file to use", metavar="FILE")
    parser.add_argument("-l", "--log", dest="log", help="Output file for log", metavar="FILE")
    parser.add_argument("-d", "--debug", dest="debug", help="Debug level: INFO (default) or DEBUG")
    args = parser.parse_args()

    # Configure logging
    debug_level = (args.debug or "INFO").upper()
    if debug_level not in ["INFO", "DEBUG"]:
        raise ValueError("Debug level must be INFO or DEBUG")
    logging.basicConfig(filename=args.log, filemode='w' if args.log else None, level=debug_level,
                        format="%(levelname)s: %(message)s")

    if not args.file:
        logging.error("Config file not specified. Usage: test.py -f <yaml file> [-d INFO|DEBUG] [-l <log file>]")
        raise ValueError("Config file not specified")

    # Load YAML config
    try:
        with open(args.file, 'r') as f:
            config = yaml.safe_load(f)
        PLATFORM_SCHEMA.validate(config)
        logging.info("Configuration file is valid")
    except FileNotFoundError:
        logging.error("Config file not found: %s", args.file)
        raise
    except yaml.YAMLError as e:
        logging.error("YAML parsing error: %s", e)
        raise
    except SchemaError as e:
        logging.error("Configuration validation error: %s", e)
        raise

    # Initialize shared data
    try:
        shared_data = BneWasteCollectionData(
            config.get(CONF_BASE_URL),
            config.get(CONF_WASTE_DAYS_TABLE),
            config.get(CONF_WASTE_WEEKS_TABLE),
            config.get(CONF_KERBSIDE_TABLE),
            config.get(CONF_PROPERTY_NUMBER),
        )
        shared_data.update()
    except Exception as e:
        logging.error("Failed to fetch waste collection data: %s", e)
        raise

    # Initialize sensors
    sensors = [
        BneWasteCollectionSensor(
            shared_data,
            config.get(CONF_NAME),
            config.get(CONF_ICON),
            config.get(CONF_ALERT_HOURS),
            recycle_week=False,
            green_bin=config.get(CONF_GREEN_BIN)
        ),
        BneWasteCollectionSensor(
            shared_data,
            config.get(CONF_NAME) + " (Recycle)",
            config.get(CONF_RECYCLE_ICON),
            config.get(CONF_ALERT_HOURS),
            recycle_week=True,
            green_bin=config.get(CONF_GREEN_BIN)
        ),
        BneWasteCollectionKerbsideSensor(
            shared_data,
            config.get(CONF_NAME) + " (Kerbside)",
            config.get(CONF_KERBSIDE_ICON),
            config.get(CONF_KERBSIDE_ALERT_HOURS)
        )
    ]

    # Update all sensors
    for sensor in sensors:
        try:
            sensor.update()
        except Exception as e:
            logging.error("Failed to update sensor '%s': %s", sensor.name, e)

    # Log all sensor data in a readable format
    for sensor in sensors:
        logging.info("=== Sensor: %s ===", sensor.name)
        for attr, value in sensor.extra_state_attributes.items():
            logging.info("%s: %s", attr, value)
        logging.info("=== End of Sensor ===\n")
