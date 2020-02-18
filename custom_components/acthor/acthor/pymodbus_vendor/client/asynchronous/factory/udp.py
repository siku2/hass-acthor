from __future__ import absolute_import, unicode_literals

import logging

from .. import schedulers
from ....constants import Defaults

LOGGER = logging.getLogger(__name__)


def async_io_factory(host="127.0.0.1", port=Defaults.Port, framer=None,
                     source_address=None, timeout=None, **kwargs):
    """
    Factory to create asyncio based asynchronous udp clients
    :param host: Host IP address
    :param port: Port
    :param framer: Modbus Framer
    :param source_address: Bind address
    :param timeout: Timeout in seconds
    :param kwargs:
    :return: asyncio event loop and udp client
    """
    import asyncio
    from ..asyncio import init_udp_client
    loop = kwargs.get("loop") or asyncio.get_event_loop()
    proto_cls = kwargs.get("proto_cls", None)
    cor = init_udp_client(proto_cls, loop, host, port)
    if not loop.is_running():
        client = loop.run_until_complete(asyncio.gather(cor))[0]
    else:
        client = asyncio.run_coroutine_threadsafe(cor, loop=loop)
        client = client.result()
    return loop, client


def get_factory(scheduler):
    """
    Gets protocol factory based on the backend scheduler being used
    :param scheduler: REACTOR/IO_LOOP/ASYNC_IO
    :return
    """
    if scheduler == schedulers.ASYNC_IO:
        return async_io_factory
    else:
        LOGGER.warning("Allowed Schedulers: {}, {}, {}".format(
            schedulers.REACTOR, schedulers.IO_LOOP, schedulers.ASYNC_IO
        ))
        raise Exception("Invalid Scheduler '{}'".format(scheduler))
