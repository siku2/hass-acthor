from typing import Optional

from homeassistant.helpers.entity import Entity

from .acthor import ACThor


class ACThorEntity(Entity):
    def __init__(self, device: ACThor, *, sensor_type: str, name: str = None) -> None:
        super().__init__()
        self._device = device
        self._sensor_type = sensor_type
        self._unique_id = f"{self._device.serial_number}-{sensor_type}"
        self.__name = name

    @property
    def available(self) -> bool:
        return self._device.available

    @property
    def name(self) -> Optional[str]:
        return self.__name

    @property
    def unique_id(self) -> str:
        return self._unique_id
