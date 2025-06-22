# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

githubRepo2Pdf is a Python tool that converts GitHub repositories into PDF documents with syntax highlighting, designed specifically with Chinese language support. It clones or updates a target repository, processes all code files with appropriate syntax highlighting, handles images (including SVG to PNG conversion), and generates a comprehensive PDF document using Pandoc and XeLaTeX.

## Key Commands

### Build and Development
```bash
# Install dependencies and convert (default)
make

# Run in debug mode with verbose logging
make debug
# or
VERBOSE=1 make

# Run in quiet mode (warnings/errors only)
QUIET=1 make

# Use custom template
TEMPLATE=technical make

# Install system and Python dependencies only
make deps

# Execute conversion only (assumes deps installed)
make convert

# Clean temporary files
make clean

# Clean all generated files including PDFs
make clean-all
```

### Testing and Debugging
```bash
# Run all tests
make test

# Run with coverage report
make test-coverage

# Run specific test file
./venv/bin/python -m pytest tests/test_repo_to_pdf.py

# Run tests with verbose output
./venv/bin/python -m pytest -xvs
```

- Comprehensive test suite using pytest
- Unit tests for all major components
- Integration tests for end-to-end conversion
- Coverage requirement: 50% (working towards 80%)
- CI/CD workflow for automated testing (.github/workflows/test.yml)
- When conversion fails, check `debug.md` for the generated markdown
- Temporary files are preserved in `temp_conversion_files/` for debugging

## Architecture Overview

### Core Components

1. **repo-to-pdf.py**: Main script containing:
   - `GitRepoManager`: Handles repository cloning/updating with shallow clones, supports HTTP/HTTPS/SSH URLs
   - `RepoPDFConverter`: Core conversion logic with template support
   - `get_system_fonts()`: Cross-platform font detection
   - `generate_directory_tree()`: Visual project structure generation
   - `generate_code_stats()`: Code statistics and language analysis
   - Smart file filtering and size management (1MB default limit)
   - SVG to PNG conversion using CairoSVG
   - Remote image downloading and embedding
   - Syntax highlighting for 30+ programming languages
   - Progress bar integration with tqdm
   - Stream processing to avoid memory issues

2. **Makefile**: Comprehensive build automation:
   - OS detection (macOS/Linux) with automatic dependency installation
   - Python virtual environment management
   - Colored output with multiple verbosity levels
   - Homebrew integration for macOS dependencies

3. **config.yaml**: User configuration:
   - Repository URL and branch specification
   - Output directories and PDF settings
   - Extensive ignore patterns for build artifacts
   - Font and styling customization

4. **templates/**: Template system for custom PDF structures:
   - `default.yaml`: Standard code documentation template
   - `technical.yaml`: Technical documentation template with file type grouping
   - Support for custom sections, statistics, and styling

### Conversion Pipeline

1. Clone/update target repository (shallow clone with `--depth=1`)
2. Walk repository tree, filtering by ignore patterns
3. Process each file:
   - Convert SVG images to PNG for PDF compatibility
   - Download and embed remote images
   - Apply syntax highlighting to code files
   - Handle HTML to Markdown conversion
4. Combine all content into single Markdown file
5. Generate PDF using Pandoc with XeLaTeX backend

### Key Technical Details

- **Image Handling**: Automatic SVG to PNG conversion, remote image downloading with caching
- **Text Processing**: Smart handling of Chinese text, LaTeX special character escaping
- **File Management**: Respects .gitignore, applies extensive default ignore patterns
- **Performance**: Shallow git clones, 1MB file size limit, efficient directory traversal
- **Logging**: Three-tier logging system (normal, verbose, quiet) controlled via make parameters

## Important Paths

- Working directory: `repo-workspace/` (gitignored)
- Output PDFs: `repo-pdfs/` (gitignored)
- Temporary files: `temp_conversion_files/`
- Virtual environment: `venv/` (gitignored)

## Dependencies

### System Requirements
- Python 3.6+
- pandoc
- XeLaTeX (via MacTeX on macOS)
- Cairo library
- Inkscape (optional, for SVG conversion)
- Git

### Python Dependencies (requirements.txt)
- GitPython==3.1.42 (git operations)
- PyYAML==6.0.1 (config parsing)
- markdown==3.5.2 (markdown processing)
- beautifulsoup4==4.12.3 (HTML parsing)
- cairosvg>=2.7.1 (SVG conversion)
- svglib>=1.5.1 (SVG parsing)
- reportlab>=4.0.9 (PDF generation support)
- requests>=2.31.0 (remote images)
- tqdm>=4.66.0 (progress bars)

### Testing Dependencies
- pytest>=7.4.0 (test framework)
- pytest-cov>=4.1.0 (coverage plugin)
- pytest-mock>=3.11.0 (mocking support)
- coverage>=7.3.0 (code coverage)

## Common Development Tasks

### Adding New Language Support
Add language mapping in `RepoPDFConverter.code_extensions` dictionary in repo-to-pdf.py:95-140

### Modifying Ignore Patterns
Edit the `ignores` section in config.yaml or add patterns to `RepoPDFConverter._should_ignore()` in repo-to-pdf.py

### Changing PDF Output Settings
Modify `pdf_settings` in config.yaml:
- `margin`: Page margins
- `main_font`: Primary font (default: "Songti SC" for Chinese)
- `mono_font`: Code font (default: "SF Mono")
- `highlight_style`: Pandoc highlight theme

### Debugging Conversion Issues
1. Run with `make debug` to see detailed logs
2. Check `debug.md` for the generated markdown
3. Review `temp_conversion_files/` for intermediate files
4. Common issues:
   - Missing fonts: Install specified fonts or update config.yaml
   - LaTeX errors: Check for special characters in code
   - Memory issues: Reduce file size limit or add more ignore patterns
   - **"Dimension too large" error**: This LaTeX error occurs when processing files with extremely long lines or large code blocks. Solutions implemented:
     - File size limit reduced from 1MB to 0.5MB for non-image files
     - Added `_process_long_lines()` method to break lines longer than 80 characters
     - Enhanced LaTeX header with `\small` font size and `etoolbox` patches
     - Automatic truncation of files with more than 1000 lines
     - Added `\maxdeadcycles=200` and `\emergencystretch=5em` to handle large content