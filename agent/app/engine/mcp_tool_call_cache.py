"""Disk-backed cache for MCP tool call results (langchain-mcp-adapters interceptors)."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from collections.abc import Awaitable, Callable
from hashlib import sha256
from pathlib import Path
from typing import Any

from langchain_mcp_adapters.interceptors import MCPToolCallRequest, MCPToolCallResult
from mcp.types import CallToolResult

from app.core.logger import get_logger
from app.core.settings import AppSettings

logger = get_logger()

_write_lock = asyncio.Lock()


def _agent_project_root() -> Path:
    """Directory that contains the agent's pyproject.toml (e.g. /app in Docker, repo/agent locally).

    ``settings._xcode_repo_root()`` walks parents[3] from ``app/core/settings.py``, which resolves
    to filesystem ``/`` when the app lives at ``/app/app/core/...`` — wrong for on-disk cache.
    """
    cur = Path(__file__).resolve().parent
    for _ in range(12):
        if (cur / "pyproject.toml").is_file():
            return cur
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return Path(__file__).resolve().parents[2]


def _default_cache_dir() -> Path:
    return _agent_project_root() / ".cache" / "mcp_tool_calls"


def normalize_tool_args_for_cache_key(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Copy of tool args normalized so equivalent invocations share one cache key."""
    out = dict(args)
    if tool_name == "read_neo4j_cypher":
        for key in ("query", "cypher", "statement", "cypherQuery"):
            val = out.get(key)
            if isinstance(val, str):
                out[key] = " ".join(val.strip().split())
    return out


def _cache_key_path(cache_dir: Path, key_hex: str) -> Path:
    return cache_dir / key_hex[:2] / key_hex[2:4] / f"{key_hex}.json"


def tool_call_cache_fingerprint(server_name: str, tool_name: str, args: dict[str, Any]) -> str:
    key_args = normalize_tool_args_for_cache_key(tool_name, args)
    payload = json.dumps(
        {"server": server_name, "tool": tool_name, "args": key_args}, sort_keys=True, default=str
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _parse_skip_tools(csv: str) -> frozenset[str]:
    return frozenset(t.strip() for t in csv.split(",") if t.strip())


class DiskMcpToolCallCacheInterceptor:
    """Caches successful CallToolResult payloads under a stable content-addressed path."""

    def __init__(
        self,
        *,
        cache_dir: Path,
        skip_tools: frozenset[str],
        ttl_seconds: int,
    ) -> None:
        self._cache_dir = cache_dir
        self._skip_tools = skip_tools
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_settings(cls, settings: AppSettings) -> DiskMcpToolCallCacheInterceptor:
        raw_dir = (settings.mcp_tool_call_cache_dir or "").strip()
        cache_dir = Path(raw_dir).expanduser() if raw_dir else _default_cache_dir()
        skip = _parse_skip_tools(settings.mcp_tool_call_cache_skip_tools)
        return cls(
            cache_dir=cache_dir,
            skip_tools=skip,
            ttl_seconds=settings.mcp_tool_call_cache_ttl_seconds,
        )

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler: Callable[[MCPToolCallRequest], Awaitable[MCPToolCallResult]],
    ) -> MCPToolCallResult:
        if request.name in self._skip_tools:
            return await handler(request)

        key = tool_call_cache_fingerprint(request.server_name, request.name, request.args)
        path = _cache_key_path(self._cache_dir, key)

        hit = await asyncio.to_thread(self._try_read, path)
        if hit is not None:
            logger.info(
                "mcp_tool_call_cache_hit",
                server=request.server_name,
                tool=request.name,
                key_prefix=key[:12],
            )
            return hit

        result = await handler(request)

        if isinstance(result, CallToolResult) and not result.isError:
            async with _write_lock:
                await asyncio.to_thread(self._write_atomic, path, result)
            logger.info(
                "mcp_tool_call_cache_store",
                server=request.server_name,
                tool=request.name,
                key_prefix=key[:12],
            )

        return result

    def _try_read(self, path: Path) -> CallToolResult | None:
        if not path.is_file():
            return None
        if self._ttl_seconds > 0:
            age = time.time() - path.stat().st_mtime
            if age > self._ttl_seconds:
                try:
                    path.unlink()
                except OSError:
                    pass
                return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CallToolResult.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.warning("mcp_tool_call_cache_read_failed", path=str(path), error=str(e))
            return None

    def _write_atomic(self, path: Path, result: CallToolResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = result.model_dump_json()
        fd: int | None = None
        tmp: str | None = None
        try:
            fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            fd = None
            os.replace(tmp, path)
            tmp = None
        except OSError as e:
            logger.warning("mcp_tool_call_cache_write_failed", path=str(path), error=str(e))
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp is not None:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass


def build_tool_call_cache_interceptors(settings: AppSettings) -> list[DiskMcpToolCallCacheInterceptor] | None:
    if not settings.mcp_tool_call_cache_enabled:
        return None
    return [DiskMcpToolCallCacheInterceptor.from_settings(settings)]


__all__ = [
    "DiskMcpToolCallCacheInterceptor",
    "build_tool_call_cache_interceptors",
    "normalize_tool_args_for_cache_key",
    "tool_call_cache_fingerprint",
]
