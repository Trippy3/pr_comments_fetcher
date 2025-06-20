# List the available recipes
default:
  @just --list

# Check for code quality and type errors
check:
  uvx ruff check

# Format the code
fmt:
  uvx ruff check --fix
  uvx ruff format

# pytest
test:
  uv run pytest
