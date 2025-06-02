
## setup

1. uv venv --python=3.11
2. source .venv/Scripts/activate
3. uv sync
4. (opt)uv pip install -e . --no-cache-dir --force-reinstall

## RUN

1. uv run examples/models/azure_openai.py
2. uv run examples/models/api_server.py
3. uv run examples/models/mcp_server.py (run-mcp-server.sh)

## Memo (.env)

1. using GEMINI_API_KEY
2. using AZURE_OPENAI_KEY & AZURE_OPENAI_ENDPOINT
3. using OPENAI_API_KEY
4. add USER_AGENT (會根據 Edge 瀏覽器版本決定是否可以連線)
5. add HTTPS_PROXY (proxy 設定， 會暴露帳密)
    + 改成沒有帳密的格式
6. add UMC_SETTING (根據 T/F 決定 Browser 設定是否使用 proxy)
7. add TZ

## Memo (files)

1. fix browser_use\logging_config.py
2. fix examples\models\azure_openai.py
3. add examples\models\api_server.py
4. add examples\models\mcp_server.py

### cUrl

```bash
curl -X POST "http://localhost:8881/search" \
-H "Content-Type: application/json" \
-d '{
  "task": "請幫我查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。並轉換成 markdown 格式。",
  "type": "azure",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54",
  "proxy_username": "your_username",
  "proxy_password": "your_password"
}'
```
