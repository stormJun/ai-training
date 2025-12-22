# Repository Guidelines

This repository collects weekly materials and reference projects for the “AI 工程化训练营”. Each week and project is a mostly self-contained Python (and notebook) workspace.

## Project Structure & Module Organization

- `week01`–`week10`: course notebooks, demos, and utilities; see each `weekXX/README.md`.
- `projects/`: larger end-to-end agent/RAG applications, typically organized into `core/`, `agents/`, `config/`, `tools/`, and `scripts/`.
- `homework_examples/`: curated homework solutions for reference only; avoid changing them unless fixing clear bugs.
- Work inside the relevant subdirectory; do not assume shared virtual environments across weeks or projects.

## Build, Test, and Development Commands

- Typical setup pattern (per subproject):
  - `cd week04 && uv sync --locked`
  - `cd week03-local-rag && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run apps from their own root, e.g. `python main.py` or `uvicorn main:app --reload` as documented in the local README.

## Coding Style & Naming Conventions

- Prefer Python 3.9+ with 4-space indentation, type hints, and module-level docstrings (see `projects/project1_1/core/logger.py`).
- Use `snake_case` for functions/variables, `PascalCase` for classes, and descriptive module names (`core/`, `config/`, `tools/`, `agents/`).
- When available, format with `black`, lint with `flake8`, and run `mypy` before committing.

## Testing Guidelines

- Tests live under `tests/` within each subproject and use `pytest` (often with `pytest-asyncio`).
- From a subproject root, run `pytest` or project-specific targets described in its README or `Makefile` (for example `week04/app/Makefile`).
- For new features, add tests that mirror existing patterns and keep them fast and deterministic; aim for meaningful coverage rather than a specific percentage.

## Commit & Pull Request Guidelines

- This copy has no shared Git history; follow a Conventional Commits-style prefix where possible (e.g. `feat: add RAG retry policy`, `fix: handle missing DASHSCOPE_API_KEY`).
- Keep commits focused and reversible; avoid mixing formatting with behavioral changes.
- Pull requests should include: motivation and scope, affected directory (e.g. `week06/` or `projects/project1_2/`), setup or migration notes, and how to run tests; attach logs or screenshots for UI or API changes.

## Security & Configuration

- Never commit real API keys or secrets; keep them in `.env` files or environment variables (e.g. `DASHSCOPE_API_KEY` in `week03-local-rag`).
- Use sample configuration files or clearly documented placeholders for credentials and endpoints.

