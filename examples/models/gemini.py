import asyncio
import os

import anyio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from browser_use import Agent, BrowserConfig
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContextConfig

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
	raise ValueError('GEMINI_API_KEY is not set')

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(api_key))

browser = Browser(
	config=BrowserConfig(
		new_context_config=BrowserContextConfig(
			viewport_expansion=0,
		)
	)
)


async def run_search(task: str = None):
	if task is None:
		task = '請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。'

	agent = Agent(
		task=task,
		llm=llm,
		max_actions_per_step=4,
		# browser=browser,
	)

	result = await agent.run(max_steps=25)
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
