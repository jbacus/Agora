#!/usr/bin/env python3
"""
Agora LibraryThing Agentic Text Acquisition Script
==================================================

Multi-agent system where each author operates as an autonomous agent with:
- Automatic profile inference (era, public domain status)
- Intelligent strategy selection
- Autonomous decision-making
- Independent book acquisition

Source Agents - Specialists for each repository:
- GutenbergAgent: Expert in pre-1928 classics (90% confidence)
- InternetArchiveAgent: All eras, scanned books (60% confidence)
- WikisourceAgent: Ancient texts, foreign languages (85% confidence)

Shared Knowledge Base:
- Tracks successful/failed searches
- Records source performance
- Recommends best strategies
- Manages rate limiting

Usage:
    python scripts/acquire_from_librarything_agentic.py --input library.tsv
    python scripts/acquire_from_librarything_agentic.py --input library.tsv --max-concurrent 20
    python scripts/acquire_from_librarything_agentic.py --input library.tsv --author-filter "Marx,Whitman" --verbose
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import quote_plus
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class Era(Enum):
    """Historical eras for author classification"""
    ANCIENT = "ancient"          # Before 500 CE
    CLASSICAL = "classical"      # 500-1500 CE
    EARLY_MODERN = "early_modern" # 1500-1800 CE
    MODERN = "modern"            # 1800-1928 (public domain)
    CONTEMPORARY = "contemporary" # After 1928


@dataclass
class Book:
    """Represents a book from LibraryThing export"""
    title: str
    author: str
    author_normalized: str
    isbn: Optional[str] = None
    publication_date: Optional[str] = None
    source_id: Optional[str] = None  # Generic ID (gutenberg_id, archive_id, etc.)
    source_url: Optional[str] = None
    source_name: Optional[str] = None  # "gutenberg", "archive", "wikisource"
    downloaded: bool = False
    download_path: Optional[str] = None
    error: Optional[str] = None
    confidence: float = 0.0  # Agent's confidence in the match


@dataclass
class AuthorProfile:
    """Profile of an author inferred from their works"""
    name: str
    normalized_id: str
    era: Era
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    is_public_domain: bool = False
    languages: Set[str] = field(default_factory=lambda: {"english"})
    total_books: int = 0

    def __post_init__(self):
        """Infer public domain status and era"""
        if self.death_year:
            # Simple heuristic: public domain if died before 1954 (70 years ago)
            self.is_public_domain = self.death_year < 1954

            # Infer era from death year
            if self.death_year < 500:
                self.era = Era.ANCIENT
            elif self.death_year < 1500:
                self.era = Era.CLASSICAL
            elif self.death_year < 1800:
                self.era = Era.EARLY_MODERN
            elif self.death_year < 1928:
                self.era = Era.MODERN
            else:
                self.era = Era.CONTEMPORARY


@dataclass
class SearchStrategy:
    """Strategy for searching sources"""
    source_name: str
    priority: int  # 1=highest, 5=lowest
    confidence: float  # Expected success rate 0.0-1.0
    reason: str  # Why this strategy was chosen


@dataclass
class SearchResult:
    """Result from a source agent search"""
    success: bool
    book: Optional[Book] = None
    source_name: str = ""
    confidence: float = 0.0
    error: Optional[str] = None
    search_time_ms: float = 0.0


@dataclass
class AgentDecision:
    """Autonomous decision made by an agent"""
    agent_id: str
    decision_type: str  # "strategy_selection", "source_search", "download"
    reasoning: str
    confidence: float
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# SHARED KNOWLEDGE BASE
# ============================================================================

class SharedKnowledgeBase:
    """
    Shared knowledge base for all agents to learn from each other.

    Tracks:
    - Successful searches per source
    - Failed searches to avoid repetition
    - Source performance metrics
    - Rate limiting coordination
    """

    def __init__(self):
        self.successful_searches: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)  # source -> [(author, title, id)]
        self.failed_searches: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)  # source -> {(author, title)}
        self.source_stats: Dict[str, Dict[str, any]] = defaultdict(lambda: {
            "total_searches": 0,
            "successful_searches": 0,
            "total_downloads": 0,
            "avg_confidence": 0.0,
            "last_request_time": 0.0
        })
        self.decisions: List[AgentDecision] = []
        self._lock = asyncio.Lock()

    async def record_search(self, source: str, author: str, title: str, success: bool, source_id: Optional[str] = None):
        """Record a search result"""
        async with self._lock:
            self.source_stats[source]["total_searches"] += 1
            if success and source_id:
                self.successful_searches[source].append((author, title, source_id))
                self.source_stats[source]["successful_searches"] += 1
            elif not success:
                self.failed_searches[source].add((author, title))

    async def record_download(self, source: str):
        """Record a successful download"""
        async with self._lock:
            self.source_stats[source]["total_downloads"] += 1

    async def record_decision(self, decision: AgentDecision):
        """Record an agent decision for analysis"""
        async with self._lock:
            self.decisions.append(decision)

    async def update_rate_limit(self, source: str):
        """Update last request time for rate limiting"""
        async with self._lock:
            self.source_stats[source]["last_request_time"] = time.time()

    async def should_rate_limit(self, source: str, min_delay: float = 1.0) -> bool:
        """Check if we should rate limit requests to a source"""
        async with self._lock:
            last_time = self.source_stats[source]["last_request_time"]
            return (time.time() - last_time) < min_delay

    async def get_source_performance(self, source: str) -> Dict:
        """Get performance metrics for a source"""
        async with self._lock:
            return self.source_stats[source].copy()

    async def get_best_source_for_profile(self, profile: AuthorProfile) -> str:
        """Recommend best source based on author profile and past performance"""
        async with self._lock:
            # Simple heuristic based on era and success rates
            if profile.era == Era.ANCIENT:
                return "wikisource"
            elif profile.era in [Era.CLASSICAL, Era.EARLY_MODERN]:
                return "gutenberg" if self.source_stats["gutenberg"]["successful_searches"] > 0 else "wikisource"
            elif profile.era == Era.MODERN and profile.is_public_domain:
                return "gutenberg"
            else:
                return "archive"  # Contemporary works might be in archive

    def get_summary(self) -> Dict:
        """Get summary of all knowledge"""
        total_searches = sum(stats["total_searches"] for stats in self.source_stats.values())
        successful = sum(stats["successful_searches"] for stats in self.source_stats.values())

        return {
            "total_searches": total_searches,
            "successful": successful,
            "failed": total_searches - successful,
            "sources": dict(self.source_stats),
            "total_decisions": len(self.decisions)
        }


# ============================================================================
# SOURCE AGENTS (Specialists)
# ============================================================================

class SourceAgent(ABC):
    """Base class for source-specific agents"""

    def __init__(self, knowledge_base: SharedKnowledgeBase):
        self.knowledge_base = knowledge_base
        self.session = self._create_session()
        self.source_name = self.__class__.__name__.replace("Agent", "").lower()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; AgoraAgenticBot/1.0; +https://github.com/agora)',
            'Accept': 'application/json, text/html',
        })
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    @abstractmethod
    async def search(self, author: str, title: str, profile: AuthorProfile) -> SearchResult:
        """Search for a book in this source"""
        pass

    @abstractmethod
    async def download(self, book: Book, output_dir: Path) -> bool:
        """Download a book from this source"""
        pass

    @abstractmethod
    def get_confidence_for_profile(self, profile: AuthorProfile) -> float:
        """Get confidence score for this source given an author profile"""
        pass


class GutenbergAgent(SourceAgent):
    """Expert agent for Project Gutenberg"""

    GUTENBERG_API = "https://gutendex.com/books"
    GUTENBERG_MIRROR = "https://www.gutenberg.org"

    def get_confidence_for_profile(self, profile: AuthorProfile) -> float:
        """Gutenberg is best for pre-1928 English texts"""
        if not profile.is_public_domain:
            return 0.1
        if profile.era == Era.MODERN:
            return 0.9
        elif profile.era == Era.EARLY_MODERN:
            return 0.85
        elif profile.era == Era.CLASSICAL:
            return 0.7
        else:
            return 0.5

    async def search(self, author: str, title: str, profile: AuthorProfile) -> SearchResult:
        """Search Gutenberg"""
        start_time = time.time()

        # Check rate limiting
        while await self.knowledge_base.should_rate_limit(self.source_name, 1.0):
            await asyncio.sleep(0.5)

        try:
            # Run API call in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._search_sync, author, title)

            elapsed = (time.time() - start_time) * 1000
            await self.knowledge_base.update_rate_limit(self.source_name)

            if result:
                book = Book(
                    title=title,
                    author=author,
                    author_normalized=profile.normalized_id,
                    source_id=result["id"],
                    source_url=result["url"],
                    source_name="gutenberg",
                    confidence=0.9
                )
                await self.knowledge_base.record_search(self.source_name, author, title, True, result["id"])
                return SearchResult(success=True, book=book, source_name="gutenberg", confidence=0.9, search_time_ms=elapsed)
            else:
                await self.knowledge_base.record_search(self.source_name, author, title, False)
                return SearchResult(success=False, source_name="gutenberg", search_time_ms=elapsed)

        except Exception as e:
            logger.error(f"Gutenberg search error: {e}")
            await self.knowledge_base.record_search(self.source_name, author, title, False)
            return SearchResult(success=False, source_name="gutenberg", error=str(e))

    def _search_sync(self, author: str, title: str) -> Optional[Dict]:
        """Synchronous API search"""
        try:
            params = {'search': f"{author} {title}"}
            response = self.session.get(self.GUTENBERG_API, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    book = data['results'][0]
                    # Find text/plain format
                    for fmt, url in book.get('formats', {}).items():
                        if 'text/plain' in fmt:
                            return {"id": str(book['id']), "url": url}
            return None
        except Exception as e:
            logger.debug(f"Gutenberg API error: {e}")
            return None

    async def download(self, book: Book, output_dir: Path) -> bool:
        """Download from Gutenberg"""
        try:
            author_dir = output_dir / book.author_normalized
            author_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{book.author_normalized}_{book.title[:50]}.txt"
            filename = re.sub(r'[^\w\s-]', '', filename).strip().replace(' ', '_')
            filepath = author_dir / filename

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.session.get(book.source_url, timeout=30)
            )

            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                book.downloaded = True
                book.download_path = str(filepath)
                await self.knowledge_base.record_download(self.source_name)
                logger.info(f"Downloaded: {filename}")
                return True
            return False

        except Exception as e:
            logger.error(f"Download error: {e}")
            book.error = str(e)
            return False


class InternetArchiveAgent(SourceAgent):
    """Expert agent for Internet Archive"""

    ARCHIVE_API = "https://archive.org/advancedsearch.php"

    def get_confidence_for_profile(self, profile: AuthorProfile) -> float:
        """Archive has everything but lower quality"""
        return 0.6  # Moderate confidence for all eras

    async def search(self, author: str, title: str, profile: AuthorProfile) -> SearchResult:
        """Search Internet Archive"""
        # Placeholder - would implement similar to Gutenberg
        return SearchResult(success=False, source_name="archive", error="Not implemented")

    async def download(self, book: Book, output_dir: Path) -> bool:
        """Download from Archive"""
        return False


class WikisourceAgent(SourceAgent):
    """Expert agent for Wikisource"""

    WIKISOURCE_API = "https://en.wikisource.org/w/api.php"

    def get_confidence_for_profile(self, profile: AuthorProfile) -> float:
        """Wikisource is best for ancient/classical texts"""
        if profile.era == Era.ANCIENT:
            return 0.9
        elif profile.era == Era.CLASSICAL:
            return 0.85
        else:
            return 0.4

    async def search(self, author: str, title: str, profile: AuthorProfile) -> SearchResult:
        """Search Wikisource"""
        # Placeholder - would implement similar to Gutenberg
        return SearchResult(success=False, source_name="wikisource", error="Not implemented")

    async def download(self, book: Book, output_dir: Path) -> bool:
        """Download from Wikisource"""
        return False


# ============================================================================
# AUTHOR AGENT (Autonomous)
# ============================================================================

class AuthorAgent:
    """
    Autonomous agent representing an author.

    Capabilities:
    - Infers own profile from book data
    - Selects best search strategy
    - Searches multiple sources
    - Makes autonomous decisions
    - Learns from shared knowledge
    """

    def __init__(
        self,
        author_name: str,
        books: List[Book],
        knowledge_base: SharedKnowledgeBase,
        source_agents: Dict[str, SourceAgent]
    ):
        self.author_name = author_name
        self.books = books
        self.knowledge_base = knowledge_base
        self.source_agents = source_agents
        self.profile = self._infer_profile()
        self.agent_id = f"author_agent_{self.profile.normalized_id}"

        logger.info(f"Initialized {self.agent_id}: {len(books)} books, era={self.profile.era.value}, pd={self.profile.is_public_domain}")

    def _infer_profile(self) -> AuthorProfile:
        """Infer author profile from available data"""
        normalized_id = re.sub(r'[^\w\s-]', '', self.author_name).strip().replace(' ', '_').lower()

        # Try to infer from author name (this is a simplified heuristic)
        profile = AuthorProfile(
            name=self.author_name,
            normalized_id=normalized_id,
            era=Era.MODERN,  # Default
            total_books=len(self.books)
        )

        # Simple heuristics based on author name
        ancient_indicators = ["homer", "virgil", "plato", "aristotle"]
        classical_indicators = ["dante", "chaucer", "aquinas"]
        early_modern_indicators = ["shakespeare", "milton", "voltaire"]
        modern_indicators = ["marx", "whitman", "baudelaire", "dickens", "twain"]

        name_lower = self.author_name.lower()

        if any(ind in name_lower for ind in ancient_indicators):
            profile.era = Era.ANCIENT
            profile.is_public_domain = True
        elif any(ind in name_lower for ind in classical_indicators):
            profile.era = Era.CLASSICAL
            profile.is_public_domain = True
        elif any(ind in name_lower for ind in early_modern_indicators):
            profile.era = Era.EARLY_MODERN
            profile.is_public_domain = True
        elif any(ind in name_lower for ind in modern_indicators):
            profile.era = Era.MODERN
            profile.is_public_domain = True

        return profile

    async def select_strategy(self) -> List[SearchStrategy]:
        """
        Autonomously select search strategy based on profile and shared knowledge.

        Returns strategies ordered by priority (highest first).
        """
        strategies = []

        # Get confidence from each source agent
        for source_name, agent in self.source_agents.items():
            confidence = agent.get_confidence_for_profile(self.profile)

            # Get performance stats from knowledge base
            perf = await self.knowledge_base.get_source_performance(source_name)
            success_rate = perf["successful_searches"] / max(perf["total_searches"], 1)

            # Combine agent confidence with observed performance
            adjusted_confidence = (confidence * 0.7) + (success_rate * 0.3)

            strategies.append(SearchStrategy(
                source_name=source_name,
                priority=0,  # Will be set after sorting
                confidence=adjusted_confidence,
                reason=f"Era={self.profile.era.value}, agent_conf={confidence:.2f}, observed_success={success_rate:.2f}"
            ))

        # Sort by confidence and assign priorities
        strategies.sort(key=lambda s: s.confidence, reverse=True)
        for i, strategy in enumerate(strategies, 1):
            strategy.priority = i

        # Record decision
        decision = AgentDecision(
            agent_id=self.agent_id,
            decision_type="strategy_selection",
            reasoning=f"Selected {len(strategies)} strategies based on profile and knowledge",
            confidence=strategies[0].confidence if strategies else 0.0
        )
        await self.knowledge_base.record_decision(decision)

        return strategies

    async def acquire_books(self, output_dir: Path, max_retries: int = 2) -> Dict:
        """
        Autonomously acquire all books for this author.

        Returns summary statistics.
        """
        logger.info(f"[{self.agent_id}] Starting acquisition for {len(self.books)} books")

        strategies = await self.select_strategy()
        logger.info(f"[{self.agent_id}] Selected strategies: {[(s.source_name, s.confidence) for s in strategies]}")

        stats = {
            "total": len(self.books),
            "found": 0,
            "downloaded": 0,
            "failed": 0
        }

        for book in self.books:
            found = False

            # Try each strategy in order of priority
            for strategy in strategies:
                if found:
                    break

                agent = self.source_agents[strategy.source_name]

                logger.debug(f"[{self.agent_id}] Searching {strategy.source_name} for '{book.title}'")
                result = await agent.search(book.author, book.title, self.profile)

                if result.success and result.book:
                    # Download the book
                    success = await agent.download(result.book, output_dir)
                    if success:
                        stats["found"] += 1
                        stats["downloaded"] += 1
                        found = True
                        logger.info(f"[{self.agent_id}] ✓ Found and downloaded '{book.title}' from {strategy.source_name}")
                    else:
                        logger.warning(f"[{self.agent_id}] Found but failed to download '{book.title}' from {strategy.source_name}")

            if not found:
                stats["failed"] += 1
                logger.warning(f"[{self.agent_id}] ✗ Failed to find '{book.title}' in any source")

        logger.info(f"[{self.agent_id}] Completed: {stats['downloaded']}/{stats['total']} books downloaded")
        return stats


# ============================================================================
# AGENTIC ORCHESTRATOR
# ============================================================================

class AgenticOrchestrator:
    """
    Orchestrates multiple author agents running in parallel.

    Manages:
    - Concurrent execution with limits
    - Shared knowledge base
    - Performance monitoring
    - Results aggregation
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.knowledge_base = SharedKnowledgeBase()
        self.source_agents = {
            "gutenberg": GutenbergAgent(self.knowledge_base),
            "archive": InternetArchiveAgent(self.knowledge_base),
            "wikisource": WikisourceAgent(self.knowledge_base)
        }

    async def orchestrate(
        self,
        books_by_author: Dict[str, List[Book]],
        output_dir: Path
    ) -> Dict:
        """
        Orchestrate parallel acquisition across all authors.

        Args:
            books_by_author: Dictionary mapping author names to their books
            output_dir: Directory to save downloaded books

        Returns:
            Summary statistics and insights
        """
        start_time = time.time()

        # Create author agents
        author_agents = []
        for author_name, books in books_by_author.items():
            agent = AuthorAgent(author_name, books, self.knowledge_base, self.source_agents)
            author_agents.append(agent)

        logger.info(f"Created {len(author_agents)} author agents")
        logger.info(f"Max concurrent agents: {self.max_concurrent}")

        # Run agents with concurrency limit
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_agent(agent: AuthorAgent):
            async with semaphore:
                return await agent.acquire_books(output_dir)

        # Execute all agents in parallel (with concurrency limit)
        results = await asyncio.gather(*[run_agent(agent) for agent in author_agents])

        elapsed = time.time() - start_time

        # Aggregate results
        summary = {
            "total_agents": len(author_agents),
            "total_books": sum(r["total"] for r in results),
            "books_found": sum(r["found"] for r in results),
            "books_downloaded": sum(r["downloaded"] for r in results),
            "books_failed": sum(r["failed"] for r in results),
            "execution_time_seconds": elapsed,
            "knowledge_base": self.knowledge_base.get_summary()
        }

        return summary


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def normalize_author(author: str) -> str:
    """Normalize author name for directory naming"""
    return re.sub(r'[^\w\s-]', '', author).strip().replace(' ', '_').lower()


def parse_librarything_export(filepath: Path) -> Dict[str, List[Book]]:
    """Parse LibraryThing TSV export"""
    books_by_author = defaultdict(list)

    with open(filepath, 'r', encoding='utf-8') as f:
        # LibraryThing exports are TSV with headers
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            title = row.get('TITLE', '').strip()
            author = row.get('AUTHOR (LAST, FIRST)', '') or row.get('AUTHOR', '')
            author = author.strip()

            if not title or not author:
                continue

            book = Book(
                title=title,
                author=author,
                author_normalized=normalize_author(author),
                isbn=row.get('ISBN', None)
            )

            books_by_author[author].append(book)

    return dict(books_by_author)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Agentic book acquisition from LibraryThing')
    parser.add_argument('--input', required=True, help='Path to LibraryThing export file (TSV/JSON)')
    parser.add_argument('--output-dir', default='data/raw', help='Output directory for downloads')
    parser.add_argument('--max-concurrent', type=int, default=5, help='Max concurrent author agents')
    parser.add_argument('--author-filter', help='Comma-separated list of authors to process')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Loading books from {input_path}")
    books_by_author = parse_librarything_export(input_path)

    # Apply author filter if specified
    if args.author_filter:
        filter_authors = set(a.strip() for a in args.author_filter.split(','))
        books_by_author = {
            author: books for author, books in books_by_author.items()
            if any(fa.lower() in author.lower() for fa in filter_authors)
        }

    logger.info(f"Processing {len(books_by_author)} authors, {sum(len(b) for b in books_by_author.values())} total books")

    # Run orchestrator
    orchestrator = AgenticOrchestrator(max_concurrent=args.max_concurrent)
    summary = await orchestrator.orchestrate(books_by_author, output_dir)

    # Print results
    print("\n" + "="*60)
    print("AGENTIC ACQUISITION SUMMARY")
    print("="*60)
    print(f"Authors processed: {summary['total_agents']}")
    print(f"Total books: {summary['total_books']}")
    print(f"Books found: {summary['books_found']}")
    print(f"Books downloaded: {summary['books_downloaded']}")
    print(f"Books failed: {summary['books_failed']}")
    print(f"Success rate: {summary['books_downloaded']/max(summary['total_books'],1)*100:.1f}%")
    print(f"Execution time: {summary['execution_time_seconds']:.3f}s")
    print()
    print("KNOWLEDGE BASE INSIGHTS")
    print("="*60)
    kb = summary['knowledge_base']
    print(f"Total searches: {kb['total_searches']}")
    print(f"Successful: {kb['successful']}")
    print(f"Failed: {kb['failed']}")
    print()
    print("Source Performance:")
    for source, stats in kb['sources'].items():
        if stats['total_searches'] > 0:
            success_rate = stats['successful_searches'] / stats['total_searches'] * 100
            print(f"  {source}: {stats['successful_searches']}/{stats['total_searches']} searches ({success_rate:.1f}%), {stats['total_downloads']} downloads")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
