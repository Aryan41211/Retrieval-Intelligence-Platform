"""Text preprocessing utilities for document cleaning."""

import re

from backend.data.models.document import Document


class TextCleaner:
    """Clean and normalize document text content."""

    def __init__(
        self,
        normalize_unicode: bool = True,
        normalize_whitespace: bool = True,
        remove_excessive_blanks: bool = True,
        max_consecutive_blanks: int = 2,
    ):
        self.normalize_unicode = normalize_unicode
        self.normalize_whitespace = normalize_whitespace
        self.remove_excessive_blanks = remove_excessive_blanks
        self.max_consecutive_blanks = max_consecutive_blanks

    def clean(self, document: Document) -> Document:
        """Clean document text content.

        Args:
            document: Document to clean.

        Returns:
            Document with cleaned content (new instance).
        """
        content = document.content

        if self.normalize_unicode:
            content = self._normalize_unicode(content)

        if self.normalize_whitespace:
            content = self._normalize_whitespace(content)

        if self.remove_excessive_blanks:
            content = self._remove_excessive_blank_lines(content)

        # Update metadata
        metadata = document.metadata
        metadata.char_count = len(content)
        metadata.word_count = len(content.split())

        return document.model_copy(update={"content": content, "metadata": metadata})

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters.

        Args:
            text: Input text.

        Returns:
            Normalized text.
        """
        import unicodedata

        text = unicodedata.normalize("NFC", text)

        # Replace smart quotes with regular quotes
        replacements = {
            "\u2018": "'",  # Left single quote
            "\u2019": "'",  # Right single quote
            "\u201c": '"',  # Left double quote
            "\u201d": '"',  # Right double quote
            "\u2013": "-",  # En dash
            "\u2014": "--",  # Em dash
            "\u2022": "*",  # Bullet
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Remove control characters except newlines and tabs
        text = "".join(char for char in text if char.isprintable() or char in "\n\t")

        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text.

        Args:
            text: Input text.

        Returns:
            Normalized text.
        """
        # Normalize line endings to \n
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse multiple spaces to single space (but preserve newlines)
        lines = text.split("\n")
        normalized_lines = []
        for line in lines:
            # Collapse spaces/tabs in each line
            normalized = re.sub(r"[ \t]+", " ", line.strip())
            normalized_lines.append(normalized)

        text = "\n".join(normalized_lines)

        return text

    def _remove_excessive_blank_lines(self, text: str) -> str:
        """Remove excessive consecutive blank lines.

        Args:
            text: Input text.

        Returns:
            Text with limited blank lines.
        """
        # Count consecutive newlines
        lines = text.split("\n")
        result_lines = []
        blank_count = 0

        for line in lines:
            if line.strip() == "":
                blank_count += 1
                if blank_count <= self.max_consecutive_blanks:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        return "\n".join(result_lines).strip()


def clean_document(
    document: Document,
    normalize_unicode: bool = True,
    normalize_whitespace: bool = True,
    remove_excessive_blanks: bool = True,
    max_consecutive_blanks: int = 2,
) -> Document:
    """Convenience function to clean a document.

    Args:
        document: Document to clean.
        normalize_unicode: Whether to normalize unicode.
        normalize_whitespace: Whether to normalize whitespace.
        remove_excessive_blanks: Whether to limit blank lines.
        max_consecutive_blanks: Maximum consecutive blank lines.

    Returns:
        Cleaned document.
    """
    cleaner = TextCleaner(
        normalize_unicode=normalize_unicode,
        normalize_whitespace=normalize_whitespace,
        remove_excessive_blanks=remove_excessive_blanks,
        max_consecutive_blanks=max_consecutive_blanks,
    )
    return cleaner.clean(document)
