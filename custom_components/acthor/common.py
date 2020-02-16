from typing import Optional

from homeassistant.helpers.entity import Entity

from .acthor import ACThor


class ACThorEntity(Entity):
    _device: ACThor
    __name: Optional[str]

    def __init__(self, device: ACThor, *, name: str = None) -> None:
        self._device = device
        self.__name = name

    @property
    def available(self) -> bool:
        return self._device.available

    @property
    def name(self) -> Optional[str]:
        return self.__name

    @property
    def unique_id(self) -> str:
        # TODO need device type suffix
        return self._device.serial_number
