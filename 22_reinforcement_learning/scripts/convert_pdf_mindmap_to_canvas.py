"""Convert the RL algorithm map PDF into an Obsidian JSON Canvas file.

The source PDF is a single large mind-map page. The converter extracts every
text and image block as standalone Canvas nodes, then infers Canvas edges from
the radial mind-map layout. It does not add the PDF itself as a background node.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz


@dataclass(frozen=True)
class TextBlock:
    """A text block extracted from the PDF page."""

    index: int
    bbox: tuple[float, float, float, float]
    text: str


@dataclass(frozen=True)
class ImageBlock:
    """An image block extracted from the PDF page."""

    index: int
    bbox: tuple[float, float, float, float]
    image: bytes
    ext: str


@dataclass(frozen=True)
class PdfGeometry:
    """Extracted geometry for the first page of the source PDF."""

    page_width: float
    page_height: float
    text_blocks: list[TextBlock]
    image_blocks: list[ImageBlock]


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:04d}"


def _relative_to_vault(path: Path, vault_root: Path) -> str:
    return path.resolve().relative_to(vault_root.resolve()).as_posix()


def _block_text(block: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in block.get("lines", []):
        text = "".join(span.get("text", "") for span in line.get("spans", []))
        text = " ".join(text.split())
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def extract_pdf_geometry(pdf_path: Path) -> PdfGeometry:
    """Extract all text and image blocks from the first page of the PDF."""

    with fitz.open(pdf_path) as doc:
        if doc.page_count != 1:
            raise ValueError(f"Expected a single-page PDF, got {doc.page_count} pages")

        page = doc[0]
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
        page_dict = page.get_text("dict")
        text_blocks: list[TextBlock] = []
        image_blocks: list[ImageBlock] = []

        for block in page_dict.get("blocks", []):
            block_type = block.get("type")
            bbox = tuple(float(value) for value in block.get("bbox", (0, 0, 0, 0)))

            if block_type == 0:
                text = _block_text(block)
                if text:
                    text_blocks.append(
                        TextBlock(index=len(text_blocks), bbox=bbox, text=text)
                    )
            elif block_type == 1:
                image = block.get("image")
                if image:
                    ext = str(block.get("ext") or "png").lower()
                    if ext == "jpeg":
                        ext = "jpg"
                    image_blocks.append(
                        ImageBlock(
                            index=len(image_blocks),
                            bbox=bbox,
                            image=image,
                            ext=ext,
                        )
                    )

    return PdfGeometry(
        page_width=page_width,
        page_height=page_height,
        text_blocks=text_blocks,
        image_blocks=image_blocks,
    )


def _canvas_rect(
    bbox: tuple[float, float, float, float],
    geometry: PdfGeometry,
    scale: float,
    padding_x: float = 14,
    padding_y: float = 10,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    x = round((x0 - geometry.page_width / 2) * scale)
    y = round((y0 - geometry.page_height / 2) * scale)
    width = round(max((x1 - x0) * scale + padding_x, 24))
    height = round(max((y1 - y0) * scale + padding_y, 24))
    return x, y, width, height


def _text_node(block: TextBlock, geometry: PdfGeometry, scale: float) -> dict[str, Any]:
    x, y, width, height = _canvas_rect(block.bbox, geometry, scale)
    return {
        "id": _node_id("text", block.index),
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "type": "text",
        "text": block.text,
    }


def _write_image(block: ImageBlock, image_dir: Path) -> Path:
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / f"{_node_id('image', block.index)}.{block.ext}"
    image_path.write_bytes(block.image)
    return image_path


def _image_node(
    block: ImageBlock,
    geometry: PdfGeometry,
    vault_root: Path,
    image_dir: Path,
    scale: float,
) -> dict[str, Any]:
    image_path = _write_image(block, image_dir)
    x, y, width, height = _canvas_rect(
        block.bbox,
        geometry,
        scale,
        padding_x=0,
        padding_y=0,
    )
    return {
        "id": _node_id("image", block.index),
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "type": "file",
        "file": _relative_to_vault(image_path, vault_root),
    }


def _center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = bbox
    return (x0 + x1) / 2, (y0 + y1) / 2


def _distance_to_root(
    bbox: tuple[float, float, float, float],
    root_center: tuple[float, float],
) -> float:
    cx, cy = _center(bbox)
    rx, ry = root_center
    return ((cx - rx) ** 2 + ((cy - ry) * 0.25) ** 2) ** 0.5


def _edge_sides(
    from_bbox: tuple[float, float, float, float],
    to_bbox: tuple[float, float, float, float],
) -> tuple[str, str]:
    from_x, from_y = _center(from_bbox)
    to_x, to_y = _center(to_bbox)
    if abs(to_x - from_x) >= abs(to_y - from_y):
        return ("right", "left") if to_x >= from_x else ("left", "right")
    return ("bottom", "top") if to_y >= from_y else ("top", "bottom")


def _find_root_block(text_blocks: list[TextBlock]) -> TextBlock:
    for block in text_blocks:
        if block.text.strip() == "强化学习算法图谱":
            return block
    return min(
        text_blocks,
        key=lambda block: len(block.text),
    )


def _infer_text_edges(text_blocks: list[TextBlock]) -> list[dict[str, Any]]:
    root = _find_root_block(text_blocks)
    root_center = _center(root.bbox)
    root_id = _node_id("text", root.index)

    distances = {
        block.index: _distance_to_root(block.bbox, root_center) for block in text_blocks
    }
    edges: list[dict[str, Any]] = []

    for child in text_blocks:
        if child.index == root.index:
            continue

        child_cx, child_cy = _center(child.bbox)
        child_distance = distances[child.index]
        candidates = [
            parent
            for parent in text_blocks
            if parent.index != child.index
            and distances[parent.index] < child_distance - 1
        ]
        if not candidates:
            parent = root
        else:
            def score(parent: TextBlock) -> float:
                parent_cx, parent_cy = _center(parent.bbox)
                parent_distance = distances[parent.index]
                outward_gap = child_distance - parent_distance
                same_side_penalty = 0
                if (child_cx - root_center[0]) * (parent_cx - root_center[0]) < 0:
                    same_side_penalty = 2000
                backwards_penalty = 0
                if child_cx >= root_center[0] and parent_cx > child_cx:
                    backwards_penalty = 1000
                if child_cx < root_center[0] and parent_cx < child_cx:
                    backwards_penalty = 1000
                return (
                    abs(child_cy - parent_cy) * 1.8
                    + abs(child_cx - parent_cx) * 0.25
                    + outward_gap * 0.15
                    + same_side_penalty
                    + backwards_penalty
                )

            parent = min(candidates, key=score)

        from_side, to_side = _edge_sides(parent.bbox, child.bbox)
        edges.append(
            {
                "id": f"edge_text_{parent.index:04d}_{child.index:04d}",
                "fromNode": _node_id("text", parent.index),
                "fromSide": from_side,
                "toNode": _node_id("text", child.index),
                "toSide": to_side,
            }
        )

    # Keep the central title visually connected to the source metadata text.
    for child in text_blocks:
        if child.index != root.index and child.text.startswith("（ rl-algo-map"):
            edge_id = f"edge_text_{root.index:04d}_{child.index:04d}"
            if not any(edge["id"] == edge_id for edge in edges):
                edges.append(
                    {
                        "id": edge_id,
                        "fromNode": root_id,
                        "fromSide": "bottom",
                        "toNode": _node_id("text", child.index),
                        "toSide": "top",
                    }
                )
    return edges


def _infer_image_edges(
    image_blocks: list[ImageBlock],
    text_blocks: list[TextBlock],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []

    for image in image_blocks:
        image_cx, image_cy = _center(image.bbox)

        def score(text: TextBlock) -> float:
            text_cx, text_cy = _center(text.bbox)
            return abs(image_cx - text_cx) * 0.75 + abs(image_cy - text_cy)

        parent = min(text_blocks, key=score)
        from_side, to_side = _edge_sides(parent.bbox, image.bbox)
        edges.append(
            {
                "id": f"edge_image_{parent.index:04d}_{image.index:04d}",
                "fromNode": _node_id("text", parent.index),
                "fromSide": from_side,
                "toNode": _node_id("image", image.index),
                "toSide": to_side,
            }
        )

    return edges


def build_canvas(
    geometry: PdfGeometry,
    vault_root: Path,
    pdf_path: Path,
    image_dir: Path,
    scale: float = 1.35,
) -> dict[str, Any]:
    """Build a JSON Canvas document from extracted PDF geometry."""

    _ = pdf_path
    nodes: list[dict[str, Any]] = [
        _text_node(block, geometry, scale) for block in geometry.text_blocks
    ]
    nodes.extend(
        _image_node(block, geometry, vault_root, image_dir, scale)
        for block in geometry.image_blocks
    )

    edges = _infer_text_edges(geometry.text_blocks)
    edges.extend(_infer_image_edges(geometry.image_blocks, geometry.text_blocks))

    return {"nodes": nodes, "edges": edges}


def validate_canvas(canvas: dict[str, Any], vault_root: Path) -> None:
    """Validate the generated document shape and file references."""

    if not isinstance(canvas.get("nodes"), list):
        raise ValueError("Canvas must contain a nodes list")
    if not isinstance(canvas.get("edges"), list):
        raise ValueError("Canvas must contain an edges list")

    seen_ids: set[str] = set()
    for node in canvas["nodes"]:
        node_id = node.get("id")
        if not node_id:
            raise ValueError(f"Node missing id: {node}")
        if node_id in seen_ids:
            raise ValueError(f"Duplicate node id: {node_id}")
        seen_ids.add(node_id)

        for field in ("x", "y", "width", "height", "type"):
            if field not in node:
                raise ValueError(f"Node {node_id} missing {field}")

        if node.get("type") == "file":
            file_path = node.get("file")
            if not file_path:
                raise ValueError(f"File node {node_id} missing file path")
            if not (vault_root / file_path).exists():
                raise ValueError(f"File node {node_id} points to missing file: {file_path}")

    for edge in canvas["edges"]:
        edge_id = edge.get("id")
        from_node = edge.get("fromNode")
        to_node = edge.get("toNode")
        if not edge_id:
            raise ValueError(f"Edge missing id: {edge}")
        if from_node not in seen_ids:
            raise ValueError(f"Edge {edge_id} points from missing node: {from_node}")
        if to_node not in seen_ids:
            raise ValueError(f"Edge {edge_id} points to missing node: {to_node}")


def write_canvas(
    pdf_path: Path,
    vault_root: Path,
    output_path: Path,
    image_dir: Path,
    scale: float = 1.35,
) -> PdfGeometry:
    """Extract PDF geometry, write Canvas JSON, and return extraction stats."""

    import json

    geometry = extract_pdf_geometry(pdf_path)
    canvas = build_canvas(
        geometry,
        vault_root=vault_root,
        pdf_path=pdf_path,
        image_dir=image_dir,
        scale=scale,
    )
    validate_canvas(canvas, vault_root)
    output_path.write_text(
        json.dumps(canvas, ensure_ascii=False, indent="\t") + "\n",
        encoding="utf-8",
    )
    return geometry


def main() -> None:
    notes_dir = Path(__file__).resolve().parents[1]
    vault_root = notes_dir.parent
    pdf_path = notes_dir / "强化学习算法图谱 (rl-algo-map).pdf"
    output_path = notes_dir / "强化学习算法图谱 (rl-algo-map).canvas"
    image_dir = notes_dir / "assets" / "rl-algo-map-extracted"

    geometry = write_canvas(
        pdf_path=pdf_path,
        vault_root=vault_root,
        output_path=output_path,
        image_dir=image_dir,
    )
    print(f"wrote {output_path}")
    print(f"text_blocks={len(geometry.text_blocks)}")
    print(f"image_blocks={len(geometry.image_blocks)}")


if __name__ == "__main__":
    main()
