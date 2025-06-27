# AC•THOR Home Assistant Integration


> [!IMPORTANT]  
> This integration is very old and hasn't really been kept up to date with modern Home Assistant standards.
>
> Check out the [mypv integration by @dneprojects](https://github.com/dneprojects/mypv).
>
> One major difference is that it uses the REST API rather than connecting over Modbus.

[![GitHub Release](https://img.shields.io/github/release/siku2/hass-acthor.svg?style=flat-square)](https://github.com/siku2/hass-acthor/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz/docs/faq/custom_repositories)

[![License](https://img.shields.io/github/license/siku2/hass-acthor.svg?style=flat-square)](LICENSE)
[![GitHub Activity](https://img.shields.io/github/commit-activity/y/siku2/hass-acthor.svg?style=flat-square)](https://github.com/siku2/hass-acthor/commits/main)

Home Assistant integration for my-PV's AC•THOR.

## Disclaimer

AC•THOR only supports one active connection.
It's impossible to connect to the device while another connection is active.

If you want to control it through another device you need to add them both to Home Assistant and use an automation to call the `acthor.set_power` service.

Please be aware that I can't guarantee that this will work well for your use case.
I'm trying to make it work for all possible use cases but because of the poor documentation on AC•THOR's side some features might not work as expected.

Don't hesitate to open an issue if something seems off.

## Installation

Make sure you have [HACS](https://hacs.xyz) installed.

1. Add this repository as a custom repository to HACS: [![Add Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=siku2&repository=hass-acthor&category=integration)
2. Use HACS to install the integration.
3. Restart Home Assistant.
4. Set up the integration using the UI: [![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=acthor)

## Contributions are welcome

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

### Providing translations for other languages

[![GitLocalize](https://gitlocalize.com/repo/9429/whole_project/badge.svg)](https://gitlocalize.com/repo/9429)

If you would like to use the integration in another language, you can help out by providing the necessary translations.

[Head over to **GitLocalize** to start translating.](https://gitlocalize.com/repo/9429)

If your desired language isn't available there, just open an issue to request it.

You can also just do the translations manually in [custom_components/acthor/translations/](./custom_components/acthor/translations/) and open a pull request with the changes.

## Limitations

The `load_nominal_power` isn't perfectly accurate which means that the switch might not provide full power.

Devices only seem to use about half of their allocated power.
The integration compensates for this by multiplying the value by 2 before writing it to the device.
