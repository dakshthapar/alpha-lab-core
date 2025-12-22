# Contributing to Alpha Lab Core

Thank you for your interest in contributing to **Alpha Lab Core**! 🎉

This project aims to provide high-quality synthetic market data for training algorithmic trading and reinforcement learning agents. We welcome contributions from the community!

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Contributing Code](#contributing-code)
- [Development Setup](#development-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Pull Request Process](#pull-request-process)
- [Community](#community)

---

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Please be respectful and constructive in all interactions.

---

## How Can I Contribute?

### Reporting Bugs

If you find a bug, please open an issue on GitHub with the following information:

1. **Clear Title**: Use a descriptive title (e.g., "Simulation crashes when `--cores` exceeds CPU count")
2. **Environment Details**:
   - OS (e.g., Ubuntu 22.04, Arch Linux, macOS)
   - Python version
   - GPU/CPU configuration
3. **Steps to Reproduce**: Provide exact commands or code snippets
4. **Expected vs Actual Behavior**: What you expected to happen vs what actually happened
5. **Error Messages**: Include full stack traces if applicable
6. **Sample Data**: If possible, provide a minimal dataset that reproduces the issue

**Example Bug Report:**
```
Title: regime_factory.py fails with KeyError when processing VOLATILE regime

Environment: Ubuntu 22.04, Python 3.10, CPU-only

Steps to Reproduce:
1. Run `python data_collection/simulation/regime_factory.py --test-mode`
2. Wait for VOLATILE regime simulation to start

Expected: Simulation completes successfully
Actual: KeyError: 'sigma_n' at line 142

Stack Trace:
<paste full error here>
```

---

### Suggesting Features

We love new ideas! Before suggesting a feature:

1. **Check Existing Issues**: Search to see if someone has already suggested it
2. **Provide Context**: Explain the use case and why it would be valuable
3. **Be Specific**: Describe the feature in detail with examples if possible

**Example Feature Request:**
```
Title: Add support for options market simulation

Description:
Currently, Alpha Lab Core only simulates equity markets. Adding options market 
simulation would allow training strategies that use derivatives for hedging.

Potential Implementation:
- Extend ABIDES to support option order books
- Add Black-Scholes pricing for option agents
- Create new regime types for high volatility option trading

Benefits:
- Enables testing of delta-hedged strategies
- Allows training on more complex market dynamics
```

---

### Contributing Code

We welcome code contributions! Here's how to get started:

1. **Fork the Repository** on GitHub
2. **Clone Your Fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/alpha-lab-core.git
   cd alpha-lab-core
   ```
3. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make Your Changes** following our [Code Style Guidelines](#code-style-guidelines)
5. **Test Your Changes** thoroughly
6. **Commit with Clear Messages**:
   ```bash
   git commit -m "Add support for intraday regime switching"
   ```
7. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** on the main repository

---

## Development Setup

Follow the [INSTALL_GUIDE.md](INSTALL_GUIDE.md) to set up your development environment.

**Additional Steps for Contributors:**

1. **Install Development Dependencies**:
   ```bash
   uv pip install pytest black flake8 mypy
   ```

2. **Run Tests** (if available):
   ```bash
   pytest tests/
   ```

3. **Format Code** before committing:
   ```bash
   black *.py
   ```

---

## Code Style Guidelines

To maintain code quality and readability:

### Python Style
- **Follow PEP 8**: Use standard Python conventions
- **Use Type Hints**: Add type annotations where possible
  ```python
  def process_data(file_path: str, regime: str) -> pd.DataFrame:
      ...
  ```
- **Docstrings**: Add docstrings for all functions and classes
  ```python
  def calculate_spread(bids: list, asks: list) -> float:
      """
      Calculate the bid-ask spread.
      
      Args:
          bids: List of bid prices
          asks: List of ask prices
          
      Returns:
          The spread in basis points
      """
      ...
  ```
- **Comments**: Add comments for complex logic, but prefer self-documenting code
- **Line Length**: Keep lines under 100 characters when possible
- **Naming Conventions**:
  - Functions and variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`

### File Organization
- **Imports**: Group imports into standard library, third-party, and local imports
  ```python
  # Standard library
  import os
  from pathlib import Path
  
  # Third-party
  import polars as pl
  import numpy as np
  
  # Local
  from libs.abides import MarketSimulator
  ```

### Performance Considerations
- **Use Polars over Pandas** for new code when handling large datasets
- **Use streaming operations** for large file merges:
  - Prefer `scan_parquet()` + `sink_parquet()` over `read_parquet()` + `write_parquet()`
  - This allows processing datasets larger than available RAM
  - Example: See `data_collection/processing/merge_batches.py` for streaming merge implementation
- **Data pipeline best practices**:
  - Use stratified splitting (`data_collection/processing/split_and_merge.py`) to maintain regime distribution
  - Always validate on a held-out validation set before touching test data
  - Consider OOD testing (`data_collection/processing/merge_ood.py`) for robustness evaluation
- **Avoid global variables** except for configuration constants
- **Profile before optimizing**: Use `cProfile` or `line_profiler` to identify bottlenecks

---

## Pull Request Process

1. **Ensure your PR**:
   - Addresses a single concern (bug fix, feature, refactor)
   - Includes clear commit messages
   - Updates relevant documentation
   - Passes all existing tests (if applicable)

2. **PR Description Should Include**:
   - **What**: Summary of changes
   - **Why**: Motivation and context
   - **How**: Technical approach
   - **Testing**: How you verified the changes work

3. **Review Process**:
   - A maintainer will review your PR within a few days
   - Address any requested changes
   - Once approved, a maintainer will merge your PR

4. **After Merge**:
   - Your contribution will be included in the next release
   - You'll be credited in the release notes

---

## Community

### Questions?
- **GitHub Discussions**: For general questions and discussions
- **GitHub Issues**: For bug reports and feature requests

### Recognition
Contributors will be acknowledged in:
- Release notes
- README.md (for significant contributions)

---

**Thank you for contributing to Alpha Lab Core!** 🚀

Your efforts help improve algorithmic trading research and education for everyone.
