from __future__ import annotations

from typing import Any, Generic, Never, TypeVar

from effect._internal import core as internal
from effect._internal.core import Effect, gen, succeed, sync
from effect.concurrency import all as all_effects
from effect.queue import Queue, queue_make
from effect.scope import acquire_release

A = TypeVar("A")


class PubSub(Generic[A]):
    def __init__(self) -> None:
        self._subscribers: set[Queue[A]] = set()

    def publish(self, value: A) -> Effect[None, Never, Never]:
        def run_publish():
            offers = [sub.offer(value) for sub in list(self._subscribers)]
            return internal.flat_map(all_effects(offers, concurrency=True), lambda _: succeed(None))

        return internal.suspend(run_publish)

    def subscribe(self) -> Effect[Queue[A], Never, Any]:
        @gen
        def acquire():
            q = yield queue_make()
            self._subscribers.add(q)
            return q

        def release(q, _exit):
            return sync(lambda: self._subscribers.discard(q))

        return acquire_release(acquire(), release)


def pubsub_make() -> Effect[PubSub[Any], Never, Never]:
    return sync(PubSub)
