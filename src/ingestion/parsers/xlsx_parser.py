import logging
import json
from pathlib import Path
from typing import List
import pandas as pd
from llama_index.core import Document

logger = logging.getLogger(__name__)

class XLSXParser:
    def parse(self, file_path: Path) -> List[Document]:
        """
        Parse an Excel file (.xlsx) into a list of Documents.
        Each row is parsed into a single Document with structured metadata.
        """
        logger.info(f"Parsing Excel file '{file_path.name}' with pandas...")
        
        try:
            # Load all sheets or just the first one? We read all sheets.
            excel_file = pd.ExcelFile(file_path)
            documents = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                
                # Drop fully empty rows/columns to clean up data
                df = df.dropna(how='all')
                
                # Reset index for clean row counting
                df = df.reset_index(drop=True)
                
                for idx, row in df.iterrows():
                    # Handle potential NaN values and format row as readable text
                    row_data = {}
                    text_parts = []
                    
                    for col_name, value in row.items():
                        # Clean column name and value
                        col_str = str(col_name).strip()
                        val_str = "" if pd.isna(value) else str(value).strip()
                        
                        row_data[col_str] = val_str
                        if val_str:
                            text_parts.append(f"{col_str}: {val_str}")
                    
                    # Row description string representation
                    row_text = f"Sheet: {sheet_name} | Row {idx + 1} | " + " | ".join(text_parts)
                    
                    # Metadata with cell values & structure info
                    metadata = {
                        "source": file_path.name,
                        "sheet_name": sheet_name,
                        "row_num": idx + 1,
                        "row_data_json": json.dumps(row_data) # Safe raw data serialization
                    }
                    
                    documents.append(
                        Document(
                            text=row_text,
                            metadata=metadata
                        )
                    )
            
            logger.info(f"Successfully parsed {len(documents)} rows from '{file_path.name}'.")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to parse Excel file '{file_path.name}': {e}")
            raise e
