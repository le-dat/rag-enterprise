from qdrant_client import QdrantClient
from src.core.config import settings

def get_qdrant_client() -> QdrantClient:
    """Khởi tạo và trả về kết nối tới Qdrant"""
    return QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT
    )
