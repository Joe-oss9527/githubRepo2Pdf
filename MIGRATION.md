# 📘 迁移指南：从v1到v2架构

## 目录
- [概述](#概述)
- [新架构优势](#新架构优势)
- [已实现的模块](#已实现的模块)
- [安装和设置](#安装和设置)
- [使用示例](#使用示例)
- [测试新模块](#测试新模块)
- [逐步迁移路径](#逐步迁移路径)
- [API参考](#api参考)

---

## 概述

v2.0版本对项目进行了全面重构，从单一的1900+行文件重构为模块化、可测试、高性能的现代Python包。

### 关键变化

| 方面 | v1.0 | v2.0 |
|------|------|------|
| 架构 | 单文件（repo-to-pdf.py） | 模块化包结构 |
| 配置 | 字典 + 手动验证 | Pydantic模型 + 自动验证 |
| 错误处理 | 通用Exception | 类型化异常层次 |
| 类型安全 | 无类型注解 | 100%类型注解 |
| 测试 | 50%覆盖率 | 目标80%+覆盖率 |
| 性能 | 同步I/O | 支持异步 + 并发 |
| 代码质量 | 手动检查 | pre-commit钩子自动化 |

---

## 新架构优势

### 1. 模块化设计

**v1.0问题：**
```python
# 所有代码在一个文件中
class RepoPDFConverter:
    def __init__(self, config_path, template_name=None):
        # 1900+行代码
        # 处理配置、文件、图片、emoji、LaTeX等所有功能
```

**v2.0解决方案：**
```python
# 清晰的职责分离
from repo_to_pdf.core.config import AppConfig
from repo_to_pdf.processors.file_processor import FileProcessor
from repo_to_pdf.git.repo_manager import GitRepoManager
from repo_to_pdf.converters.image_converter import ImageConverter

# 每个类专注单一职责
```

### 2. 强类型配置验证

**v1.0问题：**
```python
# 手动检查，容易出错
if fontsize not in VALID_FONTSIZES:
    raise ValueError(...)
```

**v2.0解决方案：**
```python
from pydantic import BaseModel, Field, field_validator

class PDFSettings(BaseModel):
    fontsize: str = Field(default="10pt")

    @field_validator("fontsize")
    @classmethod
    def validate_fontsize(cls, v: str) -> str:
        if v not in VALID_FONTSIZES:
            raise ValueError(f"Invalid fontsize: {v}")
        return v

# 自动验证，类型安全
config = AppConfig.from_yaml("config.yaml")  # 自动验证所有字段
```

### 3. 安全的文件处理

**v1.0问题：**
```python
# 直接读取，可能路径遍历攻击
with open(file_path, 'r') as f:
    content = f.read()
```

**v2.0解决方案：**
```python
from repo_to_pdf.processors.file_processor import FileProcessor

processor = FileProcessor(config)

# 自动验证路径安全性
if processor.is_safe_path(repo_root, file_path):
    content = processor.read_file_safe(file_path)  # 带大小限制
```

### 4. 更好的错误处理

**v1.0问题：**
```python
except Exception as e:
    logger.error(f"Error: {e}")  # 不知道具体错误类型
```

**v2.0解决方案：**
```python
from repo_to_pdf.core.exceptions import (
    ConfigurationError,
    GitOperationError,
    FileProcessingError
)

try:
    config = AppConfig.from_yaml("config.yaml")
except ConfigurationError as e:
    print(f"配置错误: {e.message}")
    if e.details:
        print(f"详情: {e.details}")
except GitOperationError as e:
    print(f"Git操作失败: {e.message}")
```

---

## 已实现的模块

### ✅ 核心模块 (core/)

#### 1. 异常定义 (core/exceptions.py)
```python
from repo_to_pdf.core.exceptions import (
    RepoPDFError,           # 基础异常
    ConfigurationError,     # 配置错误
    GitOperationError,      # Git操作错误
    FileProcessingError,    # 文件处理错误
    ImageProcessingError,   # 图片处理错误
    ValidationError,        # 验证错误
)
```

#### 2. 常量定义 (core/constants.py)
```python
from repo_to_pdf.core.constants import (
    MAX_FILE_SIZE_MB,       # 最大文件大小
    MAX_LINES_BEFORE_SPLIT, # 分割阈值
    CODE_EXTENSIONS,        # 代码扩展名映射
    DEVICE_PRESETS,         # 设备预设
    # ... 更多常量
)
```

#### 3. 配置管理 (core/config.py)
```python
from repo_to_pdf.core.config import AppConfig

# 从YAML加载并验证
config = AppConfig.from_yaml("config.yaml")

# 访问配置
print(config.repository.url)
print(config.pdf_settings.fontsize)
print(config.workspace_path)  # 自动解析为绝对路径

# 保存配置
config.to_yaml("config_backup.yaml")
```

### ✅ 处理器模块 (processors/)

#### 4. 文件处理器 (processors/file_processor.py)
```python
from repo_to_pdf.processors.file_processor import FileProcessor

processor = FileProcessor(config)

# 收集文件
files = processor.collect_files(repo_path)

# 安全读取文件
content = processor.read_file_safe(file_path)

# 流式读取大文件
for line in processor.read_file_lines(large_file):
    process_line(line)

# 检查文件类型
if processor.is_text_file(file_path):
    content = processor.read_file_safe(file_path)

# 获取文件信息
info = processor.get_file_info(file_path)
print(f"Size: {info['size_mb']:.2f}MB")
```

### ✅ Git模块 (git/)

#### 5. 仓库管理器 (git/repo_manager.py)
```python
from repo_to_pdf.git.repo_manager import GitRepoManager

# 方式1：手动管理
manager = GitRepoManager(
    repo_url="https://github.com/user/repo.git",
    branch="main"
)
repo_path = manager.clone_or_pull(workspace_dir)
# ... 处理文件
manager.cleanup()  # 清理

# 方式2：上下文管理器（推荐）
with GitRepoManager(url, branch, cleanup_on_exit=True) as manager:
    repo_path = manager.clone_or_pull(workspace)
    # ... 处理文件
# 自动清理

# 获取提交信息
info = manager.get_commit_info()
print(f"Commit: {info['short_sha']} by {info['author']}")
```

---

## 安装和设置

### 1. 安装依赖

```bash
# 安装项目（开发模式）
pip install -e ".[dev]"

# 或者只安装运行时依赖
pip install -e .

# 安装pre-commit钩子
pre-commit install
```

### 2. 验证安装

```bash
# 检查CLI
repo-to-pdf --version

# 运行测试
pytest

# 运行代码质量检查
black --check repo_to_pdf/
isort --check repo_to_pdf/
flake8 repo_to_pdf/
mypy repo_to_pdf/
```

---

## 使用示例

### 示例1：配置加载和验证

```python
from repo_to_pdf.core.config import AppConfig
from repo_to_pdf.core.exceptions import ConfigurationError

try:
    # 加载配置（自动验证）
    config = AppConfig.from_yaml("config.yaml")

    # 访问配置
    print(f"Repository: {config.repository.url}")
    print(f"Branch: {config.repository.branch}")
    print(f"Font size: {config.pdf_settings.fontsize}")
    print(f"Device preset: {config.device_preset}")

    # 路径自动解析为绝对路径
    print(f"Workspace: {config.workspace_path}")
    print(f"Output: {config.output_path}")

except ConfigurationError as e:
    print(f"配置错误: {e.message}")
    if e.details:
        print(f"详情: {e.details}")
```

### 示例2：安全的文件处理

```python
from pathlib import Path
from repo_to_pdf.core.config import AppConfig
from repo_to_pdf.processors.file_processor import FileProcessor
from repo_to_pdf.core.exceptions import FileProcessingError, ValidationError

config = AppConfig.from_yaml("config.yaml")
processor = FileProcessor(config)

repo_path = Path("/path/to/repo")

# 收集所有文件
files = processor.collect_files(repo_path)
print(f"Found {len(files)} files")

# 处理每个文件
for file_path in files:
    try:
        # 检查路径安全性
        if not processor.is_safe_path(repo_path, file_path):
            print(f"⚠️  Unsafe path: {file_path}")
            continue

        # 检查是否应该忽略
        if processor.should_ignore(file_path):
            continue

        # 安全读取文件
        content = processor.read_file_safe(file_path)
        print(f"✅ Processed: {file_path.name}")

    except ValidationError as e:
        print(f"⚠️  File too large: {file_path.name}")
    except FileProcessingError as e:
        print(f"❌ Error: {e.message}")
```

### 示例3：Git仓库管理

```python
from pathlib import Path
from repo_to_pdf.git.repo_manager import GitRepoManager
from repo_to_pdf.core.exceptions import GitOperationError

# 使用上下文管理器（推荐）
try:
    with GitRepoManager(
        repo_url="https://github.com/gofiber/fiber.git",
        branch="main",
        cleanup_on_exit=True  # 自动清理
    ) as manager:
        # 克隆或更新
        repo_path = manager.clone_or_pull(Path("./workspace"))
        print(f"Repository cloned to: {repo_path}")

        # 获取提交信息
        info = manager.get_commit_info()
        if info:
            print(f"Latest commit: {info['short_sha']}")
            print(f"Author: {info['author']}")
            print(f"Message: {info['message']}")

        # 处理文件...
        # ...

    # 退出时自动清理

except GitOperationError as e:
    print(f"Git操作失败: {e.message}")
    if e.details:
        print(f"详情: {e.details}")
```

---

## 测试新模块

### 运行已有测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_repo_to_pdf.py -v

# 运行测试并生成覆盖率报告
pytest --cov=repo_to_pdf --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 手动测试新模块

创建一个测试脚本 `test_new_modules.py`:

```python
#!/usr/bin/env python3
"""测试新模块"""

from pathlib import Path
from repo_to_pdf.core.config import AppConfig
from repo_to_pdf.processors.file_processor import FileProcessor
from repo_to_pdf.git.repo_manager import GitRepoManager

def test_config():
    """测试配置加载"""
    print("1️⃣  测试配置加载...")
    config = AppConfig.from_yaml("config.yaml")
    print(f"   ✅ 仓库URL: {config.repository.url}")
    print(f"   ✅ 设备预设: {config.device_preset}")
    print(f"   ✅ 字体大小: {config.pdf_settings.fontsize}")

def test_file_processor():
    """测试文件处理器"""
    print("\n2️⃣  测试文件处理器...")
    config = AppConfig.from_yaml("config.yaml")
    processor = FileProcessor(config)

    # 测试忽略规则
    assert processor.should_ignore(Path("node_modules/test.js"))
    assert not processor.should_ignore(Path("src/main.py"))
    print("   ✅ 忽略规则正常")

    # 测试路径安全性
    base = Path("/home/user/repo")
    safe = Path("/home/user/repo/src/file.py")
    unsafe = Path("/home/user/repo/../../etc/passwd")

    assert processor.is_safe_path(base, safe)
    assert not processor.is_safe_path(base, unsafe)
    print("   ✅ 路径安全验证正常")

def test_git_manager():
    """测试Git管理器"""
    print("\n3️⃣  测试Git管理器...")

    manager = GitRepoManager(
        "https://github.com/octocat/Hello-World.git",
        branch="master"
    )
    print(f"   ✅ Git管理器创建成功")
    print(f"   ℹ️  仓库: Hello-World")

if __name__ == "__main__":
    try:
        test_config()
        test_file_processor()
        test_git_manager()
        print("\n🎉 所有测试通过！")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
```

运行测试：
```bash
python test_new_modules.py
```

---

## 逐步迁移路径

### 阶段1：基础设施（已完成✅）

- [x] 创建模块结构
- [x] 实现核心模块（config, constants, exceptions）
- [x] 实现文件处理器
- [x] 实现Git仓库管理器
- [x] 配置pyproject.toml
- [x] 配置pre-commit钩子

### 阶段2：转换器实现（进行中🚧）

**需要实现的模块：**

1. **图片转换器** (`converters/image_converter.py`)
   - SVG到PNG转换
   - 远程图片下载
   - 图片缓存管理

2. **Emoji处理器** (`converters/emoji_handler.py`)
   - Emoji检测和提取
   - Twemoji下载
   - 批量处理

3. **LaTeX生成器** (`converters/latex_generator.py`)
   - header.tex生成
   - Pandoc配置生成
   - 字体配置

4. **Markdown处理器** (`processors/markdown_processor.py`)
   - Markdown解析
   - 图片路径处理
   - 特殊字符转义

5. **代码处理器** (`processors/code_processor.py`)
   - 语言检测
   - 长行处理
   - 文件分割

### 阶段3：主转换器（待实现📝）

创建 `converter.py` 协调所有组件：

```python
# converter.py (骨架)
from repo_to_pdf.core.config import AppConfig
from repo_to_pdf.processors.file_processor import FileProcessor
from repo_to_pdf.git.repo_manager import GitRepoManager
# ... 其他导入

class RepoPDFConverter:
    """主转换器 - 协调所有组件"""

    def __init__(self, config: AppConfig, template_name: Optional[str] = None):
        self.config = config

        # 初始化所有组件
        self.file_processor = FileProcessor(config)
        self.git_manager = GitRepoManager(
            config.repository.url,
            config.repository.branch
        )
        # ... 初始化其他组件

    def convert(self) -> Path:
        """执行转换"""
        # 1. 克隆仓库
        repo_path = self.git_manager.clone_or_pull(self.config.workspace_path)

        # 2. 收集文件
        files = self.file_processor.collect_files(repo_path)

        # 3. 处理文件
        # ... 使用各个组件处理

        # 4. 生成PDF
        # ...

        return pdf_path
```

### 阶段4：测试和文档（待完成📝）

- [ ] 编写单元测试（目标80%覆盖率）
- [ ] 编写集成测试
- [ ] 性能基准测试
- [ ] API文档（Sphinx）
- [ ] 用户指南

---

## API参考

### 核心模块

#### AppConfig
```python
class AppConfig:
    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> 'AppConfig'
    def to_yaml(self, output_path: Union[str, Path]) -> None

    # 属性
    repository: RepositoryConfig
    workspace_dir: str
    output_dir: str
    pdf_settings: PDFSettings
    ignores: List[str]
    device_preset: str

    # 属性
    @property
    def project_root(self) -> Path
    @property
    def workspace_path(self) -> Path
    @property
    def output_path(self) -> Path
```

#### FileProcessor
```python
class FileProcessor:
    def __init__(self, config: AppConfig)

    def should_ignore(self, path: Path) -> bool
    def is_safe_path(self, base_dir: Path, target_path: Path) -> bool
    def read_file_safe(self, file_path: Path, encoding: str = 'utf-8',
                      max_size: Optional[int] = None) -> str
    def read_file_lines(self, file_path: Path, encoding: str = 'utf-8') -> Iterator[str]
    def collect_files(self, repo_path: Path, include_hidden: bool = False) -> List[Path]
    def is_text_file(self, file_path: Path) -> bool
    def get_file_info(self, file_path: Path) -> dict
```

#### GitRepoManager
```python
class GitRepoManager:
    def __init__(self, repo_url: str, branch: str = 'main',
                 cleanup_on_exit: bool = False)

    def clone_or_pull(self, workspace_dir: Path, depth: int = 1,
                     single_branch: bool = True) -> Path
    def cleanup(self) -> None
    def get_commit_info(self) -> Optional[dict]

    # 上下文管理器支持
    def __enter__(self) -> 'GitRepoManager'
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool
```

---

## 后续步骤

1. **完成剩余模块实现**
   - 图片转换器
   - Emoji处理器
   - Markdown处理器
   - 代码处理器
   - LaTeX生成器

2. **实现主转换器**
   - 协调所有组件
   - 实现转换流程
   - 添加进度报告

3. **提升测试覆盖率**
   - 编写单元测试
   - 编写集成测试
   - 达到80%+覆盖率

4. **性能优化**
   - 实现异步I/O
   - 添加并发处理
   - 优化内存使用

5. **文档完善**
   - API文档
   - 用户指南
   - 开发者指南

---

## 获取帮助

- **GitHub Issues**: 报告bug或请求功能
- **文档**: 查看README.md和CLAUDE.md
- **测试**: 运行测试suite学习API用法

---

**祝使用愉快！** 🚀
