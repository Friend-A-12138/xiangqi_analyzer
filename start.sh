#!/bin/bash

echo "正在启动中国象棋AI分析器..."
echo

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

# 安装依赖
echo "检查并安装依赖..."
pip3 install -r requirements.txt

# 启动服务
echo
echo "启动Web服务..."
python3 main.py --no-browser

# 保持终端窗口打开
read -p "按回车键退出..."