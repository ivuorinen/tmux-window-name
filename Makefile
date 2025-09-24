.DEFAULT_GOAL := help

UV ?= UV_CACHE_DIR=.uv-cache UV_TOOL_DIR=.uv-tools uv
PYTEST ?= $(UV) run --with . --with '.[dev]' pytest -p pytest_cov $(PYTEST_ARGS)
PRECOMMIT_ARGS ?= --all-files

export UV_CACHE_DIR ?= .uv-cache
export UV_TOOL_DIR ?= .uv-tools

.PHONY: help install test coverage format check lint typecheck precommit precommit-install precommit-autoupdate clean

help: ## Show available Makefile targets
	@echo "Available commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*##' Makefile | awk -F':.*##' '{printf "  %-20s %s\n", $$1, $$2}'

install: ## Sync development dependencies with uv
	$(UV) sync --all-extras

test: ## Run the full pytest suite
	$(PYTEST)

coverage: ## Run tests with coverage reporting
	$(PYTEST)

format: ## Format Python sources using ruff
	$(UV) run --with '.[dev]' ruff format

check: ## Lint Python sources and apply auto-fixes using ruff
	$(UV) run --with '.[dev]' ruff check . --no-cache --fix

lint: ## Lint Python sources without modifications
	$(UV) run --with '.[dev]' ruff check . --no-cache

typecheck: ## Run mypy type checks
	$(UV) run --with '.[dev]' mypy scripts

precommit: ## Run pre-commit on all files
	$(UV) run --with '.[dev]' pre-commit run $(PRECOMMIT_ARGS)

precommit-install: ## Install pre-commit hooks locally
	$(UV) run --with '.[dev]' pre-commit install
	$(UV) run --with '.[dev]' pre-commit install --hook-type commit-msg
	$(UV) run --with '.[dev]' pre-commit install --hook-type pre-push

precommit-autoupdate: ## Update pre-commit hooks to latest versions
	$(UV) run --with '.[dev]' pre-commit autoupdate

clean: ## Remove cached Python and coverage artifacts
	rm -rf .mypy_cache .pytest_cache htmlcov coverage.xml
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
