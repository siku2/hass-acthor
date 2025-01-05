import logging

import pymodbus.exceptions
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_MODE, CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.typing import ConfigType

from .acthor import ACThor, OverrideMode
from .config_flow import ACThorConfigFlow
from .const import ACTHOR_DATA, ATTR_OVERRIDE, ATTR_POWER, DOMAIN

__all__ = ["Component", "get_component"]

_ = ACThorConfigFlow

logger = logging.getLogger(__name__)

ATTR_DEVICE = "device"

SERVICE_BASE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE): cv.string,
    }
)

SERVICE_ACTIVATE_BOOST = "activate_boost"
SERVICE_ACTIVATE_BOOST_SCHEMA = SERVICE_BASE_SCHEMA.extend({})  # type: ignore

SERVICE_SET_POWER = "set_power"
SERVICE_SET_POWER_SCHEMA = SERVICE_BASE_SCHEMA.extend(  # type: ignore
    {
        vol.Required(ATTR_POWER): cv.positive_int,
        vol.Optional(ATTR_OVERRIDE, default=False): cv.boolean,
        vol.Optional(ATTR_MODE): OverrideMode.__call__,
    }
)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.WATER_HEATER]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def handle_activate_boost(call: ServiceCall) -> None:
        component = _get_component_by_sn(hass, call.data.get(ATTR_DEVICE))
        await component.handle_activate_boost(call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ACTIVATE_BOOST,
        handle_activate_boost,
        SERVICE_ACTIVATE_BOOST_SCHEMA,
    )

    async def handle_set_power(call: ServiceCall) -> None:
        component = _get_component_by_sn(hass, call.data.get(ATTR_DEVICE))
        await component.handle_set_power(call)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_POWER, handle_set_power, SERVICE_SET_POWER_SCHEMA
    )

    return True


_LOADED_ENTRIES: list[str] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = entry.data

    try:
        device: ACThor = await ACThor.connect(data[CONF_HOST])
    except pymodbus.exceptions.ConnectionException:
        raise ConfigEntryNotReady

    device.start()

    sw_version = await device.registers.get_control_firmware_version()

    device_info: DeviceInfo = {
        "identifiers": {(DOMAIN, device.serial_number)},
        "manufacturer": "my-PV",
        "name": data["name"],
        "sw_version": ".".join(map(str, sw_version)),
    }

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(config_entry_id=entry.entry_id, **device_info)

    get_components(hass)[entry.entry_id] = Component(hass, device, device_info)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        component = get_components(hass).pop(config_entry.entry_id)
        await component.shutdown()

    return unload_ok


class Component:
    def __init__(
        self,
        hass: HomeAssistant,
        device: ACThor,
        device_info: DeviceInfo,
    ) -> None:
        self.hass = hass
        self.device = device
        self.device_info = device_info

    @property
    def device_name(self) -> str:
        return self.device_info.get("name") or ""

    async def shutdown(self) -> None:
        self.device.stop()
        await self.device.registers.disconnect()

    async def handle_activate_boost(self, call: ServiceCall) -> None:
        await self.device.trigger_boost()

    async def handle_set_power(self, call: ServiceCall) -> None:
        data = call.data
        power = int(data[ATTR_POWER])
        if data[ATTR_OVERRIDE]:
            await self.device.set_power_override(power, mode=data.get(ATTR_MODE))
        else:
            await self.device.set_power_excess(power)


def get_components(hass: HomeAssistant) -> dict[str, Component]:
    ret: dict[str, Component]
    try:
        ret = hass.data[ACTHOR_DATA]
    except KeyError:
        ret = hass.data[ACTHOR_DATA] = {}
    return ret


def get_component(hass: HomeAssistant, entry_id: str) -> Component:
    return get_components(hass)[entry_id]


def _get_component_by_sn(hass: HomeAssistant, sn: str | None) -> Component:
    comps = get_components(hass)
    if sn is None:
        if len(comps) != 1:
            raise ValueError(
                "device serial number must be specified when there isn't exactly one device"
            )

        return next(iter(comps.values()))

    sn = str(sn)
    for c in comps.values():
        if c.device.serial_number == sn:
            return c

    raise ValueError("no device with serial number found")
