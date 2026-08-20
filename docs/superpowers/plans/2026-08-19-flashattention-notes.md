# FlashAttention Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Transformer notes with a source-oriented FlashAttention explanation at the same depth as the existing SwiGLU section.

**Architecture:** Keep the material in the Stage 2 Attention walkthrough. Add a standalone section between GQA and Mask so the algorithm, PyTorch SDPA dispatch, and MiniMind execution paths remain distinct but adjacent.

**Tech Stack:** Markdown, LaTeX, Python/PyTorch source excerpts

## Global Constraints

- Modify the existing notes without changing `minimind-master` source code.
- Distinguish the SDPA API from the FlashAttention backend.
- Describe MiniMind's checked-in implementation exactly as it exists at `model/model_minimind.py:21,109,125-131`.
- Preserve the document's existing Chinese teaching style and source-reference convention.
- Do not claim that `flash_attn=True` guarantees a FlashAttention kernel.
- Do not commit changes unless the user explicitly requests a commit.

---

### Task 1: Add the FlashAttention walkthrough

**Files:**
- Modify: `05a_deep_learning_architecture/transformer笔记.md:337-411`

**Interfaces:**
- Consumes: MiniMind's `MiniMindConfig.flash_attn`, `Attention.self.flash`, SDPA branch, and manual Attention fallback.
- Produces: A self-contained explanation linked to the surrounding GQA and Mask sections.

- [x] **Step 1: Make the displayed Attention code match both execution branches**

Add `self.flash`, the SDPA condition, and the manual fallback to the existing source excerpt. Preserve the Q/K/V, RoPE, GQA, mask, Softmax, and output-projection lines.

- [x] **Step 2: Explain ordinary Attention's memory traffic**

Show that a straightforward implementation materializes `scores` and `probs` with shape `[B,H,T,T]`, and explain why their storage grows quadratically with sequence length.

- [x] **Step 3: Explain FlashAttention's tiled online Softmax**

Describe loading Q/K/V blocks into on-chip memory, maintaining running maximum `m`, exponential sum `l`, and accumulated output `O`, and rescaling previous partial results when the maximum changes. State that it is exact Attention up to floating-point ordering, retains quadratic arithmetic complexity, and primarily reduces high-bandwidth-memory traffic and intermediate activation storage.

- [x] **Step 4: Map the principle to MiniMind and PyTorch SDPA**

Document that `flash_attn=True` only enables the SDPA branch, while PyTorch selects the actual FlashAttention, another fused implementation, or math backend according to runtime support. State that MiniMind has no direct `flash-attn` package dependency.

- [x] **Step 5: Add a MiniMind execution-path table**

Cover unpadded full-sequence training, unpadded prompt prefill, padded input, historical KV Cache, and single-token decoding. Keep causal-mask behavior consistent with the existing Mask section.

- [x] **Step 6: Separate related optimizations**

Add a compact comparison of GQA, FlashAttention, KV Cache, and causal mask by the problem each one solves.

### Task 2: Synchronize summaries and verify the document

**Files:**
- Modify: `05a_deep_learning_architecture/transformer笔记.md:721-736`
- Modify: `05a_deep_learning_architecture/transformer笔记.md:1097-1104`

**Interfaces:**
- Consumes: Terminology established in Task 1.
- Produces: Summary rows that do not equate SDPA with FlashAttention.

- [x] **Step 1: Update Stage 2 summaries**

Replace generic SDPA wording with `PyTorch SDPA; eligible inputs may dispatch to a FlashAttention kernel` and retain the hand-written fallback.

- [x] **Step 2: Run focused terminology checks**

Run:

```bash
rg -n -i 'flash|sdpa|scaled_dot_product_attention' '05a_deep_learning_architecture/transformer笔记.md'
```

Expected: Every FlashAttention claim distinguishes the algorithm/backend from the SDPA interface.

- [x] **Step 3: Check formatting and source references**

Run:

```bash
git diff --check -- '05a_deep_learning_architecture/transformer笔记.md'
git diff -- '05a_deep_learning_architecture/transformer笔记.md'
```

Expected: `git diff --check` exits 0; the diff changes only the approved FlashAttention material in addition to the user's pre-existing edits.
