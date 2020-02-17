import logging
import time
from typing import Any, Optional

from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import get_component
from .acthor import ACThor
from .common import ACThorEntity

logger = logging.getLogger(__name__)

SECS_IN_HOUR = 60 * 60


async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, add_entities, discovery_info=None) -> None:
    if discovery_info is None:
        return

    component = get_component(hass)
    entity = ACThorSwitch(component.device, name=component.device_name)
    add_entities((entity,))


class ACThorSwitch(ACThorEntity, SwitchDevice):
    def __init__(self, device: ACThor, *, name: str = None) -> None:
        super().__init__(device, name=name, sensor_type="switch")
        self._attrs = {}

        self._last_update = time.time()
        self._today_energy = 0
        # TODO reset after 1 day

    @property
    def device_state_attributes(self) -> dict:
        return self._attrs

    @property
    def is_on(self) -> bool:
        return self._device.power_override > 0

    @property
    def current_power_w(self) -> Optional[float]:
        return self._device.power

    @property
    def today_energy_kwh(self) -> float:
        return round(self._today_energy, 1)

    @property
    def is_standby(self) -> bool:
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._device.set_power_override(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.set_power_override(False)

    def _update_today_energy(self) -> None:
        now = time.time()
        diff = now - self._last_update
        self._last_update = now

        power = self._device.power
        if not power:
            return
        watt_hours = power * diff / SECS_IN_HOUR
        self._today_energy += watt_hours / 1000

    async def async_update(self) -> None:
        self._update_today_energy()

        attrs = self._attrs
        attrs["status"] = self._device.status
        attrs["load_nominal_power"] = self._device.load_nominal_power or 0

        for sensor, temp in self._device.temperatures.items():
            attrs[f"temperature_{sensor}"] = temp
