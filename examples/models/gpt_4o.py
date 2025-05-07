"""
Simple try of the agent.

@dev You need to add OPENAI_API_KEY to your environment variables.
"""

import os
import sys

import anyio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from langchain_openai import ChatOpenAI

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig

browser = Browser(
	config=BrowserConfig(
		headless=True,  # 啟用無頭模式
		disable_security=True,  # 可選：如果需要禁用某些安全限制
	)
)

llm = ChatOpenAI(model='gpt-4o-mini')
# llm = ChatOpenAI(model='GPT-4.1-nano')


async def run_search(task: str = None):
	if task is None:
		task = '請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。'

	agent = Agent(
		task=task,
		llm=llm,
		# browser=browser,
	)

	await agent.run(max_steps=10)
	# 取得最後結果
	if agent.state.last_result and agent.state.last_result[-1].extracted_content:
		content = agent.state.last_result[-1].extracted_content
		async with await anyio.open_file('result.md', 'w', encoding='utf-8') as f:
			await f.write(content)
		return content
	return ''


if __name__ == '__main__':
	asyncio.run(run_search())
