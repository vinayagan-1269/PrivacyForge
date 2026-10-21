from collections import defaultdict
import hashlib
import json
import re


# Standardize entity labels from different detection engines.
ENTITY_TYPE_MAP = {
    "PER": "PERSON",
    "PERSON": "PERSON",
    "ORG": "ORGANIZATION",
    "ORGANIZATION": "ORGANIZATION",
    "LOC": "LOCATION",
    "LOCATION": "LOCATION",
    "GPE": "LOCATION",
    "EMAIL": "EMAIL",
    "PHONE": "PHONE",
    "IP_ADDRESS": "IP_ADDRESS",
    "CREDIT_CARD": "CREDIT_CARD",
    "EMPLOYEE_ID": "EMPLOYEE_ID"
}


def normalize_entity_type(entity_type):
    """
    Convert equivalent entity labels into a common representation.
    """
    return ENTITY_TYPE_MAP.get(
        entity_type.upper(),
        entity_type.upper()
    )


def normalize_text(text):
    """
    Normalize text for duplicate comparison without
    changing the original text stored in the results.
    """
    return re.sub(r"\s+", " ", text).strip().casefold()


def create_mention_key(detection):
    """
    Identify duplicate detections of the same text span
    in the same extracted document segment.
    """
    location = detection.get("location", {})

    key_data = {
        "source": detection.get("source"),
        "location": location,
        "start": detection.get("start"),
        "end": detection.get("end"),
        "text": normalize_text(detection["text"])
    }

    serialized = json.dumps(
        key_data,
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def merge_detections(detections):
    """
    Consolidate duplicate detections while preserving
    all original mention locations.

    This function does not attempt to determine whether
    different names refer to the same real-world person.
    """

    unique_mentions = {}

    for detection in detections:

        text = detection.get("text", "").strip()

        if not text:
            continue

        entity_type = normalize_entity_type(
            detection.get("type", "UNKNOWN")
        )

        mention_key = create_mention_key(detection)

        mention = {
            **detection,
            "text": text,
            "type": entity_type
        }

        if mention_key not in unique_mentions:
            unique_mentions[mention_key] = mention

        else:
            # Preserve the detection with higher confidence.
            existing = unique_mentions[mention_key]

            if (
                mention.get("confidence", 0)
                > existing.get("confidence", 0)
            ):
                unique_mentions[mention_key] = mention

    # Group distinct mentions by normalized text and entity type.
    grouped_entities = defaultdict(list)

    for mention in unique_mentions.values():

        entity_key = (
            mention["type"],
            normalize_text(mention["text"])
        )

        grouped_entities[entity_key].append(mention)

    # Create a canonical registry.
    entities = []

    for (entity_type, normalized_value), mentions in sorted(
        grouped_entities.items()
    ):

        # Stable within this particular registry.
        entity_id = f"ENTITY_{len(entities) + 1:05d}"

        canonical_text = mentions[0]["text"]

        entities.append({
            "entity_id": entity_id,
            "canonical_text": canonical_text,
            "normalized_text": normalized_value,
            "type": entity_type,
            "mentions": mentions
        })

    return entities
