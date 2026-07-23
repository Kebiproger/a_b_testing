import asyncio
import logging
import json

import aio_pika
from src.schemas.events import TrackingEvent

log = logging.getLogger("broker")


class EventBroker:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection: aio_pika.Connection | None = None
        self.channel: aio_pika.Channel | None = None
        self.exchange: aio_pika.Exchange | None = None
        self._connected = False

    async def connect(self, retries: int = 5, delay: float = 2.0):
        """Подключение к RabbitMQ с retry (ждём, пока RabbitMQ встанет)."""
        for attempt in range(1, retries + 1):
            try:
                self.connection = await aio_pika.connect_robust(self.amqp_url)
                self.channel = await self.connection.channel()
                self.exchange = await self.channel.declare_exchange(
                    "ab_platform_events", aio_pika.ExchangeType.DIRECT, durable=True
                )
                queue = await self.channel.declare_queue("analytics_events", durable=True)
                await queue.bind(self.exchange, routing_key="events")
                self._connected = True
                log.info("Connected to RabbitMQ (attempt %d/%d)", attempt, retries)
                return
            except (ConnectionRefusedError, aio_pika.exceptions.AMQPConnectionError) as e:
                if attempt < retries:
                    log.warning(
                        "RabbitMQ not ready (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt, retries, e, delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= 1.5  # exponential backoff
                else:
                    log.error("Failed to connect to RabbitMQ after %d attempts", retries)
                    raise

    async def publish(self, event: TrackingEvent):
        if not self._connected:
            raise RuntimeError("RabbitMQ not connected")
        body = json.dumps(event.model_dump(mode="json")).encode()
        message = aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await self.exchange.publish(message, routing_key="events")

    async def close(self):
        if self.connection:
            await self.connection.close()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected


broker = EventBroker("")
