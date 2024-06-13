# Brisbane Bin Day Sensor

This project creates two new Home Assistant binary sensors that provide details of bin collections in the Brisbane City Council area.  One sensor is for the "normal" (or optionally green bin) week while the other is for the recycle (yellow bin) week.  Two sensors are used to enable the creation of alerts in Home Assistant with names specific to the weeks.

While most Councils provide details of their waste collection schedules via their Open Data portals there is no consistency or standards in how the data is structured (especially when it comes to the recycle week determination).  Therefore, it is not possible to create a generic sensor but you are welcome to fork this code and cusrtomize it for your particular Council. 

## Installation (HACS) - Recommended
0. Have [HACS](https://custom-components.github.io/hacs/installation/manual/) installed, this will allow you to easily update
1. Add `https://github.com/mark1foley/Brisbane-Bin-Day-Sensor` as a [custom repository](https://custom-components.github.io/hacs/usage/settings/#add-custom-repositories) as Type: Integration
2. Click install under "Brisbane Bin Day Sensor", restart your instance.

## Installation (Manual)
1. Download this repository as a ZIP (green button, top right) and unzip the archive
2. Copy `/custom_components/bne_wc` to your `<config_dir>/custom_components/` directory
   * You will need to create the `custom_components` folder if it does not exist
   * On Hassio the final location will be `/config/custom_components/bne_wc`
   * On Hassbian the final location will be `/home/homeassistant/.homeassistant/custom_components/bne_wc`

## Configuration

You will need to obtain your property number from the [Brisbane City Council Waste Collection Open Data Site](https://data.brisbane.qld.gov.au/explore/dataset/waste-collection-days-collection-days/table/).  Search for your address and copy the value in the Property_Number column of the table.

Add the following to your `configuration.yaml` file:

```yaml

sensor:
  - platform: bne_wc
    name: Brisbane Bin Day
    scan_interval: 300
    base_url: https://www.data.brisbane.qld.gov.au/api/explore/v2.1/catalog/datasets/{dataset_id}/records?where={query}&limit=1
    days_table: waste-collection-days-collection-days
    weeks_table: waste-collection-days-collection-weeks
    property_number: <value you copied above>
```

Configuration variables:

- **name** (*Required*): Name of the sensor in HA
- **scan_interval** (*Optional*): Home Assistant updates sensors every 30 seconds by default.  As this data changes slowly I suggest a larger interval 
- **base_url** (*Required*): URL for the brisbane City Council Open Data website
- **days_table** (*Required*): Name of the open data table that contain details of collection days for each property
- **weeks_table** (*Required*): Name of the open data table that contain details which additional bins are collected each week
- **property_number** (*Required*): Unique property number to be used (from the Brisbane City Council Waster Collection Data Open Data Site referenced above
- **icon** (*Optional*): Name of the icon to use for the "normal" week sensor (defaults to mdi:trash-can)
- **recycle_icon** (*Optional*): Name of the icon to use for the "recycle" week sensor (defaults to mdi:recycle)
- **alert_hours** (*Optional*): Number of hours before bin day to raise alert (defaults to 12)
- **green_bin** (*Optional*): true/false to indicate if you have a green bin (reflected in the Extra Bin attribute for the "normal" weeks

## Sensor

The integration creates a sensor with the name specified in the configuration with the following attributes.

- **name** (*String*): As specified in the configuration.  The "recycle" week sensor has the suffix " (Recycle)"
- **Property Number** (*Integer*): As specified in the configuration 
- **Alert Hours** (*Integer*): As specified in the configuration 
- **Suburb** (*String*): Name of suburb returned from the Open Data website for the specified property  
- **Street** (*String*): Name of street, road etc returned from the Open Data website for the specified property  
- **House Number** (*String*): Lot/street number returned from the Open Data website for the specified property  
- **Collection Day** (*String*): Collection day name (MONDAY, TUESDAY etc) for the specified property  
- **Collection Zone** (*String*): Collection zone for the specified property.  Used to determine which extra bin to put out for the next collection
- **Next Collection Date** (*DateTime*): Date and time (at 12:00AM) of the next collection day for the specified property 
- **Extra Bin** (*String*): Name of the extra bin to be put out for the next collection (either 'Yellow/Recycle' or 'Green/Garden')
- **Due In** (*Integer*): Number of hours until the 12:00AM on the next collection day for the specified property 
- **Recycle Week**: true/false to indicate if this is the "recycle" week sensor
- **icon** (*String*): As specified in the configuration, or default of mdi:trash-can
- **friendly_name** (*String*): As specified in the configuration

The state of the sensor will be set to 'off' unless the 'Due In' attribute is less than or equal to the 'Alert Hours' when it will be set to 'on'.  The state will return to 'off' when the 'Due In' attribute reaches 0.

## Alerts

Home assistant alerts that use notifications can be setup to monitor the state of the sensors.  Here are some examples.

```yaml
  take_the_bin_out:
    name: Take the bin out (red bin only)
    entity_id: sensor.brisbane_bin_day
    state: "on"
    repeat: 1
    can_acknowledge: false
    skip_first: false
    message: "Take the bin out (+ {{ state_attr('sensor.brisbane_bin_day', 'Extra Bin') }})!!!"
    notifiers:
      - persistent_notification
```

```yaml
  take_the_recycle_bin_out:
    name: Take the bins out (red + yellow bin)
    entity_id: sensor.brisbane_bin_day_recycle
    state: "on"
    repeat: 60
    can_acknowledge: false
    skip_first: false
    notifiers:
      - persistent_notification
```
## Reporting an Issue

1. Setup your logger to print debug messages for this component using:
```yaml
logger:
  default: info
  logs:
    custom_components.bne_wc: debug
```
2. Restart HA
3. Verify you're still having the issue
4. File an issue in this Github Repository containing your HA log (Developer section > Info > Load Full Home Assistant Log)
   * You can paste your log file at pastebin https://pastebin.com/ and submit a link.
   * Please include details about your setup (Pi, NUC, etc, docker?, HASSOS?)
   * The log file can also be found at `/<config_dir>/home-assistant.log`
