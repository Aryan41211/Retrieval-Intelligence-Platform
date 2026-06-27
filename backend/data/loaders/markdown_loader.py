"""Markdown document loader."""

import re
from pathlib import Path
from typing import Optional

from backend.core.exceptions import (
    DocumentLoadError,
    EmptyDocumentError,
)
from backend.data.loaders.base_loader import BaseLoader
from backend.data.models.document import Document


class MarkdownLoader(BaseLoader):
    """Load Markdown documents."""

    def get_supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def load(self, file_path: str | Path) -> Document:
        """Load a Markdown document.

        Args:
            file_path: Path to the Markdown file.

        Returns:
            Document object with text content.

        Note:
            For markdown, we strip markdown formatting and return plain text
            to be consistent with other loaders. The original markdown is
            available in the source if needed.
        """
        path = self.validate_file(file_path)
        checksum = self.compute_checksum(path)
        file_extension = path.suffix.lower()

        encoding = self.detect_encoding(path)

        try:
            with open(path, encoding=encoding) as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            for fallback in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(path, encoding=fallback) as f:
                        raw_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise DocumentLoadError(f"Could not decode file with any encoding: {path}") from None

        if not raw_content.strip():
            raise EmptyDocumentError(f"File is empty: {path}")

        # Try to strip markdown formatting to get plain text
        try:
            import html
            import markdown  # markdown package

            # Convert to html then strip tags
            html_content = markdown.markdown(raw_content)
            content = self._strip_html_tags(html_content, html)
        except ImportError:
            # If markdown not installed, use raw content
            content = raw_content

        # Extract title from first heading if available
        title = self._extract_title(raw_content)

        metadata = self.build_metadata(
            title=title,
            char_count=len(content),
            word_count=len(content.split()),
        )

        source = self.build_source(path, checksum)

        return Document(
            filename=path.name,
            file_extension=file_extension,
            source_path=str(path),
            content=content,
            metadata=metadata,
            checksum=checksum,
            file_size=path.stat().st_size,
            source=source,
        )

    def _strip_html_tags(self, html_content: str, html_module) -> str:
        """Strip HTML tags to get plain text.

        Args:
            html_content: HTML content string.
            html_module: The html module for unescape.

        Returns:
            Plain text without HTML tags.
        """
        # Remove script and style elements
        text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

        # Replace block elements with newlines
        for tag in ["<p>", "</p>", "<div>", "</div>", "<br>", "<br/>", "<h1>", "</h1>", "<h2>", "</h2>", "<h3>", "</h3>"]:
            text = text.replace(tag, "\n")

        # Remove all remaining tags
        text = re.sub(r"<[^>]+>", "", text)

        # Decode HTML entities
        text = html_module.unescape(text)

        # Clean up whitespace
        lines = [line.strip() for line in text.split("\n")]
        return "\n".join(line for line in lines if line)

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract title from markdown content.

        Args:
            content: Markdown content.

        Returns:
            Title string or None.
        """
        # Match first ATX-style heading (# Title)
        match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()

        # Match first setext-style heading
        match = re.match(r"^( .{1,})\n=+\n", content)
        if match:
            return match.group(1).strip()

        return None