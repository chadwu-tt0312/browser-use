# Browser-Use MCP 伺服器

這是一個使用 MCP (Model Context Protocol) 機制的 Browser-Use 伺服器，取代了原本的 WebAPI 機制。

## 功能特色

- 🔧 **MCP 工具**: 提供 `search_task` 工具
- 🌐 **多模型支援**: 支援 Gemini、OpenAI、Azure 模型
- ⏱️ **超時控制**: 可設定任務執行超時時間
- 📝 **日誌記錄**: 完整的執行日誌和錯誤處理
- 🔄 **即時通訊**: 透過 MCP Context 發送即時狀態更新

## 安裝依賴

確保已安裝必要的套件：

```bash
pip install fastmcp
# 或使用 uv
uv add fastmcp
```

## 使用方式

### 1. 直接啟動伺服器

```bash
python examples/models/mcp_server.py
```

### 2. 使用啟動腳本

**Windows:**

```bash
run-mcp-server.bat
```

**Linux/macOS:**

```bash
./run-mcp-server.sh
```

### 3. 測試伺服器

```bash
python test_mcp_server.py
```

## 伺服器配置

- **主機**: 0.0.0.0
- **端口**: 8082
- **傳輸協議**: SSE (Server-Sent Events)
- **日誌檔案**: `logs/mcp_server.log`

## MCP 工具說明

### search_task

執行瀏覽器搜尋任務的主要工具，使用 AI 驅動的瀏覽器自動化代理。

**功能:**
- 執行網頁搜尋和數據提取
- 支援多種 AI 模型（根據環境變數 `UMC_SETTING` 自動選擇）
- 處理複雜的自然語言搜尋指令

**參數:**
- `task` (str): 自然語言搜尋任務描述
- `user_agent` (str, 可選): 自定義 User-Agent 字串，用於代理相容性
- `proxy_username` (str, 可選): 代理伺服器認證用戶名
- `proxy_password` (str, 可選): 代理伺服器認證密碼
- `context` (Context, 可選): MCP 上下文，用於日誌記錄和進度報告

**模型選擇:**
- 當 `UMC_SETTING=true` 時使用 Azure 模型（支援動態代理參數）
- 其他情況使用 Gemini 模型（不支援動態代理參數）

**範例:**

```python
# 基本調用
result = await client.call_tool("search_task", {
    "task": "請幫我用 bing 查詢最新的 AI 新聞，並列出 10 條最新的新聞標題和鏈接。"
})

# 使用自定義 User-Agent
result = await client.call_tool("search_task", {
    "task": "Search for Python tutorials on Google and summarize the top 5 results",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54"
})

# 使用代理認證
result = await client.call_tool("search_task", {
    "task": "Find information about climate change on Wikipedia",
    "proxy_username": "your_proxy_user",
    "proxy_password": "your_proxy_pass"
})

# 完整參數範例
result = await client.call_tool("search_task", {
    "task": "搜尋最新的 AI 技術趨勢",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/135.0.3179.54",
    "proxy_username": "proxy_user",
    "proxy_password": "proxy_pass"
})
```

## 動態參數功能

### User-Agent 動態設定

您可以透過 MCP 參數動態設定 User-Agent，這對於代理相容性特別有用：

- **僅 Azure 模型支援**: 只有當 `UMC_SETTING=true` 使用 Azure 模型時才支援動態 User-Agent
- **環境變數優先**: 如果設定了 `USER_AGENT` 環境變數，將作為預設值
- **參數覆蓋**: 透過 `user_agent` 參數可以覆蓋環境變數設定
- **版本相容性**: 不同的 Chrome/Edge 版本號碼可能影響代理連線能力

### 代理認證動態設定

代理伺服器的用戶名和密碼可以透過以下方式提供：

**⚠️ 注意**: 只有 Azure 模型（`UMC_SETTING=true`）支援代理功能

1. **環境變數**: 在 `HTTPS_PROXY` URL 中包含認證資訊
   ```
   HTTPS_PROXY=http://username:password@proxy.example.com:8080
   ```

2. **MCP 參數**: 透過 `proxy_username` 和 `proxy_password` 參數提供
   ```python
   result = await client.call_tool("search_task", {
       "task": "搜尋任務",
       "proxy_username": "your_username",
       "proxy_password": "your_password"
   })
   ```

3. **優先順序**: MCP 參數 > URL 中的認證資訊

## 與 WebAPI 版本的差異

| 特性 | WebAPI 版本 | MCP 版本 |
|------|-------------|----------|
| 協議 | HTTP REST API | MCP (Model Context Protocol) |
| 端口 | 8881 | 8082 |
| 請求格式 | JSON POST | MCP 工具調用 |
| 回應格式 | JSON 回應 | MCP 工具結果 |
| 即時通訊 | 無 | 支援 (透過 Context) |
| 客戶端整合 | 需要 HTTP 客戶端 | 原生 MCP 支援 |

## 客戶端整合

### Claude Desktop

在 Claude Desktop 的配置檔案中添加：

```json
{
  "mcpServers": {
    "browser-use-mcp": {
      "command": "python",
      "args": ["examples/models/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "your-api-key",
        "AZURE_OPENAI_KEY": "your-azure-key",
        "AZURE_OPENAI_ENDPOINT": "your-azure-endpoint"
      }
    }
  }
}
```

### Cursor IDE

在 `~/.cursor/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "browser-use-mcp": {
      "command": "python",
      "args": ["examples/models/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "your-api-key"
      }
    }
  }
}
```

## 環境變數

確保設定以下環境變數：

### 模型選擇

- `UMC_SETTING`: 設為 `"true"` 使用 Azure 模型，其他值或未設定則使用 Gemini 模型

### 代理和瀏覽器設定

- `USER_AGENT`: 預設 User-Agent 字串（可透過 MCP 參數覆蓋）
- `HTTPS_PROXY`: 代理伺服器 URL（當 `UMC_SETTING=true` 時需要）

### API 金鑰（根據使用的模型）

- `GEMINI_API_KEY`: Google Gemini API 金鑰（當使用 Gemini 模型時）
- `AZURE_OPENAI_KEY`: Azure OpenAI API 金鑰（當 `UMC_SETTING=true` 時）
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 端點（當 `UMC_SETTING=true` 時）
- `OPENAI_API_KEY`: OpenAI API 金鑰（當使用 OpenAI 模型時）

## 故障排除

### 常見問題

1. **導入錯誤**: 確保已安裝 `fastmcp` 套件
2. **端口衝突**: 檢查端口 8082 是否被其他程序佔用
3. **API 金鑰**: 確保環境變數正確設定

### 日誌檢查

查看日誌檔案以獲取詳細錯誤資訊：

```bash
tail -f logs/mcp_server.log
```

## 開發說明

### 添加新工具

在 `mcp_server.py` 中添加新的 MCP 工具：

```python
@mcp.tool()
async def new_tool(param1: str, param2: int = 10, context: Context = None) -> str:
    """新工具的描述"""
    # 工具邏輯
    if context:
        await context.session.send_log_message(
            level='info',
            data={'message': '工具執行中...'}
        )
    return "結果"
```

### 測試新功能

使用 MCP Inspector 進行測試：

```bash
# 如果 FastMCP 支援 dev 模式
fastmcp dev examples/models/mcp_server.py
```

## 相關資源

- [MCP 官方文檔](https://modelcontextprotocol.io/)
- [FastMCP 文檔](https://pypi.org/project/fastmcp/)
- [Browser-Use 專案](https://github.com/browser-use/browser-use)
