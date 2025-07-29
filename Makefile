# ========== 配置部分 ==========
PYTHON ?= python3
VENV ?= venv
CONFIG ?= config.yaml
TEMPLATE ?=
VERBOSE ?= 0
QUIET ?= 0

# 目录配置
WORKSPACE_DIR ?= repo-workspace
PDF_DIR ?= repo-pdfs
TEMP_DIR ?= temp
TEMPLATE_DIR ?= templates

# 系统检测
UNAME_S := $(shell uname -s)
IS_WSL := $(shell grep -qi microsoft /proc/version 2>/dev/null && echo 1 || echo 0)

# Python 虚拟环境
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

# 必要的命令
REQUIRED_CMDS := python3 git xelatex pandoc

# 转换参数
CONVERT_ARGS := -c $(CONFIG)
ifeq ($(VERBOSE),1)
    CONVERT_ARGS += -v
endif
ifeq ($(QUIET),1)
    CONVERT_ARGS += -q
endif
ifneq ($(TEMPLATE),)
    CONVERT_ARGS += -t $(TEMPLATE)
endif

# 设备预设支持
ifneq ($(DEVICE),)
    export DEVICE
endif

# ========== 目标定义 ==========
.PHONY: all help deps setup convert test clean clean-all install-deps \
        quickstart list-templates check-config test-unit test-integration test-coverage \
        kindle kindle7 tablet mobile desktop

# 默认目标
all: convert

# 帮助信息
help:
	@echo "GitHub Repo to PDF - 将代码仓库转换为 PDF 文档"
	@echo ""
	@echo "快速开始:"
	@echo "  make quickstart         # 创建示例配置文件"
	@echo "  make                    # 转换为 PDF"
	@echo "  make TEMPLATE=technical # 使用模板"
	@echo ""
	@echo "常用命令:"
	@echo "  make setup              # 安装依赖"
	@echo "  make convert            # 转换为 PDF"
	@echo "  make test               # 运行测试"
	@echo "  make clean              # 清理临时文件"
	@echo "  make clean-all          # 清理所有文件"
	@echo ""
	@echo "配置选项:"
	@echo "  CONFIG=file             # 指定配置文件"
	@echo "  TEMPLATE=name           # 使用模板"
	@echo "  DEVICE=preset           # 使用设备预设"
	@echo "  VERBOSE=1               # 详细输出"
	@echo "  QUIET=1                 # 静默模式"
	@echo ""
	@echo "设备预设:"
	@echo "  make kindle             # 7英寸Kindle优化"
	@echo "  make tablet             # 平板设备优化"
	@echo "  make mobile             # 手机设备优化"
	@echo "  make desktop            # 桌面端优化(默认)"

# 快速开始
quickstart:
	@if [ ! -f $(CONFIG) ]; then \
		echo "创建示例配置文件..."; \
		echo '# 仓库配置\nrepository:\n  url: "https://github.com/用户名/仓库名.git"\n  branch: "main"\n\nworkspace_dir: "./repo-workspace"\noutput_dir: "./repo-pdfs"\n\nignores:\n  - "node_modules"\n  - ".git"' > $(CONFIG); \
		echo "✓ 已创建 $(CONFIG)"; \
		echo "! 请编辑 $(CONFIG) 中的仓库地址"; \
	else \
		echo "✓ 配置文件已存在: $(CONFIG)"; \
	fi

# 列出模板
list-templates:
	@echo "可用的模板:"
	@if [ -d $(TEMPLATE_DIR) ]; then \
		for template in $(TEMPLATE_DIR)/*.yaml; do \
			if [ -f "$$template" ]; then \
				name=$$(basename $$template .yaml); \
				desc=$$(grep -m1 "description:" $$template 2>/dev/null | sed 's/.*description: *"\(.*\)"/\1/' || echo ""); \
				echo "  $$name - $$desc"; \
			fi \
		done; \
	else \
		echo "  (模板目录不存在)"; \
	fi

# 检查配置
check-config:
	@echo "当前配置:"
	@echo "  配置文件: $(CONFIG)"
	@echo "  模板: $(if $(TEMPLATE),$(TEMPLATE),无)"
	@echo "  Python: $(PYTHON)"
	@echo "  虚拟环境: $(VENV)"
	@echo "  输出目录: $(PDF_DIR)"
	@echo "  操作系统: $(UNAME_S)$(if $(filter 1,$(IS_WSL)), (WSL2),)"

# 安装依赖
deps: check-deps $(VENV)/deps-installed

setup: deps

# 检查系统命令
check-deps:
	@echo "检查必要的命令..."
	@missing=""; \
	for cmd in $(REQUIRED_CMDS); do \
		if ! command -v $$cmd >/dev/null 2>&1; then \
			missing="$$missing $$cmd"; \
		fi; \
	done; \
	if [ -n "$$missing" ]; then \
		echo "✗ 缺少以下命令:$$missing"; \
		echo "  请运行 'make install-deps' 安装"; \
		exit 1; \
	fi; \
	echo "✓ 所有必要的命令都已安装"

# 安装系统依赖
install-deps:
	@echo "安装系统依赖..."
ifeq ($(UNAME_S),Darwin)
	@# macOS
	@command -v brew >/dev/null 2>&1 || { \
		echo "安装 Homebrew..."; \
		/bin/bash -c "$$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; \
	}
	@for pkg in pandoc cairo; do \
		brew list $$pkg >/dev/null 2>&1 || brew install $$pkg; \
	done
	@command -v inkscape >/dev/null 2>&1 || brew install inkscape
	@command -v xelatex >/dev/null 2>&1 || brew install --cask mactex-no-gui
else ifeq ($(UNAME_S),Linux)
	@# Linux/WSL2
	@if [ "$(IS_WSL)" = "1" ]; then \
		echo "检测到 WSL2 环境"; \
	fi
	@if command -v apt-get >/dev/null 2>&1; then \
		echo "使用 apt-get 安装依赖..."; \
		sudo apt-get update && sudo apt-get install -y \
			pandoc texlive-xetex texlive-fonts-recommended \
			texlive-fonts-extra texlive-lang-chinese texlive-lang-greek \
			python3-venv python3-pip libcairo2-dev inkscape librsvg2-bin \
			fonts-noto-cjk fonts-wqy-microhei; \
	else \
		echo "请手动安装: pandoc texlive-xetex python3-venv cairo inkscape"; \
	fi
endif

# Python 虚拟环境
$(VENV)/deps-installed: requirements.txt
	@echo "设置 Python 环境..."
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@$(VENV_PIP) install --quiet --upgrade pip
	@$(VENV_PIP) install --quiet -r requirements.txt
	@touch $@
	@echo "✓ Python 依赖安装完成"

# 转换为 PDF
convert: deps
	@echo "开始转换 PDF..."
	@if [ ! -f $(CONFIG) ]; then \
		echo "✗ 找不到配置文件: $(CONFIG)"; \
		exit 1; \
	fi
	@$(VENV_PYTHON) repo-to-pdf.py $(CONVERT_ARGS)

# ========== 设备预设快捷命令 ==========

# Kindle 7英寸设备优化
kindle: kindle7
kindle7: deps
	@echo "使用Kindle 7英寸设备预设转换PDF..."
	@if [ ! -f $(CONFIG) ]; then \
		echo "✗ 找不到配置文件: $(CONFIG)"; \
		exit 1; \
	fi
	@DEVICE=kindle7 $(VENV_PYTHON) repo-to-pdf.py $(CONVERT_ARGS)

# 平板设备优化
tablet: deps
	@echo "使用平板设备预设转换PDF..."
	@if [ ! -f $(CONFIG) ]; then \
		echo "✗ 找不到配置文件: $(CONFIG)"; \
		exit 1; \
	fi
	@DEVICE=tablet $(VENV_PYTHON) repo-to-pdf.py $(CONVERT_ARGS)

# 手机设备优化
mobile: deps
	@echo "使用手机设备预设转换PDF..."
	@if [ ! -f $(CONFIG) ]; then \
		echo "✗ 找不到配置文件: $(CONFIG)"; \
		exit 1; \
	fi
	@DEVICE=mobile $(VENV_PYTHON) repo-to-pdf.py $(CONVERT_ARGS)

# 桌面端优化(默认)
desktop: deps
	@echo "使用桌面端预设转换PDF..."
	@if [ ! -f $(CONFIG) ]; then \
		echo "✗ 找不到配置文件: $(CONFIG)"; \
		exit 1; \
	fi
	@DEVICE=desktop $(VENV_PYTHON) repo-to-pdf.py $(CONVERT_ARGS)

# ========== 测试和其他 ==========

# 测试
test: deps
	@echo "运行所有测试..."
	@$(VENV_PYTHON) -m pytest

test-unit: deps
	@echo "运行单元测试..."
	@$(VENV_PYTHON) -m pytest tests/test_repo_to_pdf.py -v

test-integration: deps
	@echo "运行集成测试..."
	@$(VENV_PYTHON) -m pytest tests/test_integration.py -v

test-coverage: deps
	@echo "生成测试覆盖率报告..."
	@$(VENV_PYTHON) -m pytest --cov=repo_to_pdf --cov-report=html --cov-report=term

# 清理
clean:
	@echo "清理临时文件..."
	@rm -rf $(TEMP_DIR) temp_conversion_files
	@rm -rf $(WORKSPACE_DIR)
	@rm -f debug.md
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ 清理完成"

clean-all: clean
	@echo "清理所有生成文件..."
	@rm -rf $(PDF_DIR)
	@rm -rf $(VENV)
	@echo "✓ 全部清理完成"

# 调试模式
debug: VERBOSE=1
debug: convert