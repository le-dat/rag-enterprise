import os
import sys

# Thêm thư mục gốc vào python path để import được từ src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.query.engine import query_rag_engine

def run_test_query():
    collection_name = "enterprise_kb"
    query = "Nguyễn Văn A là ai và đã sáng lập công ty nào?"
    
    print("==================================================")
    print("🔍 BẮT ĐẦU CHẠY THỬ NGHIỆM TRUY VẤN GRAPH-VECTOR RAG")
    print("==================================================")
    
    # CASE 1: Người dùng có quyền truy cập ['finance', 'management']
    # Mong đợi: Tìm thấy dữ liệu của dummy.pdf (được nạp với quyền 'finance'/'management') và trả lời đúng.
    print("\n🔒 CASE 1: Người dùng thuộc nhóm ['finance', 'management'] (Có quyền đọc)")
    answer_authorized = query_rag_engine(
        query_str=query,
        collection_name=collection_name,
        user_groups=["finance", "management"]
    )
    print("\n💬 Câu trả lời nhận được:")
    print(answer_authorized)
    
    # CASE 2: Người dùng chỉ có quyền ['public'] (Bị giới hạn quyền truy cập)
    # Mong đợi: Bộ lọc RBAC trên Qdrant và Neo4j sẽ chặn hết dữ liệu. LLM phản hồi lịch sự không tìm thấy thông tin.
    print("\n🔒 CASE 2: Người dùng chỉ thuộc nhóm ['public'] (Không có quyền đọc)")
    answer_unauthorized = query_rag_engine(
        query_str=query,
        collection_name=collection_name,
        user_groups=["public"]
    )
    print("\n💬 Câu trả lời nhận được:")
    print(answer_unauthorized)
    print("\n==================================================")
    print("🎉 Hoàn thành kiểm thử truy vấn.")

if __name__ == "__main__":
    run_test_query()
