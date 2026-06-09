from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import fitz  # PyMuPDF
from PIL import Image, ImageDraw


# =========================================================
# Configuration
# =========================================================

ZOOM: Final[float] = 3.0
OUTPUT_DIR: Final[Path] = Path("img")
VERIFICATION_DIR: Final[Path] = Path("verification")

PDF_CANDIDATES: Final[tuple[Path, ...]] = (
    Path("physics_posn_63.pdf"),
    Path("Ref/physics_posn_63.pdf"),
    Path("ref/physics_posn_63.pdf"),
)


@dataclass(frozen=True)
class PixelMask:
    """White rectangle applied after rendering, using crop-local pixels."""

    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class ProblemCrop:
    """
    One exact crop from the 2563 POSN physics exam.

    page_index is zero-based and includes the cover page.
    crop_box contains PDF coordinates: (left, top, right, bottom).
    """

    filename: str
    page_index: int
    crop_box: tuple[float, float, float, float]
    masks: tuple[PixelMask, ...] = ()


# =========================================================
# Verified crop coordinates
# =========================================================

PROBLEMS: Final[tuple[ProblemCrop, ...]] = (
    ProblemCrop("posn63q2.png", 1, (38, 185, 570, 405)),
    ProblemCrop("posn63q3.png", 1, (38, 445, 570, 735)),
    ProblemCrop("posn63q12.png", 4, (38, 430, 570, 675)),
    ProblemCrop("posn63q13.png", 5, (38, 70, 570, 265)),
    ProblemCrop("posn63q14.png", 5, (38, 280, 570, 490)),
    ProblemCrop("posn63q20.png", 7, (38, 470, 570, 720)),
    ProblemCrop("posn63q21.png", 8, (38, 70, 570, 292)),
    ProblemCrop("posn63q22.png", 8, (38, 290, 570, 500)),
    ProblemCrop(
        "posn63q23.png",
        8,
        (38, 522, 570, 770),
        masks=(PixelMask(0, 0, 1596, 34),),
    ),
    ProblemCrop("posn63q26.png", 10, (38, 72, 570, 305)),
    ProblemCrop("posn63q27.png", 10, (38, 325, 570, 525)),
    ProblemCrop(
        "posn63q28.png",
        10,
        (38, 520, 570, 780),
        masks=(PixelMask(0, 0, 1596, 52),),
    ),
    ProblemCrop("posn63q29.png", 11, (38, 70, 570, 290)),
    ProblemCrop("posn63q31.png", 11, (38, 555, 570, 780)),
)


def find_pdf() -> Path:
    """Locate the exam PDF in the current working directory or Ref folder."""

    for candidate in PDF_CANDIDATES:
        if candidate.exists():
            return candidate

    searched = "\n".join(f"  - {candidate}" for candidate in PDF_CANDIDATES)
    raise FileNotFoundError(
        "Cannot find physics_posn_63.pdf. Place it in the current directory "
        "or inside Ref/. Searched:\n" + searched
    )


def render_crop(page: fitz.Page, problem: ProblemCrop) -> Image.Image:
    """Render a clean high-resolution crop for one question."""

    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(ZOOM, ZOOM),
        clip=fitz.Rect(*problem.crop_box),
        alpha=False,
    )

    image = Image.frombytes(
        "RGB",
        (pixmap.width, pixmap.height),
        pixmap.samples,
    )

    if problem.masks:
        draw = ImageDraw.Draw(image)
        for mask in problem.masks:
            draw.rectangle(
                (mask.left, mask.top, mask.right, mask.bottom),
                fill="white",
            )

    return image


def create_contact_sheet(image_paths: list[Path], output_path: Path) -> None:
    """Create a two-column preview for fast visual verification."""

    cards: list[Image.Image] = []
    card_width = 1040
    preview_max_width = 1000
    preview_max_height = 600

    for image_path in image_paths:
        image = Image.open(image_path).convert("RGB")
        preview = image.copy()
        preview.thumbnail((preview_max_width, preview_max_height))

        card = Image.new("RGB", (card_width, preview.height + 80), "white")
        draw = ImageDraw.Draw(card)
        draw.text((20, 15), image_path.name, fill="black")

        paste_x = (card_width - preview.width) // 2
        card.paste(preview, (paste_x, 55))
        cards.append(card)

    columns = 2
    rows = (len(cards) + columns - 1) // columns
    cell_height = max(card.height for card in cards) + 20

    sheet = Image.new(
        "RGB",
        (columns * card_width, rows * cell_height),
        (230, 230, 230),
    )

    for index, card in enumerate(cards):
        x = (index % columns) * card_width
        y = (index // columns) * cell_height
        sheet.paste(card, (x, y))

    sheet.save(output_path, optimize=True)


def main() -> None:
    pdf_path = find_pdf()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)

    generated_paths: list[Path] = []

    with fitz.open(pdf_path) as document:
        if len(document) < 12:
            raise ValueError(
                "The PDF has fewer than 12 pages. Check that you are using "
                "the correct 2563 POSN physics exam PDF."
            )

        for problem in PROBLEMS:
            page = document[problem.page_index]
            image = render_crop(page, problem)

            output_path = OUTPUT_DIR / problem.filename
            image.save(output_path, format="PNG", optimize=True)
            generated_paths.append(output_path)

            print(
                f"Created: {output_path} "
                f"({image.width} x {image.height} px)"
            )

    preview_path = VERIFICATION_DIR / "posn63_mechanics_crop_preview.png"
    create_contact_sheet(generated_paths, preview_path)

    print()
    print("Finished cropping the 2563 mechanics-related questions.")
    print(f"Verification preview: {preview_path}")
    print()
    print("Open the preview with:")
    print(f'  xdg-open "{preview_path}"')


if __name__ == "__main__":
    main()