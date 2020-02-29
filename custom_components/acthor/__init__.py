import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_MODE, CONF_HOST
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceCallType

from .acthor import ACThor, OverrideMode
from .config_flow import ACThorConfigFlow
from .const import ACTHOR_DATA, ATTR_OVERRIDE, ATTR_POWER, DEVICE_NAME, DOMAIN

__all__ = ["Component",
           "get_component"]

_ = ACThorConfigFlow

logger = logging.getLogger(__name__)

SERVICE_ACTIVATE_BOOST = "activate_boost"
SERVICE_ACTIVATE_BOOST_SCHEMA = vol.Schema({})

SERVICE_SET_POWER = "set_power"
SERVICE_SET_POWER_SCHEMA = vol.Schema({
    vol.Required(ATTR_POWER): cv.positive_int,
    vol.Optional(ATTR_OVERRIDE, default=False): cv.boolean,
    vol.Optional(ATTR_MODE, default=None): cv.enum(OverrideMode),
})


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    return True


_LOADED_ENTRIES = []


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> bool:
    data = entry.data

    device: ACThor = await ACThor.connect(data[CONF_HOST])
    device.start()

    sw_version = await device.registers.get_control_firmware_version()

    device_info = {
        "config_entry_id": entry.entry_id,
        "identifiers": {(DOMAIN, device.serial_number)},
        "manufacturer": "my-PV",
        "name": data["name"],
        "sw_version": ".".join(map(str, sw_version))
    }

    hass.data[ACTHOR_DATA] = Component(hass, device, device_info)

    for domain in ("sensor", "switch"):
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, domain))
        _LOADED_ENTRIES.append(domain)

    operation_mode = await device.operation_mode
    if operation_mode.has_ww:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "water_heater"))
        _LOADED_ENTRIES.append("water_heater")

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(**device_info)
    return True


async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigEntry) -> bool:
    for domain in _LOADED_ENTRIES:
        await hass.config_entries.async_forward_entry_unload(config_entry, domain)
    _LOADED_ENTRIES.clear()

    await get_component(hass).shutdown()
    return True


class Component:
    def __init__(self, hass: HomeAssistantType, device: ACThor, device_info: dict) -> None:
        self.hass = hass
        self.device = device
        self.device_info = device_info

        hass.services.async_register(DOMAIN, SERVICE_ACTIVATE_BOOST, self.__handle_activate_boost,
                                     SERVICE_ACTIVATE_BOOST_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_SET_POWER, self.__handle_set_power,
                                     SERVICE_SET_POWER_SCHEMA)

    @property
    def device_name(self) -> str:
        return self.device_info["name"]

    async def shutdown(self) -> None:
        self.device.stop()
        await self.device.registers.disconnect()

    async def __handle_activate_boost(self, call: ServiceCallType) -> None:
        await self.device.trigger_boost()

    async def __handle_set_power(self, call: ServiceCallType) -> None:
        data = call.data
        power = int(data[ATTR_POWER])
        if data[ATTR_OVERRIDE]:
            await self.device.set_power_override(power, mode=data.get(ATTR_MODE))
        else:
            await self.device.set_power_excess(power)


def get_component(hass: HomeAssistantType) -> Component:
    # TODO use component on a per-device level.
    return hass.data[ACTHOR_DATA]
