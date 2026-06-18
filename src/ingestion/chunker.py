import logging
import uuid
from typing import List, Dict, Any
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)

class DocumentChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_documents(
        self, 
        documents: List[Document], 
        department: str, 
        role: str
    ) -> List[TextNode]:
        """
        Split a list of parsed Documents into smaller TextNodes (chunks)
        and attach mandatory RBAC metadata fields.
        """
        logger.info(f"Chunking {len(documents)} documents with target size...")
        
        # SentenceSplitter will process the list and return TextNode objects
        nodes = self.splitter.get_nodes_from_documents(documents)
        
        processed_nodes = []
        for idx, node in enumerate(nodes):
            # Extract standard metadata from original document if available
            source = node.metadata.get("source", "unknown")
            page = node.metadata.get("page", 1)
            sheet_name = node.metadata.get("sheet_name")
            row_num = node.metadata.get("row_num")
            
            # Form clean and trackable chunk_id (e.g. hr_policy_pdf_003 or custom uuid prefix)
            clean_filename = source.replace(".", "_").replace(" ", "_").lower()
            chunk_id = f"{clean_filename}_{idx:03d}_{str(uuid.uuid4())[:8]}"
            
            # Form the standardized RBAC metadata structure
            rbac_metadata: Dict[str, Any] = {
                "chunk_id": chunk_id,
                "source": source,
                "department": department,
                "role": role,
                "page": page
            }
            
            # Forward XLSX specifics if existing
            if sheet_name:
                rbac_metadata["sheet_name"] = sheet_name
            if row_num:
                rbac_metadata["row_num"] = row_num
                
            # Override node metadata completely to enforce schema consistency
            node.metadata = rbac_metadata
            node.id_ = chunk_id  # Enforce Qdrant point mapping consistency
            
            processed_nodes.append(node)
            
        logger.info(f"Generated {len(processed_nodes)} chunks with RBAC metadata: dept={department}, role={role}.")
        return processed_nodes
