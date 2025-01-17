#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 清理临时文件函数
cleanup() {
    echo -e "${YELLOW}正在清理临时文件...${NC}"
    # 删除临时目录
    if [ -d "temp" ]; then
        rm -rf temp
        echo "✓ 已删除临时目录"
    fi
    # 删除工作目录
    if [ -d "repo-workspace" ]; then
        rm -rf repo-workspace
        echo "✓ 已删除工作目录"
    fi
    # 删除调试文件
    if [ -f "debug.md" ]; then
        rm debug.md
        echo "✓ 已删除调试文件"
    fi
    echo -e "${GREEN}清理完成${NC}"
}

# 清理所有内容函数（包括 PDF）
cleanup_all() {
    cleanup
    echo -e "${YELLOW}正在清理所有内容...${NC}"
    # 删除 PDF 输出目录
    if [ -d "repo-pdfs" ]; then
        rm -rf repo-pdfs
        echo "✓ 已删除 PDF 输出目录"
    fi
    echo -e "${GREEN}全部清理完成${NC}"
}

# 检查命令行参数
case "$1" in
    "clean")
        cleanup
        exit 0
        ;;
    "clean-all")
        cleanup_all
        exit 0
        ;;
esac

# 检查 Python 虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建 Python 虚拟环境...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 运行转换脚本
echo -e "${GREEN}运行转换脚本...${NC}"
python repo-to-pdf.py -c config.yaml

# 如果脚本执行失败，保留临时文件以便调试
if [ $? -ne 0 ]; then
    echo -e "${RED}转换失败，保留临时文件以便调试${NC}"
    exit 1
fi

# 如果指定了 --clean 参数，则清理临时文件
if [ "$1" == "--clean" ]; then
    cleanup
fi 