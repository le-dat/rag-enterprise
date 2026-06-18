import os
import logging
from pathlib import Path
from typing import List
from llama_index.core import Document

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self):
        self.api_key = os.getenv("LLAMAPARSE_API_KEY")
        self.use_llamaparse = os.getenv("USE_LLAMAPARSE", "true").lower() == "true"

    def parse(self, file_path: Path) -> List[Document]:
        """
        Parse a PDF file to a list of Documents.
        Tries LlamaParse first (if enabled and key present), falls back to PyMuPDF.
        """
        if self.use_llamaparse and self.api_key:
            try:
                logger.info(f"Attempting to parse '{file_path.name}' with LlamaParse...")
                return self._parse_with_llamaparse(file_path)
            except Exception as e:
                logger.warning(
                    f"LlamaParse failed for {file_path.name}: {e}. "
                    "Falling back to PyMuPDF..."
                )
                return self._parse_with_pymupdf(file_path)
        else:
            logger.info(f"LlamaParse disabled or key missing. Using PyMuPDF directly for '{file_path.name}'.")
            return self._parse_with_pymupdf(file_path)

    def _parse_with_llamaparse(self, file_path: Path) -> List[Document]:
        from llama_parse import LlamaParse
        
        parser = LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            verbose=False,
            language="en"
        )
        
        # llama-parse returns llama_index Document objects directly
        documents = parser.load_data(str(file_path))
        if not documents:
            raise ValueError("LlamaParse returned no documents.")
            
        logger.info(f"LlamaParse successfully parsed {len(documents)} document pages.")
        return documents

    def _parse_with_pymupdf(self, file_path: Path) -> List[Document]:
        import fitz  # PyMuPDF
        
        documents = []
        doc = fitz.open(file_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            # Create a LlamaIndex Document object with proper page metadata
            documents.append(
                Document(
                    text=text,
                    metadata={
                        "page": page_num + 1,
                        "source": file_path.name
                    }
                )
            )
            
        logger.info(f"PyMuPDF successfully parsed {len(documents)} pages from '{file_path.name}'.")
        return documents
