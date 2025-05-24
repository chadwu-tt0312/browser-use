"""
browser_use 套件很可能只支援 langchain 官方的 LLM 介面（如 ChatOpenAI、ChatOpenRouter 等），而你傳入的 OpenRouterLLM 物件不完全相容。
或者 browser_use 期望 llm 物件有 get 方法或 dict-like 行為，但 OpenRouterLLM 沒有。
"""

import asyncio
import os

import anyio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use import Agent

load_dotenv()


async def run_search():
	llm = ChatOpenAI(
		model='qwen/qwen3-30b-a3b:free',
		base_url='https://openrouter.ai/api/v1',
		api_key=os.getenv('OPENROUTER_API_KEY'),
		temperature=0,
	)

	agent = Agent(
		task=(
			# "請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。"
			'請幫我查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。'
		),
		llm=llm,
		max_actions_per_step=1,
		enable_memory=True,
	)

	result = await agent.run()
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
# 	with open("result.md", "w", encoding="utf-8") as f:
# 		f.write(agent.state.last_result[-1].extracted_content)

if __name__ == '__main__':
	asyncio.run(run_search())
