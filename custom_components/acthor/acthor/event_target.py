import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

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

    def dispatch_event(self, name: str, *args, **kwargs) -> asyncio.Task:
        return asyncio.create_task(self.__dispatch_event(name, args, kwargs))


class HasOptionalEventTargetMixin:
    @property
    def event_target(self) -> Optional[EventTarget]:
        return getattr(self, "__event_target", None)

    @event_target.setter
    def event_target(self, value: Optional[EventTarget]) -> None:
        if value is None:
            del self.event_target
            return
        assert isinstance(value, EventTarget)
        self.__event_target = value

    @event_target.deleter
    def event_target(self) -> None:
        delattr(self, "__event_target")

    def _maybe_dispatch_event(self, name: str, *args, **kwargs) -> Optional[asyncio.Task]:
        et = self.event_target
        if et is None:
            return None
        return et.dispatch_event(name, *args, **kwargs)
