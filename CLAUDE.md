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

# Use device presets for optimized reading
make kindle             # 7-inch Kindle optimization
make tablet             # Tablet device optimization  
make mobile             # Mobile device optimization
make desktop            # Desktop optimization (default)

# Use device preset via environment variable
DEVICE=kindle7 make

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
   - `RepoPDFConverter`: Core conversion logic with template support and device preset integration
   - `get_system_fonts()`: Cross-platform font detection
   - `get_device_presets()`: Device-specific configuration presets (desktop, kindle7, tablet, mobile)
   - `_apply_device_preset()`: Applies device-specific settings based on environment or config
   - `generate_directory_tree()`: Visual project structure generation
   - `generate_code_stats()`: Code statistics and language analysis
   - Smart file filtering and size management (0.5MB default limit)
   - SVG to PNG conversion using CairoSVG
   - Remote image downloading and embedding
   - Syntax highlighting for 30+ programming languages
   - Progress bar integration with tqdm
   - Stream processing to avoid memory issues
   - `_process_large_file()`: Intelligent file splitting for files over 1000 lines
     - Splits into 800-line chunks with proper code block formatting
     - Preserves syntax highlighting by ensuring newlines around code markers
   - `_process_long_lines()`: Line breaking for lines over 80 characters
   - `_break_long_strings()`: Smart string breaking for long literals

2. **Makefile**: Comprehensive build automation:
   - OS detection (macOS/Linux) with automatic dependency installation
   - Python virtual environment management
   - Colored output with multiple verbosity levels
   - Homebrew integration for macOS dependencies
   - Device preset shortcuts (`make kindle`, `make tablet`, etc.)
   - Environment variable support for device presets (`DEVICE=kindle7`)

3. **config.yaml**: User configuration:
   - Repository URL and branch specification
   - Output directories and PDF settings
   - Device preset configuration (`device_preset`, `device_presets`)
   - Extensive ignore patterns for build artifacts
   - Font and styling customization with device-specific overrides

4. **templates/**: Template system for custom PDF structures:
   - `default.yaml`: Standard code documentation template
   - `technical.yaml`: Technical documentation template with file type grouping
   - `kindle.yaml`: 7-inch Kindle optimized template with compact layout
   - Support for custom sections, statistics, and styling
   - Device-specific font sizes and layout optimizations

### Conversion Pipeline

1. Apply device preset configuration (if specified via DEVICE env var or config)
2. Clone/update target repository (shallow clone with `--depth=1`)
3. Walk repository tree, filtering by ignore patterns
4. Process each file:
   - Convert SVG images to PNG for PDF compatibility
   - Download and embed remote images
   - Apply syntax highlighting to code files
   - Handle HTML to Markdown conversion
5. Combine all content into single Markdown file
6. Generate PDF using Pandoc with XeLaTeX backend and device-optimized settings

### Key Technical Details

- **Device Presets**: Configurable device-specific settings for optimal reading experience
  - Desktop: Standard layout with 10pt fonts and 1-inch margins
  - Kindle7: Compact layout with 8pt fonts, `\scriptsize` code, and 0.4-inch margins
  - Tablet: Medium layout with 9pt fonts and 0.6-inch margins  
  - Mobile: Ultra-compact with 7pt fonts and 0.3-inch margins
- **Image Handling**: Automatic SVG to PNG conversion, remote image downloading with caching
- **Text Processing**: Smart handling of Chinese text, LaTeX special character escaping
- **File Management**: Respects .gitignore, applies extensive default ignore patterns
- **Performance**: Shallow git clones, 0.5MB file size limit, efficient directory traversal
- **Logging**: Three-tier logging system (normal, verbose, quiet) controlled via make parameters
- **YAML Handling**: Custom YAML dumper class for proper backslash escaping, separate header.tex file approach
- **Markdown Processing**: Escapes "---" lines to prevent YAML delimiter confusion, removes yaml_metadata_block from pandoc format
- **Pandoc Configuration**: Disables raw_tex extension to prevent backslash interpretation issues in code blocks

## Important Paths

- Working directory: `repo-workspace/` (gitignored)
- Output PDFs: `repo-pdfs/` (gitignored)
- Temporary files: `temp_conversion_files/`
- Virtual environment: `venv/` (gitignored)

## Dependencies

### System Requirements
- Python 3.6+
- pandoc
- XeLaTeX (via MacTeX on macOS, texlive-xetex on Linux)
- texlive-lang-greek (required for proper Greek character support in LaTeX)
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

## Quick Troubleshooting Guide

| Error | Solution |
|-------|----------|
| Font not found | Update config.yaml with system-appropriate fonts or install missing fonts |
| YAML parse exception | Check temp_conversion_files/header.tex was created properly |
| Undefined control sequence | Ensure pandoc is using `-raw_tex` flag |
| Dimension too large | Check if files over 1000 lines are being split properly |
| puenc-greek.def not found | Install texlive-lang-greek package |
| File too large | Reduce file size limit in code or enable split_large_files |

## Common Development Tasks

### Adding New Language Support
Add language mapping in `RepoPDFConverter.code_extensions` dictionary in repo-to-pdf.py:95-140

### Modifying Ignore Patterns
Edit the `ignores` section in config.yaml or add patterns to `RepoPDFConverter._should_ignore()` in repo-to-pdf.py

### Changing PDF Output Settings
Modify `pdf_settings` in config.yaml:
- `margin`: Page margins
- `main_font`: Primary font (default: "Songti SC" for Chinese on macOS, "Noto Serif CJK SC" on Linux)
- `mono_font`: Code font (default: "SF Mono" on macOS, "DejaVu Sans Mono" on Linux)
- `fontsize`: Document font size (e.g., "10pt", "8pt")
- `code_fontsize`: Code block font size (e.g., "\\small", "\\scriptsize", "\\tiny")
- `linespread`: Line spacing multiplier (e.g., "1.0", "0.9")
- `parskip`: Paragraph spacing (e.g., "6pt", "3pt")
- `highlight_style`: Pandoc highlight theme
- `split_large_files`: Whether to split large files into parts (default: true)

### Using Device Presets
Set device preset in config.yaml or use environment variable:
```yaml
device_preset: "kindle7"  # or desktop, tablet, mobile
```
Or use make shortcuts:
```bash
make kindle    # Kindle 7-inch optimization
make tablet    # Tablet optimization  
make mobile    # Mobile optimization
make desktop   # Desktop optimization (default)
```
Or use environment variable:
```bash
DEVICE=kindle7 make
```

### Debugging Conversion Issues
1. Run with `make debug` to see detailed logs
2. Check `debug.md` for the generated markdown
3. Review `temp_conversion_files/` for intermediate files
4. Common issues:
   - **Missing fonts**: Install specified fonts or update config.yaml
     - macOS defaults: "Songti SC" (main), "SF Mono" (mono)
     - Linux/WSL defaults: "Noto Serif CJK SC" (main), "DejaVu Sans Mono" (mono)
     - The tool automatically detects the OS and suggests appropriate fonts
   - **LaTeX errors**: Check for special characters in code
     - "File 'puenc-greek.def' not found" error: Install `texlive-lang-greek` package
     - On Ubuntu/Debian: `sudo apt-get install texlive-lang-greek`
     - This package is required for proper Greek character support in LaTeX documents
   - Memory issues: Reduce file size limit or add more ignore patterns
   - **YAML parsing errors with pandoc**: When pandoc fails with YAML parse exceptions, the issue is often related to how pandoc defaults files handle LaTeX commands. Solutions implemented:
     - Moved from inline `header-includes` in YAML to separate `header.tex` file using `include-in-header`
     - Created custom YAML dumper class to properly quote strings containing backslashes
     - Removed `yaml_metadata_block` from pandoc input format to avoid parsing conflicts
     - Escape "---" lines in markdown files to prevent them being interpreted as YAML delimiters
     - Use file paths instead of inline content for LaTeX headers in pandoc defaults
   - **"Undefined control sequence" errors**: When LaTeX encounters backslashes in code, it may interpret them as commands. Solution:
     - Disabled `raw_tex` extension in pandoc input format (`-raw_tex`) to prevent backslashes being interpreted as LaTeX commands
     - This ensures code blocks are properly handled without manual escaping
   - **"Dimension too large" error**: This LaTeX error occurs when processing files with extremely long lines or large code blocks. Solutions implemented:
     - File size limit reduced from 1MB to 0.5MB for non-image files
     - Added `_process_long_lines()` method to break lines longer than 80 characters
     - Enhanced LaTeX header with `\small` font size and `etoolbox` patches
     - Intelligent file splitting: Files with more than 1000 lines are split into multiple parts (800 lines each) instead of truncation
     - Added `\maxdeadcycles=200` and `\emergencystretch=5em` to handle large content
     - Each part is clearly labeled with line numbers for easy reference
   - **Code block formatting in split files**: When large files are split into parts, ensure proper syntax highlighting:
     - Code blocks must have newlines after the opening marker: `` `````python\n``
     - Code blocks must have newlines before the closing marker: ``\n````` ``
     - This ensures pandoc correctly applies syntax highlighting to each part
   - **Absolute path images in Markdown**: When Markdown files contain images with absolute paths (starting with `/`), these are treated as relative to the repository root:
     - Example: `![](/docs/assets/image.png)` is resolved as `{repo_root}/docs/assets/image.png`
     - The leading slash is stripped and the path is resolved relative to the repository root
     - This fix ensures compatibility with documentation that uses absolute paths for images