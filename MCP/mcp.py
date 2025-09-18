import os
import httpx
from mcp.server.fastmcp import FastMCP
import logging
import traceback

# Set up root logger to output to console at DEBUG level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger("VibeTTS-MCP")

# === MCP Server Setup ===
mcp = FastMCP("vibetts_mcp")

# Base VibeType API
VIBETYPE_API_BASE = "http://localhost:9031/api/v1/tts/kokoro"  # corrected port to match API server
API_KEY = None  # add if you implement future auth

# === MCP Tools ===

@mcp.tool()
async def list_languages() -> dict:
    """
    Returns supported languages for Kokoro TTS.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{VIBETYPE_API_BASE}/languages")
            resp.raise_for_status()
            languages = resp.json()
        return {"status": "success", "languages": languages}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_voices(language: str = None) -> dict:
    """
    Returns voices optionally filtered by language.
    """
    try:
        params = {"language": language} if language else {}
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{VIBETYPE_API_BASE}/voices", params=params)
            resp.raise_for_status()
            voices = resp.json()
        return {"status": "success", "voices": voices}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def list_models() -> dict:
    """
    Returns available Kokoro TTS models.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{VIBETYPE_API_BASE}/models")
            resp.raise_for_status()
            models = resp.json()
        return {"status": "success", "models": models}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@mcp.tool()
async def speak(
        text: str,
        voice: str = "am_adam",
        language: str = "English (US)",
        speed: float = 1.0,
) -> dict:
    """Trigger speech playback on server; no audio returned."""
    if not text:
        logger.error("speak: Text cannot be empty")
        print("speak: Text cannot be empty")
        return {"status": "error", "message": "Text cannot be empty"}
    try:
        log_msg = f"speak: Sending request to {VIBETYPE_API_BASE}/speak with text='{text}', voice='{voice}', language='{language}', speed={speed}"
        logger.info(log_msg)
        print(log_msg)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{VIBETYPE_API_BASE}/speak",
                json={"text": text, "voice": voice, "language": language, "speed": speed},
            )
            log_msg = f"/speak response status: {resp.status_code}, headers: {dict(resp.headers)}, content: {resp.text}"
            logger.info(log_msg)
            print(log_msg)
            try:
                result_json = resp.json()
            except Exception:
                result_json = {}
            result = {
                "status": "success",
                "message": result_json.get("message", "Speech synthesis started"),
                "text": text,
                "voice": voice,
                "language": language,
                "speed": speed,
            }
            logger.info(f"speak: Returning result: {result}")
            print(f"speak: Returning result: {result}")
            return result
    except Exception as e:
        logger.error(f"speak exception: {e}\n{traceback.format_exc()}")
        print(f"speak exception: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": f"{e}: {traceback.format_exc()}"}

@mcp.tool()
async def phonemes(text: str, language: str = "English (US)") -> dict:
    """
    Returns phoneme breakdown for a given text.
    """
    if not text:
        return {"status": "error", "message": "Text cannot be empty"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{VIBETYPE_API_BASE}/phonemes",
                json={"text": text, "language": language}
            )
            resp.raise_for_status()
            phoneme_data = resp.json()
        return {"status": "success", "data": phoneme_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# === Run MCP ===
if __name__ == "__main__":
    mcp.run(transport="stdio")
