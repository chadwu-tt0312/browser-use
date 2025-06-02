"""
Browser-Use API 伺服器

基本使用範例：
curl -X POST "http://localhost:8881/search" \
-H "Content-Type: application/json" \
-d '{"task": "Please help me search for the latest AI news using bing and list the 10 latest news titles and links. And convert it to markdown format.", "type": "gemini"}'

使用 Azure 模型並指定代理參數：
curl -X POST "http://localhost:8881/search" \
-H "Content-Type: application/json" \
-d '{
  "task": "Search for Python tutorials on Google",
  "type": "azure",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Edg/135.0.3179.54",
  "proxy_username": "your_username",
  "proxy_password": "your_password"
}'

注意：
- 用 bash 測試時，task 內的中文字解析有問題，建議使用英文
- user_agent, proxy_username, proxy_password 參數僅在 type="azure" 時有效
- Gemini 和 OpenAI 模型使用標準配置，不支援動態參數
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uvicorn import run

# 設置日誌
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'api_server.log'
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s %(message)s',
	handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入現有的模組
from examples.models.azure_openai import run_search as azure_search
from examples.models.gemini import run_search as gemini_search
from examples.models.gpt_4o import run_search as gpt4o_search

app = FastAPI(title='Browser Use API')


class SearchRequest(BaseModel):
	task: str
	type: str = 'gemini'  # 可選: "gemini", "openai", "azure"
	user_agent: Optional[str] = None  # 自定義 User-Agent 字串
	proxy_username: Optional[str] = None  # 代理認證用戶名
	proxy_password: Optional[str] = None  # 代理認證密碼
	# max_steps: Optional[int] = 25
	# max_actions_per_step: Optional[int] = 4
	timeout_minutes: Optional[int] = 10


class SearchResponse(BaseModel):
	content: str
	status: str
	type: str
	execution_time: float


@app.post('/search', response_model=SearchResponse, operation_id='search_task')
async def search(request: SearchRequest):
	task_id = f'{datetime.now().timestamp()}'
	logger.info(f'收到新的 search 請求 {task_id}: {request.task}')

	# 設定超時時間（默認為 10 分鐘）
	timeout_seconds = (request.timeout_minutes or 10) * 60
	# logger.info(f'設定請求超時時間: {timeout_seconds} 秒 ({request.timeout_minutes or 10} 分鐘)')

	start_time = datetime.now()
	try:
		if request.type == 'gemini':
			logger.info('使用 Gemini 執行任務 (標準模式)')
			result = await asyncio.wait_for(gemini_search(request.task), timeout=timeout_seconds)
		elif request.type == 'openai':
			logger.info('使用 OpenAI 執行任務 (標準模式)')
			result = await asyncio.wait_for(gpt4o_search(request.task), timeout=timeout_seconds)
		elif request.type == 'azure':
			logger.info('使用 Azure 執行任務 (支援動態代理參數)')
			# 傳遞額外參數給 azure_search
			result = await asyncio.wait_for(
				azure_search(
					request.task,
					user_agent=request.user_agent,
					proxy_username=request.proxy_username,
					proxy_password=request.proxy_password,
				),
				timeout=timeout_seconds,
			)
		else:
			error_msg = f'不支援的類型: {request.type}'
			logger.error(error_msg)
			raise ValueError(error_msg)

		execution_time = (datetime.now() - start_time).total_seconds()
		logger.info(f'任務 {task_id} 執行完成，耗時: {execution_time:.2f} 秒')

		return SearchResponse(content=result, status='success', type=request.type, execution_time=execution_time)
	except asyncio.TimeoutError:
		execution_time = (datetime.now() - start_time).total_seconds()
		error_msg = f'任務 {task_id} 執行超時 (超過 {request.timeout_minutes or 10} 分鐘)'
		logger.error(error_msg)
		raise HTTPException(status_code=408, detail=error_msg)
	except Exception as e:
		execution_time = (datetime.now() - start_time).total_seconds()
		error_msg = f'任務 {task_id} 執行失敗: {str(e)}'
		logger.error(error_msg)
		raise HTTPException(status_code=500, detail=error_msg)


@app.get('/health', operation_id='health_check')
async def health_check():
	logger.info('健康檢查請求')
	return {'status': 'healthy'}


if __name__ == '__main__':
	logger.info('啟動 API 服務器')
	run(app, host='0.0.0.0', port=8881)
