from extractors.extractor import extract_file
from pii.regex_engine import detect_extracted_pii


file_path = r"D:\studies PDF\optiv project\case study\Case Study 2 Supporting Material\Cadence_Financial_Group_Organizational_Pack.pptx"


# Step 1: Extract content
extracted_items = extract_file(file_path)

print("Extracted items:", len(extracted_items))


# Step 2: Detect PII
pii_results = detect_extracted_pii(extracted_items)

print("PII detected:", len(pii_results))


# Step 3: Display results
for result in pii_results:
    print("\nPII:", result["text"])
    print("Type:", result["type"])
    print("Confidence:", result["confidence"])
    print("Source:", result["source"])
    print("Location:", result["location"])
    print("Method:", result["detection_method"])
