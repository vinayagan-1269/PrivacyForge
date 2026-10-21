from pathlib import Path

from extractors.pdf_extractor import extract_pdf


pdf_path = Path(
    r"D:\studies PDF\optiv project\case study"
    r"\Case Study 2 Supporting Material"
    r"\Cadence_Group_Risk_Management_Policy__v6.0.pdf"
)

try:
    results = extract_pdf(pdf_path)
    output_path = Path("pdf_extraction_output.txt")

    with output_path.open("w", encoding="utf-8") as file:
        for index, item in enumerate(results, start=1):
            file.write(f"\n{'=' * 60}\n")
            file.write(f"PAGE {item['location']['page']}\n")
            file.write(f"METHOD: {item['extraction_method']}\n")
            file.write(f"{'=' * 60}\n\n")
            file.write(item["text"])
            file.write("\n")

    print(f"Full extraction saved to: {output_path.resolve()}")

    print("\n========== EXTRACTION SUMMARY ==========")

    print(f"Pages extracted: {len(results)}")

    for index, item in enumerate(results, start=1):

        print(f"\nRecord {index}")
        print(f"Source: {item['source']}")
        print(f"Location: {item['location']}")
        print(f"Method: {item['extraction_method']}")
        print(f"Text length: {len(item['text'])}")

        print("\nText preview:")
        print(item["text"][:300])

        print("-" * 50)

except Exception as error:
    print(f"Extraction failed: {error}")
