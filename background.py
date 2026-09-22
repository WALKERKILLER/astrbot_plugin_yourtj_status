from __future__ import annotations

import asyncio
import mimetypes
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Optional

import httpx

try:
    from astrbot.api import logger
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)


ROOT = Path(__file__).parent
DEFAULT_BG = ROOT / "default_bg.webp"
LOLI_URL = "https://www.loliapi.com/acg/pe/"
DEFAULT_TIMEOUT = 10
DEFAULT_RETRIES = 2


@dataclass(frozen=True)
class BackgroundRequest:
    provider_chain: tuple[str, ...]
    local_path: Path | None = None
    timeout: int = DEFAULT_TIMEOUT
    proxy: str | None = None
    preload_count: int = 1
    retry_count: int = DEFAULT_RETRIES


@dataclass(frozen=True)
class BackgroundData:
    data: bytes
    mime: str


def _detect_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return "image/webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return "application/octet-stream"


def _mime_for_path(path: Path, data: bytes) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    return mime or _detect_mime(data)


def _client(timeout: int, proxy: str | None) -> httpx.AsyncClient:
    kwargs = {"follow_redirects": True, "timeout": timeout}
    if not proxy:
        return httpx.AsyncClient(**kwargs)
    try:
        return httpx.AsyncClient(proxy=proxy, **kwargs)
    except TypeError:  # httpx < 0.28
        return httpx.AsyncClient(proxies=proxy, **kwargs)  # type: ignore[call-arg]


def _is_image(data: bytes, content_type: str | None = None) -> bool:
    return _detect_mime(data).startswith("image/") or bool(
        content_type and content_type.lower().startswith("image/")
    )


def _read_local(path: Path | None = None) -> Optional[BackgroundData]:
    target = path or DEFAULT_BG
    try:
        if target.is_dir():
            candidates = [
                item
                for item in target.iterdir()
                if item.is_file() and item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
            ]
            target = random.choice(candidates) if candidates else DEFAULT_BG
        data = target.read_bytes()
        return BackgroundData(data=data, mime=_mime_for_path(target, data))
    except Exception as exc:
        logger.warning("YourTJ Status local background failed: %s", exc)
        return None


async def _fetch_loli(request: BackgroundRequest) -> Optional[BackgroundData]:
    attempts = max(1, request.retry_count + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            async with _client(request.timeout, request.proxy) as client:
                response = await client.get(LOLI_URL)
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get("content-type")
                if not _is_image(content, content_type):
                    raise ValueError(f"unexpected content type: {content_type or 'unknown'}")
                return BackgroundData(data=content, mime=content_type or _detect_mime(content))
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(0.25 * (attempt + 1))
    logger.warning("YourTJ Status loli background failed after %s attempts: %s", attempts, last_error)
    return None


async def _fetch_local(request: BackgroundRequest) -> Optional[BackgroundData]:
    return _read_local(request.local_path)


async def _fetch_default(request: BackgroundRequest) -> Optional[BackgroundData]:
    return _read_local()


BgProvider = Callable[[BackgroundRequest], Awaitable[Optional[BackgroundData]]]
_PROVIDERS: dict[str, BgProvider] = {
    "loli": _fetch_loli,
    "local": _fetch_local,
    "none": _fetch_default,
    "default": _fetch_default,
}


class BackgroundPreloader:
    def __init__(self, request: BackgroundRequest):
        self.request = request
        self.queue: asyncio.Queue[BackgroundData] = asyncio.Queue()
        self._preload_task: asyncio.Task | None = None
        self._last_remote: BackgroundData | None = None

    async def _fetch_once(self) -> BackgroundData:
        for raw_name in self.request.provider_chain:
            name = raw_name.strip().lower()
            provider = _PROVIDERS.get(name)
            if not provider:
                logger.warning("YourTJ Status unknown background provider: %s", name)
                continue
            try:
                background = await provider(self.request)
            except Exception as exc:  # pragma: no cover
                logger.warning("YourTJ Status background provider %s failed: %s", name, exc)
                background = None
            if background:
                if name == "loli":
                    self._last_remote = background
                return background
            if name == "loli" and self._last_remote:
                return self._last_remote

        if self._last_remote and "loli" in self.request.provider_chain:
            return self._last_remote
        fallback = _read_local()
        if not fallback:  # pragma: no cover
            raise FileNotFoundError(DEFAULT_BG)
        return fallback

    def _ensure_preload(self) -> asyncio.Task:
        if not self._preload_task or self._preload_task.done():
            self._preload_task = asyncio.create_task(self._fill_queue())
        return self._preload_task

    async def _fill_queue(self) -> None:
        try:
            count = max(1, int(self.request.preload_count))
            while self.queue.qsize() < count:
                await self.queue.put(await self._fetch_once())
        except Exception as exc:  # pragma: no cover
            logger.warning("YourTJ Status background preloader failed: %s", exc)
        finally:
            self._preload_task = None

    async def get(self) -> BackgroundData:
        preload_task = self._ensure_preload()
        if self.queue.empty():
            await preload_task
        try:
            return self.queue.get_nowait()
        except asyncio.QueueEmpty:
            return await self._fetch_once()


_cached_preloader: BackgroundPreloader | None = None
_cached_key: tuple | None = None


def _get_preloader(request: BackgroundRequest) -> BackgroundPreloader:
    global _cached_preloader, _cached_key
    key = (
        request.provider_chain,
        str(request.local_path) if request.local_path else "",
        request.timeout,
        request.proxy or "",
        request.preload_count,
        request.retry_count,
    )
    if _cached_preloader is None or _cached_key != key:
        _cached_preloader = BackgroundPreloader(request)
        _cached_key = key
    return _cached_preloader


def _request_from_config(config: dict) -> BackgroundRequest:
    section = config.get("background") if isinstance(config, dict) else {}
    section = section if isinstance(section, dict) else {}
    provider = str(section.get("bg_provider") or "loli").strip().lower()
    fallback = str(section.get("bg_fallback_chain") or "local")
    chain = tuple(dict.fromkeys([provider, *(item.strip().lower() for item in fallback.split(","))]))
    try:
        timeout = max(1, int(section.get("bg_req_timeout", DEFAULT_TIMEOUT)))
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    try:
        preload_count = max(1, int(section.get("bg_preload_count", 1)))
    except (TypeError, ValueError):
        preload_count = 1
    try:
        retry_count = max(0, int(section.get("bg_retry_count", DEFAULT_RETRIES)))
    except (TypeError, ValueError):
        retry_count = DEFAULT_RETRIES
    return BackgroundRequest(
        provider_chain=chain,
        local_path=Path(str(section.get("bg_local_path")).strip()).expanduser()
        if str(section.get("bg_local_path") or "").strip()
        else None,
        timeout=timeout,
        proxy=str(section.get("bg_proxy") or "").strip() or None,
        preload_count=preload_count,
        retry_count=retry_count,
    )


async def resolve_background(config: dict) -> tuple[bytes, str]:
    background = await _get_preloader(_request_from_config(config)).get()
    return background.data, background.mime
