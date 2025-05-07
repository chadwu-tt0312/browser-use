"""
Simple try of the agent.

@dev You need to add OPENAI_API_KEY to your environment variables.
"""

import os
import sys

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
agent = Agent(
	# task='Go to amazon.com, search for laptop, sort by best rating, and give me the price of the first result',
	task="請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。",
	llm=llm,
	browser=browser,
)


async def main():
	await agent.run(max_steps=10)
	# 取得最後結果
	if agent.state.last_result and agent.state.last_result[-1].extracted_content:
		with open("result.md", "w", encoding="utf-8") as f:
			f.write(agent.state.last_result[-1].extracted_content)
	# input('Press Enter to continue...')


asyncio.run(main())
