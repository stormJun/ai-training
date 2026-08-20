"""Verify that the RL algorithm map PDF is fully converted to JSON Canvas."""

from __future__ import annotations

import json
from pathlib import Path

from convert_pdf_mindmap_to_canvas import (
    build_canvas,
    extract_pdf_geometry,
    validate_canvas,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
NOTES_DIR = REPO_ROOT / "22_reinforcement_learning"
PDF_PATH = NOTES_DIR / "强化学习算法图谱 (rl-algo-map).pdf"


def main() -> None:
    geometry = extract_pdf_geometry(PDF_PATH)
    assert len(geometry.text_blocks) >= 500, len(geometry.text_blocks)
    assert len(geometry.image_blocks) >= 120, len(geometry.image_blocks)

    canvas = build_canvas(
        geometry,
        vault_root=REPO_ROOT,
        pdf_path=PDF_PATH,
        image_dir=NOTES_DIR / "assets" / "rl-algo-map-extracted",
    )
    validate_canvas(canvas, REPO_ROOT)

    text_nodes = [node for node in canvas["nodes"] if node["id"].startswith("text_")]
    image_nodes = [node for node in canvas["nodes"] if node["id"].startswith("image_")]
    pdf_nodes = [
        node
        for node in canvas["nodes"]
        if node.get("type") == "file" and str(node.get("file", "")).endswith(".pdf")
    ]
    assert len(text_nodes) == len(geometry.text_blocks)
    assert len(image_nodes) == len(geometry.image_blocks)
    assert not pdf_nodes, pdf_nodes
    assert all(node["id"] != "source_pdf_background" for node in canvas["nodes"])
    assert len(canvas["edges"]) >= len(text_nodes) - 1, len(canvas["edges"])

    # Ensure it is serializable as normal JSON Canvas.
    json.dumps(canvas, ensure_ascii=False)


if __name__ == "__main__":
    main()
