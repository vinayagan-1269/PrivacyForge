from pii.regex_engine import detect_regex_pii
from pii.model_engine import (
    load_ner_model,
    detect_ner_batch
)


def detect_pii(extracted_items, batch_size=16):

    # Load the NER model if it has not been loaded yet.
    load_ner_model()

    all_detections = []

    # Prepare text and preserve its source information.
    texts = [item["text"] for item in extracted_items]

    # Run the regex engine on each extracted item.
    for item in extracted_items:

        regex_results = detect_regex_pii(item["text"])

        for result in regex_results:

            result["source"] = item["source"]
            result["location"] = item["location"]

            all_detections.append(result)

    # Run NER in batches.
    ner_results = detect_ner_batch(
        texts,
        batch_size=batch_size
    )

    # Attach source information to each NER detection.
    for item, entities in zip(extracted_items, ner_results):

        for entity in entities:

            entity["source"] = item["source"]
            entity["location"] = item["location"]

            all_detections.append(entity)

    return all_detections
