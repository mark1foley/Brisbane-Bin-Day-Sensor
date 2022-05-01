# Waste Collection Algorithm 
# Explanation:
# If the ZONE for the address matches the ZONE for the week, it is yellow recycling bin week.
# If the ZONE for the address does not match the ZONE for the week, it is green waste bin week.

import math
import requests
import logging
import pandas as pd
import voluptuous as vol

from calendar import weekday
from datetime import datetime, timedelta, date
from time import strptime
#from geopy.geocoders import Nominatim

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, ATTR_LONGITUDE, ATTR_LATITUDE)
import homeassistant.util.dt as dt_util
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_STOP_ID = "Stop ID"
ATTR_ROUTE = "Route"
ATTR_DUE_IN = "Due in"
ATTR_DUE_AT = "Due at"
ATTR_NEXT_UP = "Next Service"
ATTR_ICON = "Icon"

CONF_SUBURB = 'suburb'
CONF_STREET = 'street'
CONF_HOUSE_NUMBER = 'house_number'

DEFAULT_ICON = 'mdi:trash-can'

MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(seconds=3600)
TIME_STR_FORMAT = "%H:%M"
BASE_URL = 'https://www.data.brisbane.qld.gov.au/data/api/3/action/datastore_search?resource_id='
WASTE_DAYS_TABLE = 'adcb0791-71f1-4b0e-bb6f-b375ac244896'
WASTE_WEEKS_TABLE = 'c6dbb0b3-1e00-4bb8-8776-aa1b8f1ecfaa'
WEEK_DAYS = 7
DAY_HOURS = 24

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SUBURB): cv.string,
    vol.Required(CONF_STREET): cv.string,
    vol.Optional(CONF_HOUSE_NUMBER): cv.string
})

dateToday = datetime.combine(date.today(), datetime.min.time())
weekStartDate = dateToday - timedelta(dateToday.weekday())
weekStartString = f'{weekStartDate.day}/{weekStartDate:%m/%Y}'
weekDayNo = dateToday.weekday()

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Get the public transport sensor."""
    
    data = BneWasteCollection(config.get(CONF_SUBURB), config.get(CONF_STREET), config.get(CONF_HOUSE_NUMBER))
    #sensors = []
    #sensors.append(PublicTransportSensor(data)

    #add_devices(sensors)

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

class BneWasteCollection(object):
    """The Class for handling the data retrieval."""

    def __init__(self, suburb, street, house_number):
        """Initialize the info object."""
        self._suburb = suburb
        self._street = street
        self._house_number = house_number
        self.info = {}
        
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.info("suburb: {}".format(self._suburb))
        _LOGGER.info("street: {}".format(self._street))
        _LOGGER.info("house_number: {0}".format(self._house_number))

        collectionday = self._get_collection_day()

    def _get_collection_day(self):

        response = requests.get(BASE_URL + WASTE_DAYS_TABLE + '&q={"HOUSE_NUMBER":"' + self._house_number + '","STREET_NAME":"' + self._street + '","SUBURB":"' + self._suburb + '"}')
        json=response.json()
        if json['success'] == True:
            _LOGGER.info("Successfully retrieved collection day dataset")
            dic=json['result']
            df = pd.DataFrame(dic['records'])
            if len(df.index) > 0:
                collectionday = df['COLLECTION_DAY'].iloc[0]
                # coll_zone = df['ZONE'].iloc[0]
            else:
                _LOGGER.error('Collection day dataset zero rows returned')
        else:            
            _LOGGER.error("updating collection day got {}.".format(requests.exceptions.RequestException))

        return collectionday
