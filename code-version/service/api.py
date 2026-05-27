"""Service API layer - write operations for ContextEngine.

This is the ONLY layer where RequestContext is mandatory and account_id is injected.
All external calls must provide a RequestContext for multi-tenant isolation.

Note: dev branch is WRITE-ONLY. Read operations (ReadAPI) are in phase1 branch.
See CLAUDE.md §7 for tool interface spec and §8 for multi-tenant rules.
"""

import os
import re
import hashlib
import threading
import uuid
from dataclasses import dataclass
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)
from core.interfaces import ContextFS, LLM, CandidateExtractor
from core.models import RequestContext, CandidateMemory, WritePlan
from commit import ContextWriter, CandidatePipeline, OutboxStore
from extraction import Extractor
from extraction.code_chunker import CodeChunk, chunk_source_code, detect_language
from retrieval.path_anchor import guess_repo_rel_from_file_path, prepend_code_location_header


class MemoryWriteAPI:
    """Public API for memory write operations.

    All methods enforce multi-tenant isolation via RequestContext.
    Writes are orchestrated through the commit pipeline:
    1. Extract candidates via CandidateExtractor
    2. Plan write actions via MergePolicy
    3. Build ContextNode via ArchiveBuilder
    4. Write to storage via ContextFS
    5. Register OutboxEvents for async indexing
    """

    def __init__(
        self,
        fs: ContextFS,
        llm: LLM,
        outbox_store: Optional[OutboxStore] = None,
        schema_registry=None,
        vector_index=None,
        embedder=None,
        uri_resolver=None,
    ):
        """Initialize the API with required dependencies.

        Args:
            fs: ContextFS implementation for persisting nodes
            llm: LLM instance for extraction
            outbox_store: OutboxStore for registering index events (optional)
            schema_registry: Optional SchemaRegistry for dynamic tool generation
            vector_index: Optional VectorIndex for prefetching existing memories
            embedder: Optional Embedder for prefetching existing memories
            uri_resolver: Optional URIResolver for prefetching existing memories
        """
        self._fs = fs
        self._llm = llm
        self._outbox_store = outbox_store
        self._schema_registry = schema_registry
        self._vector_index = vector_index
        self._embedder = embedder
        self._uri_resolver = uri_resolver

        # Initialize write components
        policy_router = None
        if schema_registry is not None:
            from commit.policy_router import PolicyRouter
            policy_router = PolicyRouter(fs, registry=schema_registry, uri_resolver=uri_resolver)
        self._writer = ContextWriter(fs, llm=self._llm, outbox_store=outbox_store, policy_router=policy_router)
        self._pipeline = CandidatePipeline()
        self._pipeline.set_extractors(self._create_extractors())
        self._tasks: dict[str, dict] = {}
        self._tasks_lock = threading.Lock()

    def _create_extractors(self) -> list[CandidateExtractor]:
        """Create default extractors for the pipeline.

        Returns:
            List of CandidateExtractor instances (single tool-use Extractor)
        """
        try:
            from extraction.prompts import PromptManager
            from providers.unified_config import get_config

            pm = PromptManager(code_mode=get_config().code_toggle)
            return [Extractor(
                self._llm,
                prompt_manager=pm,
                schema_registry=self._schema_registry,
                fs=self._fs,
                vector_index=self._vector_index,
                embedder=self._embedder,
                uri_resolver=self._uri_resolver,
            )]
        except Exception:
            # Fallback to hardcoded prompts if template system unavailable
            return [Extractor(
                self._llm,
                schema_registry=self._schema_registry,
                fs=self._fs,
                vector_index=self._vector_index,
                embedder=self._embedder,
                uri_resolver=self._uri_resolver,
            )]

    def commit_session(
        self,
        messages: list[dict],
        ctx: RequestContext,
        confidence_threshold: float = 0.5,
        wait: bool = True,
        session_time=None,
        session_summary: str = "",
        tool_stats_text: str = "",
    ) -> dict:
        """Commit a conversation session to memory.

        This is the main entry point for writing memories.
        Extracts candidates from messages, filters by confidence,
        and writes to storage.

        Args:
            messages: List of message dicts with "role" and "content"
                      Example: [{"role": "user", "content": "..."}, ...]
            ctx: RequestContext for this operation
            confidence_threshold: Minimum confidence for writing (default 0.5)
            wait: If True, block until extraction completes (default).
                  If False, return immediately with task_id for async processing.
            session_time: Optional datetime for temporal resolution (defaults to now).
            session_summary: Optional summary of previously extracted content.
            tool_stats_text: Optional tool usage statistics text.

        Returns:
            Dict with write results:
            {
                "candidates_extracted": int,
                "candidates_filtered": int,
                "writes_completed": int,
                "writes_skipped": int,
                "writes_failed": int,
                "plans": list[WritePlan dict],
                "task_id": str (only if wait=False),
                "status": "processing" (only if wait=False)
            }
        """
        # Step 1: Extract candidates
        candidates = self._pipeline.extract(
            messages, ctx, session_time=session_time,
            session_summary=session_summary,
            tool_stats_text=tool_stats_text,
        )

        # Step 2: Filter by confidence
        filtered = self._pipeline.filter_by_confidence(candidates, confidence_threshold)

        # Step 3: Deduplicate
        deduplicated = self._pipeline.deduplicate(filtered)

        # Step 4: Write candidates (ContextWriter handles outbox registration internally)
        plans = self._writer.write_candidates(deduplicated, ctx)

        # Compile results
        writes_completed = sum(1 for p in plans if p.action != "skip")
        writes_skipped = sum(1 for p in plans if p.action == "skip")
        writes_failed = len(deduplicated) - writes_completed - writes_skipped

        result = {
            "candidates_extracted": len(candidates),
            "candidates_filtered": len(candidates) - len(filtered),
            "writes_completed": writes_completed,
            "writes_skipped": writes_skipped,
            "writes_failed": writes_failed,
            "plans": [
                {
                    "action": p.action,
                    "target_uri": p.target_uri,
                    "merged_fields": p.merged_fields,
                }
                for p in plans
            ],
        }

        # For async mode, return task_id
        if not wait:
            task_id = str(uuid.uuid4())
            with self._tasks_lock:
                self._tasks[task_id] = {"status": "completed", "result": result}
            result["task_id"] = task_id
            result["status"] = "completed"

        return result

    def commit_session_async(
        self,
        messages: list[dict],
        ctx: RequestContext,
        confidence_threshold: float = 0.5,
        session_time=None,
        session_summary: str = "",
        tool_stats_text: str = "",
    ) -> str:
        """Fire-and-forget version of commit_session.

        Dispatches extraction + write to a background thread and returns
        a task_id immediately.  The caller can poll get_task_status(task_id)
        for the result.

        Returns:
            task_id string for tracking the background job.
        """
        task_id = str(uuid.uuid4())
        with self._tasks_lock:
            self._tasks[task_id] = {"status": "processing", "result": None}

        def _run():
            try:
                result = self.commit_session(
                    messages=messages,
                    ctx=ctx,
                    confidence_threshold=confidence_threshold,
                    wait=True,
                    session_time=session_time,
                    session_summary=session_summary,
                    tool_stats_text=tool_stats_text,
                )
                with self._tasks_lock:
                    self._tasks[task_id] = {"status": "completed", "result": result}
            except Exception as exc:
                logger.error("commit_session_async failed for task %s: %s", task_id, exc, exc_info=True)
                with self._tasks_lock:
                    self._tasks[task_id] = {"status": "failed", "error": str(exc)}

        t = threading.Thread(target=_run, daemon=True, name=f"commit-{task_id[:8]}")
        t.start()
        return task_id

    def get_task_status(self, task_id: str) -> dict | None:
        """Check status of an async commit_session task."""
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def write_memory(
        self,
        candidate: CandidateMemory,
        ctx: RequestContext,
    ) -> dict:
        """Write a single candidate memory.

        Bypasses extraction - use when you already have a CandidateMemory.

        Args:
            candidate: CandidateMemory to write
            ctx: RequestContext for this operation

        Returns:
            Dict with write result:
            {
                "action": str,
                "target_uri": str,
                "merged_fields": dict,
            }
        """
        plan = self._writer.write_candidate(candidate, ctx)

        return {
            "action": plan.action,
            "target_uri": plan.target_uri,
            "merged_fields": plan.merged_fields,
        }

    def write_memories(
        self,
        candidates: list[CandidateMemory],
        ctx: RequestContext,
        parallel: bool = True,
    ) -> list[dict]:
        """Write multiple candidate memories.

        Args:
            candidates: List of CandidateMemory to write
            ctx: RequestContext for these operations
            parallel: If True, write in parallel (default True)

        Returns:
            List of write result dicts
        """
        # Deduplicate first
        deduplicated = self._pipeline.deduplicate(candidates)

        # Write (ContextWriter handles outbox registration internally)
        if parallel:
            plans = self._writer.write_candidates_parallel(deduplicated, ctx)
        else:
            plans = self._writer.write_candidates(deduplicated, ctx)

        return [
            {
                "action": p.action,
                "target_uri": p.target_uri,
                "merged_fields": p.merged_fields,
            }
            for p in plans
        ]

    def ingest_code_file(
        self,
        *,
        file_path: str,
        source_code: str,
        ctx: RequestContext,
        project_id: str = "",
        language: str | None = None,
        parallel: bool = True,
    ) -> dict:
        """Chunk and write a source file as code memories."""
        if not source_code:
            return {
                "chunks_total": 0,
                "chunks_rejected": 0,
                "chunks_accepted": 0,
                "writes_completed": 0,
                "writes_skipped": 0,
                "writes_failed": 0,
                "plans": [],
            }

        lang = detect_language(file_path, language)
        chunks = chunk_source_code(source_code, file_path, language=lang)
        chunk_uris = {id(chunk): self._code_memory_uri(chunk=chunk, ctx=ctx) for chunk in chunks}
        self._resolve_code_graph_relations(chunks, chunk_uris)

        chunks_rejected = 0
        chunks_accepted = 0
        candidates: list[CandidateMemory] = []
        for chunk in chunks:
            if self._should_reject_code_chunk(chunk.file_path, chunk.symbol):
                chunks_rejected += 1
                continue
            chunks_accepted += 1
            rel_display = (
                guess_repo_rel_from_file_path(chunk.file_path)
                or str(chunk.file_path or "").strip().replace("\\", "/")
            )
            sym = str(chunk.symbol or "").strip()
            abstract_l0 = self._code_memory_l0(chunk)
            graph_metadata = {}
            if getattr(chunk, "metadata", None):
                graph_metadata = dict(chunk.metadata.get("graph") or {})
            agfs_uri = chunk_uris.get(id(chunk)) or self._code_memory_uri(chunk=chunk, ctx=ctx)
            agfs_directory = self._agfs_directory_for_uri(agfs_uri)
            overview_l1 = self._code_memory_l1(
                symbol=sym,
                agfs_uri=agfs_uri,
                agfs_directory=agfs_directory,
                file_path=chunk.file_path,
                rel_path=rel_display,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                signature=chunk.signature,
                graph_metadata=graph_metadata,
            )
            ctags_entry = {
                "name": chunk.symbol,
                "kind": chunk.symbol_kind or "code",
                "path": rel_display,
                "line": chunk.start_line,
                "end": chunk.end_line,
                "language": chunk.language,
                "signature": chunk.signature,
            }
            bm25_document = " ".join(
                part for part in [
                    f"path:{rel_display}",
                    f"symbol:{chunk.symbol}",
                    f"kind:{chunk.symbol_kind or 'code'}",
                    f"signature:{chunk.signature or ''}",
                    str(chunk.content or ""),
                ] if part
            )
            code_metadata = {
                "language": chunk.language,
                "file_path": chunk.file_path,
                "symbol": chunk.symbol,
                "symbol_kind": chunk.symbol_kind or "code",
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_hash": chunk.chunk_hash,
                "project_id": project_id,
                "signature": chunk.signature,
                "agfs_uri": agfs_uri,
                "agfs_directory": agfs_directory,
                # L1 lexical/structural sidecar fields for hybrid retrieval.
                "ctags": ctags_entry,
                "bm25_document": bm25_document,
                "graph": graph_metadata,
                "graph_document": overview_l1,
            }
            content_l2 = prepend_code_location_header(str(chunk.content or ""), code_metadata)
            candidates.append(
                CandidateMemory(
                    category="code",
                    owner_scope="agent",
                    routing_key=chunk.routing_key,
                    abstract=abstract_l0,
                    overview=overview_l1,
                    content=content_l2,
                    confidence=0.95,
                    code_metadata=code_metadata,
                )
            )

        results = self.write_memories(candidates, ctx, parallel=parallel)
        writes_completed = sum(1 for result in results if result["action"] != "skip")
        writes_skipped = sum(1 for result in results if result["action"] == "skip")
        writes_failed = len(candidates) - writes_completed - writes_skipped
        return {
            "chunks_total": len(chunks),
            "chunks_rejected": chunks_rejected,
            "chunks_accepted": chunks_accepted,
            "writes_completed": writes_completed,
            "writes_skipped": writes_skipped,
            "writes_failed": writes_failed,
            "plans": results,
        }

    @staticmethod
    def _should_reject_code_chunk(file_path: str, symbol: str) -> bool:
        """Reject synthetic/internal diagnostic chunks from code memory."""
        path = str(file_path or "").strip().lower()
        base = os.path.basename(path)
        sym = str(symbol or "").strip().lower()

        if base.startswith("turn_"):
            return True
        if "diag_many_funcs.py" in path:
            return True
        if re.fullmatch(r"ast_h\d+", sym) and "diag" in path:
            return True
        return False

    @classmethod
    def _resolve_code_graph_relations(cls, chunks: list[CodeChunk], chunk_uris: dict[int, str]) -> None:
        """Attach build-time resolved graph edges to chunk metadata."""
        symbol_index: dict[str, list[CodeChunk]] = {}

        def leaf(value: object) -> str:
            text = str(value or "").strip()
            if not text:
                return ""
            return text.rsplit(".", 1)[-1]

        def add_symbol(symbol: object, chunk: CodeChunk) -> None:
            key = leaf(symbol)
            if key:
                symbol_index.setdefault(key, []).append(chunk)

        for chunk in chunks:
            add_symbol(chunk.symbol, chunk)
            graph = (chunk.metadata or {}).get("graph") if chunk.metadata else {}
            if isinstance(graph, dict):
                add_symbol(graph.get("symbol"), chunk)

        for chunk in chunks:
            metadata = dict(chunk.metadata or {})
            graph = dict(metadata.get("graph") or {})
            relations: list[dict] = []
            seen: set[tuple[str, str, str]] = set()
            for relation_type in ("calls", "extends", "contains"):
                values = graph.get(relation_type)
                if not isinstance(values, list):
                    continue
                for raw_name in values:
                    name = str(raw_name or "").strip()
                    target_key = leaf(name)
                    if not target_key:
                        continue
                    for target in symbol_index.get(target_key, []):
                        if target is chunk:
                            continue
                        target_uri = chunk_uris.get(id(target), "")
                        dedupe_key = (relation_type, name, target_uri or target.routing_key)
                        if dedupe_key in seen:
                            continue
                        seen.add(dedupe_key)
                        relations.append(
                            {
                                "type": relation_type,
                                "name": name,
                                "target_uri": target_uri,
                                "target_symbol": target.symbol,
                                "target_path": target.file_path,
                                "target_start_line": target.start_line,
                                "target_end_line": target.end_line,
                                "target_signature": target.signature,
                                "confidence": "resolved_symbol",
                            }
                        )
            graph["relations"] = relations
            metadata["graph"] = graph
            chunk.metadata = metadata

    @staticmethod
    def _code_memory_l0(chunk: CodeChunk) -> str:
        """L0 text for code memories."""
        sym = str(chunk.symbol or "").strip()
        kind = chunk.symbol_kind or "code"
        label = {
            "function": "function",
            "async_function": "async function",
            "type": "type",
            "code": "code",
        }.get(kind, "code")
        if sym:
            return f"{sym} {label}"
        return label

    @staticmethod
    def _code_memory_l1(
        *,
        symbol: str,
        agfs_uri: str,
        agfs_directory: str,
        file_path: str,
        rel_path: str,
        start_line: int,
        end_line: int,
        signature: str,
        graph_metadata: dict,
    ) -> str:
        """L1 text for code memories: locator + compact CGM-style graph properties."""
        title = symbol or "code"
        lines: list[str] = [f"# {title}", "", "## Location"]
        lines.append(f"- symbol: {title}")
        if agfs_uri:
            lines.append(f"- agfs.uri: {agfs_uri}")
        if agfs_directory:
            lines.append(f"- agfs.directory: {agfs_directory}")
        if file_path:
            file_display = str(file_path).strip().replace("\\", "/")
            lines.append(f"- source.file: {file_display}")
        if rel_path:
            lines.append(f"- path: {rel_path}")
        if start_line is not None and end_line is not None:
            lines.append(f"- source.lines: {start_line}-{end_line}")
        if signature:
            lines.extend(["", "## Signature", f"```text\n{signature}\n```"])

        def add_list(label: str, values: object, limit: int = 12) -> None:
            if not isinstance(values, list):
                return
            cleaned = [str(v).strip() for v in values if str(v).strip()]
            if cleaned:
                lines.append(f"- {label}: {', '.join(cleaned[:limit])}")

        graph_start = len(lines)
        lines.extend(["", "## Graph"])
        add_list("graph.calls", graph_metadata.get("calls"))
        add_list("graph.imports", graph_metadata.get("imports"))
        add_list("graph.extends", graph_metadata.get("extends"))
        add_list("graph.contains", graph_metadata.get("contains"))
        relations = graph_metadata.get("relations")
        if isinstance(relations, list):
            relation_lines: list[str] = []
            for rel in relations[:12]:
                if not isinstance(rel, dict):
                    continue
                relation_type = str(rel.get("type") or "").strip()
                name = str(rel.get("name") or rel.get("target_symbol") or "").strip()
                target_path = str(rel.get("target_path") or "").strip().replace("\\", "/")
                start = rel.get("target_start_line")
                end = rel.get("target_end_line")
                target_uri = str(rel.get("target_uri") or "").strip()
                location = target_path
                if start is not None and end is not None:
                    location = f"{location}:{start}-{end}" if location else f"{start}-{end}"
                if relation_type and name:
                    suffix = f" -> {location}" if location else ""
                    if target_uri:
                        suffix += f" ({target_uri})"
                    relation_lines.append(f"{relation_type}:{name}{suffix}")
            if relation_lines:
                lines.append(f"- graph.resolved_relations: {'; '.join(relation_lines)}")
        if len(lines) == graph_start + 2:
            lines.append("- graph.relations: none")
        return "\n".join(lines).strip() or "code"

    @staticmethod
    def _slugify_code_value(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "code_chunk"

    @classmethod
    def _code_memory_slug(cls, chunk: CodeChunk) -> str:
        language = str(chunk.language or "unknown")
        file_path = str(chunk.file_path or "")
        symbol = str(chunk.symbol or chunk.routing_key or "symbol")
        line_range = (
            f"{chunk.start_line}_{chunk.end_line}"
            if chunk.start_line is not None and chunk.end_line is not None
            else "0_0"
        )
        file_name = os.path.basename(file_path) if file_path else "file"
        file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        prefix = cls._slugify_code_value(f"{language}_{file_stem}_{symbol}_{line_range}")
        prefix = prefix[:96].rstrip("_") or "code_chunk"
        identity_line_range = (
            f"{chunk.start_line}-{chunk.end_line}"
            if chunk.start_line is not None and chunk.end_line is not None
            else "0-0"
        )
        identity = f"{language}:{file_path}:{symbol}:{identity_line_range}"
        digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"

    @classmethod
    def _code_memory_uri(cls, *, chunk: CodeChunk, ctx: RequestContext) -> str:
        owner_type = "agents"
        owner_id = ctx.agent_id
        slug = cls._code_memory_slug(chunk)
        return f"ctx://{ctx.account_id}/{owner_type}/{owner_id}/memories/code/{slug}"

    def write_natural_language(
        self,
        memories: list[dict],
        ctx: RequestContext,
    ) -> list[dict]:
        """Write prepared non-code memory entries.

        Accepts already prepared content and routes it through the normal
        write pipeline. Entries can provide properties directly, or have
        them extracted from the content when possible.
        """
        try:
            from filter.handlers.keywords import extract_user_prompt_keywords
            from filter.handlers.response_keywords import extract_response_keywords
        except ImportError:
            extract_user_prompt_keywords = None
            extract_response_keywords = None

        candidates: list[CandidateMemory] = []
        for mem in memories:
            mem_type = mem.get("type", "l0")
            role = mem.get("role", "user")
            raw_content = mem.get("content", "")
            category = mem.get("category") or "natural_language"

            abstract = mem.get("abstract") or (raw_content[:200] if raw_content else "")

            overview = mem.get("overview") or ""
            if mem_type == "l1":
                provided_props = mem.get("properties", "")
                if overview:
                    pass
                elif provided_props:
                    overview = provided_props
                elif role == "user" and extract_user_prompt_keywords:
                    overview = extract_user_prompt_keywords(raw_content)
                elif role == "assistant" and extract_response_keywords:
                    overview = extract_response_keywords(raw_content)

            metadata = mem.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            for key in ("source", "tool_name", "file_path", "detected", "strategy"):
                value = mem.get(key)
                if value:
                    metadata[key] = value

            candidates.append(CandidateMemory(
                category=category,
                owner_scope=mem.get("owner_scope") or ("agent" if category == "tool_outputs" else "user"),
                routing_key=mem.get("routing_key", "default"),
                abstract=abstract,
                overview=overview,
                content=raw_content,
                confidence=mem.get("confidence", 0.8),
                code_metadata=metadata or None,
            ))

        deduplicated = self._pipeline.deduplicate(candidates)
        plans = self._writer.write_candidates(deduplicated, ctx)

        return [
            {
                "action": p.action,
                "target_uri": p.target_uri,
                "merged_fields": p.merged_fields,
            }
            for p in plans
        ]

    @staticmethod
    def _agfs_directory_for_uri(uri: str) -> str:
        if not uri.startswith("ctx://"):
            return ""
        rest = uri[len("ctx://"):]
        parts = rest.split("/")
        if not parts:
            return ""
        return "/accounts/" + "/".join(parts)


# Singleton instances for simple usage
# In production, use dependency injection
_default_write_api: Optional[MemoryWriteAPI] = None


def init_write_api(
    fs: ContextFS,
    llm: LLM,
    outbox_store: Optional[OutboxStore] = None,
    schema_registry=None,
    vector_index=None,
    embedder=None,
    uri_resolver=None,
) -> MemoryWriteAPI:
    """Initialize the global write API instance.

    Args:
        fs: ContextFS implementation
        llm: LLM instance for extraction
        outbox_store: Optional OutboxStore for async indexing
        schema_registry: Optional SchemaRegistry for dynamic tool generation
        vector_index: Optional VectorIndex for prefetching existing memories
        embedder: Optional Embedder for prefetching existing memories
        uri_resolver: Optional URIResolver for prefetching existing memories

    Returns:
        Configured MemoryWriteAPI instance
    """
    global _default_write_api
    _default_write_api = MemoryWriteAPI(
        fs, llm, outbox_store, schema_registry,
        vector_index, embedder, uri_resolver,
    )
    return _default_write_api


def get_write_api() -> Optional[MemoryWriteAPI]:
    """Get the global write API instance.

    Returns:
        MemoryWriteAPI if initialized, None otherwise
    """
    return _default_write_api


# ---------------------------------------------------------------------------
# Read / Search API
# ---------------------------------------------------------------------------

from core.errors import AccessDeniedError, ValidationError as CoreValidationError
from core.models import (
    RetrievalConfig,
    RetrievedBlock,
    RetrieverMode,
    SearchMemoryResult,
)
from retrieval.pipeline import RetrievalPipeline
from retrieval.context_reader import ContextReader


class ReadAPI:
    """Public API for memory search and read operations.

    Exposes two tools consumed by AI agents:
      - search_memory: semantic retrieval -> structured SearchMemoryResult
      - read_memory: URI-based read -> RetrievedBlock with full content
    """

    def __init__(
        self,
        pipeline: RetrievalPipeline,
        read_service: ContextReader | None = None,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._read_service = read_service
        self._cfg = config or RetrievalConfig()

    def search_memory(
        self,
        query: str,
        ctx: RequestContext,
        *,
        top_k: int = 10,
        categories: list[str] | None = None,
        target_uri: str | None = None,
        session_archive: dict | None = None,
        score_threshold: float | None = None,
        include_debug: bool = False,
        mode: str = RetrieverMode.QUICK,
        fill_content_for_top_k: int = 0,
    ) -> SearchMemoryResult:
        if not (query or "").strip():
            raise CoreValidationError("query", "query must not be empty")
        if top_k > self._cfg.max_top_k:
            raise CoreValidationError("top_k", f"top_k={top_k} exceeds max {self._cfg.max_top_k}")

        if target_uri:
            prefix = f"ctx://{ctx.account_id}/"
            if target_uri.startswith("ctx://") and not target_uri.startswith(prefix):
                raise AccessDeniedError(target_uri, ctx.account_id, "target_uri account mismatch")

        result = self._pipeline.run(
            query, ctx,
            top_k=top_k,
            categories=categories,
            target_uri=target_uri,
            session_archive=session_archive,
            score_threshold=score_threshold,
            mode=mode,
            fill_content_for_top_k=fill_content_for_top_k,
        )

        if not include_debug:
            result.trace = None

        return result

    def read_memory(
        self,
        uri: str,
        ctx: RequestContext,
    ) -> RetrievedBlock:
        """Read L2 md file content by URI.

        Since search_memory already returns abstract in results,
        read_memory only reads the actual md file content.
        """
        return self._read_service.read(uri, ctx=ctx)
