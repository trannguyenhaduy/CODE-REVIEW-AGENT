# SE373 · Buổi 06: RAG Cho Hệ Thống Phần Mềm & Kiến Trúc Knowledge Harness

> **Môn học:** SE373 — Kỹ thuật xây dựng hệ thống Agentic AI (FIT - HCMUS / UIT)  
> **Chủ đề:** RAG trong kiến trúc Harness, Ingestion/Chunking/Metadata, Embedding & Vector DB, Hybrid Search, Reranking, Grounding & Đánh giá  
> **Giảng viên lý thuyết:** TS. Đỗ Trọng Hợp · ThS. Ngô Ngọc Đăng Khoa · ThS. Phạm Hoàng Hải  
> **Giảng viên thực hành:** Bùi Cao Doanh · Dương Nguyễn Phương Nam · Nguyễn Hiếu Nghĩa · Nguyễn Ngọc Quí · Nguyễn Thị Hoàng Anh · Quan Chí Khánh An  
> **Mục tiêu cốt lõi:** Xây dựng pipeline RAG có trích dẫn kiểm chứng được và đo lường chất lượng bằng số liệu thực nghiệm.

---

## 1. RAG Trong Kiến Trúc Harness (Phần 1)

### 1.1. Khái niệm & Vị trí trong Hệ thống Agentic
* **Định nghĩa RAG (Retrieval-Augmented Generation):** Mẫu kiến trúc sinh câu trả lời dựa trên ngữ cảnh được truy xuất từ kho dữ liệu ngoài theo thời gian thực.
* **Vị trí của RAG:** Nằm ở **Lớp Harness (Knowledge & Retrieval Harness)** trung gian giữa LLM và kho tri thức (Knowledge Store).
* **Trách nhiệm của Harness:** Quyết định chunk tri thức nào được đưa vào context window của model, bảo đảm tính xác thực, phân quyền và khả năng truy vết.

```
User Query ──► [Retrieval Layer / Harness] ──► Context Injection & Prompt Assembly ──► LLM ──► Grounded Answer
                         ▲
                         │ (Relevant Chunks)
                 [Knowledge Store / External Data]
```

### 1.2. Ba Cơ chế Nạp Tri thức vào AI
| Tiêu chí | 01. Fine-tuning | 02. Context Stuffing | 03. Retrieval (RAG) |
| :--- | :--- | :--- | :--- |
| **Cơ chế** | Nạp vào trọng số của model | Dán toàn bộ tài liệu vào prompt | Truy xuất chunk liên quan theo từng query |
| **Cập nhật tri thức** | Rất chậm (cần train lại) | Tức thì khi đổi file | **Tức thì (Index lại chunk)** |
| **Khả năng trích dẫn** | Không thể (black box) | Có thể nhưng khó chính xác | **Trích dẫn chính xác file, dòng, version** |
| **Chi phí token** | Đắt lúc train, rẻ lúc inference | Rất đắt (nhồi cả repo vào prompt) | **Tiết kiệm (chỉ gửi chunk liên quan)** |
| **Thu hồi dữ liệu** | Không thể xóa (Machine unlearning khó) | Xóa file trong prompt | **Xóa/thu hồi tức thì trong Vector DB** |

### 1.3. Kiến trúc RAG Hai Pha Bắt Buộc (SĐ-3)
Pipeline RAG chuẩn kỹ thuật phần mềm chia làm 2 pha độc lập:
1. **Pha Nạp (Offline Indexing):**
   `Repo / Docs / Issues` ➔ `[01] Document Loader` ➔ `[02] Data Cleaning` ➔ `[03] Chunking & Metadata` ➔ `[04] Embedding Generation` ➔ `[05] Vector DB / Index`
2. **Pha Truy Vấn (Online Querying):**
   `User Query` ➔ `[06] Query Transformation` ➔ `[07] Query Embedding` ➔ `[08] Hybrid Retrieval` ➔ `[09] Cross-Encoder Rerank` ➔ `[10] Prompt Assembly` ➔ `[11] LLM Generation` ➔ `[12] Citation Verification`

> [!CRITICAL]
> **Quy tắc bất biến:** Hai pha nạp và truy vấn **BẮT BUỘC dùng chung đúng một Embedding Model**. Nếu dùng model khác nhau hoặc đổi version embedding mà không re-index, khoảng cách vector sẽ hoàn toàn sai lệch.

### 1.4. Thách thức Khi Nhồi Quá Nhiều Context (Context Stuffing)
* **Chi phí token:** Tăng tuyến tính theo độ dài prompt và số lượng truy vấn.
* **Hiện tượng "Lost in the Middle":** LLM chú ý tốt ở đầu prompt (High) và cuối prompt (High), nhưng suy giảm mạnh độ chính xác ở vùng giữa prompt.
* **Context Rot:** Context càng phình to, khả năng suy luận logic và tuân thủ chỉ dẫn của model càng giảm.
* **Kết luận:** *Dù context window của model có dài tới 1M - 2M tokens, ta vẫn bắt buộc phải dùng RAG để chọn lọc đúng phần cần đọc.*

### 1.5. Năm Loại Tài liệu Kỹ thuật & Chiến lược Phân đoạn
Không được cắt text theo độ dài cố định bừa bãi! Mỗi loại tài liệu phần mềm đòi hỏi chiến lược riêng:
1. **README:** Cắt theo heading (H1, H2, H3), lưu `heading_path`.
2. **API Documentation:** Mỗi endpoint REST/gRPC là một chunk hoàn chỉnh.
3. **Source Code:** Cắt theo AST (Abstract Syntax Tree) bằng Tree-sitter, luôn kèm chữ ký hàm (function signature) và class context.
4. **Spec / ADR (Architecture Decision Record):** Cắt theo section, lưu trạng thái (`status: accepted/superseded`) và ngày quyết định.
5. **Issue / PR:** Giữ trọn vẹn issue kèm thảo luận, tác giả và trạng thái (`open/closed/merged`).

---

## 2. Ingestion, Chunking và Metadata (Phần 2)

### 2.1. Pipeline Ingestion & Tiền xử lý
* **Document Boundary:** Cần xác định ranh giới tài liệu hoàn chỉnh (ví dụ: source code là từng file; issue tracker là từng ticket).
* **Bốn bước tiền xử lý bắt buộc (Deterministic):**
  1. *Loại bỏ nhiễu:* Xóa badge CI/CD, table of contents (TOC), thanh điều hướng, footer bản quyền.
  2. *Bảo toàn code block:* Tuyệt đối không cắt ngang block code triple-backtick, giữ nguyên ngữ cảnh code.
  3. *Giữ nguyên header bảng:* Cắt bảng markdown mà làm mất dòng tiêu đề cột sẽ biến dữ liệu bên dưới thành vô nghĩa.
  4. *Mô tả sơ đồ:* Dùng Vision Model hoặc mô tả alt text để chuyển sơ đồ kiến trúc thành text.

### 2.2. Chiến lược Chunking
* **Định nghĩa Chunk:** Phân đoạn văn bản đủ nhỏ để vector search chính xác, nhưng đủ lớn để mang trọn vẹn ngữ nghĩa độc lập.
* **Overlap:** Vùng đệm gối đầu giữa hai chunk liền kề (thường 10% – 20% kích thước chunk) giúp tránh mất thông tin tại vết cắt.
* **Ba họ chiến lược:**
  * *Fixed-size (theo ký tự/token):* Đều đặn, dễ cài nhưng hay cắt ngang giữa thân hàm, câu hoặc mệnh đề.
  * *Structure-based (theo heading/cú pháp):* Giữ nguyên vẹn cấu trúc logic, kích thước chunk có thể không đều nhau.
  * *Semantic (theo ngữ nghĩa):* Tách khi có bước nhảy khoảng cách vector embedding, chất lượng tốt nhưng tốn tài nguyên.
* **Khuyến nghị cho tài liệu kỹ thuật:** Kết hợp cắt theo Heading trước, nếu đoạn con vượt quá ngưỡng token thì mới cắt tiếp kèm overlap.

### 2.3. Cắt Code theo Cú pháp (Syntax-Aware Chunking)
* Cắt code theo ký tự làm đứt đoạn thân hàm, khiến hàm mất định nghĩa tham số, kiểu trả về và docstring.
* Cần dùng parser chuyên biệt (như `RecursiveCharacterTextSplitter.from_language` hoặc tree-sitter):

```python
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

py_splitter = RecursiveCharacterTextSplitter.from_language(
    language=Language.PYTHON,
    chunk_size=2000,
    chunk_overlap=200
)
chunks = py_splitter.create_documents(
    [code_content],
    metadatas=[{"path": "src/session.py", "lang": "python"}]
)
```

### 2.4. Nguyên tắc "Chunk = Text + Metadata"
> **"Không có Metadata thì không thể trích dẫn được file, số dòng, hay phiên bản!"**

Metadata chính là hệ tọa độ của chunk trong kho tri thức. Bảng schema metadata chuẩn cho codebase:

| Thuộc tính | Kiểu dữ liệu | Ví dụ minh họa | Ý nghĩa |
| :--- | :--- | :--- | :--- |
| `source_type` | `str` | `api_doc`, `code`, `adr`, `convention`, `issue` | Dùng để filter theo loại tài liệu |
| `repo` | `str` | `code-review-agent`, `payment-service` | Định danh kho mã nguồn |
| `path` | `str` | `app/services/auth.py`, `docs/api.md` | Đường dẫn file tương đối |
| `version` / `commit` | `str` | `v2.4.0`, `a3f91c2` | Xác định phiên bản |
| `line_start`, `line_end` | `int` | `118`, `173` | Tọa độ dòng chính xác để highlight/comment |
| `heading_path` | `str` | `API > Sessions > POST /v2` | Cây phân cấp tiêu đề |
| `symbol` | `str` | `SessionManager.refresh_token` | Tên hàm / Class tương ứng |
| `status` | `str` | `active`, `deprecated`, `superseded` | Tránh truy xuất quy ước lỗi thời |
| `chunk_id` | `str` | `sha1_hash:chunk_index` | Khóa chính phục vụ Upsert Idempotent |

### 2.5. Contextual Retrieval (Kỹ thuật từ Anthropic 2024)
* **Vấn đề:** Khi cắt nhỏ thành từng chunk, chunk con mất đi ngữ cảnh cha (ví dụ chỉ thấy dòng `return token` mà không biết đang nằm trong file nào, class nào).
* **Giải pháp:** Gắn 50–100 token mô tả ngữ cảnh tổng quan vào đầu mỗi chunk trước khi sinh vector embedding.
  * *Ví dụ text bổ sung:* `"Tài liệu docs/api.md, mục Deprecated v1 của service thanh toán, mô tả endpoint POST /v1/sessions, đã được thay thế bởi API v2."`
* **Hiệu quả thực nghiệm:** Giảm **49% lỗi truy xuất** (giảm tới **67%** nếu kết hợp cùng Reranking).

---

## 3. Embedding và Vector Database (Phần 3)

### 3.1. Bản chất Embedding: Bắt Ngữ Nghĩa, Mất Ký Tự
* Embedding chuyển văn bản thành vector số thực đa chiều trong không gian ngữ nghĩa (semantic space).
* **Điểm mạnh:** Hiểu được từ đồng nghĩa (ví dụ: *"lỗi xác thực"* gần với *"auth failure"*).
* **Điểm yếu chí mạng trong kỹ thuật phần mềm:**
  * Không bắt được chính xác tên biến, mã lỗi cụ thể (ví dụ: `ERR_40103` vs `ERR_40104`).
  * Khó tìm đúng định danh chính xác (Exact Match) như tên hàm `find_user_by_uuid`.
  * $\rightarrow$ **Cần kết hợp Keyword/BM25 Search (Hybrid Search).**

### 3.2. Nguy cơ Khóa Cứng Model (Embedding Lock-in)
* Khi đã index toàn bộ kho tài liệu với một embedding model (ví dụ `text-embedding-3-small` - 1536 chiều), nếu muốn đổi sang model khác (như `bge-m3` - 1024 chiều), **bắt buộc phải re-embed và re-index 100% dữ liệu**.
* Thiết kế Harness phải bọc lớp Embedding qua Interface để dễ dàng nâng cấp khi cần.

### 3.3. So sánh Vector Database cho Đồ án
| Tiêu chí | ChromaDB (Khuyên dùng) | Qdrant | PGVector (PostgreSQL) |
| :--- | :--- | :--- | :--- |
| **Hình thức** | Embedded / Local (file-based) | Container / Server / Cloud | Extension cho Postgres |
| **Cài đặt** | `pip install chromadb` (cực nhanh) | Chạy Docker | Cần server PostgreSQL |
| **Phù hợp đồ án** | ⭐ **Hoàn hảo cho đồ án và demo local** | Tốt cho production | Tốt khi hệ thống đã có sẵn Postgres |
| **Lọc Metadata** | Hỗ trợ lọc theo dictionary | Rất mạnh mẽ | Dùng SQL `WHERE` |

### 3.4. Cài đặt Upsert Idempotent (Chống nhân đôi dữ liệu)
Khi re-index, nếu không có cơ chế định danh duy nhất (Idempotency), database sẽ bị trùng lặp chunk:

```python
import hashlib

def generate_chunk_id(doc_path: str, content: str) -> str:
    """Sinh ID duy nhất dựa trên nội dung băm SHA256."""
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    return f"{doc_path}#{content_hash}"

# Upsert vào ChromaDB: nếu ID đã tồn tại thì cập nhật, chưa có thì thêm mới
vector_store.upsert(
    ids=[chunk_id],
    documents=[chunk_text],
    metadatas=[chunk_metadata]
)
```

---

## 4. Retrieval, Hybrid Search và Reranking (Phần 4)

### 4.1. Tại sao Dense Search (Vector thuần) Thất Bại?
* **Thực nghiệm (Ca thất bại CLO G3.3):**
  * Câu hỏi tìm kiếm: *"Mã lỗi trả về khi token hết hạn là gì?"*
  * Vector Search trả về: Các đoạn thảo luận chung về token expiration nhưng không chứa mã lỗi `AUTH_TOKEN_EXPIRED`.
  * Lý do: Embedding gom theo ngữ nghĩa chung, bỏ qua sự khác biệt của từ khóa chính xác.

### 4.2. Kiến trúc Hybrid Search (Dense + Sparse)
Kết hợp sức mạnh của 2 phương pháp:
* **Dense Retrieval (Vector Embedding):** Bắt ngữ nghĩa, từ đồng nghĩa, khái niệm trừu tượng.
* **Sparse Retrieval (BM25 / Keyword Search):** Bắt chính xác tên biến, tên hàm, mã lỗi, UUID, commit hash.

```
                  ┌──► Dense Search (Vector / Cosine)  ──► List 1 (Rank) ──┐
User Query ───────┤                                                        ├──► Reciprocal Rank Fusion (RRF) ──► Top Candidates
                  └──► Sparse Search (BM25 / Keywords) ──► List 2 (Rank) ──┘
```

### 4.3. Thuật toán Hợp nhất Thứ hạng: Reciprocal Rank Fusion (RRF)
* **Vấn đề:** Không thể cộng trực tiếp điểm số Vector (ví dụ cosine: 0.82) với điểm BM25 (ví dụ: 14.5) vì khác phân phối thang đo.
* **Công thức RRF:** Sử dụng **thứ hạng (rank)** thay vì điểm thô:
  $$\text{RRF\_Score}(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
  * Trong đó: $r_m(d)$ là thứ hạng của tài liệu $d$ trong danh sách $m$.
  * Hằng số tiêu chuẩn: $k = 60$ (đã được chứng minh tối ưu theo công trình của Cormack et al. để tránh một bên áp đảo).

```python
def reciprocal_rank_fusion(dense_ranks: list[str], sparse_ranks: list[str], k: int = 60) -> list[tuple[str, float]]:
    """Hợp nhất 2 danh sách tài liệu theo thuật toán RRF k=60."""
    scores = {}
    
    for rank, doc_id in enumerate(dense_ranks, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        
    for rank, doc_id in enumerate(sparse_ranks, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        
    sorted_docs = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return sorted_docs
```

### 4.4. Cross-Encoder Reranking
* **Bi-Encoder (Vector search):** Mã hóa Query và Chunk riêng rẽ $\rightarrow$ Rất nhanh nhưng mất tương tác từ vựng chi tiết.
* **Cross-Encoder (Reranker):** Đưa `[Query, Chunk]` cùng lúc vào model Transformer để chú ý chéo (cross-attention) từng từ.
  * Model phổ biến: `BAAI/bge-reranker-large` hoặc `ms-marco-MiniLM-L-6-v2`.
  * Độ chính xác cực cao, dùng để tinh lọc Top 50 ứng viên xuống Top 5 chunk chất lượng nhất cho LLM.

### 4.5. Kiến trúc Thác Truy Xuất (Retrieval Cascade)
1. **Tầng 1 (Lọc rộng):** Hybrid Search (BM25 + Vector) lấy Top 50–100 chunks ($\sim 10-20\text{ms}$).
2. **Tầng 2 (Lọc metadata):** Lọc theo `repo`, `version`, `status == 'active'` ($\sim 1\text{ms}$).
3. **Tầng 3 (Sắp xếp sâu):** Cross-Encoder Reranker chấm điểm lại Top 50 ➔ Chọn Top 3–5 chunks ($\sim 50\text{ms}$).
4. **Tầng 4 (Prompt):** Dán Top 3–5 chunks vào context window cho LLM sinh câu trả lời.

---

## 5. Grounding, Citation và Đánh Giá RAG (Phần 5)

### 5.1. Khái niệm Grounding & Năm Quy Tắc Prompt Bám Nguồn
* **Grounding:** Sự neo chặt của câu trả lời vào đúng các dữ kiện có trong ngữ cảnh truy xuất.
* **Năm quy tắc thiết kế Prompt bám nguồn:**
  1. *Quy tắc phạm vi:* Chỉ được dùng thông tin từ tài liệu đính kèm, không dùng kiến thức nền phỏng đoán.
  2. *Quy tắc trích dẫn:* Mọi phát biểu thực tế phải kèm mã nguồn `[S1]`, `[S2]`.
  3. *Quy tắc trung thực (Abstention):* Nếu tài liệu không chứa đủ dữ kiện để trả lời, phải nói rõ: *"Tài liệu hiện tại không đề cập đến thông tin này"* (không được bịa câu trả lời).
  4. *Quy tắc phân biệt:* Khi có 2 tài liệu mâu thuẫn nhau, trích dẫn cả hai và ghi chú phiên bản.
  5. *Quy tắc bảo toàn code:* Giữ nguyên định danh code, không tự ý sửa tên hàm khi trích dẫn.

### 5.2. Cơ chế Citation & Kiểm chứng Tự động
* Mỗi chunk đưa vào prompt được gán nhãn định danh: `[S1]`, `[S2]`,...
* **Citation Verification Harness:** Một validator chạy sau khi LLM sinh output để kiểm tra:
  * Mã trích dẫn `[Sx]` có nằm trong danh sách chunk đã đưa vào prompt không?
  * Nếu xuất hiện `[S3]` mà prompt chỉ có `S1`, `S2` $\rightarrow$ **Cảnh báo Hallucination** và loại bỏ comment.

### 5.3. Bốn Failure Modes Của Retrieval
| Mode | Hiện tượng | Đo bằng | Cách khắc phục |
| :--- | :--- | :--- | :--- |
| **01. Miss** | Chunk chứa đáp án đúng không lọt vào Top-k | Recall@k | Thêm BM25, tăng k, dùng Contextual Retrieval |
| **02. Wrong Chunk** | Top-k toàn rác hoặc chunk gây nhiễu | Precision@k | Lọc Metadata nghiêm ngặt, dùng Parent-Child chunking |
| **03. Nguồn mâu thuẫn** | Cả bản cũ và bản mới cùng lọt vào Top-k | Bộ test version | Upsert idempotent, lọc theo `status: active` |
| **04. Ảo giác dù có nguồn** | Đúng chunk nhưng model vẫn suy diễn sai | Faithfulness | Prompt escape hatch, kiểm tra Entailment NLI |

> [!WARNING]
> **Nghiên cứu của Google (ICLR 2025 - Joren et al.):**
> Khi **không có ngữ cảnh**, tỷ lệ trả lời sai là **10.2%**.
> Khi có **ngữ cảnh nửa vời / không đủ**, tỷ lệ trả lời sai vọt lên **66.1%** (tăng gấp 6.5 lần)!
> *Kết luận:* Ngữ cảnh không đủ nguy hiểm hơn nhiều so với không có ngữ cảnh. Agent phải có khả năng chủ động từ chối (Abstention).

### 5.4. Thiết Kế Golden Eval Dataset (20–30 Cases)
Bộ dữ liệu chuẩn để đo lường RAG gồm 3 nhóm câu hỏi:
* **1/3 Khái niệm:** Câu hỏi lý thuyết, nguyên lý chung.
* **1/3 Định danh:** Tên mã lỗi, đoạn code cụ thể, endpoint API chính xác.
* **1/3 Câu bẫy / Phủ định:** Hỏi về phiên bản cũ, tính năng đã bị deprecated.
* **BẮT BUỘC có 3–5 câu KHÔNG CÓ ĐÁP ÁN trong kho tri thức:** Để đo lường tỷ lệ dám từ chối (**Abstention Rate**).

### 5.5. Bộ Chỉ số Đánh giá RAG Hoàn chỉnh

#### Nhóm 1: Đánh giá Bước Tìm Tài Liệu (Retrieval Step)
* **Recall@k:** Tỷ lệ câu hỏi mà chunk đúng xuất hiện trong Top-k kết quả (Mục tiêu đồ án $\ge 80\%$).
* **Precision@k:** Tỷ lệ chunk hữu ích trên tổng số chunk lấy về trong Top-k.
* **MRR (Mean Reciprocal Rank):** Vị trí nghịch đảo của chunk đúng đầu tiên ($1/\text{rank}$).

#### Nhóm 2: Đánh giá Chất lượng Câu Trả Lời (Generation Step)
* **Faithfulness (Độ trung thực):** Tỷ lệ mệnh đề trong câu trả lời được chứng thực trực tiếp từ context (đo tự động qua RAGAS framework):
  $$\text{Faithfulness} = \frac{\text{Số mệnh đề được context chứng thực}}{\text{Tổng số mệnh đề trong câu trả lời}}$$
* **Citation Existence (Tính hợp lệ của nguồn):** $100\%$ mã trích dẫn phải tồn tại trong ngữ cảnh được cung cấp.
* **Abstention Rate (Tỷ lệ từ chối đúng):** Tỷ lệ từ chối trả lời chính xác khi gặp câu hỏi không có dữ liệu.

### 5.6. Bảng So sánh 4 Cấu hình Thực nghiệm
Để đạt điểm tối đa tiêu chí **U3 (Kiểm chứng)**, đồ án cần đo đạc và lập bảng so sánh ít nhất 2 cấu hình:

| Cấu hình thử nghiệm | Recall@5 | Recall@20 | Faithfulness | Citation Acc | Abstention | Latency P50 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Baseline:** Vector thuần, chunk 500 fixed | $62\%$ | $74\%$ | $0.71$ | $88\%$ | $40\%$ | $180\text{ms}$ |
| **B. Structured:** Syntax Chunking + Metadata | $75\%$ | $86\%$ | $0.84$ | $96\%$ | $70\%$ | $195\text{ms}$ |
| **C. Hybrid:** B + BM25 + RRF ($k=60$) | $88\%$ | $95\%$ | $0.91$ | $100\%$ | $85\%$ | $240\text{ms}$ |
| **D. Cascade:** C + Cross-Encoder Reranker | **$94\%$** | **$98\%$** | **$0.96$** | **$100\%$** | **$95\%$** | $320\text{ms}$ |

---

## 6. Hướng Dẫn Ứng Dụng Vào Đề Tài Code Review Agent (SE373)

### Áp dụng vào Use Case UC-02 (Review theo quy ước & checklist - K3)
1. **Kho tri thức nạp vào Vector DB:**
   * `knowledge/CONVENTIONS.md` (Tối thiểu 20 quy tắc mã nguồn, mỗi quy tắc có ID: `CONV-001`, `CONV-002`,...).
   * `knowledge/REVIEW_CHECKLIST.md` (Tối thiểu 15 mục checklist theo các nhóm: Security, Performance, Logic, Testing).
2. **Metadata gắn kèm mỗi chunk quy ước:**
   * `rule_id`: ví dụ `CONV-012`
   * `category`: `security`, `performance`, `naming`, `logging`
   * `scope`: `python`, `typescript`, `backend`, `tests/`
3. **Đóng gói thành Tool cho Agent (`search_conventions`):**
   * Cho phép reviewer agent tra cứu quy tắc phù hợp với file/hunk đang review.
   * Lọc metadata: quy tắc chỉ áp dụng cho `app/api/` sẽ không bị áp sai lên `tests/`.
4. **Trích dẫn bắt buộc trong Finding:**
   * Mọi comment inline thuộc loại `convention` đều phải ghi rõ: `Vi phạm quy tắc CONV-012: [Tên quy tắc] tại [file:dòng]`.
   * Validator harness kiểm tra: nếu mã quy tắc không tồn tại trong DB, loại bỏ finding ngay lập tức.
