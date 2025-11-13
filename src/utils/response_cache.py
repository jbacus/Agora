"""
Response caching system with semantic similarity matching.
Reduces costs by ~80% for repeated/similar queries.
"""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.data.embeddings import cosine_similarity


class ResponseCache:
    """
    Cache responses with semantic similarity matching.
    
    Provides both exact match and semantic similarity caching
    to reduce redundant LLM API calls.
    """
    
    def __init__(
        self,
        ttl_hours: int = 24,
        similarity_threshold: float = 0.95,
        persist_dir: str = "./data/cache",
        max_cache_size: int = 1000
    ):
        self.ttl = timedelta(hours=ttl_hours)
        self.threshold = similarity_threshold
        self.persist_dir = Path(persist_dir)
        self.max_cache_size = max_cache_size
        
        self.cache: Dict[str, dict] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        
        # Create persist directory
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Load from disk if exists
        self._load_cache()
    
    def get(
        self,
        query: str,
        query_embedding: List[float]
    ) -> Optional[dict]:
        """
        Get cached response if similar query exists.
        
        Args:
            query: Query text
            query_embedding: Query embedding vector
            
        Returns:
            Cached response or None
        """
        # Check exact match first
        query_hash = self._hash_query(query)
        if query_hash in self.cache:
            entry = self.cache[query_hash]
            if not self._is_expired(entry):
                self.stats["hits"] += 1
                entry["hits"] += 1
                logger.info(f"Cache HIT (exact): {query[:50]}...")
                return entry["response"]
            else:
                # Remove expired entry
                del self.cache[query_hash]
        
        # Check semantic similarity
        for entry_hash, entry in list(self.cache.items()):
            if self._is_expired(entry):
                del self.cache[entry_hash]
                continue
            
            similarity = cosine_similarity(query_embedding, entry["embedding"])
            if similarity >= self.threshold:
                self.stats["hits"] += 1
                entry["hits"] += 1
                logger.info(
                    f"Cache HIT (semantic, {similarity:.2%}): {query[:50]}..."
                )
                return entry["response"]
        
        # Cache miss
        self.stats["misses"] += 1
        logger.info(f"Cache MISS: {query[:50]}...")
        return None
    
    def set(
        self,
        query: str,
        query_embedding: List[float],
        response: dict
    ):
        """
        Cache a response.
        
        Args:
            query: Query text
            query_embedding: Query embedding vector
            response: Response to cache
        """
        query_hash = self._hash_query(query)
        
        # Evict old entries if cache is full
        if len(self.cache) >= self.max_cache_size:
            self._evict_oldest()
        
        self.cache[query_hash] = {
            "query": query,
            "embedding": query_embedding,
            "response": response,
            "timestamp": datetime.now(),
            "hits": 0
        }
        
        logger.info(f"Cached response for: {query[:50]}...")
        
        # Persist to disk periodically
        if len(self.cache) % 10 == 0:
            self._save_cache()
    
    def clear(self):
        """Clear all cached entries."""
        self.cache.clear()
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            self.stats["hits"] / total_requests
            if total_requests > 0
            else 0
        )
        
        return {
            "size": len(self.cache),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self.stats["evictions"],
            "total_requests": total_requests
        }
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for exact match lookup."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    def _is_expired(self, entry: dict) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() - entry["timestamp"] > self.ttl
    
    def _evict_oldest(self):
        """Evict oldest cache entry."""
        if not self.cache:
            return
        
        oldest_hash = min(
            self.cache.keys(),
            key=lambda h: self.cache[h]["timestamp"]
        )
        del self.cache[oldest_hash]
        self.stats["evictions"] += 1
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            cache_file = self.persist_dir / "response_cache.json"
            
            # Convert to serializable format
            serializable_cache = {}
            for key, entry in self.cache.items():
                serializable_cache[key] = {
                    "query": entry["query"],
                    "embedding": entry["embedding"],
                    "response": entry["response"],
                    "timestamp": entry["timestamp"].isoformat(),
                    "hits": entry["hits"]
                }
            
            with open(cache_file, "w") as f:
                json.dump(serializable_cache, f)
            
            logger.debug(f"Saved {len(self.cache)} entries to cache")
        
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_cache(self):
        """Load cache from disk."""
        try:
            cache_file = self.persist_dir / "response_cache.json"
            
            if not cache_file.exists():
                return
            
            with open(cache_file) as f:
                serializable_cache = json.load(f)
            
            # Convert back to cache format
            for key, entry in serializable_cache.items():
                self.cache[key] = {
                    "query": entry["query"],
                    "embedding": entry["embedding"],
                    "response": entry["response"],
                    "timestamp": datetime.fromisoformat(entry["timestamp"]),
                    "hits": entry["hits"]
                }
            
            # Remove expired entries
            expired = [
                key for key, entry in self.cache.items()
                if self._is_expired(entry)
            ]
            for key in expired:
                del self.cache[key]
            
            logger.info(
                f"Loaded {len(self.cache)} cached entries "
                f"({len(expired)} expired)"
            )
        
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            self.cache = {}
