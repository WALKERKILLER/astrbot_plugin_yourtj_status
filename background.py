from __future__ import annotations

import mimetypes
import random
from pathlib import Path

import httpx

try:
    from astrbot.api import logger
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


ROOT = Path(__file__).parent
DEFAULT_BG = ROOT / "default_bg.webp"
LOLI_URL = "https://www.loliapi.com/acg/pe/"


def _client(timeout: int, proxy: str | None) -> httpx.AsyncClient:
    kwargs = {"follow_redirects": True, "timeout": timeout}
    if not proxy:
        return httpx.AsyncClient(**kwargs)
    try:
        return httpx.AsyncClient(proxy=proxy, **kwargs)
    except TypeError:  # httpx < 0.28
        return httpx.AsyncClient(proxies=proxy, **kwargs)  # type: ignore[call-arg]


def _mime(data: bytes, name: str = "") -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "image/webp"
    return mimetypes.guess_type(name)[0] or "image/jpeg"


def _read_local(path: str | None) -> tuple[bytes, str] | None:
    target = Path(path).expanduser() if path else DEFAULT_BG
    try:
        if target.is_dir():
            files = [item for item in target.iterdir() if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}]
            target = random.choice(files) if files else DEFAULT_BG
        data = target.read_bytes()
        return data, _mime(data, target.name)
    except Exception as exc:
        logger.warning("YourTJ Status local background failed: %s", exc)
        return None


async def resolve_background(config: dict) -> tuple[bytes, str]:
    section = config.get("background") if isinstance(config, dict) else {}
    section = section if isinstance(section, dict) else {}
    provider = str(section.get("bg_provider") or "loli").strip().lower()
    local_path = str(section.get("bg_local_path") or "").strip()
    try:
        timeout = max(1, int(section.get("bg_req_timeout", 10)))
    except (TypeError, ValueError):
        timeout = 10
    proxy = str(section.get("bg_proxy") or "").strip() or None
    chain = [provider]
    chain.extend(item.strip().lower() for item in str(section.get("bg_fallback_chain") or "local").split(","))

    for name in dict.fromkeys(chain):
        if name == "loli":
            try:
                async with _client(timeout, proxy) as client:
                    response = await client.get(LOLI_URL)
                    response.raise_for_status()
                    data = response.content
                    if data[:4] in {b"RIFF", b"\x89PNG"} or data[:3] == b"\xff\xd8\xff" or response.headers.get("content-type", "").startswith("image/"):
                        return data, response.headers.get("content-type") or _mime(data)
            except Exception as exc:
                logger.warning("YourTJ Status loli background failed: %s", exc)
        elif name == "local":
            resolved = _read_local(local_path)
            if resolved:
                return resolved
        elif name in {"none", "default"}:
            resolved = _read_local(None)
            if resolved:
                return resolved

    resolved = _read_local(None)
    if not resolved:  # pragma: no cover
        raise FileNotFoundError(DEFAULT_BG)
    return resolved
