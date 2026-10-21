from gliner import GLiNER

MODEL_NAME = "urchade/gliner_multi-v2.1"

ner_model = None
model_ready = False

ENTITY_LABELS = [
    "person",
    "organization",
]


def load_ner_model():
    global ner_model, model_ready

    if model_ready:
        return

    print("Loading GLiNER model...")

    ner_model = GLiNER.from_pretrained(MODEL_NAME)

    model_ready = True

    print("GLiNER model is ready!")


def detect_ner_pii(text, threshold=0.4):
    if not model_ready:
        raise RuntimeError(
            "GLiNER is not ready. Load the model first."
        )

    if not isinstance(text, str) or not text.strip():
        return []

    entities = ner_model.predict_entities(
        text,
        ENTITY_LABELS,
        threshold=threshold,
    )

    results = []

    for entity in entities:
        start = entity.get("start")
        end = entity.get("end")

        if start is None or end is None:
            continue

        if start < 0 or end > len(text) or start >= end:
            continue

        original_text = text[start:end]

        # Reject predictions whose offsets do not match the text.
        if original_text != entity["text"]:
            continue

        results.append({
            "text": original_text,
            "type": entity["label"].upper(),
            "confidence": float(entity["score"]),
            "start": start,
            "end": end,
            "detection_method": "NER",
        })

    return results


def detect_ner_batch(texts, batch_size=16):
    if not model_ready:
        raise RuntimeError(
            "GLiNER is not ready. Load the model first."
        )

    return [
        detect_ner_pii(text)
        for text in texts
    ]
