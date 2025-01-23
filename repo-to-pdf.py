#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import yaml
import shutil
import tempfile
import logging
import git
from datetime import datetime
import markdown
from bs4 import BeautifulSoup
import hashlib
import re

# 设置 Cairo 库路径
os.environ['DYLD_LIBRARY_PATH'] = '/opt/homebrew/lib:' + os.environ.get('DYLD_LIBRARY_PATH', '')

# 获取主日志记录器
logger = logging.getLogger(__name__)

# 设置 git 模块的日志级别为 WARNING，抑制调试信息
logging.getLogger('git').setLevel(logging.WARNING)
logging.getLogger('git.cmd').setLevel(logging.WARNING)
logging.getLogger('git.util').setLevel(logging.WARNING)

class GitRepoManager:
    def __init__(self, repo_url: str, branch: str = 'main'):
        self.repo_url = repo_url
        self.branch = branch
        self.repo_dir = None
        
        # 设置 Git 环境变量，避免不必要的检查
        if os.uname().sysname == 'Darwin':  # macOS
            os.environ['GIT_PYTHON_GIT_EXECUTABLE'] = '/usr/bin/git'
            os.environ['GIT_PYTHON_REFRESH'] = 'quiet'
        
    def clone_or_pull(self, workspace_dir: Path) -> Path:
        """克隆或更新仓库"""
        repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        self.repo_dir = workspace_dir / repo_name
        
        try:
            if self.repo_dir.exists():
                logger.info(f"Repository exists, pulling latest changes from {self.branch}")
                repo = git.Repo(self.repo_dir)
                # 确保远程分支存在
                if not repo.remotes:
                    repo.create_remote('origin', self.repo_url)
                origin = repo.remotes.origin
                # 获取最新的远程分支信息
                origin.fetch()
                # 重置到远程分支的最新状态
                repo.git.reset('--hard', f'origin/{self.branch}')
            else:
                logger.info(f"Cloning repository from {self.repo_url}")
                # 使用官方推荐的克隆参数
                git.Repo.clone_from(
                    url=self.repo_url,
                    to_path=self.repo_dir,
                    branch=self.branch,
                    depth=1,  # 浅克隆
                    single_branch=True,  # 单分支
                    filter='blob:none'  # 不下载大文件，只获取文件树
                )
                
            return self.repo_dir
            
        except git.GitCommandError as e:
            logger.error(f"Git operation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during git operation: {str(e)}")
            raise

class RepoPDFConverter:
    def __init__(self, config_path: Path):
        self.project_root = config_path.parent.absolute()
        self.config = self._load_config(config_path)
        self.temp_dir = None
        
        # 确保所有路径都相对于项目根目录
        self.workspace_dir = self.project_root / self.config['workspace_dir']
        self.output_dir = self.project_root / self.config['output_dir']
        
        # 创建必要的目录
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 支持的图片格式
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.svgz'}
        
        # 支持的代码文件扩展名和对应的语言
        self.code_extensions = {
            # 前端相关
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.vue': 'javascript',
            '.svelte': 'javascript',
            '.css': 'css',
            '.scss': 'css',
            '.sass': 'css',
            '.less': 'css',
            '.html': 'html',
            '.json': 'javascript',
            '.graphql': 'graphql',
            '.gql': 'graphql',
            
            # 后端相关
            '.py': 'python',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            
            # 配置和脚本
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.xml': 'xml',
            '.md': 'markdown',
            '.mdx': 'mdx'  # 添加 MDX 支持
        }
        
        # 语言缩进配置（基于各语言的最佳实践）
        self.language_indents = {
            'python': 4,      # PEP 8
            'go': 8,         # Go 标准
            'javascript': 2,  # JavaScript 常用
            'typescript': 2,  # TypeScript 常用
            'java': 4,       # Java 常用
            'c': 4,          # C 常用
            'cpp': 4,        # C++ 常用
            'rust': 4,       # Rust 常用
            'ruby': 2,       # Ruby 常用
            'php': 4,        # PSR-2
            'html': 2,       # HTML 常用
            'css': 2,        # CSS 常用
            'yaml': 2,       # YAML 常用
            'markdown': 4,   # Markdown 常用
            'bash': 2,       # Shell 常用
            'sql': 2,        # SQL 常用
            'csharp': 4,     # C# 常用
            'vue': 2,        # Vue 常用
            'svelte': 2,     # Svelte 常用
            'graphql': 2,    # GraphQL 常用
            'toml': 2,       # TOML 常用
            'xml': 2,        # XML 常用
            'mdx': 2,        # MDX 常用
        }
        
        # 初始化 Markdown 转换器
        self.md = markdown.Markdown(extensions=['fenced_code', 'tables'])
        
    def _load_config(self, config_path: Path) -> dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
            
    def create_temp_markdown(self):
        """创建临时目录并准备 Markdown 文件"""
        # 在项目根目录下创建 temp 目录
        self.temp_dir = self.project_root / 'temp'
        # 如果目录已存在，先清空它
        if self.temp_dir.exists():
            import shutil
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created temporary directory: {self.temp_dir}")
        return self.temp_dir / "output.md"

    def convert_svg_to_png(self, svg_content: str, output_path: Path) -> bool:
        """将 SVG 内容转换为 PNG 文件"""
        try:
            import cairosvg
            from xml.etree import ElementTree as ET
            from io import BytesIO
            
            # 移除 XML 声明
            svg_content = svg_content.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            svg_content = svg_content.replace('<?xml version="1.0"?>', '')
            
            logger.debug(f"处理 SVG 内容: {svg_content[:200]}...")  # 打印前200个字符用于调试
            
            # 检查是否是图标定义文件
            if '<symbol' in svg_content or '<defs>' in svg_content:
                logger.debug("跳过图标定义 SVG 文件")
                return False
            
            # 解析 SVG 内容
            tree = ET.fromstring(svg_content)
            
            # 获取或设置 SVG 尺寸
            width = tree.get('width', '').strip()
            height = tree.get('height', '').strip()
            viewBox = tree.get('viewBox', '').strip()
            
            logger.debug(f"原始尺寸 - 宽度: {width}, 高度: {height}, viewBox: {viewBox}")
            
            # 检查尺寸是否为 0
            try:
                if width and float(width.replace('px', '').strip()) == 0:
                    logger.debug("跳过宽度为 0 的 SVG")
                    return False
                if height and float(height.replace('px', '').strip()) == 0:
                    logger.debug("跳过高度为 0 的 SVG")
                    return False
            except ValueError:
                pass  # 忽略无法转换为数字的值
            
            # 如果有 viewBox 但没有宽高，从 viewBox 提取
            if viewBox and not (width and height):
                try:
                    vb_parts = viewBox.split()
                    if len(vb_parts) == 4:
                        _, _, vb_width, vb_height = vb_parts
                        # 检查 viewBox 尺寸是否为 0
                        if float(vb_width) == 0 or float(vb_height) == 0:
                            logger.debug("跳过 viewBox 尺寸为 0 的 SVG")
                            return False
                        tree.set('width', vb_width + 'px')
                        tree.set('height', vb_height + 'px')
                        logger.debug(f"从 viewBox 提取尺寸 - 宽度: {vb_width}px, 高度: {vb_height}px")
                except Exception as e:
                    logger.debug(f"从 viewBox 提取尺寸失败: {e}")
            
            # 如果仍然没有尺寸信息，添加默认尺寸
            width = tree.get('width', '').strip()
            height = tree.get('height', '').strip()
            if not (width and height):
                # 设置默认尺寸为 800x600
                tree.set('width', '800px')
                tree.set('height', '600px')
                logger.debug("使用默认尺寸 800x600px")
            
            # 确保单位
            for dim in ['width', 'height']:
                value = tree.get(dim, '')
                if value and not any(unit in value.lower() for unit in ['px', 'pt', 'cm', 'mm', 'in']):
                    tree.set(dim, value + 'px')
                    logger.debug(f"添加像素单位到 {dim}: {value}px")
            
            # 重新生成 SVG 内容
            svg_content = ET.tostring(tree, encoding='unicode')
            logger.debug(f"最终 SVG 尺寸 - 宽度: {tree.get('width')}, 高度: {tree.get('height')}")
            
            # 转换为 PNG，设置合适的输出尺寸
            cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                write_to=str(output_path),
                parent_width=1600,  # 设置父容器宽度
                parent_height=1200,  # 设置父容器高度
                scale=2.0  # 设置缩放比例以提高清晰度
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to convert SVG to PNG using cairosvg: {e}")
            try:
                # 尝试使用 Inkscape 作为备选方案
                inkscape_cmd = ['inkscape', 
                              '--export-type=png',
                              '--export-filename=' + str(output_path),
                              '--export-width=1600']
                
                # 将 SVG 内容写入临时文件
                temp_svg = output_path.parent / f"temp_{output_path.stem}.svg"
                with open(temp_svg, 'w', encoding='utf-8') as f:
                    f.write(svg_content)
                
                # 运行 Inkscape 命令
                result = subprocess.run([*inkscape_cmd, str(temp_svg)], 
                                     capture_output=True, 
                                     text=True)
                
                # 删除临时文件
                temp_svg.unlink()
                
                if result.returncode == 0 and output_path.exists():
                    return True
                    
                logger.warning(f"Inkscape conversion failed: {result.stderr}")
            except Exception as e2:
                logger.warning(f"Backup SVG conversion also failed: {e2}")
            return False

    def _convert_image_to_png(self, path: str) -> str:
        """转换图片为 PNG 格式"""
        try:
            # 创建 images 目录
            images_dir = self.temp_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # 处理相对路径和绝对路径
            img_path = Path(path)
            if not img_path.is_absolute():
                img_path = self.project_root / path
                
            if not img_path.exists():
                return path  # 如果文件不存在，返回原路径
                
            if path.lower().endswith('.svg'):
                # SVG 转 PNG 的处理
                with open(img_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                hash_name = hashlib.md5(svg_content.encode()).hexdigest()
                png_path = images_dir / f"{hash_name}.png"
                
                if png_path.exists():
                    return f"images/{png_path.name}"
                    
                if self.convert_svg_to_png(svg_content, png_path):
                    return f"images/{png_path.name}"
                    
            return path
        except Exception as e:
            logger.warning(f"Failed to convert image {path}: {e}")
            return path

    def _is_valid_svg(self, content: str) -> bool:
        """检查是否是有效的 SVG 内容"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            svg = soup.find('svg')
            return svg is not None and (svg.get('width') or svg.get('height') or svg.get('viewBox'))
        except:
            return False

    def _convert_svg_content_to_png(self, svg_content: str) -> str:
        """将 SVG 内容转换为 PNG"""
        try:
            images_dir = self.temp_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            hash_name = hashlib.md5(svg_content.encode()).hexdigest()
            png_path = images_dir / f"{hash_name}.png"
            
            if png_path.exists():
                return png_path.name
                
            if self.convert_svg_to_png(svg_content, png_path):
                return png_path.name
                
            return ""
        except Exception as e:
            logger.warning(f"Failed to convert SVG content to PNG: {e}")
            return ""

    def process_markdown(self, content: str) -> str:
        """处理 Markdown 内容，处理图片和 SVG"""
        # 1. 处理代码块的 title 属性
        content = re.sub(r'```(\w+)\s+title="([^"]+)"', r'```\1', content)
        
        # 2. 处理 Markdown 图片语法
        def process_md_image(match):
            alt = match.group(1) or ''  # 可能为空
            path = match.group(2)
            title = match.group(3) or '' if len(match.groups()) > 2 else ''
            
            if path.lower().endswith('.svg'):
                new_path = self._convert_image_to_png(path)
                if title:
                    return f'![{alt}]({new_path} "{title}")'
                return f'![{alt}]({new_path})'
            return match.group(0)  # 保持原样
        
        # 处理带 title 的图片
        content = re.sub(r'!\[(.*?)\]\((.*?)\s+"(.*?)"\)', process_md_image, content)
        # 处理不带 title 的图片
        content = re.sub(r'!\[(.*?)\]\((.*?)\)', process_md_image, content)
        
        # 3. 处理 HTML 图片标签
        def process_html_image(match):
            tag = match.group(0)
            soup = BeautifulSoup(tag, 'html.parser')
            img = soup.find('img')
            if not img:
                return tag
                
            src = img.get('src', '')
            if src.lower().endswith('.svg'):
                new_src = self._convert_image_to_png(src)
                img['src'] = new_src
                return str(img)
            return tag
        
        # 匹配 HTML img 标签，考虑单引号和双引号
        content = re.sub(r'<img\s+[^>]+>', process_html_image, content, flags=re.IGNORECASE)
        
        # 4. 处理内嵌 SVG
        def process_svg(match):
            svg_content = match.group(0)
            if self._is_valid_svg(svg_content):
                png_path = self._convert_svg_content_to_png(svg_content)
                if png_path:
                    return f'![](images/{png_path})'
            return match.group(0)
        
        # 匹配内嵌的 SVG 标签
        content = re.sub(r'<svg\s*.*?>.*?</svg>', process_svg, content, flags=re.DOTALL | re.IGNORECASE)
        
        return content

    def _clean_text(self, text: str) -> str:
        """清理文本内容，只处理特殊字符，保持原始格式"""
        import re
        
        # 处理引号内的 \t，将其转义为 LaTeX 可识别的形式
        def escape_tab_in_quotes(match):
            content = match.group(1)
            return '"' + content.replace('\\t', '\\textbackslash{}t') + '"'
            
        text = re.sub(r'"([^"]*)"', escape_tab_in_quotes, text)
        
        return text

    def process_file(self, file_path: Path, repo_root: Path) -> str:
        """处理单个文件，返回对应的 Markdown 内容"""
        import re
        
        ext = file_path.suffix.lower()
        rel_path = file_path.relative_to(repo_root)
        
        # 检查是否在忽略列表中
        if any(ignore in str(rel_path) for ignore in self.config.get('ignores', [])):
            return ""
            
        # 创建临时目录下的 images 目录
        images_dir = self.temp_dir / "images"
        images_dir.mkdir(exist_ok=True)
            
        # 处理图片文件
        if ext.lower() in self.image_extensions:
            try:
                if ext.lower() in {'.svg', '.svgz'}:
                    # 处理 SVG 文件
                    png_name = self.process_svg_file(file_path, images_dir)
                    if not png_name:
                        return ""
                else:
                    # 处理其他图片文件
                    target_path = images_dir / file_path.name
                    shutil.copy2(file_path, target_path)
            except Exception as e:
                logger.warning(f"Failed to process image {file_path}: {e}")
            return ""
            
        try:
            # 获取文件大小（MB）
            file_size = file_path.stat().st_size / (1024 * 1024)
            # 如果文件大于 1MB，跳过
            if file_size > 1 and ext not in self.image_extensions:
                logger.debug(f"跳过大文件 ({file_size:.1f}MB): {file_path}")
                return ""
            
            # 读取文件内容并清理
            with open(file_path, 'r', encoding='utf-8') as f:
                content = self._clean_text(f.read().strip())
            
            # 如果是 Markdown 或 MDX 文件，处理图片路径
            if ext in {'.md', '.mdx'}:
                # 处理图片路径
                def process_image_path(match):
                    img_path = match.group(2)
                    if not img_path.startswith(('http://', 'https://', '/')):
                        # 尝试多种路径解析方式
                        possible_paths = [
                            # 1. 从当前文件目录解析
                            file_path.parent / img_path,
                            # 2. 从仓库根目录解析
                            repo_root / img_path,
                            # 3. 处理 ../类型的相对路径
                            (file_path.parent / img_path).resolve(),
                            # 4. 处理 ./类型的相对路径
                            (file_path.parent / img_path.lstrip('./')).resolve(),
                            # 5. 如果路径以 docs/ 开头，尝试从仓库根目录解析
                            repo_root / img_path.lstrip('./')
                        ]
                        
                        # 尝试所有可能的路径
                        for abs_img_path in possible_paths:
                            try:
                                if abs_img_path.exists() and abs_img_path.suffix.lower() in self.image_extensions:
                                    # 复制图片到临时目录
                                    target_path = images_dir / abs_img_path.name
                                    shutil.copy2(abs_img_path, target_path)
                                    logger.debug(f"成功处理图片: {abs_img_path} -> {target_path}")
                                    return f"![{match.group(1)}](images/{target_path.name})"
                            except Exception as e:
                                logger.debug(f"尝试路径 {abs_img_path} 失败: {e}")
                                continue
                        
                        logger.warning(f"无法找到图片: {img_path}, 在文件: {file_path}")
                    return match.group(0)
                
                # 处理 Markdown 中的图片引用
                content = re.sub(r'!\[(.*?)\]\((.*?)\)', process_image_path, content)
                cleaned_content = self.process_markdown(content)
                
                # 如果是 MDX 文件，使用 MDX 语法高亮
                if ext == '.mdx':
                    return f"\n\n# {rel_path}\n\n`````mdx\n{cleaned_content}\n`````\n\n"
                return f"\n\n# {rel_path}\n\n{cleaned_content}\n\n"
            
            # 如果是支持的代码文件（排除已处理的 MDX）
            if ext in self.code_extensions and ext != '.mdx':
                # 跳过包含 SVG 的文件
                if '<svg' in content:
                    return ""
                    
                # 对于 package.json 和 package-lock.json 文件不使用高亮
                if file_path.name in ['package.json', 'package-lock.json', 'yarn.lock']:
                    return f"\n\n# {rel_path}\n\n`````\n{content}\n`````\n\n"
                    
                # 对于其他文件使用语言高亮
                lang = self.code_extensions[ext]
                # 处理长字符串，将它们分割成多行
                content = self._process_long_lines(content)
                return f"\n\n# {rel_path}\n\n`````{lang}\n{content}\n`````\n\n"
                
            return ""
        except UnicodeDecodeError:
            logger.debug(f"跳过二进制文件: {file_path}")
            return ""
            
    def _process_long_lines(self, content: str, max_length: int = 100) -> str:
        """处理长行，将它们分割成多行"""
        lines = []
        for line in content.splitlines():
            if len(line) > max_length:
                # 检查是否是数组
                if '[' in line and ']' in line:
                    # 在逗号后添加换行
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    parts = line.split(',')
                    formatted_parts = []
                    current_line = parts[0]
                    
                    for part in parts[1:]:
                        if len(current_line + ',' + part) > max_length:
                            formatted_parts.append(current_line + ',')
                            current_line = indent + part.lstrip()
                        else:
                            current_line += ',' + part
                            
                    formatted_parts.append(current_line)
                    line = '\n'.join(formatted_parts)
                # 对于包含长字符串的行进行特殊处理
                elif '"' in line or "'" in line:
                    line = self._break_long_strings(line)
            lines.append(line)
        return '\n'.join(lines)
        
    def _break_long_strings(self, line: str) -> str:
        """处理包含长字符串的行"""
        import re
        # 查找长字符串（包括包名和版本号）
        pattern = r'["\']([^"\']{100,})["\']'
        
        def replacer(match):
            # 将长字符串每隔 80 个字符添加换行和适当的缩进
            s = match.group(1)
            indent = ' ' * (len(line) - len(line.lstrip()))
            parts = [s[i:i+80] for i in range(0, len(s), 80)]
            if len(parts) > 1:
                quote = match.group(0)[0]  # 获取原始引号
                return f'{quote}\\\n{indent}'.join(parts) + quote
            return match.group(0)
            
        return re.sub(pattern, replacer, line)

    def create_language_definitions(self) -> list:
        """创建所有支持的语言定义"""
        definitions = []
        
        # TypeScript 定义
        definitions.extend([
            '\\lstdefinelanguage{typescript}[]{javascript}{%',
            '  morekeywords={interface,type,implements,namespace,declare,abstract,',
            '                as,is,keyof,in,extends,readonly,instanceof,unique,',
            '                infer,await,async,module,namespace,declare,export,import},',
            f'  tabsize={self.language_indents["typescript"]},',
            '}',
        ])
        
        # Go 语言定义
        definitions.extend([
            '\\lstdefinelanguage{go}{',
            '  morekeywords={package,import,func,return,var,const,type,struct,interface,',
            '                if,else,for,range,break,continue,switch,case,default,',
            '                go,chan,select,defer,fallthrough,goto,map,make,new},',
            '  sensitive=true,',
            '  morecomment=[l]{//},',
            '  morecomment=[s]{/*}{*/},',
            '  morestring=[b]",',
            '  morestring=[b]`,',
            '  morestring=[b]\',',
            '  keywordstyle=\\color{blue},',
            '  commentstyle=\\color{darkgreen},',
            '  stringstyle=\\color{red},',
            '  basicstyle=\\ttfamily\\small\\keepspaces,',
            f'  tabsize={self.language_indents["go"]},',
            '}',
        ])
        
        # Python 定义
        definitions.extend([
            '\\lstdefinelanguage{python}{',
            '  morekeywords={def,class,from,import,return,yield,raise,try,except,finally,',
            '                if,elif,else,for,while,break,continue,pass,assert,with,as,',
            '                lambda,global,nonlocal,True,False,None,and,or,not,is,in},',
            '  sensitive=true,',
            '  morecomment=[l]\\#,',
            '  morestring=[b]",',
            '  morestring=[b]\',',
            '  morestring=[s]{"""}{"""},',
            '  morestring=[s]{\'\'\'}{\'\'\'}, ',
            '  keywordstyle=\\color{blue},',
            '  commentstyle=\\color{darkgreen},',
            '  stringstyle=\\color{red},',
            '  basicstyle=\\ttfamily\\small\\keepspaces,',
            f'  tabsize={self.language_indents["python"]},',
            '}',
        ])
        
        # JavaScript 定义
        definitions.extend([
            '\\lstdefinelanguage{javascript}{',
            '  morekeywords={const,let,var,function,class,extends,implements,import,export,',
            '                return,if,else,for,while,do,switch,case,break,continue,try,',
            '                catch,finally,throw,async,await,new,this,super,static},',
            '  sensitive=true,',
            '  morecomment=[l]{//},',
            '  morecomment=[s]{/*}{*/},',
            '  morestring=[b]",',
            '  morestring=[b]\',',
            '  morestring=[b]`,',
            '  keywordstyle=\\color{blue},',
            '  commentstyle=\\color{darkgreen},',
            '  stringstyle=\\color{red},',
            '  basicstyle=\\ttfamily\\small\\keepspaces,',
            f'  tabsize={self.language_indents["javascript"]},',
            '}',
        ])
        
        # Vue 定义
        definitions.extend([
            '\\lstdefinelanguage{vue}{',
            '  basicstyle=\\ttfamily,',
            '  keywords={template,script,style,export,default,props,data,methods,computed,watch,',
            '            components,mounted,created,updated,destroyed,beforeCreate,beforeMount,',
            '            beforeUpdate,beforeDestroy},',
            '  keywordstyle=\\color{blue},',
            '  sensitive=true,',
            '  comment=[l]{//},',
            '  morecomment=[s]{/*}{*/},',
            '  commentstyle=\\color{darkgreen},',
            '  stringstyle=\\color{red},',
            '  morestring=[b]",',
            '  morestring=[b]\',',
            f'  tabsize={self.language_indents["vue"]},',
            '}',
        ])
        
        # MDX 定义
        definitions.extend([
            '\\lstdefinelanguage{mdx}{',
            '  basicstyle=\\ttfamily,',
            '  keywords={import,export,default,function,return,props,const,let,var,if,else,',
            '            switch,case,break,continue,for,while,do,try,catch,finally,throw,',
            '            class,extends,new,delete,typeof,instanceof,void,this,super,with,',
            '            yield,async,await,static,get,set,of,from,as},',
            '  keywordstyle=\\color{blue},',
            '  sensitive=true,',
            '  comment=[l]{//},',
            '  morecomment=[s]{/*}{*/},',
            '  commentstyle=\\color{darkgreen},',
            '  stringstyle=\\color{red},',
            '  morestring=[b]",',
            '  morestring=[b]\',',
            '  alsoletter={<>,/},',  # 让 JSX 标签被识别为单个token
            '  morekeywords=[2]{<,</,/>,>},', # JSX 标签作为第二组关键字
            '  keywordstyle=[2]\\color{purple},',
            f'  tabsize={self.language_indents["mdx"]},',
            '}',
        ])
        
        # 添加标题和段落设置
        definitions.extend([
            '\\setlength{\\headheight}{15pt}',
        ])
        
        return definitions

    def create_pandoc_yaml(self, repo_name: str) -> Path:
        """创建 Pandoc 的 YAML 配置文件"""
        pdf_config = self.config.get('pdf_settings', {})
        
        yaml_config = {
            'pdf-engine': 'xelatex',
            'highlight-style': pdf_config.get('highlight_style', 'tango'),
            'from': 'markdown+fenced_code_attributes+fenced_code_blocks+backtick_code_blocks',  # 移除 highlighting
            'variables': {
                'documentclass': 'article',
                'geometry': pdf_config.get('margin', 'margin=1in'),
                # 中文正文字体
                'CJKmainfont': 'Songti SC',
                'CJKsansfont': 'PingFang SC',
                'CJKmonofont': 'STFangsong',
                # 等宽字体（代码）
                'monofont': pdf_config.get('mono_font', 'SF Mono'),
                'monofontoptions': [
                    'Scale=0.85',
                    'BoldFont=SF Mono Bold',
                    'ItalicFont=SF Mono Regular Italic',
                    'BoldItalicFont=SF Mono Bold Italic'
                ],
                'colorlinks': True,
                'linkcolor': 'blue',
                'urlcolor': 'blue',
                'header-includes': [
                    # 加载必要的包
                    '\\usepackage{fontspec}',    # XeTeX 的字体支持
                    '\\usepackage{xunicode}',    # Unicode 支持
                    '\\usepackage{xeCJK}',       # 中文支持
                    '\\usepackage{fvextra}',     # 代码块支持
                    '\\usepackage[most]{tcolorbox}',
                    '\\usepackage{listings}',
                    '\\usepackage{graphicx}',
                    '\\usepackage{float}',
                    '\\usepackage{sectsty}',   # 节标题格式支持
                    '\\usepackage{hyperref}',  # hyperref 应该最后加载
                    '\\usepackage{longtable}', # 基本表格支持
                    '\\usepackage{ragged2e}',  # 段落对齐支持
                    # 段落对齐设置
                    '\\AtBeginDocument{\\justifying}',
                    # PDF 元数据设置
                    '\\hypersetup{',
                    f'    pdftitle={{{repo_name} 代码文档}},',
                    f'    pdfauthor={{{pdf_config.get("metadata", {}).get("author", "Repo-to-PDF Generator")}}},',
                    f'    pdfcreator={{{pdf_config.get("metadata", {}).get("creator", "LaTeX")}}},',
                    f'    pdfproducer={{{pdf_config.get("metadata", {}).get("producer", "XeLaTeX")}}},',
                    '    colorlinks=true,',
                    '    linkcolor=blue,',
                    '    urlcolor=blue',
                    '}',
                    # 字体设置
                    '\\defaultfontfeatures{Mapping=tex-text}',  # 启用 TeX 连字
                    # 中文字体设置
                    '\\setCJKmainfont[BoldFont={Songti SC Bold},ItalicFont={Songti SC Light}]{Songti SC}',
                    '\\setCJKsansfont[BoldFont={PingFang SC Semibold},ItalicFont={PingFang SC Light}]{PingFang SC}',
                    '\\setCJKmonofont{STFangsong}',
                    # 中文断行设置
                    '\\XeTeXlinebreaklocale "zh"',
                    '\\XeTeXlinebreakskip = 0pt plus 1pt',
                    # 标题格式设置
                    '\\allsectionsfont{\\CJKfamily{sf}}',  # 使用 sectsty 包的命令设置所有标题字体
                    # 图片设置
                    '\\DeclareGraphicsExtensions{.png,.jpg,.jpeg,.gif}',
                    '\\graphicspath{{./images/}}',
                    # 图片处理设置
                    '\\usepackage{adjustbox}',
                    '\\setkeys{Gin}{width=0.8\\linewidth,keepaspectratio}',
                    # 代码块设置
                    '\\DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,commandchars=\\\\\\{\\}}',
                    '\\fvset{breaklines=true, breakanywhere=true, breakafter=\\\\}',
                    # 代码框设置
                    '\\renewenvironment{Shaded}{\\begin{tcolorbox}[breakable,boxrule=0pt,frame hidden,sharp corners]}{\\end{tcolorbox}}',
                    # 设置 listings 包的全局选项
                    '\\lstset{%',
                    '  basicstyle=\\ttfamily\\small,',
                    '  backgroundcolor=\\color{white},',
                    '  commentstyle=\\color{green!60!black},',
                    '  keywordstyle=\\color{blue!70!black},',
                    '  stringstyle=\\color{red!70!black},',
                    '  numberstyle=\\tiny\\color{gray},',
                    '  breaklines=true,',
                    '  breakatwhitespace=true,',
                    '  keepspaces=true,',
                    '  showspaces=false,',
                    '  showstringspaces=false,',
                    '  showtabs=false,',
                    '  frame=none,',
                    '  xleftmargin=0pt,',
                    '  numbers=none,',
                    '  inputencoding=utf8,',
                    '  extendedchars=true,',
                    '  columns=flexible,',
                    '  basewidth={0.5em,0.45em},',
                    '  keepspaces=true,',
                    '}',
                    *self.create_language_definitions(),  # 添加所有语言定义
                ]
            }
        }
        
        yaml_path = Path(self.temp_dir) / "pandoc.yaml"
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_config, f, allow_unicode=True)
        
        return yaml_path

    def convert(self):
        """转换仓库内容为 PDF"""
        try:
            # 不需要创建工作目录，因为在初始化时已经创建
            
            # 克隆或更新仓库
            repo_manager = GitRepoManager(
                self.config['repository']['url'],
                self.config['repository'].get('branch', 'main')
            )
            repo_path = repo_manager.clone_or_pull(self.workspace_dir)
            
            # 创建临时文件
            temp_md = self.create_temp_markdown()
            yaml_path = self.create_pandoc_yaml(repo_path.name)
            
            # 生成输出路径（已经是相对于项目根目录）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_pdf = self.output_dir / f"{repo_path.name}_{timestamp}.pdf"
            
            # 收集并处理所有文件
            with open(temp_md, 'w', encoding='utf-8') as out_file:
                # 写入标题
                out_file.write(f"---\ntitle: {repo_path.name} 代码文档\ndate: \\today\n---\n\n")
                
                # 处理所有文件
                for file_path in sorted(repo_path.rglob('*')):
                    if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                        content = self.process_file(file_path, repo_path)
                        if content:
                            out_file.write(content)
            
            # 调用 pandoc 进行转换，添加更多选项
            cmd = [
                'pandoc',
                '-f', 'markdown+pipe_tables+grid_tables+table_captions+yaml_metadata_block+smart+fenced_code_blocks+fenced_code_attributes+backtick_code_blocks+inline_code_attributes+line_blocks+fancy_lists+definition_lists+example_lists+task_lists+citations+footnotes+smart+superscript+subscript+raw_html+tex_math_dollars+tex_math_single_backslash+tex_math_double_backslash+raw_tex+implicit_figures+link_attributes+bracketed_spans+native_divs+native_spans+raw_attribute+header_attributes+auto_identifiers+pandoc_title_block+mmd_title_block+autolink_bare_uris+emoji+hard_line_breaks+escaped_line_breaks+blank_before_blockquote+blank_before_header+space_in_atx_header+strikeout+east_asian_line_breaks',  # 添加所有有用的扩展特性
                '--pdf-engine=xelatex',
                '--wrap=none',
                '--toc',
                '--toc-depth=2',
                '--defaults', str(yaml_path),
                '--highlight-style=tango',  # 显式指定代码高亮样式
                '-V', 'geometry:margin=0.5in',
                '-V', 'fontsize=10pt',
                '--resource-path=' + str(self.temp_dir),
                '--standalone',
                # 输出设置
                '-o', str(output_pdf),
                str(temp_md)
            ]
            
            # 设置环境变量来增加 TeX 内存
            env = os.environ.copy()
            env['max_print_line'] = '1000'
            env['error_line'] = '254'
            env['half_error_line'] = '238'
            
            logger.info("Converting to PDF...")
            logger.info(f"Running command: {' '.join(cmd)}")  # 打印完整命令便于调试
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if result.returncode != 0:
                logger.error(f"Pandoc stderr: {result.stderr}")
                logger.error(f"Pandoc stdout: {result.stdout}")
                raise Exception(f"Pandoc conversion failed: {result.stderr}")
                
            logger.info(f"Successfully created PDF: {output_pdf}")
            
        except Exception as e:
            logger.error(f"转换失败: {str(e)}")
            # 保存生成的 markdown 文件以便调试
            debug_md = self.project_root / "debug.md"
            if temp_md.exists():
                import shutil
                shutil.copy2(temp_md, debug_md)
                logger.info(f"已保存调试用 Markdown 文件: {debug_md}")
            raise
            
        finally:
            # 不再删除临时目录，因为它在项目目录下可能还有用
            if self.temp_dir and self.temp_dir.exists():
                logger.info(f"临时文件保存在: {self.temp_dir}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert GitHub repository to PDF with syntax highlighting')
    parser.add_argument('-c', '--config', type=Path, required=True,
                      help='Path to configuration YAML file')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='Enable verbose output (DEBUG level)')
    parser.add_argument('-q', '--quiet', action='store_true',
                      help='Only show warnings and errors')
    
    args = parser.parse_args()
    
    # 配置日志级别
    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    
    # 配置日志
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # 设置 git 模块的日志级别
    git_level = logging.WARNING if not args.verbose else log_level
    logging.getLogger('git').setLevel(git_level)
    logging.getLogger('git.cmd').setLevel(git_level)
    logging.getLogger('git.util').setLevel(git_level)
    
    # 设置其他模块的日志级别
    logging.getLogger('MARKDOWN').setLevel(git_level)
    
    converter = RepoPDFConverter(args.config)
    converter.convert()

if __name__ == '__main__':
    main()