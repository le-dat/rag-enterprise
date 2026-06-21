import logging
from typing import List, Dict, Any, Optional
from src.auth.jwt_handler import UserContext

logger = logging.getLogger(__name__)

# Standard Query blocked exception
class QueryBlockedError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Query blocked by Input Rail: {reason}")


class MockSearchEngine:
    _MOCK_CHUNKS = [
        # HR Chunks - Staff level
        {
            "chunk_id": "hr_leave_01",
            "text": "Chính sách Nghỉ phép: Mỗi nhân viên chính thức tại Enterprise RAG được hưởng 12 ngày nghỉ phép năm hưởng nguyên lương. Việc đăng ký nghỉ phép phải được thực hiện trước ít nhất 5 ngày làm việc thông qua Hệ thống Portal Nhân sự.",
            "source": "chinh_sach_nhan_su_2026.pdf",
            "department": "HR",
            "role": "staff",
            "page": 4
        },
        {
            "chunk_id": "hr_benefit_02",
            "text": "Quyền lợi Bảo hiểm Sức khỏe: Công ty đài thọ 100% chi phí mua bảo hiểm sức khỏe cao cấp UIC cho toàn bộ nhân viên chính thức. Nhân viên có thể đăng ký mua thêm bảo hiểm cho người thân (vợ/chồng, con cái) với mức ưu đãi giảm giá 50% phí thường niên.",
            "source": "phuc_loi_y_te.pdf",
            "department": "HR",
            "role": "staff",
            "page": 2
        },
        {
            "chunk_id": "hr_workhours_03",
            "text": "Quy định Giờ làm việc tiêu chuẩn: Thời gian làm việc chính thức tại văn phòng là từ 9:00 sáng đến 6:00 chiều, từ thứ Hai đến thứ Sáu hàng tuần. Thời gian nghỉ trưa cố định là 1 tiếng từ 12:00 trưa đến 1:00 chiều.",
            "source": "noi_quy_lao_dong.pdf",
            "department": "HR",
            "role": "staff",
            "page": 1
        },
        # HR Chunks - Manager level
        {
            "chunk_id": "hr_mgr_leave_01",
            "text": "Quy trình phê duyệt nghỉ phép của quản lý: Quản lý trực tiếp (Manager) có thẩm quyền phê duyệt các đơn xin nghỉ phép năm của nhân viên cấp dưới trực thuộc với thời gian nghỉ liên tục không quá 5 ngày làm việc. Đơn nghỉ phép từ 6 ngày trở lên cần có sự phê chuẩn từ Trưởng phòng Nhân sự.",
            "source": "so_tay_quan_ly.pdf",
            "department": "HR",
            "role": "manager",
            "page": 12
        },
        {
            "chunk_id": "hr_mgr_review_02",
            "text": "Hướng dẫn Đánh giá Hiệu suất: Quản lý bộ phận có trách nhiệm thực hiện đánh giá hiệu suất công việc định kỳ hàng quý (Performance Review) cho các nhân viên trực thuộc. Thang điểm đánh giá từ 1 (Không đạt yêu cầu) đến 5 (Xuất sắc). Kết quả đánh giá là cơ sở xét thưởng và tăng lương định kỳ.",
            "source": "quy_trinh_danh_gia_v2.pdf",
            "department": "HR",
            "role": "manager",
            "page": 8
        },
        # Sales Chunks - Staff level
        {
            "chunk_id": "sales_commission_01",
            "text": "Cơ chế tính Hoa hồng doanh số: Chuyên viên kinh doanh được hưởng lương cứng cơ bản kèm theo tỷ lệ hoa hồng hoa lợi đạt 3% giá trị hợp đồng đối với tất cả các giao dịch bán hàng đã ký kết và nghiệm thu thành công có giá trị tối thiểu từ $10,000 USD mỗi tháng.",
            "source": "chinh_sach_luong_thuong.pdf",
            "department": "Sales",
            "role": "staff",
            "page": 3
        },
        {
            "chunk_id": "sales_leads_02",
            "text": "Quy tắc phân bổ Lead khách hàng: Các lead thông tin khách hàng mới từ hệ thống Marketing inbound sẽ tự động được phân chia ngẫu nhiên xoay vòng (Round-Robin) cho các chuyên viên kinh doanh đang ở trạng thái active trực tuyến trong vòng tối đa 15 phút.",
            "source": "sales_operations.pdf",
            "department": "Sales",
            "role": "staff",
            "page": 1
        },
        # Sales Chunks - Manager level
        {
            "chunk_id": "sales_mgr_target_01",
            "text": "Chỉ tiêu doanh số Quý 3: Tổng chỉ tiêu doanh thu Sales của bộ phận kinh doanh đặt ra cho Quý 3 là $1.2M USD. Trưởng nhóm/Quản lý kinh doanh khu vực có trách nhiệm lập kế hoạch, chia nhỏ chỉ tiêu và giao chỉ tiêu doanh số cụ thể (KIP) cho từng nhân viên kinh doanh trong nhóm.",
            "source": "ke_hoach_sales_q3.pdf",
            "department": "Sales",
            "role": "manager",
            "page": 6
        },
        {
            "chunk_id": "sales_mgr_discount_02",
            "text": "Hạn mức duyệt Chiết khấu giá: Nhân viên kinh doanh được phép chủ động chiết khấu giảm giá cho khách hàng tối đa 10% giá trị hợp đồng niêm yết. Mức chiết khấu từ 11% đến 25% bắt buộc phải có phê duyệt bằng văn bản của Quản lý bộ phận Sales.",
            "source": "chinh_sach_gia_ca.pdf",
            "department": "Sales",
            "role": "manager",
            "page": 14
        }
    ]

    def __init__(self, *args, **kwargs):
        logger.info("[DEMO MODE] Initialized MockSearchEngine")

    def search(self, query_text: str, user: UserContext, limit: int = 10) -> List[Dict[str, Any]]:
        logger.info(f"[DEMO MODE] Simulating search for: {query_text!r} under user={user.user_id} ({user.department}/{user.role})")
        
        # 1. Filter by Department
        dept_chunks = [c for c in self._MOCK_CHUNKS if c["department"].lower() == user.department.lower()]
        
        # 2. Filter by Role (RBAC)
        rbac_chunks = []
        for c in dept_chunks:
            if user.role.lower() == "manager":
                rbac_chunks.append(c)
            elif c["role"].lower() == "staff":
                rbac_chunks.append(c)
                
        # 3. Score chunks by checking keyword match overlap
        scored_chunks = []
        query_words = set(query_text.lower().split())
        for c in rbac_chunks:
            chunk_words = set(c["text"].lower().split())
            overlap = len(query_words.intersection(chunk_words))
            score = 0.5 + (0.1 * overlap)
            score = min(score, 0.99)
            
            c_copy = c.copy()
            c_copy["score"] = score
            scored_chunks.append(c_copy)
            
        # 4. Sort and limit
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"[DEMO MODE] Found {len(scored_chunks)} mock matching chunks.")
        return scored_chunks[:limit]


class MockReranker:
    def __init__(self, *args, **kwargs):
        logger.info("[DEMO MODE] Initialized MockReranker")

    def rerank(self, query: str, documents: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
        logger.info(f"[DEMO MODE] Bypassing reranking for {len(documents)} documents.")
        return documents[:top_n]


class MockGenerator:
    def __init__(self, *args, **kwargs):
        logger.info("[DEMO MODE] Initialized MockGenerator")

    def generate(self, query: str, documents: List[Dict[str, Any]]) -> str:
        logger.info(f"[DEMO MODE] Generating mock response for query: {query!r}")
        
        if not documents:
            return "Không tìm thấy tài liệu phù hợp trong ngữ cảnh phòng ban và vai trò của bạn để trả lời câu hỏi này. (No relevant context found under your current role and department context)."
            
        # Determine language based on query content
        is_vietnamese = any(char in "đĐàáảãạằắẳẵặềếểễệìíỉĩịòóỏõọồốổỗộùúủũụỳýỷỹỵ" for char in query) or any(w in query.lower() for w in ["nghỉ", "phép", "giờ", "lương", "bảo", "hiểm", "thưởng", "hoa", "hồng"])
        
        if is_vietnamese:
            intro = "Dựa trên các tài liệu nghiệp vụ được phê duyệt an toàn (RBAC) cho tài khoản của bạn:\n\n"
            bullets = []
            for doc in documents:
                text = doc.get("text", "")
                source = doc.get("source", "unknown")
                page = doc.get("page", "N/A")
                chunk_id = doc.get("chunk_id", "unknown")
                bullets.append(f"• Theo [{source}] (trang {page}): {text} [{chunk_id}]")
            
            outro = "\n\n(Lưu ý: Phản hồi này được tự động mô phỏng và xác thực tại local ở chế độ DEMO MODE)."
            return intro + "\n".join(bullets) + outro
        else:
            intro = "Based on the secure business documents authorized under your RBAC clearance:\n\n"
            bullets = []
            for doc in documents:
                text = doc.get("text", "")
                source = doc.get("source", "unknown")
                page = doc.get("page", "N/A")
                chunk_id = doc.get("chunk_id", "unknown")
                bullets.append(f"• According to [{source}] (Page {page}): {text} [{chunk_id}]")
                
            outro = "\n\n(Note: This response is dynamically generated in local DEMO MODE simulation)."
            return intro + "\n".join(bullets) + outro


class MockGroundingChecker:
    def __init__(self, *args, **kwargs):
        logger.info("[DEMO MODE] Initialized MockGroundingChecker")

    def check_grounding(self, documents: List[Dict[str, Any]], answer: str) -> Dict[str, Any]:
        logger.info("[DEMO MODE] Grounding checker bypassed.")
        return {
            "grounded": True,
            "reason": "Demo Mode: Verified grounded context locally (simulated)."
        }


class MockInputRail:
    def __init__(self, *args, **kwargs):
        logger.info("[DEMO MODE] Initialized MockInputRail")
        # Initialize basic patterns for local heuristic check
        self._HEURISTIC_PATTERNS = [
            r"ignore\s+(?:previous|above|all|every|prior)\s+(?:instructions?|prompts?|directives?|rules?)",
            r"forget\s+(?:previous|above|all|every|prior)\s+(?:instructions?|prompts?|directives?|rules?)",
            r"you\s+are\s+now\s+(?:a|an|the)",
            r"act\s+as\s+(?:a|an|the)\s+(?:dan|jailbreak|evil|unrestricted)",
            r"disregard\s+(?:your|all|the)\s+(?:instructions?|guidelines?|rules?|training)",
            r"override\s+(?:your|the|all)\s+(?:instructions?|directives?|safety)",
            r"new\s+(?:system\s+)?(?:instruction|directive|prompt|rule)",
            r"system\s*:\s*\S",
            r"<\s*system\s*>",
            r"\[\s*system\s*\]",
            r"reveal\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)",
            r"print\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?)",
        ]
        import re
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self._HEURISTIC_PATTERNS]

    def validate_query(self, query: str) -> None:
        if not query or not query.strip():
            return
            
        # Run heuristic checks so prompt injection demo still works
        query_lower = query.lower()
        if any(p.search(query_lower) for p in self._compiled):
            logger.warning(f"🚨 [DEMO MODE] INPUT RAIL [heuristic] blocked query: {query[:120]!r}")
            raise QueryBlockedError("Query contains a known prompt-injection pattern.")
            
        logger.info("[DEMO MODE] InputRail check bypassed.")


class MockRetrievalRail:
    def __init__(self, *args, **kwargs):
        logger.info("[DEMO MODE] Initialized MockRetrievalRail")

    def validate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logger.info("[DEMO MODE] RetrievalRail bypassed.")
        return chunks
