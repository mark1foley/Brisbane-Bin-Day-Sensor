"""Constants for the Brisbane Waste Collection integration."""
 
DOMAIN = "bne_wc"
 
# Config keys
CONF_BASE_URL = "base_url"
CONF_WASTE_DAYS_TABLE = "days_table"
CONF_WASTE_WEEKS_TABLE = "weeks_table"
CONF_KERBSIDE_TABLE = "kerbside_table"
CONF_PROPERTY_NUMBER = "property_number"
CONF_ICON = "icon"
CONF_RECYCLE_ICON = "recycle_icon"
CONF_KERBSIDE_ICON = "kerbside_icon"
CONF_ALERT_HOURS = "alert_hours"
CONF_KERBSIDE_ALERT_HOURS = "kerbside_alert_hours"
CONF_HAS_GREEN_BIN = "green_bin"
CONF_COLLECTION_TIME = "collection_time"
CONF_ENABLE_KERBSIDE = "enable_kerbside"
 
# Defaults
DEFAULT_NAME = "Brisbane Bin Day"
DEFAULT_ICON = "mdi:trash-can"
DEFAULT_RECYCLE_ICON = "mdi:recycle"
DEFAULT_KERBSIDE_ICON = "mdi:truck-alert"
DEFAULT_ALERT_HOURS = 12
DEFAULT_KERBSIDE_ALERT_HOURS = 168
DEFAULT_COLLECTION_TIME = "05:00"
 
# Brisbane City Council Open Data base URL template
DEFAULT_BASE_URL = (
    "https://www.data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets"
    "/{dataset_id}/records?where={query}&limit=100"
)
DEFAULT_WASTE_DAYS_TABLE = "waste-collection-days-collection-days"
DEFAULT_WASTE_WEEKS_TABLE = "waste-collection-days-collection-weeks"
DEFAULT_KERBSIDE_TABLE = "kerbside-large-item-collection-schedule"
  
# Sensor attribute names
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
ATTR_LAST_UPDATE_FAILED = "Last Update Failed"
 
# Timing
WEEK_DAYS = 7
DAY_HOURS = 24
HOUR_SECONDS = 3600