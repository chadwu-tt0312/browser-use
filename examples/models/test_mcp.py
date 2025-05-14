from api_server import app
from fastapi_mcp import FastApiMCP

# from fastapi import FastAPI
# app = FastAPI()

mcp = FastApiMCP(
	app,
	# Optional parameters
	name='Browser Use MCP',
	description='Browser Use MCP',
	# base_url='http://localhost:8880',
	exclude_operations=['health_check'],
)

# Mount the MCP server directly to your FastAPI app
mcp.mount()

if __name__ == '__main__':
	import uvicorn

	uvicorn.run(app, host='0.0.0.0', port=8880)
