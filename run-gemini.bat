@echo off
chcp 65001
echo 請稍等...

cd /d D:\_Code\_GitHub\browser-use

REM 啟動虛擬環境
call .venv\Scripts\activate

REM 執行命令
c:\Users\chad\.local\bin\uv run examples\models\gemini.py

REM 停用虛擬環境（可選）
deactivate