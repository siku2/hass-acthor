import abc
import asyncio
import enum
import logging
import typing

import pymodbus.exceptions
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu.register_read_message import ReadHoldingRegistersResponse

from .event_target import EventTarget
from .registers import ACThorRegistersMixin

logger = logging.getLogger(__name__)

# The port cannot be changed in the AC THOR
MODBUS_PORT = 502


async def test_connection(host: str, *, timeout: float | None = None) -> bool:
    client = AsyncModbusTcpClient(host, port=MODBUS_PORT, timeout=timeout or 3.0)
    try:
        return await client.connect()
    except Exception:
        return False
    finally:
        client.close()


class ACThorRegistersMixinWithEvents(EventTarget, ACThorRegistersMixin, abc.ABC):
    __slots__ = ()

    async def disconnect(self) -> None: ...


class ACThorRegisters(ACThorRegistersMixinWithEvents):
    __slots__ = ("_client", "_lock")

    def __init__(self, client: AsyncModbusTcpClient) -> None:
        super().__init__()

        self._client = client
        # FIXME lock here because pymodbus currently can't handle concurrent requests.
        #   see: https://github.com/riptideio/pymodbus/issues/475
        self._lock = asyncio.Lock()

    @classmethod
    async def connect(cls, host: str, *, timeout: float | None = None):
        logger.info("connecting to %r", host)
        client = AsyncModbusTcpClient(host, port=MODBUS_PORT, timeout=timeout or 3.0)
        if not await client.connect():
            raise pymodbus.exceptions.ConnectionException("not connected")
        return cls(client)

    @property
    def available(self) -> bool:
        return self._client.connected

    async def read_register(self, address: int) -> int:
        return (await self.read_registers(address, 1))[0]

    async def read_registers(self, address: int, count: int) -> tuple[int, ...]:
        async with self._lock:
            logger.debug("reading %r register(s) from %r", count, address)
            tmp = self._client.read_holding_registers(address, count=count)
            result = await typing.cast(
                typing.Awaitable[ReadHoldingRegistersResponse], tmp
            )
        return tuple(result.registers)

    async def write_register(self, address: int, value: int) -> None:
        async with self._lock:
            logger.debug("writing %r to register %r", value, address)
            tmp = self._client.write_register(address, value)
            await typing.cast(typing.Awaitable[None], tmp)

    async def write_registers(self, address: int, values: list[int]) -> None:
        async with self._lock:
            logger.debug("writing %r to registers starting at %r", values, address)
            tmp = self._client.write_registers(address, values)  # type: ignore
            await typing.cast(typing.Awaitable[None], tmp)

    async def disconnect(self) -> None:
        self._client.close()


class StatusCode(int):
    @property
    def is_off(self) -> bool:
        return self == 0

    @property
    def is_startup(self) -> bool:
        return 1 <= self <= 8

    @property
    def is_operation(self) -> bool:
        return 9 <= self < 200

    @property
    def is_error(self) -> bool:
        return self >= 200

    @property
    def name(self) -> str:
        if self.is_off:
            return "off"
        elif self.is_startup:
            return "starting"
        elif self.is_operation:
            return "on"
        elif self.is_error:
            return "error"
        else:
            return "unknown"


class OperationState(enum.IntEnum):
    WAITING_FOR_EXCESS = 0
    HEATING_WITH_EXCESS = 1
    BOOST_BACKUP = 2
    TEMPERATURE_REACHED = 3
    NO_CONTROL_SIGNAL = 4
    # TODO not documented?
    RED_CROSS_FLASHES = 5


class BoostMode(enum.IntEnum):
    OFF = 0
    ON = 1
    RELAY_BOOST_ON = 3

    @property
    def is_on(self) -> bool:
        return self is not self.OFF


class OperationMode(enum.IntEnum):
    WW_3KW = 1
    WW_LAYER = 2
    WW_6KW = 3
    WW_AND_PUMP = 4
    WW_AND_HEATING = 5
    HEATING = 6
    WW_AND_PWM = 7
    FREQ_MODE = 8

    @property
    def single_mode(self) -> bool:
        return self not in (self.WW_AND_PUMP, self.WW_AND_HEATING, self.WW_AND_PWM)

    @property
    def has_ww(self) -> bool:
        return self.WW_3KW <= self <= self.WW_AND_HEATING or self == self.WW_AND_PWM

    @property
    def has_heating(self) -> bool:
        return self in (self.HEATING, self.WW_AND_HEATING)


class OverrideMode(enum.Enum):
    OVERRIDE = "override"
    REPLACE = "replace"
    MINIMUM = "minimum"


class ACThor(EventTarget):
    def __init__(
        self,
        registers: ACThorRegistersMixinWithEvents,
        serial_number: str,
        *,
        loop_interval: float = 5,
    ) -> None:
        super().__init__()
        self.registers = registers
        registers.add_listener("connected", self._on_connected)
        self.serial_number = serial_number

        self.__update_interval = loop_interval
        self.__slow_update_interval = max(60, loop_interval)
        self.__run_loop_task: asyncio.Task[None] | None = None

        self._power_excess = 0
        self._power_override = 0
        self._override_mode = OverrideMode.OVERRIDE

        self.status: StatusCode | None = None
        self.load_nominal_power: int | None = None
        self.relay1_status = 0
        self.power: int | None = None
        self.temperatures: dict[int, float] = {}

    def __str__(self) -> str:
        return f"ACThor#{self.serial_number}"

    @classmethod
    async def connect(cls, host: str, *, timeout: int | None = None):
        registers = await ACThorRegisters.connect(host, timeout=timeout)
        sn = await registers.serial_number
        return cls(registers, sn)

    @property
    def _run_loop_running(self) -> bool:
        task = self.__run_loop_task
        return task is not None and not task.done()

    @property
    def available(self) -> bool:
        return self.registers.available

    @property
    async def operation_mode(self) -> OperationMode:
        return OperationMode(await self.registers.operation_mode)

    @property
    def power_excess(self) -> int:
        """Current power excess sent to the device."""
        return self._power_excess

    @property
    def power_override(self) -> int:
        return self._power_override

    @property
    def override_mode(self) -> OverrideMode:
        return self._override_mode

    @property
    def power_target(self) -> int:
        mode = self._override_mode

        if mode == OverrideMode.REPLACE:
            return self._power_override

        if mode == OverrideMode.MINIMUM:
            return max(self._power_override, self._power_excess)

        # default is OVERRIDE
        return self._power_override or self._power_excess

    def __power_write(self, power: int) -> None:
        # TODO find out why ACTHOR only uses half the excess power.
        self.registers.power = int(power)

    def start(self) -> None:
        logger.debug("%s: starting loop", self)
        assert not self._run_loop_running
        self.__run_loop_task = asyncio.create_task(self.__run_loop())

    def stop(self) -> None:
        assert self.__run_loop_task
        self.__run_loop_task.cancel()

    async def _on_connected(self) -> None:
        logger.info("%s: reconnected", self)
        self.registers.power_timeout = max(round(1.5 * self.__slow_update_interval), 10)

    async def __slow_update_once(self) -> None:
        self.status = StatusCode(await self.registers.status)
        self.load_nominal_power = int(await self.registers.load_nominal_power)
        self.relay1_status = bool(await self.registers.relay1_status)

        self.temperatures.clear()
        for sensor, temp in enumerate(await self.registers.get_temps(), 1):
            if not temp:
                continue
            self.temperatures[sensor] = temp

    async def __update_once(self) -> None:
        self.power = int(await self.registers.power)
        self.__power_write(self.power_target)

    async def __run_loop(self) -> None:
        async def _run_update_fn(
            fn: typing.Callable[[], typing.Awaitable[None]],
        ) -> bool:
            try:
                await fn()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("error while updating (%s)", fn)
            else:
                return True

            return False

        async def update_loop() -> None:
            while True:
                logger.debug("running update")
                if await _run_update_fn(self.__update_once):
                    await self.dispatch_event("after_update")
                await asyncio.sleep(self.__update_interval)

        async def slow_update_loop() -> None:
            while True:
                logger.debug("running slow update")
                await _run_update_fn(self.__slow_update_once)
                await asyncio.sleep(self.__slow_update_interval)

        # on_connected isn't called for the initial connection.
        # To reach this point we MUST have connected at least once though.
        await self._on_connected()
        await asyncio.gather(update_loop(), slow_update_loop())

    async def _force_update_power(self) -> None:
        power = self.power_target
        self.__power_write(power)
        _ = self.dispatch_event("after_write_power", power)

    async def set_power_excess(self, watts: int) -> None:
        """Set the current power excess.

        If the client is running (`start` has been called) this value will be
        kept and sent to the device until it is updated by another call to this
        function.

        `power_override` takes precedence over this!

        Args:
            watts: Amount of power in watts.
        """
        self._power_excess = watts
        await self._force_update_power()

    async def set_power_override(
        self, watts: bool | int, mode: OverrideMode | str | None = None
    ) -> None:
        """Set the power override.

        The override mode determines how the value is used:
        `OVERRIDE`: Used instead of the excess power if it isn't 0.
        `REPLACE`: Excess power is ignored entirely even if the override value is 0.
        `MINIMUM`: The bigger value between excess and override is used.

        Args:
            watts: Amount of power in watts.
                `True` is short for granting the 'load nominal power'.
                `False` is 0.
            mode: Override mode. If `None`, the current value is kept.
        """
        if watts is True:
            nominal_power = await self.registers.load_nominal_power
            # nominal power also isn't very accurate.
            watts = int(1.25 * nominal_power) if nominal_power else 1000
        elif watts is False:
            watts = 0

        if mode is not None:
            self._override_mode = OverrideMode(mode)

        self._power_override = int(watts)
        await self._force_update_power()

    async def trigger_boost(self) -> None:
        self.registers.boost_activate = 1
