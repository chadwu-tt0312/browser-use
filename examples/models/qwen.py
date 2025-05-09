# import logging
# import sys

# # 設定日誌基礎配置
# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# # 將 httpx 和 httpcore 的日誌級別設為 DEBUG
# logging.getLogger("httpx").setLevel(logging.DEBUG)
# logging.getLogger("httpcore").setLevel(logging.DEBUG)

import asyncio

from langchain_ollama import ChatOllama

from browser_use import Agent


async def run_search():
	agent = Agent(
		task=(
			# "請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。"
			"請幫我查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。"
		),
		llm=ChatOllama(
			# model='qwen2.5:32b-instruct-q4_K_M',
			# model='qwen2.5:14b',
			# model='qwen2.5:latest',
			model='qwen3:8b',
			# num_ctx=128000,	# 因為這個指令，導致 ollama 使用 CPU (default num_ctx=4096/40960)
			num_ctx=40960,
			base_url="http://localhost:11434"
		),
		max_actions_per_step=1,
		# enable_memory=True
	)

	await agent.run()
	# 取得最後結果
	if agent.state.last_result and agent.state.last_result[-1].extracted_content:
		with open("result.md", "w", encoding="utf-8") as f:
			f.write(agent.state.last_result[-1].extracted_content)


if __name__ == '__main__':
	asyncio.run(run_search())

# OLLAMA_HOST=127.0.0.1 uv run examples/models/qwen.py
# uv run examples/models/qwen.py
