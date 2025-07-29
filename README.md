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
- 设备预设系统（支持Kindle、平板、手机等设备优化）
- 完整的单元测试和集成测试
- 55%+ 测试覆盖率（持续改进中）

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
                     texlive-lang-chinese texlive-lang-greek python3-venv python3-pip \
                     cairo-dev inkscape
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
   
   # 使用设备预设
   make kindle    # 7英寸Kindle优化
   make tablet    # 平板设备优化
   make mobile    # 手机设备优化
   make desktop   # 桌面端优化（默认）
   
   # 或使用环境变量
   DEVICE=kindle7 make
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
   
   # 使用Kindle优化模板
   TEMPLATE=kindle make
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

## 设备预设

工具提供了针对不同设备优化的预设配置，让生成的PDF在各种设备上都有最佳的阅读体验：

### 可用预设

| 预设名称 | 适用设备 | 字体大小 | 代码字体 | 页边距 | 特点 |
|---------|---------|---------|----------|-------|------|
| `desktop` | 桌面电脑 | 10pt | `\small` | 1英寸 | 标准布局，适合大屏幕 |
| `kindle7` | 7英寸Kindle | 11pt | `\small` | 0.4英寸 | 专家推荐，E-ink优化 |
| `tablet` | 平板设备 | 9pt | `\small` | 0.6英寸 | 中等布局，触屏友好 |
| `mobile` | 手机设备 | 7pt | `\tiny` | 0.3英寸 | 超紧凑，小屏优化 |

### 使用方法

1. **通过make快捷命令**：
   ```bash
   make kindle    # 使用Kindle预设
   make tablet    # 使用平板预设
   make mobile    # 使用手机预设
   make desktop   # 使用桌面预设（默认）
   ```

2. **通过环境变量**：
   ```bash
   DEVICE=kindle7 make
   DEVICE=tablet make
   ```

3. **通过配置文件**：
   在 `config.yaml` 中设置：
   ```yaml
   device_preset: "kindle7"  # 或 desktop, tablet, mobile
   ```

### Kindle优化特性

Kindle预设专门针对7英寸E-ink屏幕进行了优化：

- **紧凑布局**：0.4英寸页边距，最大化内容显示区域
- **专家推荐字体**：11pt主字体，`\small`(10pt)代码字体，遵循专业阅读标准
- **高对比度**：使用monochrome语法高亮，适合E-ink显示
- **舒适间距**：标准1.0倍行间距，5pt段落间距，确保阅读舒适度
- **简化结构**：最多2层目录树，减少导航复杂度

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
- 测试覆盖率要求：50%+（当前：55%）
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

# 设备预设配置
device_preset: "desktop"  # 可选：desktop, kindle7, tablet, mobile

# PDF 设置
pdf_settings:
  margin: "margin=1in"           # 页边距
  main_font: "Songti SC"         # 主字体（macOS）/ "Noto Serif CJK SC"（Linux）
  mono_font: "SF Mono"           # 等宽字体（macOS）/ "DejaVu Sans Mono"（Linux）
  fontsize: "10pt"               # 文档字体大小
  code_fontsize: "\\small"       # 代码块字体大小
  linespread: "1.0"              # 行间距倍数
  parskip: "6pt"                 # 段落间距
  highlight_style: "monochrome"  # 代码高亮主题
  split_large_files: true        # 将大文件分割成多个部分而不是截断

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

1. 默认跳过大于 0.5MB 的文件（图片除外）
2. 自动处理长行（超过 80 字符）和大型代码块
3. 大文件（超过 1000 行）会自动分割成多个部分
4. 自动跳过二进制文件
5. SVG 文件会自动转换为 PNG
6. 支持中文文件名和内容
7. 日志输出可通过参数控制详细程度

## 常见问题

1. **PDF 生成失败**
   - 检查是否安装了所有依赖（运行 `make deps`）
   - 确认中文字体是否可用
   - 使用 `make debug` 查看详细日志
   - 查看 debug.md 文件了解详情

2. **中文显示异常**
   - 确认系统安装了配置文件中指定的字体
   - macOS 默认使用 "Songti SC"，Linux 默认使用 "Noto Serif CJK SC"
   - 工具会自动检测系统并选择合适的字体

3. **LaTeX 错误**
   - "Dimension too large" 错误：文件已自动分割处理
   - "puenc-greek.def not found" 错误：需要安装 texlive-lang-greek 包
   - 特殊字符错误：已通过禁用 raw_tex 扩展解决

4. **内存不足**
   - 文件大小限制已优化为 0.5MB
   - 大文件会自动分割而不是截断
   - 使用流式处理避免内存溢出

5. **SVG 转换失败**
   - 确保已安装 Cairo 和 Inkscape
   - 检查 SVG 文件格式是否正确
   - 使用 `make debug` 查看详细的转换日志

6. **设备预设相关问题**
   - 如果PDF在特定设备上显示效果不佳，尝试使用对应的设备预设
   - Kindle用户推荐使用 `make kindle` 获得最佳阅读体验
   - 可以通过修改配置文件中的 `device_presets` 来自定义设备配置
   - 环境变量 `DEVICE` 的优先级高于配置文件中的 `device_preset`

## License

MIT 