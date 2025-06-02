#!/bin/bash

echo "啟動 Browser-Use MCP 伺服器..."
echo

# 檢查是否安裝了 fastmcp
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "正在安裝 fastmcp..."
    uv pip install fastmcp
    echo
fi

# 啟動 MCP 伺服器
echo "啟動 MCP 伺服器在 http://0.0.0.0:8082"
echo "按 Ctrl+C 停止伺服器"
echo

uv run examples/models/mcp_server.py 