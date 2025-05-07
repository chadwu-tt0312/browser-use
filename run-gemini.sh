#!/bin/bash

# 切換到專案目錄
cd /d/_Code/_GitHub/browser-use

# 啟動虛擬環境
source .venv/bin/activate
source .venv/Scripts/activate

# 執行命令
uv run examples/models/gemini.py

# 停用虛擬環境（可選）
deactivate
