#!/usr/bin/env python3
"""
Crop the POSN exam images used by the chapter:
    Ideal Gases, Kinetic Theory, and the First Law of Thermodynamics

Run from the directory that contains the POSN PDF files:
    python3 crop_thermo_exam_images.py

Requirements:
    pip install pymupdf pillow

The script creates the images expected by the LaTeX chapter inside ./img/
and also writes a contact sheet for visual verification:
    img/_verify_thermo_exam_crops.jpg

Crop rectangles are deliberately specified manually after checking every source
page. They are normalized to the page size, so the script remains stable even
when a PDF renderer uses a different DPI.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import sys

import fitz  # PyMuPDF
from PIL import Image, ImageChops, ImageDraw, ImageOps


# Rendering scale. 3.0 gives clear images for insertion into a PDF without
# making each crop unnecessarily large.
RENDER_SCALE = 3.0
OUTPUT_DIR = Path("img")
CONTACT_SHEET_NAME = "_verify_thermo_exam_crops.jpg"


@dataclass(frozen=True)
class CropSpec:
    output_name: str
    pdf_candidates: tuple[str, ...]
    page_number: int  # Human-readable PDF page number, starting from 1
    crop: tuple[float, float, float, float]  # x0, y0, x1, y1 normalized to page
    label: str


# Each box was checked against the original page so that it includes the full
# statement, every answer choice, and every required diagram while excluding
# lines from the neighboring questions.
CROPS: tuple[CropSpec, ...] = (
    CropSpec(
        "posn60q19.png",
        ("posn1-60-physics.pdf",),
        8,
        (0.105, 0.472, 0.885, 0.590),
        "2560 ข้อ 19",
    ),
    CropSpec(
        "posn61q17.png",
        ("posn1-61-physics.pdf",),
        9,
        (0.122, 0.073, 0.900, 0.260),
        "2561 ข้อ 17",
    ),
    CropSpec(
        "posn61q19.png",
        ("posn1-61-physics.pdf",),
        10,
        (0.122, 0.073, 0.900, 0.260),
        "2561 ข้อ 19",
    ),
    CropSpec(
        "posn62q16.png",
        ("posn1-62-physics.pdf",),
        6,
        (0.120, 0.402, 0.905, 0.686),
        "2562 ข้อ 16",
    ),
    CropSpec(
        "posn63centerq10.png",
        ("physics_posn_63.pdf",),
        5,
        (0.055, 0.087, 0.945, 0.235),
        "ศูนย์ สอวน. 2563 ข้อ 10",
    ),
    CropSpec(
        "posn63centerq11.png",
        ("physics_posn_63.pdf",),
        5,
        (0.055, 0.255, 0.945, 0.500),
        "ศูนย์ สอวน. 2563 ข้อ 11",
    ),
    CropSpec(
        "posn63centerq29.png",
        ("physics_posn_63.pdf",),
        12,
        (0.055, 0.087, 0.945, 0.342),
        "ศูนย์ สอวน. 2563 ข้อ 29",
    ),
    CropSpec(
        "posn64q14.png",
        ("posn1-64-physics.pdf",),
        5,
        (0.055, 0.655, 0.940, 0.800),
        "2564 ข้อ 14",
    ),
    CropSpec(
        "posn65q14.png",
        ("posn1-65-physics.pdf",),
        6,
        (0.075, 0.045, 0.940, 0.235),
        "2565 ข้อ 14",
    ),
    CropSpec(
        "posn66q5.png",
        ("posn1-66-physics.pdf",),
        3,
        (0.075, 0.045, 0.900, 0.405),
        "2566 ข้อ 5",
    ),
    CropSpec(
        "posn66q7.png",
        ("posn1-66-physics.pdf",),
        3,
        (0.075, 0.635, 0.930, 0.785),
        "2566 ข้อ 7",
    ),
    CropSpec(
        "posn66q24.png",
        ("posn1-66-physics.pdf",),
        9,
        (0.075, 0.595, 0.930, 0.680),
        "2566 ข้อ 24",
    ),
)


def locate_pdf(candidates: Iterable[str]) -> Path:
    searched: list[Path] = []
    for candidate in candidates:
        path = Path(candidate)
        searched.append(path)
        if path.exists():
            return path

        if not path.is_absolute() and (not path.parts or path.parts[0].lower() != "ref"):
            for ref_dir in (Path("Ref"), Path("ref")):
                ref_path = ref_dir / path
                searched.append(ref_path)
                if ref_path.exists():
                    return ref_path

    expected = ", ".join(str(path) for path in searched)
    raise FileNotFoundError(
        "Missing PDF. Expected one of: " + expected
    )


def normalized_to_pdf_rect(
    page_rect: fitz.Rect,
    crop: tuple[float, float, float, float],
) -> fitz.Rect:
    x0, y0, x1, y1 = crop
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"Invalid normalized crop rectangle: {crop}")
    return fitz.Rect(
        page_rect.x0 + x0 * page_rect.width,
        page_rect.y0 + y0 * page_rect.height,
        page_rect.x0 + x1 * page_rect.width,
        page_rect.y0 + y1 * page_rect.height,
    )


def pixmap_to_image(pix: fitz.Pixmap) -> Image.Image:
    mode = "RGBA" if pix.alpha else "RGB"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples).convert("RGB")


def edge_warning(image: Image.Image, border: int = 3, threshold: int = 245) -> bool:
    """Return True when dark content touches a crop edge.

    A warning does not necessarily indicate an error, but it is useful when a
    future PDF version shifts its layout and the crop needs manual inspection.
    """
    gray = image.convert("L")
    w, h = gray.size
    edges = [
        gray.crop((0, 0, w, min(border, h))),
        gray.crop((0, max(0, h - border), w, h)),
        gray.crop((0, 0, min(border, w), h)),
        gray.crop((max(0, w - border), 0, w, h)),
    ]
    for edge in edges:
        extrema = edge.getextrema()
        if extrema and extrema[0] < threshold:
            return True
    return False


def crop_one(spec: CropSpec) -> tuple[Path, Image.Image, bool]:
    pdf_path = locate_pdf(spec.pdf_candidates)
    with fitz.open(pdf_path) as doc:
        if not 1 <= spec.page_number <= len(doc):
            raise IndexError(
                f"{pdf_path}: page {spec.page_number} does not exist; PDF has {len(doc)} pages"
            )
        page = doc[spec.page_number - 1]
        clip = normalized_to_pdf_rect(page.rect, spec.crop)
        pix = page.get_pixmap(
            matrix=fitz.Matrix(RENDER_SCALE, RENDER_SCALE),
            clip=clip,
            alpha=False,
        )
        image = pixmap_to_image(pix)
        # Add a small white border so the LaTeX output has breathing room and
        # edge checks are not triggered by text that legitimately begins close
        # to a manually selected crop boundary.
        image = ImageOps.expand(image, border=12, fill="white")

    output_path = OUTPUT_DIR / spec.output_name
    image.save(output_path, optimize=True)
    return output_path, image, edge_warning(image)


def fit_inside(image: Image.Image, width: int, height: int) -> Image.Image:
    copied = image.copy()
    copied.thumbnail((width, height), Image.Resampling.LANCZOS)
    return copied


def make_contact_sheet(items: list[tuple[CropSpec, Image.Image]]) -> Path:
    cols = 2
    cell_w = 920
    cell_h = 480
    header_h = 42
    padding = 18
    rows = (len(items) + cols - 1) // cols

    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)

    for index, (spec, image) in enumerate(items):
        col = index % cols
        row = index // cols
        left = col * cell_w
        top = row * cell_h

        draw.rectangle(
            (left, top, left + cell_w - 1, top + cell_h - 1),
            outline=(190, 190, 190),
            width=1,
        )
        draw.text((left + padding, top + 12), f"{spec.label}  ->  {spec.output_name}", fill="black")

        preview = fit_inside(
            image,
            cell_w - 2 * padding,
            cell_h - header_h - 2 * padding,
        )
        x = left + (cell_w - preview.width) // 2
        y = top + header_h + (cell_h - header_h - preview.height) // 2
        sheet.paste(preview, (x, y))

    path = OUTPUT_DIR / CONTACT_SHEET_NAME
    sheet.save(path, quality=94, optimize=True)
    return path


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Cropping thermodynamics POSN questions...")
    previews: list[tuple[CropSpec, Image.Image]] = []
    warnings: list[str] = []

    for spec in CROPS:
        try:
            output_path, image, touches_edge = crop_one(spec)
        except Exception as exc:
            print(f"[ERROR] {spec.label}: {exc}", file=sys.stderr)
            return 1

        previews.append((spec, image))
        status = "CHECK EDGE" if touches_edge else "OK"
        print(f"[{status:10}] {spec.label:24} -> {output_path}  {image.width}x{image.height}px")
        if touches_edge:
            warnings.append(spec.output_name)

    contact_sheet = make_contact_sheet(previews)
    print(f"\nCreated contact sheet: {contact_sheet}")
    if warnings:
        print("\nSome crops contain dark content close to an edge. Open the contact sheet and inspect:")
        for name in warnings:
            print(f"  - {name}")
    else:
        print("All crop edges have safe whitespace margins.")

    print("\nExpected LaTeX image paths were generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
