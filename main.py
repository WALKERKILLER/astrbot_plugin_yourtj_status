from __future__ import annotations

from typing import Any, Final
from urllib.parse import urlparse

import httpx

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .background import resolve_background
from .poster_renderer import build_poster_html


PLUGIN_NAME: Final[str] = "astrbot_plugin_yourtj_status"
DEFAULT_API_URL: Final[str] = "https://status.yourtj.de/api/status"


def _int_config(config: Any, key: str, default: int) -> int:
    try:
        return max(1, int(config.get(key, default)))
    except (AttributeError, TypeError, ValueError):
        return default


def _api_url(config: Any) -> str:
    try:
        value = str(config.get("api_url") or DEFAULT_API_URL).strip()
    except AttributeError:
        value = DEFAULT_API_URL
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("api_url must be an http(s) URL")
    return value


@register(
    PLUGIN_NAME,
    "YourTJ",
    "获取 YourTJ 社区实时运行状态并生成状态海报",
    "1.0.0",
)
class YourTJStatusPlugin(Star):
    def __init__(self, context: Context, config: dict[str, Any] | None = None):
        super().__init__(context)
        self.config = config if isinstance(config, dict) else {}

    @filter.command("监控")
    async def command_status(self, event: AstrMessageEvent):
        try:
            api_url = _api_url(self.config)
            timeout = _int_config(self.config, "request_timeout", 15)
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.get(api_url, params={"range": "24h", "serverRange": "1h", "deviceRange": "7d"})
                response.raise_for_status()
                payload = response.json()
            if payload.get("code") != 0 or not isinstance(payload.get("result"), dict):
                raise ValueError("status API returned an invalid response")

            background, background_mime = await resolve_background(self.config)
            html = build_poster_html(payload, background, background_mime)
            image_url = await self.html_render(
                html,
                {},
                return_url=True,
                options={
                    "type": "jpeg",
                    "quality": 92,
                    "full_page": True,
                    "animations": "disabled",
                    "caret": "hide",
                    "scale": "css",
                    "device_scale_factor_level": "ultra",
                },
            )
            yield event.image_result(image_url)
        except Exception as exc:
            logger.exception("YourTJ Status poster failed: %s", exc)
            yield event.plain_result("获取状态海报失败，请稍后重试")

    async def terminate(self):
        logger.info("YourTJ Status plugin terminated")
