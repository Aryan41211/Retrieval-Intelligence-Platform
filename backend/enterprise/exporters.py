"""
Conversation export to JSON, Markdown and PDF.

PDF export is implemented with a small, dependency-free PDF writer so no extra
system libraries are required.
"""

import json
from typing import Any

from backend.enterprise.models import Conversation, Message

_CONTENT_TYPES = {
    "json": "application/json",
    "markdown": "text/markdown",
    "pdf": "application/pdf",
}


def _to_dict(conversation: Conversation, messages: list[Message]) -> dict[str, Any]:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "workspace_id": conversation.workspace_id,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


def _to_markdown(conversation: Conversation, messages: list[Message]) -> str:
    lines = [f"# {conversation.title}", ""]
    for m in messages:
        ts = m.created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(f"**{m.role.title()}** ({ts}):")
        lines.append(m.content)
        lines.append("")
    return "\n".join(lines)


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _render_pdf(lines: list[str]) -> bytes:
    """Render a minimal multi-page PDF from plain text lines."""
    page_height = 60
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= page_height:
            pages.append(current)
            current = []
    if current:
        pages.append(current)
    if not pages:
        pages.append([""])

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font_id = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []
    for page_lines in pages:
        stream = "\n".join(
            "BT /F1 11 Tf 50 760 Td 14 TL"
            + "".join(f" ({_escape_pdf_text(ln)}) Tj T*" for ln in page_lines)
            + " ET"
        ).encode("latin-1", "replace")
        cid = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_ids.append(cid)
    for cid in content_ids:
        pid = add(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (font_id, cid)
        )
        page_ids.append(pid)
    pages_obj = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (
        b" ".join(b"%d 0 R" % pid for pid in page_ids),
        len(page_ids),
    )
    pages_id = add(pages_obj)
    catalog_id = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)

    # Fix page Parent references to the real pages object id.
    objects = [
        b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
        % (pages_id, font_id, cid)
        if obj.startswith(b"<< /Type /Page /Parent 2 0 R")
        else obj
        for obj, cid in zip(objects, content_ids, strict=False)
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1,
        catalog_id,
        xref_pos,
    )
    return bytes(out)


def export_conversation(
    conversation: Conversation, messages: list[Message], fmt: str
) -> tuple[bytes, str, str]:
    """Export a conversation in the requested format.

    Returns:
        Tuple of (content bytes, media type, filename).
    """
    fmt = (fmt or "json").lower()
    if fmt not in _CONTENT_TYPES:
        raise ValueError(f"Unsupported export format: {fmt}")
    if fmt == "json":
        content = json.dumps(_to_dict(conversation, messages), indent=2).encode("utf-8")
    elif fmt == "markdown":
        content = _to_markdown(conversation, messages).encode("utf-8")
    else:
        lines = [conversation.title, ""]
        for m in messages:
            lines.append(f"{m.role.title()}: {m.content}")
            lines.append("")
        content = _render_pdf(lines)
    safe_title = (conversation.title or "conversation").replace(" ", "_")
    filename = f"{safe_title}.{fmt}"
    return content, _CONTENT_TYPES[fmt], filename
