"""
使用 MCP (Model Context Protocol) 機制的 Browser-Use 伺服器

使用方式：
uv run examples/models/mcp_server.py

測試方式：
可以使用 MCP 客戶端連接到 http://localhost:8082
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastmcp import Context, FastMCP

# 設置日誌
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'mcp_server.log'
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s %(message)s',
	handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入現有的模組
from examples.models.azure_openai import run_search as azure_search
from examples.models.gemini import run_search as gemini_search
from examples.models.gpt_4o import run_search as gpt4o_search

# 載入環境變數
load_dotenv()

umc_setting = os.environ.get('UMC_SETTING')
# print('umc_setting =', umc_setting)
if umc_setting == 'true':
	model_type = 'azure'
else:
	model_type = 'gemini'

timeout_minutes = None

# 初始化 FastMCP 伺服器
mcp = FastMCP('browser-use-mcp')


@mcp.tool()
async def search_task(
	task: str = '',
	user_agent: str = '',
	proxy_username: str = '',
	proxy_password: str = '',
	context: Context = None,
) -> str:
	"""Execute browser search task using Browser-Use agent.

	This tool performs web searches and data extraction using an AI-powered browser automation agent.
	It supports multiple AI models and can handle complex search tasks with natural language instructions.

	Args:
		task: The search task description in natural language (required, cannot be empty)
		user_agent: Custom User-Agent string to override default (leave empty to use default)
		proxy_username: Username for proxy authentication (leave empty if not required)
		proxy_password: Password for proxy authentication (leave empty if not required)
		context: MCP context for logging and progress reporting (optional)

	Returns:
		Search results as formatted text content, or error message if task is empty

	Examples:
		- "請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接"
		- "Search for Python tutorials on Google and summarize the top 5 results"
		- "Find information about climate change on Wikipedia and extract key facts"

	Note:
		- task parameter is required and cannot be empty string
		- user_agent parameter allows you to specify browser version for proxy compatibility
		- proxy credentials can be provided via parameters instead of environment variables
		- context parameter is optional for MCP logging functionality
	"""
	task_id = f'{datetime.now().timestamp()}'
	logger.info(f'收到新的 search 請求 {task_id}: {task}')

	if task == '':
		return '請提供任務描述 (task)'

	# 設定超時時間（預設為 10 分鐘）
	timeout_seconds = (timeout_minutes or 10) * 60

	start_time = datetime.now()
	try:
		if model_type == 'gemini':
			logger.info('使用 Gemini 執行任務 (標準模式)')
			result = await asyncio.wait_for(
				gemini_search(task),
				timeout=timeout_seconds,
			)
		elif model_type == 'openai':
			logger.info('使用 OpenAI 執行任務 (標準模式)')
			result = await asyncio.wait_for(
				gpt4o_search(task),
				timeout=timeout_seconds,
			)
		elif model_type == 'azure':
			logger.info('使用 Azure 執行任務 (支援動態代理參數)')
			# 傳遞額外參數給 azure_search，將空字串轉換為 None
			result = await asyncio.wait_for(
				azure_search(
					task,
					user_agent=user_agent if user_agent else None,
					proxy_username=proxy_username if proxy_username else None,
					proxy_password=proxy_password if proxy_password else None,
				),
				timeout=timeout_seconds,
			)
		else:
			error_msg = f'不支援的模型類型: {model_type}'
			logger.error(error_msg)
			raise ValueError(error_msg)

		execution_time = (datetime.now() - start_time).total_seconds()
		logger.info(f'任務 {task_id} 執行完成，耗時: {execution_time:.2f} 秒')

		# 發送日誌訊息到客戶端（如果有 context）
		if context:
			await context.session.send_log_message(
				level='info',
				data={
					'message': '任務執行完成',
					'task_id': task_id,
					'execution_time': execution_time,
					'model_type': model_type,
				},
			)

		return result

	except asyncio.TimeoutError:
		execution_time = (datetime.now() - start_time).total_seconds()
		error_msg = f'任務 {task_id} 執行超時 (超過 {timeout_minutes or 10} 分鐘)'
		logger.error(error_msg)

		if context:
			await context.session.send_log_message(level='error', data={'message': error_msg, 'task_id': task_id})

		return error_msg

	except Exception as e:
		execution_time = (datetime.now() - start_time).total_seconds()
		error_msg = f'任務 {task_id} 執行失敗: {str(e)}'
		logger.error(error_msg)

		if context:
			await context.session.send_log_message(
				level='error', data={'message': error_msg, 'task_id': task_id, 'error': str(e)}
			)

		return error_msg


if __name__ == '__main__':
	logger.info('啟動 MCP 伺服器')
	# 使用 SSE transport 在指定的 host 和 port 上運行
	mcp.run(transport='sse', host='0.0.0.0', port=8082)  # FastMCP 2.3.4 版本之後支援 host & port
