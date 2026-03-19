from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import yt_dlp
import json
import re
import os

app = FastAPI(title="YT Description API")


class VideoResponse(BaseModel):
    title: str
    description: str
    uploader: str
    upload_date: str | None
    thumbnail: str | None


def _parse_body(raw: bytes) -> str:
    """Parse request body, fixing invalid JSON escape sequences in URLs."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Remove backslashes before characters that are not valid JSON escapes
        # Valid: \" \\ \/ \b \f \n \r \t \uXXXX — everything else is invalid
        cleaned = re.sub(r'\\([^"\\/bfnrtu])', r'\1', raw.decode("utf-8"))
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=422, detail=f"Invalid JSON body: {e}")
    url = data.get("url") if isinstance(data, dict) else None
    if not url:
        raise HTTPException(status_code=422, detail="Missing 'url' field")
    return str(url)


def _build_ydl_opts() -> dict:
    """Build yt-dlp options from environment variables.

    Supported env vars:
    - COOKIES or COOKIEFILE: path to cookies.txt
    """
    opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }

    cookiefile = os.getenv("COOKIES") or os.getenv("COOKIEFILE")
    if cookiefile and os.path.isfile(cookiefile):
        opts["cookiefile"] = cookiefile

    return opts


@app.post("/description", response_model=VideoResponse)
async def get_description(request: Request):
    raw = await request.body()
    url = _parse_body(raw)

    ydl_opts = _build_ydl_opts()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return VideoResponse(
        title=info.get("title", ""),
        description=info.get("description", ""),
        uploader=info.get("uploader", ""),
        upload_date=info.get("upload_date"),
        thumbnail=info.get("thumbnail"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
