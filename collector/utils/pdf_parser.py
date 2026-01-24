from pathlib import Path
import fitz  # pymupdf
import re
from typing import Union

class PDFParser:
    @staticmethod
    def extract_text_from_pdf(pdf_source: Union[Path, str, 'google.cloud.storage.Blob']) -> str:
        """
        Extract full text from PDF file using pymupdf.

        Args:
            pdf_source: Path to PDF file (str/Path) or GCS Blob object

        Returns:
            Extracted text string
        """
        try:
            # Check if it's a GCS blob object
            if hasattr(pdf_source, 'download_as_bytes'):
                # It's a GCS blob - download content to memory
                pdf_bytes = pdf_source.download_as_bytes()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            else:
                # It's a file path
                doc = fitz.open(pdf_source)

            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                text_parts.append(page_text)

            doc.close()

            full_text = "\n\n".join(text_parts)

            # Clean up text - remove null bytes and control characters for PostgreSQL
            full_text = full_text.replace("\x00", "")  # Remove null bytes
            full_text = re.sub(
                r"[\x01-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", full_text
            )  # Remove other control chars
            full_text = re.sub(r"\n{3,}", "\n\n", full_text)
            full_text = re.sub(r" {2,}", " ", full_text)

            return full_text.strip()

        except Exception as e:
            raise Exception(f"Error extracting text from {pdf_source}: {e}")