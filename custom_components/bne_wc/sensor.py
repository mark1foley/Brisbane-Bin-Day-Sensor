# Waste Collection Algorithm 
# Explanation:
# If the ZONE for the address matches the ZONE for the week, it is yellow recycling bin week.
# If the ZONE for the address does not match the ZONE for the week, it is green waste bin week.

from calendar import weekday
import math
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from time import strptime
from geopy.geocoders import Nominatim

baseUrl = 'https://www.data.brisbane.qld.gov.au/data/api/3/action/datastore_search?resource_id='
wasteDaysTable = 'adcb0791-71f1-4b0e-bb6f-b375ac244896'
wasteWeeksTable = 'c6dbb0b3-1e00-4bb8-8776-aa1b8f1ecfaa'
dateToday = datetime.combine(date.today(), datetime.min.time())
weekStartDate = dateToday - timedelta(dateToday.weekday())
weekStartString = f'{weekStartDate.day}/{weekStartDate:%m/%Y}'
weekDays = 7
weekDayNo = dateToday.weekday()
dayHours = 24
geolocator = Nominatim(user_agent='HA_BNE_Waste_Collection')
location = geolocator.reverse("-27.51753948915311, 153.01444530487063")
address = location.raw['address']
houseNumber = address.get('house_number', '')
houseRoad = address.get('road', '')[0:address.get('road', '').rfind(" ")]
houseSuburb = address.get('suburb', '')
#print(baseUrl + wasteDaysTable + '&q={"HOUSE_NUMBER":"' + houseNumber + '","STREET_NAME":"' + houseRoad + '","SUBURB":"' + houseSuburb + '"}')

# Make the HTTP request
try:  
    # response = requests.get(baseUrl + wasteDaysTable + '&q={"PROPERTY_NUMBER":"' + propertyId + '"}')
    response = requests.get(baseUrl + wasteDaysTable + '&q={"HOUSE_NUMBER":"' + houseNumber + '","STREET_NAME":"' + houseRoad + '","SUBURB":"' + houseSuburb + '"}')
    json=response.json()
    if json['success'] == True:
        dic=json['result']
        df = pd.DataFrame(dic['records'])
        if len(df.index) > 0:
            coll_day = df['COLLECTION_DAY'].iloc[0]
            coll_zone = df['ZONE'].iloc[0]
            # Dataset contains week day names so need to convert it into integer for the day
            coll_day_no = strptime(coll_day,'%A').tm_wday
            if coll_day_no > weekDayNo:
                next_coll_date = dateToday + timedelta(days=coll_day_no-weekDayNo)
            else:
                next_coll_date = dateToday + timedelta(days=(weekDays+coll_day_no)-weekDayNo)
            time_to_coll = next_coll_date - datetime.now()
            hours_to_coll = math.ceil(time_to_coll.seconds/3660) + (time_to_coll.days*dayHours)
            try:
                response = requests.get(baseUrl + wasteWeeksTable + '&q={"WEEK_STARTING":"' + weekStartString + ',"ZONE":' + coll_zone + '"}')
                json=response.json()
                if json['success'] == True:
                    dic=json['result']
                    df = pd.DataFrame(dic['records'])
                    if len(df.index) > 0:
                        additionalBin = 'Yellow'
                    else:
                        additionalBin = 'Green'
                    print('Address: ' + houseNumber + ' ' + houseRoad + ' ' + houseSuburb)
                    print('Collection Day: ' + coll_day)
                    print('Next Collection Date: ' + f'{next_coll_date}')
                    print('Additional Bin: ' + f'{additionalBin}')
                    print('Hours To Collection: ' + f'{hours_to_coll}')
                else:
                    print('Weeks Dataset error')
            except requests.exceptions.RequestException as e:
                print(e)
        else:
            print('Zero rows returned')
    else:
        print('Days Dataset error')
except requests.exceptions.RequestException as e:
    print(e)

