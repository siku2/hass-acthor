import asyncio

from homeassistant.components.water_heater import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, TEMP_CELSIUS
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import HomeAssistantType

from . import ACThor, get_component
from .entity import ACThorEntity


async def async_setup_entry(
    hass: HomeAssistantType, config_entry: ConfigEntry, add_entities
):
    component = get_component(hass, config_entry.entry_id)
    add_entities(
        (ACThorWaterHeater(component.device, component.device_info, temp_sensor=1),)
    )


class ACThorWaterHeater(ACThorEntity, WaterHeaterEntity):
    def __init__(
        self, device: ACThor, device_info: DeviceInfo, *, temp_sensor: int
    ) -> None:
        super().__init__(device, device_info, sensor_type="Water Heater")

        self._min_temp = None
        self._max_temp = None
        self._temp_sensor = temp_sensor
        self._temp = None
        self._on: bool = False

    @property
    def min_temp(self) -> float:
        return self._min_temp or 0.0

    @property
    def max_temp(self) -> float:
        return self._max_temp or 0.0

    @property
    def current_temperature(self) -> float | None:
        return self._temp

    @property
    def current_operation(self) -> str:
        return STATE_ON if self._on else STATE_OFF

    @property
    def temperature_unit(self) -> str:
        return TEMP_CELSIUS

    @property
    def supported_features(self) -> WaterHeaterEntityFeature:
        return WaterHeaterEntityFeature.TARGET_TEMPERATURE

    async def async_set_temperature(self, **kwargs) -> None:
        reg = self._device.registers

        try:
            low = kwargs[ATTR_TARGET_TEMP_LOW]
        except KeyError:
            pass
        else:
            reg.ww1_min = float(low)

        try:
            high = kwargs[ATTR_TARGET_TEMP_HIGH]
        except KeyError:
            pass
        else:
            reg.ww1_max = float(high)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        raise NotImplementedError

    async def on_device_update(self) -> None:
        dev = self._device
        reg = dev.registers

        self._min_temp, self._max_temp = await asyncio.gather(reg.ww1_min, reg.ww1_max)
        self._temp = dev.temperatures[self._temp_sensor]
        self._on = (dev.power or 0) > 0

    async def _handle_write_power(self, power: int) -> None:
        pass
