import asyncio
import enum
import logging
from typing import Iterable, Tuple

from pymodbus.client.asynchronous.asyncio import ModbusClientProtocol, ReconnectingAsyncioModbusTcpClient, \
    init_tcp_client

from .registers import ACThorRegistersMixin

__all__ = ["ACThorRegisters", "ACThor",
           "OperationState"]

logger = logging.getLogger(__name__)

# The port cannot be changed in the AC THOR
MODBUS_PORT = 502


class ACThorRegisters(ACThorRegistersMixin):
    __slots__ = ("_client", "_lock")

    def __init__(self, client: ReconnectingAsyncioModbusTcpClient) -> None:
        self._client = client
        # FIXME lock here because pymodbus currently can't handle concurrent requests.
        #   see: https://github.com/riptideio/pymodbus/issues/475
        self._lock = asyncio.Lock()

    @classmethod
    async def connect(cls, host: str = None):
        logger.info("connecting to %r", host)
        client = await init_tcp_client(None, None, host, MODBUS_PORT)
        return cls(client)

    @property
    def available(self) -> bool:
        return self._client.connected

    @property
    def _protocol(self) -> ModbusClientProtocol:
        return self._client.protocol

    async def read_register(self, address: int) -> int:
        return (await self.read_registers(address, 1))[0]

    async def read_registers(self, address: int, count: int) -> Tuple[int, ...]:
        async with self._lock:
            logger.debug("reading %r register(s) from %r", count, address)
            result = await self._protocol.read_holding_registers(address, count)

        # TODO error handling
        return tuple(result.registers)

    async def write_register(self, address: int, value: int) -> None:
        async with self._lock:
            logger.debug("writing %r to register %r", value, address)
            await self._protocol.write_register(address, value)

    async def write_registers(self, address: int, values: Iterable[int]) -> None:
        async with self._lock:
            logger.debug("writing %r to registers starting at %r", values, address)
            await self._protocol.write_registers(address, values)


class OperationState(enum.IntEnum):
    WAITING_FOR_EXCESS = 0
    HEATING_WITH_EXCESS = 1
    BOOST_BACKUP = 2
    TEMPERATURE_REACHED = 3
    NO_CONTROL_SIGNAL = 4
    # TODO not documented?
    RED_CROSS_FLASHES = 5


class ACThor:
    def __init__(self, registers: ACThorRegistersMixin, serial_number: str) -> None:
        self.registers = registers
        self.serial_number = serial_number

    @classmethod
    async def connect(cls, host: str = None):
        registers = await ACThorRegisters.connect(host)
        sn = await registers.serial_number
        return cls(registers, sn)

    @property
    def available(self) -> bool:
        return self.registers.available

    async def set_power(self, watts: int) -> None:
        self.registers.power = watts

    async def get_power(self) -> int:
        return await self.registers.power

    async def set_power_timeout(self, timeout: int) -> None:
        self.registers.power_timeout = timeout

    async def get_state(self) -> OperationState:
        return OperationState(await self.registers.operation_state)
