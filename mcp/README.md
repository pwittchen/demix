# demix-mcp

Model Context Protocol (MCP) server for [demix](https://github.com/pwittchen/demix).

Exposes demix's audio-processing capabilities (download from YouTube, stem
separation, key detection, tempo/pitch shifting, segment cutting) as MCP
tools that LLM clients (Claude Desktop, Claude Code, etc.) can call.

## Why a separate package?

`demix` is pinned to Python 3.8 because spleeter does not support newer
versions. The official `mcp` SDK requires Python 3.10+. The two cannot
share an environment, so `demix-mcp` is a thin wrapper that shells out
to the `demix` CLI binary on PATH.

## Install

Install demix in its own environment (Python 3.8):

```bash
pipx install demix
```

Install the MCP server in a Python 3.10+ environment:

```bash
pipx install ./mcp        # from a checkout of the demix repo
# or, once published:
# pipx install demix-mcp
```

Both `demix` and `demix-mcp` need to be reachable from the same PATH that
your MCP client uses.

## Configure an MCP client

### Claude Desktop / Claude Code

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`
(or your client's equivalent):

```json
{
  "mcpServers": {
    "demix": {
      "command": "demix-mcp",
      "cwd": "/Users/you/demix-workspace"
    }
  }
}
```

The `cwd` is where demix will create `output/` and cache `pretrained_models/`.
Pick a stable directory so spleeter models do not redownload every run.

## Tools

| Tool             | Purpose                                                      |
|------------------|--------------------------------------------------------------|
| `process_audio`  | Process an audio source (file/url/search) end-to-end.        |
| `detect_key`     | Detect the musical key of a local audio file.                |
| `search_youtube` | Resolve a search query to its top YouTube URL + title.       |
| `clean`          | Remove demix output and/or cached spleeter models.           |
