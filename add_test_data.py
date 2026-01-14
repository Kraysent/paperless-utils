import asyncio
import json
import os
import sys

from redis.asyncio import Redis


async def add_test_data(redis_host: str, redis_port: int, queue_name: str, count: int = 5):
    redis_url = f"redis://{redis_host}:{redis_port}"
    client = await Redis.from_url(redis_url, decode_responses=True)

    try:
        print(f"Adding {count} test messages to Redis stream '{queue_name}'...")

        for i in range(1, count + 1):
            message_data = {"id": i}
            msg_id = await client.xadd(queue_name, {"data": json.dumps(message_data)})
            print(f"Added message {i} with ID {msg_id}: {message_data}")

        print(f"\nSuccessfully added {count} test messages!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.aclose()


async def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    queue_name = os.getenv("REDIS_QUEUE", "documents")
    count = int(os.getenv("TEST_COUNT", "5"))

    await add_test_data(redis_host, redis_port, queue_name, count)


if __name__ == "__main__":
    asyncio.run(main())
