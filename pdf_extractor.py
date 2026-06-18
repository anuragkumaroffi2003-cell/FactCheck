import fitz
import streamlit as st


def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extract text from a text-based PDF.

    Returns:
        Extracted text as a string.
        Returns empty string if extraction fails.
    """
    try:
        pdf_bytes = uploaded_file.read()

        if not pdf_bytes:
            st.error("Uploaded PDF is empty.")
            return ""

        pages = []

        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text = page.get_text("text")

                if text and text.strip():
                    pages.append(text.strip())

        if not pages:
            st.error(
                "No extractable text found. "
                "Scanned/image PDFs are not currently supported."
            )
            return ""

        return "\n\n".join(pages)

    except Exception as e:
        st.error(f"Failed to extract PDF: {str(e)}")
        return ""
