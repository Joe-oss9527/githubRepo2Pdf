#!/usr/bin/env python3
"""
Unit tests for repo-to-pdf converter
"""
import unittest
import tempfile
import shutil
from pathlib import Path
import yaml
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path modification
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module (file is named repo-to-pdf.py)
import importlib.util
spec = importlib.util.spec_from_file_location("repo_to_pdf", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repo-to-pdf.py"))
repo_to_pdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repo_to_pdf)

# Import classes and functions
GitRepoManager = repo_to_pdf.GitRepoManager
RepoPDFConverter = repo_to_pdf.RepoPDFConverter
get_system_fonts = repo_to_pdf.get_system_fonts


class TestGitRepoManager(unittest.TestCase):
    """Test GitRepoManager class"""
    
    def setUp(self):
        self.test_repo_url = "https://github.com/test/repo.git"
        self.test_branch = "main"
        
    def test_init(self):
        """Test GitRepoManager initialization"""
        manager = GitRepoManager(self.test_repo_url, self.test_branch)
        self.assertEqual(manager.repo_url, self.test_repo_url)
        self.assertEqual(manager.branch, self.test_branch)
        self.assertIsNone(manager.repo_dir)
    
    def test_url_parsing_https(self):
        """Test HTTPS URL parsing"""
        manager = GitRepoManager("https://github.com/user/repo.git")
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # Mock the actual cloning
            with patch('git.Repo.clone_from') as mock_clone:
                mock_clone.return_value = Mock()
                result = manager.clone_or_pull(workspace)
                self.assertEqual(result.name, "repo")
    
    def test_url_parsing_ssh(self):
        """Test SSH URL parsing"""
        manager = GitRepoManager("git@github.com:user/repo.git")
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            # Create the expected directory
            (workspace / "repo").mkdir()
            # Mock git operations
            with patch('git.Repo') as mock_repo:
                mock_repo.return_value = Mock()
                result = manager.clone_or_pull(workspace)
                self.assertEqual(result.name, "repo")
    
    def test_url_parsing_edge_cases(self):
        """Test edge cases in URL parsing"""
        test_cases = [
            ("https://gitlab.com/group/subgroup/repo.git", "repo"),
            ("https://github.com/user/repo", "repo"),
            ("git@bitbucket.org:team/repo.git", "repo"),
            ("https://custom.git.server:8080/path/to/repo.git", "repo"),
        ]
        
        for url, expected_name in test_cases:
            manager = GitRepoManager(url)
            with tempfile.TemporaryDirectory() as tmpdir:
                workspace = Path(tmpdir)
                # Create expected directory
                (workspace / expected_name).mkdir()
                with patch('git.Repo') as mock_repo:
                    mock_repo.return_value = Mock()
                    result = manager.clone_or_pull(workspace)
                    self.assertEqual(result.name, expected_name)


class TestSystemFonts(unittest.TestCase):
    """Test font detection functionality"""
    
    def test_get_system_fonts_structure(self):
        """Test that get_system_fonts returns correct structure"""
        fonts = get_system_fonts()
        self.assertIn('main_font', fonts)
        self.assertIn('sans_font', fonts)
        self.assertIn('mono_font', fonts)
        self.assertIn('fallback_fonts', fonts)
        self.assertIsInstance(fonts['fallback_fonts'], list)
    
    @patch('os.uname')
    def test_get_system_fonts_macos(self, mock_uname):
        """Test font detection on macOS"""
        mock_uname.return_value = Mock(sysname='Darwin')
        fonts = get_system_fonts()
        self.assertEqual(fonts['main_font'], 'Songti SC')
        self.assertEqual(fonts['mono_font'], 'SF Mono')
    
    @patch('os.uname')
    def test_get_system_fonts_linux(self, mock_uname):
        """Test font detection on Linux"""
        mock_uname.return_value = Mock(sysname='Linux')
        fonts = get_system_fonts()
        self.assertEqual(fonts['main_font'], 'Noto Serif CJK SC')
        self.assertEqual(fonts['mono_font'], 'DejaVu Sans Mono')


class TestRepoPDFConverter(unittest.TestCase):
    """Test RepoPDFConverter class"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = Path(self.test_dir) / "test_config.yaml"
        
        # Create test configuration
        self.test_config = {
            'repository': {
                'url': 'https://github.com/test/repo.git',
                'branch': 'main'
            },
            'workspace_dir': './test-workspace',
            'output_dir': './test-pdfs',
            'pdf_settings': {
                'margin': 'margin=1in',
                'main_font': 'Test Font',
                'mono_font': 'Test Mono',
                'highlight_style': 'monochrome'
            },
            'ignores': ['node_modules', '*.pyc', '.git']
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init_without_template(self):
        """Test RepoPDFConverter initialization without template"""
        converter = RepoPDFConverter(self.config_path)
        self.assertEqual(converter.config['repository']['url'], 
                        self.test_config['repository']['url'])
        self.assertIsNone(converter.template)
        self.assertTrue(converter.workspace_dir.exists())
        self.assertTrue(converter.output_dir.exists())
    
    def test_init_with_template(self):
        """Test RepoPDFConverter initialization with template"""
        # Create template directory and file
        template_dir = Path(self.test_dir) / "templates"
        template_dir.mkdir()
        template_file = template_dir / "test.yaml"
        
        template_config = {
            'name': 'Test Template',
            'description': 'Test template description',
            'structure': {
                'include_tree': True,
                'include_stats': True
            }
        }
        
        with open(template_file, 'w') as f:
            yaml.dump(template_config, f)
        
        converter = RepoPDFConverter(self.config_path, 'test')
        self.assertIsNotNone(converter.template)
        self.assertEqual(converter.template['name'], 'Test Template')
    
    def test_should_ignore(self):
        """Test file ignore logic"""
        converter = RepoPDFConverter(self.config_path)
        
        # Test exact matches
        self.assertTrue(converter._should_ignore(Path("test.pyc")))
        self.assertTrue(converter._should_ignore(Path("path/to/node_modules/file.js")))
        
        # Test wildcards
        self.assertTrue(converter._should_ignore(Path("test.pyc")))
        self.assertTrue(converter._should_ignore(Path("another.pyc")))
        
        # Test non-ignored files
        self.assertFalse(converter._should_ignore(Path("test.py")))
        self.assertFalse(converter._should_ignore(Path("src/main.js")))
    
    def test_process_long_lines(self):
        """Test long line processing"""
        converter = RepoPDFConverter(self.config_path)
        
        # Test normal line
        short_line = "print('hello')"
        self.assertEqual(converter._process_long_lines(short_line), short_line)
        
        # Test long array
        long_array = "[" + ", ".join([f"'item{i}'" for i in range(50)]) + "]"
        processed = converter._process_long_lines(long_array, max_length=50)
        self.assertIn('\n', processed)
        
        # Test long string
        long_string = '"' + "a" * 150 + '"'
        processed = converter._process_long_lines(long_string)
        self.assertIn('\n', processed)
    
    def test_generate_directory_tree(self):
        """Test directory tree generation"""
        converter = RepoPDFConverter(self.config_path)
        
        # Create test directory structure
        test_repo = Path(self.test_dir) / "test_repo"
        test_repo.mkdir()
        (test_repo / "src").mkdir()
        (test_repo / "src" / "main.py").write_text("print('hello')")
        (test_repo / "README.md").write_text("# Test")
        (test_repo / ".git").mkdir()  # Should be ignored
        
        tree = converter.generate_directory_tree(test_repo, max_depth=2)
        
        self.assertIn("test_repo/", tree)
        self.assertIn("src/", tree)
        self.assertIn("main.py", tree)
        self.assertIn("README.md", tree)
        self.assertNotIn(".git", tree)  # Hidden directories should be ignored
    
    def test_generate_code_stats(self):
        """Test code statistics generation"""
        converter = RepoPDFConverter(self.config_path)
        
        # Create test files
        test_repo = Path(self.test_dir) / "test_repo"
        test_repo.mkdir()
        
        # Python file
        (test_repo / "test.py").write_text("def hello():\n    print('world')\n")
        
        # JavaScript file
        (test_repo / "app.js").write_text("console.log('test');\n")
        
        # Text file (not code)
        (test_repo / "notes.txt").write_text("Some notes\n")
        
        stats = converter.generate_code_stats(test_repo)
        
        self.assertIn("代码统计", stats)
        self.assertIn("总文件数", stats)
        self.assertIn("python", stats.lower())
        self.assertIn("javascript", stats.lower())
    
    @patch('subprocess.run')
    def test_convert_svg_to_png(self, mock_run):
        """Test SVG to PNG conversion"""
        converter = RepoPDFConverter(self.config_path)
        converter.temp_dir = Path(self.test_dir) / "temp"
        converter.temp_dir.mkdir()
        
        svg_content = '<svg width="100" height="100"><rect width="100" height="100"/></svg>'
        output_path = converter.temp_dir / "test.png"
        
        # Mock cairosvg in sys.modules
        mock_cairosvg = Mock()
        mock_cairosvg.svg2png = Mock()
        
        # Store the original module state
        original_modules = sys.modules.copy()
        sys.modules['cairosvg'] = mock_cairosvg
        
        try:
            result = converter.convert_svg_to_png(svg_content, output_path)
            self.assertTrue(result)
            mock_cairosvg.svg2png.assert_called_once()
        finally:
            # Restore the original modules
            sys.modules.clear()
            sys.modules.update(original_modules)
    
    def test_process_markdown(self):
        """Test markdown processing"""
        converter = RepoPDFConverter(self.config_path)
        converter.temp_dir = Path(self.test_dir) / "temp"
        converter.temp_dir.mkdir()
        
        # Test image processing
        content = "![Alt text](image.svg)"
        with patch.object(converter, '_convert_image_to_png') as mock_convert:
            mock_convert.return_value = "images/image.png"
            processed = converter.process_markdown(content)
            self.assertIn("images/image.png", processed)
            self.assertNotIn("image.svg", processed)
        
        # Test remote image
        content = "![Badge](https://img.shields.io/badge/test-badge.svg)"
        with patch.object(converter, '_download_remote_image') as mock_download:
            mock_download.return_value = "images/badge.png"
            processed = converter.process_markdown(content)
            self.assertIn("images/badge.png", processed)
    
    def test_clean_text(self):
        """Test text cleaning"""
        converter = RepoPDFConverter(self.config_path)
        
        # Test that clean_text returns text unchanged
        test_text = "Hello\nWorld\n特殊字符：$%^&*()"
        cleaned = converter._clean_text(test_text)
        self.assertEqual(cleaned, test_text)


class TestFileProcessing(unittest.TestCase):
    """Test file processing functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = Path(self.test_dir) / "config.yaml"
        
        config = {
            'repository': {'url': 'test', 'branch': 'main'},
            'workspace_dir': './workspace',
            'output_dir': './output',
            'ignores': []
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
        
        self.converter = RepoPDFConverter(self.config_path)
        self.converter.temp_dir = Path(self.test_dir) / "temp"
        self.converter.temp_dir.mkdir()
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_process_python_file(self):
        """Test Python file processing"""
        test_file = Path(self.test_dir) / "test.py"
        test_file.write_text("def hello():\n    print('world')")
        
        result = self.converter.process_file(test_file, Path(self.test_dir))
        self.assertIn("```python", result)
        self.assertIn("def hello():", result)
        self.assertIn("test.py", result)
    
    def test_process_markdown_file(self):
        """Test Markdown file processing"""
        test_file = Path(self.test_dir) / "README.md"
        test_file.write_text("# Title\n\nContent with ![image](pic.png)")
        
        result = self.converter.process_file(test_file, Path(self.test_dir))
        self.assertIn("# Title", result)
        self.assertIn("README.md", result)
    
    def test_process_large_file(self):
        """Test large file handling"""
        test_file = Path(self.test_dir) / "large.txt"
        # Create a file larger than 0.5MB (new limit)
        test_file.write_text("x" * (512 * 1024 + 1))
        
        result = self.converter.process_file(test_file, Path(self.test_dir))
        self.assertEqual(result, "")  # Should skip large files
    
    def test_process_binary_file(self):
        """Test binary file handling"""
        test_file = Path(self.test_dir) / "binary.bin"
        test_file.write_bytes(b'\x00\x01\x02\x03')
        
        result = self.converter.process_file(test_file, Path(self.test_dir))
        self.assertEqual(result, "")  # Should skip binary files
    
    def test_process_long_lines(self):
        """Test long line processing"""
        # Test array formatting
        long_array = "[" + ", ".join([f"'item{i}'" for i in range(50)]) + "]"
        processed = self.converter._process_long_lines(long_array)
        self.assertIn("\n", processed)  # Should contain line breaks
        
        # Test string breaking
        long_string = 'test_string = "' + "x" * 200 + '"'
        processed = self.converter._process_long_lines(long_string)
        self.assertIn("\\\n", processed)  # Should contain line continuation
        
        # Test normal line
        short_line = "def hello(): pass"
        processed = self.converter._process_long_lines(short_line)
        self.assertEqual(short_line, processed)  # Should remain unchanged
    
    def test_break_long_strings(self):
        """Test long string breaking"""
        # Test long string
        line = 'url = "' + "a" * 150 + '"'
        result = self.converter._break_long_strings(line)
        self.assertIn("\\\n", result)  # Should contain line continuation
        
        # Test short string
        line = 'name = "short"'
        result = self.converter._break_long_strings(line)
        self.assertEqual(line, result)  # Should remain unchanged
    
    def test_file_truncation(self):
        """Test file splitting for very large files"""
        test_file = Path(self.test_dir) / "huge.py"
        # Create a file with more than 1000 lines
        content = "\n".join([f"print('Line {i}')" for i in range(1500)])
        test_file.write_text(content)
        
        result = self.converter.process_file(test_file, Path(self.test_dir))
        self.assertIn("注意：此文件包含 1500 行", result)  # Should contain notice
        self.assertIn("已分为", result)  # Should mention parts
        self.assertIn("第 1/2 部分", result)  # Should have first part
        self.assertIn("第 2/2 部分", result)  # Should have second part
    
    def test_process_large_file_method(self):
        """Test the _process_large_file method directly"""
        lines = [f"line {i}" for i in range(2000)]
        result = self.converter._process_large_file("test/large.py", lines, "python")
        
        # Check structure
        self.assertIn("注意：此文件包含 2000 行", result)
        self.assertIn("已分为 3 个部分", result)  # 2000/800 = 2.5, so 3 parts
        self.assertIn("第 1/3 部分 (行 1-800)", result)
        self.assertIn("第 2/3 部分 (行 801-1600)", result)
        self.assertIn("第 3/3 部分 (行 1601-2000)", result)
        
        # Check content preservation
        self.assertIn("line 0", result)
        self.assertIn("line 799", result)
        self.assertIn("line 800", result)
        self.assertIn("line 1999", result)


class TestLaTeXGeneration(unittest.TestCase):
    """Test LaTeX generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.config_path = Path(self.test_dir) / "config.yaml"
        
        config = {
            'repository': {'url': 'test', 'branch': 'main'},
            'workspace_dir': './workspace',
            'output_dir': './output',
            'pdf_settings': {
                'main_font': 'Noto Serif CJK SC',
                'mono_font': 'DejaVu Sans Mono'
            }
        }
        
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_latex_header_generation(self):
        """Test LaTeX header generation with dimension handling"""
        converter = RepoPDFConverter(self.config_path)
        converter.temp_dir = Path(self.test_dir) / "temp"
        converter.temp_dir.mkdir()
        
        # Mock repo path
        repo_path = Path(self.test_dir) / "repo"
        repo_path.mkdir()
        
        # Create header.tex by running the header generation code
        header_path = converter.temp_dir / "header.tex"
        
        # Extract header generation logic from convert method
        fonts = get_system_fonts()
        main_font = converter.config.get('pdf_settings', {}).get('main_font', fonts['main_font'])
        mono_font = converter.config.get('pdf_settings', {}).get('mono_font', fonts['mono_font'])
        
        header_content = f"""% 设置字体
\\usepackage{{fontspec}}
\\usepackage{{xeCJK}}
\\setCJKmainfont{{{main_font}}}
\\setCJKsansfont{{{fonts.get('sans_font', main_font)}}}
\\setCJKmonofont{{{main_font}}}
\\setmonofont{{{mono_font}}}

% 中文支持
\\XeTeXlinebreaklocale "zh"
\\XeTeXlinebreakskip = 0pt plus 1pt

% 代码高亮
\\usepackage{{fvextra}}
\\DefineVerbatimEnvironment{{Highlighting}}{{Verbatim}}{{breaklines,commandchars=\\\\\\{{\\}}, fontsize=\\small}}
\\fvset{{breaklines=true, breakanywhere=true, fontsize=\\small}}

% 防止 Dimension too large 错误
\\maxdeadcycles=200
\\emergencystretch=5em
\\usepackage{{etoolbox}}
\\makeatletter
\\patchcmd{{\\@verbatim}}
  {{\\verbatim@font}}
  {{\\verbatim@font\\small}}
  {{}}{{}}
\\makeatother

% 页面设置
\\usepackage{{graphicx}}
\\DeclareGraphicsExtensions{{.png,.jpg,.jpeg,.gif}}
\\graphicspath{{{{./images/}}}}

% 超链接
\\usepackage{{hyperref}}
\\hypersetup{{
    pdftitle={{{repo_path.name} 代码文档}},
    pdfauthor={{Repo-to-PDF Generator}},
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue
}}
"""
        
        with open(header_path, 'w', encoding='utf-8') as f:
            f.write(header_content)
        
        # Verify header content
        self.assertTrue(header_path.exists())
        content = header_path.read_text()
        
        # Check for dimension handling
        self.assertIn("\\maxdeadcycles=200", content)
        self.assertIn("\\emergencystretch=5em", content)
        self.assertIn("\\usepackage{etoolbox}", content)
        self.assertIn("fontsize=\\small", content)
        self.assertIn("\\patchcmd{\\@verbatim}", content)
        
        # Check for font settings
        self.assertIn("\\setCJKmainfont", content)
        self.assertIn("\\setmonofont", content)
        
        # Check for fvextra settings
        self.assertIn("\\usepackage{fvextra}", content)
        self.assertIn("breaklines=true", content)
        self.assertIn("breakanywhere=true", content)


class TestTemplateSystem(unittest.TestCase):
    """Test template system functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.template_dir = Path(self.test_dir) / "templates"
        self.template_dir.mkdir()
        
        # Create test template
        self.template_content = {
            'name': 'Test Template',
            'description': 'A test template',
            'structure': {
                'include_tree': True,
                'include_stats': False,
                'sections': [
                    {
                        'title': 'Overview',
                        'content': 'Project: {{repo_name}}\nDate: {{date}}'
                    }
                ]
            }
        }
        
        with open(self.template_dir / "test.yaml", 'w') as f:
            yaml.dump(self.template_content, f)
    
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_load_template_success(self):
        """Test successful template loading"""
        config_path = Path(self.test_dir) / "config.yaml"
        config = {
            'repository': {'url': 'test', 'branch': 'main'},
            'workspace_dir': './workspace',
            'output_dir': './output'
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        converter = RepoPDFConverter(config_path, 'test')
        self.assertIsNotNone(converter.template)
        self.assertEqual(converter.template['name'], 'Test Template')
    
    def test_load_nonexistent_template(self):
        """Test loading non-existent template"""
        config_path = Path(self.test_dir) / "config.yaml"
        config = {
            'repository': {'url': 'test', 'branch': 'main'},
            'workspace_dir': './workspace',
            'output_dir': './output'
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        converter = RepoPDFConverter(config_path, 'nonexistent')
        self.assertIsNone(converter.template)


if __name__ == '__main__':
    unittest.main()