import sys
import os
from typing import Any, Dict, List, Union
import contextlib

# Ensure project root is on sys.path for imports like `from core import tts`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Use stderr for any human-readable logs to avoid corrupting stdio protocol frames
print("--- STARTING VibeTTS MCP STDIO SERVER ---", file=sys.stderr, flush=True)

try:
    # FastMCP provides a concise way to define tools for the MCP protocol over stdio
    from mcp.server.fastmcp import FastMCP  # type: ignore
except Exception as e:
    # Provide a clear error for the IDE logs if the dependency is missing
    print(
        "ERROR: Python package 'mcp' is not installed.\n"
        "Install with your project interpreter: pip install mcp\n"
        f"Detailed import error: {e}",
        file=sys.stderr,
        flush=True,
    )
    # Exit with non-zero so the IDE knows the server failed to start
    raise

# Import TTS core after path fix; guard stdout during import to keep stdio clean
with contextlib.redirect_stdout(sys.stderr):
    from core import tts as core_tts  # noqa: E402

app = FastMCP("vibetts-mcp")


@app.tool()
def health() -> str:
    """Simple readiness check for IDE tooling."""
    return "ok"


@app.tool()
def speak(text: str) -> Dict[str, Any]:
    """Speak a single line using the app's configured TTS."""
    if not isinstance(text, str) or not text.strip():
        return {"error": "Missing or invalid 'text'"}
    try:
        core_tts.speak_text(text)
        return {"status": "accepted", "queued": 1}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


@app.tool()
def speak_batch(items: List[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """Speak multiple items sequentially.

    Each item can be a string or an object with a 'text' field.
    """
    if not isinstance(items, list) or not items:
        return {"error": "Missing or empty 'items' array"}
    accepted = 0
    try:
        for it in items:
            t = it.get("text") if isinstance(it, dict) else it
            if not isinstance(t, str) or not t.strip():
                continue
            core_tts.speak_text(t)
            accepted += 1
        return {"status": "accepted", "queued": accepted}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e), "queued": accepted}


@app.tool()
def phonemes(text: str, language: str = "Auto-Detect") -> Dict[str, Any]:
    """Return phoneme/segment info using Kokoro TTS if available."""
    if not isinstance(text, str) or not text.strip():
        return {"error": "Missing 'text'"}
    try:
        # Ensure Kokoro TTS is initialized before use
        core_tts._initialize_kokoro_tts()  # type: ignore[attr-defined]
        kt = getattr(core_tts, "kokoro_tts_instance", None)
        if not kt:
            return {"error": "Kokoro TTS not initialized or is disabled."}
        segments = kt.phonemize_text(text, language_name=language)
        if not segments or any(seg.get("error") for seg in segments):
            return {"error": "Phoneme generation failed.", "details": segments}
        return {"status": "ok", "count": len(segments), "segments": segments}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


if __name__ == "__main__":
    # Run with stdio transport so IDEs (JetBrains, etc.) can discover via mcp.json
    print("VibeTTS MCP stdio server is starting...", file=sys.stderr, flush=True)
    app.run()
    print("VibeTTS MCP stdio server stopped.", file=sys.stderr, flush=True)
