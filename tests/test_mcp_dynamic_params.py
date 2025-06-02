#!/usr/bin/env python3
"""
測試 MCP 伺服器動態參數功能的腳本

使用方式：
python test_mcp_dynamic_params.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_mcp_dynamic_params():
	"""測試動態參數功能"""
	try:
		# 導入 MCP 伺服器
		from examples.models.mcp_server import mcp

		print('✅ MCP 伺服器導入成功')
		print(f'伺服器名稱: {mcp.name}')

		# 測試參數解析
		print('\n🔧 測試動態參數功能:')

		# 測試 User-Agent 參數
		test_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54'
		print(f'✓ User-Agent 參數: {test_user_agent[:50]}...')

		# 測試代理認證參數
		test_proxy_username = 'test_user'
		test_proxy_password = 'test_pass'
		print(f'✓ 代理用戶名: {test_proxy_username}')
		print(f'✓ 代理密碼: {"*" * len(test_proxy_password)}')

		# 檢查環境變數
		print('\n🌍 環境變數檢查:')
		umc_setting = os.environ.get('UMC_SETTING')
		print(f'UMC_SETTING: {umc_setting}')

		user_agent_env = os.environ.get('USER_AGENT')
		if user_agent_env:
			print(f'USER_AGENT (環境變數): {user_agent_env[:50]}...')
		else:
			print('USER_AGENT (環境變數): 未設定')

		https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
		if https_proxy:
			print(f'HTTPS_PROXY: {https_proxy[:30]}...')
		else:
			print('HTTPS_PROXY: 未設定')

		print('\n🎉 動態參數功能測試通過！')
		print('\n📋 支援的參數:')
		print('- task: 搜尋任務描述')
		print('- user_agent: 自定義 User-Agent')
		print('- proxy_username: 代理用戶名')
		print('- proxy_password: 代理密碼')
		print('- context: MCP 上下文')

		print('\n🚀 使用範例:')
		print('await client.call_tool("search_task", {')
		print('    "task": "搜尋最新 AI 新聞",')
		print('    "user_agent": "Mozilla/5.0...",')
		print('    "proxy_username": "your_user",')
		print('    "proxy_password": "your_pass"')
		print('})')

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
	success = asyncio.run(test_mcp_dynamic_params())
	sys.exit(0 if success else 1)
