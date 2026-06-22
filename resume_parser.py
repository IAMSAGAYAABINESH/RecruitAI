"""
resume_parser.py
----------------
Extracts raw text from an uploaded PDF resume.
Uses pdfplumber for reliable text extraction with layout awareness.
"""

import io
import pdfplumber


def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract all text from a PDF file uploaded via Streamlit's file_uploader.

    Args:
        uploaded_file: Streamlit UploadedFile object (PDF)

    Returns:
        Full resume text as a single string, pages separated by newlines.
    """
    pdf_bytes = uploaded_file.read()
    text_parts = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())

    return "\n\n".join(text_parts)
