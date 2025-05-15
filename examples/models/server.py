"""
MCP Server Module

This module provides a framework for creating an MCP (Model Context Protocol) server.
It allows you to easily define and handle various types of requests and notifications
in an asynchronous manner.

Usage:
1. Create a Server instance:
   server = Server("your_server_name")

2. Define request handlers using decorators:
   @server.list_prompts()
   async def handle_list_prompts() -> list[types.Prompt]:
       # Implementation

   @server.get_prompt()
   async def handle_get_prompt(
       name: str, arguments: dict[str, str] | None
   ) -> types.GetPromptResult:
       # Implementation

   @server.list_tools()
   async def handle_list_tools() -> list[types.Tool]:
       # Implementation

   @server.call_tool()
   async def handle_call_tool(
       name: str, arguments: dict | None
   ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
       # Implementation

   @server.list_resource_templates()
   async def handle_list_resource_templates() -> list[types.ResourceTemplate]:
       # Implementation

3. Define notification handlers if needed:
   @server.progress_notification()
   async def handle_progress(
       progress_token: str | int, progress: float, total: float | None
   ) -> None:
       # Implementation

4. Run the server:
   async def main():
       async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
           await server.run(
               read_stream,
               write_stream,
               InitializationOptions(
                   server_name="your_server_name",
                   server_version="your_version",
                   capabilities=server.get_capabilities(
                       notification_options=NotificationOptions(),
                       experimental_capabilities={},
                   ),
               ),
           )

   asyncio.run(main())

The Server class provides methods to register handlers for various MCP requests and
notifications. It automatically manages the request context and handles incoming
messages from the client.
"""

from __future__ import annotations as _annotations

import contextvars
import logging
import warnings
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from contextlib import AbstractAsyncContextManager, AsyncExitStack, asynccontextmanager
from typing import Any, Generic, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import AnyUrl

import mcp.types as types
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.models import InitializationOptions
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server as stdio_server
from mcp.shared.context import RequestContext
from mcp.shared.exceptions import McpError
from mcp.shared.message import SessionMessage
from mcp.shared.session import RequestResponder

logger = logging.getLogger(__name__)

LifespanResultT = TypeVar("LifespanResultT")

# This will be properly typed in each Server instance's context
request_ctx: contextvars.ContextVar[RequestContext[ServerSession, Any]] = (
    contextvars.ContextVar("request_ctx")
)


class NotificationOptions:
    def __init__(
        self,
        prompts_changed: bool = False,
        resources_changed: bool = False,
        tools_changed: bool = False,
    ):
        self.prompts_changed = prompts_changed
        self.resources_changed = resources_changed
        self.tools_changed = tools_changed


@asynccontextmanager
async def lifespan(server: Server[LifespanResultT]) -> AsyncIterator[object]:
    """Default lifespan context manager that does nothing.

    Args:
        server: The server instance this lifespan is managing

    Returns:
        An empty context object
    """
    yield {}


class Server(Generic[LifespanResultT]):
    def __init__(
        self,
        name: str,
        version: str | None = None,
        instructions: str | None = None,
        lifespan: Callable[
            [Server[LifespanResultT]], AbstractAsyncContextManager[LifespanResultT]
        ] = lifespan,
    ):
        self.name = name
        self.version = version
        self.instructions = instructions
        self.lifespan = lifespan
        self.request_handlers: dict[
            type, Callable[..., Awaitable[types.ServerResult]]
        ] = {
            types.PingRequest: _ping_handler,
        }
        self.notification_handlers: dict[type, Callable[..., Awaitable[None]]] = {}
        self.notification_options = NotificationOptions()
        logger.debug(f"Initializing server '{name}'")

    def create_initialization_options(
        self,
        notification_options: NotificationOptions | None = None,
        experimental_capabilities: dict[str, dict[str, Any]] | None = None,
    ) -> InitializationOptions:
        """Create initialization options from this server instance."""

        def pkg_version(package: str) -> str:
            try:
                from importlib.metadata import version

                return version(package)
            except Exception:
                pass

            return "unknown"

        return InitializationOptions(
            server_name=self.name,
            server_version=self.version if self.version else pkg_version("mcp"),
            capabilities=self.get_capabilities(
                notification_options or NotificationOptions(),
                experimental_capabilities or {},
            ),
            instructions=self.instructions,
        )

    def get_capabilities(
        self,
        notification_options: NotificationOptions,
        experimental_capabilities: dict[str, dict[str, Any]],
    ) -> types.ServerCapabilities:
        """Convert existing handlers to a ServerCapabilities object."""
        prompts_capability = None
        resources_capability = None
        tools_capability = None
        logging_capability = None

        # Set prompt capabilities if handler exists
        if types.ListPromptsRequest in self.request_handlers:
            prompts_capability = types.PromptsCapability(
                listChanged=notification_options.prompts_changed
            )

        # Set resource capabilities if handler exists
        if types.ListResourcesRequest in self.request_handlers:
            resources_capability = types.ResourcesCapability(
                subscribe=False, listChanged=notification_options.resources_changed
            )

        # Set tool capabilities if handler exists
        if types.ListToolsRequest in self.request_handlers:
            tools_capability = types.ToolsCapability(
                listChanged=notification_options.tools_changed
            )

        # Set logging capabilities if handler exists
        if types.SetLevelRequest in self.request_handlers:
            logging_capability = types.LoggingCapability()

        return types.ServerCapabilities(
            prompts=prompts_capability,
            resources=resources_capability,
            tools=tools_capability,
            logging=logging_capability,
            experimental=experimental_capabilities,
        )

    @property
    def request_context(self) -> RequestContext[ServerSession, LifespanResultT]:
        """If called outside of a request context, this will raise a LookupError."""
        return request_ctx.get()

    def list_prompts(self):
        def decorator(func: Callable[[], Awaitable[list[types.Prompt]]]):
            logger.debug("Registering handler for PromptListRequest")

            async def handler(_: Any):
                prompts = await func()
                return types.ServerResult(types.ListPromptsResult(prompts=prompts))

            self.request_handlers[types.ListPromptsRequest] = handler
            return func

        return decorator

    def get_prompt(self):
        def decorator(
            func: Callable[
                [str, dict[str, str] | None], Awaitable[types.GetPromptResult]
            ],
        ):
            logger.debug("Registering handler for GetPromptRequest")

            async def handler(req: types.GetPromptRequest):
                prompt_get = await func(req.params.name, req.params.arguments)
                return types.ServerResult(prompt_get)

            self.request_handlers[types.GetPromptRequest] = handler
            return func

        return decorator

    def list_resources(self):
        def decorator(func: Callable[[], Awaitable[list[types.Resource]]]):
            logger.debug("Registering handler for ListResourcesRequest")

            async def handler(_: Any):
                resources = await func()
                return types.ServerResult(
                    types.ListResourcesResult(resources=resources)
                )

            self.request_handlers[types.ListResourcesRequest] = handler
            return func

        return decorator

    def list_resource_templates(self):
        def decorator(func: Callable[[], Awaitable[list[types.ResourceTemplate]]]):
            logger.debug("Registering handler for ListResourceTemplatesRequest")

            async def handler(_: Any):
                templates = await func()
                return types.ServerResult(
                    types.ListResourceTemplatesResult(resourceTemplates=templates)
                )

            self.request_handlers[types.ListResourceTemplatesRequest] = handler
            return func

        return decorator

    def read_resource(self):
        def decorator(
            func: Callable[
                [AnyUrl], Awaitable[str | bytes | Iterable[ReadResourceContents]]
            ],
        ):
            logger.debug("Registering handler for ReadResourceRequest")

            async def handler(req: types.ReadResourceRequest):
                result = await func(req.params.uri)

                def create_content(data: str | bytes, mime_type: str | None):
                    match data:
                        case str() as data:
                            return types.TextResourceContents(
                                uri=req.params.uri,
                                text=data,
                                mimeType=mime_type or "text/plain",
                            )
                        case bytes() as data:
                            import base64

                            return types.BlobResourceContents(
                                uri=req.params.uri,
                                blob=base64.b64encode(data).decode(),
                                mimeType=mime_type or "application/octet-stream",
                            )

                match result:
                    case str() | bytes() as data:
                        warnings.warn(
                            "Returning str or bytes from read_resource is deprecated. "
                            "Use Iterable[ReadResourceContents] instead.",
                            DeprecationWarning,
                            stacklevel=2,
                        )
                        content = create_content(data, None)
                    case Iterable() as contents:
                        contents_list = [
                            create_content(content_item.content, content_item.mime_type)
                            for content_item in contents
                        ]
                        return types.ServerResult(
                            types.ReadResourceResult(
                                contents=contents_list,
                            )
                        )
                    case _:
                        raise ValueError(
                            f"Unexpected return type from read_resource: {type(result)}"
                        )

                return types.ServerResult(
                    types.ReadResourceResult(
                        contents=[content],
                    )
                )

            self.request_handlers[types.ReadResourceRequest] = handler
            return func

        return decorator

    def set_logging_level(self):
        def decorator(func: Callable[[types.LoggingLevel], Awaitable[None]]):
            logger.debug("Registering handler for SetLevelRequest")

            async def handler(req: types.SetLevelRequest):
                await func(req.params.level)
                return types.ServerResult(types.EmptyResult())

            self.request_handlers[types.SetLevelRequest] = handler
            return func

        return decorator

    def subscribe_resource(self):
        def decorator(func: Callable[[AnyUrl], Awaitable[None]]):
            logger.debug("Registering handler for SubscribeRequest")

            async def handler(req: types.SubscribeRequest):
                await func(req.params.uri)
                return types.ServerResult(types.EmptyResult())

            self.request_handlers[types.SubscribeRequest] = handler
            return func

        return decorator

    def unsubscribe_resource(self):
        def decorator(func: Callable[[AnyUrl], Awaitable[None]]):
            logger.debug("Registering handler for UnsubscribeRequest")

            async def handler(req: types.UnsubscribeRequest):
                await func(req.params.uri)
                return types.ServerResult(types.EmptyResult())

            self.request_handlers[types.UnsubscribeRequest] = handler
            return func

        return decorator

    def list_tools(self):
        def decorator(func: Callable[[], Awaitable[list[types.Tool]]]):
            logger.debug("Registering handler for ListToolsRequest")

            async def handler(_: Any):
                tools = await func()
                return types.ServerResult(types.ListToolsResult(tools=tools))

            self.request_handlers[types.ListToolsRequest] = handler
            return func

        return decorator

    def call_tool(self):
        def decorator(
            func: Callable[
                ...,
                Awaitable[
                    Iterable[
                        types.TextContent | types.ImageContent | types.EmbeddedResource
                    ]
                ],
            ],
        ):
            logger.debug("Registering handler for CallToolRequest")

            async def handler(req: types.CallToolRequest):
                try:
                    results = await func(req.params.name, (req.params.arguments or {}))
                    return types.ServerResult(
                        types.CallToolResult(content=list(results), isError=False)
                    )
                except Exception as e:
                    return types.ServerResult(
                        types.CallToolResult(
                            content=[types.TextContent(type="text", text=str(e))],
                            isError=True,
                        )
                    )

            self.request_handlers[types.CallToolRequest] = handler
            return func

        return decorator

    def progress_notification(self):
        def decorator(
            func: Callable[[str | int, float, float | None], Awaitable[None]],
        ):
            logger.debug("Registering handler for ProgressNotification")

            async def handler(req: types.ProgressNotification):
                await func(
                    req.params.progressToken, req.params.progress, req.params.total
                )

            self.notification_handlers[types.ProgressNotification] = handler
            return func

        return decorator

    def completion(self):
        """Provides completions for prompts and resource templates"""

        def decorator(
            func: Callable[
                [
                    types.PromptReference | types.ResourceReference,
                    types.CompletionArgument,
                ],
                Awaitable[types.Completion | None],
            ],
        ):
            logger.debug("Registering handler for CompleteRequest")

            async def handler(req: types.CompleteRequest):
                completion = await func(req.params.ref, req.params.argument)
                return types.ServerResult(
                    types.CompleteResult(
                        completion=completion
                        if completion is not None
                        else types.Completion(values=[], total=None, hasMore=None),
                    )
                )

            self.request_handlers[types.CompleteRequest] = handler
            return func

        return decorator

    async def run(
        self,
        read_stream: MemoryObjectReceiveStream[SessionMessage | Exception],
        write_stream: MemoryObjectSendStream[SessionMessage],
        initialization_options: InitializationOptions,
        # When False, exceptions are returned as messages to the client.
        # When True, exceptions are raised, which will cause the server to shut down
        # but also make tracing exceptions much easier during testing and when using
        # in-process servers.
        raise_exceptions: bool = False,
        # When True, the server is stateless and
        # clients can perform initialization with any node. The client must still follow
        # the initialization lifecycle, but can do so with any available node
        # rather than requiring initialization for each connection.
        stateless: bool = False,
    ):
        async with AsyncExitStack() as stack:
            lifespan_context = await stack.enter_async_context(self.lifespan(self))
            session = await stack.enter_async_context(
                ServerSession(
                    read_stream,
                    write_stream,
                    initialization_options,
                    stateless=stateless,
                )
            )

            async with anyio.create_task_group() as tg:
                async for message in session.incoming_messages:
                    logger.debug(f"Received message: {message}")

                    tg.start_soon(
                        self._handle_message,
                        message,
                        session,
                        lifespan_context,
                        raise_exceptions,
                    )

    async def _handle_message(
        self,
        message_item: RequestResponder[types.ClientRequest, types.ServerResult]
        | types.ClientNotification
        | Exception,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False,
    ):
        try:
            with warnings.catch_warnings(record=True) as caught_warnings:
                if isinstance(message_item, RequestResponder):
                    # This is the case for requests that expect a response.
                    # The RequestResponder instance itself is message_item.
                    responder = message_item
                    request_obj = responder.request.root # Extract the actual request model

                    # The 'with responder:' block handles __enter__ and __exit__ of RequestResponder.
                    # Exceptions from __enter__, _handle_request (if it internally decides to raise),
                    # or __exit__ will be caught by the outer 'except Exception as e_outer_handling'.
                    with responder:
                        await self._handle_request(
                            responder, request_obj, session, lifespan_context, raise_exceptions
                        )
                elif isinstance(message_item, types.ClientNotification):
                    # This is for notifications that don't expect a response.
                    # message_item is the ClientNotification model instance.
                    await self._handle_notification(message_item.root)
                elif isinstance(message_item, Exception):
                    # This handles cases where the session.incoming_messages stream itself yields an Exception.
                    logger.error(f"Exception received directly from session stream: {message_item}", exc_info=message_item)
                    if raise_exceptions:
                        raise message_item # Re-raise the original exception from the stream if configured.
                    # If raise_exceptions is False, the error is logged, and _handle_message completes for this item.
                else:
                    logger.warning(f"Unhandled message type in _handle_message: {type(message_item)}")

            for warning_message in caught_warnings:
                logger.info(f"Warning during message handling: {warning_message.category.__name__}: {warning_message.message}")

        except Exception as e_outer_handling:
            # This catches exceptions from responder.__enter__/__exit__, _handle_request (if it raised),
            # _handle_notification, or re-raised stream exceptions.
            logger.error(f"Unhandled exception in _handle_message processing: {e_outer_handling}", exc_info=True)
            if raise_exceptions:
                raise # Re-raise if configured, allowing it to propagate (e.g., to TaskGroup)
            # If raise_exceptions is False, the exception is logged and swallowed here,
            # preventing it from crashing the _handle_message task and propagating further,
            # which should prevent the "Unexpected ASGI message" error.

    async def _handle_request(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult],
        req: Any,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool,
    ):
        logger.info(f"Processing request of type {type(req).__name__}")
        
        response_payload: types.ServerResult | types.ErrorData

        if type(req) in self.request_handlers:
            handler = self.request_handlers[type(req)]
            logger.debug(f"Dispatching request of type {type(req).__name__}")
            token = None
            try:
                token = request_ctx.set(
                    RequestContext(
                        message.request_id,
                        message.request_meta,
                        session,
                        lifespan_context,
                    )
                )
                response_payload = await handler(req)
            except McpError as err:
                response_payload = err.error
            except Exception as err:
                if raise_exceptions:
                    raise err
                response_payload = types.ErrorData(code=0, message=str(err), data=None)
            finally:
                if token is not None:
                    request_ctx.reset(token)
        else: # Method not found
            response_payload = types.ErrorData(
                code=types.METHOD_NOT_FOUND,
                message="Method not found",
            )

        # Common sending logic for response_payload
        response_was_successfully_processed_for_sending = False
        try:
            # 'message' (RequestResponder) is already in a context manager scope
            # established in the _handle_message method.
            # Calling message.respond() directly relies on that outer scope.
            await message.respond(response_payload)
            response_was_successfully_processed_for_sending = True
        except AssertionError as e_assert:
            # This exception is expected if the request was already completed (e.g., by cancellation)
            logging.info(
                f"Could not send response for request {message.request_id} (already completed/cancelled): {e_assert}"
            )
        except Exception as e_respond: # Catch other errors during the respond() call itself
            logger.error(
                f"Exception during message.respond() for request {message.request_id}: {e_respond}",
                exc_info=True 
            )
            # If raise_exceptions is true, let it propagate for debugging.
            # This can lead to the ASGI 'response already completed' error if not handled by caller.
            if raise_exceptions:
                raise e_respond
            # If raise_exceptions is false, we've logged it. Swallowing it here
            # prevents the ASGI 'response already completed' error when the primary
            # issue is, e.g., a broken client connection during the send attempt.
        
        if response_was_successfully_processed_for_sending:
            logger.debug(f"MCP response processed for request {message.request_id}.")
        else:
            logger.debug(f"MCP response for request {message.request_id} was not sent or failed during send (e.g. already completed, or error during respond()).")

    async def _handle_notification(self, notify: Any):
        if type(notify) in self.notification_handlers:
            assert type(notify) in self.notification_handlers

            handler = self.notification_handlers[type(notify)]
            logger.debug(f"Dispatching notification of type {type(notify).__name__}")

            try:
                await handler(notify)
            except Exception as err:
                logger.error(f"Uncaught exception in notification handler: {err}")


async def _ping_handler(request: types.PingRequest) -> types.ServerResult:
    return types.ServerResult(types.EmptyResult())
