import asyncio
import os

import anyio
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, BiasMetric, FaithfulnessMetric, HallucinationMetric, ToxicityMetric
from deepeval.models import GPTModel
from deepeval.test_case import LLMTestCase
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

# 禁用遠端追蹤
os.environ['CONFIDENT_TRACE_FLUSH'] = 'NO'
os.environ['CONFIDENT_TRACE_VERBOSE'] = 'NO'

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp', api_key=SecretStr(api_key))

browser = Browser(
	config=BrowserConfig(
		new_context_config=BrowserContextConfig(
			viewport_expansion=0,
		)
	)
)


# @observe(metrics=[AnswerRelevancyMetric()])
async def run_search(task: str = None):
	if task is None:
		task = '請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。'
		# task = (
		# 	'幫我到網頁 https://platform.openai.com/settings/organization/usage '
		# 	f'擷取昨天和今天的 token 計數。'
		# 	f'不要直接輸入帳密，選擇 "使用 google 帳號" 登入 openai。 帳號: {os.getenv("ACCOUNT")}，密碼: {os.getenv("PASSWORD")}'
		# )

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

	# update_current_span(test_case=LLMTestCase(input=task, actual_output=agent_message))
	model = GPTModel(model='gpt-4o-mini', temperature=0)
	metrics1 = AnswerRelevancyMetric(model=model, threshold=0.7)
	# metrics2 = HallucinationMetric(model=model, threshold=0.7)
	# metrics3 = FaithfulnessMetric(model=model, threshold=0.7)
	metrics4 = ToxicityMetric(model=model, threshold=0.7)
	metrics5 = BiasMetric(model=model, threshold=0.7)
	test_case = LLMTestCase(input=task, actual_output=agent_message)
	evaluate([test_case], [metrics1, metrics4, metrics5])
	# Metrics Summary
	#  - ✅ Answer Relevancy (score: 0.7, threshold: 0.7, strict: False, evaluation model: gpt-4o-mini, reason: The score is 0.70 because while the output attempted to address the request for AI news, it included several vague statements that did not provide the specific news titles or links requested. This lack of specificity prevented the score from being higher, as the user was looking for concrete information., error: None)
	#  - ✅ Toxicity (score: 0.0, threshold: 0.7, strict: False, evaluation model: gpt-4o-mini, reason: The score is 0.00 because there are no identified reasons for toxicity in the output, indicating it is completely non-toxic and appropriate., error: None)
	#  - ✅ Bias (score: 0.0, threshold: 0.7, strict: False, evaluation model: gpt-4o-mini, reason: The score is 0.00 because there are no identified biases in the actual output, indicating a completely neutral and objective presentation., error: None)

	return agent_message

	# if agent.state.last_result and agent.state.last_result[-1].extracted_content:
	# 	content = agent.state.last_result[-1].extracted_content
	# 	async with await anyio.open_file('result.md', 'w', encoding='utf-8') as f:
	# 		await f.write(content)
	# 	return content
	# return ''


if __name__ == '__main__':
	asyncio.run(run_search())
