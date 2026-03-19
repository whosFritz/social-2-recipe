# testing0

Recipe automation stack: Mealie + n8n + YouTube description API.
The n8n workflow needs to be done by urself xD

## Services

| Service | URL |
|---------|-----|
| Mealie | http://localhost:9925 |
| n8n | http://localhost:5678 |
| YT API | http://localhost:8089 |

## Setup

```bash
cp .env.example .env   # fill in OPENAI_API_KEY
```

Optionally add Instagram cookies (Netscape format):

```bash
# Export from browser and place at:
./cookies.txt
```

## Run

```bash
docker compose up -d
```

## YT API

```bash
curl -X POST http://localhost:8089/description \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=... or https://www.instagram.com/...."}'
```
