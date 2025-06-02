"""
Simple try of the agent.

@dev You need to add AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT to your environment variables.
"""

import asyncio
import os
import sys
from urllib.parse import urlparse

import anyio
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig, ProxySettings
from browser_use.browser.context import BrowserContextConfig

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

# Retrieve Azure-specific environment variables
azure_openai_api_key = os.getenv('AZURE_OPENAI_KEY')
azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')

if not azure_openai_api_key or not azure_openai_endpoint:
	raise ValueError('AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT is not set')


def create_browser_with_params(user_agent: str = None, proxy_username: str = None, proxy_password: str = None):
	"""根據參數動態創建瀏覽器配置"""

	umc_setting = os.environ.get('UMC_SETTING')
	# print('umc_setting =', umc_setting)

	if umc_setting == 'true':
		proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

		if not proxy_url:
			raise ValueError('HTTPS_PROXY is not set when UMC_SETTING=true')

		# 使用傳入的 user_agent 或環境變數
		final_user_agent = user_agent or os.getenv('USER_AGENT')
		# print('final_user_agent =', final_user_agent)

		if not final_user_agent:
			raise ValueError('USER_AGENT is not set and not provided as parameter when UMC_SETTING=true')

		# 解析代理 URL
		parsed = urlparse(proxy_url)

		# 使用傳入的認證資訊或從 URL 中提取
		final_username = proxy_username or parsed.username
		final_password = proxy_password or parsed.password
		# print('final_username =', final_username)
		# print('final_password =', final_password)

		proxy = ProxySettings(
			server=f'{parsed.scheme}://{parsed.hostname}:{parsed.port}',
			username=final_username,
			password=final_password,
		)

		return Browser(
			config=BrowserConfig(
				headless=False,
				proxy=proxy,
				new_context_config=BrowserContextConfig(
					user_agent=final_user_agent,
					ignore_https_errors=True,  # 忽略 SSL 憑證錯誤
				),
			)
		)
	else:
		return Browser(
			config=BrowserConfig(
				headless=False,
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
	api_version='2024-12-01-preview',
	temperature=0,
)


async def run_search(task: str = None, user_agent: str = None, proxy_username: str = None, proxy_password: str = None):
	if task is None:
		task = '請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。'

	# 動態創建瀏覽器配置，根據傳入的參數
	browser_to_use = create_browser_with_params(user_agent, proxy_username, proxy_password)

	agent = Agent(
		task=task,
		llm=llm,
		# enable_memory=True,
		enable_memory=False,
		browser=browser_to_use,
	)

	result = await agent.run(max_steps=10)
	await browser_to_use.close()
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


if __name__ == '__main__':
	asyncio.run(run_search())
