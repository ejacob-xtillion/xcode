import asyncio
from pathlib import Path

from agent.app.engine.mcp_tool_call_cache import (
    DiskMcpToolCallCacheInterceptor,
    normalize_tool_args_for_cache_key,
    tool_call_cache_fingerprint,
)
from agent.app.core.settings import AppSettings
from langchain_mcp_adapters.interceptors import MCPToolCallRequest
from mcp.types import CallToolResult, TextContent


def test_tool_call_cache_fingerprint_stable_ordering():
    a = tool_call_cache_fingerprint("neo4j", "read", {"x": 1, "y": 2})
    b = tool_call_cache_fingerprint("neo4j", "read", {"y": 2, "x": 1})
    assert a == b


def test_read_neo4j_cypher_fingerprint_ignores_extra_whitespace():
    a = tool_call_cache_fingerprint(
        "neo4j",
        "read_neo4j_cypher",
        {"query": "MATCH (n) RETURN n\nLIMIT 5"},
    )
    b = tool_call_cache_fingerprint(
        "neo4j",
        "read_neo4j_cypher",
        {"query": "MATCH  (n)\n   RETURN   n  LIMIT 5"},
    )
    assert a == b


def test_normalize_tool_args_neo4j_known_keys():
    raw = {"query": "  MATCH (x)\nRETURN x  "}
    out = normalize_tool_args_for_cache_key("read_neo4j_cypher", raw)
    assert out["query"] == "MATCH (x) RETURN x"


def test_app_settings_mcp_tool_call_cache_model_defaults():
    """Schema defaults (runtime .env / OS env can override)."""
    assert AppSettings.model_fields["mcp_tool_call_cache_enabled"].default is False
    assert AppSettings.model_fields["mcp_tool_call_cache_ttl_seconds"].default == 86400
    skip = AppSettings.model_fields["mcp_tool_call_cache_skip_tools"].default
    assert isinstance(skip, str) and "write_file" in skip


def test_cache_hit_skips_handler(tmp_path: Path) -> None:
    cache_dir = tmp_path / "c"
    ic = DiskMcpToolCallCacheInterceptor(cache_dir=cache_dir, skip_tools=frozenset(), ttl_seconds=3600)
    path_key = tool_call_cache_fingerprint("srv", "t", {"k": "v"})
    path = cache_dir / path_key[:2] / path_key[2:4] / f"{path_key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    r = CallToolResult(content=[TextContent(type="text", text="cached")], isError=False)
    path.write_text(r.model_dump_json(), encoding="utf-8")

    async def handler(req: MCPToolCallRequest) -> CallToolResult:
        raise AssertionError("handler should not run")

    async def run() -> None:
        req = MCPToolCallRequest(name="t", args={"k": "v"}, server_name="srv")
        out = await ic(req, handler)
        assert isinstance(out, CallToolResult)
        assert out.content[0].text == "cached"

    asyncio.run(run())


def test_skip_tools_bypasses_cache(tmp_path: Path) -> None:
    ic = DiskMcpToolCallCacheInterceptor(
        cache_dir=tmp_path / "c",
        skip_tools=frozenset({"write_file"}),
        ttl_seconds=3600,
    )
    called = False

    async def handler(req: MCPToolCallRequest) -> CallToolResult:
        nonlocal called
        called = True
        return CallToolResult(content=[TextContent(type="text", text="live")], isError=False)

    async def run() -> None:
        req = MCPToolCallRequest(name="write_file", args={"p": "/x"}, server_name="fs")
        out = await ic(req, handler)
        assert called
        assert out.content[0].text == "live"

    asyncio.run(run())


def test_ttl_expires_entry(tmp_path: Path) -> None:
    cache_dir = tmp_path / "c"
    ic = DiskMcpToolCallCacheInterceptor(cache_dir=cache_dir, skip_tools=frozenset(), ttl_seconds=1)
    path_key = tool_call_cache_fingerprint("srv", "t", {"k": "v"})
    path = cache_dir / path_key[:2] / path_key[2:4] / f"{path_key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    r = CallToolResult(content=[TextContent(type="text", text="stale")], isError=False)
    path.write_text(r.model_dump_json(), encoding="utf-8")
    old = path.stat().st_mtime - 10
    os_utime = __import__("os").utime
    os_utime(path, (old, old))

    called = False

    async def handler(req: MCPToolCallRequest) -> CallToolResult:
        nonlocal called
        called = True
        return CallToolResult(content=[TextContent(type="text", text="fresh")], isError=False)

    async def run() -> None:
        req = MCPToolCallRequest(name="t", args={"k": "v"}, server_name="srv")
        out = await ic(req, handler)
        assert called
        assert out.content[0].text == "fresh"

    asyncio.run(run())
