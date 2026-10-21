from type_identifier import get_file_type

from extractors.docx_extractor import extract_docx
from extractors.pdf_extractor import extract_pdf
from extractors.pptx_extractor import extract_pptx
def extract_file(file_path):

    file_type = get_file_type(file_path)

    if file_type == "PDF":
        return extract_pdf(file_path)

    elif file_type == "DOCX":
        return extract_docx(file_path)

    elif file_type == "PPTX":
        return extract_pptx(file_path)

    else:
        raise ValueError("Unsupported file type")
