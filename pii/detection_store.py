import json
from pathlib import Path


def save_detections(detections, output_path):
    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            detections,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"Detections saved to: {output_path.resolve()}")


def load_detections(input_path):
    input_path = Path(input_path)

    with input_path.open("r", encoding="utf-8") as file:
        return json.load(file)
