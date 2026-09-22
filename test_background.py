import asyncio

from background import resolve_background


async def test_local_fallback() -> None:
    data, mime = await resolve_background({"background": {"bg_provider": "local"}})
    assert data.startswith(b"RIFF")
    assert mime == "image/webp"


if __name__ == "__main__":
    asyncio.run(test_local_fallback())
    print("background self-check passed")
