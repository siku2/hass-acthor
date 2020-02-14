import asyncio
import logging
from typing import Optional

from pymodbus.client.asynchronous.asyncio import ModbusClientProtocol, ReconnectingAsyncioModbusTcpClient, \
    init_tcp_client

logger = logging.getLogger(__name__)

# The port cannot be changed in the AC THOR
MODBUS_PORT = 502


class ACThor:
    __slots__ = ("_client", "_lock",
                 "_serial_number")

    _serial_number: Optional[str]

    def __init__(self, client: ReconnectingAsyncioModbusTcpClient) -> None:
        self._client = client
        # FIXME lock here because pymodbus currently can't handle concurrent requests.
        #   see: https://github.com/riptideio/pymodbus/issues/475
        self._lock = asyncio.Lock()
        self._serial_number = None

    @classmethod
    async def connect(cls, host: str = None):
        logger.info("connecting to %r", host)
        client = await init_tcp_client(None, None, host, MODBUS_PORT)
        return cls(client)

    @property
    def _protocol(self) -> ModbusClientProtocol:
        return self._client.protocol

    @property
    def connected(self) -> bool:
        return self._client.connected

    async def _read_register(self, address: int) -> int:
        async with self._lock:
            logger.debug("reading register %r", address)
            result = await self._protocol.read_holding_registers(address)

        # TODO error handling
        return result.registers[0]

    async def _read_two_chars(self, address: int) -> str:
        value = await self._read_register(address)
        return chr(value >> 8) + chr(value & 0xFF)

    async def _write_register(self, address: int, value: int) -> None:
        async with self._lock:
            logger.debug("writing %r to register %r", value, address)
            await self._protocol.write_register(address, value)

    async def read_power(self) -> int:
        return await self._read_register(1000)

    async def write_power(self, value: int) -> None:
        await self._write_register(1000, value)

    async def read_status(self) -> int:
        return await self._read_register(1003)

    async def read_temp1(self) -> float:
        return await self._read_register(1001) / 10

    async def read_temp2(self) -> float:
        return await self._read_register(1030) / 10

    async def read_temp3(self) -> float:
        return await self._read_register(1031) / 10

    async def read_temp4(self) -> float:
        return await self._read_register(1032) / 10

    async def read_temp5(self) -> float:
        return await self._read_register(1033) / 10

    async def read_temp6(self) -> float:
        return await self._read_register(1034) / 10

    async def read_temp7(self) -> float:
        return await self._read_register(1035) / 10

    async def read_temp8(self) -> float:
        return await self._read_register(1036) / 10

    async def _read_serial_number(self) -> str:
        logger.debug("reading serial number")
        sn = ""
        # serial number in registers 1018-1025 (inclusive)
        for addr in range(1018, 1026):
            sn += await self._read_two_chars(addr)

        logger.debug("serial number: %r", self._serial_number)

        return sn

    async def get_serial_number(self) -> str:
        if self._serial_number is None:
            self._serial_number = await self._read_serial_number()

        return self._serial_number
