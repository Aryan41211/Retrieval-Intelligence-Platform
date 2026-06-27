# Generation Lifecycle

## Purpose

Generation produces grounded answers from retrieved context using LLMs, including citation extraction, streaming support, and answer verification.

## Sequence Diagram

```
sequenceDiagram
    participant API as Query API
    participant Gen as Generator
    participant Prompt as PromptBuilder
    participant LLM as LLMProvider
    participant Extractor as CitationExtractor
    participant Verifier as GroundingVerifier
    participant Resp as ResponseFormatter
    
    API->>Gen: generate(query, context)
    
    Gen->>Prompt: build_prompt(query, context)
    Prompt-->>Gen: formatted_prompt
    
    Gen->>LLM: call_api(formatted_prompt)
    
    alt Streaming Enabled
        LLM-->>Gen: yield tokens
        Gen->>Resp: format_stream(tokens)
        Resp-->>API: stream_response
    else Sync
        LLM-->>Gen: full_answer
        
        Gen->>Extractor: extract_citations(answer)
        Extractor-->>Gen: citations
        
        Gen->>Verifier: verify(answer, context)
        Verifier-->>Gen: grounding_score
        
        Gen->>Resp: format_response(answer, citations, metadata)
        Resp-->>API: GenerationResult
    end
```

## Flowchart

```
flowchart TD
    A[Query + Context] --> B{Streaming?}
    B -->|Yes| C[Build Prompt]
    B -->|No| C
    
    C --> D[Call LLM API]
    
    D --> E{Streaming?}
    E -->|Yes| F[Yield Tokens]
    E -->|No| G[Full Answer]
    
    G --> H[Extract Citations]
    H --> I{Verify Grounding?}
    I -->|Yes| J[Check Claims vs Context]
    I -->|No| K[Skip Verification]
    
    J --> L[Return GenerationResult]
    K --> L
    F --> L
    
    L --> M[Format Response]
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `query` | `str` | Original user query |
| `context` | `RetrievalResult[]` | Ranked chunks with scores |
| `config.model` | `str` | LLM model identifier |
| `config.max_context_tokens` | `int` | Context window limit |
| `config.temperature` | `float` | Sampling temperature |
| `config.citation_enabled` | `bool` | Extract citations |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `answer` | `str` | Generated answer text |
| `citations` | `Citation[]` | Source references |
| `metadata.prompt_tokens` | `int` | Tokens in prompt |
| `metadata.completion_tokens` | `int` | Tokens in answer |
| `metadata.latency_ms` | `int` | Generation time |
| `metadata.groundedness_score` | `float` | 0-1 verification score |

## Prompt Building

### System Prompt Template
```
You are a helpful assistant that answers questions using only the provided context.
Always cite your sources using [doc_N] format.
Do not use prior knowledge. If unsure, say "I don't know."
```

### Context Formatting
```
[doc_1]: Extracted chunk content...
[doc_2]: Another chunk...
...
```

### Few-Shot Examples
```
Q: What is the capital of France?
Context: [doc_1]: France is a country in Europe. The capital is Paris.
A: The capital of France is Paris [doc_1].
```

## Citation Extraction

### Format Detection
```python
# Pattern: [doc_1], [doc_2], [doc_1, doc_2]
pattern = r'\[doc_(\d+)(?:,\s*\d+)*\]'
matches = re.findall(pattern, answer)
```

### Confidence Scoring
- Citations near sentence boundaries: high confidence
- Citations in middle of sentence: medium confidence
- Missing citations for claims: low confidence

## Verification

### Claim Extraction
- Split answer into factual statements
- Identify entity references
- Map to context

### Support Checking
- Check if claim exists in context
- Semantic equivalence (embed both)
- Return groundedness score

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| Context exceeds limit | `GenerationError` | Truncate lowest-ranked chunks |
| LLM timeout | `LLMError` | Return partial, mark incomplete |
| Citation parsing fails | `CitationError` | Return answer without citations |
| Safety filter trigger | `GenerationError` | Return refusal, use fallback prompt |
| Rate limit exceeded | `LLMError` | Backoff, retry, circuit breaker |
| Model unavailable | `LLMError` | Fallback model, log alert |

## Recovery Strategy

### Context Truncation
```python
# Keep highest-ranked chunks until context fits
while total_tokens > max_context:
    remove lowest_ranked_chunk
```

### Fallback Model
```python
# Primary: gpt-4o
# Fallback: gpt-4o-mini
if primary_fails:
    retry_with_fallback_model()
```

### Streaming Partial Results
```python
# On timeout, return whatever we have
# Mark completion_tokens as incomplete
# Client receives via SSE
```

## Performance Considerations

| Provider | Latency | Throughput | Quality |
|----------|---------|------------|---------|
| OpenAI | Low | High | High |
| Anthropic | Low | High | High |
| Ollama | Med | Med | Med |
| vLLM | Low | High | High |
| TGI | Low | High | High |

### Token Management
- Pre-truncate context to fit window
- Reserve tokens for answer generation
- Use tiktoken for accurate counting

### Temperature Tuning
- 0.0-0.3: Factual queries (revenue, dates)
- 0.5-0.7: Creative tasks (summaries, analysis)
- Low temperature = more consistent citations

## Future Scalability

### Multi-LLM Generation
- Query multiple models in parallel
- Select best answer via scoring
- Consensus-based grounding

### Structured Output
```python
class StructuredAnswer(BaseModel):
    answer: str
    key_points: list[str]
    citations: list[Citation]
    confidence: float
```

### Progressive Citations
- Stream answer + citations together
- Real-time grounding score updates