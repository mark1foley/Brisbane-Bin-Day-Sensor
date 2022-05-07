# Brisbane Bin Day Sensor

This project contains a new Home Assistant sensor that provides details of bin day

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

You will need to obtain your property number from the [Brisbane City Council Waster Collection Data Open Data Site](https://www.data.brisbane.qld.gov.au/data/dataset/waste-collection-days/resource/adcb0791-71f1-4b0e-bb6f-b375ac244896).  Search for your address and copy the value in the Property_Number column of the table.

Add the following to your `configuration.yaml` file:

```yaml

sensor:
  - platform: bne_wc
    name: Brisbane Bin Day
    base_url: https://www.data.brisbane.qld.gov.au/data/api/3/action/datastore_search?resource_id=
    days_table: adcb0791-71f1-4b0e-bb6f-b375ac244896
    weeks_table: c6dbb0b3-1e00-4bb8-8776-aa1b8f1ecfaa
    property_number: <value you copied above>
```

Configuration variables:

- **name** (*Required*): Name of the sensor in HA
- **base_url** (*Required*): URL for the brisbane City Council Open Data website
- **days_table** (*Required*): Name of the open data table that contain details of collection days for each property
- **weeks_table** (*Required*): Name of the open data table that contain details which additional bins are collected each week
- **property_number** (*Required*): Unique property number to be used (from the Brisbane City Council Waster Collection Data Open Data Site referenced above
- **icon** (*Optional*): Name of the icon to use for the sensor (defaults to mdi:trash-can)
- **alert_hours** (*Optional*): Number of hours before bin day to raise alert (defaults to 12)

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
