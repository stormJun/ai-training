# LangGraph Topics Consolidation Design

## Goal

Consolidate the advanced LangGraph learning topics under `02_langgraph_basics/` so the repository presents a single, unified LangGraph learning area without duplicating content.

## Scope

This design covers the physical relocation of three existing topic directories:

- `21_langgraph_workflows/`
- `30_agent_protocols_and_mcp/31_mcp_langgraph_integration/`
- `30_agent_protocols_and_mcp/32_a2a_langgraph/`

They will be moved into `02_langgraph_basics/` while preserving each moved directory's existing internal structure and directory name.

## Target Structure

After the change, the repository structure will include:

- `02_langgraph_basics/05-2langgraph.py`
- `02_langgraph_basics/README.md`
- `02_langgraph_basics/21_langgraph_workflows/`
- `02_langgraph_basics/31_mcp_langgraph_integration/`
- `02_langgraph_basics/32_a2a_langgraph/`

The following old paths will no longer exist as standalone topic locations:

- `21_langgraph_workflows/`
- `30_agent_protocols_and_mcp/31_mcp_langgraph_integration/`
- `30_agent_protocols_and_mcp/32_a2a_langgraph/`

## Design Decisions

### 1. Preserve moved directory names

The moved directories will keep their original names:

- `21_langgraph_workflows`
- `31_mcp_langgraph_integration`
- `32_a2a_langgraph`

This minimizes risk during the move because it avoids unnecessary renaming of internal files, asset references, and project-local documentation.

### 2. Update navigation-level documentation

Documentation that acts as repository navigation or topic entry guidance will be updated to point to the new paths. This includes at least:

- repository root `README.md`
- `02_langgraph_basics/README.md`
- `30_agent_protocols_and_mcp/README.md`

Additional markdown files that explicitly describe these topics at the repository structure level may also be updated if they are clearly intended as active navigation documents rather than historical notes.

### 3. Do not mass-edit notebooks

Notebook files under `21_langgraph_workflows/` contain historical text and setup instructions that reference the old top-level path. This change will not rewrite notebook JSON in bulk.

Reasoning:

- bulk notebook edits create large, noisy diffs
- many path mentions are explanatory, historical, or output cells rather than active runtime logic
- the immediate user goal is repository consolidation, not notebook content normalization

### 4. Keep parent protocol directory intact

`30_agent_protocols_and_mcp/` will remain in place because it still groups other MCP/A2A materials. Its README will be adjusted so it no longer presents the moved LangGraph subtopics as residing directly inside that parent directory.

## Data and Path Handling

The move is a filesystem reorganization only. No application data format changes are required.

Path handling rules:

- move directories with `mv` so git can detect renames where possible
- update repository-level markdown references to the new locations
- avoid editing generated content, virtual environments, and runtime artifacts

## Risks

### 1. Stale internal path references

Some markdown and notebook content inside `21_langgraph_workflows/` will continue to mention the old path. This is an accepted limitation for this change set.

### 2. Broken manual navigation

Any repository document that explicitly points to the old paths could become misleading if not updated. This is why navigation-level README updates are part of scope.

### 3. Dirty worktree

The repository already has unrelated changes. This work must avoid reverting or disturbing user changes outside the targeted LangGraph paths and documentation files.

## Testing and Verification

Verification for this reorganization is lightweight and repository-structure focused:

1. Confirm the three source directories no longer exist at their old locations.
2. Confirm the three directories exist under `02_langgraph_basics/`.
3. Confirm updated README files reference the new paths.
4. Run targeted search queries for the moved top-level paths in active navigation documents to catch obvious stale references.

## Out of Scope

The following are explicitly out of scope for this task:

- renaming the moved directories to new semantic names
- rewriting notebook cell content in bulk
- updating every historical design document under `docs/plans/`
- changing code imports unless a moved file path is directly referenced by active repository documentation
- reorganizing other LangGraph-related projects such as `22_langgraph_service_apps/`, `23_langgraph_demo_project/`, or `16_customer_service_platform/`
