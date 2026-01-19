@echo off
echo 正在启动中国象棋AI分析器...
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

:: 安装依赖
echo 检查并安装依赖...
pip install -r requirements.txt

:: 启动服务
echo.
echo 启动Web服务...
python main.py --no-browser

pause