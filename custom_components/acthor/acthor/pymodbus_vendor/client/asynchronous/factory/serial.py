"""
Factory to create asynchronous serial clients based on twisted/tornado/asyncio
"""
from __future__ import absolute_import, unicode_literals

import logging

from .. import schedulers

LOGGER = logging.getLogger(__name__)


def async_io_factory(port=None, framer=None, **kwargs):
    """
    Factory to create asyncio based asynchronous serial clients
    :param port:  Serial port
    :param framer: Modbus Framer
    :param kwargs: Serial port options
    :return: asyncio event loop and serial client
    """
    import asyncio
    from ..asyncio import (ModbusClientProtocol,
                           AsyncioModbusSerialClient)
    loop = kwargs.pop("loop", None) or asyncio.get_event_loop()
    proto_cls = kwargs.pop("proto_cls", None) or ModbusClientProtocol

    try:
        from serial_asyncio import create_serial_connection
    except ImportError:
        LOGGER.critical("pyserial-asyncio is not installed, "
                        "install with 'pip install pyserial-asyncio")
        import sys
        sys.exit(1)

    client = AsyncioModbusSerialClient(port, proto_cls, framer, loop, **kwargs)
    coro = client.connect()
    loop.run_until_complete(coro)
    return loop, client


def get_factory(scheduler):
    """
    Gets protocol factory based on the backend scheduler being used
    :param scheduler: REACTOR/IO_LOOP/ASYNC_IO
    :return:
    """
    if scheduler == schedulers.ASYNC_IO:
        return async_io_factory
    else:
        LOGGER.warning("Allowed Schedulers: {}, {}, {}".format(
            schedulers.REACTOR, schedulers.IO_LOOP, schedulers.ASYNC_IO
        ))
        raise Exception("Invalid Scheduler '{}'".format(scheduler))
