"""Offline RAG evaluation metrics for Retrieval Intelligence Platform.

Implements RAG evaluation metrics WITHOUT requiring external LLM API keys:
- Faithfulness: Is the answer supported by the retrieved context?
- Answer Relevancy: Does the answer address the question?
- Context Precision: Is the retrieved context relevant to the question?
- Context Recall: Is all needed information present in the context?
- Citation Precision: Are citations backed by actual retrieved context?
- Citation Coverage: Are all factual claims in the answer cited?
- Unsupported Claim Rate: What fraction of claims lack context support?

All metrics use local computation only (sentence-transformers embeddings +
heuristic overlap). No external API calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer, util


@dataclass
# ... shared types ...
class OfflineEvalSample:
    """A single offline evaluation sample."""

    query_id: str
    question: str
    ground_truth: str
    answer: str
    contexts: list[str]
    citations: list[dict[str, Any]] = field(default_factory=list)
    label_source: str = "human-validated"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OfflineEvalResult:
    """Result for a single evaluation sample."""

    query_id: str
    question: str
    metrics: dict[str, float] = field(default_factory=dict)
    error: str | None = None


@dataclass
class OfflineEvalReport:
    """Aggregate offline evaluation report."""

    total_samples: int = 0
    successful_evaluations: int = 0
    failed_evaluations: int = 0
    metrics: dict[str, float] = field(default_factory=dict)
    per_sample: list[OfflineEvalResult] = field(default_factory=list)
    latency_ms: float = 0.0


# Lazy-loaded embedding model for semantic similarity
_EMBED_MODEL: SentenceTransformer | None = None
_EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _get_embed_model() -> SentenceTransformer:
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer(_EMBED_MODEL_NAME)
    return _EMBED_MODEL


def _tokenize(text: str) -> set[str]:
    """Simple word tokenizer: lowercase, alphanumeric only."""
    return set(re.findall(r"\b[a-z0-9]+\b", text.lower()))


def _word_overlap(a: str, b: str) -> float:
    """Jaccard overlap of word sets between two texts."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _semantic_similarity(a: str, b: str) -> float:
    """Cosine similarity between two texts using sentence embeddings."""
    model = _get_embed_model()
    emb_a = model.encode(a, convert_to_numpy=True, normalize_embeddings=True)
    emb_b = model.encode(b, convert_to_numpy=True, normalize_embeddings=True)
    return float(np.dot(emb_a, emb_b))


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def _extract_claims(text: str) -> list[str]:
    """Extract factual claims from text (simple sentence-level splitting)."""
    return _split_sentences(text)


def _claim_supported_by_context(claim: str, contexts: list[str], threshold: float = 0.5) -> bool:
    """Check if a claim is supported by any context chunk (semantic similarity)."""
    if not contexts:
        return False
    model = _get_embed_model()
    claim_emb = model.encode(claim, convert_to_numpy=True, normalize_embeddings=True)
    for ctx in contexts:
        ctx_emb = model.encode(ctx, convert_to_numpy=True, normalize_embeddings=True)
        sim = float(np.dot(claim_emb, ctx_emb))
        if sim >= threshold:
            return True
    return False


def compute_faithfulness(answer: str, contexts: list[str]) -> float:
    """
    Faithfulness: fraction of answer sentences supported by retrieved context.
    
    Each sentence in the answer is checked against all context chunks using
    semantic similarity. A sentence is "faithful" if it has >= 0.5 cosine
    similarity with at least one context chunk.
    
    Returns: fraction of supported sentences (0.0 to 1.0).
    """
    sentences = _split_sentences(answer)
    if not sentences:
        return 0.0
    supported = sum(1 for s in sentences if _claim_supported_by_context(s, contexts))
    return supported / len(sentences)


def compute_answer_relevancy(question: str, answer: str) -> float:
    """
    Answer Relevancy: semantic similarity between question and answer.
    
    Returns: cosine similarity (0.0 to 1.0).
    """
    return _semantic_similarity(question, answer)


def compute_context_precision(question: str, contexts: list[str]) -> float:
    """
    Context Precision: fraction of context chunks relevant to the question.
    
    A context chunk is "relevant" if it has >= 0.4 semantic similarity with
    the question.
    
    Returns: fraction of relevant chunks (0.0 to 1.0).
    """
    if not contexts:
        return 0.0
    relevant = sum(1 for c in contexts if _semantic_similarity(question, c) >= 0.4)
    return relevant / len(contexts)


def compute_context_recall(question: str, ground_truth: str, contexts: list[str]) -> float:
    """
    Context Recall: fraction of ground truth sentences covered by contexts.
    
    Each ground truth sentence is checked against all context chunks. A
    ground truth sentence is "covered" if it has >= 0.5 semantic similarity
    with at least one context chunk.
    
    Returns: fraction of covered sentences (0.0 to 1.0).
    """
    gt_sentences = _split_sentences(ground_truth)
    if not gt_sentences:
        return 0.0
    covered = sum(1 for s in gt_sentences if _claim_supported_by_context(s, contexts))
    return covered / len(gt_sentences)


def compute_citation_precision(citations: list[dict[str, Any]], contexts: list[str]) -> float:
    """
    Citation Precision: fraction of citations backed by actual context.
    
    A citation is "valid" if its chunk_text matches (semantic similarity >= 0.8)
    at least one context chunk.
    
    Returns: fraction of valid citations (0.0 to 1.0).
    """
    if not citations:
        return 0.0
    if not contexts:
        return 0.0
    valid = 0
    for citation in citations:
        chunk_text = citation.get("chunk_text", "")
        if not chunk_text:
            continue
        if _claim_supported_by_context(chunk_text, contexts, threshold=0.8):
            valid += 1
    return valid / len(citations)


def compute_citation_coverage(answer: str, citations: list[dict[str, Any]]) -> float:
    """
    Citation Coverage: fraction of answer sentences that have at least one citation.
    
    Simple heuristic: each answer sentence is checked for nearby citation
    markers (e.g., [1], [2], or citation indices).
    
    Returns: fraction of sentences with citation coverage (0.0 to 1.0).
    """
    if not citations:
        return 0.0
    sentences = _split_sentences(answer)
    if not sentences:
        return 0.0
    # Count citation markers in the answer
    citation_markers = set(re.findall(r"\[(\d+)\]", answer))
    cited_indices = {int(m) for m in citation_markers}
    available_citation_ids = {c.get("doc_index") for c in citations if c.get("doc_index") is not None}
    
    covered = 0
    for i, sentence in enumerate(sentences, start=1):
        if i in cited_indices or i in available_citation_ids:
            covered += 1
    return covered / len(sentences)


def compute_unsupported_claim_rate(answer: str, contexts: list[str]) -> float:
    """
    Unsupported Claim Rate: fraction of answer sentences NOT supported by context.
    
    Returns: 1.0 - faithfulness (0.0 to 1.0).
    """
    return 1.0 - compute_faithfulness(answer, contexts)


def evaluate_sample(sample: OfflineEvalSample) -> dict[str, float]:
    """Compute all offline metrics for a single sample."""
    metrics: dict[str, float] = {}

    metrics["faithfulness"] = round(compute_faithfulness(sample.answer, sample.contexts), 4)
    metrics["answer_relevancy"] = round(compute_answer_relevancy(sample.question, sample.answer), 4)
    metrics["context_precision"] = round(compute_context_precision(sample.question, sample.contexts), 4)
    metrics["context_recall"] = round(compute_context_recall(sample.question, sample.ground_truth, sample.contexts), 4)
    metrics["citation_precision"] = round(compute_citation_precision(sample.citations, sample.contexts), 4)
    metrics["citation_coverage"] = round(compute_citation_coverage(sample.answer, sample.citations), 4)
    metrics["unsupported_claim_rate"] = round(compute_unsupported_claim_rate(sample.answer, sample.contexts), 4)

    return metrics


def run_offline_evaluation(samples: list[OfflineEvalSample]) -> OfflineEvalReport:
    """Run offline RAG evaluation on a list of samples."""
    import time

    t0 = time.perf_counter()
    per_sample: list[OfflineEvalResult] = []
    successful = 0
    failed = 0

    for sample in samples:
        try:
            metrics = evaluate_sample(sample)
            per_sample.append(
                OfflineEvalResult(
                    query_id=sample.query_id,
                    question=sample.question,
                    metrics=metrics,
                )
            )
            successful += 1
        except Exception as exc:
            per_sample.append(
                OfflineEvalResult(
                    query_id=sample.query_id,
                    question=sample.question,
                    error=str(exc),
                )
            )
            failed += 1

    # Aggregate metrics: mean across successful samples.
    agg_metrics: dict[str, float] = {}
    if per_sample:
        metric_keys = set()
        for r in per_sample:
            if r.metrics:
                metric_keys.update(r.metrics.keys())
        for key in metric_keys:
            values = [r.metrics[key] for r in per_sample if r.metrics and key in r.metrics]
            if values:
                agg_metrics[key] = round(sum(values) / len(values), 4)

    return OfflineEvalReport(
        total_samples=len(samples),
        successful_evaluations=successful,
        failed_evaluations=failed,
        metrics=agg_metrics,
        per_sample=per_sample,
        latency_ms=int((time.perf_counter() - t0) * 1000),
    )
