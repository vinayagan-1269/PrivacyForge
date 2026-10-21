import hashlib
import hmac
import json
import secrets

from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Sensitive files: keep these local and do not commit them to Git.
KEY_FILE = DATA_DIR / ".pseudonymization_key"
MAPPING_FILE = DATA_DIR / "pseudonym_mapping.json"


def load_or_create_key():
    """
    Load the persistent secret key or generate it on first use.
    The same key must be retained to preserve entity lookup.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()

        if len(key) != 32:
            raise ValueError(
                "Invalid pseudonymization key. "
                "Restore the original 32-byte key."
            )

        return key

    key = secrets.token_bytes(32)

    with KEY_FILE.open("xb") as file:
        file.write(key)

    return key


def load_mapping():
    """Load the existing pseudonym mapping."""
    if not MAPPING_FILE.exists():
        return {}

    with MAPPING_FILE.open("r", encoding="utf-8") as file:
        mapping = json.load(file)

    if not isinstance(mapping, dict):
        raise ValueError("The pseudonym mapping must be a JSON object.")

    return mapping


def save_mapping(mapping):
    """
    Save the mapping locally.

    This file contains original PII and must be protected.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = MAPPING_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            mapping,
            file,
            indent=4,
            ensure_ascii=False
        )

    temporary_file.replace(MAPPING_FILE)


def create_lookup_key(entity_type, normalized_text, secret_key):
    """
    Create a keyed fingerprint for looking up an entity.

    Unlike a plain SHA-256 hash, HMAC requires the secret key.
    The fingerprint is not used as the visible pseudonym.
    """
    value = f"{entity_type}:{normalized_text}".encode("utf-8")

    return hmac.new(
        secret_key,
        value,
        hashlib.sha256
    ).hexdigest()


def generate_pseudonym(entity_type, counter):
    """Generate a readable pseudonym."""
    return f"[{entity_type}_{counter:05d}]"


def pseudonymize_entities(entities):
    """
    Assign consistent pseudonyms to consolidated entities.

    Expected entity fields:
        canonical_text
        normalized_text
        type
        mentions

    Returns:
        A list of entities with an additional 'pseudonym' field.
    """
    secret_key = load_or_create_key()
    mapping = load_mapping()

    counters = {}

    # Continue numbering from the existing mapping.
    for record in mapping.values():
        entity_type = record["type"]
        counters[entity_type] = max(
            counters.get(entity_type, 0),
            record["counter"]
        )

    pseudonymized_entities = []

    for entity in entities:
        original_text = entity.get("canonical_text", "").strip()
        normalized_text = entity.get(
            "normalized_text",
            original_text.casefold()
        ).strip()

        entity_type = entity.get("type", "UNKNOWN").upper()

        if not original_text or not normalized_text:
            continue

        lookup_key = create_lookup_key(
            entity_type,
            normalized_text,
            secret_key
        )

        if lookup_key not in mapping:
            counters[entity_type] = (
                counters.get(entity_type, 0) + 1
            )

            pseudonym = generate_pseudonym(
                entity_type,
                counters[entity_type]
            )

            mapping[lookup_key] = {
                "type": entity_type,
                "original_value": original_text,
                "pseudonym": pseudonym,
                "counter": counters[entity_type]
            }

        pseudonym = mapping[lookup_key]["pseudonym"]

        # Preserve the original entity data and add its pseudonym.
        pseudonymized_entity = entity.copy()
        pseudonymized_entity["pseudonym"] = pseudonym

        pseudonymized_entities.append(pseudonymized_entity)

    save_mapping(mapping)

    return pseudonymized_entities


def main():
    """Run the pseudonymizer on merged_entities.json."""
    input_path = DATA_DIR / "merged_entities.json"
    output_path = DATA_DIR / "pseudonymized_entities.json"

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_path}\n"
            "Run the entity merger first."
        )

    with input_path.open("r", encoding="utf-8") as file:
        entities = json.load(file)

    if not isinstance(entities, list):
        raise ValueError(
            "Expected merged_entities.json to contain a JSON list."
        )

    pseudonymized_entities = pseudonymize_entities(entities)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            pseudonymized_entities,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("Pseudonymization completed!")
    print(f"Entities processed: {len(pseudonymized_entities)}")
    print(f"Output saved to: {output_path}")
    print(f"Protected mapping saved to: {MAPPING_FILE}")


if __name__ == "__main__":
    main()
