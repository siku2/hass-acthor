import asyncio
from typing import Optional

from homeassistant.components.water_heater import SUPPORT_OPERATION_MODE, WaterHeaterDevice
from homeassistant.const import STATE_OFF, STATE_ON, TEMP_CELSIUS
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import ACThor, get_component
from .entity import ACThorEntity

SUPPORT_FLAGS_HEATER = SUPPORT_OPERATION_MODE
SUPPORT_WATER_HEATER = [STATE_ON, STATE_OFF]


async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, add_entities, discovery_info=None) -> None:
    if discovery_info is None:
        return

    component = get_component(hass)
    entity = ACThorWaterHeater(component.device, name=component.device_name, temp_sensor=1)
    add_entities((entity,))


class ACThorWaterHeater(ACThorEntity, WaterHeaterDevice):
    def __init__(self, device: ACThor, *,
                 temp_sensor: int,
                 name: str = None) -> None:
        super().__init__(device, name=name, sensor_type="water_heater")

        self._min_temp = None
        self._max_temp = None
        self._temp_sensor = temp_sensor
        self._temp = None
        self._on = False

    @property
    def min_temp(self) -> Optional[float]:
        return self._min_temp

    @property
    def max_temp(self) -> Optional[float]:
        return self._max_temp

    @property
    def current_temperature(self) -> Optional[float]:
        return self._temp

    @property
    def current_operation(self) -> str:
        return STATE_ON if self._on else STATE_OFF

    @property
    def operation_list(self):
        return SUPPORT_WATER_HEATER

    @property
    def temperature_unit(self) -> str:
        return TEMP_CELSIUS

    @property
    def supported_features(self) -> int:
        return SUPPORT_FLAGS_HEATER

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        # TODO
        raise NotImplementedError

    async def async_update(self) -> None:
        dev = self._device
        reg = dev.registers

        self._min_temp, self._max_temp = await asyncio.gather(reg.ww1_min, reg.ww1_max)
        self._temp = dev.temperatures[self._temp_sensor]
        self._on = (await reg.power) > 0
