# AC•THOR

Home Assistant integration for my-PV's AC•THOR.

## Disclaimer

AC•THOR only supports one active connection.
It's impossible to connect to the device while another connection is active.

If you want to control it through another device you need to add them both to Home Assistant and use an automation to call the `acthor.set_power` service.

Please be aware that I can't guarantee that this will work well for your use case.
I'm trying to make it work for all possible use cases but because of the poor documentation on AC•THOR's side some features might not work as expected.

Don't hesitate to open an issue if something seems off.

## Installation

1. Go to the HACS Settings and add the custom repository `siku2/hass-acthor` with category "Integration".
2. Open the "Integrations" tab and search for "AC•THOR".
3. Follow the instructions there to set the integration up.

## Entities

The integration adds multiple entities because the AC•THOR doesn't really fit any platform.

### Sensor

The sensor reflects the current power usage of the device.
It also comes with a few additional attributes:

- `status`: Status name
- `status_code`: Status code number
- `power_target`: Power usage the integration is targeting.
  This will be different from the actual state if the device isn't using all the power it's given.
- `load_nominal_power`: The load's nominal power
- `temp_internal`: Internal temperature
- `temp_sensor_X`: Temperature sensors

### Switch

The switch uses the power-override feature to operate the device like a switch.
Turning the switch on will allow the device to use as much power as the `load_nominal_power` reports.
Note that power-override deliberately takes precedence over power-excess.

### Water Heater

For the water heater entity to be added the device must be in one of the warm water modes.

## Services

For now, please refer to the [services.yaml](custom_components/acthor/services.yaml) file for information about the available services.

## Limitations

The `load_nominal_power` isn't perfectly accurate which means that the switch might not provide full power.

Devices only seem to use about half of their allocated power.
The integration compensates for this by multiplying the value by 2 before writing it to the device.
