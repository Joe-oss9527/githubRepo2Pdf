#!/bin/bash

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "请先安装 Python 3"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 检查是否安装了必要的系统依赖
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if ! command -v brew &> /dev/null; then
        echo "请先安装 Homebrew"
        exit 1
    fi
    
    # 检查并安装必要的系统依赖
    if ! command -v pandoc &> /dev/null; then
        echo "安装 pandoc..."
        brew install pandoc
    fi
    
    if ! command -v xelatex &> /dev/null; then
        echo "安装 MacTeX..."
        brew install --cask mactex
    fi
    
    if ! brew list cairo &> /dev/null; then
        echo "安装 cairo..."
        brew install cairo
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if ! command -v pandoc &> /dev/null || ! command -v xelatex &> /dev/null; then
        echo "请运行以下命令安装必要的系统依赖："
        echo "sudo apt-get update"
        echo "sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended texlive-fonts-extra"
        exit 1
    fi
    
    if ! command -v cairo-trace &> /dev/null; then
        echo "请运行以下命令安装 cairo："
        echo "sudo apt-get install libcairo2-dev"
        exit 1
    fi
fi

# 运行脚本
echo "运行转换脚本..."
python repo-to-pdf.py -c config.yaml

# 退出虚拟环境
deactivate 