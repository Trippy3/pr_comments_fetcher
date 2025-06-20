# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python tool for fetching GitHub pull request review comments using the GitHub API. The project provides two main CLI commands:
- `github-review-fetcher`: Fetch review comments from a single PR with thread structure analysis
- `bulk-review-fetcher`: Fetch review comments from multiple PRs with CSV export

The tool specializes in collecting comments from PR threads, with a focus on identifying and filtering non-parent comments (replies and issue comments).

## Package Management

This project uses `uv` for package management instead of pip/poetry:

```bash
# Install dependencies
uv sync

# Install with test dependencies  
uv sync --all-extras

# Run commands
uv run github-review-fetcher [args]
uv run bulk-review-fetcher [args]
```

## Development Commands

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov

# Run specific test file
uv run pytest src/tests/unit/test_github_review_comments_fetcher.py

# Generate HTML coverage report
uv run pytest --cov --cov-report=html
```

### Code Quality (using just)
```bash
# Check code quality
just check

# Format code
just fmt

# Run tests
just test
```

### Alternative (without just)
```bash
# Lint/check code
uvx ruff check

# Format code
uvx ruff check --fix
uvx ruff format
```

## Architecture

- `src/make_rule/github_review_comments_fetcher.py`: Core single PR fetching logic with GitHub API pagination, thread structure analysis, and comment filtering
- `src/make_rule/bulk_review_comments_fetcher.py`: Bulk PR fetching with CSV export and rate limiting
- `main.py`: Entry point showing available commands
- Test structure follows `src/tests/unit/` pattern with pytest fixtures in `conftest.py`

The fetcher classes handle GitHub API authentication, pagination, rate limiting, thread structure analysis, and data formatting into JSON/CSV outputs.

### Comment Types and Thread Structure

The `github_review_comments_fetcher.py` module handles three types of comments:

1. **Review Comments** (`/pulls/{pr}/comments`): Comments on specific code lines
   - Can have `in_reply_to_id` for thread replies
   - Include file path, line number, and commit information
   
2. **Issue Comments** (`/issues/{pr}/comments`): General PR-level comments
   - Always treated as independent comments
   - No file/line association
   
3. **Review Bodies**: Summary comments in review submissions
   - Processed as part of the review data structure

### Key Methods

- `get_review_comments()`: Fetches code review comments with pagination
- `get_issue_comments()`: Fetches PR-level discussion comments with pagination  
- `format_comment_info()`: Formats review comments with thread metadata
- `format_issue_comment_info()`: Formats issue comments with type identification

### Output Structure

The tool produces:
- `all_comments`: Complete list of all comments (review + issue)
- `target_comments`: Filtered list containing only non-parent comments:
  - Reply comments (review comments with `in_reply_to_id`)
  - All issue comments (PR-level discussions)

## Environment Variables

- `GITHUB_TOKEN`: GitHub Personal Access Token (required for API access)

## Key Features

- Supports both single and bulk PR comment fetching
- **Thread structure analysis and comment filtering**
- **Fetches both review comments and issue comments**
- **Identifies and filters non-parent comments (replies + discussions)**
- Handles GitHub API pagination automatically
- Includes rate limiting controls (`--delay` option)
- Exports data in JSON and CSV formats
- Provides detailed summary statistics including comment breakdowns
- Supports comment preview in terminal output