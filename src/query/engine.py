import os
import json
from typing import List, Dict, Any, Tuple
import cohere
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter, 
    FieldCondition, 
    MatchAny, 
    PointStruct, 
    SparseVector, 
    Prefetch, 
    Fusion,
    FusionQuery
)
from fastembed import SparseTextEmbedding
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.qdrant_client import get_qdrant_client
from src.core.neo4j_client import Neo4jClient

# Khởi tạo mô hình Sparse Embedding cục bộ (BM25) cho Query
print("⏳ Đang khởi tạo mô hình Sparse Embedding cho Query...")
sparse_embedding_model = SparseTextEmbedding(model_name="Qdrant/bm25")
print("✅ Khởi tạo mô hình Sparse Embedding thành công.")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    reraise=True
)
def classify_query(query_str: str) -> str:
    """Phân loại câu hỏi của người dùng để định tuyến (Router):
    - Trả về 'simple' nếu là câu hỏi tra cứu thông tin đơn giản.
    - Trả về 'complex' nếu là câu hỏi cần tìm mối quan hệ hoặc tổng hợp phức tạp.
    """
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    prompt = f"""
    Bạn là bộ định tuyến truy vấn (Query Router) thông minh. Hãy phân tích câu hỏi dưới đây và phân loại nó vào một trong hai nhóm:
    1. 'simple': Nếu câu hỏi mang tính chất tra cứu thông số, định nghĩa, thông tin cụ thể, hoặc một đoạn nội dung ngắn.
    2. 'complex': Nếu câu hỏi yêu cầu phân tích mối quan hệ giữa các đối tượng, so sánh, tổng hợp thông tin từ nhiều nguồn, hoặc tìm các thực thể liên kết với nhau.

    Chỉ trả về duy nhất một từ 'simple' hoặc 'complex', không giải thích gì thêm.

    Câu hỏi: "{query_str}"
    Phân loại:
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    result = response.choices[0].message.content.strip().lower()
    return "complex" if "complex" in result else "simple"


def retrieve_qdrant_hybrid(
    query_str: str, 
    collection_name: str, 
    user_groups: List[str], 
    top_k: int = 10
) -> List[Tuple[str, float]]:
    """Tìm kiếm Hybrid (Dense + Sparse) trên Qdrant lọc theo phân quyền người dùng (user_groups).
    Có cơ chế fallback sang Dense Search truyền thống nếu phiên bản Qdrant/Client gặp lỗi.
    """
    client = get_qdrant_client()
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # 1. Sinh dense vector bằng OpenAI
    response = openai_client.embeddings.create(
        input=query_str,
        model="text-embedding-3-small"
    )
    query_vector = response.data[0].embedding
    
    # Thiết lập bộ lọc bảo mật RBAC: Point phải có ít nhất 1 group trùng với group của user
    rbac_filter = Filter(
        must=[
            FieldCondition(
                key="group_access",
                match=MatchAny(any=user_groups)
            )
        ]
    )
    
    try:
        # 2. Sinh sparse vector cục bộ bằng fastembed
        sparse_embs = list(sparse_embedding_model.query_embed(query_str))
        sparse_embedding = sparse_embs[0]
        
        # 3. Truy vấn Hybrid bằng query_points API (Qdrant 1.9+) kết hợp RRF
        search_results = client.query_points(
            collection_name=collection_name,
            prefetch=[
                Prefetch(
                    query=query_vector, 
                    using="dense", 
                    limit=top_k
                ),
                Prefetch(
                    query=SparseVector(
                        indices=list(sparse_embedding.indices),
                        values=list(sparse_embedding.values)
                    ),
                    using="sparse",
                    limit=top_k
                )
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=rbac_filter,
            limit=top_k
        )
        # Trả về dạng list [(content, score)]
        return [(res.payload["text"], res.score) for res in search_results.points]
        
    except Exception as e:
        print(f"⚠️ Không thể chạy Hybrid Search (sử dụng query_points): {e}. Fallback sang Dense Search...")
        # Fallback sang Dense Search truyền thống
        try:
            search_results = client.query_points(
                collection_name=collection_name,
                query=query_vector,
                using="dense",
                query_filter=rbac_filter,
                limit=top_k
            )
            return [(res.payload["text"], res.score) for res in search_results.points]
        except Exception as err:
            print(f"❌ Lỗi tìm kiếm Qdrant: {err}")
            return []


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    reraise=True
)
def retrieve_neo4j_graph(query_str: str, user_groups: List[str]) -> List[str]:
    """Sử dụng LLM sinh truy vấn Neo4j Cypher bảo mật để trích xuất các quan hệ thực thể"""
    neo4j = Neo4jClient()
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # Prompt yêu cầu LLM bắt buộc nhúng bộ lọc bảo mật group_access dựa trên danh sách $user_groups
    prompt = f"""
    Dựa trên câu hỏi sau, hãy tạo một câu truy vấn Neo4j Cypher tương ứng để tìm thông tin liên quan.
    Bạn phải bảo mật dữ liệu ở mức đồ thị: Tất cả các Node và Edge đều chứa thuộc tính danh sách `group_access` (ví dụ: ['public', 'finance']).
    Do đó, trong câu truy vấn Cypher, bạn BẮT BUỘC phải thêm điều kiện lọc:
    - `any(g IN n.group_access WHERE g IN $user_groups)` cho mọi node `n` xuất hiện.
    - `any(g IN r.group_access WHERE g IN $user_groups)` cho mọi quan hệ `r` xuất hiện.

    Chỉ trả về câu truy vấn Cypher duy nhất trong thẻ ```cypher, không giải thích thêm.
    Sử dụng tham số truy vấn `$user_groups` truyền vào thay vì hardcode danh sách nhóm.

    Ví dụ câu truy vấn bảo mật chuẩn:
    MATCH (s)-[r]->(t) 
    WHERE s.name CONTAINS 'Công ty X' 
      AND any(g IN s.group_access WHERE g IN $user_groups)
      AND any(g IN r.group_access WHERE g IN $user_groups)
      AND any(g IN t.group_access WHERE g IN $user_groups)
    RETURN s.name, type(r), t.name, r.description LIMIT 5

    Câu hỏi: "{query_str}"
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    raw_content = response.choices[0].message.content
    if "```cypher" in raw_content:
        cypher = raw_content.split("```cypher")[1].split("```")[0].strip()
    else:
        cypher = raw_content.strip()
        
    print(f"🤖 Sinh truy vấn Cypher: {cypher}")
    
    try:
        # Thực thi Cypher an toàn bằng cách truyền tham số bảo mật user_groups
        results = neo4j.query(cypher, {"user_groups": user_groups})
        
        formatted_results = []
        for record in results:
            desc = list(record.values())
            # Trích xuất và định dạng kết quả thành chuỗi mô tả quan hệ
            formatted_results.append(f"Mối quan hệ đồ thị tìm thấy: {', '.join(map(str, desc))}")
        return formatted_results
    except Exception as e:
        print(f"⚠️ Neo4j Query Lỗi: {e}")
        return []
    finally:
        neo4j.close()


def reciprocal_rank_fusion(
    vector_results: List[Tuple[str, float]], 
    graph_results: List[str], 
    k: int = 60
) -> List[str]:
    """Hợp nhất xếp hạng kết quả từ Vector DB và Graph DB dựa trên thuật toán RRF"""
    rrf_scores = {}
    
    # 1. Cộng điểm từ kết quả Vector DB (Qdrant)
    for rank, (text, _) in enumerate(vector_results):
        rrf_scores[text] = rrf_scores.get(text, 0) + (1.0 / (k + rank + 1))
        
    # 2. Cộng điểm từ kết quả Graph DB (Neo4j)
    for rank, text in enumerate(graph_results):
        rrf_scores[text] = rrf_scores.get(text, 0) + (1.0 / (k + rank + 1))
        
    # Sắp xếp lại theo điểm RRF giảm dần
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc[0] for doc in sorted_docs]


def query_rag_engine(
    query_str: str, 
    collection_name: str, 
    user_groups: List[str]
) -> str:
    """Luồng RAG chính phối hợp định tuyến, truy xuất hỗn hợp, rerank và tạo câu trả lời"""
    print(f"\n🔍 Nhận truy vấn: '{query_str}'")
    print(f"🔒 Quyền hạn người dùng: {user_groups}")
    
    # 1. Định tuyến câu hỏi
    intent = classify_query(query_str)
    print(f"🧭 Bộ định tuyến phân loại Intent: '{intent.upper()}'")
    
    # 2. Lấy dữ liệu theo định tuyến
    vector_res = []
    graph_res = []
    
    if intent == "simple":
        # Với câu hỏi đơn giản, chỉ tìm trên Vector DB để tiết kiệm chi phí
        vector_res = retrieve_qdrant_hybrid(query_str, collection_name, user_groups, top_k=5)
    else:
        # Với câu hỏi phức tạp, truy vấn song song cả Vector DB và Graph DB
        vector_res = retrieve_qdrant_hybrid(query_str, collection_name, user_groups, top_k=10)
        graph_res = retrieve_neo4j_graph(query_str, user_groups)
        
    # 3. Gộp kết quả bằng RRF
    merged_contexts = reciprocal_rank_fusion(vector_res, graph_res)
    
    if not merged_contexts:
         return "Xin lỗi, tôi không tìm thấy tài liệu nào liên quan hoặc bạn không có quyền truy cập vào thông tin này."
         
    # 4. Rerank ngữ cảnh sử dụng Cohere Rerank Multilingual
    # Đảm bảo xử lý lỗi và suy thoái mềm (graceful degradation) nếu API Cohere gặp lỗi
    final_contexts = merged_contexts[:5]  # Fallback mặc định lấy top 5 từ RRF
    
    try:
        cohere_client = cohere.Client(api_key=settings.COHERE_API_KEY)
        rerank_response = cohere_client.rerank(
            query=query_str,
            documents=merged_contexts,
            top_n=5,
            model="rerank-multilingual-v3.0"  # Model tối ưu hóa đa ngôn ngữ bao gồm tiếng Việt
        )
        final_contexts = [merged_contexts[res.index] for res in rerank_response.results]
        print("🎯 Đã sắp xếp lại ngữ cảnh bằng Cohere Rerank thành công.")
    except Exception as e:
        print(f"⚠️ Cohere Rerank gặp sự cố: {e}. Sử dụng kết quả RRF gốc làm dự phòng.")
        
    # 5. Gửi ngữ cảnh và sinh câu trả lời bằng OpenAI
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    context_str = "\n---\n".join(final_contexts)
    
    system_prompt = """Bạn là trợ lý ảo thông minh bảo mật cho doanh nghiệp. 
    Nhiệm vụ của bạn là trả lời chính xác câu hỏi của người dùng chỉ dựa vào các ngữ cảnh (context) được cung cấp dưới đây.
    
    Quy tắc an toàn & ứng xử:
    1. Nếu ngữ cảnh được cung cấp không chứa thông tin để trả lời câu hỏi, hãy trả lời lịch sự rằng bạn không có thông tin tương ứng.
    2. Tuyệt đối không tự bịa đặt câu trả lời (ảo giác - hallucination).
    3. Trả lời bằng ngôn ngữ trùng với ngôn ngữ của câu hỏi (mặc định tiếng Việt).
    """
    
    prompt = f"""
    Ngữ cảnh được cung cấp:
    {context_str}

    Câu hỏi: "{query_str}"
    Câu trả lời:
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Lỗi khi sinh câu trả lời bằng LLM: {e}"
