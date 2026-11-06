import re
from typing import List, Dict, Any

class MarkdownChunker:
    """
    Intelligent Markdown chunker for SRE runbooks and post-mortems.
    Splits by H1/H2/H3 headers so that each chunk preserves the operational context
    (e.g., Symptoms, Diagnostic Workflow, Remediation Steps).
    """

    def __init__(self, min_chunk_len: int = 80, max_chunk_len: int = 1500):
        self.min_chunk_len = min_chunk_len
        self.max_chunk_len = max_chunk_len

    def chunk_markdown(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        metadata = metadata or {}
        chunks = []
        
        # Split by markdown headers (# Header)
        header_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
        matches = list(header_pattern.finditer(text))

        if not matches:
            # Fallback: whole document or paragraph split
            return [{
                "title": metadata.get("title", "Runbook Document"),
                "content": text.strip(),
                "metadata": metadata
            }]

        doc_title = metadata.get("title") or matches[0].group(2).strip()

        for i, match in enumerate(matches):
            header_level = len(match.group(1))
            section_title = match.group(2).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            section_content = text[start_pos:end_pos].strip()
            
            # Combine header with content
            chunk_text = f"## {section_title}\n{section_content}".strip()
            
            if len(chunk_text) < self.min_chunk_len and i > 0 and chunks:
                # Merge short sections into previous chunk
                chunks[-1]["content"] += f"\n\n{chunk_text}"
                continue

            chunk_meta = {
                **metadata,
                "doc_title": doc_title,
                "section_title": section_title,
                "header_level": header_level,
            }

            chunks.append({
                "title": f"{doc_title} > {section_title}",
                "content": chunk_text,
                "metadata": chunk_meta
            })

        return chunks
