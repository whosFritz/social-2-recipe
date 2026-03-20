# testing0

Recipe automation stack: Mealie + n8n + YouTube/Instagram/TikTok etc. description API.

Automatically extracts recipes from YouTube, Instagram or TikTok videos etc., translates them to German via AI, and saves them directly into Mealie — including the thumbnail image.

## Services

| Service | URL |
|---------|-----|
| Mealie | http://localhost:9925 |
| n8n | http://localhost:5678 |
| SocialMediaMetaDownlaoder API | http://localhost:8089 |

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

## n8n Workflow

Import `public-n8n-workflow-with-example-values.json` into n8n and configure the following placeholders:

| Placeholder | Description |
|---|---|
| `<your-ai-api-url>` | OpenAI-compatible API endpoint (e.g. `https://api.openai.com/v1/chat/completions`) |
| `<your-ai-api-key>` | API key for the AI service |
| `<your-mealie-api-token>` | Mealie long-lived API token (Settings → API Tokens) |
| `<your-mealie-domain>` | Your Mealie instance domain (e.g. `mealie.example.com`) |
| `<your-webhook-id>` | Generated automatically by n8n after import |
| `<your-instance-id>` | Generated automatically by n8n |

The workflow exposes a webhook (POST). Send a JSON body with a `url` field pointing to a YouTube or Instagram video.

## Example Request

```bash
curl -X POST http://localhost:8089/description \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=... or https://www.instagram.com/...."}'
```
