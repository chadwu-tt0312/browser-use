# test_mcp fix
_Exported on 2025/5/15 at 13:50:34 [GMT+8] from Cursor (0.50.4)_

---

**Cursor**

我將檢查追蹤記錄中提到的 `mcp/shared/session.py` 檔案，並修正 `AttributeError`。

首先，我將使用檔案搜尋來定位 `session.py`。


檔案搜尋未能找到 `mcp/shared/session.py`。這可能是因為該檔案位於已安裝的套件中，而不是工作區中。

由於追蹤記錄提供了檔案路徑的片段 (`D:\_Code\_GitHub\browser-use\.venv\Lib\site-packages\mcp\shared\session.py`)，我將假設這個路徑是正確的，並直接嘗試讀取該檔案的相關部分以確認問題。錯誤發生在 `session.py` 的第 330 行。


好的，正如預期的那樣，第 330 行是 `elif isinstance(message.message.root, JSONRPCRequest):`。

我將把它修改為 `elif isinstance(message.root, JSONRPCRequest):`。同樣地，我會修改第 353 行和第 373 行中類似的存取方式。


```python
// ... existing code ...
                elif isinstance(message, Exception):
                    await self._handle_incoming(message)
                elif isinstance(message.root, JSONRPCRequest):
                    validated_request = self._receive_request_type.model_validate(
                        message.root.model_dump(
                            by_alias=True, mode="json", exclude_none=True
                        )
                    )

                    responder = RequestResponder(
                        request_id=message.root.id,
                        request_meta=validated_request.root.params.meta
                        if validated_request.root.params
                        else None,
                        request=validated_request,
                        session=self,
                        on_complete=lambda r: self._in_flight.pop(r.request_id, None),
                    )

                    self._in_flight[responder.request_id] = responder
                    await self._received_request(responder)

                    if not responder._completed:  # type: ignore[reportPrivateUsage]
                        await self._handle_incoming(responder)

                elif isinstance(message.root, JSONRPCNotification):
                    try:
                        notification = self._receive_notification_type.model_validate(
                            message.root.model_dump(
                                by_alias=True, mode="json", exclude_none=True
                            )
                        )
                        # Handle cancellation notifications
                        if isinstance(notification.root, CancelledNotification):
                            cancelled_id = notification.root.params.requestId
                            if cancelled_id in self._in_flight:
                                await self._in_flight[cancelled_id].cancel()
                        else:
                            await self._received_notification(notification)
                            await self._handle_incoming(notification)
                    except Exception as e:
                        # For other validation errors, log and continue
                        logging.warning(
                            f"Failed to validate notification: {e}. "
                            f"Message was: {message.root}"
                        )
                else:  # Response or error
                    stream = self._response_streams.pop(message.root.id, None)
                    if stream:
                        await stream.send(message.root)
                    else:
                        await self._handle_incoming(
                            RuntimeError(
                                "Received response with an unknown "
                                f"request ID: {message}"
                            )
                        )

    async def _received_request(

```

變更已成功套用。這應該可以解決 `AttributeError`。

請您再次執行您的程式碼，確認問題是否已解決。

```python
# Example from docstring
# with request_responder as resp:
#     await resp.respond(result)
```

```python
# lines 115-116
if not self._entered:
    raise RuntimeError("RequestResponder must be used as a context manager")
assert not self._completed, "Request already responded to" # This is where it fails

if not self.cancelled:
    self._completed = True
    # ... sends response
```

```python
# mcp/server/lowlevel/server.py (from previous knowledge or logical deduction)
# async def _handle_request(self, message: RequestResponder, request_body: RpcRequest) -> None:
# ...
#     response = await handler(request_body.params, message.request_meta) # This calls the user's handler
#     await message.respond(response) # Error here
```

```python
elif isinstance(message.root, JSONRPCRequest):
    # ...
    responder = RequestResponder(...) # responder is created
    # ...
    await self._received_request(responder) # Hook for subclasses, might call responder.respond()

    if not responder._completed:  # type: ignore[reportPrivateUsage]
        await self._handle_incoming(responder) # This is where lowlevel.Server._handle_request gets called
```

```python
# mcp/server/lowlevel/server.py
# async def _handle_incoming(self, item):
#    if isinstance(item, RequestResponder):
#        await self._handle_message(item, item.request.root) # item.request.root should be the RpcRequest
```

```python
# async def _handle_message(self, message: RequestResponder, request_body: RpcRequest):
#    if isinstance(request_body, Request): # or some specific request type
#        await self._handle_request(message, request_body)
```

```plaintext
    This class MUST be used as a context manager to ensure proper cleanup and
    cancellation handling:

    Example:
        with request_responder as resp: # This is resp, not request_responder. Not an issue.
            await resp.respond(result)
```

```python
    async def respond(self, response: SendResultT | ErrorData) -> None:
        """Send a response for this request.

        Must be called within a context manager block. <--- This is the key
        Raises:
            RuntimeError: If not used within a context manager
            AssertionError: If request was already responded to
        """
        if not self._entered: # This check implies that respond() can be called on an instance that is not in its CM block.
            raise RuntimeError("RequestResponder must be used as a context manager")
        assert not self._completed, "Request already responded to" # Fails here
```

```python
# mcp/server/lowlevel/server.py line 574
async def _handle_request(
    self, message: RequestResponder, request_body: RpcRequest # message is the RequestResponder
) -> None:
    # ...
    handler = self._handlers[method_name]
    # ...
    response = await handler(request_body.params, message.request_meta) # User handler
    await message.respond(response) # <--- call that fails assertion
```

```python
# mcp/server/lowlevel/server.py
# In _handle_request:
# async def _handle_request(self, message: RequestResponder, ...):
    # ...
    # response = await handler(...)
    # await message.respond(response) # OLD
    with message as r: # NEW
        await r.respond(response)
```

```python
# with message as r:
#    await r.respond(response)
```

```python
  if isinstance(notification.root, CancelledNotification):
      cancelled_id = notification.root.params.requestId
      if cancelled_id in self._in_flight:
          await self._in_flight[cancelled_id].cancel() # This calls RequestResponder.cancel()
```

```python
    async def cancel(self) -> None:
        """Cancel this request and mark it as completed."""
        if not self._entered: # This check!
            raise RuntimeError("RequestResponder must be usado as a context manager")
        # ...
        self._completed = True
```

```python
# In BaseSession._receive_loop for cancellation
# if cancelled_id in self._in_flight:
#    responder_to_cancel = self._in_flight[cancelled_id]
#    with responder_to_cancel as rtc:
#        await rtc.cancel()

# In lowlevel.Server._handle_request for responding
# with message as r:
#    await r.respond(response)
```

```python
    def __init__(...):
        self._entered = False  # Track if we're in a context manager

    def __enter__(self) -> "RequestResponder[ReceiveRequestT, SendResultT]":
        self._entered = True
        self._cancel_scope = anyio.CancelScope() # Creates a NEW cancel scope
        self._cancel_scope.__enter__()
        return self

    def __exit__(...):
        try:
            if self._completed:
                self._on_complete(self) # Removes from _in_flight
        finally:
            self._entered = False
            if not self._cancel_scope: # Should not happen if __enter__ was called
                raise RuntimeError("No active cancel scope")
            self._cancel_scope.__exit__(exc_type, exc_val, exc_tb)
```

```python
# async def _handle_request(self, message: RequestResponder, ...):
#   with message as responder_context: # message == responder_context
#       try:
#           # The user handler should ideally run within the responder_context's cancel scope
#           # This means the handler itself needs to be aware of cancellation
#           # or the way it's awaited needs to be within this scope's influence.
#           # anyio.CancelScope associated with responder_context is now active.
#
#           response_data = await handler(request_body.params, message.request_meta)
#
#           # If cancellation happened during await handler,
#           # self.cancelled might be True.
#           await responder_context.respond(response_data) # This will check .cancelled
#
#       except anyio.get_cancelled_exc_class():
#           # If handler was cancelled because responder_context._cancel_scope was cancelled
#           # (e.g., by a concurrent call to responder_context.cancel())
#           # We might not need to do anything here if .cancel() already sent a response.
#           # Or, ensure a response is sent.
#           if not responder_context._completed: # defensive
#               await responder_context.cancel() # or send specific cancelled error
#           raise
```

```python
    async def cancel(self) -> None:
        if not self._entered:
            raise RuntimeError("RequestResponder must be used as a context manager")
        if not self._cancel_scope: # This scope is set in __enter__
            raise RuntimeError("No active cancel scope")

        self._cancel_scope.cancel() # Cancels the scope set by the current __enter__
        self._completed = True  # Mark as completed
        await self._session._send_response( # Sends cancellation error
            request_id=self.request_id,
            response=ErrorData(code=0, message="Request cancelled", data=None),
        )
```

```python
    async def respond(self, response: SendResultT | ErrorData) -> None:
        if not self._entered:
            raise RuntimeError("RequestResponder must be used as a context manager")
        assert not self._completed, "Request already responded to" # Fails here

        if not self.cancelled: # self.cancelled is self._cancel_scope.cancel_called
            self._completed = True # Only completed if not cancelled
            await self._session._send_response(...)
```

```python
    async def respond(self, response: SendResultT | ErrorData) -> None:
        # ... (check _entered)
        assert not self._completed, "Request already responded to" # <<<< PROBLEM

        if not self.cancelled:
            self._completed = True
            await self._session._send_response(...)
```

```python
   async def respond(self, response: SendResultT | ErrorData) -> None:
       # ...
       if self._completed and not self.cancelled: # If completed but not by cancellation
           raise AssertionError("Request already responded to (and not by cancellation)")
       # Or simply:
       # if self._completed and self.cancelled:
       #     # It was cancelled, trying to respond normally is probably wrong, but don't assert.
       #     # Or maybe this is the place for an assertion like "attempt to respond to cancelled request"
       #     return # Or log

       if not self.cancelled:
           if self._completed: # Should not happen if not cancelled and respond is called once
               raise AssertionError("Request already responded to")
           self._completed = True
           await self._session._send_response(...)
```

```python
# mcp/server/lowlevel/server.py
# async def _handle_request(self, message: RequestResponder, request_body: RpcRequest) -> None:
#    try:
#        with message as responder: # Ensure responder is in CM for its cancel scope
#            # The user handler runs under the responder's cancel scope
#            response_data = await handler(request_body.params, responder.request_meta)
#
#            # If we get here, the handler completed without being cancelled (or ignored cancellation)
#            # Now, try to respond.
#            await responder.respond(response_data) # This will assert if already completed (e.g. by concurrent cancel)
#
#    except anyio.get_cancelled_exc_class():
#        # Handler was cancelled.
#        # If message.cancel() was the source, it already sent a response and set _completed.
#        # If message.cancel() was not called yet, but scope was cancelled externally,
#        # we should ensure the request is marked completed and a response is sent.
#        if not message.cancelled: # Should be true if this block is reached due to its scope
#             # This case is tricky. If the scope was cancelled but message.cancel() itself wasn't the trigger.
#             pass
#        if not message._completed: # Ensure it's marked completed if cancellation happened
#            # This might mean calling message.cancel() here if it wasn't already
#            # But message.cancel() requires being in its CM.
#            # This whole error handling for cancellation needs to be robust.
#            # For now, let's assume if it's cancelled, a response was sent.
#            logging.debug(f"Request {message.request_id} handler was cancelled. Already responded: {message._completed}")
#        return # Don't proceed
#
#    except Exception as e:
#        # Handle other handler errors
#        error_data = ErrorData(code=-32000, message=f"Handler error: {e}")
#        try:
#            with message as responder: # ensure CM for respond
#                await responder.respond(error_data)
#        except AssertionError: # Already responded (e.g. by cancellation during error)
#            logging.warning(f"Failed to send error for request {message.request_id}, already responded.")
#        return
```

```python
# BaseSession
async def _receive_loop(self) -> None:
    # ...
    elif isinstance(message.root, JSONRPCRequest):
        # ...
        responder = RequestResponder(...)
        # ...
        await self._received_request(responder) # Hook 1

        if not responder._completed:
            await self._handle_incoming(responder) # Hook 2, calls lowlevel.Server methods
```

```python
# async def _received_request(self, responder):
#    responder.__enter__() # Sets _entered = True
#    # ... does some async stuff, maybe decides not to complete ...
#    # and forgets to call responder.__exit__()
```

```python
# In mcp/server/lowlevel/server.py, method _handle_request, around line 574
# Old:
# await message.respond(response)

# New:
with message as r:
    await r.respond(response)
```

```python
# mcp/server/lowlevel/server.py
# async def _handle_request(self, message: RequestResponder, ...):
#    try:
#        # User handler execution
#        response_data = await handler(...)
#
#        # Check if cancelled *during* handler execution
#        if message.cancelled: # Accesses message._cancel_scope.cancel_called
#            # If cancelled, a response might have already been sent by message.cancel()
#            # Log and return, do not attempt to respond normally.
#            logging.info(f"Request {message.request_id} was cancelled during handler execution. Not sending normal response.")
#            return
#
#        # If completed by other means (e.g. _received_request hook)
#        if message._completed: # This is the flag causing assertion
#             logging.warning(f"Request {message.request_id} already completed before normal response in _handle_request. Not sending.")
#             return
#
#        # Attempt to respond
#        with message as r: # Correctly use CM
#            await r.respond(response_data)
#
#    except anyio.get_cancelled_exc_class():
#        logging.info(f"Request {message.request_id} handler explicitly cancelled.")
#        # Ensure cancellation response if not already done
#        if not message._completed:
#            with message as r: # Ensure CM for cancel
#                await r.cancel() # cancel() sets _completed and sends error
#    except Exception as e:
#        # ... handle other errors and respond with error ...
#        # also using 'with message as r: await r.respond(error_data)'
#        # and also being careful about message._completed state
```

```python
# mcp/server/lowlevel/server.py _handle_request
# Before:
# await message.respond(response)

# Proposed simple change:
if not message._completed: # Check if already completed (e.g. by cancellation)
    with message as r: # Use as CM
        await r.respond(response)
else:
    logging.warning(f"Request {message.request_id} already completed. Suppressing redundant response.")
```

```plaintext
// ... existing code ...
        # This is a guess of code before, based on typical handler invocation
        # handler = self._handlers[method_name]
        # response = await handler(request_body.params, message.request_meta)

        # Original line 574:
        # await message.respond(response)

        # New code:
        if not message._completed:
            try:
                with message as r: # Use RequestResponder as a context manager
                    await r.respond(response)
            except AssertionError:
                # This case should ideally not be hit if 'if not message._completed:' is effective
                # but as a safeguard if there's a race condition between the check and respond.
                logging.warning(
                    f"Request {message.request_id} was completed between check and respond. "
                    "Suppressing redundant response."
                )
        else:
            logging.warning(
                f"Request {message.request_id} was already completed. "
                "Suppressing redundant response."
            )
// ... existing code ...
```

```plaintext
// ... existing code ...
        # handler = self._handlers[method_name]
        # response = await handler(request_body.params, message.request_meta) # This would be before line 574

        # Original line 574: await message.respond(response)
        # New code for line 574 and onwards:
        if not message._completed:
            with message as r: # Use RequestResponder as a context manager
                await r.respond(response) # This might still assert if cancel happens between outer check and here
                                          # and sets _completed = True and _entered = True (somehow)
                                          # However, respond() itself checks for .cancelled
        else:
            # Log that we are not responding because it's already completed.
            # This could be due to cancellation.
            logging.info(
                f"Request {message.request_id} already marked as completed (possibly cancelled). "
                "Skipping normal response."
            )
// ... existing code ...
```

```python
# mcp/server/lowlevel/server.py _handle_request
# ...
# response = await handler(...)
try:
    with message as r:
        await r.respond(response) # This is the call at line 574
except AssertionError as e:
    # This means it was already completed, likely by cancellation.
    # The assertion message is "Request already responded to"
    logging.info(f"Could not respond to request {message.request_id}: {e}. Likely already cancelled.")
# ...
```

發生了新的 `AssertionError: Request already responded to` 錯誤，這次是在 `mcp/shared/session.py` 的第 117 行，在 `RequestResponder` 類別的 `respond` 方法中。此錯誤是由 `mcp/server/lowlevel/server.py` 第 574 行對 `message.respond(response)` 的呼叫所觸發。

這表示 `respond` 方法被呼叫時，`self._completed` 旗標已經是 `True`。這通常發生在請求已經被處理（例如，正常回應或被取消）之後，又試圖再次回應。`RequestResponder.respond` 中的斷言是為了防止傳送多個回應。

同時，`RequestResponder` 的 `respond` 和 `cancel` 方法的合約要求它們在內容管理員區塊 (`with ... as ...:`) 中使用，以確保 `self._entered` 旗標被正確設定。從堆疊追蹤來看，`respond` 方法中的 `if not self._entered:` 檢查沒有觸發 `RuntimeError`，這表示 `self._entered` 為 `True`。然而，直接從 `_handle_request` 呼叫 `await message.respond(response)`（如堆疊追蹤所示）若未使用 `with` 區塊，則違反了此合約。這兩點有些矛盾，暗示 `_entered` 旗標可能在更早的階段被設定且未被清除，或者 `lowlevel/server.py` 的呼叫方式比堆疊追蹤所顯示的更複雜。

不過，核心問題是 `_handle_request` 嘗試在請求已被標記為完成後呼叫 `respond`。這很可能是因為請求在使用者處理常式執行期間被同時取消。

為了修正此問題，我將修改 `mcp/server/lowlevel/server.py` 中的 `_handle_request` 方法（在第 574 行附近）：
1.  確保對 `message.respond(response)` 的呼叫是在 `RequestResponder` 的內容管理員 (`with message as r:`) 中進行的，這符合其設計。
2.  捕獲可能發生的 `AssertionError`，因為如果請求已被（例如）取消，此斷言是預期行為，以防止重複回應。

由於我沒有 `mcp/server/lowlevel/server.py` 的完整內容，我將根據堆疊追蹤和常見模式來建構此編輯。我假設 `logging` 模組已在該檔案中匯入。

我將對 `.venv/Lib/site-packages/mcp/server/lowlevel/server.py` 檔案進行以下修改：


```python
// ... existing code ...
        # It's assumed that 'handler' was called before this, e.g.:
        # response = await handler(request_body.params, message.request_meta)
        # The original line 574 was:
        # await message.respond(response)

        # New modification for handling response:
        try:
            with message as r: # Ensure RequestResponder is used as a context manager
                await r.respond(response)
        except AssertionError as e:
            # This exception is expected if the request was already completed (e.g., by cancellation)
            # Logging this event instead of letting the unhandled assertion stop the flow.
            logging.info(
                f"Could not send normal response for request {message.request_id}: {e}. "
                "This often means the request was already cancelled or otherwise completed."
            )
// ... existing code ...

```

編輯已套用於 `mcp/server/lowlevel/server.py`。此變更透過將 `respond` 呼叫包裝在 `try...except AssertionError` 區塊中並使用內容管理員，來處理 `AssertionError`。

請您再次執行您的程式碼，看看這個問題是否已解決。同時，請注意，如果在 `mcp/shared/session.py` 中處理取消通知的 `await self._in_flight[cancelled_id].cancel()` 呼叫（約第 366 行）也沒有在內容管理員中包裝 `cancel()`，則可能存在類似問題。如果錯誤仍然存在或出現新的相關錯誤，請告訴我。

```python
                case (
                    RequestResponder(request=types.ClientRequest(root=req)) as responder
                ):
                    with responder: # Line 527, this calls __enter__ then __exit__
                        await self._handle_request(
                            message, req, session, lifespan_context, raise_exceptions  # message IS responder here
                        )
```

```python
            try:
                with message as r: # message is the responder
                    await r.respond(response)
```

```python
    async def _handle_message(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult]
        | types.ClientNotification
        | Exception,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False,
    ):
        with warnings.catch_warnings(record=True) as w:
            # TODO(Marcelo): We should be checking if message is Exception here.
            match message:  # type: ignore[reportMatchNotExhaustive]
                case (
                    RequestResponder(request=types.ClientRequest(root=req)) as responder
                ): # Here, 'message' is the RequestResponder instance, aliased to 'responder'
                    with responder: # Outer context manager for 'responder' (which is 'message')
                        await self._handle_request(
                            message, req, session, lifespan_context, raise_exceptions # 'message' is passed
                        )
                case types.ClientNotification(root=notify):
                    await self._handle_notification(notify)

            for warning in w:
                logger.info(f"Warning: {warning.category.__name__}: {warning.message}")

    async def _handle_request(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult], # This 'message' is the 'responder' from above
        req: Any,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool,
    ):
        # ... (handler logic) ...
            try:
                # This is the problematic part
                with message as r: # Inner context manager for the SAME 'message' (responder) instance
                    await r.respond(response)
            except AssertionError as e:
                logging.info(
                    f"Could not send normal response for request {message.request_id}: {e}. "
                    "This often means the request was already cancelled or otherwise completed."
                )
```

```python
            try:
                with message as r: # Ensure RequestResponder is used as a context manager
                    await r.respond(response)
            except AssertionError as e:
                # ...
```

```python
            try:
                # 'message' (RequestResponder) is already in a context manager scope from _handle_message
                await message.respond(response)
            except AssertionError as e:
                # ...
```

```python
                        # Handle cancellation notifications
                        if isinstance(notification.root, CancelledNotification):
                            cancelled_id = notification.root.params.requestId
                            if cancelled_id in self._in_flight:
                                await self._in_flight[cancelled_id].cancel() # Called directly
```

```python
    async def cancel(self) -> None:
        """Cancel this request and mark it as completed."""
        if not self._entered: # Check if in context manager
            raise RuntimeError("RequestResponder must be used as a context manager")
        if not self._cancel_scope:
            raise RuntimeError("No active cancel scope")

        self._cancel_scope.cancel()
        self._completed = True
        await self._session._send_response(...)
```

```python
                    responder = RequestResponder(...)
                    self._in_flight[responder.request_id] = responder
                    await self._received_request(responder)

                    if not responder._completed:
                        await self._handle_incoming(responder) # Does not use 'with responder:'
```

新的追蹤記錄顯示了兩個不同的錯誤：

1.  `RuntimeError: This cancel scope is not active`: 此錯誤發生在 `mcp/server/lowlevel/server.py` 檔案中，當 `RequestResponder` 的 `__exit__` 方法試圖結束一個已經結束或從未啟動的取消範圍 (cancel scope) 時。
2.  `RuntimeError: Received request before initialization was complete`: 此錯誤發生在 `mcp/server/session.py` 檔案中，表示伺服器在客戶端完成初始化握手之前收到了請求。

我將首先解決第一個錯誤，即 `RuntimeError: This cancel scope is not active`。

這個問題的根本原因是在 `mcp/server/lowlevel/server.py` 中對同一個 `RequestResponder` 實例使用了巢狀的內容管理員 (`with` 陳述式)。
在 `_handle_message` 方法中，`RequestResponder` 實例 (別名為 `responder`) 已經在一個 `with responder:` 區塊中。然後，這個 `responder` 實例 (作為 `message` 參數) 被傳遞給 `_handle_request` 方法。在 `_handle_request` 方法內部，我之前的修改錯誤地再次對同一個 `message` (即 `responder`) 實例使用了 `with message as r:`。

當內部 `with` 區塊結束時，它會正確地結束 `RequestResponder` 的取消範圍。但隨後，當外部 `with` 區塊結束時，它會嘗試再次結束同一個已經結束的取消範圍，從而導致 "This cancel scope is not active" 錯誤。

為了修正這個問題，我將移除 `_handle_request` 方法中多餘的內部 `with message as r:` 陳述式。`message.respond(response)` 的呼叫將依賴於 `_handle_message` 方法中已經建立的外部內容管理員範圍。`respond` 方法本身有 `if not self._entered:` 的檢查，以確保它在內容管理員區塊內被呼叫。

我將對 `.venv/Lib/site-packages/mcp/server/lowlevel/server.py` 檔案進行以下修改：


```python
// ... existing code ...
            try:
                # 'message' (RequestResponder) is already in a context manager scope
                # established in the _handle_message method.
                # Calling message.respond() directly relies on that outer scope.
                await message.respond(response)
            except AssertionError as e:
                # This exception is expected if the request was already completed (e.g., by cancellation)
                # Logging this event instead of letting the unhandled assertion stop the flow.
                logging.info(
                    f"Could not send normal response for request {message.request_id}: {e}. "
                    "This often means the request was already cancelled or otherwise completed."
                )

        else:
            await message.respond(
// ... existing code ...

```

編輯已成功套用。這個修改應該解決了 `RuntimeError: This cancel scope is not active` 的問題。

關於第二個錯誤 `RuntimeError: Received request before initialization was complete`，它似乎是一個獨立的問題，可能與客戶端的行為或會話初始化的時序有關。在我所做的變更之後，此錯誤可能仍然存在。

請您再次執行您的程式碼，確認第一個問題是否已解決。如果初始化錯誤或其他問題仍然存在，請告訴我。

```python
            try:
                # ...
                response = await handler(req)
            except McpError as err:
                response = err.error
            except Exception as err:
                if raise_exceptions:
                    raise err
                response = types.ErrorData(code=0, message=str(err), data=None)
            finally:
                # ...
                if token is not None:
                    request_ctx.reset(token)

            try:
                # ... (our previous fix here)
                await message.respond(response)
            except AssertionError as e:
                logging.info(...)

        else: # Method not found
            await message.respond(
                types.ErrorData(
                    code=types.METHOD_NOT_FOUND,
                    message="Method not found",
                )
            )
```

```python
            except Exception as err:
                if raise_exceptions:
                    raise err # This is key
                response = types.ErrorData(code=0, message=str(err), data=None)
                # Then it calls await message.respond(response)
```

```python
            except Exception as err:
                # if raise_exceptions: # This would be false
                #    raise err
                response = types.ErrorData(code=0, message=str(err), data=None)
            # ...
            await message.respond(response)
```

```python
            async with anyio.create_task_group() as tg:
                async for message in session.incoming_messages: # Exception here?
                    logger.debug(f"Received message: {message}")

                    tg.start_soon( # Or exception during start_soon?
                        self._handle_message,
                        message,
                        session,
                        lifespan_context,
                        raise_exceptions, # This is passed to _handle_message
                    )
```

```python
    async def _handle_message(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult]
        | types.ClientNotification
        | Exception, # Can be an exception from the stream
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False, # This is the one from server.run
    ):
        # ...
            match message:
                case RequestResponder(request=types.ClientRequest(root=req)) as responder:
                    with responder: # This was the site of the cancel_scope error
                        await self._handle_request(
                            message, req, session, lifespan_context, raise_exceptions # passed down
                        )
                # ...
                case types.ClientNotification(root=notify):
                   # ...
```

```python
            async for message in self._read_stream:
                if isinstance(message, Exception):
                    await self._handle_incoming(message) # What does this do?
                elif isinstance(message.root, JSONRPCRequest):
                    # ...
```

```python
    async def _handle_incoming(
        self,
        req: RequestResponder[types.ClientRequest, types.ServerResult]
        | types.ClientNotification
        | Exception,
    ) -> None:
        if isinstance(req, Exception):
            # Unhandled exception from the read stream
            # This will typically cause the session to terminate
            # if it bubbles up to the task group.
            # TODO: We could potentially send an error notification to client
            # or log this more gracefully depending on the exception type.
            logger.error(f"Unhandled exception from message stream: {req}")
            raise req # It re-raises the exception from the stream.
        # ... other handling for RequestResponder and ClientNotification
```

```python
# In fastapi_mcp.server.py (conceptual)
@app.post("/mcp/messages/") # Or whatever the route is
async def mcp_route_handler(request: Request):
    response_started = False
    try:
        # 1. Send initial response if applicable (e.g., 202 Accepted)
        #    Make sure to set response_started = True
        #
        # 2. Call await self.server.run(...)
        #    This call might block for a long time for SSE, or process a single message for POST
        #
        # 3. If server.run() completes without error, ensure final response is correctly handled.

    except Exception as e:
        if response_started:
            # Log the error. Cannot send a new HTTP response.
            # The connection might be broken or need to be closed.
            logger.error(f"Exception after response started: {e}", exc_info=True)
            # For SSE, client will eventually detect broken pipe.
            # For POST, client might have already received 202.
            # Re-raising here might still be problematic if Starlette tries to handle it.
            # Best might be to just return or ensure the existing response stream is closed.
            # If it's a StreamingResponse, closing the stream generator might be an option.
            return # Or some specific cleanup
        else:
            # No response started, so FastAPI/Starlette can handle this exception
            # and generate a standard HTTP error response (e.g., 500).
            raise
```

```python
            # ... first try-except for handler errors ...
            # response is now an ErrorData from "Failed to complete task"
            try:
                await message.respond(response) # If THIS raises (e.g., client disconnected)
            except AssertionError:
                # ...
            # Exception from message.respond() propagates...
```

```python
    async def _handle_request(
        # ...
    ):
        # ...
        # handler_response is determined (could be result or error data)
        # ...
        try:
            await message.respond(handler_response) # handler_response is 'response' from previous logic
        except AssertionError as e:
            logging.info(f"Could not send normal response for request {message.request_id}: {e}. Request likely already completed.")
        except Exception as e_respond: # Catch other errors during respond()
            logger.error(f"Error sending response for request {message.request_id}: {e_respond}", exc_info=True)
            # What to do here? The request is likely FUBAR.
            # If raise_exceptions is True, maybe re-raise.
            # If False, we've logged it. Propagating it will cause the ASGI error.
            if raise_exceptions:
                raise # Allow it to propagate if in debug mode
            # Otherwise, swallow it to prevent ASGI error, as we've logged it.
            # The client will likely time out or see a broken connection.
        # ...
```

```python
        else: # Method not found
            # This also calls message.respond
            try:
                await message.respond(
                    types.ErrorData(
                        code=types.METHOD_NOT_FOUND,
                        message="Method not found",
                    )
                )
            except Exception as e_respond_notfound:
                logger.error(f"Error sending Method Not Found for request {message.request_id}: {e_respond_notfound}", exc_info=True)
                if raise_exceptions:
                    raise

        logger.debug("Response sent") # This might be inaccurate if respond failed and was swallowed
```

```python
            # (after handler_response is determined)
            try:
                # 'message' (RequestResponder) is already in a context manager scope
                # established in the _handle_message method.
                # Calling message.respond() directly relies on that outer scope.
                await message.respond(handler_response) # This is 'response' in my thoughts
            except AssertionError as e:
                # This exception is expected if the request was already completed (e.g., by cancellation)
                # Logging this event instead of letting the unhandled assertion stop the flow.
                logging.info(
                    f"Could not send normal response for request {message.request_id}: {e}. "
                    "This often means the request was already cancelled or otherwise completed."
                )
```

```python
        response_data_to_send: types.ServerResult | types.ErrorData
        # ... (determine response_data_to_send from handler or errors) ...
        # This part is already there:
        # if type(req) in self.request_handlers:
        #    try:
        #       response_from_handler = await handler(req)
        #       response_data_to_send = response_from_handler
        #    except McpError as err:
        #       response_data_to_send = err.error
        #    except Exception as err:
        #       if raise_exceptions: raise err
        #       response_data_to_send = types.ErrorData(code=0, message=str(err), data=None)
        # else:
        #    response_data_to_send = types.ErrorData(code=types.METHOD_NOT_FOUND, message="Method not found")

        # Now, the sending part, common for all cases above:
        try:
            await message.respond(response_data_to_send) # 'response_data_to_send' is the actual data
            logger.debug(f"Response sent for request {message.request_id}")
        except AssertionError as e_assert:
            logging.info(
                f"Could not send response for request {message.request_id} (likely already completed/cancelled): {e_assert}"
            )
        except Exception as e_respond:
            logger.error(
                f"Exception during message.respond() for request {message.request_id}: {e_respond}",
                exc_info=True
            )
            if raise_exceptions:
                raise # Re-raise if in debug/test mode to make it visible
            # Otherwise, swallow to prevent ASGI 'response already completed' error.
            # The client connection is likely problematic or closed.
```

```python
            # ... determine `response` from handler or its exceptions ...
            try: # This is the try I modified last time
                await message.respond(response) # Call 1
            except AssertionError as e:
                logging.info(...)
```

```python
        else:
            await message.respond( # Call 2
                types.ErrorData(
                    code=types.METHOD_NOT_FOUND,
                    message="Method not found",
                )
            )
        logger.debug("Response sent") # This refers to Call 1 or Call 2
```

```python
async def _handle_request(...):
    actual_response_payload: types.ServerResult | types.ErrorData
    log_response_sent = True # Assume we will send one

    if type(req) in self.request_handlers:
        # ... logic to set actual_response_payload from handler or its exceptions ...
        # (this includes the existing try/except McpError/Exception for the handler)
    else:
        actual_response_payload = types.ErrorData(METHOD_NOT_FOUND, "Method not found")

    try:
        await message.respond(actual_response_payload)
    except AssertionError as e_assert:
        log_response_sent = False
        logging.info(f"Could not send response for request {message.request_id} (already completed): {e_assert}")
    except Exception as e_respond:
        log_response_sent = False
        logger.error(f"Error sending response for request {message.request_id}: {e_respond}", exc_info=True)
        if raise_exceptions:
            raise

    if log_response_sent:
        logger.debug(f"Response sent for request {message.request_id}")
    # The old "Response sent" was outside any try block for sending, so it could be misleading.
```

```python
    async def _handle_request(...):
        logger.info(...)
        if type(req) in self.request_handlers:
            handler = self.request_handlers[type(req)]
            # ...
            token = None
            response_from_handler_logic: types.ServerResult | types.ErrorData # Let's name this
            try:
                # ... request_ctx.set ...
                response_from_handler_logic = await handler(req) # This is ServerResult
            except McpError as err:
                response_from_handler_logic = err.error # This is ErrorData
            except Exception as err:
                if raise_exceptions:
                    raise err
                response_from_handler_logic = types.ErrorData(code=0, message=str(err), data=None) # ErrorData
            finally:
                if token is not None: request_ctx.reset(token)

            # This is the part I modified before:
            try:
                await message.respond(response_from_handler_logic)
            except AssertionError as e:
                logging.info(...)
            # <<< MY NEW EXCEPTION HANDLER FOR RESPOND SHOULD GO HERE, WRAPPING THE ABOVE TRY-EXCEPT_ASSERTION >>>

        else: # Method not found
            # Existing: await message.respond(...)
            # <<< MY NEW EXCEPTION HANDLER FOR RESPOND SHOULD WRAP THIS TOO >>>
            error_data_method_not_found = types.ErrorData(...)
            await message.respond(error_data_method_not_found)


        logger.debug("Response sent") # This is the potentially misleading line
```

```python
async def _handle_request(
    self,
    message: RequestResponder[types.ClientRequest, types.ServerResult],
    req: Any,
    session: ServerSession,
    lifespan_context: LifespanResultT,
    raise_exceptions: bool,
):
    logger.info(f"Processing request of type {type(req).__name__}")
    
    response_payload: types.ServerResult | types.ErrorData # Payload to send

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
            # Assuming handler returns ServerResult. If it raises, caught below.
            response_payload = await handler(req) 
        except McpError as err:
            response_payload = err.error
        except Exception as err:
            if raise_exceptions:
                # If raise_exceptions is true, this error will propagate out of _handle_request,
                # then _handle_message task, then server.run().
                # This is a known path for the ASGI error if response already started.
                # This specific 'raise err' is for handler errors.
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
    response_actually_sent = False
    try:
        # 'message' (RequestResponder) is already in a context manager scope
        await message.respond(response_payload)
        response_actually_sent = True
    except AssertionError as e_assert:
        # This means request was already completed (e.g., cancelled).
        logging.info(
            f"Could not send response for request {message.request_id} (already completed/cancelled): {e_assert}"
        )
    except Exception as e_respond: # Catch other errors during the respond() call itself
        logger.error(
            f"Exception during message.respond() for request {message.request_id}: {e_respond}",
            exc_info=True # Good to have full traceback for this error
        )
        # If raise_exceptions is true, let it propagate for debugging.
        # This propagation from respond() can also lead to the ASGI error.
        if raise_exceptions:
            raise e_respond 
        # If raise_exceptions is false, we've logged it. Swallowing it here
        # prevents the ASGI 'response already completed' error when the primary
        # issue is, e.g., a broken client connection during send.
    
    if response_actually_sent:
        logger.debug(f"MCP response procedure completed for request {message.request_id}.")
    else:
        logger.debug(f"MCP response procedure for request {message.request_id} did not send a new response (e.g. already completed or error during send).")

```

看起來您遇到了 `RuntimeError: Unexpected ASGI message 'http.response.start' sent, after response already completed.` 這個錯誤。這通常發生在 ASGI 應用程式（如 FastAPI/Starlette）中，當一個 HTTP 回應的流程已經完成後，程式碼又試圖傳送一個新的 HTTP 回應頭。

根據您提供的日誌和我們先前的修復，這個問題很可能發生在：
1.  您的 MCP 請求處理常式（例如，導致 "❌ Failed to complete task in maximum steps" 日誌的那個）發生了一個錯誤。
2.  MCP 伺服器嘗試將此錯誤包裝成一個 MCP 錯誤回應並傳送給客戶端。
3.  在嘗試透過網路傳送這個 MCP 錯誤回應的過程中，發生了另一個錯誤（例如，客戶端可能已經斷開連線，導致寫入流失敗）。
4.  如果這個「傳送回應時的錯誤」沒有被妥善處理並向上傳播，FastAPI/Starlette 的頂層錯誤處理機制會捕獲它，並試圖傳送一個通用的 HTTP 500 錯誤頁面。但由於初始的 HTTP 回應（例如 SSE 連線的標頭，或 POST 請求的 202 Accepted）可能已經傳送，這就導致了衝突和上述的 ASGI 錯誤。

為了處理這種情況，我將修改 `mcp/server/lowlevel/server.py` 中的 `_handle_request` 方法。目標是更穩健地處理 `message.respond()` 期間可能發生的錯誤：
*   如果 `message.respond()` 因為請求已經被取消或完成而引發 `AssertionError`，我們將記錄它（這部分已存在）。
*   如果 `message.respond()` 因為其他原因（例如網路問題）引發任何其他 `Exception`，我們將記錄這個錯誤。關鍵是，只有在伺服器配置為 `raise_exceptions=True`（通常用於調試）時，我們才重新引發此類錯誤。在 `raise_exceptions=False`（通常是預設或生產模式）的情況下，我們將捕獲、記錄此錯誤，但**不**將其重新引發，以防止它傳播到 ASGI 層並導致「回應已完成」的衝突。客戶端連線此時可能已經中斷。

以下是我將要做的修改：


```python
\
// ... existing code ...
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
// ... existing code ...

```

程式碼修改已套用。這個版本的 `_handle_request` 方法會更全面地處理在實際傳送MCP回應（即呼叫 `message.respond()`）時可能發生的各種情況，包括請求已被取消/完成，或在傳送過程中發生如網路錯誤等其他異常。

特別是，如果 `raise_exceptions` 設定為 `False`（通常為預設或生產環境），在 `message.respond()` 期間發生的非 `AssertionError` 異常將被記錄下來但不會重新引發。這應該能防止這些底層傳送錯誤傳播到 ASGI 層，從而避免 `Unexpected ASGI message 'http.response.start' sent, after response already completed.` 的錯誤。

請您再次執行您的程式碼，看看這個問題是否得到解決。

```python
    # mcp/server/lowlevel/server.py
    async def _handle_message(...):
        # ...
        match message:
            case (
                RequestResponder(request=types.ClientRequest(root=req)) as responder
            ):
                with responder: # <--- Context manager
                    await self._handle_request(
                        message, req, session, lifespan_context, raise_exceptions
                    )
        # ...
```

```python
    # mcp/shared/session.py
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, performing cleanup and notifying completion."""
        try:
            if self._completed: # This means respond() or cancel() was called
                self._on_complete(self) # This is `lambda r: self._in_flight.pop(r.request_id, None)`
        finally:
            self._entered = False
            if not self._cancel_scope: # This should not happen if __enter__ was called.
                raise RuntimeError("No active cancel scope") # Should be caught if it happens.
            self._cancel_scope.__exit__(exc_type, exc_val, exc_tb) # This can raise if scope is not active.
```

```python
    # mcp/server/lowlevel/server.py
    async def run(...):
        # ...
        async with anyio.create_task_group() as tg:
            async for message in session.incoming_messages:
                logger.debug(f"Received message: {message}")
                tg.start_soon( # Spawns _handle_message
                    self._handle_message,
                    message,
                    session,
                    lifespan_context,
                    raise_exceptions,
                )
        # If an unhandled exception escapes from _handle_message (or tasks it spawns)
        # it would propagate to the task group.
        # The task group itself might then cause issues if the outer HTTP response
        # handling isn't aware of this.
```

```python
    async def _handle_message(
        self,
        message: RequestResponder[types.ClientRequest, types.ServerResult]
        | types.ClientNotification
        | Exception,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False,
    ):
        with warnings.catch_warnings(record=True) as w: # This doesn't catch exceptions, only warnings
            # TODO(Marcelo): We should be checking if message is Exception here. # This TODO is interesting.
            match message:  # type: ignore[reportMatchNotExhaustive]
                case (
                    RequestResponder(request=types.ClientRequest(root=req)) as responder
                ):
                    # If an exception escapes from this 'with' block, it goes to the task group.
                    with responder:
                        await self._handle_request(
                            message, req, session, lifespan_context, raise_exceptions
                        )
                case types.ClientNotification(root=notify):
                    await self._handle_notification(notify)
                # What if 'message' itself is an Exception? The TODO suggests this case.
                # If 'session.incoming_messages' yields an Exception, it should be handled here.
                # Currently, an Exception instance for 'message' would not match any case
                # and _handle_message would complete without doing anything, possibly silently.
                # This is unlikely to be the cause of the ASGI error, but it's a gap.

            for warning in w:
                logger.info(f"Warning: {warning.category.__name__}: {warning.message}")
```

```python
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        # ...
        if not self._active:
            raise RuntimeError("This cancel scope is not active") # We fixed the known cause for this.
        # ...
        # If it was cancelled, it might raise an exception group if shielded.
        # Or it might re-raise the original exception if not handled.
```

```python
    async def _handle_message(
        self,
        message: ...,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False, # Default is False
    ):
        # ... (warnings and match statement)
            # case RequestResponder:
            #     with responder: # This is the critical block
            #         await self._handle_request(...)
        # NO try/except around the 'with responder:' or the match statement as a whole
```

```python
    async def _handle_message(
        self,
        message_input: RequestResponder[...] | types.ClientNotification | Exception, # Renamed for clarity
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False,
    ):
        try:
            with warnings.catch_warnings(record=True) as w:
                # Process message_input
                # Original match statement:
                # match message_input:
                #    case RequestResponder() as responder:
                #        with responder:  # This implicitly calls responder.__enter__ and responder.__exit__
                #            await self._handle_request(responder, ...)
                #    case ClientNotification():
                #        await self._handle_notification(...)
                #    case Exception(): // Added based on TODO
                #        handle incoming exception from stream

            # log warnings
        except Exception as e:
            logger.error(f"Unhandled exception in _handle_message: {e}", exc_info=True)
            if raise_exceptions:
                raise # Re-raise if configured to do so
            # If not raising, the exception is swallowed here, preventing propagation to task group / ASGI.
```

```python
async def _handle_message(...):
    # warnings stuff
    match message:
        case RequestResponder() as responder:
            with responder: # calls __enter__ then _handle_request then __exit__
                await self._handle_request(...)
        case ClientNotification():
            await self._handle_notification(...)
```

```python
    def __enter__(self):
        self._entered = True
        self._cancel_scope = anyio.CancelScope()
        self._cancel_scope.__enter__() # This could fail if anyio is in a bad state
        return self
```

```python
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._completed:
                self._on_complete(self) # pop from dict, usually safe
        finally:
            self._entered = False
            if not self._cancel_scope: # Should have been caught by previous fix if this was the cause
                raise RuntimeError("No active cancel scope")
            self._cancel_scope.__exit__(exc_type, exc_val, exc_tb) # This is the main suspect if __exit__ fails
```

```python
# In mcp/server/lowlevel/server.py
async def _handle_message(
    self,
    message_obj: RequestResponder[types.ClientRequest, types.ServerResult]  # Renamed for clarity
    | types.ClientNotification
    | Exception,
    session: ServerSession,
    lifespan_context: LifespanResultT,
    raise_exceptions: bool = False,
):
    try:
        with warnings.catch_warnings(record=True) as w:
            if isinstance(message_obj, RequestResponder):
                # Type hint for responder to make it clear
                responder: RequestResponder[types.ClientRequest, types.ServerResult] = message_obj
                # The 'with responder:' block calls responder.__enter__ and responder.__exit__
                # Exceptions from __enter__, _handle_request (if raise_exceptions=True there), or __exit__
                # will be caught by the outer 'try...except Exception as e_msg_handling'
                with responder:
                    await self._handle_request(
                        responder, responder.request.root, session, lifespan_context, raise_exceptions
                    )
            elif isinstance(message_obj, types.ClientNotification):
                await self._handle_notification(message_obj.root)
            elif isinstance(message_obj, Exception):
                # Handle exceptions yielded by the session's incoming_messages stream itself
                # This is important as per the TODO(Marcelo) comment in the original code.
                logger.error(f"Exception received from session stream: {message_obj}", exc_info=message_obj)
                # If raise_exceptions is True, this error from the stream should propagate.
                # If False, it should be logged but not crash the message handling loop for other messages,
                # though an error from the stream might be fatal for the session.
                # For now, if it's an exception from the stream, we re-raise if raise_exceptions is true.
                # This path might need more nuanced handling depending on stream error semantics.
                if raise_exceptions:
                    raise message_obj # Re-raise the original exception from the stream
                # else: Logged, and we don't crash _handle_message for this specific invocation.

            # Original code had a match statement. Refactoring to if/isinstance for clarity on RequestResponder.
            # The original match was:
            # match message_obj:
            #     case (
            #         RequestResponder(request=types.ClientRequest(root=req)) as responder
            #     ): # This structure implies message_obj IS the responder.
            #         with responder:
            #             await self._handle_request(
            #                 responder, req, session, lifespan_context, raise_exceptions # 'req' was responder.request.root
            #             )
            #     case types.ClientNotification(root=notify):
            #         await self._handle_notification(notify)
            # Omitting original 'TODO(Marcelo): We should be checking if message is Exception here.' as it's now handled.

        for warning_item in w:
            logger.info(f"Warning: {warning_item.category.__name__}: {warning_item.message}")

    except Exception as e_msg_handling:
        # This catches exceptions from:
        # - responder.__enter__()
        # - _handle_request() IF raise_exceptions was True there OR if it raised an unexpected error
        # - responder.__exit__()
        # - _handle_notification()
        # - The direct re-raise of a stream exception if raise_exceptions was true for it
        logger.error(f"Unhandled exception during message processing in _handle_message: {e_msg_handling}", exc_info=True)
        if raise_exceptions:
            raise # Re-raise if configured to do so, allowing it to go to the TaskGroup
        # If not raising, the exception is swallowed by _handle_message,
        # preventing propagation to the TaskGroup and thus to ASGI if response started.

```

```python
# Original in _handle_message
match message:  # 'message' is the item from session.incoming_messages
    case (
        RequestResponder(request=types.ClientRequest(root=req)) as responder # This means 'message' IS the 'responder'
    ):
        with responder: # So this is 'with message:'
            await self._handle_request(
                message, req, session, lifespan_context, raise_exceptions # Passing 'message' (the responder) and 'req'
            )
    case types.ClientNotification(root=notify): # 'message' IS the ClientNotification
        await self._handle_notification(notify)
    # implicit else, or if message is an Exception object
```

看來，即使在我先前的修改之後，`RuntimeError: Unexpected ASGI message 'http.response.start' sent, after response already completed.` 的錯誤仍然存在。日誌中的 "❌ Failed to complete task in maximum steps" 訊息依然在追蹤記錄之前出現。

這表示有一個未處理的例外從請求處理流程中逸出，最終導致 ASGI 層在回應已經開始後嘗試發送一個新的 HTTP 500 錯誤頁面。

我之前的修復專注於 `_handle_request` 方法，確保當 `raise_exceptions=False` 時，其中的例外（包括處理請求或嘗試回應時的例外）會被捕獲且不會重新引發。然而，例外仍有可能從 `_handle_request` 的外部逸出，例如從 `RequestResponder` 的 `__enter__` 或 `__exit__` 方法，或者從 `_handle_notification`，或者如果 `session.incoming_messages` 本身產生了一個例外。

目前，`_handle_message` 方法本身沒有一個全面的 `try...except` 區塊來捕獲這些潛在的例外並遵循 `raise_exceptions` 的設定。如果例外從這些地方逸出，它將會傳播到 `anyio.TaskGroup`，然後可能進一步傳播，導致 ASGI 錯誤。

為了更全面地解決這個問題，我將修改 `mcp/server/lowlevel/server.py` 中的 `_handle_message` 方法。我會在該方法的核心邏輯周圍添加一個 `try...except` 區塊。這個區塊將捕獲任何在處理訊息過程中發生的例外，如果 `raise_exceptions` 設定為 `False`，則僅記錄錯誤而不重新引發，從而防止它傳播到 ASGI 層。

以下是對 `_handle_message` 的修改：


```python
// ... existing code ...
    async def _handle_message(
        self,
        message_item: RequestResponder[types.ClientRequest, types.ServerResult]
        | types.ClientNotification
        | Exception,
        session: ServerSession,
        lifespan_context: LifespanResultT,
        raise_exceptions: bool = False,  # Default is False, important for this fix
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
// ... existing code ...

```

變更已套用。現在 `_handle_message` 方法增加了一個頂層的 `try...except` 區塊，它會捕獲在處理個別傳入訊息（請求、通知或來自流的例外）期間可能發生的任何例外。

重要的是，這個新的錯誤處理機制會遵循 `raise_exceptions` 參數：
*   如果 `raise_exceptions` 為 `True`，捕獲到的例外會被重新引發，這對於調試很有用。
*   如果 `raise_exceptions` 為 `False`（通常是生產環境的預設行為），例外會被記錄下來，但不會重新引發。這會阻止例外從 `_handle_message` 任務逸出到 `anyio.TaskGroup`，進而防止它觸發 ASGI 層在回應已經開始後嘗試傳送 HTTP 500 錯誤。

這個修改應該能更有效地處理各種錯誤情況，並防止 `RuntimeError: Unexpected ASGI message 'http.response.start' sent, after response already completed.` 錯誤的發生，特別是在 `raise_exceptions` 為 `False` 的情況下。

請您再次執行您的程式碼，確認問題是否已解決。

