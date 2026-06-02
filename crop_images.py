
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import sys

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageOps


# =========================================================
# POSN image cropper for chapter-12-temperature.tex
#
# Run from the LaTeX project root:
#   python crop_temperature_images.py
#
# Install dependencies once if needed:
#   python -m pip install pymupdf pillow
#
# Verified source PDFs currently present in this project:
#   Ref/posn1-60-physics.pdf
#   Ref/posn1-61-physics.pdf
#   Ref/posn1-62-physics.pdf
#   Ref/posn1-67-physics-1.pdf
#   Ref/06-*.pdf  (the POSN 2568 paper)
#
# Output images:
#   img/posn60p1q18.png
#   img/posn60p2q9.png
#   img/posn61q18.png
#   img/posn61p2q9.png
#   img/posn62q7.png
#   img/posn62q8.png
#   img/posn67q15.png
#   img/posn68q9.png
#   img/posn68q10.png
#
# The 2563-center paper is not present in the uploaded working folder.
# Therefore this verified script intentionally does not generate:
#   img/posn63centerq8.png
#   img/posn63centerq9.png
#   img/posn63centerq30.png
# =========================================================


ROOT = Path(__file__).resolve().parent
REF_DIR = ROOT / "Ref"
OUT_DIR = ROOT / "img"
PREVIEW_PATH = OUT_DIR / "_temperature_crop_preview.png"
DPI = 300


@dataclass(frozen=True)
class ProblemCrop:
    output_name: str
    source_pdf: str
    page: int  # 1-based page number
    crop: tuple[float, float, float, float]  # left, top, right, bottom in PDF coordinates
    title: str


# These rectangles were visually checked against the source PDFs.
# Each rectangle includes the entire question and its figure or choices,
# while stopping inside whitespace before the neighboring question.
PROBLEMS: tuple[ProblemCrop, ...] = (
    ProblemCrop(
        output_name="posn60p1q18.png",
        source_pdf="posn1-60-physics.pdf",
        page=8,
        crop=(64, 193, 533, 382),
        title="ปี 2560 ตอนที่ 1 ข้อ 18: น้ำร้อนผสมกับน้ำมันในภาชนะฉนวน",
    ),
    ProblemCrop(
        output_name="posn60p2q9.png",
        source_pdf="posn1-60-physics.pdf",
        page=11,
        crop=(64, 412, 533, 610),
        title="ปี 2560 ตอนที่ 2 ข้อ 9: ทรงกระบอกและทรงกลมทองแดงขยายตัว",
    ),
    ProblemCrop(
        output_name="posn61q18.png",
        source_pdf="posn1-61-physics.pdf",
        page=9,
        crop=(85, 246, 532, 512),
        title="ปี 2561 ข้อ 18: แถบโลหะสองชนิดโค้งเป็นวงกลม",
    ),
    ProblemCrop(
        output_name="posn61p2q9.png",
        source_pdf="posn1-61-physics.pdf",
        page=14,
        crop=(85, 60, 532, 206),
        title="ปี 2561 ตอนที่ 2 ข้อ 9: โลหะร้อน น้ำ และน้ำแข็ง",
    ),
    ProblemCrop(
        output_name="posn62q7.png",
        source_pdf="posn1-62-physics.pdf",
        page=3,
        crop=(83, 603, 540, 768),
        title="ปี 2562 ข้อ 7: การกระจายอุณหภูมิในแท่งเนื้อเดียว",
    ),
    ProblemCrop(
        output_name="posn62q8.png",
        source_pdf="posn1-62-physics.pdf",
        page=4,
        crop=(83, 64, 540, 197),
        title="ปี 2562 ข้อ 8: คาบลูกตุ้มเมื่อเส้นลวดขยายตัว",
    ),
    ProblemCrop(
        output_name="posn67q15.png",
        source_pdf="posn1-67-physics-1.pdf",
        page=6,
        crop=(48, 73, 550, 424),
        title="ปี 2567 ข้อ 15: การนำความร้อนร่วมกับการแผ่รังสี",
    ),
    ProblemCrop(
        output_name="posn68q9.png",
        source_pdf="__POSN_2568__",
        page=3,
        crop=(48, 424, 550, 582),
        title="ปี 2568 ข้อ 9: อัตราการไหลของพลังงานผ่านท่อนำความร้อน",
    ),
    ProblemCrop(
        output_name="posn68q10.png",
        source_pdf="__POSN_2568__",
        page=3,
        crop=(48, 583, 550, 765),
        title="ปี 2568 ข้อ 10: อุณหภูมิที่รอยต่อของท่อนำความร้อน",
    ),
)


MISSING_SOURCE_OUTPUTS = (
    "img/posn63centerq8.png",
    "img/posn63centerq9.png",
    "img/posn63centerq30.png",
)


def find_posn_2568_pdf() -> Path:
    """
    Locate the POSN 2568 PDF without depending on its escaped Thai filename.

    The uploaded folder stores this PDF with an escaped filename beginning
    with '06-', so matching Ref/06-*.pdf is more reliable than hard-coding
    the complete filename.
    """
    candidates = sorted(REF_DIR.glob("06-*.pdf"))

    if not candidates:
        raise FileNotFoundError(
            "Cannot find the POSN 2568 PDF. "
            "Expected one file matching Ref/06-*.pdf"
        )

    for candidate in candidates:
        try:
            with fitz.open(candidate) as document:
                first_page_text = document[0].get_text("text")

            if "2568" in first_page_text:
                return candidate
        except Exception:
            continue

    if len(candidates) == 1:
        return candidates[0]

    raise FileNotFoundError(
        "Found multiple Ref/06-*.pdf files but could not identify "
        "the POSN 2568 paper."
    )


def resolve_pdf(source_pdf: str) -> Path:
    """
    Convert the PDF identifier stored in PROBLEMS into an actual file path.
    """
    if source_pdf == "__POSN_2568__":
        return find_posn_2568_pdf()

    return REF_DIR / source_pdf


def render_crop(
    problem: ProblemCrop,
    pdf_path: Path,
    output_path: Path,
) -> None:
    """
    Render one rectangular region from a PDF page into a high-resolution PNG.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing source PDF: {pdf_path}")

    with fitz.open(pdf_path) as document:
        if problem.page < 1 or problem.page > document.page_count:
            raise ValueError(
                f"Page {problem.page} is outside {pdf_path.name}; "
                f"the PDF has {document.page_count} pages."
            )

        page = document[problem.page - 1]
        rectangle = fitz.Rect(*problem.crop)

        if not page.rect.contains(rectangle):
            raise ValueError(
                f"Crop rectangle {problem.crop} is outside page size "
                f"{page.rect} for {pdf_path.name}, page {problem.page}."
            )

        matrix = fitz.Matrix(DPI / 72, DPI / 72)

        pixmap = page.get_pixmap(
            matrix=matrix,
            clip=rectangle,
            alpha=False,
        )

        pixmap.save(output_path)


def nonwhite_bbox(
    image: Image.Image,
    threshold: int = 248,
):
    """
    Return the smallest box containing visible content.

    Near-white pixels are treated as background. This allows the script
    to detect obviously blank crops and crops that may have clipped text.
    """
    grayscale = image.convert("L")

    mask = grayscale.point(
        lambda pixel: 255 if pixel < threshold else 0
    )

    return mask.getbbox()


def validate_crop(
    image_path: Path,
) -> tuple[bool, str]:
    """
    Detect obvious crop failures.

    This checks that:
    1. The crop is not blank.
    2. Visible text or a figure is not touching an image edge.

    The rectangles were also manually reviewed against the source PDFs,
    so this automatic check acts as an additional guard.
    """
    image = Image.open(image_path).convert("RGB")
    bounding_box = nonwhite_bbox(image)

    if bounding_box is None:
        return False, "crop is blank"

    left, top, right, bottom = bounding_box
    width, height = image.size

    margins = {
        "left": left,
        "top": top,
        "right": width - right,
        "bottom": height - bottom,
    }

    minimum_margin = min(margins.values())

    if minimum_margin < 4:
        return (
            False,
            f"visible content is too close to an edge: {margins}",
        )

    return (
        True,
        f"size={width}x{height}, visible-content margins={margins}",
    )


def make_preview(
    image_paths: Iterable[Path],
    preview_path: Path,
) -> None:
    """
    Create a vertical contact sheet containing all generated crops.

    Open img/_temperature_crop_preview.png after running the script
    to review every question at once.
    """
    cards: list[Image.Image] = []

    card_width = 1000
    padding = 30
    label_height = 52

    for path in image_paths:
        image = Image.open(path).convert("RGB")

        image.thumbnail(
            (card_width - 2 * padding, 650)
        )

        card = Image.new(
            "RGB",
            (
                card_width,
                image.height + label_height + 2 * padding,
            ),
            "white",
        )

        draw = ImageDraw.Draw(card)

        draw.text(
            (padding, 16),
            path.name,
            fill="black",
        )

        x = (card_width - image.width) // 2
        y = label_height + padding

        card.paste(
            image,
            (x, y),
        )

        cards.append(
            ImageOps.expand(
                card,
                border=1,
                fill="black",
            )
        )

    total_height = (
        sum(card.height for card in cards)
        + padding * (len(cards) + 1)
    )

    sheet = Image.new(
        "RGB",
        (
            card_width + 2 * padding,
            total_height,
        ),
        (235, 235, 235),
    )

    current_y = padding

    for card in cards:
        sheet.paste(
            card,
            (padding, current_y),
        )

        current_y += card.height + padding

    sheet.save(preview_path)


def main() -> int:
    """
    Generate all verified temperature-chapter problem crops.
    """
    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "Cropping verified POSN images "
        "for the temperature chapter...\n"
    )

    created: list[Path] = []
    failures: list[str] = []

    for problem in PROBLEMS:
        pdf_path = resolve_pdf(
            problem.source_pdf
        )

        output_path = OUT_DIR / problem.output_name

        try:
            render_crop(
                problem=problem,
                pdf_path=pdf_path,
                output_path=output_path,
            )

            passed, details = validate_crop(
                output_path
            )

            status = "OK" if passed else "CHECK"

            print(
                f"{status:5} "
                f"{output_path.relative_to(ROOT)}"
            )

            print(
                f"      {problem.title}"
            )

            print(
                f"      source={pdf_path.relative_to(ROOT)}, "
                f"page={problem.page}"
            )

            print(
                f"      {details}"
            )

            created.append(
                output_path
            )

            if not passed:
                failures.append(
                    problem.output_name
                )

        except Exception as error:
            print(
                f"ERROR {problem.output_name}: {error}",
                file=sys.stderr,
            )

            failures.append(
                problem.output_name
            )

    if created:
        make_preview(
            image_paths=created,
            preview_path=PREVIEW_PATH,
        )

        print(
            "\nPreview contact sheet: "
            f"{PREVIEW_PATH.relative_to(ROOT)}"
        )

    print(
        "\nNot generated because the required "
        "2563-center source PDF is absent:"
    )

    for missing_output in MISSING_SOURCE_OUTPUTS:
        print(
            f"  - {missing_output}"
        )

    if failures:
        print(
            "\nSome generated files need inspection:",
            file=sys.stderr,
        )

        for name in failures:
            print(
                f"  - {name}",
                file=sys.stderr,
            )

        return 1

    print(
        "\nDone. All available temperature-chapter crops "
        "passed the automated edge checks."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
