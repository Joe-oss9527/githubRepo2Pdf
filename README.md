# GitHub Repo to PDF

一个将 GitHub 仓库代码转换为 PDF 文档的工具。支持语法高亮、中文显示，并且可以自定义配置。

## 功能特点

- 支持多种编程语言的语法高亮
- 自动生成目录
- 支持中文显示
- 可配置的文件过滤
- 自动处理大文件和长行
- 优雅的代码块展示

## 系统要求

- Python 3.6+
- pandoc
- XeLaTeX
- 中文字体（默认使用 Songti SC）

### macOS 安装依赖

```bash
# 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装系统依赖
brew install pandoc
brew install --cask mactex
```

### Linux (Ubuntu/Debian) 安装依赖

```bash
sudo apt-get update
sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended texlive-fonts-extra
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

3. 运行脚本：
   ```bash
   # 基本用法
   ./run.sh

   # 运行完成后清理临时文件
   ./run.sh --clean

   # 仅清理临时文件
   ./run.sh clean

   # 清理所有文件（包括生成的 PDF）
   ./run.sh clean-all
   ```

生成的 PDF 文件将保存在 `repo-pdfs` 目录下。

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

## 注意事项

1. 默认跳过大于 1MB 的文件
2. 自动处理长行和大型代码块
3. 自动跳过二进制文件和图片
4. 支持中文文件名和内容

## 常见问题

1. **PDF 生成失败**
   - 检查是否安装了所有依赖
   - 确认中文字体是否可用
   - 查看 debug.md 文件了解详情

2. **中文显示异常**
   - 确认系统安装了配置文件中指定的字体
   - 尝试修改配置文件中的字体设置

3. **内存不足**
   - 增加被忽略的文件类型
   - 减小文件大小限制
   - 使用更简单的代码高亮主题

## License

MIT 