import datetime
import logging
import time
from typing import Any, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import HomeAssistantType

from . import get_component
from .acthor import ACThor
from .entity import ACThorEntity

logger = logging.getLogger(__name__)

SECS_IN_HOUR = 60 * 60


async def async_setup_entry(hass: HomeAssistantType, config_entry: ConfigEntry, add_entities):
    component = get_component(hass, config_entry.entry_id)
    add_entities((ACThorSwitch(component.device, component.device_info),))


class ACThorSwitch(ACThorEntity, SwitchEntity):
    def __init__(self, device: ACThor, device_info: dict) -> None:
        super().__init__(device, device_info, sensor_type="Switch")

        self._last_update = time.time()
        self._next_energy_reset = 0
        self._today_energy = 0

    @property
    def is_on(self) -> bool:
        return self._device.power_override > 0

    @property
    def current_power_w(self) -> Optional[float]:
        return self._device.power

    @property
    def today_energy_kwh(self) -> float:
        return round(self._today_energy, 3)

    @property
    def is_standby(self) -> bool:
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._device.set_power_override(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._device.set_power_override(False)

    def _reset_today_energy(self) -> None:
        self._today_energy = 0
        tomorrow = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        midnight = datetime.datetime.combine(tomorrow.date(), datetime.time(0, 0), tzinfo=tomorrow.tzinfo)
        self._next_energy_reset = midnight.timestamp()

    def _update_today_energy(self) -> None:
        now = time.time()
        diff = now - self._last_update
        self._last_update = now

        if now > self._next_energy_reset:
            self._reset_today_energy()

        power = self._device.power
        if not power:
            return
        watt_hours = power * diff / SECS_IN_HOUR
        self._today_energy += watt_hours / 1000

    async def on_device_update(self) -> None:
        self._update_today_energy()

    async def _handle_write_power(self, power: int) -> None:
        pass
