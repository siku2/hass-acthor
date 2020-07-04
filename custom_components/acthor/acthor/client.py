import abc
import asyncio
import enum
import functools
import logging
from typing import Callable, Dict, Iterable, Optional, Tuple, Union

from .event_target import EventTarget
# FIXME switch back to pymodbus once HomeAssistant uses a compatible version
from .pymodbus_vendor.client.asynchronous.asyncio import ModbusClientProtocol, ReconnectingAsyncioModbusTcpClient, \
    init_tcp_client
from .registers import ACThorRegistersMixin

logger = logging.getLogger(__name__)

# The port cannot be changed in the AC THOR
MODBUS_PORT = 502


def _add_made_connection_listener(client: ReconnectingAsyncioModbusTcpClient, listener: Callable) -> None:
    previous = client.protocol_made_connection

    @functools.wraps(previous)
    def wrapper(*args):
        previous(*args)
        listener()

    client.protocol_made_connection = wrapper


async def test_connection(host: str, port: int = MODBUS_PORT, *, timeout: int = None) -> bool:
    loop = asyncio.get_running_loop()
    conn_lost = asyncio.Event()
    protocol = asyncio.Protocol()
    protocol.connection_lost = lambda e: conn_lost.set()

    try:
        coro = loop.create_connection(lambda: protocol, host, port)
        transport, _ = await asyncio.wait_for(coro, timeout=timeout)
    except Exception:
        return False
    else:
        transport.close()
        await conn_lost.wait()
        return True


async def modbus_connect(host: str, port: int = MODBUS_PORT, *,
                         timeout: int = None) -> ReconnectingAsyncioModbusTcpClient:
    coro = init_tcp_client(None, None, host, port)
    client: ReconnectingAsyncioModbusTcpClient = await asyncio.wait_for(coro, timeout=timeout)

    return client


class ACThorRegistersMixinWithEvents(EventTarget, ACThorRegistersMixin, abc.ABC):
    __slots__ = ()


class ACThorRegisters(ACThorRegistersMixinWithEvents):
    __slots__ = ("_client", "_lock",
                 "_made_connection")

    def __init__(self, client: ReconnectingAsyncioModbusTcpClient) -> None:
        super().__init__()

        self._client = client
        _add_made_connection_listener(client, self._handle_made_connection)
        # FIXME lock here because pymodbus currently can't handle concurrent requests.
        #   see: https://github.com/riptideio/pymodbus/issues/475
        self._lock = asyncio.Lock()

        self._made_connection = asyncio.Event()

    @classmethod
    async def connect(cls, host: str = None, *, timeout: int = None):
        logger.info("connecting to %r", host)
        client = await modbus_connect(host, timeout=timeout)
        return cls(client)

    @property
    def available(self) -> bool:
        return self._client.connected

    def _handle_made_connection(self) -> None:
        self._made_connection.set()
        self.dispatch_event("connected")

    async def _get_protocol(self) -> ModbusClientProtocol:
        if self._client.protocol is None:
            logger.debug("no protocol, waiting for connection")
            self._made_connection.clear()
            await self._made_connection.wait()

        return self._client.protocol

    async def read_register(self, address: int) -> int:
        return (await self.read_registers(address, 1))[0]

    async def read_registers(self, address: int, count: int) -> Tuple[int, ...]:
        async with self._lock:
            protocol = await self._get_protocol()
            logger.debug("reading %r register(s) from %r", count, address)
            result = await protocol.read_holding_registers(address, count)

        # TODO error handling
        return tuple(result.registers)

    async def write_register(self, address: int, value: int) -> None:
        async with self._lock:
            protocol = await self._get_protocol()
            logger.debug("writing %r to register %r", value, address)
            await protocol.write_register(address, value)

    async def write_registers(self, address: int, values: Iterable[int]) -> None:
        async with self._lock:
            protocol = await self._get_protocol()
            logger.debug("writing %r to registers starting at %r",
                         values, address)
            await protocol.write_registers(address, values)

    async def disconnect(self) -> None:
        self._client.stop()


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
    def __init__(self, registers: ACThorRegistersMixinWithEvents, serial_number: str, *,
                 loop_interval: float = 5) -> None:
        super().__init__()
        self.registers = registers
        registers.add_listener("connected", self._on_connected)
        self.serial_number = serial_number

        self.__update_interval = loop_interval
        self.__update_loop_task: Optional[asyncio.Task] = None

        self._power_excess = 0
        self._power_override = 0
        self._override_mode = OverrideMode.OVERRIDE

        self._status: Optional[StatusCode] = None
        self._load_nominal_power: Optional[int] = None
        self._power: Optional[int] = None
        self._temps: Dict[int, float] = {}

    def __str__(self) -> str:
        return f"ACThor#{self.serial_number}"

    @classmethod
    async def connect(cls, host: str = None, *, timeout: int = None):
        registers = await ACThorRegisters.connect(host, timeout=timeout)
        sn = await registers.serial_number
        return cls(registers, sn)

    @property
    def _update_loop_running(self) -> bool:
        task = self.__update_loop_task
        return task is not None and not task.done()

    @property
    def available(self) -> bool:
        return self.registers.available

    @property
    async def operation_mode(self) -> OperationMode:
        return OperationMode(await self.registers.operation_mode)

    @property
    def status(self) -> Optional[StatusCode]:
        return self._status

    @property
    def power(self) -> Optional[int]:
        """Current power consumed by the device"""
        return self._power

    @property
    def load_nominal_power(self) -> Optional[int]:
        return self._load_nominal_power

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

    @property
    def temperatures(self) -> Dict[int, float]:
        return self._temps

    def __power_write(self, power: int) -> int:
        # TODO find out why ACTHOR only uses half the excess power.
        self.registers.power = int(1.8 * power)

    def start(self) -> None:
        logger.debug("%s: starting loop", self)
        assert not self._update_loop_running
        self.__update_loop_task = asyncio.create_task(self.__update_loop())

    def stop(self) -> None:
        assert self._update_loop_running
        self.__update_loop_task.cancel()

    async def _on_connected(self) -> None:
        logger.info("%s: reconnected", self)
        self.registers.power_timeout = 1.5 * self.__update_interval

    async def __read_update(self) -> None:
        self._status = StatusCode(await self.registers.status)
        self._power = await self.registers.power
        self._load_nominal_power = await self.registers.load_nominal_power

        self._temps.clear()
        for sensor, temp in enumerate(await self.registers.get_temps(), 1):
            if not temp:
                continue

            self._temps[sensor] = temp

    async def __write_update(self) -> None:
        self.__power_write(self.power_target)

    async def __update_loop(self) -> None:
        # on_connected isn't called for the initial connection.
        # To reach this point we MUST have connected at least once though.
        await self._on_connected()

        while True:
            logger.debug("running update")
            try:
                await self.__read_update()
                await self.__write_update()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("error while updating")
            else:
                await self.dispatch_event("after_update")

            await asyncio.sleep(self.__update_interval)

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

    async def set_power_override(self, watts: Union[bool, int], mode: Union[OverrideMode, str] = None) -> None:
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

        self._power_override = watts
        await self._force_update_power()

    async def trigger_boost(self) -> None:
        self.registers.boost_activate = 1
