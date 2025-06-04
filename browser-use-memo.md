
## setup

1. uv venv --python=3.11
2. source .venv/Scripts/activate
3. uv add fastmcp
4. uv sync
5. (opt)uv pip install -e . --no-cache-dir --force-reinstall
6. (opt)playwright install --with-deps chromium
    + playwright --version
        + Version 1.49.1
        + Version 1.52.0

## RUN

1. uv run examples/models/azure_openai.py
2. uv run examples/models/api_server.py
3. uv run examples/models/mcp_server.py
    + run-mcp-server.sh
4. uv run examples/models/mcp_server2.py

## Memo (.env)

1. using GEMINI_API_KEY
2. using AZURE_OPENAI_KEY & AZURE_OPENAI_ENDPOINT
3. using OPENAI_API_KEY
4. add USER_AGENT (會根據 Edge 瀏覽器版本決定是否可以連線)
5. add HTTPS_PROXY (proxy 設定， 會暴露帳密)
    + 改成沒有帳密的格式
6. add UMC_SETTING (根據 T/F 決定 Browser 設定是否使用 proxy)
7. add TZ
8. playwright 會根據不同版本 package 安裝不同版本瀏覽器
    + chromium-1148 (v1.49.1)
    + chromium-1155
    + chromium-1169 (最新 v1.52.0)

## Memo (files)

0. fix browser_use\__init__.py
    + mark set_event_loop_policy()
1. fix browser_use\logging_config.py
2. add examples\models\api_server.py
3. add examples\models\mcp_server.py
4. fix examples\models\azure_openai.py
5. fix examples\models\gemini.py
6. fix examples\models\gpt_4o.py
    + old name is gpt-4o.py
7. add examples\models\mcp_server2.py

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

### Log

```bash
DEBUG    [browser]  ↳ Spawned browser subprocess: browser_pid=5496 C:\Users\chad\AppData\Local\ms-playwright\chromium-1169\chrome-win\chrome.exe --type=gpu-process --disable-breakpad --noerrdialogs --user-data-dir=C:\Users\chad\.config\browseruse\profiles\default --no-pre-read-main-dll --start-stack-profiler --gpu-preferences=UAAAAAAAAADgAAAEAAAAAAAAAAAAAAAAAABgAAEAAAAAAAAAAAAAAAAAAAACAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAEAAAAAAAAAAIAAAAAAAAAAgAAAAAAAAA --field-trial-handle=1956,i,7684095984264873977,1626716454442479953,262144 --enable-features=NetworkService,NetworkServiceInProcess --disable-features=AcceptCHFrame,AutoExpandDetailsElement,AutofillServerCommunication,AutomationControlled,AvoidUnnecessaryBeforeUnloadCheckSync,CalculateNativeWinOcclusion,CertificateTransparencyComponentUpdater,CrashReporting,DestroyProfileOnBrowserClose,DialMediaRouteProvider,ExtensionDisableUnsupportedDeveloper,ExtensionManifestV2Disabled,GlobalMediaControls,HeavyAdPrivacyMitigations,HttpsUpgrades,ImprovedCookieControls,InfiniteSessionRestore,InterestFeedContentSuggestions,LazyFrameLoading,LensOverlay,MediaRouter,OptimizationHints,OverscrollHistoryNavigation,PaintHolding,PrivacySandboxSettings4,ProcessPerSiteUpToMainFrameThreshold,ThirdPartyStoragePartitioning,Translate --variations-seed-version --log-level=2 --mojo-platform-channel-handle=1944 /prefetch:2
DEBUG    [browser] 📐 Setting up viewport: headless=False window=1920x1080px (no viewport) device_scale_factor=1.0 is_mobile=False color_scheme=light permissions=clipboard-read,clipboard-write,notifications
```
