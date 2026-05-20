"""Merge policies for determining write actions.

Each policy implements the MergePolicy Protocol and decides whether
to create, merge, append, or skip a candidate memory.
"""

import hashlib
import re
import uuid as uuid_lib
from datetime import UTC, datetime
from pathlib import Path

from commit.routing_key import normalize_routing_key
from core.interfaces import ContextFS, MergePolicy
from core.models import CandidateMemory, RequestContext, WritePlan
from core.uri_resolver import URIResolver


class ProfilePolicy(MergePolicy):
    """Merge policy for user profile nodes.

    Behavior (CLAUDE.md §5):
    - Target URI: ctx://{account}/users/{user}/memories/profile
    - Always merge (never create new, never skip)
    - New information replaces old (user state changes)
    - Conflict resolution: new information wins

    Profile is a fixed URI that gets continuously updated.
    """

    def __init__(self, fs: ContextFS, uri_resolver: URIResolver):
        """Initialize ProfilePolicy.

        Args:
            fs: ContextFS for checking existing nodes
            uri_resolver: URIResolver for URI construction
        """
        self._fs = fs
        self._uri_resolver = uri_resolver

    def plan(self, candidate: CandidateMemory, ctx: RequestContext) -> WritePlan:
        """Generate WritePlan for profile candidate.

        Args:
            candidate: CandidateMemory (must be category="profile")
            ctx: RequestContext for this operation

        Returns:
            WritePlan with action="merge" and target URI for profile
        """
        target_uri = self._uri_resolver.resolve("profile", {"routing_key": candidate.routing_key}, ctx)

        # Check if profile exists
        exists = self._fs.exists(target_uri, ctx)

        if exists:
            action = "merge"
            # Read existing node to get version for optimistic locking
            existing_node = self._fs.read_node(target_uri, ctx)
            current_version = existing_node.metadata.get("version", 0)

            # Merge strategy: new info replaces old (user state changes)
            merged_fields = {
                "abstract": candidate.abstract,
                "overview": candidate.overview,
                "content": candidate.content,
                "updated_at": datetime.now(UTC).isoformat(),
                "expected_version": current_version,  # For optimistic locking
            }
        else:
            action = "create"
            merged_fields = {}

        return WritePlan(
            action=action,
            target_uri=target_uri,
            merged_fields=merged_fields,
            relation_edges=[],
        )


class AggregateTopicPolicy(MergePolicy):
    """Merge policy for topic-based memories.

    Applies to: preference, entity, pattern

    Behavior (CLAUDE.md §5):
    - Target URI: ctx://.../{category}/{slug}
    - If exists: merge content into overview/content
    - If not exists: create new node
    - Similar slug handling: edit distance < 2 or semantic > 0.9 → merge

    Uses routing_key as slug for URI construction.
    """

    def __init__(self, fs: ContextFS, uri_resolver: URIResolver, similarity_threshold: float = 0.9):
        """Initialize AggregateTopicPolicy.

        Args:
            fs: ContextFS for checking existing nodes
            uri_resolver: URIResolver for URI construction
            similarity_threshold: Semantic similarity threshold for slug merging
        """
        self._fs = fs
        self._uri_resolver = uri_resolver
        self._similarity_threshold = similarity_threshold

    def plan(self, candidate: CandidateMemory, ctx: RequestContext) -> WritePlan:
        """Generate WritePlan for topic-based candidate.

        Args:
            candidate: CandidateMemory (preference, entity, or pattern)
            ctx: RequestContext for this operation

        Returns:
            WritePlan with action="create" or "merge"
        """
        # Normalize routing_key to avoid fragmentation
        normalized_key = normalize_routing_key(candidate.routing_key, candidate.category)

        # Determine semantic field name based on category
        # Map category to its identifying field
        if candidate.category == "preference":
            routing_fields = {"topic": normalized_key}
        elif candidate.category == "entity":
            routing_fields = {"name": normalized_key}
        elif candidate.category == "pattern":
            routing_fields = {"topic": normalized_key}
        else:
            routing_fields = {"routing_key": normalized_key}

        target_uri = self._uri_resolver.resolve(candidate.category, routing_fields, ctx)

        # Check if exact URI exists
        if self._fs.exists(target_uri, ctx):
            # Read existing node to get version for optimistic locking
            existing_node = self._fs.read_node(target_uri, ctx)
            current_version = existing_node.metadata.get("version", 0)

            return WritePlan(
                action="merge",
                target_uri=target_uri,
                merged_fields={
                    "abstract": candidate.abstract,
                    "existing_overview": existing_node.overview,
                    "overview_append": candidate.overview,
                    "existing_content": existing_node.content,
                    "content_append": candidate.content,
                    "expected_version": current_version,  # For optimistic locking
                },
                relation_edges=[],
            )

        # Check for similar slugs via normalization (see routing_key.py)
        # If not found with normalized key, create new node

        return WritePlan(
            action="create",
            target_uri=target_uri,
            merged_fields={},
            relation_edges=[],
        )


class AppendOnlyPolicy(MergePolicy):
    """Merge policy for time-series events.

    Applies to: event, case

    Behavior (CLAUDE.md §5):
    - event_id/case_id globally unique (timestamp_uuid)
    - Always create, never overwrite history
    - Establish SEQUENCE relations for same-session events

    Each event is a new node - historical record preserved.
    """

    def __init__(self, fs: ContextFS, uri_resolver: URIResolver):
        """Initialize AppendOnlyPolicy.

        Args:
            fs: ContextFS for checking existing nodes
            uri_resolver: URIResolver for URI construction
        """
        self._fs = fs
        self._uri_resolver = uri_resolver

    def plan(self, candidate: CandidateMemory, ctx: RequestContext) -> WritePlan:
        """Generate WritePlan for event/case candidate.

        Args:
            candidate: CandidateMemory (event or case)
            ctx: RequestContext for this operation

        Returns:
            WritePlan with action="create" and unique event ID
        """
        # Build fields based on category
        if candidate.category == "event":
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            unique_id = uuid_lib.uuid4().hex[:8]
            event_id = f"{timestamp}_{unique_id}"
            fields = {"event_name": candidate.routing_key, "timestamp": event_id}
        elif candidate.category == "case":
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            unique_id = uuid_lib.uuid4().hex[:8]
            case_id = f"{timestamp}_{unique_id}"
            fields = {"case_name": candidate.routing_key, "timestamp": case_id}
        else:
            timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            unique_id = uuid_lib.uuid4().hex[:8]
            fields = {"routing_key": f"{candidate.routing_key}_{timestamp}_{unique_id}"}

        target_uri = self._uri_resolver.resolve(candidate.category, fields, ctx)

        # Always create new event nodes (never merge)
        return WritePlan(
            action="create",
            target_uri=target_uri,
            merged_fields={},
            relation_edges=[],
        )


class SkillToolPolicy(MergePolicy):
    """Merge policy for agent skills and tools.

    Applies to: skill, tool

    Behavior (CLAUDE.md §5):
    - skill URI: ctx://{account}/agents/{agent}/skills/{skill_name}
    - tool URI:  ctx://{account}/agents/{agent}/memories/tools/{tool_name}
    - Fixed URI, always exists or is created
    - Cumulative: best practices, failures, parameters appended
    - Usage stats tracked in metadata

    Skills and tools accumulate knowledge over time.
    """

    def __init__(self, fs: ContextFS, uri_resolver: URIResolver):
        """Initialize SkillToolPolicy.

        Args:
            fs: ContextFS for checking existing nodes
            uri_resolver: URIResolver for URI construction
        """
        self._fs = fs
        self._uri_resolver = uri_resolver

    def plan(self, candidate: CandidateMemory, ctx: RequestContext) -> WritePlan:
        """Generate WritePlan for skill/tool candidate.

        Args:
            candidate: CandidateMemory (skill or tool)
            ctx: RequestContext for this operation

        Returns:
            WritePlan with action="create" or "merge" (accumulate)
        """
        if candidate.category == "tool":
            fields = {"tool_identifier": candidate.routing_key}
        else:
            fields = {"skill_name": candidate.routing_key}

        target_uri = self._uri_resolver.resolve(candidate.category, fields, ctx)

        exists = self._fs.exists(target_uri, ctx)

        if exists:
            # Read existing node to get version for optimistic locking
            existing_node = self._fs.read_node(target_uri, ctx)
            current_version = existing_node.metadata.get("version", 0)

            return WritePlan(
                action="merge",
                target_uri=target_uri,
                merged_fields={
                    "skill_merge": True,
                    "existing_content": existing_node.content,
                    "existing_overview": existing_node.overview,
                    "existing_abstract": existing_node.abstract,
                    "new_content": candidate.content,
                    "new_overview": candidate.overview,
                    "new_abstract": candidate.abstract,
                    "usage_count": existing_node.metadata.get("usage_count", 0) + 1,
                    "expected_version": current_version,  # For optimistic locking
                },
                relation_edges=[],
            )
        else:
            return WritePlan(
                action="create",
                target_uri=target_uri,
                merged_fields={
                    "usage_count": 1,
                },
                relation_edges=[],
            )


class CodeChunkPolicy(MergePolicy):
    """Merge policy for code chunks with canonical latest + version history."""

    def __init__(self, fs: ContextFS):
        self._fs = fs

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return value.strip("_") or "code_chunk"

    def _build_identity(self, candidate: CandidateMemory) -> str:
        metadata = candidate.code_metadata or {}
        language = str(metadata.get("language") or "unknown")
        file_path = str(metadata.get("file_path") or "")
        symbol = str(metadata.get("symbol") or candidate.routing_key or "symbol")
        start_line = metadata.get("start_line")
        end_line = metadata.get("end_line")
        line_range = f"{start_line}-{end_line}" if start_line is not None and end_line is not None else "0-0"
        return f"{language}:{file_path}:{symbol}:{line_range}"

    def _build_slug(self, candidate: CandidateMemory) -> str:
        metadata = candidate.code_metadata or {}
        language = str(metadata.get("language") or "unknown")
        file_path = str(metadata.get("file_path") or "")
        symbol = str(metadata.get("symbol") or candidate.routing_key or "symbol")
        start_line = metadata.get("start_line")
        end_line = metadata.get("end_line")
        line_range = f"{start_line}_{end_line}" if start_line is not None and end_line is not None else "0_0"

        file_name = Path(file_path).name if file_path else "file"
        file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        prefix = self._slugify(f"{language}_{file_stem}_{symbol}_{line_range}")
        prefix = prefix[:96].rstrip("_") or "code_chunk"
        digest = hashlib.sha1(self._build_identity(candidate).encode("utf-8")).hexdigest()[:16]
        return f"{prefix}_{digest}"

    def _build_target_uri(self, candidate: CandidateMemory, ctx: RequestContext) -> str:
        owner_type = f"{candidate.owner_scope}s"
        owner_id = ctx.agent_id if candidate.owner_scope == "agent" else ctx.user_id
        slug = self._build_slug(candidate)
        return f"ctx://{ctx.account_id}/{owner_type}/{owner_id}/memories/code/{slug}"

    def _compute_chunk_hash(self, candidate: CandidateMemory) -> str:
        metadata = candidate.code_metadata or {}
        existing_hash = str(metadata.get("chunk_hash") or "").strip()
        if existing_hash:
            return existing_hash
        return hashlib.sha256(candidate.content.encode("utf-8")).hexdigest()

    def plan(self, candidate: CandidateMemory, ctx: RequestContext) -> WritePlan:
        target_uri = self._build_target_uri(candidate, ctx)
        chunk_hash = self._compute_chunk_hash(candidate)

        if not self._fs.exists(target_uri, ctx):
            return WritePlan(
                action="create",
                target_uri=target_uri,
                merged_fields={
                    "code_identity": self._build_identity(candidate),
                    "chunk_hash": chunk_hash,
                },
                relation_edges=[],
            )

        existing_node = self._fs.read_node(target_uri, ctx)
        current_version = existing_node.metadata.get("version", 0)
        existing_hash = (
            existing_node.metadata.get("chunk_hash")
            or hashlib.sha256(existing_node.content.encode("utf-8")).hexdigest()
        )

        if existing_hash == chunk_hash:
            if existing_node.abstract != candidate.abstract or existing_node.overview != candidate.overview:
                return WritePlan(
                    action="merge",
                    target_uri=target_uri,
                    merged_fields={
                        "expected_version": current_version,
                        "code_identity": self._build_identity(candidate),
                        "chunk_hash": chunk_hash,
                    },
                    relation_edges=[],
                )
            return WritePlan(
                action="skip",
                target_uri=target_uri,
                merged_fields={},
                relation_edges=[],
            )

        snapshot_version = int(current_version) if isinstance(current_version, int) else 0
        snapshot_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        snapshot_uri = f"{target_uri}/_history/v{snapshot_version}_{snapshot_id}"
        return WritePlan(
            action="merge",
            target_uri=target_uri,
            merged_fields={
                "expected_version": current_version,
                "code_identity": self._build_identity(candidate),
                "chunk_hash": chunk_hash,
                "latest_snapshot_uri": snapshot_uri,
            },
            relation_edges=[],
        )
