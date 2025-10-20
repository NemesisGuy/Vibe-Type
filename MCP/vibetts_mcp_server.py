import os
import sys
import logging
from typing import Any, Dict, Iterable, List, Union

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response

# Ensure project root is on sys.path for imports like `from core import tts`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print("--- STARTING VibeTTS MCP server (HTTP transport) ---", file=sys.stderr, flush=True)

try:
    from core import tts as core_tts
except Exception as exc:  # pragma: no cover - fatal import
    print("ERROR: Unable to import core.tts. Ensure dependencies are installed.", file=sys.stderr, flush=True)
    raise

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("vibetts_mcp")
logging.basicConfig(level=logging.INFO)


def _json_response(payload: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    response = JSONResponse(payload, status_code=status_code)
    response.headers["Connection"] = "close"
    return response


def _collect_batch_items(payload: Dict[str, Any]) -> List[str]:
    raw_items: Union[List[Any], None] = None
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            raw_items = payload["items"]
        elif isinstance(payload.get("texts"), list):
            raw_items = payload["texts"]
    if not raw_items:
        return []
    cleaned: List[str] = []
    for entry in raw_items:
        candidate = entry
        if isinstance(entry, dict):
            candidate = entry.get("text")
        if isinstance(candidate, str):
            stripped = candidate.strip()
            if stripped:
                cleaned.append(stripped)
    return cleaned


def create_server(host: str, port: int) -> tuple[FastMCP, Any]:
    server = FastMCP(
        "vibetts-mcp",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        sse_path="/events",
        message_path="/messages/",
    )

    @server.tool(description="Readiness probe that returns 'ok' when the MCP server is ready.")
    def health() -> str:
        return "ok"

    @server.tool(
        description="Queue a single text string for speech synthesis using the active VibeType TTS pipeline.",
    )
    def speak(text: str) -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Missing or invalid 'text'")
        core_tts.speak_text(text)
        return {"status": "accepted", "queued": 1}

    @server.tool(
        description=(
            "Queue multiple text entries sequentially for speech synthesis. Each item may be a string or an "
            "object with a 'text' field."
        ),
    )
    def speak_batch(items: List[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"items": items}
        texts = _collect_batch_items(payload)
        if not texts:
            raise ValueError("No valid text entries provided")
        queued = 0
        for entry in texts:
            core_tts.speak_text(entry)
            queued += 1
        return {"status": "accepted", "queued": queued}

    @server.tool(
        description=(
            "Return Kokoro phoneme segmentation for the supplied text. Requires Kokoro TTS to be initialised."
        ),
    )
    def phonemes(text: str, language: str = "Auto-Detect") -> Dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Missing or invalid 'text'")
        core_tts._initialize_kokoro_tts()  # type: ignore[attr-defined]
        kt = getattr(core_tts, "kokoro_tts_instance", None)
        if kt is None:
            raise RuntimeError("Kokoro TTS not initialized or disabled.")
        segments = kt.phonemize_text(text, language_name=language)
        if not segments or any(seg.get("error") for seg in segments):
            raise RuntimeError("Phoneme generation failed")
        return {"status": "ok", "count": len(segments), "segments": segments}

    starlette_app = server.streamable_http_app()

    async def http_health(request: Request) -> Response:  # noqa: ARG001
        return PlainTextResponse("ok", status_code=200)

    async def http_index(request: Request) -> Response:
        if request.method == "POST":
            # Forward JSON-RPC requests to the /mcp endpoint used by FastMCP
            return RedirectResponse(url="/mcp", status_code=307)
        payload = {
            "service": "VibeType MCP",
            "endpoints": {
                "health": "/health",
                "speak": "/speak",
                "speak_batch": "/speak_batch",
                "phonemes": "/phonemes",
                "rpc": "/mcp",
            },
        }
        return _json_response(payload)

    async def http_speak(request: Request) -> Response:
        data = await request.json() if request.headers.get("content-type") else {}
        if not isinstance(data, dict):
            return _json_response({"error": "Invalid payload"}, status_code=400)
        text = data.get("text")
        if not isinstance(text, str) or not text.strip():
            return _json_response({"error": "Missing or invalid 'text'"}, status_code=400)
        try:
            core_tts.speak_text(text)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("/speak failed: %s", exc)
            return _json_response({"error": str(exc)}, status_code=500)
        return _json_response({"status": "accepted", "queued": 1}, status_code=202)

    async def http_speak_batch(request: Request) -> Response:
        data = await request.json() if request.headers.get("content-type") else {}
        if not isinstance(data, dict):
            return _json_response({"error": "Invalid payload"}, status_code=400)
        items = _collect_batch_items(data)
        if not items:
            return _json_response({"error": "No valid text entries provided"}, status_code=400)
        queued = 0
        try:
            for entry in items:
                core_tts.speak_text(entry)
                queued += 1
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("/speak_batch failure after %d items: %s", queued, exc)
            return _json_response({"error": str(exc), "queued": queued}, status_code=500)
        return _json_response({"status": "accepted", "queued": queued}, status_code=202)

    async def http_phonemes(request: Request) -> Response:
        data = await request.json() if request.headers.get("content-type") else {}
        if not isinstance(data, dict):
            return _json_response({"error": "Invalid payload"}, status_code=400)
        text = data.get("text")
        language = data.get("language", "Auto-Detect")
        if not isinstance(text, str) or not text.strip():
            return _json_response({"error": "Missing or invalid 'text'"}, status_code=400)
        try:
            core_tts._initialize_kokoro_tts()  # type: ignore[attr-defined]
            kt = getattr(core_tts, "kokoro_tts_instance", None)
            if kt is None:
                return _json_response({"error": "Kokoro TTS not initialized or disabled."}, status_code=503)
            segments = kt.phonemize_text(text, language_name=language)
            if not segments or any(seg.get("error") for seg in segments):
                return _json_response({"error": "Phoneme generation failed.", "details": segments}, status_code=500)
            return _json_response({"status": "ok", "count": len(segments), "segments": segments})
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("/phonemes failed: %s", exc)
            return _json_response({"error": str(exc)}, status_code=500)

    starlette_app.add_route("/health", http_health, methods=["GET"])
    starlette_app.add_route("/", http_index, methods=["GET", "POST"])
    starlette_app.add_route("/speak", http_speak, methods=["POST"])
    starlette_app.add_route("/speak_batch", http_speak_batch, methods=["POST"])
    starlette_app.add_route("/phonemes", http_phonemes, methods=["POST"])

    return server, starlette_app


if __name__ == "__main__":
    host = os.environ.get("VIBETYPE_API_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("VIBETYPE_API_PORT", "9032"))
    except ValueError:
        port = 9032

    server, http_app = create_server(host, port)
    print(
        f"VibeTTS MCP HTTP server listening on http://{host}:{port}",
        file=sys.stderr,
        flush=True,
    )

    import uvicorn

    uvicorn.run(http_app, host=host, port=port, log_level="info")
