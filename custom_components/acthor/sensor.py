from homeassistant.const import STATE_UNKNOWN
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

    async def async_update(self) -> None:
        self._state = self._device.status.name

        for sensor, temp in self._device.temperatures.items():
            self._attrs[f"temp_sensor_{sensor}"] = temp
