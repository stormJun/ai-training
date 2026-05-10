# Lecturer Transcripts To Markdown Design

## Goal

Convert the two lecturer transcript text files under `06_langgraph_basics/21_langgraph_workflows/` into readable Markdown documents that preserve the lecturer's meaning while improving readability for study.

## In Scope

The work applies to these two source files:

- `06_langgraph_basics/21_langgraph_workflows/02_工作流编排_讲师文稿.txt`
- `06_langgraph_basics/21_langgraph_workflows/03_工作流编排_讲师笔记.txt`

The result will add two Markdown companions:

- `06_langgraph_basics/21_langgraph_workflows/02_工作流编排_讲师文稿.md`
- `06_langgraph_basics/21_langgraph_workflows/03_工作流编排_讲师笔记.md`

The original `.txt` files will remain in place.

## Chosen Approach

Use a middle-ground editorial pass:

- preserve the lecturer's original meaning and ordering
- keep the material recognizably as lecture transcript content
- improve readability through structure and light cleanup

This is not a literal transcript dump, and it is not a rewritten study guide. It sits between those extremes.

## Editing Rules

### 1. Preserve meaning and sequence

- Do not change the core claims, examples, or teaching sequence.
- Do not insert new concepts or outside explanations.
- Do not reinterpret the content into a different structure than the lecture flow.

### 2. Add Markdown structure

- Add a top-level title reflecting the file name.
- Split long transcript text into readable paragraphs.
- Promote obvious topic changes into Markdown headings such as `##` and `###`.
- Convert enumerations, steps, comparisons, and repeated examples into flat Markdown lists when the transcript clearly expresses list-like content.

### 3. Compress obvious oral filler

Allow light cleanup of repeated spoken filler that harms readability, such as:

- `呃`
- `啊`
- `是吧`
- `那这边`
- `我们说了`

Rules:

- remove or compress repeated filler when it does not carry meaning
- keep filler when it changes tone or emphasis in a way that helps preserve the lecturer's intent
- do not over-clean into formal prose

### 4. Merge repeated adjacent phrasing

If the transcript repeats the same short phrase back-to-back due to spoken rhythm or speech recognition artifacts, merge it into one readable expression.

Examples of allowed cleanup:

- duplicated transition phrases
- repeated short setup clauses
- obvious speech-recognition duplication

### 5. Keep transcript character

The output should still read like a cleaned lecture transcript, not a polished article.

That means:

- preserve first-person teaching style where present
- preserve examples and rhetorical flow
- preserve interactive teaching moments when understandable

## File Format

Each generated Markdown file should:

1. start with a `#` title matching the transcript theme
2. use `##` for major topic shifts
3. use `###` for subtopics only when clearly justified
4. prefer short paragraphs over huge text blocks
5. use flat bullet lists where the speaker is clearly enumerating points

## Out of Scope

The following are not part of this task:

- deleting the original `.txt` files
- converting the transcripts into formal written articles
- turning them into concise summary notes
- adding new knowledge, references, or explanations
- normalizing every spoken sentence into standard written Chinese
- rewriting unrelated files in `21_langgraph_workflows/`

## Risks

### 1. Over-editing

If cleanup goes too far, the result stops feeling like the original lecture and becomes a rewritten article. This must be avoided.

### 2. Under-editing

If cleanup is too conservative, the output remains difficult to read and fails the study-use goal.

### 3. Ambiguous section boundaries

Spoken transcripts do not always have crisp transitions, so section headings require judgment. The heading pass should stay conservative and follow explicit topical shifts.

## Verification

The result is considered successful if:

1. both `.md` files exist beside the original `.txt` files
2. the content is easier to scan than the raw transcript
3. the lecturer's meaning and ordering are preserved
4. filler and repeated phrases are visibly reduced
5. the files read as cleaned transcripts, not rewritten notes
