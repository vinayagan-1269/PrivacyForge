import json
import re
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Existing pseudonym mapping
MAPPING_FILE = DATA_DIR / "pseudonym_mapping.json"


def load_pseudonym_mapping(mapping_file=MAPPING_FILE):
    """
    Load the existing pseudonym mapping.

    Expected mapping value:
    {
        "type": "PERSON",
        "original_value": "John Smith",
        "pseudonym": "[PERSON_00001]",
        "counter": 1
    }
    """
    mapping_file = Path(mapping_file)

    if not mapping_file.exists():
        raise FileNotFoundError(
            f"Pseudonym mapping not found: {mapping_file}"
        )

    with open(mapping_file, "r", encoding="utf-8") as file:
        mapping_data = json.load(file)

    # Convert the stored mapping into:
    # pseudonym -> original value
    reverse_mapping = {}

    for entry in mapping_data.values():
        pseudonym = entry.get("pseudonym")
        original_value = entry.get("original_value")

        if pseudonym and original_value is not None:
            reverse_mapping[pseudonym] = original_value

    return reverse_mapping


def reidentify_text(text, mapping_file=MAPPING_FILE):
    """
    Restore recognized pseudonyms in a text string.

    Example:
        "[PERSON_00001] is responsible for the assessment."

    Becomes:
        "John Smith is responsible for the assessment."
    """
    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")

    reverse_mapping = load_pseudonym_mapping(mapping_file)

    if not reverse_mapping:
        return text

    # Match longer placeholders first.
    # re.escape() ensures brackets and other special characters
    # are treated literally.
    placeholders = sorted(
        reverse_mapping.keys(),
        key=len,
        reverse=True
    )

    pattern = re.compile(
        "|".join(re.escape(token) for token in placeholders)
    )

    # Replace only exact recognized placeholders.
    restored_text = pattern.sub(
        lambda match: reverse_mapping[match.group(0)],
        text
    )

    return restored_text


def reidentify_file(input_file, mapping_file=MAPPING_FILE):
    """
    Read an LLM analysis from a TXT file, restore recognized
    pseudonyms, and save the result as a separate TXT file.

    The input file is never overwritten.
    """
    input_file = Path(input_file).resolve()

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_file}"
        )

    if not input_file.is_file():
        raise ValueError(
            f"Input path is not a file: {input_file}"
        )

    if input_file.suffix.lower() != ".txt":
        raise ValueError(
            "Re-identification currently supports .txt files only."
        )

    # Read the uploaded LLM analysis.
    with open(
        input_file,
        "r",
        encoding="utf-8-sig"
    ) as file:
        original_text = file.read()

    # Restore recognized placeholders.
    restored_text = reidentify_text(
        original_text,
        mapping_file
    )

    # Create output directory.
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Generate a separate output file.
    output_file = OUTPUT_DIR / (
        f"{input_file.stem}_reidentified.txt"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(restored_text)

    print("\nRE-IDENTIFICATION COMPLETED")
    print(f"Input analysis: {input_file}")
    print(f"Restored analysis: {output_file}")

    return output_file


if __name__ == "__main__":
    # Example input file.
    input_file = BASE_DIR / "llm_analysis.txt"

    reidentify_file(input_file)
