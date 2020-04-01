import logging
from typing import Dict, Optional

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

ATTR_DEVICE = "device"

SERVICE_BASE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_DEVICE): cv.string,
})

SERVICE_ACTIVATE_BOOST = "activate_boost"
SERVICE_ACTIVATE_BOOST_SCHEMA = SERVICE_BASE_SCHEMA.extend({})

SERVICE_SET_POWER = "set_power"
SERVICE_SET_POWER_SCHEMA = SERVICE_BASE_SCHEMA.extend({
    vol.Required(ATTR_POWER): cv.positive_int,
    vol.Optional(ATTR_OVERRIDE, default=False): cv.boolean,
    vol.Optional(ATTR_MODE): OverrideMode.__call__,
})


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    async def handle_activate_boost(call: ServiceCallType) -> None:
        component = _get_component_by_sn(hass, call.data.get(ATTR_DEVICE))
        await component.handle_activate_boost(call)

    hass.services.async_register(DOMAIN, SERVICE_ACTIVATE_BOOST, handle_activate_boost, SERVICE_ACTIVATE_BOOST_SCHEMA)

    async def handle_set_power(call: ServiceCallType) -> None:
        component = _get_component_by_sn(hass, call.data.get(ATTR_DEVICE))
        await component.handle_set_power(call)

    hass.services.async_register(DOMAIN, SERVICE_SET_POWER, handle_set_power, SERVICE_SET_POWER_SCHEMA)

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

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(**device_info)

    get_components(hass)[entry.entry_id] = Component(hass, device, device_info)

    for domain in ("sensor", "switch"):
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, domain))
        _LOADED_ENTRIES.append(domain)

    operation_mode = await device.operation_mode
    if operation_mode.has_ww:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(entry, "water_heater"))
        _LOADED_ENTRIES.append("water_heater")

    return True


async def async_unload_entry(hass: HomeAssistantType, config_entry: ConfigEntry) -> bool:
    for domain in _LOADED_ENTRIES:
        await hass.config_entries.async_forward_entry_unload(config_entry, domain)
    _LOADED_ENTRIES.clear()

    component = get_components(hass).pop(config_entry.entry_id)
    await component.shutdown()

    return True


class Component:
    def __init__(self, hass: HomeAssistantType, device: ACThor, device_info: dict) -> None:
        self.hass = hass
        self.device = device
        self.device_info = device_info

    @property
    def device_name(self) -> str:
        return self.device_info["name"]

    async def shutdown(self) -> None:
        self.device.stop()
        await self.device.registers.disconnect()

    async def handle_activate_boost(self, call: ServiceCallType) -> None:
        await self.device.trigger_boost()

    async def handle_set_power(self, call: ServiceCallType) -> None:
        data = call.data
        power = int(data[ATTR_POWER])
        if data[ATTR_OVERRIDE]:
            await self.device.set_power_override(power, mode=data.get(ATTR_MODE))
        else:
            await self.device.set_power_excess(power)


def get_components(hass: HomeAssistantType) -> Dict[str, Component]:
    try:
        ret = hass.data[ACTHOR_DATA]
    except KeyError:
        ret = hass.data[ACTHOR_DATA] = {}
    return ret


def get_component(hass: HomeAssistantType, entry_id: str) -> Component:
    return get_components(hass)[entry_id]


def _get_component_by_sn(hass: HomeAssistantType, sn: Optional[str]) -> Component:
    comps = get_components(hass)
    if sn is None:
        if len(comps) != 1:
            raise ValueError("device serial number must be specified when there isn't exactly one device")

        return next(iter(comps.values()))

    sn = str(sn)
    for c in comps.values():
        if c.device.serial_number == sn:
            return c

    raise ValueError("no device with serial number found")
