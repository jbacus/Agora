"""
Telemetry and analytics system for Agora.
Tracks usage patterns, performance metrics, and costs.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class Telemetry:
    """
    Simple telemetry system for tracking usage and performance.
    
    Logs events to a JSONL file for later analysis.
    """
    
    def __init__(self, log_file: str = "logs/telemetry.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory counters for quick stats
        self.counters = {
            "queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
    
    def log_query(
        self,
        query: str,
        selected_authors: List[str],
        response_time: float,
        cache_hit: bool = False,
        error: Optional[str] = None
    ):
        """Log a query event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "query",
            "query": query[:100],  # Truncate long queries
            "authors_selected": selected_authors,
            "response_time_seconds": response_time,
            "cache_hit": cache_hit,
            "error": error
        }
        
        self._write_event(event)
        self.counters["queries"] += 1
        
        if cache_hit:
            self.counters["cache_hits"] += 1
        else:
            self.counters["cache_misses"] += 1
        
        if error:
            self.counters["errors"] += 1
    
    def log_author_selection(
        self,
        query: str,
        author_id: str,
        relevance_score: float
    ):
        """Log author selection event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "author_selection",
            "query": query[:100],
            "author_id": author_id,
            "relevance_score": relevance_score
        }
        
        self._write_event(event)
    
    def log_response_generated(
        self,
        author_id: str,
        generation_time: float,
        token_count: Optional[int] = None
    ):
        """Log response generation event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "response_generated",
            "author_id": author_id,
            "generation_time_seconds": generation_time,
            "token_count": token_count
        }
        
        self._write_event(event)
    
    def log_error(self, error_type: str, error_message: str, context: dict = None):
        """Log an error event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "error",
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {}
        }
        
        self._write_event(event)
        self.counters["errors"] += 1
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        cache_hit_rate = (
            self.counters["cache_hits"] /
            (self.counters["cache_hits"] + self.counters["cache_misses"])
            if (self.counters["cache_hits"] + self.counters["cache_misses"]) > 0
            else 0
        )
        
        return {
            **self.counters,
            "cache_hit_rate": cache_hit_rate
        }
    
    def _write_event(self, event: dict):
        """Write event to log file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write telemetry event: {e}")


# Global telemetry instance
_telemetry_instance = None


def get_telemetry() -> Telemetry:
    """Get global telemetry instance."""
    global _telemetry_instance
    if _telemetry_instance is None:
        _telemetry_instance = Telemetry()
    return _telemetry_instance
