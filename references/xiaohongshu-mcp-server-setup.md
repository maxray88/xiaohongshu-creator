# Xiaohongshu MCP Server Setup Guide

## Overview

The `xiaohongshu-mcp-server` npm package provides MCP tools for Xiaohongshu automation. This guide covers the full setup including known bugs and workarounds.

## Prerequisites

- Node.js 16+ (for npx)
- Python 3.11+ (fastmcp requires 3.10+; system Python 3.9 on macOS is NOT sufficient)
- Homebrew (recommended for Python install)

## Quick Install

```bash
# 1. Install Python 3.11
brew install python@3.11

# 2. Install npm package
npm install -g xiaohongshu-mcp-server

# 3. Install Python deps (fix requirements.txt first: python-dotenv>=1.1.0)
/usr/local/bin/python3.11 -m pip install -r /usr/local/lib/node_modules/xiaohongshu-mcp-server/requirements.txt

# 4. Install Playwright Chromium
/usr/local/bin/python3.11 -m playwright install chromium
```

## Known Bug: Missing Cache Module

The npm package is missing `src/infrastructure/cache/`. Create it:

```bash
mkdir -p /usr/local/lib/node_modules/xiaohongshu-mcp-server/src/infrastructure/cache

cat > /usr/local/lib/node_modules/xiaohongshu-mcp-server/src/infrastructure/cache/__init__.py << 'EOF'
from src.infrastructure.cache.cache import cache_manager
__all__ = ["cache_manager"]
EOF

cat > /usr/local/lib/node_modules/xiaohongshu-mcp-server/src/infrastructure/cache/cache.py << 'EOF'
"""Cache manager for Xiaohongshu MCP server."""
import asyncio, time
from typing import Any, Optional, Dict, Tuple
from src.core.logging.logger import logger

class CacheManager:
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        logger.info("Cache manager initialized")
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                v, exp = self._cache[key]
                if time.time() < exp: return v
                del self._cache[key]
            return None
    async def set(self, key: str, value: Any, ttl: int = 600) -> None:
        async with self._lock: self._cache[key] = (value, time.time() + ttl)
    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache: del self._cache[key]; return True
            return False
    async def clear(self) -> int:
        async with self._lock: c = len(self._cache); self._cache.clear(); return c
    async def cleanup_expired(self) -> int:
        async with self._lock:
            now = time.time()
            expired = [k for k, (_, e) in self._cache.items() if now >= e]
            for k in expired: del self._cache[k]
            return len(expired)

cache_manager = CacheManager()
EOF
```

Also copy to npx cache:
```bash
NPX=~/.npm/_npx/eebcc7e98fb1225b/node_modules/xiaohongshu-mcp-server/src/infrastructure/cache
mkdir -p $NPX && cp /usr/local/lib/node_modules/xiaohongshu-mcp-server/src/infrastructure/cache/*.py $NPX/
```

## Hermes Config

In `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  xiaohongshu:
    command: /usr/local/bin/python3.11
    args: [-m, src.interfaces.mcp.server]
    env:
      PYTHONPATH: /usr/local/lib/node_modules/xiaohongshu-mcp-server
      XIAOHONGSHU_DATA_DIR: /Users/maochundong/.xiaohongshu-mcp/data
    timeout: 120
    connect_timeout: 60
```

> ⚠️ Do NOT use `npx` as command — it resolves to system Python 3.9, not 3.11.
