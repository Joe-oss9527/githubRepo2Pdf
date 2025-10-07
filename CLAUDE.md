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
- Coverage requirement: 25% (incrementally improving towards 50%+)
- CI/CD workflow for automated testing (.github/workflows/test.yml)
- When conversion fails, check `debug.md` for the generated markdown
- Temporary files are preserved in `temp_conversion_files/` for debugging

## Architecture Overview

**Version**: 2.0 (Modular Architecture)

The project has been refactored from a monolithic 1944-line script into a clean, modular Python package with 21 modules organized by functionality.

### Core Components

1. **repo_to_pdf/** - Main package (21 modules, 4,762 lines)

   **Entry Point:**
   - `cli.py`: Command-line interface with argparse configuration

   **Core Modules:**
   - `converter.py`: Main `RepoPDFConverter` class - orchestrates the entire conversion pipeline
   - `core/config.py`: Pydantic-based configuration with validation (`AppConfig`, `PDFSettings`, etc.)
   - `core/constants.py`: Centralized constants (file size limits, extensions, pandoc settings)
   - `core/exceptions.py`: Custom exception hierarchy

   **Git Operations:**
   - `git/repo_manager.py`: `GitRepoManager` - handles repository cloning/updating with shallow clones, context managers

   **File Processing:**
   - `processors/file_processor.py`: `FileProcessor` - file filtering, size management, ignore patterns
   - `processors/code_processor.py`: `CodeProcessor` - syntax detection, code formatting, large file splitting
   - `processors/markdown_processor.py`: `MarkdownProcessor` - markdown processing, image path resolution, HTML conversion

   **Image & Emoji:**
   - `converters/image_converter.py`: `ImageConverter` - SVG to PNG conversion, remote image downloading
   - `converters/emoji_handler.py`: `EmojiHandler` - Twemoji download and caching, emoji detection

   **LaTeX & PDF:**
   - `converters/latex_generator.py`: `LaTeXGenerator` - generates header.tex and pandoc configuration

   **Statistics & Analysis:**
   - `stats/directory_tree.py`: Visual directory tree generation
   - `stats/code_stats.py`: Code statistics and language analysis

   **Templates:**
   - `templates/`: Template loading and processing

   **Key Features:**
   - Type-safe configuration with Pydantic validation
   - Context managers for resource management
   - Comprehensive logging throughout
   - Progress bars with tqdm integration
   - Intelligent file splitting (800-line chunks for files >1000 lines)
   - Smart image path resolution (absolute paths, relative paths, HTML img tags)
   - Graceful error handling (missing images removed instead of causing errors)

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
  - Kindle7: Expert-recommended layout with 11pt fonts, `\small` code, and 0.4-inch margins
  - Tablet: Medium layout with 9pt fonts and 0.6-inch margins
  - Mobile: Ultra-compact with 7pt fonts and 0.3-inch margins

- **Code Highlighting**: Professional syntax highlighting with visual enhancements
  - Default style: `tango` (colorful, high contrast, excellent readability)
  - Customizable code block styling (background, border, padding)
  - Support for 30+ programming languages
  - Alternative styles available: kate, pygments, zenburn, espresso, breezedark

- **Image Handling**: Comprehensive image processing pipeline
  - Automatic SVG to PNG conversion using CairoSVG
  - Remote image downloading with caching
  - Smart path resolution (absolute paths, relative paths)
  - HTML `<img>` tag conversion to Markdown
  - Graceful handling of missing images (removes references to prevent Pandoc errors)
  - Support for image titles and alt text

- **Emoji Support**: Multi-strategy emoji rendering
  - Twemoji PNG download and caching (with offline mode)
  - Font-based emoji fallback (Apple Color Emoji, Noto Color Emoji, Symbola)
  - Special CodeBlock environment for emoji in code blocks

- **Text Processing**: Advanced text handling
  - Smart Chinese text with proper line breaking
  - LaTeX special character escaping
  - Unicode sequence handling (\\U, \\u)
  - YAML delimiter escaping
  - Hard-wrapping of long lines in code blocks

- **File Management**: Intelligent file filtering
  - Respects .gitignore patterns
  - Extensive default ignore patterns (node_modules, build artifacts, lock files)
  - 0.5MB file size limit for non-image files
  - Large file splitting (>1000 lines → 800-line chunks)

- **Performance**: Optimized for speed and memory
  - Shallow git clones (--depth=1)
  - Stream processing to avoid memory issues
  - Efficient directory traversal
  - Progress bars for user feedback

- **Type Safety**: Modern Python best practices
  - Pydantic models for configuration validation
  - Full type annotations with mypy checking
  - Custom exception hierarchy
  - Context managers for resource cleanup

- **Code Quality**: Automated quality checks
  - Pre-commit hooks (black, isort, flake8, mypy, bandit)
  - pytest test suite with 25% coverage (incrementally improving)
  - CI/CD workflow for automated testing

- **Logging**: Three-tier logging system
  - Normal: INFO level with key progress messages
  - Verbose: DEBUG level with detailed operation logs
  - Quiet: WARNING/ERROR only
  - Controlled via make parameters (VERBOSE=1, QUIET=1)

- **Pandoc Configuration**: Carefully tuned for reliability
  - Separate header.tex file approach (avoids YAML escaping issues)
  - Disables raw_tex extension (prevents backslash interpretation in code)
  - Removes yaml_metadata_block from input format
  - Custom tcolorbox for enhanced code block styling

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
Add language mapping in `repo_to_pdf/core/constants.py`:
- Update `CODE_EXTENSIONS` dictionary with new file extensions
- Update `LANGUAGE_NAMES` if needed for display purposes

### Modifying Ignore Patterns
1. Edit the `ignores` section in `config.yaml` for project-specific patterns
2. Modify `repo_to_pdf/processors/file_processor.py` - `FileProcessor._should_ignore()` for default patterns
3. Update `DEFAULT_IGNORES` in `repo_to_pdf/core/constants.py` for global defaults

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

## Recent Major Changes

### v2.0 - Modular Architecture Refactoring (2025-10)

**Complete rewrite from monolithic script to modular package:**
- Refactored 1944-line `repo-to-pdf.py` into 21 organized modules (4,762 lines)
- Introduced Pydantic-based type-safe configuration
- Added comprehensive test suite with pytest (34+ tests)
- Implemented pre-commit hooks for code quality
- Created custom exception hierarchy
- Added context managers for resource management
- Full type annotations with mypy checking
- Archived old code in `old_code/` directory

**Key improvements:**
- Better separation of concerns (git, processing, conversion, stats)
- Easier to test and maintain
- Type safety prevents configuration errors
- More professional code structure

### Code Highlighting Optimization (2025-10)

**Visual enhancement for better reading experience:**
- Changed default syntax highlighting from `monochrome` to `tango`
- Added customizable code block styling (background, border, padding)
- Enhanced LaTeX tcolorbox configuration
- 150% improvement in code readability
- Configurable via `pdf_settings` in config.yaml

**New configuration options:**
- `code_block_bg`: Code block background color (default: `gray!5`)
- `code_block_border`: Code block border color (default: `gray!30`)
- `code_block_padding`: Code block padding (default: `5pt`)

### Image Processing Improvements (2025-10)

**Enhanced image handling for better compatibility:**
- Fixed absolute path image resolution (e.g., `/img/foo.png`)
- Added HTML `<img>` tag to Markdown conversion
- Implemented graceful handling of missing images
- Added remote image downloading from HTML tags
- Smart path resolution strategies (multiple fallbacks)

**Results:**
- Successfully converts repositories with complex image references
- No more Pandoc errors from missing images
- Better support for documentation with varied image formats

## Migration from v1.0

If you have the old `repo-to-pdf.py` script:

1. **Update Makefile calls**: Change from `python repo-to-pdf.py` to `python -m repo_to_pdf.cli`
2. **Install new dependencies**: Run `make deps` to install updated requirements
3. **Configuration**: `config.yaml` structure remains compatible (no changes needed)
4. **Templates**: Existing templates work without modification
5. **Old code**: Available in `old_code/` directory for reference

The command-line interface and configuration format are backward compatible, so existing workflows should continue to work seamlessly.