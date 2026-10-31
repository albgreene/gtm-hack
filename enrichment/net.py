"""Small HTTP helpers: JSON requests, page fetches and MCP tool calls over HTTP (AI Ark, Needle)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import USER_AGENT


class HTTPError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status, self.body = status, body


class ToolError(RuntimeError):
    """An MCP tool answered with an error (for AI Ark this includes "404 data not found")."""


def _request(url: str, data: bytes | None, headers: dict, method: str, timeout: float):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **headers}, method=method)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        raise HTTPError(exc.code, exc.read().decode(errors="replace")) from exc


def get_json(url: str, headers: dict | None = None, timeout: float = 20):
    with _request(url, None, {"Accept": "application/json", **(headers or {})}, "GET", timeout) as resp:
        return json.loads(resp.read().decode() or "null")


def post_json(url: str, body, headers: dict | None = None, timeout: float = 30, method: str = "POST"):
    data = json.dumps(body, ensure_ascii=False).encode()
    hdrs = {"Content-Type": "application/json", "Accept": "application/json", **(headers or {})}
    with _request(url, data, hdrs, method, timeout) as resp:
        raw = resp.read().decode()
    return json.loads(raw) if raw.strip() else None


def get_text(url: str, timeout: float = 15, max_bytes: int = 3_000_000) -> tuple[str, str]:
    """Fetch a page; returns (final URL after redirects, decoded body)."""
    hdrs = {"Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5", "Accept-Language": "en,de;q=0.8"}
    with _request(url, None, hdrs, "GET", timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.geturl(), resp.read(max_bytes).decode(charset, errors="replace")


def parse_rpc_body(content_type: str, raw: str) -> dict:
    """A JSON-RPC reply arrives either as plain JSON or as server-sent events; take the last event."""
    if "event-stream" in (content_type or ""):
        datas = [line[5:].strip() for line in raw.splitlines() if line.startswith("data:")]
        raw = datas[-1] if datas else "{}"
    return json.loads(raw) if raw.strip() else {}


def tool_result(reply: dict):
    """The parsed JSON (or text) of a tools/call reply; raises ToolError for protocol or tool errors."""
    if reply.get("error"):
        raise ToolError(str(reply["error"].get("message") or reply["error"]))
    result = reply.get("result") or {}
    texts = [block.get("text", "") for block in result.get("content") or [] if block.get("type") == "text"]
    text = "\n".join(texts).strip()
    if result.get("isError"):
        raise ToolError(text or "tool error")
    if result.get("structuredContent") is not None and not text:
        return result["structuredContent"]
    try:
        parsed = json.loads(text) if text else None
    except json.JSONDecodeError:
        return text
    if isinstance(parsed, dict) and parsed.get("error") and len(parsed) == 1:
        raise ToolError(str(parsed["error"]))
    return parsed


def mcp_call(url: str, headers: dict, tool: str, arguments: dict, timeout: float = 60):
    """Call one tool on a stateless streamable-HTTP MCP server (both AI Ark and Needle work without a session)."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    hdrs = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", **headers}
    with _request(url, json.dumps(body).encode(), hdrs, "POST", timeout) as resp:
        reply = parse_rpc_body(resp.headers.get("Content-Type", ""), resp.read().decode(errors="replace"))
    return tool_result(reply)
