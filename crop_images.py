#!/usr/bin/env python3
"""
Verified POSN electrostatics crop script.

Run from the LaTeX project root:
    python3 crop_electrostatics_verified.py

Required packages:
    pip install pymupdf pillow numpy

Output:
    img/posn60q12.png
    img/posn60p2q6.png
    ...
    crop_review/electrostatics_verified_sheet.jpg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import math

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw


DPI = 240
ROOT = Path.cwd()
IMG_DIR = ROOT / "img"
REVIEW_DIR = ROOT / "crop_review"


@dataclass(frozen=True)
class CropItem:
    output: str
    pdf_candidates: tuple[str, ...]
    page: int  # 1-indexed
    # Crop box measured on the reference preview image.
    # The script converts it to fractional coordinates so it still works at any DPI.
    box_px: tuple[int, int, int, int]
    ref_size: tuple[int, int]
    # Optional white rectangles applied before final whitespace trim.
    # Each rectangle uses fractions of the crop image: left, top, right, bottom.
    whiteouts: tuple[tuple[float, float, float, float], ...] = ()


CROPS: list[CropItem] = [
    CropItem(
        "posn60q12.png",
        ("posn1-60-physics.pdf", "physics_posn_60.pdf", "physics-posn-60.pdf"),
        6,
        (95, 700, 980, 915),
        (1075, 1521),
    ),
    CropItem(
        "posn60p2q6.png",
        ("posn1-60-physics.pdf", "physics_posn_60.pdf", "physics-posn-60.pdf"),
        10,
        (85, 980, 985, 1205),
        (1075, 1521),
    ),
    CropItem(
        "posn61q12.png",
        ("posn1-61-physics.pdf", "physics_posn_61.pdf", "physics-posn-61.pdf"),
        7,
        (140, 100, 990, 625),
        (1105, 1430),
    ),
    CropItem(
        "posn61q14.png",
        ("posn1-61-physics.pdf", "physics_posn_61.pdf", "physics-posn-61.pdf"),
        7,
        (140, 880, 990, 1350),
        (1105, 1430),
    ),
    CropItem(
        "posn62q9.png",
        ("posn1-62-physics.pdf", "physics_posn_62.pdf", "physics-posn-62.pdf"),
        4,
        (130, 400, 980, 780),
        (1075, 1520),
    ),
    CropItem(
        "posn62q25.png",
        ("posn1-62-physics.pdf", "physics_posn_62.pdf", "physics-posn-62.pdf"),
        9,
        (125, 500, 985, 860),
        (1075, 1520),
    ),
    CropItem(
        "posn63centerq6.png",
        ("physics_posn_63.pdf", "physics-posn-63.pdf", "posn1-63-physics.pdf"),
        3,
        (70, 900, 1015, 1340),
        (1075, 1521),
    ),
    CropItem(
        "posn63centerq7.png",
        ("physics_posn_63.pdf", "physics-posn-63.pdf", "posn1-63-physics.pdf"),
        4,
        (70, 125, 1010, 540),
        (1075, 1521),
        whiteouts=((0.0, 0.88, 0.12, 1.0),),
    ),
    CropItem(
        "posn64q8.png",
        ("posn1-64-physics.pdf", "physics_posn_64.pdf", "physics-posn-64.pdf"),
        4,
        (45, 15, 920, 310),
        (960, 1373),
    ),
    CropItem(
        "posn64q9.png",
        ("posn1-64-physics.pdf", "physics_posn_64.pdf", "physics-posn-64.pdf"),
        4,
        (45, 300, 920, 725),
        (960, 1373),
    ),
    CropItem(
        "posn64q10.png",
        ("posn1-64-physics.pdf", "physics_posn_64.pdf", "physics-posn-64.pdf"),
        4,
        (45, 750, 925, 1040),
        (960, 1373),
    ),
    CropItem(
        "posn64q16.png",
        ("posn1-64-physics.pdf", "physics_posn_64.pdf", "physics-posn-64.pdf"),
        6,
        (45, 170, 925, 470),
        (960, 1373),
    ),
    CropItem(
        "posn65q3.png",
        ("posn1-65-physics.pdf", "physics_posn_65.pdf", "physics-posn-65.pdf"),
        2,
        (45, 720, 925, 1120),
        (960, 1371),
    ),
    CropItem(
        "posn65q4.png",
        ("posn1-65-physics.pdf", "physics_posn_65.pdf", "physics-posn-65.pdf"),
        3,
        (45, 60, 925, 515),
        (960, 1371),
    ),
    CropItem(
        "posn65q7.png",
        ("posn1-65-physics.pdf", "physics_posn_65.pdf", "physics-posn-65.pdf"),
        4,
        (45, 60, 925, 360),
        (960, 1371),
    ),
    CropItem(
        "posn65q17.png",
        ("posn1-65-physics.pdf", "physics_posn_65.pdf", "physics-posn-65.pdf"),
        7,
        (45, 60, 925, 430),
        (960, 1371),
    ),
    CropItem(
        "posn66q12.png",
        ("posn1-66-physics.pdf", "physics_posn_66.pdf", "physics-posn-66.pdf"),
        5,
        (75, 280, 1000, 1120),
        (1075, 1521),
    ),
    CropItem(
        "posn66q26.png",
        ("posn1-66-physics.pdf", "physics_posn_66.pdf", "physics-posn-66.pdf"),
        10,
        (75, 85, 1000, 365),
        (1075, 1521),
    ),
    CropItem(
        "posn66q27.png",
        ("posn1-66-physics.pdf", "physics_posn_66.pdf", "physics-posn-66.pdf"),
        10,
        (75, 380, 1000, 720),
        (1075, 1521),
    ),
    CropItem(
        "posn68q4.png",
        ("06-วิชาฟิสิกส์.pdf", "posn1-68-physics.pdf", "physics_posn_68.pdf"),
        2,
        (75, 930, 1060, 1285),
        (1075, 1521),
    ),
    CropItem(
        "posn68q17.png",
        ("06-วิชาฟิสิกส์.pdf", "posn1-68-physics.pdf", "physics_posn_68.pdf"),
        5,
        (75, 805, 1060, 1075),
        (1075, 1521),
    ),
    CropItem(
        "posn68q19.png",
        ("06-วิชาฟิสิกส์.pdf", "posn1-68-physics.pdf", "physics_posn_68.pdf"),
        6,
        (75, 65, 1065, 350),
        (1075, 1521),
    ),
]


def iter_pdfs(root: Path) -> Iterable[Path]:
    ignored = {".git", "node_modules", "venv", ".venv", "__pycache__", "img", "crop_review"}
    for path in root.rglob("*.pdf"):
        if any(part in ignored for part in path.parts):
            continue
        yield path


def find_pdf(candidates: tuple[str, ...], all_pdfs: list[Path]) -> Path:
    candidate_names = {name.lower() for name in candidates}
    for pdf in all_pdfs:
        if pdf.name.lower() in candidate_names:
            return pdf

    keywords = [name.lower().replace("_", "-").replace(" ", "") for name in candidates]
    for pdf in all_pdfs:
        normalized = pdf.name.lower().replace("_", "-").replace(" ", "")
        if any(key.replace("_", "-").replace(" ", "") in normalized for key in keywords):
            return pdf

    raise FileNotFoundError(
        "Could not find PDF. Expected one of: " + ", ".join(candidates)
    )


def render_page(pdf_path: Path, page_number: int) -> Image.Image:
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_number - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(DPI / 72, DPI / 72), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    finally:
        doc.close()


def fractional_box(item: CropItem) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = item.box_px
    width, height = item.ref_size
    return x0 / width, y0 / height, x1 / width, y1 / height


def crop_by_fraction(image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    width, height = image.size
    x0, y0, x1, y1 = box
    return image.crop(
        (
            round(x0 * width),
            round(y0 * height),
            round(x1 * width),
            round(y1 * height),
        )
    )


def apply_whiteouts(image: Image.Image, whiteouts: tuple[tuple[float, float, float, float], ...]) -> None:
    if not whiteouts:
        return
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for left, top, right, bottom in whiteouts:
        draw.rectangle(
            (
                round(left * width),
                round(top * height),
                round(right * width),
                round(bottom * height),
            ),
            fill="white",
        )


def trim_whitespace(image: Image.Image, padding: int = 14) -> Image.Image:
    gray = image.convert("L")
    arr = np.asarray(gray)
    mask = arr < 248
    if not mask.any():
        return image

    ys, xs = np.where(mask)
    left = max(0, int(xs.min()) - padding)
    top = max(0, int(ys.min()) - padding)
    right = min(image.width, int(xs.max()) + padding)
    bottom = min(image.height, int(ys.max()) + padding)
    return image.crop((left, top, right, bottom))


def make_contact_sheet(paths: list[Path], output_path: Path) -> None:
    cards: list[Image.Image] = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        image.thumbnail((560, 380), Image.Resampling.LANCZOS)
        card = Image.new("RGB", (600, 450), "white")
        card.paste(image, ((600 - image.width) // 2, 20))
        draw = ImageDraw.Draw(card)
        draw.text((10, 415), path.name, fill="red")
        cards.append(card)

    if not cards:
        return

    cols = 2
    rows = math.ceil(len(cards) / cols)
    sheet = Image.new("RGB", (cols * 600, rows * 450), "white")
    for index, card in enumerate(cards):
        sheet.paste(card, ((index % cols) * 600, (index // cols) * 450))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def main() -> None:
    IMG_DIR.mkdir(exist_ok=True)
    REVIEW_DIR.mkdir(exist_ok=True)

    all_pdfs = list(iter_pdfs(ROOT))
    if not all_pdfs:
        raise SystemExit("No PDF files found under this project directory.")

    saved_paths: list[Path] = []

    for item in CROPS:
        pdf_path = find_pdf(item.pdf_candidates, all_pdfs)
        page_image = render_page(pdf_path, item.page)
        cropped = crop_by_fraction(page_image, fractional_box(item))
        apply_whiteouts(cropped, item.whiteouts)
        cropped = trim_whitespace(cropped)

        output_path = IMG_DIR / item.output
        cropped.save(output_path)
        saved_paths.append(output_path)
        print(f"saved {output_path}  source={pdf_path.name} page={item.page}")

    contact_sheet = REVIEW_DIR / "electrostatics_verified_sheet.jpg"
    make_contact_sheet(saved_paths, contact_sheet)
    print(f"saved {contact_sheet}")


if __name__ == "__main__":
    main()