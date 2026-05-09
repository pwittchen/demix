"""MCP server for the demix CLI.

Exposes demix audio-processing capabilities (download/search/process,
key detection, cleanup) over the Model Context Protocol via stdio.

The server is a thin wrapper that shells out to the `demix` CLI binary,
which must be installed and available on PATH. This keeps the MCP server
(Python 3.10+, requires the `mcp` SDK) decoupled from demix's own
Python 3.8 environment (locked by spleeter).
"""

__version__ = "0.1.0"

from demix_mcp.server import main, mcp

__all__ = ["main", "mcp", "__version__"]
