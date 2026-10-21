import re


PATTERNS = {

    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",

    "PHONE_PATTERN": (
        r"(?<!\w)"
        r"(?:\+\d{1,3}[\s.-]*)?"
        r"(?:\(\d{3}\)|\d{3})"
        r"[\s.-]*"
        r"\d{4}"
        r"(?!\w)"
        r"|"
        r"(?<!\w)"
        r"(?:\+\d{1,3}[\s.-]*)?"
        r"(?:\(\d{3}\)|\d{3})"
        r"[\s.-]*"
        r"\d{3}"
        r"[\s.-]*"
        r"\d{4}"
        r"(?!\w)"
    ),
    "IP_ADDRESS": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",

    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,19}\b",

    "EMPLOYEE_ID": r"\bEMP[-_]?\d{3,10}\b"
}


def detect_regex_pii(text):

    results = []

    for pii_type, pattern in PATTERNS.items():

        matches = re.finditer(pattern, text)

        for match in matches:

            results.append({
                "text": match.group(),
                "type": pii_type,
                "confidence": 1.0,
                "start": match.start(),
                "end": match.end(),
                "detection_method": "regex"
            })

    return results


def detect_extracted_pii(extracted_items):

    results = []

    for item in extracted_items:

        text = item["text"]

        detections = detect_regex_pii(text)

        for detection in detections:

            detection["source"] = item["source"]
            detection["location"] = item["location"]

            results.append(detection)

    return results
