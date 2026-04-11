"""Constants for the Brisbane Bin Day Sensor integration."""

DOMAIN = "bne_wc"

# ── API ──────────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = (
    "https://www.data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets"
    "/{dataset_id}/records?where={query}&limit={limit}"
)

DEFAULT_LIMIT = 100

# ── Dataset table names ──────────────────────────────────────────────────────

DEFAULT_WASTE_DAYS_TABLE    = "waste-collection-days-collection-days"
DEFAULT_WASTE_WEEKS_TABLE   = "waste-collection-days-collection-weeks"
DEFAULT_KERBSIDE_TABLE      = "kerbside-large-item-collection-schedule"

# ── Config entry keys ────────────────────────────────────────────────────────

CONF_SENSOR_NAME            = "name"
CONF_PROPERTY_NUMBER        = "property_number"
CONF_WASTE_DAYS_TABLE       = "waste_days_table"
CONF_WASTE_WEEKS_TABLE      = "waste_weeks_table"
CONF_KERBSIDE_TABLE         = "kerbside_table"
CONF_SUBURB                 = "suburb"
CONF_STREET_NAME            = "street_name"
CONF_HOUSE_NUMBER           = "house_number"
CONF_ICON                   = "icon"
CONF_RECYCLE_ICON           = "recycle_icon"
CONF_KERBSIDE_ICON          = "kerbside_icon"
CONF_ALERT_HOURS            = "alert_hours"
CONF_KERBSIDE_ALERT_HOURS   = "kerbside_alert_hours"
CONF_HAS_GREEN_BIN          = "has_green_bin"
CONF_COLLECTION_TIME        = "collection_time"
CONF_ENABLE_KERBSIDE        = "enable_kerbside"

# ── Sensor attribute keys ────────────────────────────────────────────────────

ATTR_PROPERTY_NUMBER                = "property_number"
ATTR_SUBURB                         = "suburb"
ATTR_STREET                         = "street_name"
ATTR_HOUSE_NUMBER                   = "house_number"
ATTR_COLLECTION_DAY                 = "collection_day"
ATTR_COLLECTION_ZONE                = "collection_zone"
ATTR_NEXT_COLLECTION_DATE           = "next_collection_date"
ATTR_NEXT_KERBSIDE_COLLECTION_DATE  = "next_kerbside_collection_date"
ATTR_NEXT_KERBSIDE_ON_FOOTPATH_DATE = "next_kerbside_on_footpath_date"
ATTR_KERBSIDE_DUE_IN                = "kerbside_due_in"
ATTR_KERBSIDE_ALERT_HOURS           = "kerbside_alert_hours"
ATTR_DUE_IN                         = "due_in"
ATTR_ALERT_HOURS                    = "alert_hours"
ATTR_EXTRA_BIN                      = "extra_bin"
ATTR_RECYCLE_WEEK                   = "recycle_week"
ATTR_LAST_UPDATE_FAILED             = "last_update_failed"

# ── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_SENSOR_NAME         = "Brisbane Bin Day"
DEFAULT_ICON                = "mdi:trash-can"
DEFAULT_RECYCLE_ICON        = "mdi:recycle"
DEFAULT_KERBSIDE_ICON       = "mdi:truck"
DEFAULT_ALERT_HOURS         = 12
DEFAULT_KERBSIDE_ALERT_HOURS = 168              # Kerbside collections are annual and require prep so longer alert time
DEFAULT_COLLECTION_TIME     = "05:00"

# ── Misc ─────────────────────────────────────────────────────────────────────

HOUR_SECONDS = 3600
