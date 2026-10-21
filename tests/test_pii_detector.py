from extractors.extractor import extract_file
from pii.detector import detect_pii


file_path = (
    r"D:\studies PDF\optiv project\case study"
    r"\Case Study 2 Supporting Material"
    r"\Cadence_Financial_Group_Organizational_Pack.pptx"
)


# Step 1: Extract document content.
print("Extracting document...")

extracted_items = extract_file(file_path)

print("Extracted items:", len(extracted_items))


# Step 2: Run Regex + NER.
print("\nRunning PII detection...")

detections = detect_pii(extracted_items, batch_size=16)

print("Total detections:", len(detections))


# Step 3: Display results.
for detection in detections:

    print("\n------------------------------")

    print("Text:", detection["text"])
    print("Type:", detection["type"])
    print("Confidence:", detection["confidence"])
    print("Method:", detection["detection_method"])
    print("Source:", detection["source"])
    print("Location:", detection["location"])
