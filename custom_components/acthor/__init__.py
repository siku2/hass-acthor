import logging

import voluptuous as vol
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from .acthor import ACThor

__all__ = ["DOMAIN", "DATA_ACTHOR"]

logger = logging.getLogger(__name__)

DOMAIN = "acthor"
DATA_ACTHOR = "data_acthor"

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_HOST): cv.string,
    }),
}, extra=vol.ALLOW_EXTRA)

ATTR_VALUE = "value"

WRITE_POWER_SCHEMA = vol.Schema({
    ATTR_ENTITY_ID: cv.entity_id,
    ATTR_VALUE: cv.positive_int,
})


async def async_setup(hass: HomeAssistantType, config: ConfigType) -> bool:
    acthor_config = config[DOMAIN]

    device = hass.data[DATA_ACTHOR] = await ACThor.connect(acthor_config[CONF_HOST])
    device.start()
    await async_load_platform(hass, "switch", DOMAIN, {}, config)

    return True
