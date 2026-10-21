from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output


def _ocr_page(page):
    """Extract OCR text while preserving line structure where possible."""

    pixmap = page.get_pixmap(
        dpi=300,
        colorspace=pymupdf.csRGB,
        alpha=False
    )

    image = Image.open(BytesIO(pixmap.tobytes("png")))

    data = pytesseract.image_to_data(
        image,
        output_type=Output.DICT,
        config="--psm 3"
    )

    lines = {}

    for i, raw_word in enumerate(data.get("text", [])):
        word = (raw_word or "").strip()

        if not word:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i]
        )

        lines.setdefault(key, []).append(
            (int(data["left"][i]), word)
        )

    extracted_lines = []

    for key in sorted(lines):
        words = sorted(
            lines[key],
            key=lambda item: item[0]
        )

        line = " ".join(
            word for _, word in words
        ).strip()

        if line:
            extracted_lines.append(line)

    return "\n".join(extracted_lines).strip()


def extract_pdf(file_path):
    """
    Extract text from a PDF.

    Returns one record per page:
    {
        "text": extracted_text,
        "source": absolute_file_path,
        "location": {
            "type": "page",
            "page": page_number
        },
        "extraction_method": "native" or "ocr"
    }
    """

    file_path = Path(file_path).resolve()

    if not file_path.is_file():
        raise FileNotFoundError(
            f"PDF file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file, got: {file_path.suffix}"
        )

    results = []

    with pymupdf.open(str(file_path)) as document:

        total_pages = len(document)

        for page_number, page in enumerate(
            document,
            start=1
        ):

            print(
                f"Extracting PDF page "
                f"{page_number}/{total_pages}..."
            )

            # First, attempt native text extraction.
            native_text = page.get_text(
                "text",
                sort=True
            ).strip()

            if native_text:
                text = native_text
                method = "native"

            else:
                # Fall back to OCR for scanned pages.
                text = _ocr_page(page)
                method = "ocr"

            if not text:
                print(
                    f"Warning: No text extracted "
                    f"from page {page_number}."
                )
                continue

            results.append({
                "text": text,
                "source": str(file_path),
                "location": {
                    "type": "page",
                    "page": page_number
                },
                "extraction_method": method
            })

    print(
        f"PDF extraction completed: "
        f"{len(results)} page records generated."
    )

    return results
