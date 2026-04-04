# Extension Topics Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Split non-memory extension materials out of topic 07 so `07_agent_memory_and_advanced_capabilities` only contains the memory-focused learning path.

**Architecture:** Keep topic 07 as the memory mainline, move extension materials into a new top-level `11_extension_topics` area, move RPA workflow materials into topic 04, and relocate the third-party fullstack quickstart into `third_party_sources`. Update repo navigation and topic README files to reflect the new structure.

**Tech Stack:** Markdown, Jupyter notebooks, shell file operations, repository README navigation

---

### Task 1: Create target directories

**Files:**
- Create: `11_extension_topics/`
- Create: `11_extension_topics/slm_optimization/`
- Create: `11_extension_topics/multimodal_clip_search/`
- Create: `11_extension_topics/reinforcement_learning/`
- Create: `04_workflow_orchestration/rpa_and_ai_workflow/`
- Create: `third_party_sources/`

### Task 2: Move extension topic materials out of topic 07

**Files:**
- Move: `07_agent_memory_and_advanced_capabilities/foundations/p32-SLM.ipynb`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/小型模型优化指南.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/模型优化技术深度解析.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/模型优化技术深度解析-第2部分-剪枝与蒸馏.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/CLIP图像搜索系统完全指南.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/Q-Learning强化学习完全指南.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/standalone_projects/p25-CLIP`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/standalone_projects/qlearn`

### Task 3: Move workflow and third-party project materials

**Files:**
- Move: `07_agent_memory_and_advanced_capabilities/foundations/RPA.py`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/RPA与AI工作流集成指南.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/RPA与AI工作流集成指南-第2部分.md`
- Move: `07_agent_memory_and_advanced_capabilities/foundations/standalone_projects/gemini-fullstack-langgraph-quickstart`

### Task 4: Rewrite topic navigation docs

**Files:**
- Modify: `README.md`
- Modify: `07_agent_memory_and_advanced_capabilities/foundations/README.md`
- Modify: `07_agent_memory_and_advanced_capabilities/foundations/TECH_DOC.md`
- Create: `11_extension_topics/README.md`
- Create: `11_extension_topics/slm_optimization/README.md`
- Create: `11_extension_topics/multimodal_clip_search/README.md`
- Create: `11_extension_topics/reinforcement_learning/README.md`
- Create: `04_workflow_orchestration/rpa_and_ai_workflow/README.md`

### Task 5: Fix moved-document path references and verify structure

**Files:**
- Modify: moved Markdown docs whose path examples still point to topic 07
- Verify: `find 07_agent_memory_and_advanced_capabilities 11_extension_topics 04_workflow_orchestration/rpa_and_ai_workflow third_party_sources -maxdepth 3`
- Verify: `rg -n "07_agent_memory_and_advanced_capabilities/foundations/standalone_projects/p25-CLIP|07_agent_memory_and_advanced_capabilities/foundations/RPA.py|07_agent_memory_and_advanced_capabilities/foundations/p32-SLM.ipynb|gemini-fullstack-langgraph-quickstart" .`
