# This file makes the server directory a Python sub-package

# Re-export for convenience and IDE resolution
try:
    from .fastmcp import FastMCP  # noqa: F401
except Exception:
    # Module may not be generated/available in some minimal envs
    pass
