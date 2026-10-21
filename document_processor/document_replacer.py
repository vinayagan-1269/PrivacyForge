import json
import re
from pathlib import Path

from docx import Document


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

ENTITIES_FILE = DATA_DIR / "pseudonymized_entities.json"
OUTPUT_DIR = BASE_DIR / "output"


def normalize_path(path):
    """
    Normalize file paths for reliable comparisons on Windows.
    """
    return str(Path(path).resolve()).casefold()


def load_pseudonymized_entities(entities_file):
    """
    Load entities and their assigned pseudonyms from JSON.
    """
    with open(entities_file, "r", encoding="utf-8") as file:
        entities = json.load(file)

    if not isinstance(entities, list):
        raise ValueError(
            "Expected pseudonymized_entities.json to contain a list."
        )

    return entities


def get_replacements(entities, source_file):
    """
    Build a mapping of original text to pseudonym.

    Only entities detected in the selected source document
    are included.
    """
    source_path = normalize_path(source_file)
    replacements = {}

    for entity in entities:
        pseudonym = entity.get("pseudonym")
        canonical_text = entity.get("canonical_text")

        if not pseudonym:
            continue

        for mention in entity.get("mentions", []):
            mention_source = mention.get("source")

            if not mention_source:
                continue

            if normalize_path(mention_source) != source_path:
                continue

            original_text = mention.get("text") or canonical_text

            if not original_text:
                continue

            # Prefer the longer original text when duplicates exist.
            replacements[original_text] = pseudonym

    return replacements


def replace_text_in_paragraph(paragraph, replacements):
    """
    Replace sensitive text in a paragraph.

    Matching is case-insensitive.
    Paragraph structure and paragraph-level styling are retained.

    Note: Rebuilding paragraph text can remove individual run-level
    formatting such as bold or italic within modified paragraphs.
    """
    original_text = paragraph.text

    if not original_text:
        return 0

    updated_text = original_text
    replacement_count = 0

    # Longer strings first to avoid replacing a short entity
    # before a longer entity containing the same text.
    sorted_replacements = sorted(
        replacements.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for original, pseudonym in sorted_replacements:
        pattern = re.compile(re.escape(original), re.IGNORECASE)

        updated_text, count = pattern.subn(
            lambda match: pseudonym,
            updated_text
        )

        replacement_count += count

    if updated_text != original_text:
        # Assigning paragraph.text retains paragraph-level styling,
        # but may reset inline formatting across its runs.
        paragraph.text = updated_text

    return replacement_count


def process_paragraphs(paragraphs, replacements):
    """
    Process a collection of paragraphs.
    """
    total_replacements = 0

    for paragraph in paragraphs:
        total_replacements += replace_text_in_paragraph(
            paragraph,
            replacements
        )

    return total_replacements


def process_table(table, replacements):
    """
    Process text inside table cells, including nested tables.
    """
    total_replacements = 0

    for row in table.rows:
        for cell in row.cells:
            total_replacements += process_paragraphs(
                cell.paragraphs,
                replacements
            )

            # Handle nested tables inside cells.
            for nested_table in cell.tables:
                total_replacements += process_table(
                    nested_table,
                    replacements
                )

    return total_replacements


def sanitize_docx(input_file, entities_file=ENTITIES_FILE):
    """
    Replace detected sensitive information in a DOCX document.

    The original document is never overwritten.
    """
    input_file = Path(input_file).resolve()
    entities_file = Path(entities_file).resolve()

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input document not found: {input_file}"
        )

    if input_file.suffix.lower() != ".docx":
        raise ValueError(
            "This version supports DOCX files only."
        )

    if not entities_file.exists():
        raise FileNotFoundError(
            f"Entity file not found: {entities_file}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    entities = load_pseudonymized_entities(entities_file)

    replacements = get_replacements(
        entities,
        input_file
    )

    if not replacements:
        raise ValueError(
            "No matching pseudonymized entities were found for "
            f"this document: {input_file.name}. "
            "Check whether detection was run on this exact file."
        )

    document = Document(input_file)

    replacement_count = 0

    # Replace text in ordinary paragraphs.
    replacement_count += process_paragraphs(
        document.paragraphs,
        replacements
    )

    # Replace text in tables.
    for table in document.tables:
        replacement_count += process_table(
            table,
            replacements
        )

    # Replace text in headers and footers.
    for section in document.sections:
        replacement_count += process_paragraphs(
            section.header.paragraphs,
            replacements
        )

        replacement_count += process_paragraphs(
            section.footer.paragraphs,
            replacements
        )

        for table in section.header.tables:
            replacement_count += process_table(
                table,
                replacements
            )

        for table in section.footer.tables:
            replacement_count += process_table(
                table,
                replacements
            )

    # Never overwrite the original.
    output_file = OUTPUT_DIR / (
        f"{input_file.stem}_sanitized.docx"
    )

    document.save(output_file)

    print("\n" + "=" * 45)
    print("DOCUMENT SANITIZATION COMPLETED")
    print("=" * 45)

    print(f"Input document:       {input_file}")
    print(f"Unique entities:      {len(replacements)}")
    print(f"Text replacements:    {replacement_count}")
    print(f"Sanitized document:   {output_file}")

    if replacement_count == 0:
        print(
            "\nWARNING: No text was replaced. "
            "Inspect the entity locations and document content."
        )

    print("=" * 45)

    return output_file


if __name__ == "__main__":

    # Replace this with the path to the DOCX document
    # that you have already processed through the detection pipeline.
    input_document = (
        r"D:\studies PDF\optiv project"
        r"\case study\Case Study 2 Supporting Material"
        r"\Cadence_TPRM_Training.docx"
    )

    sanitize_docx(input_document)
