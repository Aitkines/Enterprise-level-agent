import io
import pandas as pd
import pdfplumber
from typing import Optional

class FileProcessor:
    @staticmethod
    def process_file(file_name: str, file_bytes: bytes) -> Optional[str]:
        """
        Parses the uploaded file and returns a text representation for the AI Agent.
        Supports PDF, Excel (xlsx, xls), and CSV.
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
