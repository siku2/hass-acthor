import abc
from typing import Iterable, Sized, Tuple, Union


class ABCModbusProtocol(abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def available(self) -> bool:
        ...

    @abc.abstractmethod
    async def read_register(self, address: int) -> int:
        ...

    @abc.abstractmethod
    async def read_registers(self, address: int, count: int) -> Tuple[int, ...]:
        ...

    @abc.abstractmethod
    async def write_register(self, address: int, value: int) -> None:
        ...

    @abc.abstractmethod
    async def write_registers(self, address: int, values: Iterable[int]) -> None:
        ...


class BaseRegister:
    __slots__ = ("_addr",)

    def __init__(self, addr: int) -> None:
        self._addr = addr


class SingleRegister(BaseRegister):
    __slots__ = ("_factor",)

    def __init__(self, addr: int, factor: float = None):
        super().__init__(addr)

        if factor == 0:
            raise ValueError("factor must not be 0")

        self._factor = factor

    async def read(self, protocol: ABCModbusProtocol) -> Union[float, int]:
        value = await protocol.read_register(self._addr)
        if self._factor is not None:
            value /= self._factor

        return value

    async def write(self, protocol: ABCModbusProtocol, value: Union[float, int]) -> None:
        if self._factor is not None:
            value *= self._factor

        await protocol.write_register(self._addr, int(value))


class MultiRegister(BaseRegister):
    __slots__ = ("_length", "_factor")

    def __init__(self, addr: int, length: int, *, factor: float = None) -> None:
        super().__init__(addr)
        self._length = length
        self._factor = factor

    async def read(self, protocol: ABCModbusProtocol) -> Tuple[Union[int, float], ...]:
        values = await protocol.read_registers(self._addr, self._length)
        fac = self._factor
        if fac is None:
            return values

        return tuple(val / fac for val in values)

    async def write(self, protocol: ABCModbusProtocol, values: Iterable[Union[int, float]]) -> None:
        fac = self._factor
        if fac is not None:
            values = tuple(fac * val for val in values)
        elif not isinstance(values, Sized):
            values = tuple(values)

        if len(values) != self._length:
            raise ValueError("can only write matching length")

        await protocol.write_registers(self._addr, values)
