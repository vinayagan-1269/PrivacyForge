import json
from pathlib import Path

from pptx import Presentation


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

ENTITIES_FILE = DATA_DIR / "pseudonymized_entities.json"


def normalize_path(path):
    """Normalize file paths for reliable comparison."""
    return str(Path(path).resolve()).casefold()


def get_replacements(input_file, entities_file=ENTITIES_FILE):
    """
    Build a mapping of original PII values to pseudonyms.

    Only use mentions associated with the input document.
    """
    input_path = normalize_path(input_file)

    with open(entities_file, "r", encoding="utf-8") as file:
        entities = json.load(file)

    replacements = {}

    for entity in entities:
        pseudonym = entity.get("pseudonym")

        if not pseudonym:
            continue

        for mention in entity.get("mentions", []):
            source = mention.get("source")

            if not source:
                continue

            if normalize_path(source) != input_path:
                continue

            original = (
                mention.get("text")
                or mention.get("canonical_text")
            )

            if original:
                replacements[original] = pseudonym

    return replacements


def replace_in_paragraph(paragraph, replacements):
    """
    Replace detected PII without replacing arbitrary substrings.

    Longer values are processed first.
    Short, ambiguous values are ignored.
    """
    import re

    if not paragraph.runs:
        return 0

    original_text = paragraph.text
    updated_text = original_text
    replacement_count = 0

    # Prevent accidental replacement of ordinary single characters
    # and extremely short strings.
    valid_replacements = {
        original: pseudonym
        for original, pseudonym in replacements.items()
        if len(original.strip()) >= 3
    }

    for original in sorted(
        valid_replacements,
        key=len,
        reverse=True
    ):
        pseudonym = valid_replacements[original]

        # Require word boundaries for values consisting of
        # ordinary word characters.
        if re.fullmatch(r"\w+", original):
            pattern = re.compile(
                r"(?<!\w)" + re.escape(original) + r"(?!\w)",
                re.IGNORECASE
            )
        else:
            # Structured values such as email addresses and phone
            # numbers may contain spaces and punctuation.
            pattern = re.compile(
                re.escape(original),
                re.IGNORECASE
            )

        updated_text, count = pattern.subn(
            lambda match: pseudonym,
            updated_text
        )

        replacement_count += count

    if updated_text != original_text:
        # Preserve the first run's formatting where possible.
        paragraph.runs[0].text = updated_text

        # Clear the remaining runs because their text has been
        # incorporated into the first run.
        for run in paragraph.runs[1:]:
            run.text = ""

    return replacement_count

def sanitize_pptx(input_file, entities_file=ENTITIES_FILE):
    """
    Replace detected PII in a PowerPoint presentation.

    Returns the path of the sanitized presentation.
    """
    input_file = Path(input_file)

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input presentation not found: {input_file}"
        )

    if input_file.suffix.lower() != ".pptx":
        raise ValueError(
            "sanitize_pptx() accepts only .pptx files."
        )

    if not Path(entities_file).exists():
        raise FileNotFoundError(
            f"Pseudonymized entities file not found: {entities_file}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    replacements = get_replacements(
        input_file,
        entities_file
    )

    presentation = Presentation(str(input_file))

    total_replacements = 0

    for slide in presentation.slides:
        for shape in slide.shapes:

            # Process ordinary text and text inside grouped shapes.
            shapes_to_process = [shape]

            if shape.shape_type == 6:  # Grouped shape
                shapes_to_process.extend(
                    shape.shapes
                )

            for current_shape in shapes_to_process:

                if current_shape.has_text_frame:
                    for paragraph in current_shape.text_frame.paragraphs:
                        total_replacements += replace_in_paragraph(
                            paragraph,
                            replacements
                        )

                # Process tables.
                if current_shape.has_table:
                    for row in current_shape.table.rows:
                        for cell in row.cells:
                            for paragraph in cell.text_frame.paragraphs:
                                total_replacements += replace_in_paragraph(
                                    paragraph,
                                    replacements
                                )

    output_file = (
        OUTPUT_DIR
        / f"{input_file.stem}_sanitized.pptx"
    )

    presentation.save(str(output_file))

    print("\nPOWERPOINT SANITIZATION COMPLETED")
    print(f"Input presentation: {input_file}")
    print(f"Replacement values: {len(replacements)}")
    print(f"Text replacements: {total_replacements}")
    print(f"Sanitized presentation: {output_file}")

    return output_file
