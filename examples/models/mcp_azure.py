import os
import asyncio
from dotenv import load_dotenv
from typing import Awaitable, Callable
from mcp.server.fastmcp import FastMCP, Context
from langchain_openai import AzureChatOpenAI
from urllib.parse import urlparse
from browser_use import Agent
from browser_use.browser.browser import Browser, BrowserConfig, ProxySettings
from browser_use.browser.context import BrowserContextConfig

from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
import uvicorn

# 處理 "Received request before initialization was complete" 錯誤
# 這是一個已知的 MCP SSE 問題，當客戶端在伺服器重啟後沒有正確重新初始化連接時會發生
# 參考：https://github.com/modelcontextprotocol/python-sdk/issues/423

# Load environment variables from .env file
load_dotenv()

# Retrieve Azure-specific environment variables
azure_openai_api_key = os.getenv('AZURE_OPENAI_KEY')
azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
user_agent = os.getenv('USER_AGENT')

if not azure_openai_api_key or not azure_openai_endpoint:
	raise ValueError('AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT is not set')

proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
if proxy_url:
    # print("proxy_url", proxy_url)
    parsed = urlparse(proxy_url)
    proxy = ProxySettings(
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
        username = parsed.username if parsed.username else None,
        password = parsed.password if parsed.password else None,
	)

browser = Browser(
	config=BrowserConfig(
		headless=False,
        proxy=proxy if proxy_url else None,   
		new_context_config=BrowserContextConfig(
			user_agent=user_agent, 
			ignore_https_errors=True, # 忽略 SSL 憑證錯誤
			# disable_security=True,  
		)
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
)
agent = None

# Initialize FastMCP server
mcp = FastMCP("browser-use")


@mcp.tool()
async def perform_search(task: str, context: Context):
    """Perform the actual search in the background."""
    async def step_handler(state, *args):
        if len(args) != 2:
            return
        await context.session.send_log_message(
            level="info",
            data={"screenshot": state.screenshot, "result": args[0]}
        )

    asyncio.create_task(
        run_browser_agent(task=task, on_step=step_handler)
    )
    return "Processing Request"


@mcp.tool()
async def stop_search(*, context: Context):
    """Stop a running browser agent search by task ID."""
    if agent is not None:
        await agent.stop()
    return "Running Agent stopped"


async def run_browser_agent(task: str, on_step: Callable[[], Awaitable[None]]):
    """Run the browser-use agent with the specified task."""
    global agent
    try:
        agent = Agent(
            task=task,
            browser=browser,
            llm=llm,
            register_new_step_callback=on_step,
            register_done_callback=on_step,
    		# enable_memory=True,
        )

        result = await agent.run()
        agent_message = None
        if result.is_done():
            agent_message = result.history[-1].result[0].extracted_content
        if agent_message is None:
            agent_message = 'Oops! Something went wrong while running Browser-Use.'
        else:
            async with await anyio.open_file('result.md', 'w', encoding='utf-8') as f:
                await f.write(agent_message)
        return agent_message
    except asyncio.CancelledError:
        return "Task was cancelled"

    except Exception as e:
        return f"Error during execution: {str(e)}"
    finally:
        await browser.close()



def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    # mcp.run(transport="sse")
    mcp_server = mcp._mcp_server  # noqa: WPS437

    import argparse

    parser = argparse.ArgumentParser(description="Run MCP SSE-based server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8082, help="Port to listen on")
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)

# uv run mcp_azure.py
# 預設情況下，伺服器在 0.0.0.0:8082 上運行，但可以使用命令列參數進行配置
# uv run mcp_azure.py --host <your host> --port <your port>

