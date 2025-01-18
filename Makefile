# 操作系统检测
UNAME_S := $(shell uname -s)

# 颜色定义
BLUE := \033[1;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[1;33m
NC := \033[0m

# Python 相关变量
PYTHON ?= python3
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

# 配置文件
CONFIG := config.yaml

# 目录
TEMP_DIR := temp
WORKSPACE_DIR := repo-workspace
PDF_DIR := repo-pdfs

# 依赖文件
REQUIREMENTS := requirements.txt

# 检查必要的命令
REQUIRED_CMDS := python3 git

# 运行参数
VERBOSE ?= 0
QUIET ?= 0
CONVERT_ARGS := -c $(CONFIG)
ifeq ($(VERBOSE),1)
    CONVERT_ARGS += -v
endif
ifeq ($(QUIET),1)
    CONVERT_ARGS += -q
endif

# 声明所有伪目标
.PHONY: all deps convert clean clean-all help check-reqs install-deps create-venv debug

# 默认目标
all: check-reqs deps convert

# 调试模式
debug: VERBOSE=1
debug: all

# 检查必要的命令是否存在
check-reqs:
	@for cmd in $(REQUIRED_CMDS); do \
		if ! command -v $$cmd >/dev/null 2>&1; then \
			echo "$(RED)错误: 找不到命令 '$$cmd'$(NC)"; \
			echo "$(YELLOW)请先安装必要的依赖$(NC)"; \
			exit 1; \
		fi \
	done

# 创建虚拟环境和安装依赖
deps: check-reqs install-deps create-venv

# 安装系统依赖
install-deps:
	@echo "$(BLUE)==> 检查系统依赖...$(NC)"
ifeq ($(UNAME_S),Darwin)
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "$(YELLOW)正在安装 Homebrew...$(NC)"; \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
	fi
	@if ! command -v inkscape >/dev/null 2>&1; then \
		echo "$(YELLOW)正在安装 Inkscape...$(NC)"; \
		brew install inkscape; \
	fi
	@if ! brew list cairo >/dev/null 2>&1; then \
		echo "$(YELLOW)正在安装 Cairo...$(NC)"; \
		brew install cairo; \
	fi
	@if ! brew list python >/dev/null 2>&1; then \
		echo "$(YELLOW)正在安装 Python...$(NC)"; \
		brew install python; \
	fi
else ifeq ($(UNAME_S),Linux)
	@echo "$(YELLOW)请确保已安装必要的系统依赖：$(NC)"
	@echo "sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended texlive-fonts-extra python3-venv python3-pip cairo-dev inkscape"
endif

# 创建并更新虚拟环境
create-venv: $(VENV)/deps-installed

$(VENV)/deps-installed: $(REQUIREMENTS)
	@echo "$(BLUE)==> 创建 Python 虚拟环境...$(NC)"
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@echo "$(BLUE)==> 安装 Python 依赖...$(NC)"
	@$(VENV_PIP) install --upgrade pip
	@$(VENV_PIP) install -r $(REQUIREMENTS)
	@touch $(VENV)/deps-installed

# 转换为 PDF
convert: deps
	@echo "$(BLUE)==> 开始转换...$(NC)"
	@if [ ! -f $(CONFIG) ]; then \
		echo "$(RED)错误: 找不到配置文件 $(CONFIG)$(NC)"; \
		exit 1; \
	fi
	@$(VENV_PYTHON) repo-to-pdf.py $(CONVERT_ARGS)

# 清理临时文件
clean:
	@echo "$(BLUE)==> 清理临时文件...$(NC)"
	@rm -rf $(TEMP_DIR)
	@rm -rf $(WORKSPACE_DIR)
	@rm -f debug.md
	@echo "$(GREEN)清理完成$(NC)"

# 清理所有文件（包括 PDF）
clean-all: clean
	@echo "$(BLUE)==> 清理所有文件...$(NC)"
	@rm -rf $(PDF_DIR)
	@rm -rf $(VENV)
	@echo "$(GREEN)全部清理完成$(NC)"

# 帮助信息
help:
	@echo "$(BLUE)可用的命令：$(NC)"
	@echo "  $(GREEN)make$(NC)          - 安装依赖并转换为 PDF"
	@echo "  $(GREEN)make deps$(NC)     - 安装所需的依赖"
	@echo "  $(GREEN)make convert$(NC)  - 仅执行转换"
	@echo "  $(GREEN)make debug$(NC)    - 以调试模式运行（显示详细日志）"
	@echo "  $(GREEN)make clean$(NC)    - 清理临时文件"
	@echo "  $(GREEN)make clean-all$(NC)- 清理所有文件（包括 PDF）"
	@echo "  $(GREEN)make help$(NC)     - 显示此帮助信息"
	@echo
	@echo "$(BLUE)运行参数：$(NC)"
	@echo "  $(GREEN)VERBOSE=1$(NC)     - 启用详细输出"
	@echo "  $(GREEN)QUIET=1$(NC)       - 只显示警告和错误" 