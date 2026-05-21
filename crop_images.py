from pathlib import Path
import fitz
from PIL import Image


# =========================================================
# POSN problem image cropper for Rotation chapter
# Run from your LaTeX project root.
#
# Required source PDFs in the same folder:
#   posn1-61-physics.pdf
#   posn1-62-physics.pdf
#   posn1-66-physics.pdf
#   posn1-67-physics-1.pdf
#
# Output:
#   img/posn67q4.png
#   img/posn61q10.png
#   img/posn62q19.png
#   img/posn62q22.png
#   img/posn62q23.png
#   img/posn66q28.png
# =========================================================


ROOT = Path(".").resolve()
OUT_DIR = ROOT / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DPI = 240


PROBLEMS = [
    {
        "name": "posn67q4",
        "pdf": "posn1-67-physics-1.pdf",
        "page": 3,
        "crop": (45, 45, 590, 145),
        "title": "ปี 2567 ข้อ 4: ล้อกลิ้งโดยไม่ไถลลงพื้นเอียง",
    },
    {
        "name": "posn61q10",
        "pdf": "posn1-61-physics.pdf",
        "page": 6,
        "crop": (80, 55, 555, 305),
        "title": "ปี 2561 ข้อ 10: ประตูกับแรงที่บานพับ",
    },
    {
        "name": "posn62q19",
        "pdf": "posn1-62-physics.pdf",
        "page": 7,
        "crop": (75, 190, 535, 365),
        "title": "ปี 2562 ข้อ 19: แท่งล้มบนพื้นลื่น",
    },
    {
        "name": "posn62q22",
        "pdf": "posn1-62-physics.pdf",
        "page": 8,
        "crop": (75, 80, 545, 500),
        "title": "ปี 2562 ข้อ 22: ล้อถูกดึงด้วยเชือกพันรอบเพลา",
    },
    {
        "name": "posn62q23",
        "pdf": "posn1-62-physics.pdf",
        "page": 8,
        "crop": (75, 500, 545, 770),
        "title": "ปี 2562 ข้อ 23: ความเร็วของจุดสีบนขอบล้อที่กลิ้ง",
    },
    {
        "name": "posn66q28",
        "pdf": "posn1-66-physics.pdf",
        "page": 11,
        "crop": (45, 202, 540, 590),
        "title": "ปี 2566 ข้อ 28: แผ่นสี่เหลี่ยมแขวนและมวลถ่วง",
    },
]


def crop_pdf_to_png(pdf_path: Path, page_number: int, crop_box: tuple, output_path: Path, dpi: int = 240) -> None:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Missing source PDF: {pdf_path}")

    doc = fitz.open(pdf_path)

    if page_number < 1 or page_number > doc.page_count:
        raise ValueError(
            f"Page {page_number} is outside range for {pdf_path.name}. "
            f"This PDF has {doc.page_count} pages."
        )

    page = doc[page_number - 1]
    rect = fitz.Rect(*crop_box)

    if not page.rect.contains(rect):
        raise ValueError(
            f"Crop box {crop_box} is outside page size {page.rect} "
            f"for {pdf_path.name}, page {page_number}."
        )

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    pix.save(output_path)

    doc.close()


def image_content_check(image_path: Path, white_threshold: int = 248, min_nonwhite_ratio: float = 0.005):
    """
    Basic safety check:
    Makes sure the crop is not blank.
    It does not replace visual inspection, but catches wrong page or empty crop mistakes.
    """
    img = Image.open(image_path).convert("L")
    width, height = img.size

    nonwhite = 0
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            if pixels[x, y] < white_threshold:
                nonwhite += 1

    ratio = nonwhite / (width * height)
    ok = ratio >= min_nonwhite_ratio

    return ok, ratio, (width, height)


def write_latex_link_snippets(output_path: Path) -> None:
    """
    Creates a small helper file showing the exact LaTeX include blocks.
    You do not need to paste this if your chapter already has the same \\IfFileExists blocks.
    """
    lines = []

    for item in PROBLEMS:
        image_name = f"img/{item['name']}.png"
        lines.append("% =========================================================")
        lines.append(f"% {item['title']}")
        lines.append(r"\vspace{1.5em}")
        lines.append(rf"\IfFileExists{{{image_name}}}{{")
        lines.append(r"\begin{center}")
        lines.append(rf"    \includegraphics[width=1\linewidth]{{{image_name}}}")
        lines.append(r"\end{center}")
        lines.append(r"}{")
        lines.append(r"\begin{tcolorbox}[title=ตำแหน่งภาพที่แนะนำ]")
        lines.append(f"ให้ตัดภาพข้อสอบแล้วบันทึกเป็น")
        lines.append("")
        lines.append(r"\[")
        lines.append(rf"\texttt{{{image_name}}}")
        lines.append(r"\]")
        lines.append(r"\end{tcolorbox}")
        lines.append(r"}")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("Cropping POSN images for the Rotation chapter...\n")

    failures = []

    for item in PROBLEMS:
        pdf_path = ROOT / item["pdf"]
        output_path = OUT_DIR / f"{item['name']}.png"

        crop_pdf_to_png(
            pdf_path=pdf_path,
            page_number=item["page"],
            crop_box=item["crop"],
            output_path=output_path,
            dpi=DPI,
        )

        ok, ratio, size = image_content_check(output_path)

        status = "OK" if ok else "CHECK"
        print(f"{status:5} {output_path}")
        print(f"      {item['title']}")
        print(f"      size={size[0]}x{size[1]}, nonwhite={ratio:.3%}")

        if not ok:
            failures.append(item["name"])

    snippet_path = ROOT / "rotation_problem_image_links.tex"
    write_latex_link_snippets(snippet_path)

    print("\nLaTeX helper snippets written to:")
    print(f"  {snippet_path}")

    if failures:
        raise RuntimeError(
            "Some crops look too blank. Please inspect these manually: "
            + ", ".join(failures)
        )

    print("\nDone. Images are ready in:")
    print(f"  {OUT_DIR}")


if __name__ == "__main__":
    main()