import abc
import asyncio
import datetime
import logging
from typing import Any, Coroutine, Generic, Iterable, Iterator, Tuple, TypeVar

from .abc import ABCModbusProtocol, MultiRegister, SingleRegister

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ReadOnlyMixin(Generic[T], abc.ABC):
    __slots__ = ()

    def __get__(self, instance: ABCModbusProtocol, cls=None) -> Coroutine[Any, Any, T]:
        return self.read(instance)

    def __set__(self, instance: ABCModbusProtocol, _) -> None:
        raise AttributeError

    @abc.abstractmethod
    async def read(self, protocol: ABCModbusProtocol) -> T:
        ...


class ReadWriteMixin(ReadOnlyMixin[T], abc.ABC):
    __slots__ = ()

    def __set__(self, instance: ABCModbusProtocol, value: T) -> None:
        asyncio.create_task(self._write_handle_error(instance, value))

    async def _write_handle_error(self, instance: ABCModbusProtocol, value: T) -> None:
        try:
            await self.write(instance, value)
        except Exception:
            logger.exception("failed to write %s to %s", repr(value), self)

    @abc.abstractmethod
    async def write(self, protocol: ABCModbusProtocol, value: T) -> None:
        ...


class ReadOnly(SingleRegister, ReadOnlyMixin[int]):
    __slots__ = ()


class ReadOnlyText(MultiRegister, ReadOnlyMixin[str]):
    __slots__ = ()

    async def read(self, protocol: ABCModbusProtocol) -> str:
        values = await super().read(protocol)
        return "".join(chr(value >> 8) + chr(value & 0xFF) for value in values)


class ReadWrite(SingleRegister, ReadWriteMixin[int]):
    __slots__ = ()


def i16s_to_bytes(it: Iterable[int]) -> Iterator[int]:
    for value in it:
        yield from value.to_bytes(2, "big")


def bytes_to_i16(it: Iterable[int]) -> Iterator[int]:
    it = iter(it)
    for high in it:
        low = next(it)
        yield (high << 8) | low


class ReadWriteMulti(MultiRegister, ReadWriteMixin[int]):
    __slots__ = ()

    async def read(self, protocol: ABCModbusProtocol) -> int:
        values = await super().read(protocol)
        return int.from_bytes(tuple(i16s_to_bytes(values)), "big")

    async def write(self, protocol: ABCModbusProtocol, value: int) -> None:
        byte_parts = value.to_bytes(2 * self._length, "big")
        await super().write(protocol, bytes_to_i16(byte_parts))


class ACThorRegistersMixin(ABCModbusProtocol, abc.ABC):
    """

    Provides direct access to the registers with some additional helper methods for accessing multi-register values.
    """
    __slots__ = ()

    power = ReadWrite(1000)
    """W
    
    0-3.000 M1, 0-6.000 M3,
    0-9.000 AC•THOR 9s
    """

    temp1 = ReadOnly(1001, 10)
    """°C"""
    temp2 = ReadOnly(1030, 10)
    """°C"""
    temp3 = ReadOnly(1031, 10)
    """°C"""
    temp4 = ReadOnly(1032, 10)
    """°C"""
    temp5 = ReadOnly(1033, 10)
    """°C"""
    temp6 = ReadOnly(1034, 10)
    """°C"""
    temp7 = ReadOnly(1035, 10)
    """°C"""
    temp8 = ReadOnly(1036, 10)
    """°C"""

    # Sensors 2-8 can be read with a single instruction
    _temp_range_2_8 = MultiRegister(1030, 7, factor=10)

    ww1_max = ReadWrite(1002, 10)
    """°C"""
    ww2_max = ReadWrite(1037, 10)
    """°C"""
    ww3_max = ReadWrite(1038, 10)
    """°C"""

    ww1_min = ReadWrite(1006, 10)
    """°C"""
    ww2_min = ReadWrite(1039, 10)
    """°C"""
    ww3_min = ReadWrite(1040, 10)
    """°C"""

    _ww_range_2_3 = MultiRegister(1037, 4)

    status = ReadOnly(1003)
    """
    
    0..... Off
    1-8... device start-up
    9... operation
    >=200 Error states power stage
    """
    power_timeout = ReadWrite(1004)
    """sec"""
    boost_mode = ReadWrite(1005)
    """0: off, 1: on, 3: relay boost on"""

    boost_time1_start = ReadWrite(1007)
    """Hour"""
    boost_time1_stop = ReadWrite(1008)
    """Hour"""
    boost_time2_start = ReadWrite(1026)
    """Hour"""
    boost_time2_stop = ReadWrite(1027)
    """Hour"""

    _boost_time1_range = MultiRegister(1007, 2)
    _boost_time2_range = MultiRegister(1026, 2)

    hour = ReadWrite(1009)
    minute = ReadWrite(1010)
    second = ReadWrite(1011)

    _hms_range = MultiRegister(1009, 3)

    boost_activate = ReadWrite(1012)
    number = ReadWrite(1013)
    max_power = ReadWrite(1014)
    """500..3000W
    
    do not use with 9s
    """
    tempchip = ReadOnly(1015, 10)
    """°C"""

    control_firmware_version = ReadOnly(1016)
    control_firmware_subversion = ReadOnly(1028)
    control_firmware_update_available = ReadOnly(1029)
    """
    
    0 : no new afw available,
    1 : new afw available (download not started, fw-version in variable Fwup_actual_version)
    2 : download started (ini-file download)
    3 : download started (afw.bin-file download)
    4 : downloading other files
    5 : download interrupted
    10: download finished, waiting for installation
    """

    ps_firmware_version = ReadOnly(1017)
    serial_number = ReadOnlyText(1018, 8)

    rh1_max = ReadWrite(1041, 10)
    """°C"""
    rh2_max = ReadWrite(1042, 10)
    """°C"""
    rh3_max = ReadWrite(1043, 10)
    """°C"""

    rh1_day_min = ReadWrite(1044, 10)
    """°C"""
    rh2_day_min = ReadWrite(1045, 10)
    """°C"""
    rh3_day_min = ReadWrite(1046, 10)
    """°C"""

    rh1_night_min = ReadWrite(1047, 10)
    """°C"""
    rh2_night_min = ReadWrite(1048, 10)
    """°C"""
    rh3_night_min = ReadWrite(1049, 10)
    """°C"""

    _rhs_max_range = MultiRegister(1041, 3)
    _rhs_day_min_range = MultiRegister(1044, 3)
    _rhs_night_min_range = MultiRegister(1047, 3)

    night_flag = ReadOnly(1050)
    """0: day, 1: night"""

    utc_correction = ReadWrite(1051)
    """0..37"""
    dst_correction = ReadWrite(1052)
    """0, 1"""

    _time_correction_range = MultiRegister(1051, 2)

    legionella_interval = ReadWrite(1053)
    """Days"""
    legionella_start = ReadWrite(1054)
    """Hour"""
    legionella_temp = ReadWrite(1055)
    """°C"""
    legionella_mode = ReadWrite(1056)
    """0: off, 1: on"""

    _legionella_range = MultiRegister(1053, 4)

    stratification_flag = ReadOnly(1057)
    """0: off, 1: on"""
    relay1_status = ReadOnly(1058)
    """0: off, 1: on"""
    load_state = ReadOnly(1059)
    """0: off, 1: on"""
    load_nominal_power = ReadOnly(1060)
    """W"""

    u_l1 = ReadOnly(1061)
    """V"""
    u_l2 = ReadOnly(1067)
    """V
    
    9s only, ACTHOR replies 0
    """
    u_l3 = ReadOnly(1072)
    """V
    
    9s only, ACTHOR replies 0
    """

    i_l1 = ReadOnly(1062, 10)
    """A"""
    i_l2 = ReadOnly(1068, 10)
    """A
    
    9s only, ACTHOR replies 0
    """
    i_l3 = ReadOnly(1073, 10)
    """A
    
    9s only, ACTHOR replies 0
    """

    _l1_range = MultiRegister(1061, 2)
    _l2_range = MultiRegister(1067, 2)
    _l3_range = MultiRegister(1072, 2)

    u_out = ReadOnly(1063)
    """V"""
    freq = ReadOnly(1064)
    """mHz"""

    operation_mode = ReadWrite(1065)
    """1-8
    
    since version a0010004
    """
    access_level = ReadWrite(1066)
    """1-3
    
    since version a0010004
    """

    meter_power = ReadOnly(1069)
    """integer, negative is feed in"""
    control_type = ReadWrite(1070)
    """
    
    1  = http
    2  = Modbus TCP
    3  = Fronius Auto
    4  = Fronius Manual
    5  = SMA
    6  = Steca / Kostal Piko MP
    7  = Varta Auto
    8  = Varta Manual
    9  = my-PV Power Meter Auto
    10 = my-PV Power Meter Manual
    11 = my-PV Power Meter Direkt (not readable, no network connection)
    12 = reserved
    13 = Multimode slave
    14 = RCT Power Manual
    15 = Adjustable Modbus TCP
    """
    pmax_abs = ReadOnly(1071)
    """
    
    incl. Slave-Power in case of multi-unit-mode
    """

    p_out1 = ReadOnly(1074)
    """W
    
    9s only, ACTHOR replies 0
    """
    p_out2 = ReadOnly(1075)
    """W
    
    9s only, ACTHOR replies 0
    """
    p_out3 = ReadOnly(1076)
    """W
    
    9s only, ACTHOR replies 0
    """

    _p_out_range = MultiRegister(1074, 3)

    operation_state = ReadOnly(1077)
    """
    
    0 green tick flashes
    1 yellow wave is on
    2 yellow wave flashes
    3 green tick is on
    4 red cross is on
    5 red cross flashes
    """

    power_big = ReadWriteMulti(1078, 2)
    """W
    
    Only for large systems with several units (multi-mode) and output specifications greater than
    65,535 watts. Power below this value is entered in register 1000.
    """
    power_and_relays = ReadWrite(1080)
    """W
    
    9s only
    
    Allows direct access to the AC•THOR 9s power stage and the relays in Modbus TCP mode.
    bit 15: relay Out-3
    bit 14: relay Out-2
    bit 13 and 12:
        0 ... power stage off
        1 ... power stage to Out-1
        2 ... power stage to Out-2
        3 ... power stage to Out-3
    bit 11 – 0: power stage power 0 – 3.000 (watt)
    """

    async def get_temps(self) -> Tuple[float, float, float, float, float, float, float, float]:
        """Get the temperatures.

        Reads all eight temperature sensors with only two instructions.

        Returns:
            8-tuple containing the temperatures in celsius.
        """
        first_temp, other_temps = await asyncio.gather(self.temp1, self._temp_range_2_8.read(self))
        return (first_temp, *other_temps)

    async def get_temp(self, sensor: int) -> float:
        """Read the value of a temperature sensor.

        Args:
            sensor: Sensor number in [1..8].

        Returns:
            Temperature of the sensor.
        """
        if not 1 <= sensor <= 8:
            raise ValueError("sensor must be in range(1, 9)")

        return await getattr(self, f"temp{sensor}")

    async def get_time(self) -> datetime.time:
        hour, minute, second = await self._hms_range.read(self)

        # TODO build tzinfo
        tzinfo = datetime.timezone.utc

        return datetime.time(
            hour, minute, second,
            tzinfo=tzinfo,
        )

    async def get_control_firmware_version(self) -> Tuple[int, int]:
        """Read the full control firmware version.

        Returns:
            2-tuple (major, sub)..
        """
        maj, sub = await asyncio.gather(self.control_firmware_version, self.control_firmware_subversion)
        return maj, sub
