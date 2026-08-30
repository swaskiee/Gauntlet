"""Indexing Layer for GAUNTLET (Phase 3 - REALITY).

Provides multi-dimensional indexing (Entity, Time Range, Event Type) and Bloom filters
to accelerate query planning and avoid scanning non-matching segments on disk.
"""

import hashlib
from typing import Dict, List, Optional, Set, Tuple
from gauntlet.models import Event
from gauntlet.storage.segment import SegmentMetadata


class BloomFilter:
    """Zero-dependency bit array Bloom filter using multiple hash seeds."""

    def __init__(self, size_bits: int = 1024, hash_count: int = 4) -> None:
        self.size_bits = size_bits
        self.hash_count = hash_count
        self.bit_array = bytearray((size_bits + 7) // 8)

    def _hashes(self, item: str) -> List[int]:
        item_bytes = item.encode("utf-8")
        h1 = int(hashlib.md5(item_bytes).hexdigest(), 16)
        h2 = int(hashlib.sha1(item_bytes).hexdigest(), 16)
        hashes = []
        for i in range(self.hash_count):
            combined = (h1 + i * h2) % self.size_bits
            hashes.append(combined)
        return hashes

    def add(self, item: str) -> None:
        for bit_idx in self._hashes(item):
            byte_pos = bit_idx // 8
            bit_pos = bit_idx % 8
            self.bit_array[byte_pos] |= (1 << bit_pos)

    def contains(self, item: str) -> bool:
        """Returns False if item is definitely NOT in set; True if it might be."""
        for bit_idx in self._hashes(item):
            byte_pos = bit_idx // 8
            bit_pos = bit_idx % 8
            if not (self.bit_array[byte_pos] & (1 << bit_pos)):
                return False
        return True


class IndexEngine:
    """Accelerates queries by maintaining sparse spatial, temporal, and entity indexes."""

    def __init__(self) -> None:
        # segment_id -> SegmentMetadata
        self._segments: Dict[str, SegmentMetadata] = {}
        # entity -> Set[segment_id]
        self._entity_to_segments: Dict[str, Set[str]] = {}
        # type -> Set[segment_id]
        self._type_to_segments: Dict[str, Set[str]] = {}
        # segment_id -> BloomFilter of entities
        self._bloom_filters: Dict[str, BloomFilter] = {}

    def register_segment(self, meta: SegmentMetadata) -> None:
        """Indexes a newly created or loaded immutable segment."""
        self._segments[meta.segment_id] = meta

        bloom = BloomFilter()
        for entity in meta.entities:
            if entity not in self._entity_to_segments:
                self._entity_to_segments[entity] = set()
            self._entity_to_segments[entity].add(meta.segment_id)
            bloom.add(entity)

        for event_type in meta.event_types:
            if event_type not in self._type_to_segments:
                self._type_to_segments[event_type] = set()
            self._type_to_segments[event_type].add(meta.segment_id)

        self._bloom_filters[meta.segment_id] = bloom

    def unregister_segment(self, segment_id: str) -> None:
        """Removes a compacted segment from indexes."""
        if segment_id in self._segments:
            del self._segments[segment_id]
        if segment_id in self._bloom_filters:
            del self._bloom_filters[segment_id]

        for seg_set in self._entity_to_segments.values():
            seg_set.discard(segment_id)
        for seg_set in self._type_to_segments.values():
            seg_set.discard(segment_id)

    def find_candidate_segments(
        self,
        entity: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> List[SegmentMetadata]:
        """Prunes segments based on time intervals, entity inverted index, and Bloom filters."""
        candidates = set(self._segments.keys())

        # 1. Prune by entity index and Bloom filter
        if entity:
            entity_segs = self._entity_to_segments.get(entity, set())
            candidates &= entity_segs

        # 2. Prune by event type
        if event_type:
            type_segs = self._type_to_segments.get(event_type, set())
            candidates &= type_segs

        # 3. Prune by temporal bounds (min_ts / max_ts)
        matched_metas: List[SegmentMetadata] = []
        for seg_id in sorted(candidates):
            meta = self._segments[seg_id]
            if start_ts is not None and meta.max_ts < start_ts:
                continue
            if end_ts is not None and meta.min_ts > end_ts:
                continue
            matched_metas.append(meta)

        return matched_metas

    def rebuild_from_segments(self, segments: List[SegmentMetadata]) -> None:
        """Rebuilds the entire in-memory index from authoritative disk metadata."""
        self._segments.clear()
        self._entity_to_segments.clear()
        self._type_to_segments.clear()
        self._bloom_filters.clear()
        for meta in segments:
            self.register_segment(meta)
