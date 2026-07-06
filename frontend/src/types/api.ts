export interface Document {
  document_id: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  status: string;
  chunk_count?: number;
}

export interface DocumentUploadRequest {
  filename: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  query: string;
  conversation_id?: string;
  context?: Record<string, unknown>;
}

export interface ChatResponse {
  message: ChatMessage;
  conversation_id: string;
  retrieved_chunks?: Array<{
    chunk_id: string;
    document_id: string;
    content: string;
    similarity_score: number;
    rank: number;
    source_filename?: string;
  }>;
  citations?: Array<{
    doc_index: number;
    chunk_id: string;
    document_id: string;
    confidence: number;
  }>;
}

export interface RetrievalResult {
  chunk_id: string;
  document_id: string;
  content: string;
  similarity_score: number;
  rank: number;
  source_filename?: string;
  metadata?: Record<string, unknown>;
}

export interface RetrievalRequest {
  query: string;
  top_k?: number;
  threshold?: number;
  filters?: Record<string, unknown>;
  strategy?: string;
}

export interface RetrievalResponse {
  results: RetrievalResult[];
  total_found: number;
  processing_time_ms: number;
  strategy?: string;
}

export interface RetrievalInspectResponse {
  query: string;
  candidates: Array<RetrievalResult & {
    dense_score?: number;
    bm25_score?: number;
    rrf_score?: number;
    rerank_score?: number;
    final_score?: number;
  }>;
  fusion_method?: string;
  reranker_used?: boolean;
}

export interface EvaluationResult {
  evaluation_type: string;
  score: number;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface EvaluationRequest {
  dataset_id?: string;
  dataset?: Array<Record<string, unknown>>;
  evaluation_types?: string[];
  metrics?: Record<string, unknown>;
}

export interface EvaluationResponse {
  evaluation_id: string;
  results: EvaluationResult[];
  overall_score: number;
  total_items: number;
  execution_time_ms: number;
}

export interface ExperimentResult {
  experiment_id: string;
  configuration: Record<string, unknown>;
  results: Array<Record<string, unknown>>;
  metrics: Record<string, number>;
  timestamp: string;
}

export interface ExperimentRequest {
  name: string;
  description?: string;
  configuration: Record<string, unknown>;
  dataset_id?: string;
}

export interface ExperimentResponse {
  experiment_id: string;
  name: string;
  status: string;
  created_at: string;
}

export interface SettingsResponse {
  llm_provider: Record<string, unknown>;
  embedding_model: Record<string, unknown>;
  retrieval_strategy: Record<string, unknown>;
  top_k: number;
  temperature: number;
  prompt_version: string;
}

export type Theme = 'light' | 'dark' | 'system';
