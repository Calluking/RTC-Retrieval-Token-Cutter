"""LLM output handler for Filter — compresses assistant responses for memory storage.

This handler is used in Agentic Loop scenarios (like SWE-bench with multi-turn
reasoning) where each LLM response needs to be stored in memory. Rather than
running the full extraction pipeline (expensive LLM call), we apply fast Filter
shortening to compress the response before storing.

Usage in hook system:
    process_bash_output("llm-output", assistant_response)
    # or directly:
    handler = LLMOutputHandler()
    compressed = handler(llm_response_text)

Integration points:
  - server/memory_service.py after_llm_response() hook
  - tests/e2e/test_memory_swebench_agentic.py Agentic loop
"""

from __future__ import annotations

import re

from filter.core.adaptive import detect_content_type, ContentType, adaptive_shorten
from filter.core.filter import MinimalFilter
from filter.core.dedup import deduplicate


# Patterns for LLM output sub-type detection
_REASONING_PATTERNS = [
    re.compile(r"^Let me think|First,? I|In summary,? |Therefore,? |The answer is", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Step \d+[\.:]\s", re.MULTILINE),
    re.compile(r"^\d+\.\s+[A-Z]", re.MULTILINE),  # Numbered reasoning steps
    re.compile(r"^\-\s+[A-Z][a-z]", re.MULTILINE),  # Bullet points in reasoning
]

_PATCH_PATTERNS = [
    re.compile(r"^--- a/", re.MULTILINE),
    re.compile(r"^\+\+\+ b/", re.MULTILINE),
    re.compile(r"^diff --git", re.MULTILINE),
    re.compile(r"^@@ -\d+,\d+ \+\d+,\d+ @@", re.MULTILINE),
]

_TOOL_CALL_PATTERNS = [
    re.compile(r'^<tool_call>', re.MULTILINE),
    re.compile(r'"name":\s*"(\w+)"', re.MULTILINE),
    re.compile(r"^Calling tool:", re.MULTILINE),
]


class LLMOutputHandler:
    """Compresses LLM output text for memory storage.

    LLM outputs fall into several categories, each requiring different treatment:

    1. **Patch/diff output** — preserve exact structure, truncate only if very long
    2. **Reasoning/chain-of-thought** — keep first/last steps, compress middle
    3. **Error output** — preserve error type, location, message
    4. **Code output** — preserve structure, compress implementation details
    5. **Tool calls** — preserve tool name and key args, truncate long outputs
    6. **Generic text** — apply standard Filter shortening

    This handler is NOT a compression codec — it does NOT encode/decode.
    It shortens by filtering, deduplicating, and truncating while preserving
    the information density needed for later retrieval.
    """

    def __init__(self, default_budget_chars: int = 3000):
        """Initialize the handler.

        Args:
            default_budget_chars: Default max characters for compressed output.
                                  Memory storage benefits from ~30-50% reduction.
        """
        self._default_budget = default_budget_chars
        self._filter = MinimalFilter()

    def __call__(self, text: str, budget_chars: int | None = None) -> str:
        """Compress LLM output text.

        Args:
            text: Raw LLM output text
            budget_chars: Optional budget override

        Returns:
            Compressed text fitting within budget
        """
        if not text or not text.strip():
            return text

        budget = budget_chars or self._default_budget

        # Fast path: already within budget
        if len(text) <= budget:
            return text

        # Detect output subtype
        subtype = self._detect_subtype(text)

        # Route to appropriate compressor
        if subtype == "patch":
            return self._compress_patch(text, budget)
        elif subtype == "reasoning":
            return self._compress_reasoning(text, budget)
        elif subtype == "error":
            return self._compress_error(text, budget)
        elif subtype == "tool_call":
            return self._compress_tool_call(text, budget)
        elif subtype == "code":
            return self._compress_code(text, budget)
        else:
            return self._compress_generic(text, budget)

    def _detect_subtype(self, text: str) -> str:
        """Detect LLM output subtype for optimal compression strategy."""
        first_500 = text[:500]

        # Patch/diff is highest priority — must preserve structure exactly
        if _PATCH_PATTERNS[0].search(text) or _PATCH_PATTERNS[1].search(text):
            return "patch"
        if "diff --git" in text:
            return "patch"

        # Tool calls
        if "<tool_call>" in text or "Calling tool:" in first_500:
            return "tool_call"
        if '"name":' in first_500 and '"arguments":' in first_500:
            return "tool_call"

        # Error traces
        if "Traceback (most recent call last)" in text:
            return "error"
        if re.search(r"\b(Error|Exception|Failed|failed|error|SEVERE)\b", first_500) and len(text) > 200:
            return "error"

        # Reasoning / chain-of-thought
        reasoning_indicators = sum(1 for p in _REASONING_PATTERNS if p.search(first_500))
        if reasoning_indicators >= 1 and len(text) > 500:
            return "reasoning"

        # Code blocks
        content_type = detect_content_type(text)
        if content_type == ContentType.CODE:
            return "code"

        return "generic"

    def _compress_patch(self, text: str, budget: int) -> str:
        """Compress patch/diff output — preserve structure, truncate if needed.

        Patch format:
            --- a/file
            +++ b/file
            @@ -old,old @@
            -old line
            +new line

        Strategy: keep all file headers + first 2 hunks, truncate remaining with marker.
        """
        lines = text.splitlines()
        if len(text) <= budget:
            return text

        # Keep all file headers (---, +++, @@)
        result_lines: list[str] = []
        hunks_kept = 0
        max_hunks = 3
        in_hunk = False

        for line in lines:
            is_header = line.startswith("--- ") or line.startswith("+++ ") or line.startswith("diff --git")
            is_hunk = line.startswith("@@ ")

            if is_header:
                result_lines.append(line)
                hunks_kept = 0
                in_hunk = False
            elif is_hunk:
                if hunks_kept < max_hunks:
                    result_lines.append(line)
                    hunks_kept += 1
                    in_hunk = True
                else:
                    if not in_hunk:
                        result_lines.append(f"// ... {len(lines) - len(result_lines)} additional lines omitted ...")
                        in_hunk = True
            elif in_hunk and hunks_kept <= max_hunks:
                result_lines.append(line)

        result = "\n".join(result_lines)
        if len(result) > budget:
            result = result[:budget] + f"\n// ... Filter truncated ..."
        return result

    def _compress_reasoning(self, text: str, budget: int) -> str:
        """Compress reasoning/chain-of-thought — keep first and last steps.

        Strategy: keep first 3 steps + last 2 steps, collapse middle with summary.
        """
        lines = text.splitlines()
        if len(text) <= budget:
            return text

        # Find step boundaries (numbered or bullet points)
        step_indices: list[int] = []
        for i, line in enumerate(lines):
            if re.match(r"^(Step \d+[\.:]\s|#\s|\d+[\.\)]\s|\-\s)", line.strip()):
                step_indices.append(i)

        if len(step_indices) <= 4:
            # Not many steps — just truncate
            return self._compress_generic(text, budget)

        # Keep: first 3 steps + last 2 steps
        keep_indices: set[int] = set()
        keep_indices.update(step_indices[:3])
        keep_indices.update(step_indices[-2:])

        result_parts: list[str] = []
        current_step_start = 0

        for idx in sorted(step_indices):
            if idx in keep_indices:
                if current_step_start < idx:
                    result_parts.extend(lines[current_step_start:idx])
                result_parts.append(lines[idx])
                current_step_start = idx + 1

        if current_step_start < len(lines):
            result_parts.extend(lines[current_step_start:])

        result = "\n".join(result_parts)
        if len(result) > budget:
            result = result[:budget] + "\n// ... reasoning truncated ..."
        return result

    def _compress_error(self, text: str, budget: int) -> str:
        """Compress error output — preserve error type, location, message.

        Strategy: keep error type + location + key message, truncate traceback middle.
        """
        lines = text.splitlines()
        if len(text) <= budget:
            return text

        # Find error message (usually first Error: or Exception: line)
        error_line_idx = -1
        for i, line in enumerate(lines[:10]):
            if re.search(r"\b(Error|Exception|Failed|SEVERE):\s+", line, re.IGNORECASE):
                error_line_idx = i
                break

        if error_line_idx < 0:
            # No clear error line — treat as generic
            return self._compress_generic(text, budget)

        result_parts: list[str] = []
        # Keep: first few lines (error intro)
        result_parts.extend(lines[:error_line_idx + 1])
        # Keep: error message
        result_parts.append(lines[error_line_idx])

        # Keep: first 5 + last 3 traceback lines
        traceback_start = error_line_idx + 1
        traceback_end = len(lines)
        traceback = lines[traceback_start:traceback_end]

        if len(traceback) > 12:
            result_parts.extend(traceback[:5])
            result_parts.append(f"    // ... {len(traceback) - 10} traceback lines omitted ...")
            result_parts.extend(traceback[-3:])
        else:
            result_parts.extend(traceback)

        result = "\n".join(result_parts)
        if len(result) > budget:
            result = result[:budget] + "\n// ... error truncated ..."
        return result

    def _compress_tool_call(self, text: str, budget: int) -> str:
        """Compress tool call output — preserve tool name, args, key results.

        Strategy: keep tool name + key arguments, truncate long output values.
        """
        if len(text) <= budget:
            return text

        # Try to extract tool_call XML-like structure
        if "<tool_call>" in text:
            return self._compress_tool_call_xml(text, budget)

        # Fallback: generic truncation with head preservation
        return self._compress_generic(text, budget)

    def _compress_tool_call_xml(self, text: str, budget: int) -> str:
        """Compress XML-style tool call output."""
        lines = text.splitlines()
        result_lines: list[str] = []
        skipped = 0

        for line in lines:
            # Keep header lines
            if line.startswith("<tool_call>") or line.startswith("</tool_call>"):
                result_lines.append(line)
            elif "<name>" in line or "<arguments>" in line or "</arguments>" in line:
                result_lines.append(line)
            elif len(line) > 200:
                # Truncate long output lines
                result_lines.append(line[:200] + " // ... truncated ...")
                skipped += len(line) - 200
            else:
                result_lines.append(line)

        result = "\n".join(result_lines)
        if len(result) > budget:
            result = result[:budget] + f"\n// ... output truncated ..."
        return result

    def _compress_code(self, text: str, budget: int) -> str:
        """Compress code output — preserve signature/structure, truncate body."""
        if len(text) <= budget:
            return text

        # Use the core adaptive shorten for code
        result = adaptive_shorten(text, max_lines=None)
        if len(result.text) <= budget:
            return result.text
        return result.text[:budget] + "\n// ... code truncated ..."

    def _compress_generic(self, text: str, budget: int) -> str:
        """Compress generic text — filter + dedup + truncate."""
        if len(text) <= budget:
            return text

        # Step 1: Minimal filter (strip comments)
        filtered = self._filter.filter(text)
        text = filtered.text if filtered.text.strip() else text

        if len(text) <= budget:
            return text

        # Step 2: Deduplicate
        deduped = deduplicate(text, max_adjacent=3)
        if len(deduped) <= budget:
            return deduped

        # Step 3: Truncate with head preservation
        head_chars = int(budget * 0.6)
        tail_chars = budget - head_chars - 20  # 20 for marker

        head = text[:head_chars]
        tail = text[-tail_chars:] if tail_chars > 0 else ""

        if tail:
            return f"{head}\n// ... {len(text) - budget} chars omitted ...\n{tail}"
        return head + f"\n// ... {len(text) - budget} chars omitted ..."


# Convenience function for hook system integration
def compress_llm_output(text: str, budget_chars: int = 3000) -> str:
    """Top-level function for compressing LLM output.

    This is the function exposed to the hook system:
        from filter.handlers.llm_output import compress_llm_output
        compressed = compress_llm_output(llm_response_text)

    Args:
        text: Raw LLM output
        budget_chars: Maximum characters in compressed output

    Returns:
        Compressed text
    """
    handler = LLMOutputHandler(default_budget_chars=budget_chars)
    return handler(text, budget_chars=budget_chars)


# Singleton for reuse in hot paths
_llm_output_handler: LLMOutputHandler | None = None


def get_handler() -> LLMOutputHandler:
    """Get the singleton LLMOutputHandler instance."""
    global _llm_output_handler
    if _llm_output_handler is None:
        _llm_output_handler = LLMOutputHandler()
    return _llm_output_handler
