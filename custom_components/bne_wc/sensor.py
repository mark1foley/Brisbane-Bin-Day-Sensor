# Waste Collection Algorithm 
# Explanation:
# If the ZONE for the address matches the ZONE for the week, it is yellow recycling bin week.
# If the ZONE for the address does not match the ZONE for the week, it is green waste bin week.

import math
import requests
import logging
import pandas as pd
import voluptuous as vol

from dateutil.parser import parse
from calendar import weekday
from datetime import datetime, timedelta, date
from time import strptime
#from geopy.geocoders import Nominatim

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME)
#import homeassistant.util.dt as dt_util
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_PROPERTY_ID = "Property ID"
ATTR_COLLECTION_DAY = "Collection Day"
ATTR_COLLECTION_ZONE = "Collection Zone"
ATTR_NEXT_COLLECTION_DATE = "Next Collection Date"
ATTR_ICON = "Icon"

CONF_BASE_URL = 'base_url'
CONF_WASTE_DAYS_TABLE = 'days_table'
CONF_WASTE_WEEKS_TABLE = 'weeks_table'
CONF_PROPERTY_ID = 'property_id'
CONF_ICON = 'icon'

DEFAULT_ICON = 'mdi:trash-can'

#MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=3600)
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

WEEK_DAYS = 7
DAY_HOURS = 24

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
    _LOGGER.debug("due_in_hour calc")
    
    diff = time_stamp - datetime.now()
    return math.ceil(diff.seconds/3660) + (diff.days*DAY_HOURS)

def date_today():
    return datetime.combine(date.today(), datetime.min.time())
    
def week_day(timestamp):
    return weekday(timestamp.year, timestamp.month, timestamp.day)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_BASE_URL): cv.string,
    vol.Required(CONF_WASTE_DAYS_TABLE): cv.string,
    vol.Required(CONF_WASTE_WEEKS_TABLE): cv.string,
    vol.Required(CONF_PROPERTY_ID): cv.string,
    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string
})

#weekStartDate = date_today - timedelta(date_today.weekday())
#weekStartString = f'{weekStartDate.day}/{weekStartDate:%m/%Y}'

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Get the waste collection sensor."""
    
    data = BneWasteCollection(config.get(CONF_BASE_URL), config.get(CONF_WASTE_DAYS_TABLE), config.get(CONF_WASTE_WEEKS_TABLE), config.get(CONF_PROPERTY_ID))
    sensors = []
    sensors.append(BneWasteCollectionSensor(
        data, 
        config.get(CONF_NAME),
        config.get(CONF_ICON),
        config.get(CONF_PROPERTY_ID)
    ))

    add_devices(sensors)


#geolocator = Nominatim(user_agent='HA_BNE_Waste_Collection')
#location = geolocator.reverse("-27.51753948915311, 153.01444530487063")
#address = location.raw['address']
#houseNumber = address.get('house_number', '')
#houseRoad = address.get('road', '')[0:address.get('road', '').rfind(" ")]
#houseSuburb = address.get('suburb', '')
#print(BASE_URL + WASTE_DAYS_TABLE + '&q={"HOUSE_NUMBER":"' + houseNumber + '","STREET_NAME":"' + houseRoad + '","SUBURB":"' + houseSuburb + '"}')

# Make the HTTP request
#try:  
#    # response = requests.get(BASE_URL + WASTE_DAYS_TABLE + '&q={"PROPERTY_NUMBER":"' + propertyId + '"}')
#    response = requests.get(BASE_URL + WASTE_DAYS_TABLE + '&q={"HOUSE_NUMBER":"' + houseNumber + '","STREET_NAME":"' + houseRoad + '","SUBURB":"' + houseSuburb + '"}')
#    json=response.json()
#    if json['success'] == True:
#        dic=json['result']
#        df = pd.DataFrame(dic['records'])
#        if len(df.index) > 0:
#            coll_day = df['COLLECTION_DAY'].iloc[0]
#            coll_zone = df['ZONE'].iloc[0]
#            # Dataset contains week day names so need to convert it into integer for the day
#            coll_day_no = strptime(coll_day,'%A').tm_wday
#            if coll_day_no > weekDayNo:
#                next_coll_date = dateToday + timedelta(days=coll_day_no-weekDayNo)
#            else:
#                next_coll_date = dateToday + timedelta(days=(WEEK_DAYS+coll_day_no)-weekDayNo)
#            time_to_coll = next_coll_date - datetime.now()
#            hours_to_coll = math.ceil(time_to_coll.seconds/3660) + (time_to_coll.days*DAY_HOURS)
#            try:
#                response = requests.get(BASE_URL + WASTE_WEEKS_TABLE + '&q={"WEEK_STARTING":"' + weekStartString + ',"ZONE":' + coll_zone + '"}')
#                json=response.json()
#                if json['success'] == True:
#                    dic=json['result']
#                    df = pd.DataFrame(dic['records'])
#                    if len(df.index) > 0:
#                        additionalBin = 'Yellow'
#                    else:
#                        additionalBin = 'Green'
#                    print('Address: ' + houseNumber + ' ' + houseRoad + ' ' + houseSuburb)
#                    print('Collection Day: ' + coll_day)
#                    print('Next Collection Date: ' + f'{next_coll_date}')
#                    print('Additional Bin: ' + f'{additionalBin}')
#                    print('Hours To Collection: ' + f'{hours_to_coll}')
#                else:
#                    print('Weeks Dataset error')
#            except requests.exceptions.RequestException as e:
#                print(e)
#        else:
#            print('Zero rows returned')
#    else:
#        print('Days Dataset error')
#except requests.exceptions.RequestException as e:
#    print(e)

class BneWasteCollectionSensor(Entity):
    """Implementation of a waste collection sensor."""

    def __init__(self, data, name, icon, property_id):
        """Initialize the sensor."""
        self.data = data
        self._name = name
        self._icon = icon
        self._property_id = property_id
        self.update()

    def _get_collection_details(self):
        collection_details = {}
        for key, value in self.data.info.items():
            collection_details[key] = value
            
        _LOGGER.debug("Collection Details: {0}".format(collection_details))
        return collection_details

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        collection_details = self._get_collection_details()
        return due_in_hours(parse(collection_details[ATTR_NEXT_COLLECTION_DATE])) if is_valid_date(collection_details[ATTR_NEXT_COLLECTION_DATE]) else '-'

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        collection_details = self._get_collection_details()
        attrs = {
            ATTR_PROPERTY_ID: self._property_id,
            ATTR_ICON: self._icon,
            ATTR_COLLECTION_DAY: collection_details[ATTR_COLLECTION_DAY],
            ATTR_COLLECTION_ZONE: collection_details[ATTR_COLLECTION_ZONE],
            ATTR_NEXT_COLLECTION_DATE: collection_details[ATTR_NEXT_COLLECTION_DATE]
        }

        return attrs

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "hr"

    @property
    def icon(self):
        return self._icon

    def update(self):
        """Get the latest data from opendata.ch and update the states."""
        self.data.update()
        _LOGGER.debug("Sensor Update:")
        _LOGGER.debug("...Name: {0}".format(self._name))
        _LOGGER.debug("...{0}: {1}".format(ATTR_ICON,self._icon))
        _LOGGER.debug("...{0}: {1}".format("unit_of_measurement",self.unit_of_measurement))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_COLLECTION_DAY,self.extra_state_attributes[ATTR_COLLECTION_DAY]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_COLLECTION_DAY))
        try:
            _LOGGER.debug("...{0}: {1}".format(ATTR_COLLECTION_ZONE,self.extra_state_attributes[ATTR_COLLECTION_ZONE]))
        except:
            _LOGGER.debug("...{0} not defined".format(ATTR_COLLECTION_ZONE))

class BneWasteCollection(object):
    """The Class for handling the data retrieval."""

    def __init__(self, base_url, days_table, weeks_table, property_id):
        """Initialize the info object."""
        self._base_url = base_url
        self._days_table = days_table
        self._weeks_table = weeks_table
        self._property_id = property_id
        self.info = {}
        
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.info("base_url: {}".format(self._base_url))
        _LOGGER.info("days_table: {}".format(self._days_table))
        _LOGGER.info("weeks_table: {0}".format(self._weeks_table))
        _LOGGER.info("property_id: {0}".format(self._property_id))

        _LOGGER.debug("BneWasteCollection.Update")

        self.info = self._get_collection_details() if self._property_id else {}

        _LOGGER.debug("...Property ID: {0}".format(self.info[ATTR_PROPERTY_ID]))
        _LOGGER.debug("...New Collection Day: {0}".format(self.info[ATTR_COLLECTION_DAY]))
        _LOGGER.debug("...New Collection Zone: {0}".format(self.info[ATTR_COLLECTION_ZONE]))
        _LOGGER.debug("...Next Collection Date: {0}".format(self.info[ATTR_NEXT_COLLECTION_DATE]))
    
    def _get_collection_details(self):

        collection = {}
        try:
            collection[ATTR_PROPERTY_ID] = self._property_id
            _LOGGER.debug("query: {0}{1}{2}{3}{4}".format(self._base_url,self._days_table,'&q={"PROPERTY_NUMBER":"',self._property_id, '"}'))
            response = requests.get(self._base_url + self._days_table + '&q={"PROPERTY_NUMBER":"' + self._property_id + '"}')
            json=response.json()
            if json['success'] == True:
                _LOGGER.info("Successfully retrieved collection day dataset")
                dic=json['result']
                df = pd.DataFrame(dic['records'])
                if len(df.index) > 0:
                    collection[ATTR_COLLECTION_DAY] = df['COLLECTION_DAY'].iloc[0]
                    collection[ATTR_COLLECTION_ZONE] = df['ZONE'].iloc[0]

                    collection_day_no = strptime(collection[ATTR_COLLECTION_DAY],'%A').tm_wday
                    current_day_no = datetime.today().weekday()
                    if collection_day_no > current_day_no:
                        collection[ATTR_NEXT_COLLECTION_DATE] = (date_today() + timedelta(days=collection_day_no-current_day_no)).isoformat()
                    else:
                        collection[ATTR_NEXT_COLLECTION_DATE] = (date_today() + timedelta(days=(WEEK_DAYS+collection_day_no)-current_day_no)).isoformat()

                else:
                    _LOGGER.error('Collection day dataset zero rows returned')
            else:            
                _LOGGER.error("Error retrieving collection day dataset")
        except requests.exceptions.RequestException as e:
                _LOGGER.error("updating collection day got {}.".format(requests.exceptions.RequestException))
                
        return collection

