import asyncio
import logging
from typing import Awaitable, MutableMapping, Optional

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_POWER, POWER_WATT, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform

from .device import ACThor

logger = logging.getLogger(__name__)

CFG_HOST = "host"
CFG_NAME = "name"

DEFAULT_NAME = "AC•THOR"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CFG_HOST): cv.string,
    vol.Optional(CFG_NAME, default=DEFAULT_NAME): cv.string,
})


async def async_setup_platform(hass: HomeAssistant, config: dict, async_add_entities, discovery_info=None) -> bool:
    device = await ACThor.connect(config.get(CFG_HOST))
    serial_number = await device.get_serial_number()
    sensor = ACThorSensor(device, serial_number,
                          name=config.get(CFG_NAME))

    async_add_entities((sensor,))
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    platform: EntityPlatform = entity_platform.current_platform.get()
    platform.async_register_entity_service(
        "write_power",
        {
            vol.Required("value"): cv.time_period,
        },
        "write"
    )


# TODO services


class ACThorSensor(Entity):
    _device: ACThor
    _serial_number: str
    _name: Optional[str]

    _state: str
    _attrs: dict

    def __init__(self, device: ACThor, serial_number: str, *, name: str = None) -> None:
        self._device = device
        self._serial_number = serial_number
        self._name = name

        self._state = STATE_UNKNOWN
        self._attrs = {}

    @property
    def available(self) -> bool:
        return self._device.connected

    @property
    def device_state_attributes(self) -> dict:
        return self._attrs

    @property
    def name(self) -> Optional[str]:
        return self._name

    @property
    def unique_id(self) -> str:
        return self._serial_number

    @property
    def state(self) -> str:
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        return POWER_WATT

    @property
    def device_class(self) -> str:
        return DEVICE_CLASS_POWER

    async def __update_attrs(self) -> None:
        dev = self._device
        await awaitable_update_dict(
            self._attrs,
            status=dev.read_status(),

            temp1=dev.read_temp1(),
            temp2=dev.read_temp2(),
            temp3=dev.read_temp3(),
            temp4=dev.read_temp4(),
            temp5=dev.read_temp5(),
            temp6=dev.read_temp6(),
            temp7=dev.read_temp7(),
            temp8=dev.read_temp8(),
        )

    async def async_update(self) -> None:
        try:
            power = await self._device.read_power()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("error while reading power")
            self._state = STATE_UNKNOWN
        else:
            self._state = str(power)

        await self.__update_attrs()


async def awaitable_update_dict(d: MutableMapping, **kwargs: Awaitable) -> None:
    async def _set_key(key, aw):
        d[key] = await aw

    f_gen = (_set_key(key, aw) for key, aw in kwargs.items())
    await asyncio.gather(*f_gen)
