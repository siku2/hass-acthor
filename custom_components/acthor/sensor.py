import asyncio
import logging
from typing import Awaitable, MutableMapping

from homeassistant.const import DEVICE_CLASS_POWER, POWER_WATT, STATE_UNKNOWN

from .acthor import ACThor
from .common import ACThorEntity

logger = logging.getLogger(__name__)


class ACThorSensor(ACThorEntity):
    _state: str
    _attrs: dict

    def __init__(self, device: ACThor, *, name: str = None) -> None:
        super().__init__(device, name=name)

        self._state = STATE_UNKNOWN
        self._attrs = {}

    @property
    def device_state_attributes(self) -> dict:
        return self._attrs

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
        await awaitable_update_dict(
            self._attrs,
        )

    async def async_update(self) -> None:
        try:
            power = await self._device.get_power()
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
