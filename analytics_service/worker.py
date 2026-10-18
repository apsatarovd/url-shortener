import asyncio
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from link_service.models import Base, ClickEvent
from dotenv import load_dotenv
import aio_pika

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost") 
DB_NAME = os.getenv("DB_NAME")

RABBITMQ_USER = os.getenv("RABBITMQ_USER")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
RABBIT_URL = f"amqp://{RABBITMQ_USER}:{RABBITMQ_PASS}@{RABBITMQ_HOST}/"

def parse_device(user_agent):
    if not user_agent:
        return "Unknown"
    
    user_agent_lower = user_agent.lower()
    if "mobile" in user_agent_lower or "android" in user_agent_lower or "iphone" in user_agent_lower:
        return "Mobile"
    return "Desktop"

def parse_source(referer):
    if not referer:
        return "Direct"
    
    referer_lower = referer.lower()
    if "t.me" in referer_lower or "telegram" in referer_lower:
        return "Telegram"
    if "google" in referer_lower:
        return "Google"
    if "yandex" in referer_lower:
        return "Yandex"
    
    return "Other"


async def main():  
    print("[ANALYTICS WORKER] Запуск..")

    connection = await aio_pika.connect_robust(RABBIT_URL)
    channel = await connection.channel()
    queue = await channel.declare_queue("click_events", durable=True)
    
    print("[ANALYTICS WORKER] Слушает очередь 'click_events'..")

    async with queue.iterator() as queue_iter:
         async for message in queue_iter:
             async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    
                    process_message(data)
                except Exception as e:
                    print(f"[ANALYTICS WORKER] Ошибка обработки: {e}")

def process_message(message_data: dict):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        device = parse_device(message_data.get("user_agent", ""))
        source = parse_source(message_data.get("referer", ""))
        
        new_click = ClickEvent(
            link_id=message_data["link_id"],
            ip_address=message_data.get("ip_address"),
            user_agent=device,      
            referer=source         
        )
        
    
        session.add(new_click)
        session.commit()
        
        print(f"[DB] Сохранен клик: Link ID={new_click.link_id}, Устройство={device}, Источник={source}")  


if __name__ == "__main__":
    asyncio.run(main())