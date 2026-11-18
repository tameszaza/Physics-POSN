#!/usr/bin/env python3
"""Crop every POSN past-exam question used by the ray-optics chapter.

The crop rectangles are normalized to the source PDF page, so the output is
stable at different render resolutions. The script also creates a contact sheet
for visual checking and validates that every image referenced by the LaTeX
chapter is generated.

Requirements:
    pip install pymupdf pillow numpy

Example:
    python crop_ray_optics_posn_questions_verified.py \
        --input-dir . \
        --output-dir img \
        --tex-file chapter-ray-optics-mirrors-lenses.tex \
        --dpi 320 \
        --preview
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps


@dataclass(frozen=True)
class PdfSource:
    key: str
    candidates: tuple[str, ...]
    min_pages: int


@dataclass(frozen=True)
class CropJob:
    output_name: str
    source_key: str
    page: int  # 1-based PDF page number
    box: tuple[float, float, float, float]
    label: str


SOURCES: dict[str, PdfSource] = {
    "60": PdfSource("60", ("posn1-60-physics.pdf", "physics_posn_60.pdf"), 11),
    "61": PdfSource("61", ("posn1-61-physics.pdf", "physics_posn_61.pdf"), 14),
    "62": PdfSource("62", ("posn1-62-physics.pdf", "physics_posn_62.pdf"), 4),
    "63": PdfSource("63", ("physics_posn_63.pdf", "posn1-63-physics.pdf"), 10),
    "66": PdfSource("66", ("posn1-66-physics.pdf", "physics_posn_66.pdf"), 7),
    "67": PdfSource(
        "67",
        ("posn1-67-physics-1.pdf", "posn1-67-physics.pdf", "physics_posn_67.pdf"),
        5,
    ),
    "68": PdfSource(
        "68",
        ("06-วิชาฟิสิกส์.pdf", "posn1-68-physics.pdf", "physics_posn_68.pdf"),
        4,
    ),
}


# These rectangles were calibrated against the exact PDFs listed above.
# Each box retains the complete statement, diagrams, and answer choices while
# stopping before neighboring questions.
JOBS: tuple[CropJob, ...] = (
    CropJob("posn60q20.png", "60", 8, (0.070, 0.590, 0.935, 0.765), "2560 ข้อ 20"),
    CropJob("posn60p2q10.png", "60", 11, (0.070, 0.735, 0.935, 0.875), "2560 ตอนที่ 2 ข้อ 10"),
    CropJob("posn61q20.png", "61", 10, (0.095, 0.268, 0.905, 0.430), "2561 ข้อ 20"),
    CropJob("posn61p2q10.png", "61", 14, (0.095, 0.268, 0.905, 0.600), "2561 ตอนที่ 2 ข้อ 10"),
    CropJob("posn62q2.png", "62", 2, (0.085, 0.195, 0.925, 0.515), "2562 ข้อ 2"),
    CropJob("posn62q10.png", "62", 4, (0.085, 0.495, 0.925, 0.835), "2562 ข้อ 10"),
    CropJob("posn63q24.png", "63", 10, (0.045, 0.090, 0.955, 0.430), "ศูนย์ สอวน. 2563 ข้อ 24"),
    CropJob("posn63q25.png", "63", 10, (0.045, 0.435, 0.955, 0.825), "ศูนย์ สอวน. 2563 ข้อ 25"),
    CropJob("posn66q15.png", "66", 7, (0.065, 0.045, 0.940, 0.300), "2566 ข้อ 15"),
    CropJob("posn66q16.png", "66", 7, (0.065, 0.295, 0.940, 0.505), "2566 ข้อ 16"),
    CropJob("posn66q17.png", "66", 7, (0.065, 0.535, 0.940, 0.900), "2566 ข้อ 17"),
    CropJob("posn67q12.png", "67", 5, (0.060, 0.195, 0.940, 0.430), "2567 ข้อ 12"),
    CropJob("posn67q14.png", "67", 5, (0.060, 0.545, 0.940, 0.715), "2567 ข้อ 14"),
    CropJob("posn68q13.png", "68", 4, (0.060, 0.430, 0.940, 0.660), "2568 ข้อ 13"),
    CropJob("posn68q14.png", "68", 4, (0.060, 0.655, 0.940, 0.900), "2568 ข้อ 14"),
)


def iter_pdfs(root: Path) -> Iterable[Path]:
    ignored = {".git", "node_modules", "venv", ".venv", "__pycache__", "img", "crop_review"}
    for path in root.rglob("*.pdf"):
        if any(part in ignored for part in path.parts):
            continue
        yield path


def find_pdf(source: PdfSource, all_pdfs: list[Path]) -> Path:
    candidate_names = {name.casefold() for name in source.candidates}
    for pdf in all_pdfs:
        if pdf.name.casefold() in candidate_names:
            return pdf
    raise FileNotFoundError(
        f"Could not find source {source.key}. Expected one of: " + ", ".join(source.candidates)
    )


def normalized_rect(page: fitz.Page, box: tuple[float, float, float, float]) -> fitz.Rect:
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"Invalid normalized crop: {box}")
    r = page.rect
    return fitz.Rect(
        r.x0 + x0 * r.width,
        r.y0 + y0 * r.height,
        r.x0 + x1 * r.width,
        r.y0 + y1 * r.height,
    )


def trim_whitespace(image: Image.Image, padding: int = 22) -> Image.Image:
    gray = np.asarray(image.convert("L"))
    mask = gray < 248
    if not mask.any():
        return image
    ys, xs = np.where(mask)
    left = max(0, int(xs.min()) - padding)
    top = max(0, int(ys.min()) - padding)
    right = min(image.width, int(xs.max()) + padding + 1)
    bottom = min(image.height, int(ys.max()) + padding + 1)
    return image.crop((left, top, right, bottom))


def validate_crop(image: Image.Image, name: str) -> list[str]:
    warnings: list[str] = []
    if image.width < 500 or image.height < 130:
        warnings.append(f"{name}: suspiciously small crop {image.size}")
    gray = np.asarray(image.convert("L"))
    dark_fraction = float((gray < 240).mean())
    if dark_fraction < 0.002:
        warnings.append(f"{name}: crop appears blank")
    border = max(3, min(image.width, image.height) // 300)
    edges = np.concatenate(
        [gray[:border, :].ravel(), gray[-border:, :].ravel(), gray[:, :border].ravel(), gray[:, -border:].ravel()]
    )
    if float((edges < 210).mean()) > 0.08:
        warnings.append(f"{name}: dark content may touch a crop edge")
    return warnings


def create_contact_sheet(items: list[tuple[CropJob, Path]], output: Path) -> None:
    cards: list[Image.Image] = []
    card_width = 1300
    max_preview_width = 1240
    max_preview_height = 780

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default()

    for job, path in items:
        image = Image.open(path).convert("RGB")
        preview = image.copy()
        preview.thumbnail((max_preview_width, max_preview_height), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (card_width, preview.height + 105), "white")
        draw = ImageDraw.Draw(card)
        draw.text((24, 18), f"{job.output_name} | {job.label}", fill="black", font=font)
        card.paste(preview, ((card_width - preview.width) // 2, 75))
        cards.append(card)

    columns = 2
    gap = 22
    rows = (len(cards) + columns - 1) // columns
    row_heights = []
    for row in range(rows):
        row_cards = cards[row * columns : (row + 1) * columns]
        row_heights.append(max(card.height for card in row_cards))

    sheet_width = columns * card_width + (columns + 1) * gap
    sheet_height = sum(row_heights) + (rows + 1) * gap
    sheet = Image.new("RGB", (sheet_width, sheet_height), (225, 225, 225))

    y = gap
    for row, row_height in enumerate(row_heights):
        for col in range(columns):
            index = row * columns + col
            if index >= len(cards):
                break
            card = cards[index]
            x = gap + col * (card_width + gap)
            sheet.paste(card, (x, y))
        y += row_height + gap

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90, optimize=True)


def latex_image_names(tex_path: Path) -> set[str]:
    text = tex_path.read_text(encoding="utf-8")
    return {Path(match).name for match in re.findall(r"img/([^}\s]+\.png)", text)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("img"))
    parser.add_argument("--tex-file", type=Path, default=Path("chapter-ray-optics-mirrors-lenses.tex"))
    parser.add_argument("--dpi", type=int, default=320)
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dpi < 150:
        raise ValueError("DPI should be at least 150")

    all_pdfs = list(iter_pdfs(args.input_dir.resolve()))
    resolved: dict[str, Path] = {}
    for key, source in SOURCES.items():
        path = find_pdf(source, all_pdfs)
        with fitz.open(path) as doc:
            if len(doc) < source.min_pages:
                raise ValueError(f"{path.name} has only {len(doc)} pages; expected at least {source.min_pages}")
        resolved[key] = path
        print(f"Source {key}: {path}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[CropJob, Path]] = []
    all_warnings: list[str] = []
    matrix = fitz.Matrix(args.dpi / 72.0, args.dpi / 72.0)

    docs: dict[str, fitz.Document] = {key: fitz.open(path) for key, path in resolved.items()}
    try:
        for job in JOBS:
            doc = docs[job.source_key]
            page = doc[job.page - 1]
            pix = page.get_pixmap(matrix=matrix, clip=normalized_rect(page, job.box), alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            image = trim_whitespace(image)
            output = args.output_dir / job.output_name
            image.save(output, format="PNG", optimize=True)
            warnings = validate_crop(image, job.output_name)
            all_warnings.extend(warnings)
            generated.append((job, output))
            print(f"Created {output} ({image.width} x {image.height})")
    finally:
        for doc in docs.values():
            doc.close()

    expected = {job.output_name for job in JOBS}
    if args.tex_file.exists():
        referenced = latex_image_names(args.tex_file)
        missing_from_script = referenced - expected
        unused_by_tex = expected - referenced
        if missing_from_script:
            raise RuntimeError("LaTeX references images not generated by this script: " + ", ".join(sorted(missing_from_script)))
        if unused_by_tex:
            print("Warning: generated but not referenced: " + ", ".join(sorted(unused_by_tex)), file=sys.stderr)
    else:
        print(f"Warning: LaTeX file not found: {args.tex_file}", file=sys.stderr)

    if args.preview:
        preview_path = args.output_dir / "ray-optics-question-crops-preview.jpg"
        create_contact_sheet(generated, preview_path)
        print(f"Created preview {preview_path}")

    if all_warnings:
        print("Crop validation warnings:", file=sys.stderr)
        for warning in all_warnings:
            print(f"  - {warning}", file=sys.stderr)
        return 2

    print(f"Verified {len(generated)} crop files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())