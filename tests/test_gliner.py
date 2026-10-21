from gliner import GLiNER

MODEL_NAME = "urchade/gliner_multi-v2.1"

print("Loading GLiNER model...")
model = GLiNER.from_pretrained(MODEL_NAME)
print("Model loaded!")

texts = [
    "Led by Tobias Lindqvist",
    "Priyanka Raghunathan",
    "Led by Priyanka Raghunathan.",
    "Adaeze Okonkwo-Bell",
    "The employee is Adaeze Okonkwo-Bell, a senior manager.",
    "Desmond Achterberg",
]

labels = ["person", "organization", "email address", "phone number"]

for text in texts:
    entities = model.predict_entities(text, labels, threshold=0.4)

    print("\nInput:", text)

    for entity in entities:
        print(
            "Text:", repr(entity["text"]),
            "| Type:", entity["label"],
            "| Start:", entity["start"],
            "| End:", entity["end"],
            "| Score:", round(entity["score"], 3)
        )
