import json

import pytest

from enrichment import net


def test_parse_sse_reply():
    first = {"jsonrpc": "2.0", "id": 1, "result": {"partial": True}}
    last = {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "{\"a\": 1}"}]}}
    raw = f"event: message\ndata: {json.dumps(first)}\n\nevent: message\ndata: {json.dumps(last)}\n\n"
    assert net.parse_rpc_body("text/event-stream", raw) == last


def test_parse_json_reply():
    body = {"jsonrpc": "2.0", "id": 1, "result": {"content": []}}
    assert net.parse_rpc_body("application/json", json.dumps(body)) == body


def test_tool_result_parses_text_block():
    reply = {"result": {"content": [{"type": "text", "text": "{\"company\": {\"name\": \"telli\"}}"}]}}
    assert net.tool_result(reply) == {"company": {"name": "telli"}}


def test_mcp_error_raises():
    reply = {"result": {"isError": True, "content": [{"type": "text", "text": "404 data not found"}]}}
    with pytest.raises(net.ToolError, match="404 data not found"):
        net.tool_result(reply)


def test_rpc_error_raises():
    with pytest.raises(net.ToolError, match="bad params"):
        net.tool_result({"error": {"code": -32602, "message": "bad params"}})
