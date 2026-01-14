Very much vibecoded

# Paperless Utils

A Python application that reads document notifications from Redis streams and sends Telegram alerts.

## Features

- Reads messages from Redis streams
- Parses JSON messages with document IDs
- Sends notifications via Telegram bot
- Uses Pydantic for data validation
- Dockerized for easy deployment

## Requirements

- Python 3.12+
- Redis server with streams enabled
- Telegram bot token

## Environment Variables

The following environment variables are required:

- `REDIS_HOST`: Redis host address (e.g., `localhost`)
- `REDIS_PORT`: Redis port number (e.g., `6379`)
- `REDIS_QUEUE`: Name of the Redis stream queue to read from
- `TELEGRAM_BOT_TOKEN`: Telegram bot API token
- `TELEGRAM_CHAT_ID`: (Optional) Telegram chat ID to send messages to

## Installation

Using `uv`:

```bash
uv pip install -e .
```

## Usage

Set the required environment variables and run:

```bash
python main.py
```

## Local Testing

Start Redis using Docker Compose:

```bash
docker-compose up -d
```

Add test data to the Redis stream:

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_QUEUE=documents
python add_test_data.py
```

You can customize the number of test messages by setting `TEST_COUNT`:

```bash
TEST_COUNT=10 python add_test_data.py
```

## Docker

Build the Docker image:

```bash
docker build -t paperless-utils .
```

Run the container:

```bash
docker run --env-file .env paperless-utils
```

## Message Format

The application expects JSON messages from Redis streams with the following format:

```json
{
  "id": 12345
}
```

## GitHub Packages

The Docker image is automatically built and pushed to GitHub Packages when changes are pushed to the main branch or when tags are created.

