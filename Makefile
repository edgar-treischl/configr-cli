.DEFAULT_GOAL := help

.PHONY: help install sync lock upgrade cli tool-install build test lint docs docs-serve

help:
	@echo configr-cli development commands
	@echo   make install       Install locked dependencies
	@echo   make sync          Update the environment from pyproject.toml
	@echo   make lock          Refresh uv.lock without upgrading packages
	@echo   make upgrade       Upgrade locked dependencies and sync
	@echo   make cli           Show the local configr CLI help
	@echo   make tool-install  Install configr as an isolated CLI tool
	@echo   make build         Build the wheel and source distribution
	@echo   make test          Run all tests; use TEST=path::test for one
	@echo   make lint          Run all pre-commit hooks
	@echo   make docs          Build documentation with strict checks
	@echo   make docs-serve    Serve documentation locally

install:
	uv sync --locked

sync:
	uv sync

lock:
	uv lock

upgrade:
	uv lock --upgrade
	uv sync

cli:
	uv run configr --help

tool-install:
	uv tool install --force .

build:
	uv build

test:
	uv run pytest $(TEST)

lint:
	uv run pre-commit run --all-files

docs:
	uv run mkdocs build --strict

docs-serve:
	uv run mkdocs serve
