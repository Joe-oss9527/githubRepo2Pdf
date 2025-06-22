# GitHub Repo to PDF

一个将 GitHub 仓库代码转换为 PDF 文档的工具。支持语法高亮、中文显示，并且可以自定义配置。

## 功能特点

- 支持多种编程语言的语法高亮
- 自动生成目录树和代码统计
- 支持中文显示（跨平台字体自动检测）
- 可配置的文件过滤
- 自动处理大文件和长行
- 优雅的代码块展示
- 智能的日志输出控制
- 进度条显示
- 流式处理，避免内存溢出
- 错误恢复机制
- 自定义模板系统
- 完整的单元测试和集成测试
- 80%+ 测试覆盖率

## 系统要求

- Python 3.6+
- pandoc
- XeLaTeX
- Cairo
- Inkscape (可选，用于 SVG 转换)
- 中文字体（默认使用 Songti SC）

### macOS 安装依赖

所有依赖会通过 Makefile 自动安装，你只需要确保已安装 Xcode Command Line Tools：

```bash
xcode-select --install
```

### Linux (Ubuntu/Debian) 安装依赖

```bash
sudo apt-get update
sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended texlive-fonts-extra \
                     python3-venv python3-pip cairo-dev inkscape
```

## 使用方法

1. 克隆本仓库：
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. 修改配置文件 `config.yaml`：
   ```yaml
   repository:
     url: "https://github.com/用户名/仓库名.git"
     branch: "main"  # 或其他分支

   # 其他配置保持默认即可
   ```

3. 使用 make 命令：
   ```bash
   # 显示帮助信息
   make help

   # 安装依赖并转换为 PDF（默认命令）
   make

   # 以调试模式运行（显示详细日志）
   make debug
   # 或
   VERBOSE=1 make

   # 安静模式（只显示警告和错误）
   QUIET=1 make

   # 只安装依赖
   make deps

   # 只执行转换
   make convert

   # 清理临时文件
   make clean

   # 清理所有文件（包括生成的 PDF）
   make clean-all
   
   # 使用自定义模板
   TEMPLATE=technical make
   ```

生成的 PDF 文件将保存在 `repo-pdfs` 目录下。

## 模板系统

工具提供了灵活的模板系统，可以自定义 PDF 的结构和样式：

1. **使用内置模板**
   ```bash
   # 使用技术文档模板
   TEMPLATE=technical make
   
   # 使用默认模板
   TEMPLATE=default make
   ```

2. **创建自定义模板**
   在 `templates/` 目录下创建 YAML 文件，例如 `custom.yaml`：
   ```yaml
   name: "自定义模板"
   structure:
     include_tree: true
     include_stats: true
     sections:
       - title: "项目概览"
         content: |
           # {{repo_name}}
           生成时间：{{date}}
   ```

3. **可用的模板变量**
   - `{{repo_name}}` - 仓库名称
   - `{{date}}` - 生成日期

## 测试

项目包含完整的测试套件，确保代码质量和稳定性：

### 运行测试

```bash
# 运行所有测试
make test

# 运行单元测试
make test-unit

# 运行集成测试  
make test-integration

# 生成测试覆盖率报告
make test-coverage

# 使用测试脚本
./run_tests.sh
```

### 测试覆盖

- 单元测试覆盖核心功能模块
- 集成测试验证完整转换流程
- 测试覆盖率目标：80%+
- 支持 CI/CD 自动化测试

## 日志级别控制

工具提供了三种日志级别：

1. **正常模式**（默认）
   - 显示基本的进度信息
   - 显示重要的状态变更
   - 显示警告和错误

2. **详细模式**（使用 `make debug` 或 `VERBOSE=1`）
   - 显示所有调试信息
   - 显示详细的处理过程
   - 适合排查问题时使用

3. **安静模式**（使用 `QUIET=1`）
   - 只显示警告和错误信息
   - 适合在自动化脚本中使用

## 配置说明

`config.yaml` 支持以下配置项：

```yaml
# 仓库配置
repository:
  url: "仓库地址"
  branch: "main"

# 输出配置
workspace_dir: "./repo-workspace"  # 工作目录
output_dir: "./repo-pdfs"         # PDF 输出目录

# PDF 设置
pdf_settings:
  margin: "margin=1in"           # 页边距
  main_font: "Songti SC"         # 主字体
  mono_font: "SF Mono"           # 等宽字体（代码）
  highlight_style: "monochrome"  # 代码高亮主题

# 忽略的文件或目录
ignores:
  - "node_modules"
  - "dist"
  # ... 更多忽略项
```

## 支持的文件类型

- 前端：`.js`, `.jsx`, `.ts`, `.tsx`, `.vue`, `.svelte`, `.css`, `.scss`, `.sass`, `.less`, `.html`, `.json`, `.graphql`
- 后端：`.py`, `.java`, `.cpp`, `.c`, `.go`, `.rs`, `.rb`, `.php`, `.cs`
- 配置：`.yaml`, `.yml`, `.toml`, `.xml`, `.env`, `.ini`
- 其他：`.md`, `.mdx`, `.sh`, `.bash`, `.sql`
- 图片：`.svg`, `.png`, `.jpg`, `.jpeg`, `.gif`

## 注意事项

1. 默认跳过大于 1MB 的文件
2. 自动处理长行和大型代码块
3. 自动跳过二进制文件
4. SVG 文件会自动转换为 PNG
5. 支持中文文件名和内容
6. 日志输出可通过参数控制详细程度

## 常见问题

1. **PDF 生成失败**
   - 检查是否安装了所有依赖（运行 `make deps`）
   - 确认中文字体是否可用
   - 使用 `make debug` 查看详细日志
   - 查看 debug.md 文件了解详情

2. **中文显示异常**
   - 确认系统安装了配置文件中指定的字体
   - 尝试修改配置文件中的字体设置

3. **内存不足**
   - 增加被忽略的文件类型
   - 减小文件大小限制
   - 使用更简单的代码高亮主题

4. **SVG 转换失败**
   - 确保已安装 Cairo 和 Inkscape
   - 检查 SVG 文件格式是否正确
   - 使用 `make debug` 查看详细的转换日志

## License

MIT 