# PrivacyForge 🔐

### Privacy-Preserving Document Processing and PII Pseudonymization

PrivacyForge is a Python-based prototype developed for an Optiv case
study. It processes PDF, DOCX, and PPTX documents, detects potential
personally identifiable information (PII), and replaces detected values
with pseudonyms before the sanitized document is used for external
analysis.

The project combines document extraction, regular-expression-based
detection, named-entity recognition (NER), entity merging, persistent
pseudonymization, and format-specific document processing behind a Flask
web application.

> **Important:** PrivacyForge does not automatically send documents to
> an external large language model (LLM). The intended workflow is to
> sanitize a document first, then let the user decide whether to use the
> sanitized output with an external service.

## Problem

Business documents can contain names, email addresses, phone numbers,
employee identifiers, IP addresses, and other sensitive information.
Sharing these documents without appropriate safeguards can expose
information that should remain private.

PrivacyForge explores a document-processing workflow that detects
potential PII and substitutes pseudonyms so users can work with a
sanitized copy rather than the original document.

## Features

-   **Multiple input formats:** PDF, DOCX, and PPTX.
-   **Text extraction:** Format-specific extractors for Word,
    PowerPoint, and PDF.
-   **OCR for scanned PDFs:** Uses Tesseract OCR through `pytesseract`
    when native PDF text is unavailable.
-   **Hybrid PII detection:** Regular expressions for structured values
    and GLiNER NER for contextual person and organization entities.
-   **Detection consolidation:** Merges duplicate detections into entity
    records.
-   **Persistent pseudonyms:** Reuses a protected mapping so recognized
    values can retain consistent placeholders.
-   **Document sanitization:** Separate processing modules for DOCX,
    PPTX, and PDF.
-   **Flask backend:** Provides endpoints for document processing, job
    status, downloads, and text-file re-identification.
-   **Explicit re-identification workflow:** Re-identification is a
    separate user-requested operation, not an automatic step in external
    LLM processing.

## Architecture and workflow

``` text
                 PDF / DOCX / PPTX
                         |
                         v
                File Type Identification
                         |
                         v
                  Text Extraction
               (OCR for scanned PDFs)
                         |
              +----------+----------+
              |                     |
              v                     v
        Regex Detection       GLiNER NER
              |                     |
              +----------+----------+
                         |
                         v
                  Entity Merging
                         |
                         v
                 Pseudonymization
                         |
                         v
              Format-Specific Replacer
                 /       |       \\
               DOCX     PPTX      PDF
                 \\       |       /
                         v
                 Sanitized Output
                         |
                         v
                 Download via Flask
```

The pipeline identifies the input format, extracts text, runs regex and
NER detection, merges duplicate detections, associates mentions with
pseudonyms through a persistent mapping, and invokes the appropriate
document replacer.

## Technology stack

  -----------------------------------------------------------------------
  Technology                          Role
  ----------------------------------- -----------------------------------
  Python                              Main implementation language

  Flask                               Web backend and API endpoints

  `python-docx`                       DOCX extraction and processing

  `python-pptx`                       PPTX extraction and processing

  PyMuPDF (`pymupdf`)                 PDF reading and page rendering

  Tesseract OCR                       OCR engine for scanned pages

  `pytesseract`                       Python interface to Tesseract

  Pillow                              Handles rendered page images for
                                      OCR

  `re`                                Regex-based PII detection and text
                                      matching

  GLiNER (`gliner`)                   Contextual named-entity recognition

  Hugging Face Transformers           Model infrastructure where used

  `hmac` and `hashlib`                Keyed lookup identifiers for
                                      pseudonymization

  `secrets`                           Secure pseudonymization-key
                                      generation

  ReportLab                           Reconstructs sanitized PDF output

  `json` and `pathlib`                Stores structured processing data
                                      and handles paths
  -----------------------------------------------------------------------

Python standard-library modules such as `re`, `json`, `pathlib`, `hmac`,
`hashlib`, `secrets`, `threading`, and `argparse` do not need separate
installation.

## PII detection

### Regex-based detection

The regex engine detects supported patterns for email addresses, phone
numbers, IP addresses, credit card numbers, and employee IDs.

Each detection can include the matched text, PII type, confidence, start
and end offsets, and detection method. Offsets refer to the extracted
text segment, not necessarily the entire source document.

Regex detection depends on the patterns and text representation. Unusual
formats and OCR errors can lead to missed or partial matches.

### Named-entity recognition

The project uses the GLiNER model `urchade/gliner_multi-v2.1` with
labels for `person` and `organization`. NER complements regex by
identifying contextual entities that do not necessarily follow a fixed
format.

NER may produce false positives or miss entities, so detections should
not be assumed to be perfect.

### Entity merging

The entity merger consolidates duplicate detections and groups matching
normalized values and types. It is not full real-world entity
resolution: different aliases for the same person or organization are
not guaranteed to be linked.

## Pseudonymization and re-identification

Detected values are associated with placeholders, for example:

  Example value      Example placeholder
  ------------------ -------------------------
  A person's name    `[PERSON_00001]`
  An email address   `[EMAIL_00002]`
  A phone number     `[PHONE_PATTERN_00003]`

These are illustrative examples; actual identifiers depend on the
entities and the persistent mapping.

The pseudonymization implementation uses HMAC-SHA256-based lookup
identifiers and a persistent mapping to reuse pseudonyms. The mapping
stores original values and is sensitive. The key and mapping must be
protected and must not be published in a public repository.

Pseudonymization is not anonymization. Anyone who obtains the mapping
may be able to associate placeholders with original values.

The re-identification module currently supports text files (`.txt`) and
requires the mapping file. Unknown placeholders are left unchanged.

## Supported formats and known limitations

  -----------------------------------------------------------------------
  Format                  Processing              Known limitations
  ----------------------- ----------------------- -----------------------
  DOCX                    Extracts text and       Rewriting paragraph
                          replaces detected       text can change
                          values in supported     run-level formatting;
                          paragraphs, tables,     unsupported objects may
                          headers, and footers    remain unprocessed

  PPTX                    Extracts text and       Some run formatting can
                          replaces detected       change; not every
                          values in supported     possible PowerPoint
                          slide shapes and tables object is handled

  PDF                     Extracts native text    Output is reconstructed
                          where available,        rather than edited in
                          otherwise uses OCR;     place, so original
                          builds a sanitized PDF  layout, tables, images,
                          from extracted text     and positioning may not
                                                  be preserved exactly;
                                                  OCR errors can affect
                                                  detection and
                                                  replacement
  -----------------------------------------------------------------------

The PDF workflow creates a readable sanitized copy, not a pixel-perfect
copy of the original document. Detection coverage and document
preservation have not been claimed to meet specific performance targets
without systematic evaluation.

## Project structure

The principal components include:

``` text
laboratory/
├── extractors/
│   ├── extractor.py
│   ├── docx_extractor.py
│   ├── pdf_extractor.py
│   └── pptx_extractor.py
├── pii/
│   ├── regex_engine.py
│   ├── model_engine.py
│   ├── detector.py
│   ├── detection_store.py
│   └── entity_merger.py
├── pseudonymization/
│   ├── pseudonymizer.py
│   └── reidentifier.py
├── document_processor/
│   ├── document_replacer.py
│   ├── pptx_replacer.py
│   └── pdf_replacer.py
├── frontend/
├── data/                 # Runtime data; do not publish sensitive contents
├── output/               # Generated files; do not publish
├── app.py
├── process_document.py
├── type_identifier.py
├── requirements.txt
├── .gitignore
└── README.md
```

This is a guide to the main components; the exact contents of the local
working directory may differ.

## Setup

### Prerequisites

-   A Python version compatible with the dependencies in
    `requirements.txt`.
-   `pip`.
-   Tesseract OCR installed separately for scanned-PDF processing.
-   Network access to download the GLiNER model on first use, unless its
    weights are already cached locally.

### 1. Clone the repository

Replace `<YOUR-REPOSITORY-URL>` with the URL of the published GitHub
repository.

``` bash
git clone <YOUR-REPOSITORY-URL>
cd <REPOSITORY-DIRECTORY>
```

### 2. Create and activate a virtual environment

**Windows:**

``` powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

``` bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Tesseract OCR

Install the Tesseract OCR application for your operating system. Ensure
its executable is available on `PATH`, or configure its location in the
Python application if necessary.

### 5. Run the Flask application

From the project root, run:

``` bash
python app.py
```

Open the local address printed by Flask in your browser. The application
is a local prototype; do not expose Flask's development server to an
untrusted network.

The GLiNER package and its pretrained model are separate: installing
`gliner` does not necessarily install the model weights. The model may
be downloaded when the detector initializes.

## Security notes

Before using PrivacyForge with real sensitive data:

-   Never commit original case-study documents or confidential source
    files.
-   Never commit `data/pseudonym_mapping.json` or
    `data/.pseudonymization_key`.
-   Do not publish detection JSON or generated outputs that contain
    sensitive values.
-   Review `.gitignore` and check whether sensitive files are already
    tracked by Git.
-   Validate sanitized outputs before sharing them. A detection pipeline
    cannot guarantee that every instance of PII has been found.
-   Protect uploaded documents, temporary files, logs, output files, and
    mapping data with appropriate access controls.
-   The current local prototype uses shared JSON files for processing
    state and is not designed for safe concurrent multi-user production
    use without further engineering.
-   Do not assume a sanitized document is anonymous or free of sensitive
    information.
-   External LLM use is a separate, user-controlled step; this
    application does not automatically submit documents to an LLM.

## Future improvements

-   Improve OCR-based matching and phone-number replacement for scanned
    PDFs.
-   Expand and test regex patterns against different formats.
-   Reduce NER false positives and missed detections.
-   Improve entity resolution across aliases and variations.
-   Preserve DOCX, PPTX, and PDF structure more faithfully.
-   Add regression tests for end-to-end detection and replacement.
-   Measure recall, precision, false-positive rates, and structural
    preservation on a representative test set.
-   Strengthen secure file handling, access controls, and multi-user
    processing before production deployment.

## Author

**Vinayagan S.**\
B.Tech, Computer Science and Engineering (Cyber Security)\
VIT-AP University

GitHub: [vinayagan-1269](https://github.com/vinayagan-1269)

------------------------------------------------------------------------

PrivacyForge is a prototype developed as a cybersecurity and
data-privacy project. Its output should be validated before being used
to share sensitive or regulated information.
