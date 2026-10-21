from pathlib import Path

def get_file_type(file_path):
    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return "PDF"
    elif extension == ".docx":
        return "DOCX"
    elif extension == ".pptx":
        return "PPTX"
    else:
        return "UNSUPPORTED"
    
