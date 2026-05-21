-- Run in Supabase SQL Editor to speed up semantic vault / RAG search.
-- Fixes match_documents timeouts reported in health audit.

-- 1) Ensure pgvector extension
create extension if not exists vector;

-- 2) Index on documents.embedding (cosine distance)
-- Adjust lists for IVFFlat after you have enough rows (rule of thumb: sqrt(row_count))
drop index if exists documents_embedding_ivfflat_idx;
create index documents_embedding_ivfflat_idx
  on documents
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- 3) Optional: raise timeout for match function only (if you wrap RPC in a function)
-- alter database postgres set statement_timeout = '30s';

-- 4) Analyze for planner
analyze documents;
