import asyncio
import json
import time
import logging

import aio_pika
import clickhouse_connect

from src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("worker")


class AnalyticsWorker:
    def __init__(self):
        self.buffer = []
        self.pending_messages = []
        self.last_flush = time.monotonic()
        self.ch_client = None

    def connect_clickhouse(self):
        self.ch_client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            user=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
        )

    def flush_sync(self):
        # вызывается в отдельном потоке (flush → asyncio.to_thread → flush_sync)
        # отправляет накопленные в буфере события одной пачкой в ClickHouse
        # это НЕ RabbitMQ — это запись в БД аналитики (clickhouse_connect.client.insert)
        if not self.buffer:
            return
        data = self.buffer
        self.buffer = []
        self.ch_client.insert(
            "tracking_events",
            data,
            column_names=["timestamp", "user_id", "event_name", "experiment_name", "variant", "event_data"],
        )
        log.info("Flushed %d events to ClickHouse", len(data))

    async def flush(self):
        # clickhouse-connect синхронный, поэтому запускаем insert в отдельном потоке
        # После успешного flush в run() вызывается ack_pending() — подтверждение RabbitMQ
        await asyncio.to_thread(self.flush_sync)

    def on_message(self, body: bytes):
        # парсим JSON-сообщение и преобразуем в кортеж для ClickHouse
        event = json.loads(body)
        self.buffer.append((
            event.get("timestamp"),
            event["user_id"],
            event["event_name"],
            event.get("experiment_name"),
            event.get("variant"),
            json.dumps(event.get("event_data")),
        ))

    async def ack_pending(self):
        # ack = подтверждение RabbitMQ: "я обработал, можешь удалить из очереди"
        # Вызывается ТОЛЬКО после успешной записи в ClickHouse
        for msg in self.pending_messages:
            await msg.ack()
        self.pending_messages.clear()

    async def check_flush(self):
        # фоновый поток: проверяет каждую секунду, не прошло ли 5с с последнего сброса
        # Если прошло — сбрасывает буфер даже если пачка не набралась
        while True:
            await asyncio.sleep(1)
            if self.buffer and time.monotonic() - self.last_flush >= settings.MAX_TIMEOUT_SECONDS:
                await self.flush()
                await self.ack_pending()
                self.last_flush = time.monotonic()

    async def run(self):
        self.connect_clickhouse()

        # открываем TCP-соединение к RabbitMQ (robust = авто-переподключение при обрыве)
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            # канал = виртуальное соединение, всё общение с RabbitMQ через каналы
            channel = await connection.channel()
            # QoS: RabbitMQ может прислать до 5000 сообщений без подтверждения (prefetch)
            # Это позволяет копить пачку, не дожидаясь ack на каждое сообщение
            await channel.set_qos(prefetch_count=settings.MAX_BATCH_SIZE)

            # declare = "создать если нет, иначе вернуть" (идемпотентно)
            # Exchange = сортировочный центр; DIRECT = в очередь с точным routing_key
            exchange = await channel.declare_exchange(
                "ab_platform_events", aio_pika.ExchangeType.DIRECT, durable=True
            )
            # очередь = лента, где хранятся сообщения для Worker'а
            queue = await channel.declare_queue("analytics_events", durable=True)
            # привязываем очередь: сообщения с routing_key "events" → наша очередь
            await queue.bind(exchange, routing_key="events")

            # фоновый поток: каждую секунду проверяет, не пора ли сбросить буфер по таймауту
            asyncio.create_task(self.check_flush())

            # queue.iterator = подписка на очередь: каждое новое сообщение приходит в цикле
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    # парсим и кладём в буфер для ClickHouse
                    self.on_message(message.body)
                    # сохраняем объект message, чтобы позже подтвердить (ack)
                    self.pending_messages.append(message)

                    # если набралась пачка — сбрасываем:
                    # 1) INSERT в ClickHouse  2) ack всех сообщений пачки  3) обновляем таймер
                    if len(self.buffer) >= settings.MAX_BATCH_SIZE:
                        await self.flush()
                        await self.ack_pending()
                        self.last_flush = time.monotonic()


if __name__ == "__main__":
    worker = AnalyticsWorker()
    asyncio.run(worker.run())
