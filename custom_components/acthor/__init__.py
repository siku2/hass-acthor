import logging

import voluptuous as vol
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.helpers import config_validation as cv
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

PLATFORMS = ("sensor", "switch", "water_heater")


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    acthor_config: ConfigType = config[DOMAIN]
    hass.data[DATA_ACTHOR] = await Component.load(hass, acthor_config)

    for platform in PLATFORMS:
        await async_load_platform(hass, platform, DOMAIN, {}, config)

    return True


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
