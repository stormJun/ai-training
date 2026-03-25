# Repository Guidelines

This repository collects topic-based materials, assignments, and reference projects for the “AI 工程化训练营”. Each topic area is a mostly self-contained Python or notebook workspace.

## Project Structure & Module Organization

- `01_llm_api_and_tool_calling/` through `10_capstone_customer_service/`: primary learning tracks organized by knowledge topic rather than week number.
- `assignments/`: homework directories and curated example answers; avoid changing example solutions unless fixing a clear bug.
- `reference_projects/`: larger end-to-end applications and extension projects, typically organized into `core/`, `agents/`, `config/`, `tools/`, `scripts/`, or `app/`.
- `archive/`: historical experiments and non-primary materials kept for reference only.
- Work inside the relevant topic or project subdirectory; do not assume shared virtual environments across topics or projects.

## Build, Test, and Development Commands

- Typical setup pattern (per subproject):
  - `cd 04_workflow_orchestration/langchain_langgraph_foundations && uv sync --locked`
  - `cd 03_rag_and_retrieval/local_rag_project && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run apps from their own root, e.g. `python main.py` or `uvicorn main:app --reload` as documented in the local README.

## Coding Style & Naming Conventions

- Prefer Python 3.9+ with 4-space indentation, type hints, and module-level docstrings.
- Use `snake_case` for functions and variables, `PascalCase` for classes, and descriptive module names such as `core/`, `config/`, `tools/`, `agents/`, `apps/`, or `services/`.
- When available, format with `black`, lint with `flake8`, and run `mypy` before committing.

## Testing Guidelines

- Tests live under `tests/` within each subproject and commonly use `pytest` or `pytest-asyncio`.
- From a subproject root, run `pytest` or project-specific targets described in its README or `Makefile` such as `04_workflow_orchestration/langchain_langgraph_foundations/app/Makefile`.
- For new features, add tests that mirror existing patterns and keep them fast and deterministic; aim for meaningful coverage rather than a specific percentage.

## Commit & Pull Request Guidelines

- This copy has no shared Git history; follow a Conventional Commits-style prefix where possible, for example `feat: add RAG retry policy` or `fix: handle missing DASHSCOPE_API_KEY`.
- Keep commits focused and reversible; avoid mixing formatting with behavioral changes.
- Pull requests should include: motivation and scope, affected directory such as `06_dsl_and_rule_engines/` or `reference_projects/project2_2/`, setup or migration notes, and how to run tests; attach logs or screenshots for UI or API changes.

## Security & Configuration

- Never commit real API keys or secrets; keep them in `.env` files or environment variables.
- Use sample configuration files or clearly documented placeholders for credentials and endpoints.
