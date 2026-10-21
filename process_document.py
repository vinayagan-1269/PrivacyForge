import json
from pathlib import Path

from type_identifier import get_file_type

from extractors.extractor import extract_file

from pii.detector import detect_pii
from pii.entity_merger import merge_detections
from pii.detection_store import save_detections

from pseudonymization.pseudonymizer import pseudonymize_entities
from document_processor.pdf_replacer import sanitize_pdf
from document_processor.document_replacer import sanitize_docx
from document_processor.pptx_replacer import sanitize_pptx


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Ensure the data directory exists.
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Map supported document types to their replacers.
# PDF will be added after pdf_replacer.py is implemented.
REPLACERS = {
    "DOCX": sanitize_docx,
    "PPTX": sanitize_pptx,
    "PDF": sanitize_pdf,
}

def process_document(file_path, progress_callback=None):
    def report_progress(percent, stage, message):
        if progress_callback:
            progress_callback({
                "percent": percent,
                "stage": stage,
                "message": message
            })
            
    """
    Run the complete PII detection and pseudonymization pipeline.

    Supported formats:
        DOCX
        PPTX

    PDF support will be added after implementing its replacer.
    """

    # Resolve and validate the input path.
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(
            f"Document not found: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"The provided path is not a file: {file_path}"
        )

    # 1. Identify the document type.
    report_progress(
        10,
        "Identifying document",
        "Checking the document format..."
    )
    file_type = get_file_type(file_path)

    if file_type == "UNSUPPORTED":
        raise ValueError(
            f"Unsupported document format: {file_path.suffix}"
        )

    print(f"\nProcessing: {file_path.name}")
    print(f"Document type: {file_type}")

    report_progress(
        20,
        "Extracting content",
        "Extracting text and document content..."
    )

    # 2. Extract document text.
    extracted_items = extract_file(str(file_path))

    print(
        f"Extracted text segments: {len(extracted_items)}"
    )

    report_progress(
        40,
        "Detecting sensitive information",
        "Running regex and named entity recognition..."
    )
    # 3. Detect PII.
    detections = detect_pii(extracted_items)

    print(f"PII detections: {len(detections)}")

    # 4. Save detections.
    detections_file = DATA_DIR / "pii_detections.json"

    save_detections(
        detections,
        detections_file
    )

    report_progress(
        60,
        "Merging detections",
        "Consolidating detected entities..."
    )

    # 5. Merge duplicate entities.
    merged_entities = merge_detections(detections)

    merged_file = DATA_DIR / "merged_entities.json"

    with open(
        merged_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            merged_entities,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"Consolidated entities: {len(merged_entities)}"
    )

    report_progress(
        75,
        "Pseudonymizing entities",
        "Assigning consistent pseudonyms..."
    )

    # 6. Pseudonymize the merged entities.
    pseudonymized_entities = pseudonymize_entities(
        merged_entities
    )

    # 7. Save pseudonymized entities for the current document.
    pseudonymized_file = (
        DATA_DIR / "pseudonymized_entities.json"
    )

    with open(
        pseudonymized_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            pseudonymized_entities,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"Pseudonymized entities saved: {pseudonymized_file}"
    )

    # 8. Select the appropriate document replacer.
    replacer = REPLACERS.get(file_type)

    if replacer is None:
        raise NotImplementedError(
            f"Sanitization for {file_type} "
            "has not been implemented yet."
        )

    report_progress(
        85,
        "Sanitizing document",
        "Replacing sensitive values in the document..."
    )

    # 9. Sanitize the document.
    output_file = replacer(
        file_path,
        entities_file=pseudonymized_file
    )

    report_progress(
        100,
        "Completed",
        "Your sanitized document is ready for download."
    )


    print("\nDOCUMENT PROCESSING COMPLETED")
    print(f"Input document: {file_path}")
    print(f"Document type: {file_type}")
    print(f"Sanitized document: {output_file}")

    return output_file

if __name__ == "__main__":

    document = (
        r"D:\studies PDF\optiv project\case study"
        r"\Case Study 2 Supporting Material"
        r"\Cadence_Financial_Group_Organizational_Pack.pptx"
    )
    process_document(document)
