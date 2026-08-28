import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.realtime.events import RealtimeEvent

DEFAULT_SUBSCRIBER_QUEUE_SIZE = 100
EventQueue = asyncio.Queue[RealtimeEvent]


class EventBroadcaster:
    def __init__(
        self,
        queue_size: int = DEFAULT_SUBSCRIBER_QUEUE_SIZE,
    ) -> None:
        if queue_size <= 0:
            raise ValueError("Subscriber queue size must be greater than zero")

        self.queue_size = queue_size
        self._subscribers: set[EventQueue] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    def subscribe(self) -> EventQueue:
        queue: EventQueue = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: EventQueue) -> None:
        self._subscribers.discard(queue)

    @asynccontextmanager
    async def subscription(self) -> AsyncIterator[EventQueue]:
        queue = self.subscribe()
        try:
            yield queue
        finally:
            self.unsubscribe(queue)

    async def publish(self, event: RealtimeEvent) -> None:
        for queue in tuple(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue


event_broadcaster = EventBroadcaster()
