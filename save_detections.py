from pathlib import Path

from extractors.extractor import extract_file
from pii.detector import detect_pii
from pii.detection_store import save_detections


file_path = r"D:\studies PDF\optiv project\case study\Case Study 2 Supporting Material\Cadence_Financial_Group_Organizational_Pack.pptx"

extracted_items = extract_file(file_path)

detections = detect_pii(
    extracted_items,
    batch_size=16
)

output_path = Path("data") / "pii_detections.json"

save_detections(detections, output_path)
