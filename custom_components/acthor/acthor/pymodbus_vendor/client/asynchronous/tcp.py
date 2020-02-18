from __future__ import absolute_import, unicode_literals

import logging

from .factory.tcp import get_factory
from .schedulers import ASYNC_IO
from ...compat import IS_PYTHON3, PYTHON_VERSION
from ...constants import Defaults

logger = logging.getLogger(__name__)


class AsyncModbusTCPClient(object):
    """
    Actual Async Serial Client to be used.

    To use do::
    """

    def __new__(cls, scheduler, host="127.0.0.1", port=Defaults.Port,
                framer=None, source_address=None, timeout=None, **kwargs):
        """
        Scheduler to use:
            - reactor (Twisted)
            - io_loop (Tornado)
            - async_io (asyncio)
        :param scheduler: Backend to use
        :param host: Host IP address
        :param port: Port
        :param framer: Modbus Framer to use
        :param source_address: source address specific to underlying backend
        :param timeout: Time out in seconds
        :param kwargs: Other extra args specific to Backend being used
        :return:
        """
        if (not (IS_PYTHON3 and PYTHON_VERSION >= (3, 4))
                and scheduler == ASYNC_IO):
            logger.critical("ASYNCIO is supported only on python3")
            import sys
            sys.exit(1)
        factory_class = get_factory(scheduler)
        yieldable = factory_class(host=host, port=port, framer=framer,
                                  source_address=source_address,
                                  timeout=timeout, **kwargs)
        return yieldable
