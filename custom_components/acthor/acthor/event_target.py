import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)

KWArgsDict = Dict[str, Any]


class EventTarget:
    __slots__ = ("__listeners",)

    __listeners: Dict[str, List[Callable]]

    def __init__(self) -> None:
        self.__listeners = {}

    def add_listener(self, name: str, listener: Callable) -> Callable[[], bool]:
        try:
            self.__listeners[name].append(listener)
        except KeyError:
            self.__listeners[name] = [listener]

        def unsubscribe() -> bool:
            return self.remove_listener(name, listener)

        return unsubscribe

    def remove_listener(self, name: str, listener: Callable) -> bool:
        try:
            self.__listeners[name].remove(listener)
        except (KeyError, ValueError):
            return False

        return True

    async def on_listener_exception(self, listener: Callable, error: Exception, *,
                                    event_name: str,
                                    args: tuple,
                                    kwargs: KWArgsDict) -> None:
        logger.exception("listener %r raised error while handling event %r", listener, event_name, exc_info=error)

    async def __dispatch_event_listener(self, listener: Callable, args: tuple, kwargs: dict, *,
                                        event_name: str) -> None:
        try:
            res = listener(*args, **kwargs)
            if inspect.isawaitable(res):
                await res
        except Exception as e:
            await self.on_listener_exception(listener, e, event_name=event_name, args=args, kwargs=kwargs)

    async def __dispatch_event(self, name: str, args: tuple, kwargs: dict) -> None:
        try:
            listeners = self.__listeners[name]
        except KeyError:
            return

        coro_gen = (self.__dispatch_event_listener(listener, args, kwargs, event_name=name) for listener in listeners)
        await asyncio.gather(*coro_gen)

    def dispatch_event(self, name: str, *args, **kwargs) -> asyncio.Future:
        return asyncio.create_task(self.__dispatch_event(name, args, kwargs))
