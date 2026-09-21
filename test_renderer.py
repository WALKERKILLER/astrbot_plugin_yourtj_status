from poster_renderer import build_poster_html


def test_renderer() -> None:
    payload = {
        "code": 0,
        "result": {
            "serverRange": "1h",
            "range": "24h",
            "server": {"state": "unconfigured", "data": None},
            "traffic": {"state": "unconfigured", "data": None},
            "uptime": {"state": "unconfigured", "data": None},
        },
    }
    html = build_poster_html(payload, b"RIFFxxxxWEBP", "image/webp")
    assert "运行状态" in html
    assert "YourTJ Status" in html
    assert 'data:image/png;base64,' in html
    assert 'class="language-toggle"' not in html
    assert 'class="theme-toggle"' not in html
    assert 'class="community-link"' not in html
    assert '<button class="status-refresh' not in html
    assert '.status-poster { position: relative;' in html
    assert 'background: transparent;' in html
    assert 'min-height: 0; height: auto;' in html
    assert "{{" not in html and "{%" not in html


if __name__ == "__main__":
    test_renderer()
    print("renderer self-check passed")
