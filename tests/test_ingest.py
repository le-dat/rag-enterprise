import os
import sys

# Thêm thư mục gốc vào python path để import được từ src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.pipeline import scan_and_ingest_directory

def main():
    print("🚀 Bắt đầu chạy thử nghiệm luồng Ingestion...")
    
    # 1. Khởi tạo thư mục data/
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"📁 Đã tạo thư mục '{data_dir}'.")
        
    # Kiểm tra xem có file PDF nào trong thư mục chưa
    pdf_files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"\n⚠️ Cảnh báo: Hiện tại chưa có file PDF nào trong thư mục '{data_dir}/'.")
        print("💡 Hãy sao chép ít nhất một file PDF (ví dụ: báo cáo tài chính) vào thư mục này rồi chạy lại script.")
        print(f"💡 Ví dụ đường dẫn file cần đặt: {os.path.abspath(os.path.join(data_dir, 'financial_report.pdf'))}\n")
    
    # 2. Tiến hành quét và nạp dữ liệu vào collection 'enterprise_kb'
    # Các tài liệu nạp sẽ được gắn thẻ group_access là ['finance', 'management'] phục vụ RBAC
    scan_and_ingest_directory(
        directory_path=data_dir,
        collection_name="enterprise_kb",
        group_access_list=["finance", "management"]
    )
    
    print("\n🎉 Hoàn thành kiểm thử quét thư mục.")

if __name__ == "__main__":
    main()
