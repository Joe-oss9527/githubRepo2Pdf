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
from html2text import HTML2Text

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
                origin = repo.remotes.origin
                origin.pull(self.branch)
            else:
                logger.info(f"Cloning repository from {self.repo_url}")
                git.Repo.clone_from(self.repo_url, self.repo_dir, branch=self.branch)
                
            return self.repo_dir
            
        except git.GitCommandError as e:
            logger.error(f"Git operation failed: {str(e)}")
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
            import re
            
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

            # 处理相对单位
            def convert_to_pixels(value, default=None):
                if not value:
                    return default
                # 处理相对单位
                units = {
                    'em': 16,     # 1em = 16px
                    'rem': 16,    # 1rem = 16px
                    'pt': 1.333,  # 1pt = 1.333px
                    'pc': 16,     # 1pc = 16px
                    'mm': 3.779,  # 1mm = 3.779px
                    'cm': 37.79,  # 1cm = 37.79px
                    'in': 96,     # 1in = 96px
                    '%': 1        # 百分比保持不变
                }
                
                # 匹配数字和单位
                match = re.match(r'^([\d.]+)([a-z%]*)$', value.lower())
                if match:
                    num, unit = match.groups()
                    num = float(num)
                    if unit in units:
                        return str(round(num * units[unit])) + 'px'
                    elif unit == 'px' or not unit:
                        return str(round(num)) + 'px'
                return default

            # 转换宽度和高度
            width = convert_to_pixels(width, '800px')
            height = convert_to_pixels(height, '600px')
            
            # 设置转换后的尺寸
            tree.set('width', width)
            tree.set('height', height)
            
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
            
            # 处理内部元素的相对单位
            for elem in tree.iter():
                for attr in ['width', 'height', 'x', 'y', 'dx', 'dy', 'font-size']:
                    value = elem.get(attr)
                    if value:
                        elem.set(attr, convert_to_pixels(value, value))
            
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

    def process_svg_file(self, svg_path: Path, images_dir: Path) -> str:
        """处理 SVG 文件，转换为 PNG"""
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            
            # 生成唯一的文件名
            hash_name = hashlib.md5(svg_content.encode()).hexdigest()
            png_path = images_dir / f"{hash_name}.png"
            
            # 如果 PNG 已存在，直接返回路径
            if png_path.exists():
                return str(png_path.name)
            
            # 转换 SVG 到 PNG
            if self.convert_svg_to_png(svg_content, png_path):
                return str(png_path.name)
        except Exception as e:
            logger.warning(f"Failed to process SVG file {svg_path}: {e}")
        return ""

    def process_markdown(self, content: str) -> str:
        """处理 Markdown 内容，处理图片和 SVG"""
        # 先转换为 HTML
        html = self.md.convert(content)
        
        # 使用 BeautifulSoup 处理 HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 处理所有 SVG 标签
        for svg in soup.find_all('svg'):
            try:
                # 创建临时目录下的 images 目录
                images_dir = self.temp_dir / "images"
                images_dir.mkdir(exist_ok=True)
                
                # 转换 SVG 为 PNG
                svg_content = str(svg)
                hash_name = hashlib.md5(svg_content.encode()).hexdigest()
                png_path = images_dir / f"{hash_name}.png"
                
                if self.convert_svg_to_png(svg_content, png_path):
                    # 创建新的 img 标签替换 svg
                    img = soup.new_tag('img')
                    img['src'] = f"images/{png_path.name}"
                    svg.replace_with(img)
                else:
                    svg.decompose()
            except Exception as e:
                logger.warning(f"Failed to process inline SVG: {e}")
                svg.decompose()
            
        # 检查所有图片标签
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.lower().endswith('.svg'):
                try:
                    # 处理 SVG 图片引用
                    if not src.startswith(('http://', 'https://', '/')):
                        images_dir = self.temp_dir / "images"
                        images_dir.mkdir(exist_ok=True)
                        svg_path = Path(src)
                        if svg_path.exists():
                            png_name = self.process_svg_file(svg_path, images_dir)
                            if png_name:
                                img['src'] = f"images/{png_name}"
                            else:
                                img.decompose()
                except Exception as e:
                    logger.warning(f"Failed to process SVG image reference: {e}")
                    img.decompose()
            elif not any(src.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico']):
                img.decompose()
            
        # 获取处理后的 HTML
        cleaned_html = str(soup)
        
        # 将 HTML 转回 Markdown
        h2t = HTML2Text()
        h2t.body_width = 0  # 不限制行宽
        cleaned_markdown = h2t.handle(cleaned_html)
        
        return cleaned_markdown

    def _clean_text(self, text: str) -> str:
        """清理文本内容，处理不可见字符和特殊字符"""
        # 移除不可见字符，但保留换行
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r')
        
        # 处理制表符
        text = text.replace('\t', '    ')  # 将制表符替换为4个空格
        
        # 只处理 LaTeX 中最基本的特殊字符
        text = text.replace('\\', '\\textbackslash{}')  # 处理 \ 符号
        text = text.replace('$', '\\$')  # 处理 $ 符号
        text = text.replace('%', '\\%')  # 处理 % 符号
        
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
                        try:
                            # 处理 ./ 和 ../ 的情况
                            img_path = img_path.lstrip('./')
                            if img_path.startswith('../'):
                                # 处理 ../ 的情况，从当前文件所在目录开始解析
                                current_dir = file_path.parent
                                while img_path.startswith('../'):
                                    img_path = img_path[3:]
                                    current_dir = current_dir.parent
                                img_path = current_dir / img_path
                            else:
                                # 相对于当前文件的路径
                                img_path = file_path.parent / img_path

                            # 尝试在仓库中定位图片
                            abs_img_path = repo_root / img_path
                            if not abs_img_path.exists():
                                # 尝试作为相对于文件的路径
                                abs_img_path = file_path.parent / img_path
                            if not abs_img_path.exists():
                                # 尝试作为相对于仓库根目录的路径
                                abs_img_path = repo_root / img_path.name

                            if abs_img_path.exists() and abs_img_path.suffix.lower() in self.image_extensions:
                                # 复制图片到临时目录，使用唯一的名称避免冲突
                                unique_name = f"{abs_img_path.stem}_{abs_img_path.parent.name}{abs_img_path.suffix}"
                                target_path = images_dir / unique_name
                                shutil.copy2(abs_img_path, target_path)
                                # 返回更新后的图片引用
                                return f"![{match.group(1)}](images/{target_path.name})"
                            else:
                                logger.warning(f"Image not found or not supported: {abs_img_path}")
                        except Exception as e:
                            logger.warning(f"Error processing image path {img_path}: {e}")
                    return match.group(0)
                
                # 处理 Markdown 中的图片引用
                content = re.sub(r'!\[(.*?)\]\((.*?)\)', process_image_path, content)
                # 处理 HTML 格式的图片标签
                def process_html_img(match):
                    img_path = match.group(1)
                    if not img_path.startswith(('http://', 'https://', '/')):
                        try:
                            # 使用与上面相同的逻辑处理路径
                            img_path = img_path.lstrip('./')
                            if img_path.startswith('../'):
                                current_dir = file_path.parent
                                while img_path.startswith('../'):
                                    img_path = img_path[3:]
                                    current_dir = current_dir.parent
                                img_path = current_dir / img_path
                            else:
                                img_path = file_path.parent / img_path

                            abs_img_path = repo_root / img_path
                            if not abs_img_path.exists():
                                abs_img_path = file_path.parent / img_path
                            if not abs_img_path.exists():
                                abs_img_path = repo_root / img_path.name

                            if abs_img_path.exists() and abs_img_path.suffix.lower() in self.image_extensions:
                                unique_name = f"{abs_img_path.stem}_{abs_img_path.parent.name}{abs_img_path.suffix}"
                                target_path = images_dir / unique_name
                                shutil.copy2(abs_img_path, target_path)
                                return f'<img src="images/{target_path.name}"'
                            else:
                                logger.warning(f"Image not found or not supported: {abs_img_path}")
                        except Exception as e:
                            logger.warning(f"Error processing HTML image path {img_path}: {e}")
                    return match.group(0)

                content = re.sub(r'<img\s+src=["\']([^"\']+)["\']', process_html_img, content)
                
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
                    return f"\n\n# {rel_path}\n\n```\n{content}\n```\n\n"
                    
                # 对于其他文件使用语言高亮
                lang = self.code_extensions[ext]
                # 处理长字符串，将它们分割成多行
                content = self._process_long_lines(content)
                return f"\n\n# {rel_path}\n\n```{lang}\n{content}\n```\n\n"
                
            return ""
        except UnicodeDecodeError:
            logger.debug(f"跳过二进制文件: {file_path}")
            return ""
            
    def _process_long_lines(self, content: str, max_length: int = 100) -> str:
        """处理长行，将它们分割成多行"""
        lines = []
        for line in content.splitlines():
            if len(line) > max_length:
                # 对于包含长字符串的行进行特殊处理
                if '"' in line or "'" in line:
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

    def create_pandoc_yaml(self, repo_name: str) -> Path:
        """创建 Pandoc 的 YAML 配置文件"""
        pdf_config = self.config.get('pdf_settings', {})
        
        yaml_config = {
            'pdf-engine': 'xelatex',
            'highlight-style': pdf_config.get('highlight_style', 'tango'),
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
                    # 代码块设置
                    '\\fvset{breaklines=true,breakanywhere=true,commandchars=\\\\\\{\\}}',
                    '\\RecustomVerbatimEnvironment{Highlighting}{Verbatim}{',
                    '    breaklines=true,',
                    '    breakanywhere=true,',
                    '    commandchars=\\\\\\{\\},',
                    '    codes={\\catcode`\\$=3\\catcode`\\^=7},',
                    '    fontsize=\\small,',
                    '    baselinestretch=1,',
                    '    breakafter=\\{,\\},;,=,|,<,>,\\,,',
                    '    breakautoindent=false,',
                    '    samepage=false',
                    '}',
                    # 代码框设置
                    '\\renewenvironment{Shaded}{',
                    '    \\begin{tcolorbox}[',
                    '        breakable,',
                    '        boxrule=0pt,',
                    '        frame hidden,',
                    '        sharp corners,',
                    '        enhanced,',
                    '        interior style={opacity=0},',
                    '        before skip=\\baselineskip,',
                    '        after skip=\\baselineskip',
                    '    ]',
                    '}{',
                    '    \\end{tcolorbox}',
                    '}',
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
                    # 设置 listings 包的全局选项
                    '\\lstset{%',
                    '  basicstyle=\\ttfamily\\small,',
                    '  backgroundcolor=\\color{white},',
                    '  commentstyle=\\color{green!60!black},',
                    '  keywordstyle=\\color{blue!70!black},',
                    '  stringstyle=\\color{red!70!black},',
                    '  numberstyle=\\tiny\\color{gray},',
                    '  breaklines=true,',
                    '  breakatwhitespace=false,',
                    '  breakindent=0pt,',
                    '  keepspaces=true,',
                    '  showspaces=false,',
                    '  showstringspaces=false,',
                    '  showtabs=false,',
                    '  tabsize=2,',
                    '  frame=none,',
                    '  xleftmargin=0pt,',
                    '  numbers=none,',
                    '  inputencoding=utf8,',
                    '  extendedchars=true,',
                    '}',
                    # 定义新的语言
                    '\\lstdefinelanguage{typescript}[]{javascript}{%',
                    '  morekeywords={interface,type,implements,namespace,declare,abstract,',
                    '                as,is,keyof,in,extends,readonly,instanceof,unique,',
                    '                infer,await,async,module,namespace,declare,export,import},',
                    '}',
                    '\\lstdefinelanguage{tsx}{',
                    '  basicstyle=\\ttfamily,',
                    '  keywords={const,let,var,function,class,extends,implements,import,export,return,if,else,for,while,do,switch,case,break,continue,try,catch,finally,throw,async,await,static,public,private,protected,get,set,new,this,super,interface,type,namespace,JSX},',
                    '  keywordstyle=\\color{blue},',
                    '  sensitive=true,',
                    '  comment=[l]{//},',
                    '  morecomment=[s]{/*}{*/},',
                    '  commentstyle=\\color{darkgreen},',
                    '  stringstyle=\\color{red},',
                    '  morestring=[b]",',
                    '  morestring=[b]\',',
                    '}',
                    '\\lstdefinelanguage{vue}{',
                    '  basicstyle=\\ttfamily,',
                    '  keywords={template,script,style,export,default,props,data,methods,computed,watch,components,mounted,created,updated,destroyed,beforeCreate,beforeMount,beforeUpdate,beforeDestroy},',
                    '  keywordstyle=\\color{blue},',
                    '  sensitive=true,',
                    '  comment=[l]{//},',
                    '  morecomment=[s]{/*}{*/},',
                    '  commentstyle=\\color{darkgreen},',
                    '  stringstyle=\\color{red},',
                    '  morestring=[b]",',
                    '  morestring=[b]\',',
                    '}',
                    '\\lstdefinelanguage{svelte}{',
                    '  basicstyle=\\ttfamily,',
                    '  keywords={script,style,export,let,const,if,else,each,await,then,catch,as,import,from},',
                    '  keywordstyle=\\color{blue},',
                    '  sensitive=true,',
                    '  comment=[l]{//},',
                    '  morecomment=[s]{/*}{*/},',
                    '  commentstyle=\\color{darkgreen},',
                    '  stringstyle=\\color{red},',
                    '  morestring=[b]",',
                    '  morestring=[b]\',',
                    '}',
                    # 添加 MDX 语言定义
                    '\\lstdefinelanguage{mdx}{',
                    '  basicstyle=\\ttfamily,',
                    '  keywords={import,export,default,function,return,props,const,let,var,if,else,switch,case,break,continue,for,while,do,try,catch,finally,throw,class,extends,new,delete,typeof,instanceof,void,this,super,with,yield,async,await,static,get,set,of,from,as},',
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
                    '}',
                    # 标题和段落设置
                    '\\setlength{\\headheight}{15pt}',
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
                '-V', 'geometry:margin=0.5in',
                '-V', 'fontsize=10pt',
                '--highlight-style=tango',
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