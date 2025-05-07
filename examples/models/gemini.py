import asyncio
import os

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


async def run_search():
	agent = Agent(
		# task='Go to amazon.com, search for laptop, sort by best rating, and give me the price of the first result',
		task="請幫我查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。",
		llm=llm,
		max_actions_per_step=4,
		# browser=browser,
	)

	await agent.run(max_steps=25)
	# 取得最後結果
	if agent.state.last_result and agent.state.last_result[-1].extracted_content:
		with open("result.md", "w", encoding="utf-8") as f:
			f.write(agent.state.last_result[-1].extracted_content)
			print(f"result.md 已經寫入.")

if __name__ == '__main__':
	asyncio.run(run_search())
