import aio_pika
import json
import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class RabbitSettings(BaseSettings):
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    RABBITMQ_HOST: str = "localhost"

    model_config = ConfigDict(
        env_file=".env",
        extra="ignore" 
    )
    

settings = RabbitSettings()
RABBIT_URL = f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}/"

connection = None
channel = None

async def get_rabbit_connection():
    global connection, channel
    if connection is None or connection.is_closed:
        connection = await aio_pika.connect_robust(RABBIT_URL)
        channel = await connection.channel()
        # Создаем очередь, если её нет, то durable=True сохраняет очередь на диск
        await channel.declare_queue("click_events", durable=True)
    return channel


async def publish_click_event(link_id: int, short_code: str, ip: str, user_agent: str, referer: str):
    try:
        channel = await get_rabbit_connection()
        
        message_body = json.dumps({
            "link_id": link_id,
            "short_code": short_code,
            "ip_address": ip,
            "user_agent": user_agent,
            "referer": referer
        }).encode()
        
        # PERSISTENT означает, что сообщение сохранится на диск RabbitMQ и не пропадет при перезапуске
        message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await channel.default_exchange.publish(message, routing_key="click_events")
        print(f"[RABBITMQ] Событие клика отправлено для {short_code}")
        
    except Exception as e:
        print(f"[RABBITMQ] Ошибка отправки (редирект всё равно сработает): {e}")