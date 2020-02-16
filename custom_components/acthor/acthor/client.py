import asyncio
import enum
import functools
import logging
from typing import Callable, Dict, Iterable, Optional, Tuple, Union

from pymodbus.client.asynchronous.asyncio import ModbusClientProtocol, ReconnectingAsyncioModbusTcpClient, \
    init_tcp_client

from .registers import ACThorRegistersMixin

__all__ = ["ACThorRegisters", "ACThor",
           "OperationState"]

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


class ACThorRegisters(ACThorRegistersMixin):
    __slots__ = ("_client", "_lock",
                 "_made_connection")

    def __init__(self, client: ReconnectingAsyncioModbusTcpClient) -> None:
        self._client = client
        _add_made_connection_listener(client, self._handle_made_connection)
        # FIXME lock here because pymodbus currently can't handle concurrent requests.
        #   see: https://github.com/riptideio/pymodbus/issues/475
        self._lock = asyncio.Lock()

        self._made_connection = asyncio.Event()

    @classmethod
    async def connect(cls, host: str = None):
        logger.info("connecting to %r", host)
        client = await init_tcp_client(None, None, host, MODBUS_PORT)
        return cls(client)

    @property
    def available(self) -> bool:
        return self._client.connected

    def _handle_made_connection(self) -> None:
        self._made_connection.set()

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
            logger.debug("writing %r to registers starting at %r", values, address)
            await protocol.write_registers(address, values)


class OperationState(enum.IntEnum):
    WAITING_FOR_EXCESS = 0
    HEATING_WITH_EXCESS = 1
    BOOST_BACKUP = 2
    TEMPERATURE_REACHED = 3
    NO_CONTROL_SIGNAL = 4
    # TODO not documented?
    RED_CROSS_FLASHES = 5


class ACThor:
    def __init__(self, registers: ACThorRegistersMixin, serial_number: str, *,
                 loop_interval: float = 20) -> None:
        self.registers = registers
        self.serial_number = serial_number

        self.__update_interval = loop_interval
        self.__update_loop_task: Optional[asyncio.Task] = None

        self._power_excess = 0
        self._power_override = 0

        self._status: Optional[int] = None
        self._load_nominal_power: Optional[int] = None
        self._power: Optional[int] = None
        self._temps: Dict[int, float] = {}

    @classmethod
    async def connect(cls, host: str = None):
        registers = await ACThorRegisters.connect(host)
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
    def status(self) -> Optional[int]:
        return self._status

    @property
    def power(self) -> Optional[int]:
        return self._power

    @property
    def power_excess(self) -> int:
        return self._power_excess

    @property
    def power_override(self) -> int:
        return self._power_override

    @property
    def temperatures(self) -> Dict[int, float]:
        return self._temps

    def start(self) -> None:
        assert not self._update_loop_running
        self.__update_loop_task = asyncio.create_task(self.__update_loop())

    def stop(self) -> None:
        assert self._update_loop_running
        self.__update_loop_task.cancel()

    async def __read_update(self) -> None:
        self._status = await self.registers.status
        self._power = await self.registers.power
        self._load_nominal_power = await self.registers.load_nominal_power

        self._temps.clear()
        for sensor, temp in enumerate(await self.registers.get_temps(), 1):
            if not temp:
                continue

            self._temps[sensor] = temp

    async def __write_update(self) -> None:
        power = self._power_override or self._power_excess
        if power:
            self.registers.power = power

    async def __update_loop(self) -> None:
        update_interval = self.__update_interval
        self.registers.power_timeout = 1.5 * update_interval

        while True:
            logger.debug("running update")
            try:
                await self.__read_update()
                await self.__write_update()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("error while updating")

            await asyncio.sleep(update_interval)

    def _write_power(self, watts: int) -> None:
        self.registers.power = watts

        if self._load_nominal_power is None:
            actual_power = watts
        else:
            actual_power = min(watts, self._load_nominal_power)

        self._power = actual_power

    async def set_power_excess(self, watts: int) -> None:
        self._power_excess = watts
        self._write_power(watts)

    async def set_power_override(self, watts: Union[bool, int]) -> None:
        if watts is True:
            nominal_power = await self.registers.load_nominal_power
            watts = nominal_power if nominal_power else 1000
        elif watts is False:
            watts = 0

        self._power_override = watts
        self._write_power(watts)
