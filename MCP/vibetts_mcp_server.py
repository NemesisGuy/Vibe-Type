import os
import httpx
from mcp.server.fastmcp import FastMCP
import logging
import traceback
from typing import List

# Set up root logger to output to console at DEBUG level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger("VibeTTS-MCP")

# === MCP Server Setup ===
# Renamed file to avoid name collision with 'mcp' package
mcp = FastMCP("vibetts_mcp")

# Base VibeType API (allow override via env)
_raw_host = os.environ.get("VIBETYPE_API_HOST", "localhost")
_api_port = os.environ.get("VIBETYPE_API_PORT", "9031")
# If the server is bound to 0.0.0.0 or ::, connect via loopback
_client_host = "127.0.0.1" if _raw_host in {"0.0.0.0", "::"} else _raw_host
VIBETYPE_API_BASE = f"http://{_client_host}:{_api_port}/api/v1/tts/kokoro"
API_KEY = None  # add if you implement future auth

# Default HTTP timeouts tuned for local TTS (return fast, don't wait on audio)
HTTP_TIMEOUT = httpx.Timeout(connect=2.0, read=1.0, write=2.0, pool=2.0)
HTTP_LIMITS = httpx.Limits(max_keepalive_connections=2, max_connections=5, keepalive_expiry=10.0)

# === MCP Tools ===

@mcp.tool()
async def list_languages() -> dict:
    """
    Returns supported languages for Kokoro TTS.
    """
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            resp = await client.get(f"{VIBETYPE_API_BASE}/languages")
            resp.raise_for_status()
            languages = resp.json()
        return {"status": "success", "languages": languages}
    except Exception as e:
        logger.error(f"list_languages error: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_voices(language: str = None) -> dict:
    """
    Returns voices optionally filtered by language.
    """
    try:
        params = {"language": language} if language else {}
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            resp = await client.get(f"{VIBETYPE_API_BASE}/voices", params=params)
            resp.raise_for_status()
            voices = resp.json()
        return {"status": "success", "voices": voices}
    except Exception as e:
        logger.error(f"list_voices error: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_models() -> dict:
    """
    Returns available Kokoro TTS models.
    """
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            resp = await client.get(f"{VIBETYPE_API_BASE}/models")
            resp.raise_for_status()
            models = resp.json()
        return {"status": "success", "models": models}
    except Exception as e:
        logger.error(f"list_models error: {e}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def speak(
        text: str,
        voice: str = "am_adam",
        language: str = "English (US)",
        speed: float = 1.0,
) -> dict:
    """Trigger speech playback on server; returns quickly; audio plays on server."""
    if not text:
        logger.error("speak: Text cannot be empty")
        return {"status": "error", "message": "Text cannot be empty"}
    try:
        log_msg = (
            f"speak: Sending request to {VIBETYPE_API_BASE}/speak with "
            f"text='{text[:60]}{'...' if len(text) > 60 else ''}', voice='{voice}', "
            f"language='{language}', speed={speed}"
        )
        logger.info(log_msg)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            resp = await client.post(
                f"{VIBETYPE_API_BASE}/speak",
                json={"text": text, "voice": voice, "language": language, "speed": speed},
                headers={"Connection": "close"}
            )
            status = resp.status_code
            body_text = resp.text
            logger.info(f"/speak response status={status}, content={body_text}")
            if status == 429:
                try:
                    j = resp.json()
                except Exception:
                    j = {}
                return {
                    "status": "busy",
                    "message": j.get("message", "TTS queue is busy. Try again shortly."),
                    "text": text,
                    "voice": voice,
                    "language": language,
                    "speed": speed,
                }
            try:
                result_json = resp.json()
            except Exception:
                result_json = {}
            # Normalize success shape for agents
            return {
                "status": result_json.get("status", "success"),
                "message": result_json.get("message", "Speech synthesis started"),
                "text": text,
                "voice": voice,
                "language": language,
                "speed": speed,
            }
    except httpx.ReadTimeout as e:
        logger.warning(f"speak timeout (treated as accepted): {e}")
        # Treat as accepted: server often starts speaking even if HTTP response is delayed.
        return {
            "status": "success",
            "message": "TTS accepted; HTTP response timed out. Audio playback likely in progress.",
            "text": text,
            "voice": voice,
            "language": language,
            "speed": speed,
        }
    except Exception as e:
        logger.error(f"speak exception: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def speak_batch(
    texts: List[str],
    voice: str = "am_adam",
    language: str = "English (US)",
    speed: float = 1.0,
) -> dict:
    """Speak multiple short lines with a single tool call to reduce prompts.
    Returns a summary with per-item status. Long lines may still time out, but are treated as accepted.
    """
    if not texts or not isinstance(texts, list):
        return {"status": "error", "message": "texts must be a non-empty list"}
    results = []
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            for t in texts:
                if not t:
                    results.append({"text": t, "status": "skipped", "reason": "empty"})
                    continue
                try:
                    resp = await client.post(
                        f"{VIBETYPE_API_BASE}/speak",
                        json={"text": t, "voice": voice, "language": language, "speed": speed},
                    )
                    try:
                        j = resp.json()
                    except Exception:
                        j = {}
                    results.append({
                        "text": t,
                        "status": j.get("status", "success"),
                        "message": j.get("message", "Speech synthesis started"),
                    })
                except httpx.ReadTimeout:
                    results.append({
                        "text": t,
                        "status": "success",
                        "message": "TTS accepted; HTTP response timed out.",
                    })
                except Exception as e:
                    results.append({"text": t, "status": "error", "message": str(e)})
        return {"status": "success", "results": results, "voice": voice, "language": language, "speed": speed}
    except Exception as e:
        logger.error(f"speak_batch exception: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def phonemes(text: str, language: str = "English (US)") -> dict:
    """
    Returns phoneme breakdown for a given text.
    """
    if not text:
        return {"status": "error", "message": "Text cannot be empty"}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, limits=HTTP_LIMITS) as client:
            resp = await client.post(
                f"{VIBETYPE_API_BASE}/phonemes",
                json={"text": text, "language": language},
                headers={"Connection": "close"}
            )
            resp.raise_for_status()
            phoneme_data = resp.json()
        return {"status": "success", "data": phoneme_data}
    except Exception as e:
        logger.error(f"phonemes error: {e}")
        return {"status": "error", "message": str(e)}

# === Run MCP ===
if __name__ == "__main__":
    logger.info(f"Starting VibeTTS MCP with API base {VIBETYPE_API_BASE}")
    mcp.run(transport="stdio")
