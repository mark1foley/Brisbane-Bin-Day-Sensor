# Brisbane Bin Collection Day

This project contains a new sensor that provides details of bin collection day

## Installation (HACS) - Recommended
0. Have [HACS](https://custom-components.github.io/hacs/installation/manual/) installed, this will allow you to easily update
1. Add `https://github.com/mark1foley/BNE_Waste_Collection` as a [custom repository](https://custom-components.github.io/hacs/usage/settings/#add-custom-repositories) as Type: Integration
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
# Example entry for Austin TX

sensor:
  - platform: gtfs_rt
    trip_update_url: 'https://data.texas.gov/download/rmk2-acnw/application%2foctet-stream'
    vehicle_position_url: 'https://data.texas.gov/download/eiei-9rpf/application%2Foctet-stream'
    departures:
    - name: Downtown to airport
      route: 100
      stopid: 514
```

```yaml
# Example entry for Seattle WA

- platform: gtfs_rt
  trip_update_url: 'http://api.pugetsound.onebusaway.org/api/gtfs_realtime/trip-updates-for-agency/1.pb?key=TEST'
  departures:
  - name: "48 to Uni"
    route: 100228
    stopid: 36800
```


Configuration variables:

- **trip_update_url** (*Required*): Provides bus route etas. See the **Finding Feeds** section at the bottom of the page for more details on how to find these
- **vehicle_position_url** (*Optional*): Provides live bus position tracking on the home assistant map
- **api_key** (*Optional*): If provided, this key will be sent with API
requests in an "Authorization" header.
- **departures** (*Required*): A list of routes and departure locations to watch
- **route** (*Optional*): The name of the gtfs route
- **stopid** (*Optional*): The stopid for the location you want etas for

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
