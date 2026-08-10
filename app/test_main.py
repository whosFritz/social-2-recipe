import os
from unittest.mock import patch, MagicMock

import pytest
import yt_dlp
from fastapi.testclient import TestClient

from main import app, _parse_body, PHOTO_PATTERN


client = TestClient(app)


class TestParseBody:
    def test_valid_json(self):
        assert _parse_body(b'{"url":"https://x.com/v"}') == "https://x.com/v"

    def test_invalid_escape_is_repaired(self):
        raw = rb'{"url":"https://x.com/path\_1"}'
        assert _parse_body(raw) == "https://x.com/path_1"

    def test_missing_url_field(self):
        with pytest.raises(Exception) as exc:
            _parse_body(b'{"foo":"bar"}')
        assert "Missing 'url' field" in str(exc.value)

    def test_invalid_json(self):
        with pytest.raises(Exception):
            _parse_body(b"not json")


class TestPhotoPattern:
    @pytest.mark.parametrize(
        "url",
        [
            "https://www.tiktok.com/@user/photo/123456",
            "https://tiktok.com/@user/photo/123456",
            "https://www.instagram.com/user/p/abc123/",
            "https://instagram.com/user/p/abc123",
            "https://www.instagram.com/p/C1gi6Ait4S5/",
            "https://instagram.com/p/C1gi6Ait4S5",
        ],
    )
    def test_matches_photo_urls(self, url):
        assert PHOTO_PATTERN.match(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://www.youtube.com/watch?v=abc",
            "https://www.tiktok.com/@user/video/123456",
            "https://instagram.com/user/reels/abc123",
        ],
    )
    def test_does_not_match_other_urls(self, url):
        assert not PHOTO_PATTERN.match(url)


class TestHealth:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestDescriptionVideo:
    @patch("main.yt_dlp.YoutubeDL")
    def test_uses_yt_dlp_for_regular_url(self, mock_ytdl):
        instance = MagicMock()
        instance.extract_info.return_value = {
            "title": "A video",
            "description": "A desc",
            "uploader": "Uploader",
            "upload_date": "20240101",
            "thumbnail": "https://thumb.jpg",
        }
        mock_ytdl.return_value.__enter__.return_value = instance

        resp = client.post("/description", json={"url": "https://youtube.com/watch?v=abc"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "A video"
        assert data["description"] == "A desc"
        assert data["uploader"] == "Uploader"
        instance.extract_info.assert_called_once()

    @patch("main.yt_dlp.YoutubeDL")
    def test_yt_dlp_error_returns_400(self, mock_ytdl):
        instance = MagicMock()
        instance.extract_info.side_effect = yt_dlp.utils.DownloadError("download failed")
        mock_ytdl.return_value.__enter__.return_value = instance

        resp = client.post("/description", json={"url": "https://youtube.com/watch?v=bad"})
        assert resp.status_code == 400


class _FakeGalleryJob:
    def __init__(self, items):
        self.items = items

    def run(self):
        pass


class TestDescriptionPhoto:
    @patch("main._GalleryDataJob")
    def test_uses_gallery_dl_for_instagram_photo(self, mock_job_cls):
        mock_job_cls.return_value = _FakeGalleryJob(
            [
                {
                    "title": "IG Title",
                    "description": "IG Desc",
                    "uploader": "ig_user",
                    "date": "2024-01-01T00:00:00",
                    "url": "https://image.jpg",
                }
            ]
        )

        resp = client.post(
            "/description",
            json={"url": "https://www.instagram.com/p/C1gi6Ait4S5/"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "IG Title"
        assert data["description"] == "IG Desc"
        assert data["uploader"] == "ig_user"
        assert data["thumbnail"] == "https://image.jpg"
        mock_job_cls.assert_called_once()

    @patch("main._GalleryDataJob")
    def test_uses_gallery_dl_for_tiktok_photo(self, mock_job_cls):
        mock_job_cls.return_value = _FakeGalleryJob(
            [
                {
                    "desc": "We have it too! #croatia",
                    "user": "croatian_memes",
                    "author": {"nickname": "Croatian memes", "uniqueId": "croatian_memes"},
                    "date": "2024-08-24 10:46:58",
                    "video": {"cover": "https://p16-tt/cover.jpg"},
                }
            ]
        )

        resp = client.post(
            "/description",
            json={"url": "https://www.tiktok.com/@croatian_memes/photo/7406655666472979745"},
        )

        data = resp.json()
        assert resp.status_code == 200
        assert data["description"] == "We have it too! #croatia"
        assert data["uploader"] == "Croatian memes"
        assert data["thumbnail"] == "https://p16-tt/cover.jpg"
        assert data["upload_date"] == "20240824"

    @patch("main._GalleryDataJob")
    def test_gallery_dl_error_returns_400(self, mock_job_cls):
        mock_job_cls.return_value = _FakeGalleryJob([])
        mock_job_cls.return_value.run = MagicMock(side_effect=Exception("login required"))

        resp = client.post(
            "/description",
            json={"url": "https://www.instagram.com/p/C1gi6Ait4S5/"},
        )

        assert resp.status_code == 400
        assert "gallery-dl error" in resp.json()["detail"]

    @patch("main._GalleryDataJob")
    def test_gallery_dl_empty_returns_404(self, mock_job_cls):
        mock_job_cls.return_value = _FakeGalleryJob([])

        resp = client.post(
            "/description",
            json={"url": "https://www.instagram.com/p/C1gi6Ait4S5/"},
        )

        assert resp.status_code == 404
        assert "No metadata" in resp.json()["detail"]


class TestGalleryDlCookies:
    @patch("main.gdl_config.set")
    @patch("main.gdl_config.load")
    @patch("main._GalleryDataJob")
    @patch.dict(os.environ, {"COOKIES": "/tmp/fake_cookies.txt"}, clear=True)
    def test_sets_cookies_when_cookiefile_exists(self, mock_job, mock_load, mock_set):
        with patch("os.path.isfile", return_value=True):
            mock_job.return_value = _FakeGalleryJob(
                [{"title": "x", "description": "y"}]
            )
            resp = client.post(
                "/description",
                json={"url": "https://www.instagram.com/p/C1gi6Ait4S5/"},
            )

        assert resp.status_code == 200
        set_calls = [name for args, _ in [call for call in mock_set.call_args_list] for name in args[0]]
        assert "cookies" in set_calls or ("extractor",) in [
            call.args[0] for call in mock_set.call_args_list
        ]
