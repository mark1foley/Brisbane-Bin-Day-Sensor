import math
import requests
import logging
import pandas as pd
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
ATTR_DUE_IN = "Due In"
ATTR_ALERT_HOURS = "Alert Hours"
ATTR_EXTRA_BIN = "Extra Bin"
ATTR_RECYCLE_WEEK = "Recycle Week"

CONF_BASE_URL = 'base_url'
CONF_WASTE_DAYS_TABLE = 'days_table'
CONF_WASTE_WEEKS_TABLE = 'weeks_table'
CONF_PROPERTY_NUMBER = 'property_number'
CONF_ICON = 'icon'
CONF_RECYCLE_ICON = 'recycle_icon'

CONF_ALERT_HOURS = 'alert_hours'
CONF_GREEN_BIN = 'green_bin'

DEFAULT_ICON = 'mdi:trash-can'
DEFAULT_RECYCLE_ICON = 'mdi:recycle'
DEFAULT_ALERT_HOURS = 12

# Throttle updates to every 5 minutes 
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)

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

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_BASE_URL): cv.string,
    vol.Required(CONF_WASTE_DAYS_TABLE): cv.string,
    vol.Required(CONF_WASTE_WEEKS_TABLE): cv.string,
    vol.Required(CONF_PROPERTY_NUMBER): cv.positive_int,
    vol.Optional(CONF_ALERT_HOURS, default=DEFAULT_ALERT_HOURS): cv.positive_int,
    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    vol.Optional(CONF_RECYCLE_ICON, default=DEFAULT_RECYCLE_ICON): cv.string,
    vol.Optional(CONF_GREEN_BIN, default=False): cv.boolean
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Get the waste collection sensor."""
    
    data_normal = BneWasteCollection(config.get(CONF_BASE_URL), config.get(CONF_WASTE_DAYS_TABLE), config.get(CONF_WASTE_WEEKS_TABLE), config.get(CONF_PROPERTY_NUMBER),config.get(CONF_GREEN_BIN),False)
    data_recycle = BneWasteCollection(config.get(CONF_BASE_URL), config.get(CONF_WASTE_DAYS_TABLE), config.get(CONF_WASTE_WEEKS_TABLE), config.get(CONF_PROPERTY_NUMBER),config.get(CONF_GREEN_BIN),True)
    recycleSensorName = config.get(CONF_NAME) + " (Recycle)"

    sensors = []

    # Add normal week sensor
    sensors.append(BneWasteCollectionSensor(
        data_normal, 
        config.get(CONF_NAME),
        config.get(CONF_ICON),
        config.get(CONF_ALERT_HOURS)
    ))

    # Add recycle week sensor
    sensors.append(BneWasteCollectionSensor(
        data_recycle, 
        recycleSensorName,
        config.get(CONF_RECYCLE_ICON),
        config.get(CONF_ALERT_HOURS)
    ))

    add_devices(sensors)

class BneWasteCollectionSensor(Entity):
    """Implementation of a waste collection sensor."""

    def __init__(self, data, name, icon, alert_hours):
        """Initialize the sensor."""
        self.data = data
        self._name = name
        self._icon = icon
        self._alert_hours = alert_hours
        self.update()

    def _get_collection_details(self):
        collection_details = {}
        for key, value in self.data.info.items():
            collection_details[key] = value
        return collection_details

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        collection = self._get_collection_details()
        _LOGGER.debug("...State Update: Due In {0} Alert Hours: {1}".format(collection[ATTR_DUE_IN], self._alert_hours))
        return STATE_ON if 0 < collection[ATTR_DUE_IN] <= self._alert_hours else STATE_OFF

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        collection_details = self._get_collection_details()
        attrs = {
            ATTR_ALERT_HOURS: self._alert_hours,
            ATTR_PROPERTY_NUMBER: collection_details[ATTR_PROPERTY_NUMBER],
            ATTR_SUBURB: collection_details[ATTR_SUBURB],
            ATTR_STREET: collection_details[ATTR_STREET],
            ATTR_HOUSE_NUMBER: collection_details[ATTR_HOUSE_NUMBER],
            ATTR_COLLECTION_DAY: collection_details[ATTR_COLLECTION_DAY],
            ATTR_COLLECTION_ZONE: collection_details[ATTR_COLLECTION_ZONE],
            ATTR_NEXT_COLLECTION_DATE: collection_details[ATTR_NEXT_COLLECTION_DATE],
            ATTR_EXTRA_BIN: collection_details[ATTR_EXTRA_BIN],
            ATTR_DUE_IN: collection_details[ATTR_DUE_IN],
            ATTR_RECYCLE_WEEK: collection_details[ATTR_RECYCLE_WEEK]
        }

        return attrs

    @property
    def icon(self):
        return self._icon

    def update(self):
        """Get the latest data from opendata.ch and update the states."""
        self.data.update()
        _LOGGER.debug("Sensor Update:")
        _LOGGER.debug("...Name: {0}".format(self._name))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_PROPERTY_NUMBER,self.extra_state_attributes[ATTR_PROPERTY_NUMBER]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_PROPERTY_NUMBER))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_SUBURB,self.extra_state_attributes[ATTR_SUBURB]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_SUBURB))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_STREET,self.extra_state_attributes[ATTR_STREET]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_STREET))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_HOUSE_NUMBER,self.extra_state_attributes[ATTR_HOUSE_NUMBER]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_HOUSE_NUMBER))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_COLLECTION_DAY,self.extra_state_attributes[ATTR_COLLECTION_DAY]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_COLLECTION_DAY))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_COLLECTION_ZONE,self.extra_state_attributes[ATTR_COLLECTION_ZONE]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_COLLECTION_ZONE))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_NEXT_COLLECTION_DATE,self.extra_state_attributes[ATTR_NEXT_COLLECTION_DATE]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_NEXT_COLLECTION_DATE))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_EXTRA_BIN,self.extra_state_attributes[ATTR_EXTRA_BIN]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_EXTRA_BIN))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_ALERT_HOURS,self.extra_state_attributes[ATTR_ALERT_HOURS]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_ALERT_HOURS))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_DUE_IN,self.extra_state_attributes[ATTR_DUE_IN]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_DUE_IN))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_RECYCLE_WEEK,self.extra_state_attributes[ATTR_RECYCLE_WEEK]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_RECYCLE_WEEK))

class BneWasteCollection(object):
    """The Class for handling the data retrieval."""

    def __init__(self, base_url, days_table, weeks_table, property_number, green_bin, recycle_week):
        """Initialize the info object."""
        self._base_url = base_url
        self._days_table = days_table
        self._weeks_table = weeks_table
        self._property_number = property_number
        self._green_bin = green_bin
        self._recycle_week = recycle_week
        self.info = {}
        
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):

        collection = self._get_collection_details() if self._property_number else {}
        self._get_extra_bin(collection)

    def _get_collection_details(self):

        collection = {}
        _LOGGER.info("Updating Waste Collection data")
        try:
            collection[ATTR_PROPERTY_NUMBER] = self._property_number
            full_url = self._base_url.format(**{
                'dataset_id': self._days_table,
                'query': quote_plus("property_number = {0}".format(int(self._property_number)))
            })
            _LOGGER.info("...Day query: {0}".format(full_url))
            response = requests.get(full_url)
            json=response.json()
            if 'error_code' in json:
                _LOGGER.error("Error retrieving collection day dataset: {0}: {1}".format(json['error_code'], json['message']))
            else:
                _LOGGER.info("...Successfully retrieved collection day dataset")
                dic=json['results']
                df = pd.DataFrame(dic)
                if len(df.index) > 0:
                    collection[ATTR_SUBURB] = df['suburb'].iloc[0]
                    collection[ATTR_STREET] = df['street_name'].iloc[0]
                    collection[ATTR_HOUSE_NUMBER] = df['house_number'].iloc[0]
                    collection[ATTR_COLLECTION_DAY] = df['collection_day'].iloc[0]
                    collection[ATTR_COLLECTION_ZONE] = df['zone'].iloc[0]

                    collection_day_no = strptime(collection[ATTR_COLLECTION_DAY],'%A').tm_wday
                    current_day_no = datetime.today().weekday()
                    if collection_day_no > current_day_no:
                        collection[ATTR_NEXT_COLLECTION_DATE] = (date_today() + timedelta(days=collection_day_no-current_day_no)).isoformat()
                    else:
                        collection[ATTR_NEXT_COLLECTION_DATE] = (date_today() + timedelta(days=(WEEK_DAYS+collection_day_no)-current_day_no)).isoformat()
        
                else:
                    _LOGGER.error('Collection day dataset zero rows returned')
        except requests.exceptions.RequestException as e:
                _LOGGER.error("updating collection day got {}.".format(requests.exceptions.RequestException))
                
        return collection

    def _get_extra_bin(self, collection):
        # Waste Collection Algorithm 
        # Explanation:
        # If the ZONE for the address matches the ZONE for the week, it is yellow recycling bin week.
        # If the ZONE for the address does not match the ZONE for the week, it is green waste bin week.
        collection_day_no = strptime(collection[ATTR_COLLECTION_DAY],'%A').tm_wday
        weekStartDate = parse(collection[ATTR_NEXT_COLLECTION_DATE]) - timedelta(days=collection_day_no)
        weekStartString = f'{weekStartDate:%Y-%m-%d}'

        try:
            full_url = self._base_url.format(**{
                'dataset_id': self._weeks_table,
                'query': quote_plus("week_starting = date'{0}' AND search(zone, '{1}')".format(str(weekStartString).replace("'", "\\'"), str(collection[ATTR_COLLECTION_ZONE]).replace("'", "\\'")))
            })
            _LOGGER.info("...Week query: {0}".format(full_url))
            response = requests.get(full_url)
            json=response.json()
            if 'error_code' in json:
                _LOGGER.error("Error retrieving collection week dataset: {0}: {1}".format(json['error_code'], json['message']))
            else:
                _LOGGER.info("...Successfully retrieved collection week dataset")
                dic=json['results']
                df = pd.DataFrame(dic)
                collection[ATTR_RECYCLE_WEEK] = self._recycle_week
                if self._recycle_week:
                    collection[ATTR_EXTRA_BIN] = 'Yellow/Recycling'
                    if len(df.index) == 0:
                        # If no row returned then next collection date is not recycling week so advance collection date one week
                        collection[ATTR_NEXT_COLLECTION_DATE] = (parse(collection[ATTR_NEXT_COLLECTION_DATE]) + timedelta(days=WEEK_DAYS)).isoformat()
                else:
                    # "Normal" week
                    if self._green_bin: 
                        collection[ATTR_EXTRA_BIN] = 'Green/Garden'
                    else:
                        collection[ATTR_EXTRA_BIN] = ''
                    if len(df.index) > 0:
                        # If row returned then next collection date is recycling week so advance collection date one week
                        collection[ATTR_NEXT_COLLECTION_DATE] = (parse(collection[ATTR_NEXT_COLLECTION_DATE]) + timedelta(days=WEEK_DAYS)).isoformat()

                if is_valid_date(collection[ATTR_NEXT_COLLECTION_DATE]):
                    collection[ATTR_DUE_IN] = due_in_hours(parse(collection[ATTR_NEXT_COLLECTION_DATE]))
                else:
                    collection[ATTR_DUE_IN] = -1                        
        except requests.exceptions.RequestException as e:
            _LOGGER.error("updating collection week got {}.".format(requests.exceptions.RequestException))

        self.info = collection