@echo off
chcp 65001
setlocal

REM 設定專案根目錄和虛擬環境路徑
set "PROJECT_ROOT=D:\_Code\_GitHub\browser-use"

set "VENV_PATH=%PROJECT_ROOT%\.venv\Scripts\activate"

REM 檢查是否傳入參數
if "%~1"=="" (
    echo 錯誤：請指定要執行的腳本路徑（相對於專案根目錄）
    exit /b 2
)

REM 切換到專案目錄
cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo 錯誤：無法切換到目錄 "%PROJECT_ROOT%"
    exit /b 3
)

REM 啟動虛擬環境
call "%VENV_PATH%"
if errorlevel 1 (
    echo 錯誤：無法啟動虛擬環境
    exit /b 4
)

REM 執行命令 (cmd 視窗下可以直接執行 uv，但 ndscheduler 的 shell_job 不行)
REM uv run "%~1"
C:\Users\chad\.local\bin\uv run "%~1"
if errorlevel 1 (
    echo 錯誤：無法執行 uv 命令
    exit /b 5
)

REM 停用虛擬環境（可選）
deactivate

endlocal