import logging
import time
from typing import Any, Optional

from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.typing import ConfigType, HomeAssistantType

from . import DATA_ACTHOR
from .acthor import ACThor
from .common import ACThorEntity

logger = logging.getLogger(__name__)

SECS_IN_HOUR = 60 * 60


async def async_setup_platform(hass: HomeAssistantType, config: ConfigType, add_entities, discovery_info=None) -> None:
    if discovery_info is None:
        return

    device = hass.data[DATA_ACTHOR]
    add_entities((ACThorSwitch(device),))

class ACThorSwitch(ACThorEntity, SwitchDevice):
    def __init__(self, device: ACThor, *, name: str = None) -> None:
        super().__init__(device, name=name)

        self._current_power = None
        self._last_update = time.time()
        self._today_energy = 0

    @property
    def is_on(self) -> bool:
        power = self._current_power
        return power is not None and power > 0

    @property
    def current_power_w(self) -> Optional[float]:
        return self._current_power

    @property
    def today_energy_kwh(self) -> float:
        return self._today_energy

    @property
    def is_standby(self) -> bool:
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._device.set_power(5000)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.set_power(0)

    def _update_today_energy(self) -> None:
        now = time.time()
        diff = self._last_update - now
        self._last_update = now

        watt_hours = self._current_power * diff / SECS_IN_HOUR
        self._today_energy += watt_hours / 1000

    async def async_update(self) -> None:
        dev = self._device
        reg = dev.registers

        self._current_power = await dev.get_power()

        self._update_today_energy()
