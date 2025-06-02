"""
Simple try of the agent.

@dev You need to add AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT to your environment variables.
@memo: 只能呼叫一次，之後就會 "Result failed"
"""

# 處理 "Received request before initialization was complete" 錯誤
# 這是一個已知的 MCP SSE 問題，當客戶端在伺服器重啟後沒有正確重新初始化連接時會發生
# 參考：https://github.com/modelcontextprotocol/python-sdk/issues/423

# Default Request Timeout = 10 * 1000ms = 10s (需要變更為 5 分鐘) (300000ms)
# Default Maximum Total Timeout = 60 * 1000ms = 60s (需要變更為 10 分鐘) (600000ms)

import asyncio
import os
import sys
from urllib.parse import urlparse

import anyio
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from mcp.server.fastmcp import Context, FastMCP

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig, ProxySettings
from browser_use.browser.context import BrowserContextConfig

# Load environment variables from .env file
load_dotenv()

# Retrieve Azure-specific environment variables
azure_openai_api_key = os.getenv('AZURE_OPENAI_KEY')
azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
user_agent = os.getenv('USER_AGENT')

if not azure_openai_api_key or not azure_openai_endpoint:
	raise ValueError('AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT is not set')

proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
if proxy_url:
	# print("proxy_url", proxy_url)
	parsed = urlparse(proxy_url)
	proxy = ProxySettings(
		server=f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
		username=parsed.username if parsed.username else None,
		password=parsed.password if parsed.password else None,
	)

browser = Browser(
	config=BrowserConfig(
		headless=False,
		proxy=proxy if proxy_url else None,
		new_context_config=BrowserContextConfig(
			user_agent=user_agent,
			ignore_https_errors=True,  # 忽略 SSL 憑證錯誤
			# disable_security=True,
		),
	)
)

# Initialize the Azure OpenAI client
llm = AzureChatOpenAI(
	# model_name='gpt-4.1',	# fail
	model_name='gpt-4o-mini',
	# model_name='gpt-4o',
	openai_api_key=azure_openai_api_key,
	azure_endpoint=azure_openai_endpoint,
	deployment_name='gpt-4o-mini',
	# deployment_name='gpt-4o',
	api_version='2024-12-01-preview',
)
agent = None

# Initialize FastMCP server
mcp = FastMCP('browser-use-mcp', host='0.0.0.0', port=8082)


@mcp.tool()
async def perform_search(task: str, context: Context):
	"""Perform the actual search and return the final result."""
	try:
		result = await run_browser_agent(task=task)
		# await context.session.send_log_message(
		# 	level='info', data={'message': f'Task completed: {task}', 'result': result}
		# )
		return result
	except Exception as e:
		error_msg = f'Error during search: {str(e)}'
		await context.session.send_log_message(level='error', data={'message': error_msg})
		return error_msg


@mcp.tool()
async def stop_search(*, context: Context):
	"""Stop a running browser agent search by task ID."""
	if agent is not None:
		await agent.stop()
	return 'Running Agent stopped'


async def run_browser_agent(task: str):
	"""Run the browser-use agent with the specified task."""
	global agent
	try:
		agent = Agent(
			task=task,
			llm=llm,
			# enable_memory=True,
			enable_memory=False,
			browser=browser,
		)

		result = await agent.run(max_steps=10)
		# 取得最後結果
		agent_message = None
		if result.is_done():
			agent_message = result.history[-1].result[0].extracted_content
		if agent_message is None:
			agent_message = 'Oops! Something went wrong while running Browser-Use.'
		else:
			async with await anyio.open_file('result.md', 'w', encoding='utf-8') as f:
				await f.write(agent_message)
		return agent_message
	except asyncio.CancelledError:
		return 'Task was cancelled'

	except Exception as e:
		return f'Error during execution: {str(e)}'
	finally:
		await browser.close()


if __name__ == '__main__':
	mcp.run(transport='sse')

# 運行方式：
# 1. 使用預設設定（SSE transport，0.0.0.0:8082）：
#    uv run examples/models/mcp_azure.py
