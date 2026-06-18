import logging
from pathlib import Path
from typing import List
from llama_index.core import Document

from src.ingestion.parsers.pdf_parser import PDFParser
from src.ingestion.parsers.xlsx_parser import XLSXParser

logger = logging.getLogger(__name__)

class IngestionRouter:
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.xlsx_parser = XLSXParser()

    def parse_file(self, file_path: str | Path) -> List[Document]:
        """
        Routes the file to the appropriate parser based on extension.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        logger.info(f"Routing file '{path.name}' with extension '{suffix}'...")

        if suffix == ".pdf":
            return self.pdf_parser.parse(path)
        elif suffix in (".xlsx", ".xls"):
            return self.xlsx_parser.parse(path)
        else:
            # Simple text/fallback reader for other plain files (.txt, .md, .csv)
            logger.info(f"Unsupported binary extension '{suffix}'. Reading as generic text...")
            return self._parse_generic_text(path)

    def _parse_generic_text(self, file_path: Path) -> List[Document]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return [
                Document(
                    text=content,
                    metadata={
                        "source": file_path.name,
                        "page": 1
                    }
                )
            ]
        except Exception as e:
            logger.error(f"Failed to read generic file '{file_path.name}': {e}")
            raise e
