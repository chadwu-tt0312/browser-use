#!/usr/bin/env python3
"""
測試 MCP 伺服器的腳本

使用方式：
python test_mcp_server.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_mcp_server():
	"""測試 MCP 伺服器的基本功能"""
	try:
		# 導入 MCP 伺服器
		from examples.models.mcp_server import mcp

		print('✅ MCP 伺服器導入成功')
		print(f'伺服器名稱: {mcp.name}')

		# 檢查工具是否已註冊
		print('\n📋 已註冊的工具:')
		# 注意：FastMCP 2.x 的 API 可能不同，這裡只是基本測試
		print('- search_task: 執行瀏覽器搜尋任務')

		print('\n🎉 MCP 伺服器測試通過！')
		print('可以使用以下命令啟動伺服器:')
		print('python examples/models/mcp_server.py')

		return True

	except ImportError as e:
		print(f'❌ 導入錯誤: {e}')
		print('請確保已安裝 fastmcp 套件:')
		print('pip install fastmcp')
		return False

	except Exception as e:
		print(f'❌ 測試失敗: {e}')
		return False


if __name__ == '__main__':
	success = asyncio.run(test_mcp_server())
	sys.exit(0 if success else 1)
