"""Unit tests for citation extraction from generated answers."""

from backend.generation.models import ContextItem
from backend.generation.pipeline_components.citation_generator import CitationGenerator


def _ctx(n: int) -> list[ContextItem]:
    return [
        ContextItem(
            chunk_id=f"chunk-{i + 1}",
            document_id=f"doc-{i + 1}",
            chunk_text=f"chunk text {i + 1}",
            rank=i + 1,
            similarity_score=0.9 - i * 0.01,
        )
        for i in range(n)
    ]


def test_multiple_citations_are_sorted_numerically():
    """[doc_10] must resolve to the tenth context chunk, not the second.

    A lexicographic sort maps "1","10","2"; the positional mapping that
    followed attached every multi-digit marker to the wrong chunk.
    """
    context = _ctx(12)
    answer = "Claim one [doc_1]. Claim two [doc_2]. Claim ten [doc_10]."
    gen = CitationGenerator()
    citations = gen.generate(answer=answer, context_items=context)

    assert [c.doc_index for c in citations] == [1, 2, 10]
    by_index = {c.doc_index: c for c in citations}
    assert by_index[10].chunk_id == "chunk-10"
    assert by_index[10].chunk_text == "chunk text 10"
    assert by_index[2].chunk_id == "chunk-2"


def test_no_context_yields_no_citations():
    gen = CitationGenerator()
    assert gen.generate(answer="Something [doc_1]", context_items=[]) == []


def test_no_markers_yields_no_citations():
    gen = CitationGenerator()
    assert gen.generate(answer="Nothing cited here.", context_items=_ctx(3)) == []


def test_out_of_range_marker_is_dropped():
    context = _ctx(3)
    gen = CitationGenerator()
    citations = gen.generate(answer="Small [doc_1] and [doc_99]", context_items=context)
    assert [c.doc_index for c in citations] == [1]


def test_out_of_order_markers_still_map_correctly():
    context = _ctx(5)
    gen = CitationGenerator()
    citations = gen.generate(answer="Backwards [doc_5] then [doc_1]", context_items=context)
    by_index = {c.doc_index: c for c in citations}
    assert by_index[5].chunk_id == "chunk-5"
    assert by_index[1].chunk_id == "chunk-1"
