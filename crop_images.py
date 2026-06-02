from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import fitz  # PyMuPDF
from PIL import Image, ImageChops, ImageDraw


# =========================================================
# Configuration
# =========================================================

PDF_PATH: Final[Path] = Path("Ref/physics_posn_63.pdf")
OUTPUT_DIR: Final[Path] = Path("img")
VERIFICATION_DIR: Final[Path] = Path("verification")

# Rendering at 3 times the native PDF resolution gives clear images
# while keeping the output file sizes reasonable.
ZOOM: Final[float] = 3.0

# Used when removing unnecessary white margins around each crop.
WHITE_THRESHOLD: Final[int] = 8
TRIM_PADDING: Final[int] = 24


@dataclass(frozen=True)
class MaskRectangle:
    """
    A white rectangle drawn after rendering.

    Coordinates are pixel coordinates inside the rendered crop,
    not PDF coordinates.
    """

    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class ProblemCrop:
    """
    Definition of one question crop.

    page_index:
        Zero-based PDF page index.
        The uploaded PDF includes its cover page, so question 8 is
        located at page index 3 even though the exam page says page 3 of 11.

    crop_box:
        PDF coordinates in points:
        (left, top, right, bottom)
    """

    output_filename: str
    page_index: int
    crop_box: tuple[float, float, float, float]
    masks: tuple[MaskRectangle, ...] = ()


# =========================================================
# Exact crop positions for the uploaded 2563 exam PDF
# =========================================================

PROBLEM_CROPS: Final[tuple[ProblemCrop, ...]] = (
    ProblemCrop(
        output_filename="posn63centerq8.png",
        page_index=3,
        crop_box=(28, 281, 580, 480),

        # The figure from question 7 contains a small curved line extending
        # slightly below its question region. It is unrelated to question 8.
        # This mask removes only that stray line without affecting question 8.
        masks=(
            MaskRectangle(
                left=0,
                top=0,
                right=1656,
                bottom=60,
            ),
        ),
    ),
    ProblemCrop(
        output_filename="posn63centerq9.png",
        page_index=3,
        crop_box=(28, 492, 580, 762),
    ),
    ProblemCrop(
        output_filename="posn63centerq30.png",
        page_index=11,
        crop_box=(28, 300, 580, 552),
    ),
)


# =========================================================
# Image processing functions
# =========================================================

def trim_white_margin(
    image: Image.Image,
    padding: int = TRIM_PADDING,
) -> Image.Image:
    """
    Remove excessive white space while preserving a comfortable margin.

    The crop coordinates already prevent neighboring questions from
    appearing. This function only makes the final PNG more compact.
    """

    rgb_image = image.convert("RGB")
    white_background = Image.new("RGB", rgb_image.size, "white")

    difference = ImageChops.difference(
        rgb_image,
        white_background,
    ).convert("L")

    difference = difference.point(
        lambda pixel: 255 if pixel > WHITE_THRESHOLD else 0
    )

    content_box = difference.getbbox()

    if content_box is None:
        return rgb_image

    left, top, right, bottom = content_box

    return rgb_image.crop(
        (
            max(0, left - padding),
            max(0, top - padding),
            min(rgb_image.width, right + padding),
            min(rgb_image.height, bottom + padding),
        )
    )


def render_problem_crop(
    page: fitz.Page,
    problem: ProblemCrop,
) -> Image.Image:
    """
    Render one cropped question from the PDF as a high-resolution PNG.
    """

    crop_rectangle = fitz.Rect(*problem.crop_box)

    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(ZOOM, ZOOM),
        clip=crop_rectangle,
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
                (
                    mask.left,
                    mask.top,
                    mask.right,
                    mask.bottom,
                ),
                fill="white",
            )

    return trim_white_margin(image)


def create_verification_contact_sheet(
    image_paths: list[Path],
    output_path: Path,
) -> None:
    """
    Create one preview image containing all generated crops.

    Open this contact sheet once after running the script to quickly
    confirm that every question is complete.
    """

    cards: list[Image.Image] = []

    for image_path in image_paths:
        image = Image.open(image_path).convert("RGB")

        preview = image.copy()
        preview.thumbnail((1200, 720))

        card_width = 1240
        card_height = preview.height + 90

        card = Image.new(
            "RGB",
            (card_width, card_height),
            "white",
        )

        x_position = (card_width - preview.width) // 2
        card.paste(preview, (x_position, 50))

        draw = ImageDraw.Draw(card)
        draw.text(
            (20, 16),
            image_path.name,
            fill="black",
        )

        cards.append(card)

    separator_height = 24
    total_height = (
        sum(card.height for card in cards)
        + separator_height * (len(cards) - 1)
    )

    contact_sheet = Image.new(
        "RGB",
        (1240, total_height),
        (235, 235, 235),
    )

    current_y = 0

    for card in cards:
        contact_sheet.paste(card, (0, current_y))
        current_y += card.height + separator_height

    contact_sheet.save(output_path, optimize=True)


# =========================================================
# Main program
# =========================================================

def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find '{PDF_PATH}'. "
            "Place this script in the same directory as physics_posn_63.pdf "
            "or update PDF_PATH near the top of the script."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)

    generated_images: list[Path] = []

    with fitz.open(PDF_PATH) as document:
        if len(document) < 12:
            raise ValueError(
                "The PDF has fewer pages than expected. "
                "Check that you are using the correct physics_posn_63.pdf file."
            )

        for problem in PROBLEM_CROPS:
            page = document[problem.page_index]
            cropped_image = render_problem_crop(page, problem)

            output_path = OUTPUT_DIR / problem.output_filename

            cropped_image.save(
                output_path,
                format="PNG",
                optimize=True,
            )

            generated_images.append(output_path)

            print(
                f"Created: {output_path} "
                f"({cropped_image.width} x {cropped_image.height} px)"
            )

    contact_sheet_path = (
        VERIFICATION_DIR / "posn63_temperature_contact_sheet.png"
    )

    create_verification_contact_sheet(
        generated_images,
        contact_sheet_path,
    )

    print()
    print("Finished cropping the 2563 temperature questions.")
    print(f"Verification preview: {contact_sheet_path}")
    print()
    print("Generated files:")

    for image_path in generated_images:
        print(f"  - {image_path}")


if __name__ == "__main__":
    main()