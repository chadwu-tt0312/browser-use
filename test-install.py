#驗證安裝
# 安裝完成後，您可以執行以下程式碼驗證安裝是否成功
from browser_use.browser.browser import Browser, BrowserConfig

#建立瀏覽器實例
browser=Browser(config=BrowserConfig(
    # browser_instance_path="C:\\Users\\rpauser\\AppData\\Local\\ms-playwright\\chromium-1169\\chrome-win\\chrome.exe",
    browser_instance_path="C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe", 
    headless=True
))

#如果沒有報錯，表示安裝成功
print("browser-use安裝成功!")
