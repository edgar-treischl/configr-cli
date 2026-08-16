.PHONY: help install sync lint format test clean build docs run

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using UV
	uv sync

install-cli: ## Install configr-cli system-wide using pipx
	pipx install .

uninstall-cli: ## Uninstall configr-cli from system
	pipx uninstall configr-cli

sync: install ## Alias for install

lint: ## Run pre-commit linting
	pre-commit run --all-files

format: ## Format code with Black
	uv run black configr_cli tests

test: ## Run pytest test suite
	uv run pytest -v

test-quick: ## Run pytest with minimal output
	uv run pytest -q

test-coverage: ## Run pytest with coverage report
	uv run pytest --cov=configr_cli --cov-report=term-showing-missing

build-docs: ## Build documentation with mkdocs
	uv run great-docs build
	uv run great-docs preview

run: ## Run the CLI
	uv run configr --help

clean: ## Remove build artifacts, cache, and lock files
	rm -rf build dist *.egg-info __pycache__ .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-all: clean ## Clean all including UV artifacts
	rm -rf .venv uv.lock

dev-setup: install pre-commit-install ## Setup development environment

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

check: lint test ## Run linting and tests

all: install lint test build-docs ## Run full pipeline (install, lint, test, docs)
