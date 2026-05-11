#!/usr/bin/env python3
"""Convert Jupyter notebooks to Markdown and Python without third-party deps."""

from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path
from typing import Iterable


IMAGE_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
    "image/gif": ".gif",
}


def ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def normalize_source(source: str | list[str]) -> str:
    if isinstance(source, list):
        return "".join(source)
    return source


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def write_text(path: Path, text: str) -> None:
    path.write_text(ensure_trailing_newline(text), encoding="utf-8")


def save_binary_asset(assets_dir: Path, filename: str, payload: str, *, is_base64: bool) -> Path:
    assets_dir.mkdir(parents=True, exist_ok=True)
    target = assets_dir / filename
    if is_base64:
        target.write_bytes(base64.b64decode(payload))
    else:
        target.write_text(payload, encoding="utf-8")
    return target


def replace_markdown_attachments(text: str, attachments: dict, assets_dir: Path, cell_index: int) -> str:
    updated = text
    for attachment_name, attachment_data in attachments.items():
        mime_type, payload = next(iter(attachment_data.items()))
        suffix = IMAGE_MIME_TYPES.get(mime_type, ".bin")
        safe_name = sanitize_filename(f"markdown_{cell_index}_{attachment_name}")
        filename = f"{safe_name}{suffix if not safe_name.endswith(suffix) else ''}"
        asset = save_binary_asset(
            assets_dir,
            filename,
            payload,
            is_base64=not mime_type.endswith("svg+xml"),
        )
        updated = updated.replace(f"attachment:{attachment_name}", asset.parent.name + "/" + asset.name)
    return updated


def format_stream_output(output: dict) -> str:
    text = normalize_source(output.get("text", ""))
    return f"```text\n{text.rstrip()}\n```\n"


def format_error_output(output: dict) -> str:
    traceback = normalize_source(output.get("traceback", ""))
    return f"```text\n{traceback.rstrip()}\n```\n"


def format_display_output(output: dict, assets_dir: Path, stem: str, cell_index: int, output_index: int) -> str:
    data = output.get("data", {})

    for mime_type, suffix in IMAGE_MIME_TYPES.items():
        if mime_type not in data:
            continue
        payload = normalize_source(data[mime_type])
        filename = f"{stem}_cell{cell_index:03d}_out{output_index:02d}{suffix}"
        asset = save_binary_asset(
            assets_dir,
            filename,
            payload,
            is_base64=mime_type != "image/svg+xml",
        )
        return f"![output]({asset.parent.name}/{asset.name})\n"

    if "text/markdown" in data:
        return ensure_trailing_newline(normalize_source(data["text/markdown"]).rstrip()) + "\n"

    if "text/plain" in data:
        text = normalize_source(data["text/plain"])
        return f"```text\n{text.rstrip()}\n```\n"

    if "text/html" in data:
        text = normalize_source(data["text/html"])
        return f"```html\n{text.rstrip()}\n```\n"

    return ""


def notebook_to_markdown(notebook: dict, notebook_path: Path) -> str:
    parts: list[str] = []
    assets_dir = notebook_path.with_name(f"{notebook_path.stem}_assets")

    for cell_index, cell in enumerate(notebook.get("cells", []), start=1):
        cell_type = cell.get("cell_type")
        source = normalize_source(cell.get("source", ""))

        if cell_type == "markdown":
            attachments = cell.get("attachments", {})
            if attachments:
                source = replace_markdown_attachments(source, attachments, assets_dir, cell_index)
            parts.append(source.rstrip() + "\n")
            continue

        if cell_type != "code":
            continue

        parts.append("```python\n" + source.rstrip() + "\n```\n")

        outputs = cell.get("outputs", [])
        rendered_outputs: list[str] = []
        for output_index, output in enumerate(outputs, start=1):
            output_type = output.get("output_type")
            if output_type == "stream":
                rendered = format_stream_output(output)
            elif output_type == "error":
                rendered = format_error_output(output)
            elif output_type in {"execute_result", "display_data"}:
                rendered = format_display_output(
                    output,
                    assets_dir,
                    notebook_path.stem,
                    cell_index,
                    output_index,
                )
            else:
                rendered = ""
            if rendered:
                rendered_outputs.append(rendered.rstrip() + "\n")

        if rendered_outputs:
            parts.append("**Output:**\n\n" + "\n".join(rendered_outputs))

    return "\n".join(part.rstrip() for part in parts if part.strip()) + "\n"


def comment_markdown_line(line: str) -> str:
    return "#" if not line else f"# {line}"


def normalize_python_code(source: str) -> str:
    lines = source.splitlines()
    normalized: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        if stripped.startswith(("%", "!")):
            normalized.append(f"{indent}# {stripped}")
        else:
            normalized.append(line)
    return "\n".join(normalized)


def notebook_to_python(notebook: dict) -> str:
    parts: list[str] = []
    for cell in notebook.get("cells", []):
        cell_type = cell.get("cell_type")
        source = normalize_source(cell.get("source", "")).rstrip("\n")

        if cell_type == "markdown":
            parts.append("# %% [markdown]")
            lines = source.splitlines() or [""]
            parts.extend(comment_markdown_line(line) for line in lines)
            parts.append("")
            continue

        if cell_type == "code":
            parts.append("# %%")
            if source:
                parts.append(normalize_python_code(source))
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def iter_notebooks(path: Path) -> Iterable[Path]:
    if path.is_file() and path.suffix == ".ipynb":
        yield path
        return
    for notebook in sorted(path.rglob("*.ipynb")):
        yield notebook


def convert_notebook(notebook_path: Path) -> None:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    markdown_path = notebook_path.with_suffix(".md")
    python_path = notebook_path.with_suffix(".py")
    write_text(markdown_path, notebook_to_markdown(notebook, notebook_path))
    write_text(python_path, notebook_to_python(notebook))


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert .ipynb files to .md and .py")
    parser.add_argument("path", type=Path, help="Notebook file or directory")
    args = parser.parse_args()

    for notebook_path in iter_notebooks(args.path):
        convert_notebook(notebook_path)
        print(f"converted {notebook_path}")


if __name__ == "__main__":
    main()
