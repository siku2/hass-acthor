from __future__ import absolute_import, unicode_literals

import logging

from .factory.serial import get_factory
from .schedulers import ASYNC_IO
from ...compat import IS_PYTHON3, PYTHON_VERSION
from ...exceptions import ParameterException
from ...factory import ClientDecoder
from ...transaction import ModbusAsciiFramer, ModbusBinaryFramer, ModbusRtuFramer, ModbusSocketFramer

logger = logging.getLogger(__name__)


class AsyncModbusSerialClient(object):
    """
    Actual Async Serial Client to be used.

    To use do::
    """

    @classmethod
    def _framer(cls, method):
        """
        Returns the requested framer

        :method: The serial framer to instantiate
        :returns: The requested serial framer
        """
        method = method.lower()
        if method == 'ascii':
            return ModbusAsciiFramer(ClientDecoder())
        elif method == 'rtu':
            return ModbusRtuFramer(ClientDecoder())
        elif method == 'binary':
            return ModbusBinaryFramer(ClientDecoder())
        elif method == 'socket':
            return ModbusSocketFramer(ClientDecoder())

        raise ParameterException("Invalid framer method requested")

    def __new__(cls, scheduler, method, port, **kwargs):
        """
        Scheduler to use:
            - reactor (Twisted)
            - io_loop (Tornado)
            - async_io (asyncio)
        The methods to connect are::

          - ascii
          - rtu
          - binary
        : param scheduler: Backend to use
        :param method: The method to use for connection
        :param port: The serial port to attach to
        :param stopbits: The number of stop bits to use
        :param bytesize: The bytesize of the serial messages
        :param parity: Which kind of parity to use
        :param baudrate: The baud rate to use for the serial device
        :param timeout: The timeout between serial requests (default 3s)
        :param scheduler:
        :param method:
        :param port:
        :param kwargs:
        :return:
        """
        if (not (IS_PYTHON3 and PYTHON_VERSION >= (3, 4))
                and scheduler == ASYNC_IO):
            logger.critical("ASYNCIO is supported only on python3")
            import sys
            sys.exit(1)
        factory_class = get_factory(scheduler)
        framer = cls._framer(method)
        yieldable = factory_class(framer=framer, port=port, **kwargs)
        return yieldable
