from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_POWER, POWER_WATT, STATE_UNKNOWN
from homeassistant.helpers.typing import HomeAssistantType

from . import ACThor, get_component
from .entity import ACThorEntity


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, add_entities):
    component = get_component(hass)
    add_entities((ACThorSensor(component.device, component.device_info),))


class ACThorSensor(ACThorEntity):
    def __init__(self, device: ACThor, device_info: dict) -> None:
        super().__init__(device, device_info, sensor_type="Sensor")
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

    async def _handle_write_power(self, power: int) -> None:
        self._state = str(power)
        self._attrs["power_target"] = self._device.power_target

        self.async_schedule_update_ha_state()

    async def on_device_update(self) -> None:
        dev = self._device
        reg = dev.registers

        self._state = str(dev.power)

        attrs = self._attrs
        attrs["status"] = dev.status.name
        attrs["status_code"] = dev.status
        attrs["power_target"] = dev.power_target
        attrs["load_nominal_power"] = dev.load_nominal_power or 0
        attrs["temp_internal"] = await reg.tempchip

        for sensor, temp in dev.temperatures.items():
            attrs[f"temp_sensor_{sensor}"] = temp
