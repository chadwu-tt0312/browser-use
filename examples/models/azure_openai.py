"""
Simple try of the agent.

@dev You need to add AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT to your environment variables.
"""

import asyncio
import os
import sys

import anyio
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Retrieve Azure-specific environment variables
azure_openai_api_key = os.getenv('AZURE_OPENAI_KEY')
azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')

if not azure_openai_api_key or not azure_openai_endpoint:
	raise ValueError('AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT is not set')

browser = Browser(
	config=BrowserConfig(
		headless=True,  # 啟用無頭模式
		disable_security=True,  # 可選：如果需要禁用某些安全限制
		# NOTE: you need to close your chrome browser - so that this can open your browser in debug mode
		# browser_binary_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
	)
)

# Initialize the Azure OpenAI client
llm = AzureChatOpenAI(
	model_name='gpt-4o-mini',
	openai_api_key=azure_openai_api_key,
	azure_endpoint=azure_openai_endpoint,
	deployment_name='gpt-4o-mini',
	api_version='2024-12-01-preview',
)


async def run_search(task: str = None):
	if task is None:
		task = '請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。'

	agent = Agent(
		task=task,
		llm=llm,
		enable_memory=True,
		# browser=browser,
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

	# if agent.state.last_result and agent.state.last_result[-1].extracted_content:
	# 	content = agent.state.last_result[-1].extracted_content
	# 	async with await anyio.open_file('result.md', 'w', encoding='utf-8') as f:
	# 		await f.write(content)
	# 	return content
	# return ''


if __name__ == '__main__':
	asyncio.run(run_search())
