def is_tiktok_url(url: str) -> bool:
    return "tiktok.com" in url.lower()


def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()


def is_tiktok_homepage_or_photo(url: str) -> bool:
    lower_url = url.lower()
    if lower_url.endswith("tiktok.com/") or lower_url.endswith("tiktok.com/uk-ua/"):
        return True
    if "/photo/" in lower_url or "aweme_type=150" in lower_url:
        return True
    return False


def test_tiktok_detection():
    assert is_tiktok_url("https://www.tiktok.com/@user/video/123456789") == True
    assert is_tiktok_url("https://vm.tiktok.com/ZMxxxxxx/") == True
    assert is_tiktok_url("https://youtube.com/watch?v=123") == False


def test_youtube_detection():
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == True
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ") == True
    assert is_youtube_url("https://www.tiktok.com/@user/video/123456789") == False


def test_tiktok_invalid_urls():
    assert is_tiktok_homepage_or_photo("https://www.tiktok.com/uk-UA/") == True
    assert is_tiktok_homepage_or_photo("https://www.tiktok.com/") == True
    assert is_tiktok_homepage_or_photo("https://www.tiktok.com/@user/photo/123") == True
    assert (
        is_tiktok_homepage_or_photo(
            "https://www.tiktok.com/@user/video/123?aweme_type=150"
        )
        == True
    )
    assert (
        is_tiktok_homepage_or_photo("https://www.tiktok.com/@user/video/123") == False
    )
