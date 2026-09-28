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
            "deviceRange": "7d",
            "devices": {
                "state": "ok",
                "fetchedAt": "2026-09-29T00:00:00Z",
                "data": {
                    "visitors": 10,
                    "totalVisitors": 10,
                    "complete": True,
                    "rows": [
                        {"device": "mobile", "os": "ios", "browser": "safari", "visitors": 6},
                        {"device": "laptop", "os": "windows", "browser": "chrome", "visitors": 4},
                    ],
                },
            },
        },
    }
    html = build_poster_html(payload, b"RIFFxxxxWEBP", "image/webp")
    assert "运行状态" in html
    assert "YourTJ Status" in html
    assert "访客设备分布" in html
    assert 'class="device-sankey"' in html
    assert "手机" in html and "Windows" in html and "Chrome" in html
    assert "悬停或聚焦节点与流线" not in html
    assert 'class="device-detail"' not in html
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
