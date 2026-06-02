# Enterprise GraphRAG Architecture

Design a microservices-based enterprise knowledge retrieval system that supports PDF, XLSX, and PPTX, while minimizing LLM hallucinations.

## 🏗️ System Architecture

```mermaid
graph TD
    %% 1. Ingestion Pipeline (Dotted/Dashed flows)
    subgraph Ingestion_Pipeline ["1. Data Ingestion Pipeline (Offline)"]
        Docs[Raw Documents: PDF, XLSX, PPTX] --> LP(LlamaParse / Markdown OCR)
        LP -->|Clean Markdown| SC(Semantic Chunking)
        SC -->|Dense & Sparse Embeddings| Q_Ingest[Embeddings Ingest]
        SC -->|Entity & Relationship Extraction| N_Ingest[Triplets Ingest]
    end

    %% 2. Retrieval & Generation Pipeline (Online)
    subgraph Query_Pipeline ["2. Retrieval & Generation Pipeline (Online)"]
        User[User Query] --> IG[Input Guardrails: NeMo / Llama Guard]
        IG --> B(Query Rewriter - LLM)
        B --> QR{Query Router}
        
        %% Routing
        QR -->|Simple / Hybrid| H_Search[Qdrant Hybrid Search]
        QR -->|Complex / Relation| H_Search
        QR -->|Complex / Relation| EE[Entity Extractor & Cypher Gen]
        
        %% Database Retrieval with RBAC
        H_Search -->|Dense Search + RBAC Payload| D1[(Qdrant Vector DB)]
        H_Search -->|Sparse Search + RBAC Payload| D2[(Qdrant BM25)]
        EE --> E[(Neo4j Graph DB)]
        
        %% Merge & Rerank
        D1 --> F[Merge Results - RRF]
        D2 --> F
        E -->|Convert Triplets to Text| F
        
        F --> G[Top 20 Contexts]
        G --> H(Cohere Rerank)
        H --> I[Top 5 Best Contexts]
        I --> J(Generator - LLM)
        
        %% Output Guardrails
        J --> OG[Output Guardrails: Hallucination Check]
        OG --> Answer[Final Answer]
    end

    %% 3. Continuous Evaluation
    subgraph Eval_System ["3. Continuous Evaluation"]
        Answer -.-> EV((Ragas / TruLens Eval))
        J -.-> EV
        I -.-> EV
        User -.-> EV
    end

    %% Connect Ingestion to DBs
    Q_Ingest --> D1
    Q_Ingest --> D2
    N_Ingest --> E

    %% CSS Styling
    classDef db fill:#f9f,stroke:#333,stroke-width:2px;
    classDef llm fill:#bbf,stroke:#333,stroke-width:2px;
    classDef guard fill:#ffcccb,stroke:#333,stroke-width:2px;
    classDef eval fill:#e0f7fa,stroke:#333,stroke-width:2px;
    classDef ingest fill:#fff9c4,stroke:#333,stroke-dasharray: 5 5;
    
    class D1,D2,E db;
    class B,QR,EE,H,J,LP,SC llm;
    class IG,OG guard;
    class EV eval;
    class Docs,Q_Ingest,N_Ingest ingest;
```

## 🔑 Pain Points Solved

*   **Strict Security (RBAC):** Prior to Vector search, Qdrant payload filters are applied matching the user's corporate group claims (JWT/AD), securing sensitive files.
*   **Complex PDF Parsing:** Heavy tables and unstructured documents are extracted as Markdown via LlamaParse, preventing broken structures.
*   **Hybrid Graph-Vector Search:** Combines unstructured semantic search (Qdrant) with structured relation paths (Neo4j Graph DB) combined via Reciprocal Rank Fusion (RRF).
*   **Cost & Latency Routing:** An intelligent router sends simple tasks exclusively to the Qdrant hybrid search path, bypassing expensive Graph querying.
*   **Dual Guardrails:** Filters unsafe prompts (Input Guardrails) and screens generated output for hallucinations (Output Guardrails).
*   **Continuous QA Loop:** Evaluates the pipeline automatically using Ragas/TruLens based on context precision and answer relevance.
