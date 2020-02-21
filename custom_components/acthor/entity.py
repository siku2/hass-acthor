import abc
import logging
from typing import Optional

from homeassistant.helpers.entity import Entity

from .acthor import ACThor

logger = logging.getLogger(__name__)


class ACThorEntity(Entity, abc.ABC):
    def __init__(self, device: ACThor, device_info: dict, *, sensor_type: str) -> None:
        super().__init__()
        self._device = device
        self._device_info = device_info

        self._unsubscribe_calls = []

        self.__unique_id = f"{self._device.serial_number}-{sensor_type}"
        device_name = self._device_info["name"]
        self.__name = f"{device_name} {sensor_type}"

    @property
    def available(self) -> bool:
        return self._device.available

    @property
    def name(self) -> Optional[str]:
        return self.__name

    @property
    def unique_id(self) -> str:
        return self.__unique_id

    @property
    def device_info(self) -> Optional[dict]:
        return self._device_info

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        unsub = self._device.add_listener("after_update", self.__handle_device_update)
        self._unsubscribe_calls.append(unsub)

    async def async_will_remove_from_hass(self) -> None:
        for unsub in self._unsubscribe_calls:
            unsub()

        self._unsubscribe_calls.clear()

    async def __handle_device_update(self) -> None:
        try:
            await self.on_device_update()
        except Exception:
            logger.exception("%s failed to handle device update", type(self))
        else:
            self.async_schedule_update_ha_state()

    @abc.abstractmethod
    async def on_device_update(self) -> None:
        ...
