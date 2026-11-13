# testing0

Recipe automation stack: Mealie + n8n + YouTube/Instagram/TikTok etc. description API.

Automatically extracts recipes from YouTube, Instagram or TikTok videos etc., translates them to German via AI, and saves them directly into Mealie — including the thumbnail image.

## Services

| Service                       | URL                   |
| ----------------------------- | --------------------- |
| Mealie                        | http://localhost:9925 |
| n8n                           | http://localhost:5678 |
| SocialMediaMetaDownlaoder API | http://localhost:8089 |

## Setup

Optionally add Instagram cookies to avoid 429 errors (Too Many Requests) (Netscape format):

```bash
# Export from browser and place at:
./cookies.txt
```

## Feature

[iOS Shortcu/Kurzbefehl](https://www.icloud.com/shortcuts/7df08a71a14046de8a30ad2b72ba7a96) for easy importing of social media URLs into the mealie via share menu in social media apps (instagram, youtube, tiktok, facebook)

## Run

```bash
docker compose up -d
```

## n8n Workflow

Import `Public-Social Media to Mealie.json` into n8n and configure the following placeholders:

The workflow exposes a webhook (POST). Send a JSON body with a `url` field pointing to a YouTube or Instagram video.

```mermaid
graph TD
    A["📱 Social Media URL<br/>(YouTube, TikTok, Instagram, Facebook)"]

    B["🔐 Validate User<br/>Mealie Authentication"]

    C{"Social Media<br/>or Direct URL?"}

    D["🎬 Extract Video Data<br/>Title, Description, Thumbnail"]

    E["🤖 AI Processing<br/>GPT-6-Luna"]

    F["🌐 Translate to German<br/>Extract Recipe<br/>Normalize Units<br/>Apply Schema"]

    G["📝 Create Recipe<br/>in Mealie"]

    H["🖼️ Download & Upload<br/>Thumbnail Image"]

    I["✅ Success<br/>Return Recipe Link"]

    J["❌ Error<br/>Notify Discord"]

    K["🔄 Direct Recipe Creation<br/>Mealie API"]

    A --> B
    B --> C
    C -->|Social Media| D
    C -->|Direct URL| K
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    K --> I
    G -.->|Error| J
    D -.->|Error| J

    style A fill:#FF6B6B,color:#fff,stroke:#333,stroke-width:3px
    style B fill:#9C27B0,color:#fff,stroke:#333,stroke-width:2px
    style C fill:#9C27B0,color:#fff,stroke:#333,stroke-width:2px
    style D fill:#2196F3,color:#fff,stroke:#333,stroke-width:2px
    style E fill:#2196F3,color:#fff,stroke:#333,stroke-width:2px
    style F fill:#2196F3,color:#fff,stroke:#333,stroke-width:2px
    style G fill:#FF9800,color:#fff,stroke:#333,stroke-width:2px
    style H fill:#FF9800,color:#fff,stroke:#333,stroke-width:2px
    style I fill:#4CAF50,color:#fff,stroke:#333,stroke-width:3px
    style J fill:#f44336,color:#fff,stroke:#333,stroke-width:2px
    style K fill:#FF9800,color:#fff,stroke:#333,stroke-width:2px
```
