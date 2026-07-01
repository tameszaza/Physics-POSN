#!/usr/bin/env python3
"""Crop every POSN exam question used by the DC circuit/capacitance chapter.

The crop rectangles were calibrated against the exact exam PDFs used for the
chapter and are stored as normalized page coordinates, so output stays correct
at any render DPI.

Requirements:
    pip install pymupdf pillow

Example:
    python crop_circuit_posn_questions.py \
        --input-dir . \
        --output-dir img \
        --dpi 300 \
        --preview

The script exits immediately if a required PDF is missing, has too few pages,
or any crop fails validation.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz  # PyMuPDF
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
    page: int  # 1-based
    box: tuple[float, float, float, float]  # normalized x0, y0, x1, y1


SOURCES: dict[str, PdfSource] = {
    "60": PdfSource("60", ("posn1-60-physics.pdf",), 11),
    "61": PdfSource("61", ("posn1-61-physics.pdf",), 14),
    "62": PdfSource("62", ("posn1-62-physics.pdf",), 7),
    "64": PdfSource("64", ("posn1-64-physics.pdf",), 9),
    "65": PdfSource("65", ("posn1-65-physics.pdf",), 3),
    "66": PdfSource("66", ("posn1-66-physics.pdf",), 8),
    "67": PdfSource("67", ("posn1-67-physics-1.pdf", "posn1-67-physics.pdf"), 6),
    "68": PdfSource(
        "68",
        (
            "06-วิชาฟิสิกส์.pdf",
            "posn1-68-physics.pdf",
            "physics-posn-68-full.pdf",
            "physics-posn-68.pdf",
        ),
        5,
    ),
}


# Each rectangle was visually checked against the rendered source page.
# Coordinates use a PDF-style normalized page coordinate system:
# (0, 0) = top-left and (1, 1) = bottom-right.
JOBS: tuple[CropJob, ...] = (
    CropJob("posn60q13.png", "60", 6, (0.050, 0.625, 0.965, 0.895)),
    CropJob("posn60q14.png", "60", 7, (0.050, 0.030, 0.965, 0.460)),
    CropJob("posn60q15.png", "60", 7, (0.050, 0.450, 0.965, 0.610)),
    CropJob("posn60p2q7.png", "60", 11, (0.050, 0.025, 0.965, 0.345)),

    CropJob("posn61q13.png", "61", 7, (0.050, 0.425, 0.965, 0.600)),
    CropJob("posn61q14.png", "61", 7, (0.050, 0.570, 0.965, 0.950)),
    CropJob("posn61q15.png", "61", 8, (0.050, 0.025, 0.965, 0.440)),
    CropJob("posn61p2q7.png", "61", 13, (0.050, 0.025, 0.965, 0.345)),

    CropJob("posn62q13.png", "62", 5, (0.045, 0.585, 0.975, 0.745)),
    CropJob("posn62q14.png", "62", 5, (0.045, 0.730, 0.975, 0.945)),
    CropJob("posn62q17.png", "62", 6, (0.045, 0.675, 0.975, 0.925)),
    CropJob("posn62q21.png", "62", 7, (0.045, 0.675, 0.975, 0.925)),

    CropJob("posn64q10.png", "64", 4, (0.045, 0.535, 0.975, 0.885)),
    CropJob("posn64q11.png", "64", 5, (0.045, 0.005, 0.975, 0.190)),
    CropJob("posn64q20.png", "64", 7, (0.045, 0.335, 0.975, 0.495)),
    CropJob("posn64p2q26.png", "64", 9, (0.045, 0.020, 0.975, 0.345)),

    CropJob("posn65q2.png", "65", 2, (0.045, 0.220, 0.975, 0.480)),
    CropJob("posn65q6.png", "65", 3, (0.045, 0.640, 0.975, 0.855)),

    CropJob("posn66q13.png", "66", 6, (0.045, 0.025, 0.975, 0.455)),
    CropJob("posn66q19.png", "66", 8, (0.045, 0.270, 0.975, 0.495)),

    CropJob("posn67q7.png", "67", 4, (0.045, 0.025, 0.975, 0.245)),
    CropJob("posn67q8.png", "67", 4, (0.045, 0.245, 0.975, 0.415)),
    CropJob("posn67q16.png", "67", 6, (0.045, 0.515, 0.975, 0.915)),

    CropJob("posn68q7.png", "68", 3, (0.045, 0.245, 0.975, 0.370)),
    CropJob("posn68q8.png", "68", 3, (0.045, 0.370, 0.975, 0.500)),
    CropJob("posn68q16.png", "68", 5, (0.045, 0.335, 0.975, 0.535)),
    CropJob("posn68q17.png", "68", 5, (0.045, 0.525, 0.975, 0.695)),
)


def fail(message: str) -> "NoReturn":
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def resolve_sources(input_dir: Path) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    errors: list[str] = []

    for key, source in SOURCES.items():
        chosen: Path | None = None
        rejected: list[str] = []

        for candidate in source.candidates:
            path = input_dir / candidate
            if not path.is_file():
                continue
            try:
                with fitz.open(path) as doc:
                    if len(doc) < source.min_pages:
                        rejected.append(
                            f"{candidate} has only {len(doc)} pages; "
                            f"at least {source.min_pages} are required"
                        )
                        continue
            except Exception as exc:
                rejected.append(f"{candidate} cannot be opened: {exc}")
                continue
            chosen = path
            break

        if chosen is None:
            expected = ", ".join(source.candidates)
            detail = "; ".join(rejected)
            line = f"256{key}: missing usable PDF. Expected one of: {expected}"
            if detail:
                line += f". Found but rejected: {detail}"
            errors.append(line)
        else:
            resolved[key] = chosen

    if errors:
        fail("\n".join(errors))

    return resolved


def normalized_box_to_rect(page_rect: fitz.Rect, box: tuple[float, float, float, float]) -> fitz.Rect:
    x0, y0, x1, y1 = box
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"Invalid normalized crop rectangle: {box}")
    return fitz.Rect(
        page_rect.x0 + x0 * page_rect.width,
        page_rect.y0 + y0 * page_rect.height,
        page_rect.x0 + x1 * page_rect.width,
        page_rect.y0 + y1 * page_rect.height,
    )


def trim_white_margin(image: Image.Image, threshold: int = 250, padding: int = 28) -> Image.Image:
    """Trim only empty outer whitespace, never interior whitespace."""
    rgb = image.convert("RGB")
    gray = ImageOps.grayscale(rgb)
    content_mask = gray.point(lambda value: 255 if value < threshold else 0)
    bbox = content_mask.getbbox()
    if bbox is None:
        return rgb

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(rgb.width, right + padding)
    bottom = min(rgb.height, bottom + padding)
    return rgb.crop((left, top, right, bottom))


def validate_crop(image: Image.Image, job: CropJob) -> None:
    width, height = image.size
    if width < 500 or height < 180:
        fail(f"{job.output_name}: suspiciously small crop ({width} x {height})")

    gray = ImageOps.grayscale(image)
    pixels = gray.histogram()
    total = width * height
    dark = sum(pixels[:245])
    dark_ratio = dark / total
    if dark_ratio < 0.002:
        fail(f"{job.output_name}: crop appears blank (dark ratio {dark_ratio:.5f})")

    # Ensure the auto-trim padding did not get lost.
    border = max(8, min(width, height) // 120)
    edges = [
        gray.crop((0, 0, width, border)),
        gray.crop((0, height - border, width, height)),
        gray.crop((0, 0, border, height)),
        gray.crop((width - border, 0, width, height)),
    ]
    for edge in edges:
        hist = edge.histogram()
        edge_dark = sum(hist[:235])
        if edge_dark / max(1, edge.width * edge.height) > 0.30:
            print(
                f"WARNING: {job.output_name}: dark content is close to a crop edge",
                file=sys.stderr,
            )


def render_job(
    job: CropJob,
    source_path: Path,
    output_dir: Path,
    dpi: int,
    trim: bool,
) -> Path:
    zoom = dpi / 72.0
    with fitz.open(source_path) as doc:
        if not 1 <= job.page <= len(doc):
            fail(
                f"{job.output_name}: page {job.page} does not exist in "
                f"{source_path.name} ({len(doc)} pages)"
            )
        page = doc[job.page - 1]
        clip = normalized_box_to_rect(page.rect, job.box)
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(zoom, zoom),
            clip=clip,
            alpha=False,
            annots=True,
        )
        image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")

    if trim:
        image = trim_white_margin(image)
    validate_crop(image, job)

    output_path = output_dir / job.output_name
    image.save(output_path, format="PNG", optimize=True)
    return output_path


def make_preview(paths: Iterable[Path], preview_path: Path) -> None:
    paths = list(paths)
    font = ImageFont.load_default()
    card_width, card_height = 820, 610
    columns = 2
    rows = math.ceil(len(paths) / columns)
    sheet = Image.new(
        "RGB",
        (columns * card_width, rows * card_height),
        (226, 226, 226),
    )

    for index, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        image.thumbnail((card_width - 30, card_height - 60), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (card_width, card_height), "white")
        card.paste(image, ((card_width - image.width) // 2, 42))
        draw = ImageDraw.Draw(card)
        draw.text((10, 10), path.name, fill="black", font=font)
        x = (index % columns) * card_width
        y = (index // columns) * card_height
        sheet.paste(card, (x, y))

    sheet.save(preview_path, format="JPEG", quality=92, optimize=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop all POSN circuit/capacitance questions used by the LaTeX chapter."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("."),
        help="Directory containing the exam PDFs (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("img"),
        help="Directory for cropped PNG files (default: ./img)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Render resolution. 250-350 is recommended (default: 300)",
    )
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Keep the full calibrated rectangle instead of trimming outer white space",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Also create circuit-question-crops-preview.jpg",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not input_dir.is_dir():
        fail(f"Input directory does not exist: {input_dir}")
    if not 120 <= args.dpi <= 600:
        fail("--dpi must be between 120 and 600")

    resolved = resolve_sources(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    produced: list[Path] = []
    for job in JOBS:
        output_path = render_job(
            job=job,
            source_path=resolved[job.source_key],
            output_dir=output_dir,
            dpi=args.dpi,
            trim=not args.no_trim,
        )
        produced.append(output_path)
        print(f"OK  {output_path.name}")

    if args.preview:
        preview_path = output_dir / "circuit-question-crops-preview.jpg"
        make_preview(produced, preview_path)
        print(f"OK  {preview_path.name}")

    print(f"\nCompleted: {len(produced)} question images written to {output_dir}")


if __name__ == "__main__":
    main()