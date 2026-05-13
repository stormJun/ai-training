# Repository Guidelines

This repository collects numbered learning workspaces, grouped topic parents, assignments, and reference projects for the “AI 工程化训练营”. Most numbered topic directories represent one knowledge theme or one self-contained project, while a small number of closely related themes are grouped under a numbered parent directory.

## Project Structure & Module Organization

- The primary learning path is still organized with numbered directories, but some adjacent topics may now be grouped under a numbered parent such as `09_finetuning_and_data_processing/`, `13_rag_and_retrieval/`, `27_multi_agent_frameworks/`, or `30_agent_protocols_and_mcp/`.
- Some numbered directories are lightweight script or notebook workspaces.
- Some numbered directories remain full runnable projects, for example `13_rag_and_retrieval/16_local_rag_project/`, `13_rag_and_retrieval/17_qanything_case_study/`, `23_langgraph_demo_project/`, and `52_customer_service_platform/`.
- `assignments/`: homework directories and curated example answers; avoid changing example solutions unless fixing a clear bug.
- `reference_projects/`: larger end-to-end applications and extension projects, typically organized into `core/`, `agents/`, `config/`, `tools/`, `scripts/`, or `app/`.
- `archive/`: historical experiments and non-primary materials kept for reference only.
- `shared_assets/`: shared notes, migrated overview docs, and auxiliary non-topic-specific assets.
- `runtime_artifacts/`: local runtime outputs, moved virtual environments, indexes, caches, or other generated assets that should not define the learning structure.

## Build, Test, and Development Commands

- Work from the relevant topic or project root instead of assuming a single shared environment.
- Typical setup patterns:
  - `cd 40_fastapi_llm_serving && uv sync --locked`
  - `cd 13_rag_and_retrieval/16_local_rag_project/local_rag_project && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
  - `cd 23_langgraph_demo_project/langgraph_demo_project && uv sync --locked`
- Script-only topics may rely on dependency anchors kept in nearby overview directories such as `01_environment_setup/`, `09_finetuning_and_data_processing/09_finetuning_overview/`, `13_rag_and_retrieval/13_llamaindex_retrieval_basics/`, `18_prompt_templates/`, `27_multi_agent_frameworks/27_autogen_two_agent_chat/`, `33_dsl_design_basics/`, `36_memory_patterns_basics/`, `40_fastapi_llm_serving/`, and `47_asyncio_and_gil_basics/`.
- Run apps from their own root, for example `python main.py` or `uvicorn main:app --reload`, as documented in the local README or project files.

## Coding Style & Naming Conventions

- Prefer Python 3.9+ with 4-space indentation, type hints, and module-level docstrings.
- Use `snake_case` for functions and variables, `PascalCase` for classes, and descriptive module names such as `core/`, `config/`, `tools/`, `agents/`, `apps/`, or `services/`.
- When available, format with `black`, lint with `flake8`, and run `mypy` before committing.

## Testing Guidelines

- Tests live under `tests/` within each subproject and commonly use `pytest` or `pytest-asyncio`.
- From a subproject root, run `pytest` or project-specific targets described in its README or `Makefile`.
- For new features, add tests that mirror existing patterns and keep them fast and deterministic; aim for meaningful coverage rather than a specific percentage.

## Commit & Pull Request Guidelines

- Follow a Conventional Commits-style prefix where possible, for example `feat: add RAG retry policy` or `fix: handle missing DASHSCOPE_API_KEY`.
- Keep commits focused and reversible; avoid mixing formatting with behavioral changes.
- Pull requests should include: motivation and scope, affected directory such as `35_dsl_agent_and_db_gateway/` or `reference_projects/project2_2/`, setup or migration notes, and how to run tests; attach logs or screenshots for UI or API changes.

## Security & Configuration

- Never commit real API keys or secrets; keep them in `.env` files or environment variables.
- Use sample configuration files or clearly documented placeholders for credentials and endpoints.
