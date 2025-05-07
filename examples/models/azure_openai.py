"""
Simple try of the agent.

@dev You need to add AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT to your environment variables.
"""

import os
import sys

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from langchain_openai import AzureChatOpenAI

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig


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

agent = Agent(
	# task='Go to amazon.com, search for laptop, sort by best rating, and give me the price of the first result',
	task='請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。',
	llm=llm,
	# enable_memory=True,
	# browser=browser,
)


async def main():
	await agent.run(max_steps=10)
	# 取得最後結果
	if agent.state.last_result and agent.state.last_result[-1].extracted_content:
		with open('result.md', 'w', encoding='utf-8') as f:
			f.write(agent.state.last_result[-1].extracted_content)
	# input('Press Enter to continue...')

asyncio.run(main())
