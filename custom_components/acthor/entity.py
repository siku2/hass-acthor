from typing import Optional

from homeassistant.helpers.entity import Entity

from .acthor import ACThor


class ACThorEntity(Entity):
    def __init__(self, device: ACThor, device_info: dict, *, sensor_type: str) -> None:
        super().__init__()
        self._device = device
        self._device_info = device_info

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
