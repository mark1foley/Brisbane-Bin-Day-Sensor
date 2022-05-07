# Brisbane Bin Day Sensor

This project contains a new Home Assistant sensor that provides details of bin day

## Installation (HACS) - Recommended
0. Have [HACS](https://custom-components.github.io/hacs/installation/manual/) installed, this will allow you to easily update
1. Add `https://github.com/mark1foley/Brisbane-Bin-Day-Sensor` as a [custom repository](https://custom-components.github.io/hacs/usage/settings/#add-custom-repositories) as Type: Integration
2. Click install under "BNE_Waste_Collection", restart your instance.

## Installation (Manual)
1. Download this repository as a ZIP (green button, top right) and unzip the archive
2. Copy `/custom_components/bne_wc` to your `<config_dir>/custom_components/` directory
   * You will need to create the `custom_components` folder if it does not exist
   * On Hassio the final location will be `/config/custom_components/bne_wc`
   * On Hassbian the final location will be `/home/homeassistant/.homeassistant/custom_components/bne_wc`

## Configuration

Add the following to your `configuration.yaml` file:

```yaml

sensor:
  - platform: bne_wc
    suburb: '<suburb name>'
    street: '<street name>'
    house_number: '<house number>'
```

Configuration variables:

- **suburb** (*Required*): Name of suburb
- **street** (*Optional*): Name of street
- **house_number** (*Optional*): House number in street.  If not supplied the detail of the first house returned will be used.

## Reporting an Issue

1. Setup your logger to print debug messages for this component using:
```yaml
logger:
  default: info
  logs:
    custom_components.gtfs_rt: debug
```
2. Restart HA
3. Verify you're still having the issue
4. File an issue in this Github Repository containing your HA log (Developer section > Info > Load Full Home Assistant Log)
   * You can paste your log file at pastebin https://pastebin.com/ and submit a link.
   * Please include details about your setup (Pi, NUC, etc, docker?, HASSOS?)
   * The log file can also be found at `/<config_dir>/home-assistant.log`
