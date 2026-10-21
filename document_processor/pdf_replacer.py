import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

import pymupdf

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer
)

from extractors.pdf_extractor import extract_pdf
from pii.regex_engine import detect_regex_pii


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

ENTITIES_FILE = DATA_DIR / "pseudonymized_entities.json"


def _normalise_path(value):
    """Normalize paths for source-document matching."""

    try:
        return str(
            Path(value).resolve()
        ).casefold()

    except (TypeError, OSError, ValueError):
        return str(value).casefold()


def _load_entities(entities_file):
    """Load pseudonymized entities from JSON."""

    if not entities_file.is_file():
        raise FileNotFoundError(
            f"Pseudonymized entities file not found: "
            f"{entities_file}"
        )

    with entities_file.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("entities", [])

    if not isinstance(data, list):
        raise ValueError(
            "pseudonymized_entities.json must contain "
            "a list of entity records."
        )

    return data


def _build_replacements(entities, input_file):
    """
    Build a dictionary mapping original PII values
    to their existing pseudonyms.

    Expected entity structure:

    {
        "pseudonym": "[PERSON_00001]",
        "mentions": [
            {
                "source": "path/to/document.pdf",
                "text": "Miriam T. Achebe"
            }
        ]
    }
    """

    target_path = _normalise_path(input_file)

    replacements = {}

    for entity in entities:

        if not isinstance(entity, dict):
            continue

        pseudonym = entity.get("pseudonym")

        if not pseudonym:
            continue

        mentions = entity.get("mentions", [])

        # Support flat records if they contain their own source.
        if not mentions and entity.get("source"):
            mentions = [entity]

        for mention in mentions:

            if not isinstance(mention, dict):
                continue

            source = (
                mention.get("source")
                or entity.get("source")
            )

            # Ignore mentions from other documents.
            if (
                source
                and _normalise_path(source) != target_path
            ):
                continue

            original = (
                mention.get("text")
                or mention.get("canonical_text")
                or entity.get("canonical_text")
                or entity.get("text")
            )

            if not isinstance(original, str):
                continue

            original = original.strip()

            if len(original) < 2:
                continue

            replacements[original] = str(pseudonym)

    return replacements


def _replace_text(text, replacements):
    """
    Replace detected PII with its pseudonym.

    Longer values are replaced first to reduce the risk
    of replacing part of a longer name prematurely.
    """

    for original in sorted(
        replacements,
        key=len,
        reverse=True
    ):

        pseudonym = replacements[original]

        # Allow whitespace variations between words.
        # This helps with some OCR line-break differences.
        parts = re.split(
            r"\s+",
            original.strip()
        )

        pattern = r"\s+".join(
            re.escape(part)
            for part in parts
        )

        text = re.sub(
            pattern,
            lambda _match, token=pseudonym: token,
            text,
            flags=re.IGNORECASE
        )

    return text



def _normalise_phone(value):
    """Return only digits for phone-number comparison."""
    return re.sub(r"\\D", "", value or "")


def _add_regex_phone_replacements(page_text, replacements):
    """
    Run the regex engine on this page's extracted text and match phone
    detections to existing pseudonyms using normalized digits.
    This does not create or alter persistent pseudonym mappings.
    """
    page_replacements = dict(replacements)
    detections = detect_regex_pii(page_text)

    phone_keys = [
        (original, pseudonym)
        for original, pseudonym in replacements.items()
        if _normalise_phone(original)
    ]

    for detection in detections:
        if detection.get("type") != "PHONE_PATTERN":
            continue

        detected_text = detection.get("text", "")
        detected_digits = _normalise_phone(detected_text)

        if len(detected_digits) < 7:
            continue

        exact_matches = [
            (original, pseudonym)
            for original, pseudonym in phone_keys
            if _normalise_phone(original) == detected_digits
        ]

        if len(exact_matches) == 1:
            page_replacements[detected_text] = exact_matches[0][1]
            continue

        # Compatibility with entities created by the older pattern, which
        # could detect only the final 7 digits of a 10-digit phone number.
        suffix_matches = [
            (original, pseudonym)
            for original, pseudonym in phone_keys
            if len(_normalise_phone(original)) >= 7
            and len(_normalise_phone(original)) < len(detected_digits)
            and detected_digits.endswith(_normalise_phone(original))
        ]

        # Only use suffix matching when it identifies one unambiguous entity.
        if len(suffix_matches) == 1:
            page_replacements[detected_text] = suffix_matches[0][1]

    return page_replacements

def _make_styles():
    """Create readable styles for the reconstructed PDF."""

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="RebuiltBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
            spaceAfter=5,
            wordWrap="CJK"
        )
    )

    styles.add(
        ParagraphStyle(
            name="RebuiltHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=6,
            keepWithNext=True
        )
    )

    styles.add(
        ParagraphStyle(
            name="RebuiltSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.grey,
            spaceAfter=5
        )
    )

    return styles


def _looks_like_heading(line):
    """Identify likely headings using simple text heuristics."""

    line = line.strip()

    if not line:
        return False

    numbered_heading = re.match(
        r"^(SECTION\s+\d+|\d+(?:\.\d+)*\.?\s+[A-Z])",
        line,
        re.IGNORECASE
    )

    return (
        len(line) <= 90
        and (
            bool(numbered_heading)
            or line.isupper()
        )
    )


def _page_to_flowables(
    page_text,
    page_number,
    styles
):
    """
    Convert one page of sanitized text into PDF elements.

    This reconstructs basic formatting rather than the
    original page's exact positioning.
    """

    flowables = [
        Paragraph(
            (
                "Reconstructed sanitized document "
                f"| Source page {page_number}"
            ),
            styles["RebuiltSmall"]
        ),
        Spacer(1, 2 * mm)
    ]

    blocks = re.split(
        r"\n\s*\n",
        page_text.strip()
    )

    for block in blocks:

        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        # Escape text before passing it to ReportLab's
        # paragraph parser.
        content = "<br/>".join(
            escape(line)
            for line in lines
        )

        if (
            len(lines) == 1
            and _looks_like_heading(lines[0])
        ):
            style = styles["RebuiltHeading"]

        else:
            style = styles["RebuiltBody"]

        flowables.append(
            Paragraph(content, style)
        )

        flowables.append(
            Spacer(1, 1.5 * mm)
        )

    return flowables


def sanitize_pdf(
    input_file,
    entities_file=ENTITIES_FILE
):
    """
    Rebuild a sanitized PDF from extracted text.

    Maintains compatibility with process_document.py.

    Output:
        output/<original_filename>_sanitized.pdf
    """

    input_file = Path(input_file).resolve()
    entities_file = Path(entities_file).resolve()

    if not input_file.is_file():
        raise FileNotFoundError(
            f"Input PDF not found: {input_file}"
        )

    if input_file.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF input, got: "
            f"{input_file.suffix}"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Load existing pseudonyms.
    entities = _load_entities(entities_file)

    replacements = _build_replacements(
        entities,
        input_file
    )

    if not replacements:
        print(
            "Warning: No source-matched pseudonym "
            "replacements were loaded."
        )

    # Extract the original PDF page by page.
    extracted_pages = extract_pdf(input_file)

    if not extracted_pages:
        raise ValueError(
            "No text could be extracted from the PDF."
        )

    output_file = (
        OUTPUT_DIR
        / f"{input_file.stem}_sanitized.pdf"
    )

    styles = _make_styles()
    story = []

    for index, record in enumerate(extracted_pages):

        page_number = (
            record.get("location", {}).get(
                "page",
                index + 1
            )
        )

        original_text = record.get("text", "")

        # Run the regex engine directly on this page's extracted text.
        # Reuse existing pseudonyms rather than generating new mappings.
        page_replacements = _add_regex_phone_replacements(
            original_text,
            replacements
        )

        # Replace PII before generating the new PDF.
        sanitized_text = _replace_text(
            original_text,
            page_replacements
        )

        story.extend(
            _page_to_flowables(
                sanitized_text,
                page_number,
                styles
            )
        )

        # Start the next extracted source page separately.
        if index < len(extracted_pages) - 1:
            story.append(PageBreak())

    # Build the reconstructed PDF.
    document = SimpleDocTemplate(
        str(output_file),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Sanitized - {input_file.stem}",
        author="PrivacyForge"
    )

    document.build(story)

    # Verify that the output is a readable PDF file.
    with pymupdf.open(str(output_file)) as check:

        if len(check) == 0:
            raise RuntimeError(
                "The rebuilt PDF contains no pages."
            )

    print(
        f"Sanitized PDF created: {output_file}"
    )

    print(
        f"Replacement values loaded: "
        f"{len(replacements)}"
    )

    print(
        f"Source pages processed: "
        f"{len(extracted_pages)}"
    )

    return output_file


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Rebuild a PDF after replacing detected PII."
        )
    )

    parser.add_argument(
        "input_pdf",
        help="Path to the source PDF"
    )

    parser.add_argument(
        "--entities",
        default=str(ENTITIES_FILE),
        help="Path to pseudonymized_entities.json"
    )

    args = parser.parse_args()

    sanitize_pdf(
        args.input_pdf,
        args.entities
    )
