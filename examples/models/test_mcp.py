from api_server import app
from fastapi_mcp import FastApiMCP

# from fastapi import FastAPI
# app = FastAPI()

mcp = FastApiMCP(
	app,
	# Optional parameters
	name='Browser-Use MCP',
	description='Browser-Use MCP',
	# base_url='http://localhost:8880',
	exclude_operations=['health_check'],
)

# Mount the MCP server directly to your FastAPI app
mcp.mount()

if __name__ == '__main__':
	import uvicorn

	uvicorn.run(app, host='0.0.0.0', port=8880)

# fastapi_mcp v0.3.3 修改 session.py 之後可以連線 (http://localhost:8880/mcp) 但使用還是有問題
# 修改 server.py 之後呼叫 Browser-Use step 2 還是會報錯
