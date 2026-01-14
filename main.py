import asyncio
import json
import os

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from redis.asyncio import Redis

load_dotenv()


class DocumentMessage(BaseModel):
    id: int = Field(..., description="Document ID")


class Config(BaseModel):
    redis_host: str = Field(..., description="Redis host")
    redis_port: int = Field(..., description="Redis port")
    redis_queue: str = Field(..., description="Redis stream queue name")
    telegram_bot_token: str = Field(..., description="Telegram bot API token")
    telegram_chat_id: str | None = Field(
        default=None, description="Telegram chat ID (optional, can be set via bot commands)"
    )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    @classmethod
    def from_env(cls) -> "Config":
        redis_host = os.getenv("REDIS_HOST")
        redis_port_str = os.getenv("REDIS_PORT")
        redis_queue = os.getenv("REDIS_QUEUE")
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not redis_host:
            raise ValueError("REDIS_HOST environment variable is required")
        if not redis_port_str:
            raise ValueError("REDIS_PORT environment variable is required")
        try:
            redis_port = int(redis_port_str)
        except ValueError as e:
            raise ValueError("REDIS_PORT must be a valid integer") from e
        if not redis_queue:
            raise ValueError("REDIS_QUEUE environment variable is required")
        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

        return cls(
            redis_host=redis_host,
            redis_port=redis_port,
            redis_queue=redis_queue,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
        )


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str | None = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, message: str, chat_id: str | None = None) -> bool:
        target_chat_id = chat_id or self.chat_id
        if not target_chat_id:
            raise ValueError("Telegram chat ID must be provided either in config or as parameter")

        url = f"{self.api_url}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                return True
            except httpx.HTTPError as e:
                print(f"Failed to send Telegram message: {e}")
                return False


class RedisStreamReader:
    def __init__(self, redis_url: str, queue_name: str):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.client: Redis | None = None
        self.last_id = "0"

    async def connect(self):
        self.client = await Redis.from_url(self.redis_url, decode_responses=True)

    async def disconnect(self):
        if self.client:
            await self.client.aclose()

    async def read_messages(self) -> list[DocumentMessage]:
        if not self.client:
            await self.connect()

        if not self.client:
            raise RuntimeError("Redis client not connected")

        try:
            messages = await self.client.xread({self.queue_name: self.last_id}, count=10, block=1000)
            documents = []

            for _stream, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    self.last_id = msg_id
                    try:
                        if "data" in msg_data:
                            data = json.loads(msg_data["data"])
                        else:
                            data = msg_data

                        document = DocumentMessage(**data)
                        documents.append(document)
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"Failed to parse message {msg_id}: {e}")
                        continue

            return documents
        except Exception as e:
            print(f"Error reading from Redis stream: {e}")
            return []


async def main():
    config = Config.from_env()
    notifier = TelegramNotifier(config.telegram_bot_token, config.telegram_chat_id)
    reader = RedisStreamReader(config.redis_url, config.redis_queue)

    try:
        await reader.connect()
        print(f"Connected to Redis. Reading from stream: {config.redis_queue}")

        while True:
            documents = await reader.read_messages()

            for doc in documents:
                message = f"📄 Document consumed: ID <b>{doc.id}</b>"
                success = await notifier.send_message(message)
                if success:
                    print(f"Notification sent for document ID: {doc.id}")
                else:
                    print(f"Failed to send notification for document ID: {doc.id}")

            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        await reader.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
