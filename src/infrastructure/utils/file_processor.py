import io
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
import pdfplumber
from typing import Optional

class FileProcessor:
    @staticmethod
    def process_file(file_name: str, file_bytes: bytes) -> Optional[str]:
        """
        Parses the uploaded file and returns a text representation for the AI Agent.
        Supports PDF, Excel (xlsx, xls), CSV, text-like files, Word (.docx),
        and image metadata for multimodal uploads.
        """
        ext = file_name.split('.')[-1].lower()
        
        try:
            if ext == 'pdf':
                return FileProcessor._parse_pdf(file_bytes)
            elif ext in ['xlsx', 'xls']:
                return FileProcessor._parse_excel(file_bytes)
            elif ext == 'csv':
                return FileProcessor._parse_csv(file_bytes)
            elif ext in ['txt', 'md']:
                return file_bytes.decode('utf-8', errors='replace')
            elif ext == 'docx':
                return FileProcessor._parse_docx(file_bytes)
            elif ext == 'doc':
                return (
                    f"[Word Document Uploaded: {file_name}]\\n"
                    "Legacy .doc files are accepted, but structured text extraction is not yet available. "
                    "Please rely on the file context and your prompt for downstream analysis."
                )
            elif ext in ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp']:
                return FileProcessor._parse_image(file_name, file_bytes)
            else:
                return f"[Unsupported File Format: {ext}]"
        except Exception as e:
            return f"[Error processing file {file_name}: {str(e)}]"

    @staticmethod
    def _parse_pdf(file_bytes: bytes) -> str:
        text_content = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
                
                # Optional: Handle tables in PDF if needed
                # tables = page.extract_tables()
                # for table in tables:
                #     df = pd.DataFrame(table)
                #     text_content.append(df.to_markdown(index=False))
                    
        return "\n\n".join(text_content)

    @staticmethod
    def _parse_excel(file_bytes: bytes) -> str:
        # Load all sheets
        dict_df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        result = []
        for sheet_name, df in dict_df.items():
            result.append(f"### Sheet: {sheet_name}\n")
            result.append(df.to_markdown(index=False))
        return "\n\n".join(result)

    @staticmethod
    def _parse_csv(file_bytes: bytes) -> str:
        df = pd.read_csv(io.BytesIO(file_bytes))
        return df.to_markdown(index=False)

    @staticmethod
    def _parse_docx(file_bytes: bytes) -> str:
        paragraphs = []
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            xml_content = archive.read("word/document.xml")
        root = ET.fromstring(xml_content)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

        for paragraph in root.findall(".//w:p", namespace):
            parts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
            if parts:
                paragraphs.append("".join(parts))

        return "\\n\\n".join(paragraphs)

    @staticmethod
    def _parse_image(file_name: str, file_bytes: bytes) -> str:
        size_kb = round(len(file_bytes) / 1024, 1)
        return (
            f"[Image Uploaded: {file_name}]\\n"
            f"File size: {size_kb} KB. "
            "The image has been attached through the multimodal upload entry. "
            "Current backend processing preserves image context metadata for analysis."
        )
