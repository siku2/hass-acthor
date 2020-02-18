import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType, HomeAssistantType, ServiceCallType

from .acthor import ACThor

__all__ = ["DOMAIN", "Component", "get_component"]

logger = logging.getLogger(__name__)

DOMAIN = "acthor"
DATA_ACTHOR = "data_acthor"

CONF_POWER_ENTITY_ID = "power_entity_id"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default="AC•THOR"): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)

ATTR_POWER = "power"
ATTR_OVERRIDE = "override"

SERVICE_ACTIVATE_BOOST = "activate_boost"
SERVICE_ACTIVATE_BOOST_SCHEMA = vol.Schema({})
SERVICE_SET_POWER = "set_power"
SERVICE_SET_POWER_SCHEMA = vol.Schema({
    vol.Required(ATTR_POWER): cv.positive_int,
    vol.Optional(ATTR_OVERRIDE, default=False): cv.boolean,
})


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    acthor_config: ConfigType = config[DOMAIN]
    component = hass.data[DATA_ACTHOR] = await Component.load(hass, acthor_config)

    operation_mode = await component.device.operation_mode

    for platform in ("sensor", "switch"):
        await async_load_platform(hass, platform, DOMAIN, True, config)

    if operation_mode.has_ww:
        await async_load_platform(hass, "water_heater", DOMAIN, True, config)

    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry) -> None:
    component = get_component(hass)
    dev = component.device
    reg = dev.registers

    device_registry = await dr.async_get_registry(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, dev.serial_number)},
        manufacturer="my-PV",
        name=component.device_name,
        sw_version=".".join(await reg.get_control_firmware_version()),
    )


class Component:
    def __init__(self, hass: HomeAssistantType, device: ACThor, *,
                 device_name: str) -> None:
        self.hass = hass
        self.device = device
        self.device_name = device_name

        hass.services.async_register(DOMAIN, SERVICE_ACTIVATE_BOOST, self.__handle_activate_boost,
                                     SERVICE_ACTIVATE_BOOST_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_SET_POWER, self.__handle_set_power,
                                     SERVICE_SET_POWER_SCHEMA)

    @classmethod
    async def load(cls, hass: HomeAssistantType, config: ConfigType):
        device = await ACThor.connect(config[CONF_HOST])
        device.start()

        return cls(hass, device,
                   device_name=config[CONF_NAME])

    async def __handle_activate_boost(self, call: ServiceCallType) -> None:
        await self.device.trigger_boost()

    async def __handle_set_power(self, call: ServiceCallType) -> None:
        data = call.data
        power = int(data[ATTR_POWER])
        if data[ATTR_OVERRIDE]:
            await self.device.set_power_override(power)
        else:
            await self.device.set_power_excess(power)


def get_component(hass: HomeAssistantType) -> Component:
    return hass.data[DATA_ACTHOR]
