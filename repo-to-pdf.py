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
            '.py': 'python',
            '.js': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.sh': 'bash',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.json': 'json',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown'
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
        """处理 Markdown 内容，移除所有图片和 SVG"""
        # 先转换为 HTML
        html = self.md.convert(content)
        
        # 使用 BeautifulSoup 处理 HTML
        soup = BeautifulSoup(html, 'html.parser')
        
        # 移除所有图片
        for img in soup.find_all('img'):
            img.decompose()
            
        # 移除所有 SVG
        for svg in soup.find_all('svg'):
            svg.decompose()
            
        # 移除所有 figure 标签
        for figure in soup.find_all('figure'):
            figure.decompose()
            
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
            
        # 跳过二进制文件和图片文件
        binary_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.svgz', '.db', '.sketch'}
        if ext in binary_extensions:
            return ""
            
        try:
            # 获取文件大小（MB）
            file_size = file_path.stat().st_size / (1024 * 1024)
            # 如果文件大于 1MB，跳过
            if file_size > 1:
                logger.debug(f"跳过大文件 ({file_size:.1f}MB): {file_path}")
                return ""
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 如果是 Markdown 文件，使用新的处理方法
            if ext == '.md':
                cleaned_content = self.process_markdown(content)
                return f"\n\n# {rel_path}\n\n{cleaned_content}\n\n"
            
            # 如果是支持的代码文件，转换为代码块
            if ext in self.code_extensions:
                # 跳过包含 SVG 的文件
                if '<svg' in content:
                    return ""
                lang = self.code_extensions[ext]
                return f"\n\n# {rel_path}\n\n```{lang}\n{content}\n```\n\n"
                
            return ""
        except UnicodeDecodeError:
            logger.debug(f"跳过二进制文件: {file_path}")
            return ""

    def create_pandoc_yaml(self) -> Path:
        """创建 Pandoc 的 YAML 配置文件"""
        pdf_config = self.config.get('pdf_settings', {})
        
        yaml_config = {
            'pdf-engine': 'xelatex',
            'variables': {
                'documentclass': 'article',
                'geometry': pdf_config.get('margin', 'margin=1in'),
                'mainfont': pdf_config.get('main_font', 'Songti SC'),
                'mainfontoptions': ['BoldFont=Songti SC Bold'],
                'monofont': pdf_config.get('mono_font', 'SF Mono'),
                'monofontoptions': ['Scale=0.9'],
                'colorlinks': True,
                'linkcolor': 'blue',
                'urlcolor': 'blue'
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
                '--toc',  # 添加目录
                '--toc-depth=2',
                '--pdf-engine=xelatex',
                '--wrap=none',
                '-V', 'geometry:margin=0.5in',
                '-V', 'CJKmainfont=Songti SC',
                '-V', 'fontsize=10pt',
                '--no-highlight',
                '--resource-path=.',
                '--standalone',
                # 简化 LaTeX 设置
                '-V', 'header-includes=\\usepackage{ragged2e}',
                '-V', 'header-includes=\\AtBeginDocument{\\justifying}',
                # 添加内存优化设置
                '--pdf-engine-opt=-halt-on-error',
                '--pdf-engine-opt=-interaction=nonstopmode',
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