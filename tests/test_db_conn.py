# tests/test_db_conn.py
import os
import sys

# Thêm thư mục gốc vào python path để import được từ src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.qdrant_client import get_qdrant_client
from src.core.neo4j_client import Neo4jClient

def test_connections():
    print("--- Đang kiểm tra kết nối Qdrant ---")
    try:
        q_client = get_qdrant_client()
        collections = q_client.get_collections()
        print(f"✅ Kết nối Qdrant thành công. Collections hiện có: {collections}")
    except Exception as e:
        print(f"❌ Lỗi kết nối Qdrant: {e}")

    print("\n--- Đang kiểm tra kết nối Neo4j ---")
    try:
        n_client = Neo4jClient()
        # Chạy thử truy vấn kiểm tra phiên bản Neo4j
        res = n_client.query("RETURN datetime() as time")
        print(f"✅ Kết nối Neo4j thành công. Thời gian DB: {res[0]['time']}")
        n_client.close()
    except Exception as e:
        print(f"❌ Lỗi kết nối Neo4j: {e}")

if __name__ == "__main__":
    test_connections()
