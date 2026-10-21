from pii.detection_store import load_detections
from pii.entity_merger import merge_detections
from pii.detection_store import load_detections, save_detections

# Load previously saved detection results.
detections = load_detections(
    "data/pii_detections.json"
)

print("Original detections:", len(detections))


# Merge duplicate detections.
entities = merge_detections(detections)

print("Consolidated entities:", len(entities))


# Display the entity registry.
for entity in entities:

    print("\n" + "=" * 50)

    print("Entity ID:", entity["entity_id"])
    print("Text:", entity["canonical_text"])
    print("Type:", entity["type"])
    print("Number of mentions:", len(entity["mentions"]))

    for mention in entity["mentions"]:

        print("\n  Source:", mention["source"])
        print("  Location:", mention["location"])
        print(
            "  Character span:",
            mention.get("start"),
            "-",
            mention.get("end")
        )
        print(
            "  Detection method:",
            mention.get("detection_method")
        )

save_detections(
    entities,
    "data/merged_entities.json"
)
