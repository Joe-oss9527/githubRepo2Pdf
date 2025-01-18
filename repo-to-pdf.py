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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitRepoManager:
    def __init__(self, repo_url: str, branch: str = 'main'):
        self.repo_url = repo_url
        self.branch = branch
        self.repo_dir = None
        
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
            '.mdx': 'mdx',
            
            # 其他
            '.dockerfile': 'dockerfile',
            '.env': 'dotenv',
            '.ini': 'ini'
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

    def process_markdown(self, content: str) -> str:
        """处理 Markdown 内容，确保只保留支持的图片格式"""
        # 先转换为 HTML
        html = self.md.convert(content)
        
        # 使用 BeautifulSoup 处理 HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除所有 SVG
        for svg in soup.find_all('svg'):
            svg.decompose()
            
        # 检查所有图片标签
        for img in soup.find_all('img'):
            src = img.get('src', '')
            # 只保留支持的图片格式
            if not any(src.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.ico']):
                img.decompose()
            
        # 获取处理后的 HTML
        cleaned_html = str(soup)
        
        # 将 HTML 转回 Markdown
        from html2text import HTML2Text
        h2t = HTML2Text()
        h2t.body_width = 0  # 不限制行宽
        cleaned_markdown = h2t.handle(cleaned_html)
        
        return cleaned_markdown

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
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico'}
        if ext.lower() in image_extensions:
            try:
                # 复制图片到临时目录
                target_path = images_dir / file_path.name
                shutil.copy2(file_path, target_path)
            except Exception as e:
                logger.warning(f"Failed to copy image {file_path}: {e}")
            return ""
            
        try:
            # 获取文件大小（MB）
            file_size = file_path.stat().st_size / (1024 * 1024)
            # 如果文件大于 1MB，跳过
            if file_size > 1 and ext not in image_extensions:
                logger.debug(f"跳过大文件 ({file_size:.1f}MB): {file_path}")
                return ""
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 如果是 Markdown 文件，处理图片路径
            if ext == '.md':
                # 处理图片路径
                def process_image_path(match):
                    img_path = match.group(2)
                    if not img_path.startswith(('http://', 'https://', '/')):
                        # 相对路径的图片
                        abs_img_path = (file_path.parent / img_path).resolve()
                        if abs_img_path.exists() and abs_img_path.suffix.lower() in image_extensions:
                            # 复制图片到临时目录
                            target_path = images_dir / abs_img_path.name
                            shutil.copy2(abs_img_path, target_path)
                            # 返回更新后的图片引用
                            return f"![{match.group(1)}](images/{target_path.name})"
                    return match.group(0)
                
                # 处理 Markdown 中的图片引用
                import re
                content = re.sub(r'!\[(.*?)\]\((.*?)\)', process_image_path, content)
                cleaned_content = self.process_markdown(content)
                return f"\n\n# {rel_path}\n\n{cleaned_content}\n\n"
            
            # 如果是支持的代码文件，转换为代码块
            if ext in self.code_extensions:
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

    def create_pandoc_yaml(self) -> Path:
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
                # LaTeX 设置
                'header-includes': [
                    # 加载必要的包
                    '\\usepackage{xeCJK}',
                    '\\usepackage{fvextra}',
                    '\\usepackage[most]{tcolorbox}',
                    '\\usepackage{listings}',
                    '\\usepackage{graphicx}',
                    '\\usepackage{float}',
                    # 图片设置
                    '\\DeclareGraphicsExtensions{.png,.jpg,.jpeg,.gif}',
                    '\\graphicspath{{./images/}}',
                    # 图片处理设置
                    '\\usepackage{adjustbox}',
                    '\\setkeys{Gin}{width=0.8\\linewidth,keepaspectratio}',
                    # 代码块设置
                    '\\DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,commandchars=\\\\\\{\\}}',
                    '\\fvset{breaklines=true, breakanywhere=true}',
                    # 代码框设置
                    '\\renewenvironment{Shaded}{\\begin{tcolorbox}[breakable,boxrule=0pt,frame hidden,sharp corners]}{\\end{tcolorbox}}',
                    # 定义新的语言
                    '\\lstdefinelanguage{typescript}[]{javascript}{%',
                    '  morekeywords={interface,type,implements,namespace,declare,abstract,',
                    '                as,is,keyof,in,extends,readonly,instanceof,unique,',
                    '                infer,await,async,module,namespace,declare,export,import},',
                    '}',
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
                    '  tabsize=2,',
                    '  frame=none,',
                    '  xleftmargin=0pt,',
                    '  numbers=none,',
                    '  inputencoding=utf8,',
                    '  extendedchars=true,',
                    '  literate={á}{{\\\'a}}1 {é}{{\\\'e}}1 {í}{{\\\'i}}1 {ó}{{\\\'o}}1 {ú}{{\\\'u}}1',
                    '           {Á}{{\\\'A}}1 {É}{{\\\'E}}1 {Í}{{\\\'I}}1 {Ó}{{\\\'O}}1 {Ú}{{\\\'U}}1',
                    '           {à}{{\`a}}1 {è}{{\`e}}1 {ì}{{\`i}}1 {ò}{{\`o}}1 {ù}{{\`u}}1',
                    '           {À}{{\`A}}1 {È}{{\\`E}}1 {Ì}{{\`I}}1 {Ò}{{\`O}}1 {Ù}{{\`U}}1',
                    '           {ä}{{\"a}}1 {ë}{{\"e}}1 {ï}{{\"i}}1 {ö}{{\"o}}1 {ü}{{\"u}}1',
                    '           {Ä}{{\"A}}1 {Ë}{{\"E}}1 {Ï}{{\"I}}1 {Ö}{{\"O}}1 {Ü}{{\"U}}1',
                    '           {â}{{\^a}}1 {ê}{{\^e}}1 {î}{{\^i}}1 {ô}{{\^o}}1 {û}{{\^u}}1',
                    '           {Â}{{\^A}}1 {Ê}{{\^E}}1 {Î}{{\^I}}1 {Ô}{{\^O}}1 {Û}{{\^U}}1',
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
                    # 标题和段落设置
                    '\\setlength{\\headheight}{15pt}',
                    # 中文字体设置
                    '\\setCJKmainfont[BoldFont={Songti SC Bold},ItalicFont={Songti SC Light}]{Songti SC}',
                    '\\setCJKsansfont[BoldFont={PingFang SC Semibold},ItalicFont={PingFang SC Light}]{PingFang SC}',
                    '\\setCJKmonofont{STFangsong}',
                    # 中文断行设置
                    '\\XeTeXlinebreaklocale "zh"',
                    '\\XeTeXlinebreakskip = 0pt plus 1pt',
                    # 标题字体设置
                    '\\usepackage{sectsty}',
                    '\\sectionfont{\\CJKfamily{sf}}',
                    '\\subsectionfont{\\CJKfamily{sf}}'
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
            yaml_path = self.create_pandoc_yaml()
            
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
                '-f', 'markdown',
                '-t', 'pdf',
                '--defaults', str(yaml_path),
                '--toc',
                '--toc-depth=2',
                '--pdf-engine=xelatex',
                '--wrap=none',
                '-V', 'geometry:margin=0.5in',
                '-V', 'fontsize=10pt',
                '--highlight-style=tango',
                '--resource-path=' + str(self.temp_dir),  # 修改资源路径设置
                '--standalone',
                # LaTeX 设置
                '-V', 'header-includes=\\usepackage{ragged2e}',
                '-V', 'header-includes=\\usepackage{graphicx}',  # 添加图片支持
                '-V', 'header-includes=\\usepackage{float}',     # 添加浮动体支持
                '-V', 'header-includes=\\AtBeginDocument{\\justifying}',
                # 优化设置
                '--pdf-engine-opt=-halt-on-error',
                '--pdf-engine-opt=-interaction=nonstopmode',
                # 移除内存设置，因为格式不正确
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
    
    args = parser.parse_args()
    
    converter = RepoPDFConverter(args.config)
    converter.convert()

if __name__ == '__main__':
    main()