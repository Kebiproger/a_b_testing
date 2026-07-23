import json
import aio_pika
from src.schemas.events import TrackingEvent


class EventBroker:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self.connection: aio_pika.Connection | None = None
        self.channel: aio_pika.Channel | None = None
        self.exchange: aio_pika.Exchange | None = None

    async def connect(self):
        # открываем TCP-соединение к RabbitMQ (robust = авто-переподключение)
        self.connection = await aio_pika.connect_robust(self.amqp_url)
        # канал = виртуальное соединение внутри TCP, всё общение идёт через каналы
        self.channel = await self.connection.channel()
        # declare = "создать если нет, иначе вернуть существующий" (идемпотентно)
        # Exchange = сортировочный центр: DIRECT = сообщение идёт в очередь с точным совпадением routing_key
        # durable = сохранять на диск, не терять при перезапуске
        self.exchange = await self.channel.declare_exchange(
            "ab_platform_events", aio_pika.ExchangeType.DIRECT, durable=True
        )
        # очередь = лента, где лежат сообщения для Worker'а
        queue = await self.channel.declare_queue("analytics_events", durable=True)
        # привязываем очередь к exchange: сообщения с routing_key "events" попадают в эту очередь
        await queue.bind(self.exchange, routing_key="events")

    async def publish(self, event: TrackingEvent):
        body = json.dumps(event.model_dump(mode="json")).encode()
        # DeliveryMode.PERSISTENT = сообщение сохраняется на диск, не потеряется при сбое RabbitMQ
        message = aio_pika.Message(body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        # публикуем в exchange с ключом "events" → очередь analytics_events
        await self.exchange.publish(message, routing_key="events")

    async def close(self):
        if self.connection:
            await self.connection.close()


broker = EventBroker("")
