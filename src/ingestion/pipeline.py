import os
import json
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any

from llama_parse import LlamaParse
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from qdrant_client.models import (
    PointStruct, 
    SparseVectorParams, 
    VectorParams, 
    Distance, 
    SparseVector
)
from fastembed import SparseTextEmbedding
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.qdrant_client import get_qdrant_client
from src.core.neo4j_client import Neo4jClient

# Thư mục và file registry quản lý trạng thái nạp dữ liệu
REGISTRY_PATH = os.path.join("data", ".ingestion_registry.json")

# Khởi tạo model sinh Sparse Vectors cục bộ (BM25)
# Sử dụng fastembed chạy hoàn toàn miễn phí trên CPU cục bộ
print("⏳ Đang khởi tạo mô hình Sparse Embedding cục bộ (BM25)...")
sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25")
print("✅ Khởi tạo mô hình Sparse Embedding thành công.")


def get_stable_uuid(text: str) -> str:
    """Tạo Point ID dạng UUID v5 duy nhất dựa trên nội dung văn bản.
    Giúp chống trùng lặp dữ liệu vật lý khi nạp lại.
    """
    hasher = hashlib.md5(text.encode("utf-8"))
    return str(uuid.UUID(hasher.hexdigest()))


def get_file_hash(file_path: str) -> str:
    """Tính toán SHA256 mã băm của file để xác định thay đổi nội dung"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_registry() -> Dict[str, Any]:
    """Tải lịch sử nạp dữ liệu từ file registry"""
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Không thể đọc registry file, sẽ khởi tạo mới: {e}")
            return {}
    return {}


def save_registry(registry: Dict[str, Any]):
    """Lưu lịch sử nạp dữ liệu vào file registry"""
    os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    try:
        with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Không thể lưu registry file: {e}")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def parse_and_chunk_document(file_path: str) -> List[Any]:
    """Trích xuất file PDF thành các chunk dựa trên ngữ nghĩa.
    Tích hợp Tenacity retry khi gọi API của LlamaParse.
    """
    print(f"📄 Đang xử lý file: {file_path} bằng LlamaParse...")
    
    # Khởi tạo LlamaParse
    parser = LlamaParse(
        api_key=settings.LLAMAPARSE_API_KEY,
        result_type="markdown",
        verbose=True
    )
    
    # Lấy tài liệu thô dưới dạng Markdown
    documents = parser.load_data(file_path)
    
    # Cấu hình Semantic Chunking sử dụng Local Model (FastEmbed) thay vì OpenAI để tiết kiệm chi phí
    embed_model = FastEmbedEmbedding(model_name="BAAI/bge-small-en-v1.5")
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model
    )
    
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"✅ Đã phân tách thành {len(nodes)} semantic chunks.")
    return nodes


def setup_hybrid_collection(collection_name: str):
    """Khởi tạo cấu trúc collection Qdrant hỗ trợ Hybrid Search (Dense + Sparse)"""
    client = get_qdrant_client()
    
    # Kiểm tra xem collection đã tồn tại chưa
    collections = client.get_collections().collections
    exists = any(c.name == collection_name for c in collections)
    
    if exists:
        print(f"ℹ️ Collection '{collection_name}' đã tồn tại. Sẽ tiến hành cập nhật dữ liệu.")
        return
        
    print(f"🔑 Đang tạo mới Hybrid Collection: {collection_name}")
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(
                size=1536,  # Kích thước vector của OpenAI text-embedding-3-small
                distance=Distance.COSINE
            )
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams()  # Cấu hình Sparse Vector cho tìm kiếm BM25
        }
    )
    print(f"✅ Đã tạo thành công collection: {collection_name}")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def ingest_to_qdrant(collection_name: str, chunks: List[Any], group_access_list: List[str], file_path: str):
    """Sinh dense embedding (OpenAI), sparse vector (fastembed) và nạp vào Qdrant kèm RBAC"""
    client = get_qdrant_client()
    
    # Đảm bảo collection được thiết lập đúng cấu hình
    setup_hybrid_collection(collection_name)
    
    embed_model = OpenAIEmbedding(api_key=settings.OPENAI_API_KEY)
    points = []
    
    # Chuẩn bị toàn bộ text để sinh sparse vector theo batch
    texts = [chunk.get_content() for chunk in chunks]
    print(f"⚡ Đang sinh Sparse Vector cho {len(texts)} chunks...")
    sparse_embeddings = list(sparse_embedding_model.embed(texts))
    
    print(f"⚡ Đang sinh Dense Vector & nạp dữ liệu vào Qdrant...")
    for idx, chunk in enumerate(chunks):
        text_content = chunk.get_content()
        
        # Sinh dense vector bằng OpenAI
        dense_vector = embed_model.get_text_embedding(text_content)
        
        # Lấy sparse vector tương ứng từ fastembed
        sparse_emb = sparse_embeddings[idx]
        
        # Tạo ID dạng UUID ổn định dựa trên mã băm nội dung chunk
        point_id = get_stable_uuid(text_content)
        
        point = PointStruct(
            id=point_id,
            vector={
                "dense": dense_vector,
                "sparse": SparseVector(
                    indices=list(sparse_emb.indices),
                    values=list(sparse_emb.values)
                )
            },
            payload={
                "text": text_content,
                "metadata": chunk.metadata,
                "file_path": file_path,          # Lưu đường dẫn file nguồn
                "group_access": group_access_list  # Metadata phân quyền
            }
        )
        points.append(point)
        
    client.upsert(collection_name=collection_name, points=points)
    print(f"✅ Đã nạp {len(points)} bản ghi vào Qdrant collection: {collection_name}")


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def extract_graph_triplets(text_content: str) -> Dict[str, Any]:
    """Sử dụng LLM trích xuất danh sách Nodes và Edges dạng JSON"""
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = f"""
    Hãy phân tích đoạn văn bản sau và trích xuất tất cả các thực thể (entities) cùng các mối quan hệ (relations) giữa chúng.
    Trả về định dạng JSON duy nhất như ví dụ dưới đây, không kèm text giải thích nào khác.

    Định dạng đầu ra:
    {{
      "nodes": [
        {{"id": "A", "label": "Company", "name": "Công ty X"}},
        {{"id": "B", "label": "Person", "name": "Nguyễn Văn A"}}
      ],
      "edges": [
        {{"source": "B", "target": "A", "type": "FOUNDED", "desc": "Nguyễn Văn A sáng lập Công ty X"}}
      ]
    }}

    Văn bản cần phân tích:
    "{text_content}"
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)


def ingest_to_neo4j(chunks: List[Any], file_path: str):
    """Duyệt qua các chunk và nạp đồ thị vào Neo4j sử dụng các câu lệnh MERGE tránh trùng lặp"""
    neo4j = Neo4jClient()
    
    try:
        for idx, chunk in enumerate(chunks):
            text_content = chunk.get_content()
            print(f"🌿 Đang phân tích đồ thị cho chunk {idx + 1}/{len(chunks)}...")
            triplets = extract_graph_triplets(text_content)
            
            # 1. Tạo hoặc cập nhật các Node (Thực thể)
            for node in triplets.get("nodes", []):
                # Clean label & parameters to avoid injection or schema syntax error
                label = "".join(char for char in node.get("label", "Entity") if char.isalnum())
                # Cypher lưu vết các files chứa thực thể này dưới dạng danh sách
                cypher = f"""
                MERGE (n:{label} {{id: $id}})
                SET n.name = $name
                WITH n
                WHERE NOT $file_path IN coalesce(n.source_files, [])
                SET n.source_files = coalesce(n.source_files, []) + $file_path
                """
                neo4j.query(cypher, {
                    "id": str(node["id"]), 
                    "name": str(node["name"]),
                    "file_path": file_path
                })
                
            # 2. Tạo hoặc cập nhật các Edge liên kết (Quan hệ)
            for edge in triplets.get("edges", []):
                edge_type = "".join(char for char in edge.get("type", "RELATED_TO") if char.isalnum() or char == "_").upper()
                cypher = f"""
                MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
                MERGE (source)-[r:{edge_type}]->(target)
                SET r.description = $desc
                WITH r
                WHERE NOT $file_path IN coalesce(r.source_files, [])
                SET r.source_files = coalesce(r.source_files, []) + $file_path
                """
                neo4j.query(cypher, {
                    "source_id": str(edge["source"]),
                    "target_id": str(edge["target"]),
                    "desc": str(edge["desc"]),
                    "file_path": file_path
                })
        print("✅ Đã hoàn thành nạp dữ liệu đồ thị vào Neo4j.")
    finally:
        neo4j.close()


def purge_document_data(file_path: str, collection_name: str):
    """Xóa toàn bộ dữ liệu liên quan đến file_path khỏi Qdrant và Neo4j"""
    print(f"🧹 Đang dọn dẹp dữ liệu của file: '{file_path}' khỏi các DB...")
    
    # 1. Xóa khỏi Qdrant
    client = get_qdrant_client()
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="file_path",
                        match=MatchValue(value=file_path)
                    )
                ]
            )
        )
        print(f"✅ Đã xóa các vector points liên quan đến '{file_path}' khỏi Qdrant.")
    except Exception as e:
        print(f"⚠️ Lỗi khi xóa dữ liệu Qdrant: {e}")
        
    # 2. Xóa khỏi Neo4j
    neo4j = Neo4jClient()
    try:
        # Gỡ file_path khỏi danh sách source_files của các mối quan hệ (Edges)
        neo4j.query("""
        MATCH ()-[r]->()
        WHERE $file_path IN coalesce(r.source_files, [])
        SET r.source_files = [x IN r.source_files WHERE x <> $file_path]
        """, {"file_path": file_path})
        
        # Xóa các mối quan hệ bị mồ côi (không còn thuộc file nào)
        neo4j.query("""
        MATCH ()-[r]->()
        WHERE size(coalesce(r.source_files, [])) = 0
        DELETE r
        """)
        
        # Gỡ file_path khỏi danh sách source_files của các thực thể (Nodes)
        neo4j.query("""
        MATCH (n)
        WHERE $file_path IN coalesce(n.source_files, [])
        SET n.source_files = [x IN n.source_files WHERE x <> $file_path]
        """, {"file_path": file_path})
        
        # Xóa các thực thể bị mồ côi (không còn thuộc file nào)
        neo4j.query("""
        MATCH (n)
        WHERE size(coalesce(n.source_files, [])) = 0
        DETACH DELETE n
        """)
        
        print(f"✅ Đã dọn dẹp đồ thị thực thể liên quan đến '{file_path}' khỏi Neo4j.")
    except Exception as e:
        print(f"⚠️ Lỗi khi dọn dẹp đồ thị Neo4j: {e}")
    finally:
        neo4j.close()


def scan_and_ingest_directory(directory_path: str, collection_name: str, group_access_list: List[str]):
    """Quét toàn bộ thư mục dữ liệu, đối chiếu registry để chỉ nạp các file PDF mới/thay đổi và xóa dữ liệu thừa của file đã mất"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"📁 Đã tạo thư mục dữ liệu trống tại: {directory_path}. Hãy thêm file PDF vào đây.")
        return

    # Tải registry
    registry = load_registry()
    
    # 1. Tìm và đồng bộ hóa (Purge) dữ liệu của các file đã bị xóa cục bộ
    active_files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) if f.lower().endswith(".pdf")]
    active_files_set = set(active_files)
    
    registry_files = list(registry.keys())
    for reg_file in registry_files:
        if reg_file not in active_files_set:
            print(f"🗑️ Phát hiện file đã bị xóa cục bộ: '{reg_file}'")
            purge_document_data(reg_file, collection_name)
            del registry[reg_file]
            save_registry(registry)
            print(f"✅ Đã gỡ bỏ file '{reg_file}' khỏi registry.")
            
    # 2. Tìm toàn bộ file PDF hiện có
    if not active_files:
        print(f"ℹ️ Không tìm thấy file PDF nào trong thư mục '{directory_path}'.")
        return
        
    print(f"🔍 Tìm thấy {len(active_files)} file PDF hoạt động. Đang kiểm tra trạng thái nạp...")
    
    for file_path in active_files:
        filename = os.path.basename(file_path)
        current_hash = get_file_hash(file_path)
        
        # Kiểm tra xem file đã từng được nạp chưa
        file_entry = registry.get(file_path)
        
        if file_entry and file_entry.get("hash") == current_hash:
            print(f"⏭️ Bỏ qua '{filename}' (File này đã được nạp và không có thay đổi).")
            continue
            
        print(f"🚀 Bắt đầu xử lý file mới/thay đổi: '{filename}'")
        try:
            # 1. Parse & Chunk
            chunks = parse_and_chunk_document(file_path)
            
            if not chunks:
                print(f"⚠️ Không trích xuất được chunk nào từ file '{filename}'.")
                continue
                
            # 2. Ingest Qdrant
            ingest_to_qdrant(collection_name, chunks, group_access_list, file_path)
            
            # 3. Ingest Neo4j
            ingest_to_neo4j(chunks, file_path)
            
            # 4. Cập nhật registry
            registry[file_path] = {
                "hash": current_hash,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            save_registry(registry)
            print(f"🎉 Đã nạp thành công và cập nhật registry cho file: '{filename}'")
            
        except Exception as e:
            print(f"❌ Thất bại khi xử lý file '{filename}': {e}")
            registry[file_path] = {
                "hash": current_hash,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
            save_registry(registry)
