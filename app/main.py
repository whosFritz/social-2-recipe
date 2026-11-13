import io
import os
import re
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone

import yt_dlp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

_gallery_dl_available = False
try:
    from gallery_dl import config as gdl_config, job as gdl_job

    _gallery_dl_available = True
except Exception:  # pragma: no cover - gallery-dl is always installed in this app
    pass

PHOTO_PATTERN = re.compile(
    r"^https?://(?:www\.)?(?:tiktok\.com/.*photo|instagram\.com/(?:.*/)?p)/.*",
    re.IGNORECASE,
)

app = FastAPI(title="YT Description API")


class VideoResponse(BaseModel):
    title: str
    description: str
    uploader: str
    upload_date: str | None
    thumbnail: str | None


class DescriptionRequest(BaseModel):
    url: str = Field(min_length=1)


def _cookie_file() -> str | None:
    path = os.getenv("COOKIES") or os.getenv("COOKIEFILE")
    return path if path and os.path.isfile(path) else None


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

    if cookiefile := _cookie_file():
        opts["cookiefile"] = cookiefile

    return opts


def _configure_gallery_dl() -> None:
    """Load gallery-dl configuration and apply cookie settings from env."""
    if not _gallery_dl_available:  # pragma: no cover
        return

    gdl_config.load()

    # Optional fixed cookie file (Netscape format).
    if cookiefile := _cookie_file():
        gdl_config.set(("extractor",), "cookies", cookiefile)

    # Optional browser cookie source (e.g. "chrome", "firefox"). Useful for
    # local development; in Docker it typically requires a mounted profile.
    cookies_from_browser = os.getenv("GALLERY_DL_COOKIES_FROM_BROWSER")
    if cookies_from_browser:
        gdl_config.set(("extractor",), "cookies-from-browser", cookies_from_browser)


class _GalleryDataJob(gdl_job.DataJob):
    """Collect metadata dictionaries without downloading any files."""

    def __init__(self, url: str):
        super().__init__(url)
        self.items: list[dict] = []

    def handle_url(self, url, kwds):
        self.items.append(dict(kwds))

    def handle_ugoira(self, *args, **kwargs):
        pass


def _format_date(value) -> str | None:
    """Normalize a date value to a YYYY-MM-DD string when possible."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y%m%d")
    text = str(value)
    # "2024-08-24 10:46:58" -> "20240824"
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    # Already YYYYMMDD
    if re.match(r"^\d{8}$", text):
        return text
    return text


def _extract_thumbnail(data: dict) -> str:
    """Best-effort extraction of a representative thumbnail/image URL."""
    if not isinstance(data, dict):
        return ""

    candidates = [
        data.get("thumbnail"),
        data.get("display_url"),
        data.get("url"),
        data.get("image"),
        data.get("cover"),
    ]

    image_post = data.get("imagePost")
    if isinstance(image_post, dict):
        cover = image_post.get("cover") or image_post.get("shareCover")
        if isinstance(cover, dict):
            image_url = cover.get("imageURL")
            if isinstance(image_url, dict):
                url_list = image_url.get("urlList")
                if isinstance(url_list, list) and url_list:
                    candidates.append(url_list[0])
            candidates.append(cover.get("url"))
        images = image_post.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, dict):
                image_url = first.get("imageURL")
                if isinstance(image_url, dict):
                    url_list = image_url.get("urlList")
                    if isinstance(url_list, list) and url_list:
                        candidates.append(url_list[0])
                candidates.append(first.get("url"))

    video = data.get("video")
    if isinstance(video, dict):
        candidates.extend(
            [
                video.get("cover"),
                video.get("originCover"),
                video.get("dynamicCover"),
            ]
        )

    author = data.get("author")
    if isinstance(author, dict):
        candidates.append(author.get("avatarLarger"))

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.startswith(("http://", "https://")):
            return candidate
    return ""


def _extract_uploader(data: dict) -> str:
    """Extract a human-readable uploader name from gallery-dl metadata."""
    if not isinstance(data, dict):
        return ""

    author = data.get("author")
    if isinstance(author, dict):
        return author.get("nickname") or author.get("uniqueId") or data.get("user", "")

    owner = data.get("owner")
    if isinstance(owner, dict):
        return owner.get("full_name") or owner.get("username") or ""

    return (
        data.get("fullname")
        or data.get("username")
        or data.get("user")
        or data.get("uploader")
        or ""
    )


def _video_response(data: dict) -> VideoResponse:
    return VideoResponse(
        title=data.get("title", ""),
        description=data.get("description", ""),
        uploader=data.get("uploader", ""),
        upload_date=data.get("upload_date"),
        thumbnail=data.get("thumbnail"),
    )


def _extract_with_gallery_dl(url: str) -> VideoResponse:
    """Extract metadata from a photo post using gallery-dl's Python API."""
    if not _gallery_dl_available:  # pragma: no cover
        raise HTTPException(status_code=501, detail="gallery-dl is not installed")

    _configure_gallery_dl()

    stdout_sink = io.StringIO()
    stderr_sink = io.StringIO()

    try:
        with redirect_stdout(stdout_sink), redirect_stderr(stderr_sink):
            job = _GalleryDataJob(url)
            job.run()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"gallery-dl error: {exc}",
        )

    if not job.items:
        raise HTTPException(status_code=404, detail="No metadata returned by gallery-dl")

    data = job.items[0]
    content = data.get("content") or ""
    title = data.get("title") or ""
    description = data.get("description") or ""
    # TikTok uses "desc"; Instagram uses "description" or "caption".
    caption = data.get("caption") or content or description or data.get("desc") or title or ""

    return _video_response({
        "title": title,
        "description": caption,
        "uploader": _extract_uploader(data),
        "upload_date": _format_date(data.get("date") or data.get("createTime") or data.get("upload_date")),
        "thumbnail": _extract_thumbnail(data),
    })


@app.post("/description", response_model=VideoResponse)
def get_description(request: DescriptionRequest):
    url = request.url

    if PHOTO_PATTERN.match(url):
        return _extract_with_gallery_dl(url)

    ydl_opts = _build_ydl_opts()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    print(f"[metadata] data: {info!r}", flush=True)
    return _video_response(info)


@app.get("/health")
def health():
    return {"status": "ok"}
