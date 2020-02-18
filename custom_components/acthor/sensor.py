from homeassistant.const import DEVICE_CLASS_POWER, POWER_WATT, STATE_OFF, STATE_UNKNOWN
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import ACThor, get_component
from .common import ACThorEntity


async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, add_entities, discovery_info=None) -> None:
    if discovery_info is None:
        return

    component = get_component(hass)
    entity = ACThorSensor(component.device, name=component.device_name)
    add_entities((entity,))


class ACThorSensor(ACThorEntity):
    def __init__(self, device: ACThor, *, name: str = None) -> None:
        super().__init__(device, name=name, sensor_type="sensor")
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

    async def async_update(self) -> None:
        dev = self._device
        reg = dev.registers

        power_target = dev.power_target
        if power_target:
            self._state = str(power_target)
        else:
            self._state = STATE_OFF

        attrs = self._attrs
        attrs["status"] = dev.status
        attrs["power_target"] = dev.power_target
        attrs["load_nominal_power"] = dev.load_nominal_power or 0
        attrs["temp_internal"] = await reg.tempchip

        for sensor, temp in dev.temperatures.items():
            attrs[f"temp_sensor_{sensor}"] = temp
