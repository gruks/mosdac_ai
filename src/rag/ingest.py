"""Semantic code chunking for RAG pipelines using AST-based splitting."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from astchunk import ASTChunkBuilder


@dataclass
class CodeChunk:
    """Represents a semantic code chunk with metadata.

    Attributes:
        code: The code content of the chunk
        metadata: Dictionary containing chunk metadata (file_path, function_name, etc.)
        chunk_type: Type of chunk - 'function', 'class', or 'module'
        file_path: Path to the source file
    """

    code: str
    metadata: dict
    chunk_type: str
    file_path: str


def split_file(file_path: str, max_chunk_tokens: int = 800) -> List[CodeChunk]:
    """Split a Python source file into semantic chunks at function/class boundaries.

    Uses AST-based chunking via astchunk to preserve complete semantic units
    rather than arbitrary text splits.

    Args:
        file_path: Path to the Python source file
        max_chunk_tokens: Maximum tokens per chunk (converted to ~4 chars/token)

    Returns:
        List of CodeChunk objects with semantic boundaries preserved
    """
    # Convert token limit to approximate character limit
    max_chars = max_chunk_tokens * 4

    # Initialize AST-based chunk builder for Python
    chunk_builder = ASTChunkBuilder(
        max_chunk_size=max_chars, language="python", metadata_template="default"
    )

    # Read the source file
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    # Use astchunk to split at semantic boundaries
    raw_chunks = chunk_builder.chunkify(source_code)

    chunks = []
    file_path_obj = Path(file_path)

    for i, raw_chunk in enumerate(raw_chunks):
        # raw_chunk is a dict with 'content' and 'metadata' keys
        code_content = raw_chunk.get("content", "")
        chunk_meta = raw_chunk.get("metadata", {})

        # Determine chunk type from content analysis
        chunk_type = _determine_chunk_type(code_content)

        # Build metadata
        metadata = {
            "chunk_index": i,
            "function_name": _extract_function_name(code_content),
            "class_name": _extract_class_name(code_content),
            "line_start": chunk_meta.get("start_line_no", 1),
            "line_end": chunk_meta.get("end_line_no", 1),
            "source_file": str(file_path_obj),
            "node_count": chunk_meta.get("node_count", 0),
        }

        code_chunk = CodeChunk(
            code=code_content.strip(),
            metadata=metadata,
            chunk_type=chunk_type,
            file_path=str(file_path_obj),
        )
        chunks.append(code_chunk)

    return chunks


def split_directory(directory: str, extensions: list = [".py"]) -> List[CodeChunk]:
    """Recursively scan directory and split all matching files into chunks.

    Args:
        directory: Root directory to scan
        extensions: List of file extensions to process (default: [".py"])

    Returns:
        Flat list of all CodeChunk objects from all files
    """
    all_chunks = []
    dir_path = Path(directory)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    # Recursively find all matching files
    for ext in extensions:
        for file_path in dir_path.rglob(f"*{ext}"):
            try:
                chunks = split_file(str(file_path))
                all_chunks.extend(chunks)
            except Exception as e:
                # Skip files that can't be parsed (e.g., syntax errors)
                # In production, you might want to log these
                continue

    return all_chunks


def _determine_chunk_type(code: str) -> str:
    """Determine the chunk type based on its content."""
    code_stripped = code.strip()

    # Check for class definition
    if code_stripped.startswith("class "):
        return "class"

    # Check for function/method definition
    if "def " in code_stripped:
        return "function"

    # Default to module-level
    return "module"


def _extract_function_name(code: str) -> Optional[str]:
    """Extract function name from code if present."""
    import re

    # Match function definitions: def function_name(...)
    match = re.search(r"def\s+(\w+)\s*\(", code)
    if match:
        return match.group(1)
    return None


def _extract_class_name(code: str) -> Optional[str]:
    """Extract class name from code if present."""
    import re

    # Match class definitions: class ClassName(...)
    match = re.search(r"class\s+(\w+)\s*[:\(]", code)
    if match:
        return match.group(1)
    return None
