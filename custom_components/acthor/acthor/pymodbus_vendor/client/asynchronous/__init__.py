"""
Async Modbus Client implementation based on Twisted, tornado and asyncio
------------------------------------------------------------------------

Example run::

    # Import The clients

    # For tornado based asynchronous client use
    event_loop, future = Client(schedulers.IO_LOOP, port=5020)

    # For twisted based asynchronous client use
    event_loop, future = Client(schedulers.REACTOR, port=5020)

    # For asyncio based asynchronous client use
    event_loop, client = Client(schedulers.ASYNC_IO, port=5020)

    # Here event_loop is a thread which would control the backend and future is
    # a Future/deffered object which would be used to
    # add call backs to run asynchronously.

    # The Actual client could be accessed with future.result() with Tornado
    # and future.result when using twisted

    # For asyncio the actual client is returned and event loop is asyncio loop

"""
